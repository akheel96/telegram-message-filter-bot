"""
String Session Generator for cloud deployments.
Generates a StringSession for use with Fly.io, Railway, or other cloud platforms.

Usage:
    python generate_string_session.py
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
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


async def generate_string_session():
    """Generate a StringSession for cloud deployments."""
    load_dotenv()
    
    # Get credentials
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    
    if not api_id or not api_hash:
        logger.error("API_ID and API_HASH must be set in .env file")
        logger.info("Get your API credentials from: https://my.telegram.org/apps")
        return
    
    print("\n" + "=" * 70)
    print("🔐 Telegram String Session Generator")
    print("=" * 70)
    print("\nThis will generate a StringSession for cloud deployments.")
    print("You'll need to enter your phone number and verification code.\n")
    
    client = TelegramClient(StringSession(), int(api_id), api_hash)
    
    try:
        await client.connect()
        
        # Get phone number
        phone = input("📱 Enter your phone number (with country code, e.g., +1234567890): ").strip()
        
        if not phone:
            logger.error("Phone number is required")
            return
        
        # Send code request
        try:
            await client.send_code_request(phone)
        except PhoneNumberInvalidError:
            logger.error("Invalid phone number format. Use international format: +1234567890")
            return
        
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
            return
        
        # Get string session
        string_session = client.session.save()
        
        # Success!
        print("\n" + "=" * 70)
        print("✅ StringSession generated successfully!")
        print("=" * 70)
        print("\n📋 Copy the following StringSession:\n")
        print(f"{string_session}\n")
        print("=" * 70)
        print("\n📝 How to use:")
        print("1. Set this as SESSION_STRING environment variable in your cloud platform")
        print("2. Example for Fly.io:")
        print(f"   fly secrets set SESSION_STRING=\"{string_session[:20]}...\"")
        print("\n3. Example for Railway:")
        print("   Add SESSION_STRING variable in Railway dashboard")
        print("\n⚠️  Keep this session string SECRET! It gives full access to your account.")
        print("=" * 70 + "\n")
        
    except Exception as e:
        logger.error(f"Failed to generate StringSession: {e}")
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(generate_string_session())
