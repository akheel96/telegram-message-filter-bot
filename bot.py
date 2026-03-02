"""
Telegram Loot Filter Bot
Monitors Telegram channels for keyword-matching messages and forwards them as-is.
"""

import os
import sys
import logging
import asyncio
import signal
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import AuthKeyUnregisteredError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import config
from src.listener import MessageListener

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

client: TelegramClient = None
listener: MessageListener = None
shutdown_event = asyncio.Event()


def setup_signal_handlers():
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def periodic_stats_logger(interval: int = 3600):
    while not shutdown_event.is_set():
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            if listener:
                listener.log_stats()


async def connect_with_retry(client: TelegramClient, max_retries: int, delay: int) -> bool:
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connecting to Telegram (attempt {attempt}/{max_retries})...")
            await client.connect()

            if not await client.is_user_authorized():
                logger.error("Client not authorised. Run: python auth.py")
                return False

            logger.info("Connected to Telegram.")
            return True

        except AuthKeyUnregisteredError:
            logger.error("Session invalid. Delete .session file and run: python auth.py")
            return False

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error("Max retries reached.")
                return False

    return False


async def main():
    global client, listener

    logger.info("=" * 60)
    logger.info("Telegram Loot Filter Bot starting...")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    load_dotenv()

    if not config.load():
        logger.error("Failed to load configuration. Exiting.")
        sys.exit(1)

    config.validate_channels()
    setup_signal_handlers()

    session_string = os.getenv("SESSION_STRING")
    if session_string:
        logger.info("Using StringSession from environment variable")
        session = StringSession(session_string)
    else:
        logger.info(f"Using session file: {config.session_name}.session")
        session = config.session_name

    client = TelegramClient(
        session,
        config.api_id,
        config.api_hash,
        connection_retries=5,
        retry_delay=1,
        auto_reconnect=True,
    )

    try:
        if not await connect_with_retry(client, config.max_retries, config.reconnect_delay):
            sys.exit(1)

        me = await client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username or 'N/A'})")

        listener = MessageListener(client, config)
        if not await listener.setup():
            logger.error("Failed to set up listener. Exiting.")
            sys.exit(1)

        logger.info("=" * 60)
        logger.info("Bot is running and monitoring channels.")
        logger.info(f"  Source channels : {len(config.source_channel_ids)}")
        logger.info(f"  Keywords        : {', '.join(config.filter_keywords)}")
        logger.info("  Press Ctrl+C to stop")
        logger.info("=" * 60)

        stats_task = asyncio.create_task(periodic_stats_logger(3600))

        await shutdown_event.wait()

        stats_task.cancel()
        try:
            await stats_task
        except asyncio.CancelledError:
            pass

        if listener:
            listener.log_stats()

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

    finally:
        if client:
            logger.info("Disconnecting from Telegram...")
            await client.disconnect()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
