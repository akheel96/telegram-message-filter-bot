# Deployment Guide — Free Hosting for Telegram Bot

## Why Cloudflare Workers Won't Work Here

Cloudflare Workers is a **serverless edge runtime** designed to handle HTTP requests in milliseconds. This bot uses **Telethon**, which requires a **persistent, long-running TCP connection** to Telegram's MTProto servers. These two models are fundamentally incompatible:

| Requirement | Cloudflare Workers | This Bot |
|---|---|---|
| Execution model | Triggered per HTTP request, max 30s CPU | Always-on, event-driven |
| Persistent TCP connections | ❌ Not supported | ✅ Required |
| Long idle periods | ❌ Instance dies between requests | ✅ Waits for Telegram events |
| Free tier duration | 30s max CPU time per invocation | 24/7 continuous |

**Cloudflare Tunnel** is also not a solution — it lets you expose a local server to the internet, but you still need a machine running the Python process.

---

## Why Keep-Alive Pings Violated Render AUP

The old `bot.py` ran a web server and printed:
> "Ping `/health` every 14 minutes to prevent sleep"

Render's free Web Service plan intentionally sleeps instances after 15 minutes of inactivity. Ping-based keep-alive is explicitly prohibited under their **Bypass Access or Usage Restrictions** policy and is actively detected. This was the cause of the account suspension.

---

## Legitimate Idle-Time Alternatives on Render

If you want to stay on Render, the correct options are:

### Option 1 — Render Background Worker (Paid, ~$7/month)
Deploy with `type: worker` in `render.yaml` (already updated). Background Workers never sleep and have no HTTP server requirement. This is the proper solution on Render.

```yaml
# render.yaml
services:
  - type: worker   # ← never sleeps, no AUP violation
    plan: starter  # $7/month
```

### Option 2 — Free Platforms That Don't Sleep

The platforms below run **persistent background processes for free** with no keep-alive needed.

---

## Free Alternatives — Step-by-Step

### A. Railway (Recommended Free Option)

Railway offers $5/month free credits — enough for a lightweight bot indefinitely.

1. Sign up at https://railway.app
2. Click **New Project → Deploy from GitHub repo**
3. Select your repository
4. Railway auto-detects Python; set the start command:
   ```
   python bot.py
   ```
5. Go to **Variables** and add:
   ```
   API_ID=your_api_id
   API_HASH=your_api_hash
   SOURCE_CHANNEL_IDS=-100xxxxx,-100yyyyy
   DESTINATION_CHANNEL_ID=-100zzzzz
   SESSION_STRING=your_session_string
   FILTER_KEYWORDS=loot,deal,offer
   ```
6. Click **Deploy**. The service runs as a persistent worker with no sleep.

**Note:** The `Procfile` in this repo uses `worker:` which Railway respects automatically.

---

### B. Fly.io (Generous Free Tier)

Fly.io provides 3 free shared-CPU VMs with 256 MB RAM each.

1. Install the CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Sign up and log in:
   ```bash
   fly auth signup
   fly auth login
   ```
3. In your project folder, initialise the app:
   ```bash
   fly launch --name telegram-loot-bot --no-deploy
   ```
   - Select region closest to you
   - Say **No** to creating a Postgres database
   - Say **No** to creating a Redis database
4. Set secrets (environment variables):
   ```bash
   fly secrets set API_ID=your_api_id
   fly secrets set API_HASH=your_api_hash
   fly secrets set SOURCE_CHANNEL_IDS=-100xxxxx
   fly secrets set DESTINATION_CHANNEL_ID=-100zzzzz
   fly secrets set SESSION_STRING=your_session_string
   fly secrets set FILTER_KEYWORDS=loot,deal,offer
   ```
5. Edit the generated `fly.toml` to remove the `[[services]]` HTTP block (no port needed):
   ```toml
   [build]

   [env]
     LOG_LEVEL = "INFO"

   # Remove or comment out the [[services]] section entirely
   ```
6. Deploy:
   ```bash
   fly deploy
   ```
7. Check logs:
   ```bash
   fly logs
   ```

The app runs as a persistent background process. No HTTP server, no sleep.

---

### C. Oracle Cloud Always Free (Best Long-Term Free Option)

Oracle Always Free provides a **permanent free VM** (2 AMD cores, 1 GB RAM) that never expires or bills you.

1. Sign up at https://cloud.oracle.com (requires a credit card for verification, but it is never charged on the Always Free tier)
2. Create a **Compute Instance**:
   - Image: Ubuntu 22.04
   - Shape: VM.Standard.E2.1.Micro (Always Free)
3. SSH into your instance:
   ```bash
   ssh -i your_key.pem ubuntu@your_instance_ip
   ```
4. Install Python and Git:
   ```bash
   sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
   ```
5. Clone your repo and install dependencies:
   ```bash
   git clone https://github.com/youruser/telegram-loot-bot.git
   cd telegram-loot-bot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
6. Create a `.env` file:
   ```bash
   cat > .env << 'EOF'
   API_ID=your_api_id
   API_HASH=your_api_hash
   SOURCE_CHANNEL_IDS=-100xxxxx
   DESTINATION_CHANNEL_ID=-100zzzzz
   SESSION_STRING=your_session_string
   FILTER_KEYWORDS=loot,deal,offer
   EOF
   ```
7. Run the bot as a systemd service so it auto-restarts:
   ```bash
   sudo nano /etc/systemd/system/lootbot.service
   ```
   Paste:
   ```ini
   [Unit]
   Description=Telegram Loot Filter Bot
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/telegram-loot-bot
   EnvironmentFile=/home/ubuntu/telegram-loot-bot/.env
   ExecStart=/home/ubuntu/telegram-loot-bot/venv/bin/python bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
   Then enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable lootbot
   sudo systemctl start lootbot
   sudo systemctl status lootbot
   ```
8. View live logs:
   ```bash
   sudo journalctl -u lootbot -f
   ```

---

### D. Koyeb (Free Plan, No Sleep on Workers)

1. Sign up at https://www.koyeb.com
2. Click **Create App → GitHub**
3. Select your repository
4. Set **Run command**: `python bot.py`
5. Add environment variables in the dashboard (same as above)
6. Set **Instance type**: Free
7. Deploy — Koyeb's free tier does not sleep persistent worker deployments

---

## Comparison Table

| Platform | Free Tier | Sleeps? | Setup Difficulty | Notes |
|---|---|---|---|---|
| Render (Worker) | ❌ Paid ($7/mo) | Never | Easy | Best if already on Render |
| Railway | $5/mo credits | Never | Easy | Best free option |
| Fly.io | 3 VMs free | Never | Medium | Very reliable |
| Oracle Cloud | Always Free VM | Never | Hard | Best long-term free |
| Koyeb | 1 service free | Never | Easy | Simple dashboard |
| Render (Web Free) | ✅ Free | After 15 min | Easy | **Violates AUP** if bypassed |

---

## Generating a SESSION_STRING

All cloud platforms above use `SESSION_STRING` instead of a `.session` file. Generate it once locally:

```bash
python generate_string_session.py
```

Copy the printed string and paste it as the `SESSION_STRING` environment variable on your chosen platform.
