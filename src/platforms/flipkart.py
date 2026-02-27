"""
Flipkart product information handler.
Extracts PID and fetches product details.
"""

import re
import json
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs, unquote

from .base import BasePlatform, ProductInfo

logger = logging.getLogger(__name__)


class FlipkartHandler(BasePlatform):
    """Handler for Flipkart product URLs."""
    
    PLATFORM_NAME = "Flipkart"
    
    # Flipkart domain patterns
    FLIPKART_DOMAINS = ['flipkart.com', 'fkrt.it', 'fkrt.to', 'dl.flipkart.com']
    
    # Browser-like user agents to avoid 403
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    def matches_url(self, url: str) -> bool:
        """Check if URL is a Flipkart URL."""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return any(d in domain for d in self.FLIPKART_DOMAINS)
        except Exception:
            return False
    
    def extract_product_id(self, url: str) -> Optional[str]:
        """Extract PID from Flipkart URL."""
        try:
            # Pattern 1: pid= in query string
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if 'pid' in query_params:
                return query_params['pid'][0]
            
            # Pattern 2: /p/itm... format
            pid_match = re.search(r'/p/(itm[a-zA-Z0-9]+)', url, re.IGNORECASE)
            if pid_match:
                return pid_match.group(1)
            
            # Pattern 3: Product ID in path /product-name/p/pid
            path_match = re.search(r'/p/([a-zA-Z0-9]+)(?:\?|$|&)', url)
            if path_match:
                return path_match.group(1)
            
            # Pattern 4: ppn parameter
            if 'ppn' in query_params:
                ppn = query_params['ppn'][0]
                pid_in_ppn = re.search(r'(itm[a-zA-Z0-9]+)', ppn)
                if pid_in_ppn:
                    return pid_in_ppn.group(1)
            
            return None
        except Exception as e:
            logger.error(f"Error extracting Flipkart PID: {e}")
            return None
    
    async def get_product_info(self, url: str) -> Optional[ProductInfo]:
        """Get product information from Flipkart."""
        pid = self.extract_product_id(url)
        if not pid:
            logger.warning(f"Could not extract PID from: {url}")
            # Try to get info from the page directly
            return await self._fetch_from_page(url)
        
        logger.info(f"Fetching Flipkart product: {pid}")
        
        # Try API first
        product_info = await self._fetch_from_api(pid, url)
        
        if not product_info or not product_info.is_valid():
            # Fallback to page scraping
            product_info = await self._fetch_from_page(url)
        
        # If still no info, try to extract from URL
        if not product_info or not product_info.is_valid():
            product_info = self._extract_from_url(pid, url)
        
        return product_info
    
    def _extract_from_url(self, pid: str, url: str) -> Optional[ProductInfo]:
        """Extract basic product info from URL when scraping fails."""
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            # Extract product name from URL path
            # Format: /product-name-with-dashes/p/item123
            parts = path.strip('/').split('/')
            if len(parts) >= 2:
                product_slug = parts[0]
                # Convert slug to title: "kwality-vanilla-ice-cream" -> "Kwality Vanilla Ice Cream"
                title = product_slug.replace('-', ' ').title()
                
                return ProductInfo(
                    platform=self.PLATFORM_NAME,
                    product_id=pid,
                    url=url,
                    title=title,
                )
            return None
        except Exception as e:
            logger.debug(f"Error extracting from URL: {e}")
            return None
    
    async def _fetch_from_api(self, pid: str, original_url: str) -> Optional[ProductInfo]:
        """Fetch product info from Flipkart's internal API."""
        # Flipkart's product API endpoint
        api_url = f"https://www.flipkart.com/api/3/page/dynamic/product"
        
        headers = {
            **self._get_browser_headers(),
            'X-User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 FKUA/website/42/website/Desktop',
            'Content-Type': 'application/json',
        }
        
        payload = {
            "requestContext": {
                "productId": pid
            }
        }
        
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(api_url, headers=headers, json=payload, ssl=False) as response:
                    if response.status != 200:
                        logger.debug(f"Flipkart API status: {response.status}")
                        return None
                    data = await response.json()
                    return self._parse_api_response(data, pid, original_url)
        except Exception as e:
            logger.debug(f"Flipkart API error: {e}")
            return None
    
    def _get_browser_headers(self) -> dict:
        """Generate browser-like headers to avoid 403."""
        import random
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.flipkart.com/',
        }
    
    def _get_mobile_headers(self) -> dict:
        """Generate mobile headers for Flipkart (less likely to be blocked)."""
        return {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-IN,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Ch-Ua-Mobile': '?1',
            'Sec-Ch-Ua-Platform': '"Android"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def _fetch_from_page(self, url: str) -> Optional[ProductInfo]:
        """Fetch product info by scraping the page."""
        # Try mobile version first (less aggressive blocking)
        import aiohttp
        
        # Try desktop first
        headers = self._get_browser_headers()
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers, ssl=False, allow_redirects=True) as response:
                    if response.status == 200:
                        html = await response.text()
                        result = self._parse_html(html, url)
                        if result:
                            return result
                    logger.debug(f"Desktop Flipkart status: {response.status}")
        except Exception as e:
            logger.debug(f"Desktop Flipkart error: {e}")
        
        # Fallback to mobile
        mobile_headers = self._get_mobile_headers()
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=mobile_headers, ssl=False, allow_redirects=True) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_html(html, url)
                    logger.warning(f"Mobile Flipkart status: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Mobile Flipkart error: {e}")
            return None
    
    def _parse_api_response(self, data: dict, pid: str, url: str) -> Optional[ProductInfo]:
        """Parse Flipkart API response."""
        info = ProductInfo(
            platform=self.PLATFORM_NAME,
            product_id=pid,
            url=url,
        )
        
        try:
            # Navigate the nested response structure
            page_context = data.get('RESPONSE', {}).get('pageContext', {})
            slots = data.get('RESPONSE', {}).get('viewOrder', [])
            
            # Title
            info.title = page_context.get('titles', {}).get('title')
            
            # Brand
            info.brand = page_context.get('brand')
            
            # Look for price data in slots
            for slot in slots:
                slot_data = data.get('RESPONSE', {}).get('slots', {}).get(slot, {})
                if 'widget' in slot_data:
                    widget_data = slot_data.get('widget', {}).get('data', {})
                    
                    # Price info
                    pricing = widget_data.get('pricing', {})
                    if pricing:
                        info.current_price = pricing.get('finalPrice', {}).get('value')
                        info.original_price = pricing.get('mrp', {}).get('value')
                        info.discount_percent = pricing.get('discount')
            
            return info if info.is_valid() else None
            
        except Exception as e:
            logger.error(f"Error parsing Flipkart API response: {e}")
            return None
    
    def _parse_html(self, html: str, url: str) -> Optional[ProductInfo]:
        """Parse Flipkart HTML for product info."""
        info = ProductInfo(
            platform=self.PLATFORM_NAME,
            url=url,
        )
        
        try:
            # Look for JSON-LD schema data
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
                        
                        rating = schema_data.get('aggregateRating', {})
                        info.rating = float(rating.get('ratingValue', 0)) or None
                        info.rating_count = int(rating.get('ratingCount', 0)) or None
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Extract from page state JSON
            page_data_match = re.search(
                r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});?\s*</script>',
                html, re.DOTALL
            )
            if page_data_match and not info.title:
                try:
                    page_data = json.loads(page_data_match.group(1))
                    # Navigate complex structure to find product info
                    page_context = page_data.get('pageDataV4', {}).get('page', {}).get('pageContext', {})
                    if not info.title:
                        info.title = page_context.get('titles', {}).get('title')
                    if not info.brand:
                        info.brand = page_context.get('brand')
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # Fallback: Regex patterns
            if not info.title:
                title_match = re.search(r'<span[^>]*class="[^"]*VU-ZEz[^"]*"[^>]*>([^<]+)</span>', html)
                if not title_match:
                    title_match = re.search(r'<h1[^>]*class="[^"]*yhB1nd[^"]*"[^>]*>([^<]+)</h1>', html)
                if title_match:
                    info.title = title_match.group(1).strip()
            
            # Price from HTML
            if not info.current_price:
                price_match = re.search(r'<div[^>]*class="[^"]*Nx9bqj[^"]*CxhGGd[^"]*"[^>]*>₹?([\d,]+)</div>', html)
                if not price_match:
                    price_match = re.search(r'class="[^"]*_30jeq3[^"]*_16Jk6d[^"]*"[^>]*>₹?([\d,]+)', html)
                if price_match:
                    info.current_price = self._clean_price(price_match.group(1))
            
            # MRP from HTML
            if not info.original_price:
                mrp_match = re.search(r'<div[^>]*class="[^"]*yRaY8j[^"]*A6\+E6v[^"]*"[^>]*>₹?([\d,]+)</div>', html)
                if not mrp_match:
                    mrp_match = re.search(r'class="[^"]*_3I9_wc[^"]*"[^>]*>₹?([\d,]+)', html)
                if mrp_match:
                    info.original_price = self._clean_price(mrp_match.group(1))
            
            # Discount
            discount_match = re.search(r'(\d+)%\s*off', html, re.IGNORECASE)
            if discount_match and not info.discount_percent:
                info.discount_percent = int(discount_match.group(1))
            
            # Extract PID from URL if not set
            if not info.product_id:
                info.product_id = self.extract_product_id(url)
            
            # Calculate discount if prices available
            if not info.discount_percent:
                info.discount_percent = info.calculate_discount()
            
            return info if info.is_valid() else None
            
        except Exception as e:
            logger.error(f"Error parsing Flipkart HTML: {e}")
            return None
