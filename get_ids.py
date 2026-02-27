"""
Utility script to get channel/chat IDs.
Run this after authentication to find the IDs of your channels.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def get_dialogs():
    """List all chats/channels the user has access to."""
    load_dotenv()
    
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    session_name = os.getenv("SESSION_NAME", "loot_filter_bot")
    
    if not api_id or not api_hash:
        logger.error("API_ID and API_HASH must be set")
        return
    
    client = TelegramClient(session_name, int(api_id), api_hash)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error("Not authenticated. Run 'python auth.py' first.")
            return
        
        print("\n" + "=" * 80)
        print("📋 Your Telegram Chats and Channels")
        print("=" * 80)
        print(f"{'Type':<12} | {'ID':<20} | {'Name'}")
        print("-" * 80)
        
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            
            if isinstance(entity, Channel):
                entity_type = "Channel" if entity.broadcast else "Group"
                entity_id = f"-100{entity.id}"
            elif isinstance(entity, Chat):
                entity_type = "Chat"
                entity_id = f"-{entity.id}"
            elif isinstance(entity, User):
                entity_type = "User"
                entity_id = str(entity.id)
            else:
                entity_type = "Unknown"
                entity_id = str(dialog.id)
            
            name = dialog.name or "Unnamed"
            print(f"{entity_type:<12} | {entity_id:<20} | {name}")
        
        print("=" * 80)
        print("\n💡 Copy the ID of the channel you want to monitor as SOURCE_CHANNEL_ID")
        print("   Copy the ID of where you want messages forwarded as DESTINATION_CHANNEL_ID")
        print()
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(get_dialogs())
