"""
Listener module for Telegram Loot Filter Bot.
Handles message listening and forwarding logic.
Supports multiple source channels and product info extraction.
"""

import logging
import asyncio
from typing import Optional, List
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
from .product_handler import ProductHandler
from .formatter import MessageFormatter
from .url_handler import URLHandler, is_listing_page

logger = logging.getLogger(__name__)


class MessageListener:
    """Listens to messages from source channels and forwards filtered ones."""
    
    def __init__(self, client: TelegramClient, config: Config):
        """
        Initialize the message listener.
        
        Args:
            client: Telethon TelegramClient instance
            config: Configuration object
        """
        self.client = client
        self.config = config
        self.filter = MessageFilter(config.filter_keywords)
        self.duplicate_detector = DuplicateDetector(config.cache_size)
        
        # Initialize product handler and formatter if enabled
        if config.enable_product_info:
            # Use faster timeout in fast mode
            timeout = min(config.http_timeout, 10) if config.fast_mode else config.http_timeout
            
            # Initialize the product handler with generic scraper option
            self.product_handler = ProductHandler(
                timeout=timeout,
                prefer_indian=config.prefer_indian_urls,
                enable_generic_scraper=config.enable_generic_scraper
            )
            self.formatter = MessageFormatter(
                discount_highlight_threshold=config.discount_highlight_threshold
            )
        else:
            self.product_handler = None
            self.formatter = None
        
        self.stats = {
            "messages_received": 0,
            "messages_filtered": 0,
            "messages_forwarded": 0,
            "products_extracted": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }
        
        # Track verified channels
        self.verified_channels = {}
        
    async def setup(self) -> bool:
        """
        Set up the message listener.
        
        Returns:
            True if setup was successful, False otherwise
        """
        try:
            # Verify all source channels
            for channel_id in self.config.source_channel_ids:
                source_entity = await self._get_entity(channel_id)
                if not source_entity:
                    logger.error(f"Cannot access source channel: {channel_id}")
                    return False
                
                source_name = self._get_entity_name(source_entity)
                self.verified_channels[channel_id] = source_name
                logger.info(f"Source channel verified: {source_name} ({channel_id})")
            
            # Verify destination channel access
            dest_entity = await self._get_entity(self.config.destination_channel_id)
            if not dest_entity:
                logger.error(f"Cannot access destination channel: {self.config.destination_channel_id}")
                return False
            
            dest_name = self._get_entity_name(dest_entity)
            logger.info(f"Destination channel verified: {dest_name}")
            
            # Register event handler for all source channels
            self._register_handler()
            logger.info(f"Message handler registered for {len(self.config.source_channel_ids)} channel(s)")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during setup: {e}")
            return False
    
    async def _get_entity(self, entity_id: int):
        """Get entity (channel/chat/user) by ID."""
        try:
            return await self.client.get_entity(entity_id)
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return None
    
    def _get_entity_name(self, entity) -> str:
        """Get the display name of an entity."""
        if isinstance(entity, (Channel, Chat)):
            return entity.title
        elif isinstance(entity, User):
            return entity.first_name or entity.username or str(entity.id)
        return str(entity)
    
    def _register_handler(self) -> None:
        """Register the new message event handler for all source channels."""
        @self.client.on(events.NewMessage(chats=self.config.source_channel_ids))
        async def handler(event: events.NewMessage.Event):
            await self._handle_message(event.message)
    
    async def _handle_message(self, message: Message) -> None:
        """
        Handle an incoming message.
        
        Args:
            message: Telethon Message object
        """
        self.stats["messages_received"] += 1
        
        try:
            # Check for duplicates
            if self.duplicate_detector.is_duplicate(message.id, message.chat_id):
                self.stats["duplicates_skipped"] += 1
                logger.debug(f"Skipping duplicate message: {message.id}")
                return
            
            # Check if message has any URL (Requirement 1: skip messages without URL)
            text = message.text or message.message
            if not text:
                logger.debug(f"Message {message.id} has no text, skipping")
                return
            
            urls = URLHandler().extract_urls(text)
            if not urls:
                logger.debug(f"Message {message.id} has no URL, skipping")
                return
            
            # Check if message matches filter
            if not self.filter.contains_keyword(message):
                logger.debug(f"Message {message.id} does not contain keywords, skipping")
                return
            
            # Check for skip sites/text patterns
            if self.config.skip_sites_text and self._contains_skip_patterns(text):
                logger.info(f"⏭️ Skipping message {message.id} due to skip patterns")
                self.duplicate_detector.mark_processed(message.id, message.chat_id)
                return
            
            self.stats["messages_filtered"] += 1
            
            # Check for listing pages and optionally skip them
            skip_due_to_listing = False
            for url in urls:
                if is_listing_page(url):
                    if self.config.skip_listing_pages:
                        logger.info(f"⏭️ Skipping listing page: {url}")
                        skip_due_to_listing = True
                        break
                    else:
                        logger.warning(f"⚠️ Message contains listing/search page URL: {url}")
                        logger.warning("   Listing pages show multiple products. Consider sharing direct product links instead.")
            
            if skip_due_to_listing:
                self.duplicate_detector.mark_processed(message.id, message.chat_id)
                return
            
            # Log matching keywords
            matching = self.filter.get_matching_keywords(message)
            source_name = self.verified_channels.get(message.chat_id, str(message.chat_id))
            logger.info(f"Found matching message {message.id} from '{source_name}' (keywords: {matching})")
            
            # FAST PATH: Skip product extraction if configured (max speed for time-critical deals)
            if self.config.skip_product_extraction:
                logger.debug("Skip product extraction enabled - fast forwarding")
                clean_url = None
                if self.product_handler:
                    original_url = self.product_handler.url_handler.extract_first_url(text)
                    if original_url:
                        expanded = await self.product_handler.url_handler.expand_url(original_url)
                        clean_url = self.product_handler.url_handler.remove_affiliate_params(expanded)
                
                success = await self._forward_message(message, clean_url)
                if success:
                    self.stats["messages_forwarded"] += 1
                    self.duplicate_detector.mark_processed(message.id, message.chat_id)
                    self._log_forwarded_message(message)
                return
            
            # Try to extract product info and send formatted message
            formatted_sent = False
            skip_due_to_stock = False
            clean_url = None
            
            if self.product_handler and self.formatter:
                formatted_sent, skip_due_to_stock, clean_url = await self._send_formatted_message(message)
            
            # Forward original message only if:
            # 1. No formatted message was sent AND
            # 2. Either no product was found OR config allows out-of-stock forwarding
            should_forward = not formatted_sent and (not skip_due_to_stock or not self.config.skip_out_of_stock)
            
            if should_forward:
                # Use clean URL in forwarded message if available
                success = await self._forward_message(message, clean_url)
                if success:
                    self.stats["messages_forwarded"] += 1
                    self.duplicate_detector.mark_processed(message.id, message.chat_id)
                    self._log_forwarded_message(message)
                else:
                    self.stats["errors"] += 1
            elif skip_due_to_stock and self.config.skip_out_of_stock:
                logger.info(f"⏭️ Skipped out-of-stock message {message.id} (SKIP_OUT_OF_STOCK=true)")
                self.duplicate_detector.mark_processed(message.id, message.chat_id)
                
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error handling message {message.id}: {e}")
    
    def _contains_skip_patterns(self, text: str) -> bool:
        """
        Check if message text contains any skip patterns.
        
        Args:
            text: Message text to check
            
        Returns:
            True if text contains skip patterns
        """
        if not text or not self.config.skip_sites_text:
            return False
        
        text_lower = text.lower()
        for pattern in self.config.skip_sites_text:
            if pattern in text_lower:
                logger.debug(f"Found skip pattern '{pattern}' in message")
                return True
        
        return False
    
    async def _send_formatted_message(self, message: Message) -> tuple[bool, bool, Optional[str]]:
        """
        Try to extract product info and send a formatted message.
        
        Args:
            message: Original message
            
        Returns:
            Tuple of (message_sent, skipped_due_to_stock, clean_url)
            - message_sent: True if formatted message was sent
            - skipped_due_to_stock: True if product was found but skipped due to being out of stock
            - clean_url: Cleaned/expanded URL if found
        """
        try:
            # Get message text
            text = message.text or message.message
            if not text:
                return (False, False, None)
            
            # Extract product info (this also expands URL internally)
            product_info = await self.product_handler.extract_product_info(text)
            
            # Get clean URL from product_info if available, otherwise expand manually
            clean_url = None
            if product_info and product_info.url:
                clean_url = self.product_handler.url_handler.remove_affiliate_params(product_info.url)
            elif text:
                # Only expand URL if product extraction failed (fallback)
                original_url = self.product_handler.url_handler.extract_first_url(text)
                if original_url:
                    expanded = await self.product_handler.url_handler.expand_url(original_url)
                    clean_url = self.product_handler.url_handler.remove_affiliate_params(expanded)
            
            if product_info:
                # Check if product should be formatted (includes stock check)
                should_format = self.formatter.should_format_product(product_info)
                
                if should_format:
                    # Format the message
                    formatted_text = self.formatter.format_product_message(product_info, text)
                    
                    # Send formatted message
                    await self.client.send_message(
                        self.config.destination_channel_id,
                        formatted_text,
                        link_preview=False
                    )
                    
                    self.stats["products_extracted"] += 1
                    self.stats["messages_forwarded"] += 1
                    self.duplicate_detector.mark_processed(message.id, message.chat_id)
                    
                    logger.info(f"✅ Sent formatted product message: {product_info.title}")
                    return True, False, clean_url
                else:
                    # Product was found but not formatted - check if due to stock
                    skip_due_to_stock = product_info.in_stock is False
                    return False, skip_due_to_stock, clean_url
            
            return False, False, clean_url
            
        except Exception as e:
            logger.error(f"Error sending formatted message: {e}")
            return False, False, None
    
    async def _forward_message(self, message: Message, clean_url: Optional[str] = None) -> bool:
        """
        Forward a message to the destination channel, optionally replacing URLs with clean versions.
        
        Args:
            message: Telethon Message object
            clean_url: Optional clean URL to replace the original URL in message text
            
        Returns:
            True if forwarding was successful, False otherwise
        """
        try:
            message_text = None
            
            # If we have a clean URL and the original message contains a URL, replace it
            if clean_url and (message.text or message.message):
                from .url_handler import URLHandler
                url_handler = URLHandler()
                original_text = message.text or message.message
                original_url = url_handler.extract_first_url(original_text)
                
                if original_url and original_url != clean_url:
                    message_text = original_text.replace(original_url, clean_url)
                    logger.info(f"🧹 Replaced URL: {original_url} -> {clean_url}")
            
            # Send as new message with clean URL if we modified the text
            if message_text:
                await self.client.send_message(
                    entity=self.config.destination_channel_id,
                    message=message_text,
                    link_preview=False
                )
            else:
                # Forward original message
                await self.client.forward_messages(
                    entity=self.config.destination_channel_id,
                    messages=message,
                    from_peer=message.chat_id
                )
            
            return True
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait error, sleeping for {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            # Retry after waiting
            return await self._forward_message(message, clean_url)
            
        except ChannelPrivateError:
            logger.error("Cannot forward: destination channel is private or inaccessible")
            return False
            
        except ChatWriteForbiddenError:
            logger.error("Cannot forward: no permission to write in destination channel")
            return False
            
        except MessageIdInvalidError:
            logger.error(f"Cannot forward: message {message.id} is invalid or deleted")
            return False
            
        except Exception as e:
            logger.error(f"Failed to forward message {message.id}: {e}")
            return False
    
    def _log_forwarded_message(self, message: Message) -> None:
        """Log details about a forwarded message."""
        text = message.text or message.message or "[Media without caption]"
        # Truncate long messages for logging
        if len(text) > 100:
            text = text[:100] + "..."
        
        msg_type = self._get_message_type(message)
        source_name = self.verified_channels.get(message.chat_id, str(message.chat_id))
        logger.info(f"✅ Forwarded [{msg_type}] from '{source_name}': {text}")
    
    def _get_message_type(self, message: Message) -> str:
        """Determine the type of message."""
        if message.photo:
            return "Photo"
        elif message.video:
            return "Video"
        elif message.document:
            return "Document"
        elif message.audio:
            return "Audio"
        elif message.voice:
            return "Voice"
        elif message.sticker:
            return "Sticker"
        elif message.forward:
            return "Forward"
        elif message.text and ("http://" in message.text or "https://" in message.text):
            return "URL"
        else:
            return "Text"
    
    def get_stats(self) -> dict:
        """Get current statistics."""
        return {
            **self.stats,
            "cache_size": self.duplicate_detector.size,
            "source_channels": len(self.config.source_channel_ids),
        }
    
    def log_stats(self) -> None:
        """Log current statistics."""
        stats = self.get_stats()
        logger.info("=" * 50)
        logger.info("📊 Bot Statistics:")
        logger.info(f"   Source channels: {stats['source_channels']}")
        logger.info(f"   Messages received: {stats['messages_received']}")
        logger.info(f"   Messages filtered: {stats['messages_filtered']}")
        logger.info(f"   Messages forwarded: {stats['messages_forwarded']}")
        logger.info(f"   Products extracted: {stats['products_extracted']}")
        logger.info(f"   Duplicates skipped: {stats['duplicates_skipped']}")
        logger.info(f"   Errors: {stats['errors']}")
        logger.info(f"   Cache size: {stats['cache_size']}")
        logger.info("=" * 50)
