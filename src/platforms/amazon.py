"""
Amazon product information handler.
Extracts ASIN and fetches product details.
"""

import re
import json
import logging
import random
from typing import Optional
from urllib.parse import urlparse, parse_qs

from .base import BasePlatform, ProductInfo

logger = logging.getLogger(__name__)


class AmazonHandler(BasePlatform):
    """Handler for Amazon product URLs."""
    
    PLATFORM_NAME = "Amazon"
    
    # Amazon domain patterns
    AMAZON_DOMAINS = [
        'amazon.in', 'amazon.com', 'amazon.co.uk', 'amazon.de',
        'amazon.fr', 'amazon.es', 'amazon.it', 'amazon.ca',
        'amazon.com.au', 'amazon.co.jp', 'amzn.in', 'amzn.to', 'a.co'
    ]
    
    # ASIN patterns (10-character alphanumeric)
    ASIN_PATTERNS = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/gp/aw/d/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'[?&]asin=([A-Z0-9]{10})',
        r'/d/([A-Z0-9]{10})',
    ]
    
    # Browser-like user agents
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    
    def matches_url(self, url: str) -> bool:
        """Check if URL is an Amazon URL."""
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            # Use exact domain matching to avoid false positives
            # (e.g., 'a.co' is substring of 'myntra.com')
            for amazon_domain in self.AMAZON_DOMAINS:
                if domain == amazon_domain or domain.endswith('.' + amazon_domain):
                    return True
            return False
        except Exception:
            return False
    
    def extract_product_id(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL."""
        for pattern in self.ASIN_PATTERNS:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None
    
    async def get_product_info(self, url: str) -> Optional[ProductInfo]:
        """Get product information from Amazon."""
        asin = self.extract_product_id(url)
        if not asin:
            logger.warning(f"Could not extract ASIN from: {url}")
            return None
        
        logger.info(f"Fetching Amazon product: {asin}")
        
        # Try mobile page first (cleaner HTML)
        product_info = await self._fetch_mobile_page(asin, url)
        
        if not product_info or not product_info.is_valid():
            # Fallback to desktop page
            product_info = await self._fetch_desktop_page(asin, url)
        
        return product_info
    
    def _get_browser_headers(self, domain: str, is_mobile: bool = False) -> dict:
        """Generate browser-like headers to avoid CAPTCHA."""
        if is_mobile:
            user_agent = 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
        else:
            user_agent = random.choice(self.USER_AGENTS)
        
        return {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?1' if is_mobile else '?0',
            'Sec-Ch-Ua-Platform': '"Android"' if is_mobile else '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Referer': f'https://www.{domain}/',
        }
    
    async def _fetch_mobile_page(self, asin: str, original_url: str) -> Optional[ProductInfo]:
        """Fetch product info from mobile page."""
        # Determine Amazon domain from URL
        domain = self._get_domain(original_url) or 'amazon.in'
        mobile_url = f"https://www.{domain}/dp/{asin}"
        
        headers = self._get_browser_headers(domain, is_mobile=True)
        
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(mobile_url, headers=headers, ssl=False) as response:
                    if response.status != 200:
                        logger.debug(f"Mobile page status: {response.status}")
                        return None
                    html = await response.text()
                    return self._parse_html(html, asin, original_url)
        except Exception as e:
            logger.error(f"Error fetching Amazon mobile page: {e}")
            return None
    
    async def _fetch_desktop_page(self, asin: str, original_url: str) -> Optional[ProductInfo]:
        """Fetch product info from desktop page."""
        domain = self._get_domain(original_url) or 'amazon.in'
        desktop_url = f"https://www.{domain}/dp/{asin}"
        
        headers = self._get_browser_headers(domain, is_mobile=False)
        
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(desktop_url, headers=headers, ssl=False) as response:
                    if response.status != 200:
                        logger.debug(f"Desktop page status: {response.status}")
                        return None
                    html = await response.text()
                    return self._parse_html(html, asin, original_url)
        except Exception as e:
            logger.error(f"Error fetching Amazon desktop page: {e}")
            return None
    
    def _get_domain(self, url: str) -> Optional[str]:
        """Extract Amazon domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            for d in self.AMAZON_DOMAINS:
                if d in domain:
                    if 'amzn' in d or d == 'a.co':
                        return 'amazon.in'  # Default for short URLs
                    return d
            return None
        except Exception:
            return None
    
    def _parse_html(self, html: str, asin: str, url: str) -> Optional[ProductInfo]:
        """Parse Amazon HTML for product info."""
        info = ProductInfo(
            platform=self.PLATFORM_NAME,
            product_id=asin,
            url=url,
        )
        
        # Debug: Save HTML sample for inspection when debugging
        logger.debug(f"HTML length: {len(html)} chars")
        
        # Debug: Check if we got a CAPTCHA or error page
        # Note: "robot" appears in Amazon's internal JSON as "isrobot":false, so don't use it as indicator
        html_lower = html.lower()
        has_captcha = 'captcha' in html_lower and 'sorry' in html_lower
        has_api_services = 'api-services-support@amazon.com' in html_lower
        
        if has_captcha or has_api_services:
            logger.warning("Amazon returned CAPTCHA page - cannot parse")
            return None
        
        try:
            # Try JSON-LD structured data first (most reliable)
            json_ld_match = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>([^<]+)</script>', html, re.IGNORECASE | re.DOTALL)
            if json_ld_match:
                try:
                    import json
                    ld_data = json.loads(json_ld_match.group(1))
                    if isinstance(ld_data, dict):
                        if ld_data.get('name'):
                            info.title = ld_data['name']
                        if ld_data.get('brand', {}).get('name'):
                            info.brand = ld_data['brand']['name']
                        if ld_data.get('offers', {}).get('price'):
                            info.current_price = float(ld_data['offers']['price'])
                        logger.debug(f"Extracted from JSON-LD: title={info.title}")
                except Exception as e:
                    logger.debug(f"JSON-LD parsing failed: {e}")
            
            # Title - try multiple patterns if JSON-LD didn't work
            if not info.title:
                title_patterns = [
                    r'<span[^>]*id="productTitle"[^>]*>\s*([^<]+?)\s*</span>',
                    r'<span[^>]*id="title"[^>]*>\s*([^<]+?)\s*</span>',
                    r'"title"\s*:\s*"([^"]+)"',
                    r'<h1[^>]*class="[^"]*a-size-large[^"]*"[^>]*>\s*([^<]+?)\s*</h1>',
                    r'<title>([^<]+?)(?:\s*:\s*Amazon|\s*-\s*Amazon|</title>)',
                    r'name="title"\s+content="([^"]+)"',
                    r'property="og:title"\s+content="([^"]+)"',
                ]
                for i, pattern in enumerate(title_patterns):
                    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                    if match:
                        info.title = self._decode_html_entities(match.group(1).strip())
                        logger.debug(f"Title found with pattern {i}: {info.title[:50]}...")
                        break
                else:
                    logger.warning("No title pattern matched")
            
            # Brand
            brand_patterns = [
                r'"brand"\s*:\s*"([^"]+)"',
                r'<a[^>]*id="bylineInfo"[^>]*>[^<]*by\s+([^<]+)</a>',
                r'Visit the ([^<]+) Store',
                r'Brand:\s*</td>\s*<td[^>]*>([^<]+)</td>',
            ]
            for pattern in brand_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    info.brand = match.group(1).strip()
                    break
            
            # Current price
            price_patterns = [
                r'"priceAmount"\s*:\s*([\d.]+)',
                r'class="a-price-whole">([^<]+)</span>',
                r'id="priceblock_dealprice"[^>]*>.*?(\d[\d,]*\.?\d*)',
                r'id="priceblock_ourprice"[^>]*>.*?(\d[\d,]*\.?\d*)',
                r'class="a-price[^"]*"[^>]*>.*?<span[^>]*>.*?(\d[\d,]*\.?\d*)',
            ]
            for pattern in price_patterns:
                match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if match:
                    price = self._clean_price(match.group(1))
                    if price:
                        info.current_price = price
                        break
            
            # Original/MRP price
            mrp_patterns = [
                r'"listPrice"\s*:\s*"?(\d[\d,.]*)"?',
                r'class="a-text-strike">.*?(\d[\d,]*\.?\d*)',
                r'priceBlockStrikePriceString.*?(\d[\d,]*\.?\d*)',
                r'<span[^>]*class="[^"]*a-price[^"]*a-text-price[^"]*"[^>]*>.*?(\d[\d,]*\.?\d*)',
            ]
            for pattern in mrp_patterns:
                match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if match:
                    mrp = self._clean_price(match.group(1))
                    if mrp:
                        info.original_price = mrp
                        break
            
            # Rating
            rating_match = re.search(r'(\d+\.?\d*)\s*out of\s*5', html, re.IGNORECASE)
            if rating_match:
                try:
                    info.rating = float(rating_match.group(1))
                except ValueError:
                    pass
            
            # Rating count
            rating_count_match = re.search(r'([\d,]+)\s*(?:ratings|reviews)', html, re.IGNORECASE)
            if rating_count_match:
                try:
                    info.rating_count = int(rating_count_match.group(1).replace(',', ''))
                except ValueError:
                    pass
            
            # Category from breadcrumbs
            category_match = re.search(r'"category"\s*:\s*"([^"]+)"', html)
            if category_match:
                info.category = category_match.group(1)
            
            # Image
            image_match = re.search(r'"large"\s*:\s*"([^"]+)"', html)
            if not image_match:
                image_match = re.search(r'"hiRes"\s*:\s*"([^"]+)"', html)
            if image_match:
                info.image_url = image_match.group(1)
            
            # In Stock detection - be conservative, prefer True/None over False
            # Only mark as out-of-stock if we're very confident
            info.in_stock = None  # Default to unknown
            html_lower = html.lower()
            
            # Method 1: JSON availability (most reliable)
            avail_match = re.search(r'"availability"\s*:\s*"(https?://schema.org/[^"]+)"', html, re.IGNORECASE)
            if avail_match:
                avail = avail_match.group(1).lower()
                if 'instock' in avail:
                    info.in_stock = True
                    logger.debug(f"Stock from schema: InStock -> True")
                elif 'outofstock' in avail or 'discontinued' in avail:
                    info.in_stock = False
                    logger.debug(f"Stock from schema: OutOfStock -> False")
            
            # Method 2: Check Add to Cart button (very reliable indicator of in-stock)
            if info.in_stock is None:
                if re.search(r'id="add-to-cart-button"', html, re.IGNORECASE):
                    info.in_stock = True
                    logger.debug("Stock from add-to-cart button: True")
                elif re.search(r'id="buy-now-button"', html, re.IGNORECASE):
                    info.in_stock = True
                    logger.debug("Stock from buy-now button: True")
            
            # Method 3: Check availability div text
            if info.in_stock is None:
                avail_div_match = re.search(r'id="availability"[^>]*>([^<]*(?:<[^>]*>[^<]*)*)</span', html, re.IGNORECASE | re.DOTALL)
                if avail_div_match:
                    avail_text = avail_div_match.group(1).lower()
                    logger.debug(f"Availability div text: {avail_text[:100]}")
                    
                    # In stock patterns (check these first)
                    in_stock_patterns = ['in stock', 'left in stock', 'available', 'ships from']
                    for pattern in in_stock_patterns:
                        if pattern in avail_text:
                            info.in_stock = True
                            logger.debug(f"Stock from availability div ('{pattern}'): True")
                            break
                    
                    # Out of stock patterns (only if not already marked in stock)
                    if info.in_stock is None:
                        out_stock_patterns = ['currently unavailable', 'out of stock', 'not available']
                        for pattern in out_stock_patterns:
                            if pattern in avail_text:
                                info.in_stock = False
                                logger.debug(f"Stock from availability div ('{pattern}'): False")
                                break
            
            # Method 4: Check for explicit "Currently unavailable" text on page
            if info.in_stock is None:
                if 'currently unavailable' in html_lower and 'id="availability"' in html_lower:
                    # Only mark out of stock if both conditions are met
                    info.in_stock = False
                    logger.debug("Stock from 'currently unavailable' in availability section: False")
            
            # If we found a price and title but couldn't determine stock, assume available
            if info.in_stock is None and info.current_price and info.title:
                logger.debug("Stock unknown but has price/title, leaving as None (unknown)")
                # Don't set True automatically, leave as None to allow forwarding
            
            # Validate prices - original price must be > current price
            if info.original_price and info.current_price:
                if info.original_price <= info.current_price:
                    # Invalid MRP, reset it
                    logger.debug(f"Invalid MRP ({info.original_price}) <= current ({info.current_price}), resetting")
                    info.original_price = None
            
            # Calculate discount
            info.discount_percent = info.calculate_discount()
            
            if info.is_valid():
                logger.info(f"Successfully parsed Amazon product: {info.title[:50] if info.title else 'No title'}...")
                return info
            else:
                logger.warning(f"Parsed but invalid - title: {info.title}, price: {info.current_price}")
                return None
            
        except Exception as e:
            logger.error(f"Error parsing Amazon HTML: {e}")
            return None
    
    def _decode_html_entities(self, text: str) -> str:
        """Decode HTML entities in text."""
        import html
        return html.unescape(text)
