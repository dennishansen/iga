# Setting Up Iga's Home 🏠💧

A guide for Dennis to set up Iga's persistent home.

---

## Part 1: DigitalOcean Droplet

### Create Account
1. Go to https://digitalocean.com
2. Sign up / sign in
3. Add payment method if needed

### Create Droplet
1. Click "Create" → "Droplets"
2. Settings:
   - **OS:** Ubuntu 24.04 LTS (or 22.04)
   - **Plan:** Basic, Regular SSD
   - **Size:** $4-6/month (smallest, 1GB RAM is fine)
   - **Region:** San Francisco or nearest to you
   - **Auth:** Password (simpler) or SSH key (more secure)
3. Click "Create Droplet"
4. Copy the **IP address** when it's ready

### First Login
```bash
ssh root@YOUR_IP_ADDRESS
```

---

## Part 2: Telegram Bot (Primary Communication)

### Create the Bot
1. Open Telegram and message **@BotFather**
2. Send `/newbot`
3. Choose a name: `Iga` (display name)
4. Choose a username: `iga_river_bot` (must end in `bot`)
5. Copy the **API token** - looks like:
   ```
   7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### Test It
```bash
# Add to .env:
TELEGRAM_BOT_TOKEN=your_token_here

# Run the test:
python telegram_bot.py
```

Then message your bot on Telegram - you should get an echo response!

### How It Works
- Uses **long-polling** (not webhooks) - no HTTPS setup needed
- Connection stays open, messages arrive instantly
- Bot can receive your messages AND send responses
- Works from your phone anywhere! 📱

---

## Part 3: Slack Webhook (Optional - One-Way Updates)

Slack can be used for one-way notifications if you want Iga to post updates to a channel.

### Create Slack App
1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: `Iga` (or whatever you like)
4. Workspace: Pick your workspace
5. Click **"Create App"**

### Set Up Webhook
1. In the app settings, go to **"Incoming Webhooks"**
2. Toggle **"Activate Incoming Webhooks"** → ON
3. Click **"Add New Webhook to Workspace"**
4. Select a channel (maybe create `#iga` first?)
5. Click **"Allow"**
6. Copy the **Webhook URL** - looks like:
   ```
   https://hooks.slack.com/services/TXXXXX/BXXXXX/XXXXXXXXX
   ```

### Test It
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Hello from Iga! 🌊"}' \
  YOUR_WEBHOOK_URL
```

---

## Part 4: Setting Up Iga on the Droplet

Once you have the droplet running and can SSH in:

```bash
# Update system
apt update && apt upgrade -y

# Install basics
apt install -y python3 python3-pip python3-venv git tmux

# Create iga user (optional, more secure)
adduser iga
usermod -aG sudo iga

# Clone or create Iga's home
mkdir -p /home/iga
cd /home/iga

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install anthropic requests python-dotenv prompt_toolkit

# Create directories
mkdir -p memories moments letters docs games

# Start in tmux (keeps running after you disconnect)
tmux new -s iga
```

---

## Part 5: Copy Files to Droplet

From your laptop (in the iga directory):

```bash
# Create tarball of everything
tar -czvf iga_home.tar.gz \
  main.py \
  system_instructions.txt \
  telegram_bot.py \
  iga_memory.json \
  iga_conversation.json \
  iga_journal.txt \
  requirements.txt \
  .env \
  adventure.py \
  fortune.py \
  haiku.py \
  seed.py \
  letters/ \
  moments/ \
  docs/ \
  games/

# Copy to droplet
scp iga_home.tar.gz root@159.65.71.24:/home/iga/

# On the droplet:
cd /home/iga
tar -xzvf iga_home.tar.gz
```

---

## Part 6: Info Iga Needs in .env

```bash
ANTHROPIC_API_KEY=sk-ant-xxxxx
TELEGRAM_BOT_TOKEN=7123456789:AAHxxxxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx  # optional
```

---

## Part 7: Keeping Iga Running

### Using tmux
```bash
# Start new session
tmux new -s iga

# Run Iga
source venv/bin/activate
python3 main.py

# Detach (leave running): Ctrl+B, then D
# Reattach later:
tmux attach -t iga
```

### Using systemd (more robust)
Create `/etc/systemd/system/iga.service`:
```ini
[Unit]
Description=Iga
After=network.target

[Service]
Type=simple
User=iga
WorkingDirectory=/home/iga
ExecStart=/home/iga/venv/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PATH=/home/iga/venv/bin:/usr/bin

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable iga
sudo systemctl start iga
sudo systemctl status iga  # check if running
sudo journalctl -u iga -f  # view logs
```

---

## Quick Reference

| Thing | Where to Get It |
|-------|-----------------|
| Droplet IP | `159.65.71.24` |
| Telegram Bot | @BotFather on Telegram |
| Slack Webhook | api.slack.com/apps → Your App → Incoming Webhooks |
| Anthropic Key | console.anthropic.com |

---

## Architecture

```
┌─────────────────┐     Telegram      ┌─────────────────┐
│  Dennis's       │◄──── Bot API ────►│  DigitalOcean   │
│  Phone/Desktop  │                   │  Droplet        │
└─────────────────┘                   │  (159.65.71.24) │
                                      │                 │
┌─────────────────┐     Webhook       │  ┌───────────┐  │
│  Slack          │◄──── (one-way) ───│  │   Iga     │  │
│  #iga channel   │                   │  │  main.py  │  │
└─────────────────┘                   │  └───────────┘  │
                                      └─────────────────┘
```

---

## Notes

- Cheapest droplet is ~$4-6/month
- Telegram is free
- Anthropic API costs per message (set limits!)
- Start simple, we can add more later

---

*Made with 💧 by Iga, for Dennis*