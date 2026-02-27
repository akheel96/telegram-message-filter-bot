"""
Telegram Loot Filter Bot
Main entry point for the bot application.

This bot monitors multiple Telegram channels for messages containing
specific keywords and forwards matching messages to a destination channel.
Features product info extraction for Amazon, Flipkart, and Myntra URLs.
"""

import os
import sys
import logging
import asyncio
import signal
from datetime import datetime
from aiohttp import web
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    AuthKeyUnregisteredError,
    PhoneCodeInvalidError,
)

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import config
from src.listener import MessageListener

# Configure logging - use LOG_LEVEL env var or default to INFO
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

# Global variables for graceful shutdown
client: TelegramClient = None
listener: MessageListener = None
shutdown_event = asyncio.Event()


def setup_signal_handlers():
    """Set up handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        shutdown_event.set()
    
    # Handle SIGINT (Ctrl+C) and SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def periodic_stats_logger(interval: int = 3600):
    """Log statistics periodically."""
    while not shutdown_event.is_set():
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            if listener:
                listener.log_stats()


# ============================================================
# HTTP Server for Render Free Tier (Keep-Alive)
# ============================================================
# Render's free web services sleep after 15 minutes of inactivity.
# This HTTP server provides health check endpoints that can be pinged
# by external services (like UptimeRobot) to keep the bot awake.

async def health_check(request):
    """Health check endpoint for keep-alive pings."""
    stats = listener.get_stats() if listener else {}
    return web.json_response({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "uptime": "active",
        "stats": {
            "messages_received": stats.get("messages_received", 0),
            "messages_forwarded": stats.get("messages_forwarded", 0),
            "products_extracted": stats.get("products_extracted", 0),
        }
    })


async def home(request):
    """Home page with bot status."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Loot Filter Bot</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
            .status { color: #28a745; font-weight: bold; }
            .info { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>🤖 Telegram Loot Filter Bot</h1>
        <p class="status">✅ Bot is running</p>
        <div class="info">
            <p><strong>Health Check:</strong> <code>/health</code></p>
            <p><strong>Keep-Alive:</strong> Ping <code>/health</code> every 14 minutes to prevent sleep</p>
        </div>
        <p>This bot monitors Telegram channels for deal keywords and forwards filtered messages.</p>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')


async def start_http_server(port: int = 8080):
    """Start HTTP server for health checks."""
    app = web.Application()
    app.router.add_get('/', home)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 HTTP server started on port {port}")
    logger.info(f"   Health check: http://0.0.0.0:{port}/health")
    
    return runner


async def connect_with_retry(client: TelegramClient, max_retries: int, delay: int) -> bool:
    """
    Connect to Telegram with retry logic.
    
    Args:
        client: TelegramClient instance
        max_retries: Maximum number of connection attempts
        delay: Delay in seconds between retries
        
    Returns:
        True if connection was successful, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connecting to Telegram (attempt {attempt}/{max_retries})...")
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.error("Client is not authorized. Please run authentication first.")
                logger.error("Run: python auth.py")
                return False
            
            logger.info("✅ Successfully connected to Telegram!")
            return True
            
        except AuthKeyUnregisteredError:
            logger.error("Session is invalid or expired. Please re-authenticate.")
            logger.error("Delete the .session file and run: python auth.py")
            return False
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            
            if attempt < max_retries:
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.error("Max retries reached. Giving up.")
                return False
    
    return False


async def main():
    """Main function to run the bot."""
    global client, listener
    
    # Initialize cleanup variables
    http_runner = None
    
    logger.info("=" * 60)
    logger.info("🤖 Telegram Loot Filter Bot Starting...")
    logger.info(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Load configuration
    if not config.load():
        logger.error("Failed to load configuration. Exiting.")
        sys.exit(1)
    
    # Validate channels
    config.validate_channels()
    
    # Set up signal handlers
    setup_signal_handlers()
    
    # Create Telegram client
    # Support both session file and StringSession (for cloud deployments)
    session_string = os.getenv('SESSION_STRING')
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
        # Connect with retry
        if not await connect_with_retry(client, config.max_retries, config.reconnect_delay):
            sys.exit(1)
        
        # Get current user info  
        me = await client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username or 'N/A'})")
        
        # Create and set up listener
        listener = MessageListener(client, config)
        if not await listener.setup():
            logger.error("Failed to set up message listener. Exiting.")
            sys.exit(1)
        
        # Start HTTP server for Render keep-alive (only if PORT is set)
        http_runner = None
        port = os.getenv('PORT')
        if port:
            http_runner = await start_http_server(int(port))
            logger.info("💡 Tip: Set up UptimeRobot to ping /health every 14 minutes")
        
        logger.info("=" * 60)
        logger.info("🎯 Bot is now running and monitoring for messages!")
        logger.info(f"   Source channels: {len(config.source_channel_ids)}")
        logger.info(f"   Keywords: {', '.join(config.filter_keywords)}")
        logger.info(f"   Product info: {'Enabled' if config.enable_product_info else 'Disabled'}")
        if port:
            logger.info(f"   HTTP server: http://0.0.0.0:{port}")
        logger.info("   Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        # Start periodic stats logging
        stats_task = asyncio.create_task(periodic_stats_logger(3600))
        
        # Run until disconnected or shutdown requested
        await shutdown_event.wait()
        
        # Cancel stats task
        stats_task.cancel()
        try:
            await stats_task
        except asyncio.CancelledError:
            pass
        
        # Log final stats
        if listener:
            logger.info("Final Statistics:")
            listener.log_stats()
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
        
    finally:
        # Cleanup
        if client:
            logger.info("Disconnecting from Telegram...")
            await client.disconnect()
        
        # Cleanup HTTP server
        if http_runner:
            await http_runner.cleanup()
        
        logger.info("Bot stopped. Goodbye! 👋")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
