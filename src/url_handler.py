"""
URL Handler module for Telegram Loot Filter Bot.
Handles URL extraction from messages and URL expansion (following redirects).
"""

import re
import logging
import asyncio
from typing import Optional, List
from urllib.parse import urlparse, urlunparse, parse_qs

import aiohttp

logger = logging.getLogger(__name__)

# URL patterns that indicate listing/search pages (not single product)
LISTING_PAGE_PATTERNS = {
    # Amazon
    '/s?', '/s/', '/b/', '/gp/browse/', '/bestsellers/', '/deals/',
    '/s?k=', '/s?rh=',
    # Flipkart
    '/search?', '/search/', '-store/', '/store/',
    # Myntra
    '/shop/', '/men-', '/women-', '/kids-', '-clothing', '-accessories',
    '-footwear', '-bags', '-jewellery', '/brand/',
}

# URL regex pattern - matches most common URL formats
URL_PATTERN = re.compile(
    r'https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,10}\.?|'  # domain
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
    r'(?::\d+)?'  # optional port
    r'(?:/[^\s<>\"\'\)]*)?',  # path - everything until whitespace or certain chars
    re.IGNORECASE
)

# Known URL shorteners
SHORT_URL_DOMAINS = {
    'bit.ly', 'bitly.com', 'tinyurl.com', 't.co', 'goo.gl',
    'amzn.to', 'amzn.in', 'a.co',  # Amazon
    'fkrt.it', 'dl.flipkart.com',  # Flipkart
    'myntr.in',  # Myntra
    'short.url', 'ow.ly', 'is.gd', 'buff.ly', 'rebrand.ly',
    'cutt.ly', 'rb.gy', 'shorturl.at', 'clck.ru', 'ekaro.in',
    'shrinkme.io', 'shorte.st', 'ouo.io', 'linkshrink.net',
    'cuttli.in', 'cutt.us', 'linktr.ee', 'tinycc.com',  # Additional shorteners
    'short.gy', 'v.gd', 'x.co', 'yourls.org', 'qr.net'
}

# Known affiliate/tracking parameters to remove
AFFILIATE_PARAMS = {
    # Universal tracking
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'gclid', 'fbclid', 'msclkid', 'dclid',
    # Amazon
    'tag', 'ref', 'ref_', 'linkCode', 'camp', 'creative', 'creativeASIN',
    'ascsubtag', 'psc', 'qid', 's', 'sr', 'keywords',
    # Flipkart 
    'affid', 'affExtParam1', 'affExtParam2', 'pid', 'lid', 'marketplace',
    # Other platforms
    'spm', 'scm', 'pvid', 'algo_pvid', 'algo_expid', 'btsid',
    'ws_ab_test', 'rdc', 'cot', 'eaf', 'rmd'
}


def is_listing_page(url: str) -> bool:
    """
    Check if URL is a listing/search page rather than a single product page.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to be a listing page
    """
    url_lower = url.lower()
    
    # Check for listing patterns in URL
    for pattern in LISTING_PAGE_PATTERNS:
        if pattern in url_lower:
            return True
    
    # Check for query params that indicate search
    parsed = urlparse(url_lower)
    params = parse_qs(parsed.query)
    
    # Common search/filter params
    search_params = {'q', 'query', 'search', 'k', 'rh', 'category', 'sort'}
    if search_params.intersection(params.keys()):
        return True
    
    return False


