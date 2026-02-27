"""
Base platform handler for product information extraction.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class ProductInfo:
    """Standardized product information structure."""
    
    title: Optional[str] = None
    brand: Optional[str] = None
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percent: Optional[int] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    category: Optional[str] = None
    platform: Optional[str] = None
    product_id: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    in_stock: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[Dict[str, Any]] = None  # Raw API/HTML response for debugging
    
    def calculate_discount(self) -> Optional[int]:
        """Calculate discount percentage from prices."""
        if self.current_price and self.original_price and self.original_price > 0:
            discount = ((self.original_price - self.current_price) / self.original_price) * 100
            return int(discount)
        return self.discount_percent
    
    def is_valid(self) -> bool:
        """Check if product info has minimum required data."""
        return bool(self.title or self.product_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'title': self.title,
            'brand': self.brand,
            'current_price': self.current_price,
            'original_price': self.original_price,
            'discount_percent': self.discount_percent or self.calculate_discount(),
            'rating': self.rating,
            'rating_count': self.rating_count,
            'category': self.category,
            'platform': self.platform,
            'product_id': self.product_id,
            'url': self.url,
            'image_url': self.image_url,
            'in_stock': self.in_stock,
            'extra': self.extra,
        }


class BasePlatform(ABC):
    """Abstract base class for platform handlers."""
    
    PLATFORM_NAME: str = "Unknown"
    
    def __init__(self, timeout: int = 30):
        """Initialize the platform handler."""
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    @abstractmethod
    def matches_url(self, url: str) -> bool:
        """
        Check if this handler can process the given URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if this handler can process the URL
        """
        pass
    
    @abstractmethod
    def extract_product_id(self, url: str) -> Optional[str]:
        """
        Extract the product ID from URL.
        
        Args:
            url: Product URL
            
        Returns:
            Product ID or None
        """
        pass
    
    @abstractmethod
    async def get_product_info(self, url: str) -> Optional[ProductInfo]:
        """
        Get product information from URL.
        
        Args:
            url: Product URL
            
        Returns:
            ProductInfo object or None if failed
        """
        pass
    
    async def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=self.headers, ssl=False) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    async def _fetch_json(self, url: str, headers: Optional[Dict] = None) -> Optional[Dict]:
        """Fetch JSON content from URL."""
        request_headers = {**self.headers, **(headers or {})}
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=request_headers, ssl=False) as response:
                    if response.status == 200:
                        return await response.json()
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching JSON from {url}: {e}")
            return None
    
    def _clean_price(self, price_str: str) -> Optional[float]:
        """Clean price string and convert to float."""
        if not price_str:
            return None
        try:
            # Remove currency symbols and commas
            cleaned = ''.join(c for c in price_str if c.isdigit() or c == '.')
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
