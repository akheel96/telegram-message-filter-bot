"""
Filter module for Telegram Loot Filter Bot.
Handles message filtering logic and duplicate detection.
Supports multiple keywords for filtering.
"""

import logging
from collections import OrderedDict
from typing import Optional, Set, List
from telethon.tl.types import Message

logger = logging.getLogger(__name__)


class MessageFilter:
    """Handles message filtering based on multiple keywords."""
    
    def __init__(self, keywords: Set[str] = None):
        """
        Initialize the message filter.
        
        Args:
            keywords: Set of keywords to filter messages by (case-insensitive)
        """
        self.keywords = {kw.lower() for kw in (keywords or {"loot"})}
        logger.info(f"MessageFilter initialized with keywords: {self.keywords}")
    
    def add_keyword(self, keyword: str) -> None:
        """Add a keyword to the filter."""
        self.keywords.add(keyword.lower())
        logger.info(f"Added keyword: {keyword}")
    
    def remove_keyword(self, keyword: str) -> None:
        """Remove a keyword from the filter."""
        self.keywords.discard(keyword.lower())
        logger.info(f"Removed keyword: {keyword}")
    
    def set_keywords(self, keywords: Set[str]) -> None:
        """Replace all keywords."""
        self.keywords = {kw.lower() for kw in keywords}
        logger.info(f"Updated keywords: {self.keywords}")
    
    def contains_keyword(self, message: Message) -> bool:
        """
        Check if a message contains any of the filter keywords.
        
        Args:
            message: Telethon Message object
            
        Returns:
            True if the message contains any keyword, False otherwise
        """
        text = self._extract_text(message)
        
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check if any keyword is present
        for keyword in self.keywords:
            if keyword in text_lower:
                return True
        
        return False
    
    def get_matching_keywords(self, message: Message) -> List[str]:
        """
        Get all keywords that match in a message.
        
        Args:
            message: Telethon Message object
            
        Returns:
            List of matching keywords
        """
        text = self._extract_text(message)
        
        if not text:
            return []
        
        text_lower = text.lower()
        matching = []
        
        for keyword in self.keywords:
            if keyword in text_lower:
                matching.append(keyword)
        
        return matching
    
    def _extract_text(self, message: Message) -> Optional[str]:
        """
        Extract text content from a message.
        
        Args:
            message: Telethon Message object
            
        Returns:
            The text content of the message, or None if no text
        """
        # Regular text message
        if message.text:
            return message.text
        
        # Message with media (caption)
        if message.message:
            return message.message
        
        return None


class DuplicateDetector:
    """Prevents forwarding duplicate messages using an LRU cache."""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize the duplicate detector.
        
        Args:
            max_size: Maximum number of message IDs to cache
        """
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        logger.info(f"DuplicateDetector initialized with cache size: {max_size}")
    
    def is_duplicate(self, message_id: int, channel_id: int) -> bool:
        """
        Check if a message has already been processed.
        
        Args:
            message_id: The unique message ID
            channel_id: The channel ID where the message originated
            
        Returns:
            True if the message is a duplicate, False otherwise
        """
        cache_key = f"{channel_id}_{message_id}"
        
        if cache_key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(cache_key)
            return True
        
        return False
    
    def mark_processed(self, message_id: int, channel_id: int) -> None:
        """
        Mark a message as processed.
        
        Args:
            message_id: The unique message ID
            channel_id: The channel ID where the message originated
        """
        cache_key = f"{channel_id}_{message_id}"
        
        # Add to cache
        self._cache[cache_key] = True
        
        # Remove oldest entries if cache is full (LRU eviction)
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        logger.info("Duplicate cache cleared")
    
    @property
    def size(self) -> int:
        """Get the current cache size."""
        return len(self._cache)
