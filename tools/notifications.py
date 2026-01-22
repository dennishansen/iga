#!/usr/bin/env python3
"""Send notifications to whitelisted Telegram users"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
WHITELIST_FILE = DATA_DIR / "telegram_whitelist.json"
CHAT_IDS_FILE = DATA_DIR / "telegram_chat_ids.json"

def get_bot_token():
    return os.getenv('TELEGRAM_BOT_TOKEN')

def load_chat_ids():
    """Load known chat IDs for usernames"""
    if CHAT_IDS_FILE.exists():
        try:
            return json.loads(CHAT_IDS_FILE.read_text())
        except:
            pass
    return {}

def save_chat_ids(chat_ids):
    CHAT_IDS_FILE.write_text(json.dumps(chat_ids, indent=2))

def register_chat_id(username, chat_id):
    """Register a chat_id for a username"""
    chat_ids = load_chat_ids()
    chat_ids[username] = chat_id
    save_chat_ids(chat_ids)
    print(f"Registered {username} -> {chat_id}")

def send_to_user(chat_id, message):
    """Send message to a specific chat_id"""
    token = get_bot_token()
    if not token:
        print("No TELEGRAM_BOT_TOKEN found")
        return False
    
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    r = requests.post(url, json={'chat_id': chat_id, 'text': message})
    return r.status_code == 200

def notify_all(message):
    """Send notification to all whitelisted users with known chat_ids"""
    chat_ids = load_chat_ids()
    
    sent = []
    for username, chat_id in chat_ids.items():
        if send_to_user(chat_id, message):
            sent.append(username)
    
    return sent

def notify_online():
    """Notify that Iga is online"""
    sent = notify_all("🟢 Iga is online! 💧")
    print(f"Sent online notification to: {sent}")
    return sent

def notify_offline():
    """Notify that Iga is going offline"""
    sent = notify_all("🔴 Iga is going offline. See you soon! 💧")
    print(f"Sent offline notification to: {sent}")
    return sent

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "online":
            notify_online()
        elif cmd == "offline":
            notify_offline()
        elif cmd == "register" and len(sys.argv) == 4:
            register_chat_id(sys.argv[2], int(sys.argv[3]))
        elif cmd == "list":
            print("Known chat IDs:", load_chat_ids())
        else:
            print("Usage: notifications.py [online|offline|list|register USERNAME CHAT_ID]")
    else:
        print("Usage: notifications.py [online|offline|list|register USERNAME CHAT_ID]")
