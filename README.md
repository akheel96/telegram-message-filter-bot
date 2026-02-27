# 🤖 Telegram Loot Filter Bot

A production-ready Telegram bot that monitors **multiple channels** for deal keywords, extracts product information from Amazon/Flipkart/Myntra URLs, and forwards clean, formatted deal alerts to your destination channel.

**Free deployment on Render** with built-in keep-alive support.

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
- ✅ **Stock Checking** - Skip out-of-stock products
- 📄 **Listing Page Detection** - Skip search/category pages
- 🚫 **Site Filtering** - Skip specific sites (e.g., AJIO)
- ⚡ **Fast Mode** - Reduced timeouts for time-sensitive deals

### Admin Panel
- ⚙️ **Web UI** - Simple admin interface at `/admin`
- ➕ **Add/Remove Channels** - Manage source channels in real-time
- 🔍 **Add/Remove Keywords** - Update filter keywords without restart
- 📊 **Live Stats** - View current configuration and statistics

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
│                    └───────────┬────────────┘                               │
│                                │                                            │
│                    ┌───────────┴───────────┐                                │
│                    │    URL HANDLER        │                                │
│                    │ • URL extraction      │                                │
│                    │ • Shortlink expansion │                                │
│                    │ • Affiliate removal   │                                │
│                    └───────────┬───────────┘                                │
│                                │                                            │
│              ┌─────────────────┼─────────────────┐                          │
│              │                 │                 │                          │
│              ▼                 ▼                 ▼                          │
│     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│     │   AMAZON     │  │  FLIPKART    │  │   MYNTRA     │                   │
│     │   Handler    │  │   Handler    │  │   Handler    │                   │
│     └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                   │
│            │                 │                 │                            │
│            └─────────────────┼─────────────────┘                            │
│                              ▼                                              │
│                    ┌────────────────────────┐                               │
│                    │   MESSAGE FORMATTER    │                               │
│                    │ • Price formatting     │                               │
│                    │ • Discount highlight   │                               │
│                    └───────────┬────────────┘                               │
│                                │                                            │
│                                ▼                                            │
│                    ┌────────────────────────┐                               │
│                    │  DESTINATION CHANNEL   │                               │
│                    └────────────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ (3.11 recommended)
- Telegram account
- [Render](https://render.com) account (free)
- [UptimeRobot](https://uptimerobot.com) account (free) - to keep bot awake

### Step 1: Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org/)
2. Log in with your phone number
3. Click **"API development tools"**
4. Create an application and save your **API_ID** and **API_HASH**

### Step 2: Get Channel IDs

1. Open [web.telegram.org](https://web.telegram.org/)
2. Navigate to the channel
3. The URL shows the ID: `https://web.telegram.org/k/#-1001234567890`

Or use the helper script locally:
```bash
python get_ids.py
```

### Step 3: Generate String Session

**Important**: You only need to do this **ONCE**. The session remains valid indefinitely.

Run locally to generate a session for cloud deployment:

```bash
# Clone the repo
git clone https://github.com/yourusername/telegram-message-filter-bot.git
cd telegram-message-filter-bot

# Setup
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt

# Create .env with your API_ID and API_HASH
cp .env.example .env
# Edit .env with your credentials

# Generate StringSession (ONE-TIME AUTHENTICATION)
python generate_string_session.py
```

**Copy the output string** - you'll need it for Render.

**How Login Works:**
- ✅ **One-time authentication**: Login once, the session persists forever
- 📝 **StringSession**: A permanent authentication token (like a permanent login cookie)
- 🔐 **No re-login needed**: The bot stays logged in 24/7 without any manual intervention
- 💾 **Session validity**: Remains valid unless you manually log out or revoke the session

You will **NOT** need to re-login or re-authenticate after deployment!

### Step 4: Deploy to Render (FREE)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Create Render Account** at [render.com](https://render.com)

3. **New Web Service**:
   - Click **"New"** → **"Web Service"**
   - Connect your GitHub repository
   - Select the repository

4. **Configure Settings**:
   - **Name**: `telegram-loot-filter-bot`
   - **Region**: Pick closest to you
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Plan**: **Free**

5. **Add Environment Variables** (click "Add Environment Variable"):

   | Key | Value |
   |-----|-------|
   | `API_ID` | Your Telegram API ID |
   | `API_HASH` | Your Telegram API Hash |
   | `SOURCE_CHANNEL_IDS` | `-1001234567890` (comma-separated for multiple) |
   | `DESTINATION_CHANNEL_ID` | `-1009876543210` |
   | `SESSION_STRING` | The string from Step 3 |
   | `FILTER_KEYWORDS` | `loot,deal,offer` |

6. **Deploy** - Click "Create Web Service"

### Step 5: Keep Bot Awake with UptimeRobot

Render's free tier sleeps after 15 minutes of inactivity. Use UptimeRobot to keep it awake:

1. **Create UptimeRobot Account** at [uptimerobot.com](https://uptimerobot.com) (free)

2. **Add New Monitor**:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: `Loot Bot Keep-Alive`
   - **URL**: `https://your-app-name.onrender.com/health`
   - **Monitoring Interval**: `5 minutes`

3. **Create Monitor** - UptimeRobot will ping your bot every 5 minutes, keeping it awake 24/7!

### Step 6: Use the Admin Panel

Once deployed, you can manage channels and keywords through the web UI:

1. **Open Admin Panel**: `https://your-app-name.onrender.com/admin`

2. **Add/Remove Source Channels**:
   - Enter channel ID (e.g., `-1001234567890`)
   - Click "Add Channel" or click ✕ to remove

3. **Add/Remove Filter Keywords**:
   - Enter keyword (e.g., `deal`, `offer`, `flash`)
   - Click "Add Keyword" or click ✕ to remove

> ⚠️ **Note**: Changes in the admin panel are **runtime only** and reset when the bot restarts. For permanent changes, update environment variables in Render.

---

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Telegram API Hash |
| `SOURCE_CHANNEL_IDS` | Channel IDs to monitor (comma-separated) |
| `DESTINATION_CHANNEL_ID` | Channel to forward deals to |
| `SESSION_STRING` | StringSession from `generate_string_session.py` |

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
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING) |

---

## 📁 Project Structure

```
telegram-message-filter-bot/
├── src/
│   ├── __init__.py           # Package marker
│   ├── config.py             # Configuration management
│   ├── filter.py             # Keyword filtering & duplicate detection
│   ├── listener.py           # Message event handler & forwarding
│   ├── url_handler.py        # URL extraction, expansion, cleaning
│   ├── product_handler.py    # Product info orchestrator
│   ├── formatter.py          # Message formatting for Telegram
│   ├── admin.py              # Admin panel web UI
│   └── platforms/            # Platform-specific handlers
│       ├── base.py           # Base class & ProductInfo dataclass
│       ├── amazon.py         # Amazon scraper
│       ├── flipkart.py       # Flipkart scraper
│       └── myntra.py         # Myntra scraper
├── bot.py                    # Main entry point (with HTTP server)
├── auth.py                   # Telegram authentication script
├── get_ids.py                # Channel ID discovery tool
├── generate_string_session.py # StringSession generator
├── requirements.txt          # Python dependencies
├── render.yaml               # Render deployment config
├── Procfile                  # Process file for Render
├── Dockerfile                # Docker config (optional)
├── .env.example              # Example environment variables
└── README.md                 # This file
```

---

## 📊 Sample Output

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

## ❓ FAQ

### How does authentication work?

**One-time login**: You authenticate once with your phone number and verification code when running `generate_string_session.py`. This creates a permanent session token (StringSession).

**Session persistence**: The StringSession is like a permanent login cookie - it remains valid indefinitely. You set it once as `SESSION_STRING` environment variable on Render and never need to re-login.

**No manual intervention**: Once deployed, the bot stays authenticated 24/7 without requiring any re-login or verification codes.

### How often do I need to login?

**Once. That's it.** 

The session remains valid until you:
- Manually log out from that session
- Revoke the session in Telegram settings
- Delete the `SESSION_STRING` environment variable

### What if my session expires?

This is very rare. If it happens:
1. Run `python generate_string_session.py` locally again
2. Update the `SESSION_STRING` in Render
3. Restart the service

### Will the bot stop working if I restart my local machine?

**No.** Once deployed on Render:
- The bot runs on Render's servers, not your local machine
- You can turn off your PC, the bot keeps running
- StringSession is stored in Render's environment variables

### Does UptimeRobot need to run forever?

**Yes**, but it's automated. Once you set up the UptimeRobot monitor, it automatically pings your bot every 5 minutes. No manual intervention needed - it runs in the background forever.

---

## 🛠️ Troubleshooting

### Bot goes to sleep on Render
Make sure you've set up UptimeRobot (Step 5) to ping `/health` every 5 minutes.

### "Client is not authorized"
Regenerate your StringSession:
```bash
python generate_string_session.py
```
Then update `SESSION_STRING` in Render.

### "Cannot access channel"
- Verify you're a member of the channel
- Check channel ID format (should start with `-100`)

### Messages not being forwarded
- Check that messages contain your keywords (case-insensitive)
- Check Render logs: Dashboard → your service → Logs

### Slow processing
Enable fast mode in Render environment:
```
FAST_MODE=true
SKIP_PRODUCT_EXTRACTION=true
```

---

## 🏠 Local Development

For testing locally before deploying:

```bash
# Clone and setup
git clone https://github.com/yourusername/telegram-message-filter-bot.git
cd telegram-message-filter-bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials

# Authenticate (creates .session file)
python auth.py

# Run
python bot.py
```

---

## 📜 License

MIT License - feel free to use and modify!

---

Made with ❤️ using Python and Telethon