class URLHandler:
    """Handles URL extraction and expansion."""
    
    # Domain mappings for Indian site conversion
    INDIAN_DOMAIN_MAP = {
        'amazon.com': 'amazon.in',
        'amazon.co.uk': 'amazon.in',
        'amazon.de': 'amazon.in',
        'amazon.fr': 'amazon.in',
        'amazon.es': 'amazon.in',
        'amazon.it': 'amazon.in',
        'amazon.ca': 'amazon.in',
        'amazon.com.au': 'amazon.in',
        'amazon.co.jp': 'amazon.in',
    }
    
    def __init__(self, timeout: int = 30, max_redirects: int = 10, prefer_indian: bool = True):
        """
        Initialize the URL handler.
        
        Args:
            timeout: HTTP request timeout in seconds
            max_redirects: Maximum number of redirects to follow
            prefer_indian: Convert e-commerce URLs to Indian domains
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.fast_timeout = aiohttp.ClientTimeout(total=8)  # Fast timeout for URL expansion (8s)
        self.max_redirects = max_redirects
        self.prefer_indian = prefer_indian
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
        }
    
    def extract_urls(self, text: str) -> List[str]:
        """
        Extract all URLs from text.
        
        Args:
            text: Text to extract URLs from
            
        Returns:
            List of URLs found in text
        """
        if not text:
            return []
        
        urls = URL_PATTERN.findall(text)
        # Clean up URLs (remove trailing punctuation)
        cleaned_urls = []
        for url in urls:
            url = url.rstrip('.,;:!?)\'\"')
            if url:
                cleaned_urls.append(url)
        
        return cleaned_urls
    
    def extract_first_url(self, text: str) -> Optional[str]:
        """
        Extract the first URL from text.
        
        Args:
            text: Text to extract URL from
            
        Returns:
            First URL found, or None
        """
        urls = self.extract_urls(text)
        return urls[0] if urls else None
    
    def is_shortened_url(self, url: str) -> bool:
        """
        Check if a URL is a known shortened URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is shortened, False otherwise
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove 'www.' prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain in SHORT_URL_DOMAINS
        except Exception:
            return False
    
    def remove_affiliate_params(self, url: str) -> str:
        """
        Remove affiliate and tracking parameters from URL.
        
        Args:
            url: URL to clean
            
        Returns:
            URL with affiliate parameters removed
        """
        if not url:
            return url
        
        try:
            parsed = urlparse(url)
            
            if not parsed.query:
                return url
            
            # Parse query parameters
            from urllib.parse import parse_qs, urlencode
            params = parse_qs(parsed.query, keep_blank_values=True)
            
            # Remove affiliate parameters
            clean_params = {}
            for key, value in params.items():
                # Keep parameter if it's not an affiliate/tracking param
                if key.lower() not in AFFILIATE_PARAMS:
                    clean_params[key] = value
            
            # Rebuild query string
            clean_query = urlencode(clean_params, doseq=True) if clean_params else ''
            
            # Rebuild URL
            clean_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                clean_query,
                parsed.fragment
            ))
            
            if clean_url != url:
                logger.debug(f"Cleaned affiliate params: {url} -> {clean_url}")
            
            return clean_url
            
        except Exception as e:
            logger.warning(f"Error removing affiliate params from {url}: {e}")
            return url

    def convert_to_indian_url(self, url: str) -> str:
        """
        Convert e-commerce URL to Indian domain.
        
        Args:
            url: URL to convert
            
        Returns:
            URL with Indian domain if applicable
        """
        if not self.prefer_indian or not url:
            return url
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove 'www.' for matching
            domain_without_www = domain[4:] if domain.startswith('www.') else domain
            
            # Check if domain should be converted
            if domain_without_www in self.INDIAN_DOMAIN_MAP:
                indian_domain = self.INDIAN_DOMAIN_MAP[domain_without_www]
                # Preserve www. if it was there
                if domain.startswith('www.'):
                    indian_domain = 'www.' + indian_domain
                
                # Replace domain in URL
                new_url = urlunparse((
                    parsed.scheme,
                    indian_domain,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
                logger.debug(f"Converted to Indian URL: {url} -> {new_url}")
                return new_url
            
            return url
        except Exception as e:
            logger.warning(f"Error converting URL to Indian: {e}")
            return url
    
    async def expand_url(self, url: str, fast: bool = True) -> str:
        """
        Expand a shortened URL by following redirects.
        
        Args:
            url: URL to expand
            fast: Use fast timeout (5s) for quicker expansion
            
        Returns:
            Final expanded URL after following all redirects
        """
        if not url:
            return url
        
        # Skip expansion for already-expanded URLs
        if not self.is_shortened_url(url):
            final_url = self.convert_to_indian_url(url)
            final_url = self.remove_affiliate_params(final_url)
            return final_url
        
        final_url = url
        timeout = self.fast_timeout if fast else self.timeout
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Use HEAD request first (faster), fall back to GET
                async with session.head(
                    url, 
                    headers=self.headers,
                    allow_redirects=True,
                    max_redirects=self.max_redirects,
                    ssl=False  # Some sites have SSL issues
                ) as response:
                    final_url = str(response.url)
                    logger.debug(f"Expanded URL: {url} -> {final_url}")
                    
        except aiohttp.ClientResponseError as e:
            # If HEAD fails, try GET with fast timeout
            logger.debug(f"HEAD request failed for {url}, trying GET: {e}")
            final_url = await self._expand_url_get(url, timeout)
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout expanding URL (fast={fast}): {url}")
            # Return original URL on timeout
            return url
            
        except Exception as e:
            logger.warning(f"Error expanding URL {url}: {e}")
        
        # Convert to Indian domain if enabled
        final_url = self.convert_to_indian_url(final_url)
        
        # Remove affiliate parameters
        final_url = self.remove_affiliate_params(final_url)
        
        return final_url
    
    async def _expand_url_get(self, url: str, timeout: aiohttp.ClientTimeout = None) -> str:
        """Expand URL using GET request (fallback)."""
        try:
            async with aiohttp.ClientSession(timeout=timeout or self.timeout) as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    allow_redirects=True,
                    max_redirects=self.max_redirects,
                    ssl=False
                ) as response:
                    return str(response.url)
        except asyncio.TimeoutError:
            logger.warning(f"GET request timed out for {url}")
            return url
        except Exception as e:
            logger.warning(f"GET request also failed for {url}: {e}")
            return url
    
    async def extract_and_expand(self, text: str) -> Optional[str]:
        """
        Extract the first URL from text and expand it if shortened.
        
        Args:
            text: Text to process
            
        Returns:
            Expanded URL or None if no URL found
        """
        url = self.extract_first_url(text)
        if not url:
            return None
        
        # Always try to expand to get final URL (handles affiliate links too)
        expanded = await self.expand_url(url)
        return expanded
    
    async def extract_and_expand_all(self, text: str) -> List[str]:
        """
        Extract all URLs from text and expand them.
        
        Args:
            text: Text to process
            
        Returns:
            List of expanded URLs
        """
        urls = self.extract_urls(text)
        if not urls:
            return []
        
        expanded_urls = []
        for url in urls:
            expanded = await self.expand_url(url)
            expanded_urls.append(expanded)
        
        return expanded_urls
