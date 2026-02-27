"""
Authentication Script for Telegram Loot Filter Bot.

Run this script first to authenticate with Telegram and create a session file.
This only needs to be done once, then the session file can be used by the bot.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def authenticate():
    """Interactive authentication with Telegram."""
    load_dotenv()
    
    # Get credentials
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    session_name = os.getenv("SESSION_NAME", "loot_filter_bot")
    
    if not api_id or not api_hash:
        logger.error("API_ID and API_HASH must be set in environment variables or .env file")
        logger.info("Get your API credentials from: https://my.telegram.org/apps")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🔐 Telegram Authentication")
    print("=" * 60)
    print("\nThis script will create a session file for the bot.")
    print("You'll need to enter your phone number and verification code.\n")
    
    client = TelegramClient(session_name, int(api_id), api_hash)
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"✅ Already authenticated as: {me.first_name} (@{me.username or 'N/A'})")
            print(f"   Session file: {session_name}.session")
            return
        
        # Get phone number
        phone = input("📱 Enter your phone number (with country code, e.g., +1234567890): ").strip()
        
        if not phone:
            logger.error("Phone number is required")
            sys.exit(1)
        
        # Send code request
        try:
            await client.send_code_request(phone)
        except PhoneNumberInvalidError:
            logger.error("Invalid phone number format. Use international format: +1234567890")
            sys.exit(1)
        
        # Get verification code
        code = input("🔢 Enter the verification code you received: ").strip()
        
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            # 2FA enabled
            print("\n⚠️  Two-Factor Authentication is enabled on this account")
            password = input("🔑 Enter your 2FA password: ").strip()
            await client.sign_in(password=password)
        except PhoneCodeInvalidError:
            logger.error("Invalid verification code")
            sys.exit(1)
        
        # Success!
        me = await client.get_me()
        print("\n" + "=" * 60)
        print(f"✅ Successfully authenticated as: {me.first_name} (@{me.username or 'N/A'})")
        print(f"   Session file created: {session_name}.session")
        print("\n   You can now run the bot with: python bot.py")
        print("=" * 60 + "\n")
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        sys.exit(1)
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(authenticate())
