"""
Product Handler - Unified orchestrator for product information extraction.
Coordinates URL handling and platform-specific handlers.
"""

import logging
import asyncio
from typing import Optional, List, Type

from .url_handler import URLHandler
from .platforms import (
    BasePlatform,
    ProductInfo,
    AmazonHandler,
    FlipkartHandler,
    MyntraHandler,
)

logger = logging.getLogger(__name__)


class ProductHandler:
    """
    Unified orchestrator for product information extraction.
    
    Workflow:
    1. Extract URL from message text
    2. Expand shortened URLs
    3. Identify platform (Amazon/Flipkart/Myntra)
    4. Fetch product details using appropriate handler
    5. Return normalized product metadata
    """
    
    def __init__(self, timeout: int = 30, prefer_indian: bool = True, enable_generic_scraper: bool = True):
        """
        Initialize the product handler.
        
        Args:
            timeout: HTTP request timeout in seconds
            prefer_indian: Convert e-commerce URLs to Indian domains
            enable_generic_scraper: Enable generic HTML scraping for unknown sites
        """
        self.timeout = timeout
        self.enable_generic_scraper = enable_generic_scraper
        self.url_handler = URLHandler(timeout=timeout, prefer_indian=prefer_indian)
        
        # Initialize platform handlers
        self.handlers: List[BasePlatform] = [
            AmazonHandler(timeout=timeout),
            FlipkartHandler(timeout=timeout),
            MyntraHandler(timeout=timeout),
        ]
        
        logger.info(f"ProductHandler initialized with {len(self.handlers)} platform handlers")
        logger.info(f"Generic scraper: {'Enabled' if self.enable_generic_scraper else 'Disabled'}")
    
    def _identify_platform(self, url: str) -> Optional[BasePlatform]:
        """
        Identify which platform handler should process the URL.
        
        Args:
            url: The URL to check
            
        Returns:
            Platform handler or None if no match
        """
        for handler in self.handlers:
            if handler.matches_url(url):
                return handler
        return None
    
    async def extract_product_info(self, text: str) -> Optional[ProductInfo]:
        """
        Extract product information from message text.
        
        This is the main entry point that orchestrates:
        1. URL extraction
        2. URL expansion
        3. Platform identification  
        4. Product info retrieval
        
        Args:
            text: Message text containing a URL
            
        Returns:
            ProductInfo object or None if extraction failed
        """
        if not text:
            return None
        
        try:
            # Step 1: Extract first URL
            original_url = self.url_handler.extract_first_url(text)
            if not original_url:
                logger.debug("No URL found in text")
                return None
            
            logger.info(f"Found URL: {original_url}")
            
            # Step 2: Expand shortened URL
            expanded_url = await self.url_handler.expand_url(original_url)
            logger.info(f"Expanded URL: {expanded_url}")
            
            # Step 3: Identify platform
            handler = self._identify_platform(expanded_url)
            if handler:
                logger.info(f"Platform identified: {handler.PLATFORM_NAME}")
                
                # Step 4: Get product info
                product_info = await handler.get_product_info(expanded_url)
                
                if product_info:
                    # Ensure URL is set to the expanded URL
                    product_info.url = expanded_url
                    logger.info(f"Successfully extracted product info: {product_info.title}")
                    return product_info
                else:
                    logger.warning(f"Platform handler failed for: {expanded_url}")
            else:
                logger.debug(f"No platform handler found for URL: {expanded_url}")
            
            # Step 5: Fallback to generic scraper for unknown sites or failed extractions
            if self.enable_generic_scraper:
                logger.info(f"Trying generic scraper for: {expanded_url}")
                product_info = await self._generic_scrape(expanded_url)
                if product_info:
                    product_info.url = expanded_url
                    logger.info(f"Generic scraper found: {product_info.title}")
                    return product_info
            
            return None
            
        except asyncio.TimeoutError:
            logger.error("Timeout extracting product info")
            return None
        except Exception as e:
            logger.error(f"Error extracting product info: {e}")
            return None
    
    async def extract_all_product_info(self, text: str) -> List[ProductInfo]:
        """
        Extract product information for all URLs in message text.
        
        Args:
            text: Message text containing URLs
            
        Returns:
            List of ProductInfo objects
        """
        if not text:
            return []
        
        try:
            # Extract all URLs
            urls = self.url_handler.extract_urls(text)
            if not urls:
                return []
            
            products = []
            for url in urls:
                # Expand URL
                expanded_url = await self.url_handler.expand_url(url)
                
                # Identify platform
                handler = self._identify_platform(expanded_url)
                if not handler:
                    continue
                
                # Get product info
                product_info = await handler.get_product_info(expanded_url)
                if product_info:
                    product_info.url = expanded_url
                    products.append(product_info)
            
            return products
            
        except Exception as e:
            logger.error(f"Error extracting all product info: {e}")
            return []
    
    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platform names."""
        return [h.PLATFORM_NAME for h in self.handlers]
    
    def is_supported_url(self, url: str) -> bool:
        """Check if a URL is from a supported platform."""
        return self._identify_platform(url) is not None
    
    async def _generic_scrape(self, url: str) -> Optional[ProductInfo]:
        """
        Generic HTML scraper for unknown e-commerce sites.
        Extracts basic product info using common HTML patterns.
        
        Args:
            url: URL to scrape
            
        Returns:
            ProductInfo with basic details or None
        """
        try:
            import aiohttp
            import re
            from urllib.parse import urlparse
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
            }
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, ssl=False) as response:
                    if response.status != 200:
                        return None
                    
                    html = await response.text()
            
            # Parse domain for platform name
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            platform_name = domain.split('.')[0].title()
            
            product_info = ProductInfo(
                platform=platform_name,
                url=url
            )
            
            # Extract title from various sources
            title_patterns = [
                r'<title[^>]*>([^<]+)</title>',
                r'<h1[^>]*>([^<]+)</h1>',
                r'<meta\s+property="og:title"\s+content="([^"]+)"',
                r'<meta\s+name="title"\s+content="([^"]+)"',
                r'"name"\s*:\s*"([^"]{10,100})"',  # JSON-LD or data
                r'"title"\s*:\s*"([^"]{10,100})"',
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if match:
                    title = match.group(1).strip()
                    # Clean common suffixes
                    title = re.sub(r'\s*[|\-]\s*[^|\-]*(?:shop|store|buy|online|india).*$', '', title, flags=re.IGNORECASE)
                    if len(title) > 10:  # Reasonable title length
                        product_info.title = title[:100]  # Limit length
                        break
            
            # Extract price from various sources  
            price_patterns = [
                r'[₹]\s*([\d,]+(?:\.\d{2})?)',  # ₹1,234.56
                r'(?:price|cost|amount)[^\d]*[₹]?\s*([\d,]+(?:\.\d{2})?)',  # price: 1234
                r'"price"\s*:\s*"?([\d,]+(?:\.\d{2})?)"?',  # JSON price
                r'"amount"\s*:\s*"?([\d,]+(?:\.\d{2})?)"?',  # JSON amount
                r'<span[^>]*class="[^"]*price[^"]*"[^>]*>.*?[₹]?\s*([\d,]+(?:\.\d{2})?)',  # price class
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    try:
                        price = float(match.replace(',', ''))
                        if 10 <= price <= 1000000:  # Reasonable price range
                            product_info.current_price = price
                            break
                    except ValueError:
                        continue
                if product_info.current_price:
                    break
            
            # Extract brand if available
            brand_patterns = [
                r'<meta\s+property="product:brand"\s+content="([^"]+)"',
                r'"brand"\s*:\s*"([^"]{2,30})"',
                r'<span[^>]*class="[^"]*brand[^"]*"[^>]*>([^<]+)</span>',
            ]
            
            for pattern in brand_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    brand = match.group(1).strip()
                    if 2 <= len(brand) <= 30:  # Reasonable brand length
                        product_info.brand = brand
                        break
            
            # Return info if we found at least title or price
            if product_info.title or product_info.current_price:
                logger.debug(f"Generic scraper extracted: {product_info.title} @ ₹{product_info.current_price}")
                return product_info
            
            return None
            
        except Exception as e:
            logger.debug(f"Generic scraper failed for {url}: {e}")
            return None
