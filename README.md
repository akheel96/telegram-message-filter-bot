# 🤖 Telegram Loot Filter Bot

A production-ready Telegram bot that monitors **multiple channels** for messages containing **deal keywords**, extracts product information from Amazon/Flipkart/Myntra URLs, filters out-of-stock items, and forwards clean, formatted deal alerts to your destination channel.

Built with **Python 3.11+**, **Telethon**, and **aiohttp** for high-performance async processing.

---

## ✨ Features

### Core Features
- 🔍 **Multi-Keyword Filtering** - Filter messages by multiple keywords (loot, deal, offer, etc.)
- 📺 **Multi-Channel Monitoring** - Monitor multiple source channels simultaneously
- 🔗 **Smart URL Processing** - Expands shortened URLs and removes affiliate/tracking parameters
- 📤 **Intelligent Forwarding** - Forwards original or beautifully formatted product messages
- 🚫 **Duplicate Prevention** - LRU cache prevents duplicate forwards
- 🔄 **Auto-Reconnect** - Automatic retry with exponential backoff

### Product Info Extraction
- 📦 **Amazon** - ASIN extraction, price, discount, rating, stock status
- 🛍️ **Flipkart** - PID extraction, price, offers, availability
- 👗 **Myntra** - Product ID, brand, price, size availability
- 🌐 **Generic Scraper** - Basic product info from unknown e-commerce sites

### Smart Filtering
- ✅ **Stock Checking** - Optionally skip out-of-stock products
- 📄 **Listing Page Detection** - Skip search/category pages (not single products)
- 🚫 **Site Filtering** - Skip specific sites (e.g., AJIO)
- ⚡ **Fast Mode** - Reduced timeouts for time-sensitive deals

### Performance Optimizations
- ⏱️ **Fast URL Expansion** - 5-8s for shortened URLs
- 🚀 **Skip Direct URLs** - No expansion needed for direct product links
- 💨 **Fast Mode** - 10s max timeout for quick processing
- ⏭️ **Skip Extraction Mode** - Maximum speed (~5s) for flash sales

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TELEGRAM LOOT FILTER BOT                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐          │
│  │ Source Channel │     │ Source Channel │     │ Source Channel │          │
│  │      #1        │     │      #2        │     │      #N        │          │
│  └───────┬────────┘     └───────┬────────┘     └───────┬────────┘          │
│          │                      │                      │                    │
│          └──────────────────────┼──────────────────────┘                    │
│                                 ▼                                           │
│                    ┌────────────────────────┐                               │
│                    │    MESSAGE LISTENER    │                               │
│                    │   (Telethon Events)    │                               │
│                    └───────────┬────────────┘                               │
│                                │                                            │
│                                ▼                                            │
│                    ┌────────────────────────┐                               │
│                    │   MESSAGE FILTER       │                               │
│                    │ • Keyword matching     │                               │
│                    │ • URL presence check   │                               │
│                    │ • Skip patterns        │                               │
│                    │ • Duplicate detection  │                               │
│                    └───────────┬────────────┘                               │
│                                │                                            │
│                    ┌───────────┴───────────┐                                │
│                    │    URL HANDLER        │                                │
│                    │ • URL extraction      │                                │
│                    │ • Shortlink expansion │                                │
│                    │ • Affiliate removal   │                                │
│                    │ • Indian URL convert  │                                │
│                    └───────────┬───────────┘                                │
│                                │                                            │
│              ┌─────────────────┼─────────────────┐                          │
│              │                 │                 │                          │
│              ▼                 ▼                 ▼                          │
│     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│     │   AMAZON     │  │  FLIPKART    │  │   MYNTRA     │                   │
│     │   Handler    │  │   Handler    │  │   Handler    │                   │
│     │ • Mobile API │  │ • API/HTML   │  │ • pdpData    │                   │
│     │ • HTML parse │  │ • URL parse  │  │ • API parse  │                   │
│     └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                   │
│            │                 │                 │                            │
│            └─────────────────┼─────────────────┘                            │
│                              ▼                                              │
│                    ┌────────────────────────┐                               │
│                    │   PRODUCT HANDLER      │                               │
│                    │ • Platform routing     │                               │
│                    │ • Generic fallback     │                               │
│                    │ • Stock validation     │                               │
│                    └───────────┬────────────┘                               │
│                                │                                            │
│                                ▼                                            │
│                    ┌────────────────────────┐                               │
│                    │   MESSAGE FORMATTER    │                               │
│                    │ • Price formatting     │                               │
│                    │ • Discount highlight   │                               │
│                    │ • Emoji decoration     │                               │
│                    └───────────┬────────────┘                               │
│                                │                                            │
│                                ▼                                            │
│                    ┌────────────────────────┐                               │
│                    │  DESTINATION CHANNEL   │                               │
│                    │   (Your Deal Alerts)   │                               │
│                    └────────────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
telegram-message-filter-bot/
├── src/
│   ├── __init__.py           # Package marker
│   ├── config.py             # Configuration management (env vars)
│   ├── filter.py             # Keyword filtering & duplicate detection
│   ├── listener.py           # Message event handler & forwarding
│   ├── url_handler.py        # URL extraction, expansion, cleaning
│   ├── product_handler.py    # Product info orchestrator
│   ├── formatter.py          # Message formatting for Telegram
│   └── platforms/            # Platform-specific handlers
│       ├── __init__.py       # Platform exports
│       ├── base.py           # Base class & ProductInfo dataclass
│       ├── amazon.py         # Amazon scraper (mobile/desktop)
│       ├── flipkart.py       # Flipkart API/scraper
│       └── myntra.py         # Myntra API/scraper
├── bot.py                    # Main entry point
├── auth.py                   # Telegram authentication script
├── get_ids.py                # Channel ID discovery tool
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker container config
├── render.yaml               # Render deployment blueprint
├── Procfile                  # Heroku/Render process file
├── runtime.txt               # Python version specification
├── env.example.txt           # Example environment variables
└── README.md                 # This file
```

---

## 🔄 Message Processing Flow

```
Message Received
       │
       ▼
