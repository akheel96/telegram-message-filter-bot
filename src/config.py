"""
Configuration module for Telegram Loot Filter Bot.
Loads and validates environment variables.
Supports multiple keywords and multiple source channels.
"""

import os
import sys
import logging
from typing import List, Set

logger = logging.getLogger(__name__)


class Config:
    """Configuration class that loads settings from environment variables."""
    
    def __init__(self):
        self.api_id: int = 0
        self.api_hash: str = ""
        self.source_channel_ids: List[int] = []
        self.destination_channel_id: int = 0
        self.filter_keywords: Set[str] = {"loot", "member"}
        self.session_name: str = "loot_filter_bot"
        self.cache_size: int = 1000  # Max messages to cache for duplicate prevention
        self.reconnect_delay: int = 5  # Seconds to wait before reconnecting
        self.max_retries: int = 10  # Max reconnection attempts
        self.http_timeout: int = 30  # HTTP request timeout in seconds
        self.fast_mode: bool = True  # Fast processing mode with reduced timeouts
        self.skip_product_extraction: bool = False  # Skip product extraction for max speed
        self.enable_product_info: bool = True  # Enable product info extraction
        self.discount_highlight_threshold: int = 50  # Highlight discounts above this %
        self.prefer_indian_urls: bool = True  # Convert Amazon/etc URLs to Indian domains
        self.skip_out_of_stock: bool = False  # Skip forwarding out-of-stock products
        self.skip_listing_pages: bool = False  # Skip forwarding listing/search pages
        self.enable_generic_scraper: bool = True  # Enable generic scraping for unknown sites
        self.skip_sites_text: Set[str] = {"ajio", "ajiio"}  # Skip messages containing these sites/text
        
    def load(self) -> bool:
        """Load configuration from environment variables."""
        try:
            # Required variables
            api_id = os.getenv("API_ID")
            api_hash = os.getenv("API_HASH")
            source_channels = os.getenv("SOURCE_CHANNEL_IDS") or os.getenv("SOURCE_CHANNEL_ID")
            dest_channel = os.getenv("DESTINATION_CHANNEL_ID")
            
            # Validate required variables
            missing = []
            if not api_id:
                missing.append("API_ID")
            if not api_hash:
                missing.append("API_HASH")
            if not source_channels:
                missing.append("SOURCE_CHANNEL_IDS (or SOURCE_CHANNEL_ID)")
            if not dest_channel:
                missing.append("DESTINATION_CHANNEL_ID")
            
            if missing:
                logger.error(f"Missing required environment variables: {', '.join(missing)}")
                return False
            
            # Parse and set values
            self.api_id = int(api_id)
            self.api_hash = api_hash.strip()
            self.destination_channel_id = int(dest_channel)
            
            # Parse multiple source channels (comma-separated)
            self.source_channel_ids = self._parse_channel_ids(source_channels)
            if not self.source_channel_ids:
                logger.error("No valid source channel IDs provided")
                return False
            
            # Parse multiple keywords (comma-separated)
            keywords_str = os.getenv("FILTER_KEYWORDS") or os.getenv("FILTER_KEYWORD", "loot")
            self.filter_keywords = self._parse_keywords(keywords_str)
            
            # Optional variables
            self.session_name = os.getenv("SESSION_NAME", "loot_filter_bot")
            self.cache_size = int(os.getenv("CACHE_SIZE", "1000"))
            self.reconnect_delay = int(os.getenv("RECONNECT_DELAY", "5"))
            self.max_retries = int(os.getenv("MAX_RETRIES", "10"))
            self.http_timeout = int(os.getenv("HTTP_TIMEOUT", "15"))  # Reduced from 30
            self.fast_mode = os.getenv("FAST_MODE", "true").lower() == "true"
            self.skip_product_extraction = os.getenv("SKIP_PRODUCT_EXTRACTION", "false").lower() == "true"
            self.enable_product_info = os.getenv("ENABLE_PRODUCT_INFO", "true").lower() == "true"
            self.discount_highlight_threshold = int(os.getenv("DISCOUNT_HIGHLIGHT_THRESHOLD", "50"))
            self.prefer_indian_urls = os.getenv("PREFER_INDIAN_URLS", "true").lower() == "true"
            self.skip_out_of_stock = os.getenv("SKIP_OUT_OF_STOCK", "true").lower() == "true"
            self.skip_listing_pages = os.getenv("SKIP_LISTING_PAGES", "false").lower() == "true"
            self.enable_generic_scraper = os.getenv("ENABLE_GENERIC_SCRAPER", "true").lower() == "true"
            
            # Parse skip sites/text (comma-separated, case-insensitive)
            skip_text_str = os.getenv("SKIP_SITES_TEXT", "ajio,ajiio")
            self.skip_sites_text = self._parse_skip_patterns(skip_text_str)
            
            logger.info("Configuration loaded successfully")
            logger.info(f"Source Channels: {self.source_channel_ids}")
            logger.info(f"Destination Channel: {self.destination_channel_id}")
            logger.info(f"Filter Keywords: {self.filter_keywords}")
            logger.info(f"Product Info Extraction: {'Enabled' if self.enable_product_info else 'Disabled'}")
            logger.info(f"Fast Mode: {'Enabled' if self.fast_mode else 'Disabled'}")
            logger.info(f"Skip Product Extraction: {'Yes' if self.skip_product_extraction else 'No'}")
            logger.info(f"HTTP Timeout: {self.http_timeout}s")
            logger.info(f"Prefer Indian URLs: {'Yes' if self.prefer_indian_urls else 'No'}")
            logger.info(f"Skip Out-of-Stock: {'Yes' if self.skip_out_of_stock else 'No'}")
            logger.info(f"Skip Listing Pages: {'Yes' if self.skip_listing_pages else 'No'}")
            logger.info(f"Generic Scraper: {'Enabled' if self.enable_generic_scraper else 'Disabled'}")
            logger.info(f"Skip Sites/Text: {self.skip_sites_text if self.skip_sites_text else 'None'}")
            
            return True
            
        except ValueError as e:
            logger.error(f"Invalid configuration value: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def _parse_channel_ids(self, channels_str: str) -> List[int]:
        """Parse comma-separated channel IDs."""
        channel_ids = []
        for ch in channels_str.split(","):
            ch = ch.strip()
            if ch:
                try:
                    channel_ids.append(int(ch))
                except ValueError:
                    logger.warning(f"Invalid channel ID: {ch}")
        return channel_ids
    
    def _parse_keywords(self, keywords_str: str) -> Set[str]:
        """Parse comma-separated keywords (case-insensitive)."""
        keywords = set()
        for kw in keywords_str.split(","):
            kw = kw.strip().lower()
            if kw:
                keywords.add(kw)
        return keywords if keywords else {"loot"}
    
    def _parse_skip_patterns(self, patterns_str: str) -> Set[str]:
        """Parse comma-separated skip patterns (case-insensitive)."""
        patterns = set()
        for pattern in patterns_str.split(","):
            pattern = pattern.strip().lower()
            if pattern:
                patterns.add(pattern)
        return patterns
    
    def validate_channels(self) -> bool:
        """Validate that source and destination channels are different."""
        if self.destination_channel_id in self.source_channel_ids:
            logger.warning("Destination channel is also a source channel!")
            return False
        return True
    
    # ============================================================
    # Runtime Configuration Methods (for Admin UI)
    # ============================================================
    
    def add_source_channel(self, channel_id: int) -> bool:
        """Add a source channel at runtime."""
        if channel_id == self.destination_channel_id:
            logger.warning(f"Cannot add destination channel as source: {channel_id}")
            return False
        if channel_id in self.source_channel_ids:
            logger.info(f"Channel already in source list: {channel_id}")
            return False
        self.source_channel_ids.append(channel_id)
        logger.info(f"Added source channel: {channel_id}")
        return True
    
    def remove_source_channel(self, channel_id: int) -> bool:
        """Remove a source channel at runtime."""
        if channel_id in self.source_channel_ids:
            self.source_channel_ids.remove(channel_id)
            logger.info(f"Removed source channel: {channel_id}")
            return True
        logger.warning(f"Channel not found in source list: {channel_id}")
        return False
    
    def add_keyword(self, keyword: str) -> bool:
        """Add a filter keyword at runtime."""
        keyword = keyword.strip().lower()
        if not keyword:
            return False
        if keyword in self.filter_keywords:
            logger.info(f"Keyword already exists: {keyword}")
            return False
        self.filter_keywords.add(keyword)
        logger.info(f"Added filter keyword: {keyword}")
        return True
    
    def remove_keyword(self, keyword: str) -> bool:
        """Remove a filter keyword at runtime."""
        keyword = keyword.strip().lower()
        if keyword in self.filter_keywords:
            self.filter_keywords.discard(keyword)
            logger.info(f"Removed filter keyword: {keyword}")
            return True
        logger.warning(f"Keyword not found: {keyword}")
        return False
    
    def get_runtime_config(self) -> dict:
        """Get current runtime configuration."""
        return {
            "source_channel_ids": self.source_channel_ids.copy(),
            "destination_channel_id": self.destination_channel_id,
            "filter_keywords": list(self.filter_keywords),
            "fast_mode": self.fast_mode,
            "skip_product_extraction": self.skip_product_extraction,
            "enable_product_info": self.enable_product_info,
            "skip_out_of_stock": self.skip_out_of_stock,
        }


# Global config instance
config = Config()
