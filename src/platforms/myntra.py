"""
Myntra product information handler.
Extracts product ID and fetches product details.
"""

import re
import json
import logging
from typing import Optional
from urllib.parse import urlparse

from .base import BasePlatform, ProductInfo

logger = logging.getLogger(__name__)


class MyntraHandler(BasePlatform):
    """Handler for Myntra product URLs."""
    
    PLATFORM_NAME = "Myntra"
    
    # Myntra domain patterns
    MYNTRA_DOMAINS = ['myntra.com', 'myntr.in']
    
    # Browser-like user agents
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    ]
    
    def _get_browser_headers(self) -> dict:
        """Generate browser-like headers to avoid blocking."""
        import random
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.myntra.com/',
        }
    
    def matches_url(self, url: str) -> bool:
        """Check if URL is a Myntra URL."""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return any(d in domain for d in self.MYNTRA_DOMAINS)
        except Exception:
            return False
    
    def extract_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from Myntra URL."""
        try:
            # Pattern: myntra.com/product-name/product-variant/12345678/buy
            # or: myntra.com/product/12345678
            pid_match = re.search(r'/(\d{6,10})(?:/|$|\?)', url)
            if pid_match:
                return pid_match.group(1)
            
            # Pattern in query params
            parsed = urlparse(url)
            if 'id=' in parsed.query:
                id_match = re.search(r'id=(\d+)', parsed.query)
                if id_match:
                    return id_match.group(1)
            
            return None
        except Exception as e:
            logger.error(f"Error extracting Myntra product ID: {e}")
            return None
    
    async def get_product_info(self, url: str) -> Optional[ProductInfo]:
        """Get product information from Myntra."""
        product_id = self.extract_product_id(url)
        if not product_id:
            logger.warning(f"Could not extract product ID from: {url}")
            return await self._fetch_from_page(url)
        
        logger.info(f"Fetching Myntra product: {product_id}")
        
        # Try API first
        product_info = await self._fetch_from_api(product_id, url)
        
        if not product_info or not product_info.is_valid():
            # Fallback to page scraping
            product_info = await self._fetch_from_page(url)
        
        return product_info
    
    async def _fetch_from_api(self, product_id: str, original_url: str) -> Optional[ProductInfo]:
        """Fetch product info from Myntra's catalogue API."""
        api_url = f"https://www.myntra.com/gateway/v2/product/{product_id}"
        
        headers = {
            **self._get_browser_headers(),
            'Accept': 'application/json',
        }
        
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(api_url, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = self._parse_api_response(data, product_id, original_url)
                        if result:
                            result.raw_response = data  # Store raw response
                        return result
                    logger.debug(f"Myntra API status: {response.status}")
                    return None
        except Exception as e:
            logger.debug(f"Myntra API error: {e}")
            return None
    
    async def _fetch_from_page(self, url: str) -> Optional[ProductInfo]:
        """Fetch product info by scraping the page."""
        headers = self._get_browser_headers()
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_html(html, url)
                    logger.debug(f"Myntra page status: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching Myntra page: {e}")
            return None
    
    def _parse_api_response(self, data: dict, product_id: str, url: str) -> Optional[ProductInfo]:
        """Parse Myntra API response."""
        info = ProductInfo(
            platform=self.PLATFORM_NAME,
            product_id=product_id,
            url=url,
        )
        
        try:
            style = data.get('style', {})
            
            # Basic info
            info.title = style.get('name')
            info.brand = style.get('brand', {}).get('name') or style.get('brandName')
            info.category = style.get('articleType', {}).get('typeName')
            
            # Pricing
            price_info = style.get('price', {})
            info.current_price = price_info.get('discounted')
            info.original_price = price_info.get('mrp')
            info.discount_percent = price_info.get('discount')
            
            # Rating
            ratings = style.get('ratings', {})
            info.rating = ratings.get('averageRating')
            info.rating_count = ratings.get('totalCount')
            
            # Image
            media = style.get('media', {}).get('albums', [])
            if media:
                images = media[0].get('images', [])
                if images:
                    info.image_url = images[0].get('secureSrc') or images[0].get('src')
            
            # Stock status
            inventory = style.get('inventory', {})
            info.in_stock = inventory.get('available', True)
            
            # Additional info
            info.extra = {
                'color': style.get('baseColour'),
                'gender': style.get('gender'),
                'season': style.get('season'),
            }
            
            # Calculate discount if not provided
            if not info.discount_percent:
                info.discount_percent = info.calculate_discount()
            
            return info if info.is_valid() else None
            
        except Exception as e:
            logger.error(f"Error parsing Myntra API response: {e}")
            return None
    
    def _parse_html(self, html: str, url: str) -> Optional[ProductInfo]:
        """Parse Myntra HTML for product info."""
        info = ProductInfo(
            platform=self.PLATFORM_NAME,
            url=url,
        )
        
        try:
            # Look for pdpData in script
            pdp_match = re.search(
                r'window\.__myx\s*=\s*(\{.*?"pdpData".*?\});?\s*</script>',
                html, re.DOTALL
            )
            if pdp_match:
                try:
                    myx_data = json.loads(pdp_match.group(1))
                    pdp_data = myx_data.get('pdpData', {})
                    
                    # Store raw response
                    info.raw_response = pdp_data
                    
                    info.title = pdp_data.get('name')
                    info.brand = pdp_data.get('brand', {}).get('name')
                    info.product_id = str(pdp_data.get('id', ''))
                    
                    price = pdp_data.get('price', {})
                    info.current_price = price.get('discounted')
                    info.original_price = price.get('mrp')
                    info.discount_percent = price.get('discount')
                    
                    ratings = pdp_data.get('ratings', {})
                    info.rating = ratings.get('averageRating')
                    info.rating_count = ratings.get('totalCount')
                    
                    # Stock status - check multiple places
                    flags = pdp_data.get('flags', {})
                    out_of_stock = flags.get('outOfStock')
                    if out_of_stock is True:
                        info.in_stock = False
                    elif out_of_stock is False:
                        info.in_stock = True
                    else:
                        # Check sizes for stock info
                        sizes = pdp_data.get('sizes', [])
                        if sizes:
                            info.in_stock = any(s.get('available', False) for s in sizes)
                        else:
                            info.in_stock = None  # Unknown
                    
                except json.JSONDecodeError:
                    pass
            
            # Fallback: JSON-LD
            if not info.title:
                schema_match = re.search(
                    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                    html, re.DOTALL | re.IGNORECASE
                )
                if schema_match:
                    try:
                        schema_data = json.loads(schema_match.group(1))
                        if isinstance(schema_data, list):
                            for item in schema_data:
                                if item.get('@type') == 'Product':
                                    schema_data = item
                                    break
                        
                        if schema_data.get('@type') == 'Product':
                            info.title = schema_data.get('name')
                            info.brand = schema_data.get('brand', {}).get('name')
                            info.image_url = schema_data.get('image')
                            
                            offers = schema_data.get('offers', {})
                            if isinstance(offers, list):
                                offers = offers[0] if offers else {}
                            info.current_price = self._clean_price(str(offers.get('price', '')))
                    except json.JSONDecodeError:
                        pass
            
            # Fallback: Regex patterns
            if not info.title:
                title_match = re.search(r'<h1[^>]*class="[^"]*pdp-title[^"]*"[^>]*>([^<]+)</h1>', html)
                if title_match:
                    info.title = title_match.group(1).strip()
            
            if not info.brand:
                brand_match = re.search(r'<h1[^>]*class="[^"]*pdp-name[^"]*"[^>]*>([^<]+)</h1>', html)
                if brand_match:
                    info.brand = brand_match.group(1).strip()
            
            if not info.current_price:
                price_match = re.search(r'<span[^>]*class="[^"]*pdp-price[^"]*"[^>]*>.*?(\d[\d,]+)', html, re.DOTALL)
                if price_match:
                    info.current_price = self._clean_price(price_match.group(1))
            
            # Extract product ID from URL if not set
            if not info.product_id:
                info.product_id = self.extract_product_id(url)
            
            # Calculate discount if not set
            if not info.discount_percent:
                info.discount_percent = info.calculate_discount()
            
            return info if info.is_valid() else None
            
        except Exception as e:
            logger.error(f"Error parsing Myntra HTML: {e}")
            return None