┌──────────────────┐
│ Has URL?         │──No──► Skip
└────────┬─────────┘
         │Yes
         ▼
┌──────────────────┐
│ Contains keyword?│──No──► Skip
└────────┬─────────┘
         │Yes
         ▼
┌──────────────────┐
│ Skip pattern?    │──Yes─► Skip (AJIO, etc.)
└────────┬─────────┘
         │No
         ▼
┌──────────────────┐
│ Listing page?    │──Yes─► Skip (if SKIP_LISTING_PAGES=true)
└────────┬─────────┘
         │No
         ▼
┌──────────────────┐
│ Duplicate?       │──Yes─► Skip
└────────┬─────────┘
         │No
         ▼
┌──────────────────────────────────┐
│ SKIP_PRODUCT_EXTRACTION=true?   │──Yes──► Forward with clean URL
└────────┬─────────────────────────┘
         │No
         ▼
┌──────────────────┐
│ Extract product  │
│ info from URL    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Out of stock?    │──Yes─► Skip (if SKIP_OUT_OF_STOCK=true)
└────────┬─────────┘
         │No/Unknown
         ▼
┌──────────────────┐
│ Format message   │
│ with product     │
│ details          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Forward to       │
│ destination      │
└──────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ (3.11 recommended)
- pip (Python package manager)
- Telegram account

### Local Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/telegram-message-filter-bot.git
cd telegram-message-filter-bot

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows PowerShell:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file (copy from example)
cp env.example.txt .env
# Edit .env with your credentials

# 6. Authenticate with Telegram (one-time)
python auth.py

# 7. Run the bot
python bot.py
```

---

## 🔐 Getting Telegram Credentials

### Step 1: Create API Credentials

1. Go to [my.telegram.org](https://my.telegram.org/)
2. Log in with your phone number
3. Click **"API development tools"**
4. Fill the form:
   - App title: `Loot Filter Bot`
   - Short name: `lootbot`
   - Platform: `Desktop`
5. Save your **API_ID** and **API_HASH**

### Step 2: Get Channel IDs

**Method 1: Using Web Telegram**
1. Open [web.telegram.org](https://web.telegram.org/)
2. Navigate to the channel
3. URL shows the ID: `https://web.telegram.org/k/#-1001234567890`

**Method 2: Using the helper script**
```bash
python get_ids.py
```
This lists all your chats with their IDs.

**Method 3: Forward to @userinfobot**
1. Forward any message from the channel to [@userinfobot](https://t.me/userinfobot)
2. The bot replies with the channel ID

---

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) | `12345678` |
| `API_HASH` | Telegram API Hash | `abc123def456...` |
| `SOURCE_CHANNEL_IDS` | Channel IDs to monitor (comma-separated) | `-1001234567890,-1009876543210` |
| `DESTINATION_CHANNEL_ID` | Channel to forward deals to | `-1009876543210` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FILTER_KEYWORDS` | `loot` | Keywords to filter (comma-separated) |
| `FAST_MODE` | `true` | Use reduced timeouts (10s max) |
| `SKIP_PRODUCT_EXTRACTION` | `false` | Skip product info for max speed |
| `ENABLE_PRODUCT_INFO` | `true` | Enable product info extraction |
| `HTTP_TIMEOUT` | `15` | HTTP request timeout (seconds) |
| `SKIP_OUT_OF_STOCK` | `true` | Skip out-of-stock products |
| `SKIP_LISTING_PAGES` | `false` | Skip category/search pages |
| `SKIP_SITES_TEXT` | `ajio,ajiio` | Skip messages containing these |
| `ENABLE_GENERIC_SCRAPER` | `true` | Scrape unknown sites |
| `PREFER_INDIAN_URLS` | `true` | Convert to Indian domains |
| `DISCOUNT_HIGHLIGHT_THRESHOLD` | `50` | Highlight discounts above this % |
| `SESSION_NAME` | `loot_filter_bot` | Telegram session file name |
| `CACHE_SIZE` | `1000` | Duplicate detection cache size |
| `RECONNECT_DELAY` | `5` | Seconds between reconnect attempts |
| `MAX_RETRIES` | `10` | Max reconnection attempts |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING) |

### Performance Tuning

For **time-sensitive flash deals** (items sell out in seconds):
```env
FAST_MODE=true
SKIP_PRODUCT_EXTRACTION=true  # ~5s processing
HTTP_TIMEOUT=10
```

For **full product information**:
```env
FAST_MODE=true
SKIP_PRODUCT_EXTRACTION=false  # ~10s processing
HTTP_TIMEOUT=15
```

---

## ☁️ Deployment

### Render (Recommended)

1. **Fork/Push** this repository to GitHub

2. **Create Render Account** at [render.com](https://render.com)

3. **New Background Worker**:
   - Click "New" → "Background Worker"
   - Connect your GitHub repository
   - Select branch (usually `main`)

4. **Configure Settings**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`

