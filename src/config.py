"""
Configuration module for Telegram Loot Filter Bot.
Loads and validates environment variables.
"""

import os
import logging
from typing import List, Set

logger = logging.getLogger(__name__)


class Config:
    """Loads settings from environment variables."""

    def __init__(self):
        self.api_id: int = 0
        self.api_hash: str = ""
        self.source_channel_ids: List[int] = []
        self.destination_channel_id: int = 0
        self.filter_keywords: Set[str] = {"loot"}
        self.session_name: str = "loot_filter_bot"
        self.cache_size: int = 1000
        self.reconnect_delay: int = 5
        self.max_retries: int = 10
        self.skip_sites_text: Set[str] = set()

    def load(self) -> bool:
        """Load configuration from environment variables."""
        try:
            api_id = os.getenv("API_ID")
            api_hash = os.getenv("API_HASH")
            source_channels = os.getenv("SOURCE_CHANNEL_IDS") or os.getenv("SOURCE_CHANNEL_ID")
            dest_channel = os.getenv("DESTINATION_CHANNEL_ID")

            missing = []
            if not api_id:
                missing.append("API_ID")
            if not api_hash:
                missing.append("API_HASH")
            if not source_channels:
                missing.append("SOURCE_CHANNEL_IDS")
            if not dest_channel:
                missing.append("DESTINATION_CHANNEL_ID")

            if missing:
                logger.error(f"Missing required env vars: {', '.join(missing)}")
                return False

            self.api_id = int(api_id)
            self.api_hash = api_hash.strip()
            self.destination_channel_id = int(dest_channel)
            self.source_channel_ids = self._parse_ids(source_channels)

            if not self.source_channel_ids:
                logger.error("No valid source channel IDs provided")
                return False

            keywords_str = os.getenv("FILTER_KEYWORDS") or os.getenv("FILTER_KEYWORD", "loot")
            self.filter_keywords = self._parse_set(keywords_str) or {"loot"}

            self.session_name = os.getenv("SESSION_NAME", "loot_filter_bot")
            self.cache_size = int(os.getenv("CACHE_SIZE", "1000"))
            self.reconnect_delay = int(os.getenv("RECONNECT_DELAY", "5"))
            self.max_retries = int(os.getenv("MAX_RETRIES", "10"))

            skip_text_str = os.getenv("SKIP_SITES_TEXT", "")
            self.skip_sites_text = self._parse_set(skip_text_str)

            logger.info("Configuration loaded")
            logger.info(f"  Source channels : {self.source_channel_ids}")
            logger.info(f"  Destination     : {self.destination_channel_id}")
            logger.info(f"  Keywords        : {self.filter_keywords}")
            if self.skip_sites_text:
                logger.info(f"  Skip patterns   : {self.skip_sites_text}")
            return True

        except ValueError as e:
            logger.error(f"Invalid config value: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return False

    def _parse_ids(self, s: str) -> List[int]:
        ids = []
        for item in s.split(","):
            item = item.strip()
            if item:
                try:
                    ids.append(int(item))
                except ValueError:
                    logger.warning(f"Invalid channel ID: {item}")
        return ids

    def _parse_set(self, s: str) -> Set[str]:
        result = set()
        for item in s.split(","):
            item = item.strip().lower()
            if item:
                result.add(item)
        return result

    def validate_channels(self) -> bool:
        if self.destination_channel_id in self.source_channel_ids:
            logger.warning("Destination channel is also a source channel!")
            return False
        return True

    # ── Runtime methods used by admin logic ──────────────────────────────────

    def add_source_channel(self, channel_id: int) -> bool:
        if channel_id == self.destination_channel_id:
            return False
        if channel_id in self.source_channel_ids:
            return False
        self.source_channel_ids.append(channel_id)
        return True

    def remove_source_channel(self, channel_id: int) -> bool:
        if channel_id in self.source_channel_ids:
            self.source_channel_ids.remove(channel_id)
            return True
        return False

    def add_keyword(self, keyword: str) -> bool:
        keyword = keyword.strip().lower()
        if not keyword or keyword in self.filter_keywords:
            return False
        self.filter_keywords.add(keyword)
        return True

    def remove_keyword(self, keyword: str) -> bool:
        keyword = keyword.strip().lower()
        if keyword in self.filter_keywords:
            self.filter_keywords.discard(keyword)
            return True
        return False

    def get_runtime_config(self) -> dict:
        return {
            "source_channel_ids": self.source_channel_ids.copy(),
            "destination_channel_id": self.destination_channel_id,
            "filter_keywords": list(self.filter_keywords),
        }


# Global config instance
config = Config()
