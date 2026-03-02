"""
Listener module for Telegram Loot Filter Bot.
Listens to source channels, filters by keyword, and forwards matching messages as-is.
"""

import logging
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import Message, Channel, Chat, User
from telethon.errors import (
    FloodWaitError,
    ChannelPrivateError,
    ChatWriteForbiddenError,
    MessageIdInvalidError,
)

from .filter import MessageFilter, DuplicateDetector
from .config import Config

logger = logging.getLogger(__name__)


class MessageListener:
    """Listens to source channels and forwards keyword-matching messages as-is."""

    def __init__(self, client: TelegramClient, config: Config):
        self.client = client
        self.config = config
        self.filter = MessageFilter(config.filter_keywords)
        self.duplicate_detector = DuplicateDetector(config.cache_size)
        self.verified_channels = {}
        self.stats = {
            "messages_received": 0,
            "messages_filtered": 0,
            "messages_forwarded": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }

    async def setup(self) -> bool:
        """Verify channels and register the message handler."""
        try:
            for channel_id in self.config.source_channel_ids:
                entity = await self._get_entity(channel_id)
                if not entity:
                    logger.error(f"Cannot access source channel: {channel_id}")
                    return False
                name = self._get_entity_name(entity)
                self.verified_channels[channel_id] = name
                logger.info(f"Source channel verified: {name} ({channel_id})")

            dest_entity = await self._get_entity(self.config.destination_channel_id)
            if not dest_entity:
                logger.error(f"Cannot access destination channel: {self.config.destination_channel_id}")
                return False
            logger.info(f"Destination channel verified: {self._get_entity_name(dest_entity)}")

            self._register_handler()
            logger.info(f"Message handler registered for {len(self.config.source_channel_ids)} channel(s)")
            return True

        except Exception as e:
            logger.error(f"Error during setup: {e}")
            return False

    async def _get_entity(self, entity_id: int):
        try:
            return await self.client.get_entity(entity_id)
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return None

    def _get_entity_name(self, entity) -> str:
        if isinstance(entity, (Channel, Chat)):
            return entity.title
        elif isinstance(entity, User):
            return entity.first_name or entity.username or str(entity.id)
        return str(entity)

    def _register_handler(self) -> None:
        @self.client.on(events.NewMessage(chats=self.config.source_channel_ids))
        async def handler(event: events.NewMessage.Event):
            await self._handle_message(event.message)

    async def _handle_message(self, message: Message) -> None:
        self.stats["messages_received"] += 1
        try:
            # Skip duplicates
            if self.duplicate_detector.is_duplicate(message.id, message.chat_id):
                self.stats["duplicates_skipped"] += 1
                return

            # Skip messages without text
            text = message.text or message.message
            if not text:
                return

            # Apply skip-site patterns
            if self.config.skip_sites_text and self._contains_skip_patterns(text):
                logger.info(f"Skipping message {message.id} — matched skip pattern")
                self.duplicate_detector.mark_processed(message.id, message.chat_id)
                return

            # Apply keyword filter
            if not self.filter.contains_keyword(message):
                return

            self.stats["messages_filtered"] += 1
            matching = self.filter.get_matching_keywords(message)
            source_name = self.verified_channels.get(message.chat_id, str(message.chat_id))
            logger.info(f"Match in '{source_name}' msg={message.id} keywords={matching}")

            # Forward as-is
            success = await self._forward_message(message)
            if success:
                self.stats["messages_forwarded"] += 1
                self.duplicate_detector.mark_processed(message.id, message.chat_id)
                self._log_forwarded(message)
            else:
                self.stats["errors"] += 1

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error handling message {message.id}: {e}")

    def _contains_skip_patterns(self, text: str) -> bool:
        text_lower = text.lower()
        for pattern in self.config.skip_sites_text:
            if pattern in text_lower:
                return True
        return False

    async def _forward_message(self, message: Message) -> bool:
        try:
            await self.client.forward_messages(
                entity=self.config.destination_channel_id,
                messages=message,
                from_peer=message.chat_id,
            )
            return True

        except FloodWaitError as e:
            logger.warning(f"FloodWait: sleeping {e.seconds}s")
            await asyncio.sleep(e.seconds)
            return await self._forward_message(message)

        except ChannelPrivateError:
            logger.error("Destination channel is private or inaccessible")
            return False

        except ChatWriteForbiddenError:
            logger.error("No write permission in destination channel")
            return False

        except MessageIdInvalidError:
            logger.error(f"Message {message.id} is invalid or deleted")
            return False

        except Exception as e:
            logger.error(f"Failed to forward message {message.id}: {e}")
            return False

    def _log_forwarded(self, message: Message) -> None:
        text = message.text or message.message or "[Media]"
        if len(text) > 100:
            text = text[:100] + "..."
        source_name = self.verified_channels.get(message.chat_id, str(message.chat_id))
        logger.info(f"Forwarded from '{source_name}': {text}")

    def get_stats(self) -> dict:
        return {
            **self.stats,
            "cache_size": self.duplicate_detector.size,
            "source_channels": len(self.config.source_channel_ids),
        }

    def log_stats(self) -> None:
        s = self.get_stats()
        logger.info("=" * 50)
        logger.info("Bot Statistics:")
        logger.info(f"  Source channels : {s['source_channels']}")
        logger.info(f"  Received        : {s['messages_received']}")
        logger.info(f"  Filtered        : {s['messages_filtered']}")
        logger.info(f"  Forwarded       : {s['messages_forwarded']}")
        logger.info(f"  Duplicates      : {s['duplicates_skipped']}")
        logger.info(f"  Errors          : {s['errors']}")
        logger.info("=" * 50)
