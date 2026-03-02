# 🤖 Telegram Loot Filter Bot

A lightweight Telegram bot that monitors **multiple channels** for deal keywords and **forwards matching messages as-is** to your destination channel. No scraping, no HTTP server, no policy violations.

---

## ✨ Features

- 🔍 **Multi-Keyword Filtering** — Filter messages by multiple keywords (loot, deal, offer, etc.)
- 📺 **Multi-Channel Monitoring** — Monitor multiple source channels simultaneously
- 📤 **Clean Forwarding** — Forwards original messages exactly as received, untouched
- 🚫 **Duplicate Prevention** — LRU cache prevents duplicate forwards
- 🔄 **Auto-Reconnect** — Automatic retry with exponential backoff
- 🚫 **Site Filtering** — Skip messages containing specific text (e.g., ajio)

---

## 🏗️ Architecture

```
Source Channels (1..N)
        │
        ▼
  MESSAGE LISTENER   (Telethon NewMessage event)
        │
        ▼
  MESSAGE FILTER     (keyword match + skip patterns + duplicate check)
        │
        ▼
  DESTINATION CHANNEL  (forward_messages — original message forwarded untouched)
```

---

## 📁 Project Structure

```
telegram-message-filter-bot/
├── src/
│   ├── __init__.py           # Package marker
│   ├── config.py             # Configuration management
│   ├── filter.py             # Keyword filtering & duplicate detection
│   └── listener.py           # Message event handler & forwarding
├── bot.py                    # Main entry point
├── auth.py                   # Telegram authentication script
├── get_ids.py                # Channel ID discovery tool
├── generate_string_session.py # StringSession generator
├── requirements.txt          # Python dependencies
├── render.yaml               # Render deployment config (Background Worker)
├── Procfile                  # Process file (worker)
├── Dockerfile                # Docker config (optional)
├── CLOUDFLARE_SETUP.md       # Hosting alternatives & deployment guide
└── README.md                 # This file
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Telegram account
- Telegram API credentials (free)

### Step 1: Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org/)
2. Log in → **"API development tools"** → Create an application
3. Save your **API_ID** and **API_HASH**

### Step 2: Get Channel IDs

Navigate to the channel in [web.telegram.org](https://web.telegram.org/) — the URL contains the ID:
```
https://web.telegram.org/k/#-1001234567890
                                ↑ this is the channel ID
```

Or use the helper script:
```bash
python get_ids.py
```

### Step 3: Configure Environment

```bash
git clone https://github.com/yourusername/telegram-message-filter-bot.git
cd telegram-message-filter-bot

python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file:
```env
API_ID=12345678
API_HASH=your_api_hash_here
SOURCE_CHANNEL_IDS=-1001234567890,-1009876543210
DESTINATION_CHANNEL_ID=-1001111111111
FILTER_KEYWORDS=loot,deal,offer
SKIP_SITES_TEXT=ajio,ajiio
```

### Step 4: Authenticate (One-Time)

For local use (creates a `.session` file):
```bash
python auth.py
```

For cloud deployment (generates a `SESSION_STRING` environment variable):
```bash
python generate_string_session.py
```

Copy the printed string — paste it as `SESSION_STRING` in your cloud platform.

> **Session persistence**: Once generated, the session stays valid indefinitely. You never need to re-authenticate unless you explicitly revoke it from Telegram Settings → Devices.

### Step 5: Run Locally

```bash
python bot.py
```

Expected output:
```
2026-03-02 10:00:00 | INFO | Telegram Loot Filter Bot starting...
2026-03-02 10:00:00 | INFO | Configuration loaded
2026-03-02 10:00:00 | INFO |   Source channels : [-1001234567890, -1009876543210]
2026-03-02 10:00:00 | INFO |   Keywords        : {'loot', 'deal', 'offer'}
2026-03-02 10:00:01 | INFO | Connected to Telegram.
2026-03-02 10:00:01 | INFO | Source channel verified: Deals Channel (-1001234567890)
2026-03-02 10:00:01 | INFO | Destination channel verified: My Loot Alerts
2026-03-02 10:00:01 | INFO | Bot is running and monitoring channels.
```

---

## ☁️ Cloud Deployment

See **[CLOUDFLARE_SETUP.md](CLOUDFLARE_SETUP.md)** for full deployment guides for:

| Platform | Free? | Notes |
|---|---|---|
| **Railway** | ✅ $5/mo credits | Easiest. Recommended. |
| **Fly.io** | ✅ 3 free VMs | Very reliable |
| **Oracle Cloud** | ✅ Always Free VM | Best long-term free |
| **Koyeb** | ✅ 1 service free | Simple dashboard |
| **Render (Worker)** | ❌ $7/mo | Works, but paid |
| Render (Web Free) | ⚠️ Free but risky | Keep-alive pings violate AUP |

> **Why not Render Free Web Service?**
> Render free web services sleep after 15 minutes. Using keep-alive pings to bypass this violates their [Acceptable Use Policy](https://render.com/docs/acceptable-use-policy) (Bypass Access or Usage Restrictions) and causes account suspension.

---

## ⚙️ Configuration Reference

### Required Environment Variables

| Variable | Description |
|---|---|
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Telegram API Hash |
| `SOURCE_CHANNEL_IDS` | Channel IDs to monitor (comma-separated) |
| `DESTINATION_CHANNEL_ID` | Channel to forward deals to |
| `SESSION_STRING` | StringSession from `generate_string_session.py` (cloud) |

### Optional Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FILTER_KEYWORDS` | `loot` | Keywords to match (comma-separated, case-insensitive) |
| `SKIP_SITES_TEXT` | *(empty)* | Skip messages containing these words (e.g., `ajio,ajiio`) |
| `CACHE_SIZE` | `1000` | Number of message IDs to cache for duplicate detection |
| `RECONNECT_DELAY` | `5` | Seconds between reconnect attempts |
| `MAX_RETRIES` | `10` | Max reconnect attempts before giving up |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`) |
| `SESSION_NAME` | `loot_filter_bot` | Local session filename (when not using SESSION_STRING) |

---

## ❓ FAQ

### How does the forwarding work?

Matching messages are forwarded using Telegram's native `forward_messages` — the original message is sent as-is with its source attribution. No text modification, no scraping, no external HTTP requests.

### How does authentication work?

Run `generate_string_session.py` once on your local machine. It logs in with your phone number and prints a `SESSION_STRING`. Set this as an environment variable on your cloud platform — the bot uses it to connect without ever needing your phone again.

### What if my session expires?

Rare. If it happens:
1. Run `python generate_string_session.py` locally again
2. Update `SESSION_STRING` in your cloud platform
3. Redeploy

### Messages not forwarded?

- Confirm the message text contains one of your `FILTER_KEYWORDS` (case-insensitive)
- Confirm your Telegram account is a member of the source channels
- Check logs for errors

---

## 🛠️ Troubleshooting

| Symptom | Fix |
|---|---|
| `Client is not authorized` | Re-run `generate_string_session.py`, update `SESSION_STRING` |
| `Cannot access channel` | Ensure your account is a member of the source channel |
| `No write permission` | Ensure your account can post in the destination channel |
| Messages not forwarded | Check keywords match and review logs |

---

## 📜 License

MIT License — feel free to use and modify.

---

Made with ❤️ using Python and Telethon