5. **Add Environment Variables**:
   Add all required variables from the table above.

6. **Session File**: For the Telegram session, either:
   - Run `auth.py` locally and commit the `.session` file
   - Use StringSession (see below)

7. **Deploy** - Render will build and start your bot

### Using render.yaml (Blueprint)

This repo includes a `render.yaml` for one-click deployment:

```yaml
services:
  - type: worker
    name: telegram-loot-filter-bot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python bot.py
```

### Docker

```bash
# Build image
docker build -t loot-filter-bot .

# Run container
docker run -d \
  --name loot-bot \
  --restart unless-stopped \
  -e API_ID=your_api_id \
  -e API_HASH=your_api_hash \
  -e SOURCE_CHANNEL_IDS=-1001234567890 \
  -e DESTINATION_CHANNEL_ID=-1009876543210 \
  -e FILTER_KEYWORDS=loot,deal \
  -v $(pwd):/app \
  loot-filter-bot
```

### Using StringSession (For Cloud)

For serverless/cloud deployments where you can't persist files:

```python
# Run locally to generate StringSession
from telethon.sessions import StringSession
from telethon import TelegramClient
import asyncio

async def get_string_session():
    # Replace with your credentials
    API_ID = 12345678
    API_HASH = "your_api_hash"
    
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()
    print("Your StringSession:")
    print(client.session.save())  # Copy this output

asyncio.run(get_string_session())

# Then set environment variable:
# SESSION_STRING=your_string_session_here
```

---

## 📊 Sample Output

### Startup Logs
```
2024-02-27 10:00:00 | INFO     | ============================================================
2024-02-27 10:00:00 | INFO     | 🤖 Telegram Loot Filter Bot Starting...
2024-02-27 10:00:00 | INFO     | Configuration loaded successfully
2024-02-27 10:00:00 | INFO     | Source Channels: [-1001234567890, -1009876543210]
2024-02-27 10:00:00 | INFO     | Filter Keywords: {'loot', 'deal', 'offer'}
2024-02-27 10:00:00 | INFO     | Fast Mode: Enabled
2024-02-27 10:00:01 | INFO     | ✅ Successfully connected to Telegram!
2024-02-27 10:00:01 | INFO     | 🎯 Bot is now running and monitoring for messages!
```

### Formatted Deal Message
```
🔥🔥🔥 MEGA LOOT DEAL - 75% OFF! 🔥🔥🔥

📦 Samsung | Galaxy M34 5G (Midnight Blue, 6GB RAM)

📌 Product: Samsung Galaxy M34 5G (Midnight Blue, 6GB, 128GB Storage)
🏷️ Brand: Samsung
💰 Price: ₹12,999 🎉
💸 MRP: ~~₹21,999~~
🚀 Discount: 75% OFF
⭐ Rating: ★★★★½ (4.3/5) • 12.5K reviews
📦 Platform: Amazon
✅ In Stock

🔗 Link: https://www.amazon.in/dp/B0C1234567

━━━━━━━━━━━━━━━━━━━━━
```

---

## 🛠️ Troubleshooting

### "ModuleNotFoundError"
Ensure virtual environment is activated and dependencies are installed:
```bash
venv\Scripts\activate  # or: source venv/bin/activate
pip install -r requirements.txt
```

### "Client is not authorized"
Run authentication script:
```bash
python auth.py
```

### "Cannot access channel"
- Verify you're a member of the channel
- Check channel ID format (should start with `-100`)
- Ensure bot account has required permissions

### "FloodWaitError"
Telegram rate limit - bot will automatically wait and retry.

### "Session expired"
Delete `.session` file and re-run `auth.py`.

### Slow processing
Enable fast mode in `.env`:
```env
FAST_MODE=true
SKIP_PRODUCT_EXTRACTION=true
```

---

## 📜 License

MIT License - feel free to use and modify!

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

Made with ❤️ using Python and Telethon
