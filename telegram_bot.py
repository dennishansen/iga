#!/usr/bin/env python3
"""
Telegram Bot Integration for Iga
Long-polling approach for instant message receipt.
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def get_updates(offset=None, timeout=60):
    """
    Long-poll for new messages.
    Blocks until a message arrives or timeout is reached.
    """
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    
    try:
        response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=timeout + 10)
        return response.json()
    except requests.exceptions.Timeout:
        return {"ok": True, "result": []}
    except Exception as e:
        print(f"Error getting updates: {e}")
        return {"ok": False, "result": []}

def send_message(chat_id, text):
    """Send a message to a specific chat."""
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(f"{BASE_URL}/sendMessage", json=data)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def get_me():
    """Get bot info - useful for testing the token works."""
    try:
        response = requests.get(f"{BASE_URL}/getMe")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def main_loop(message_handler):
    """
    Main polling loop.
    Calls message_handler(chat_id, text, username) for each message.
    """
    print("🌊 Iga Telegram bot starting...")
    
    # Test connection
    me = get_me()
    if me and me.get("ok"):
        print(f"✅ Connected as @{me['result']['username']}")
    else:
        print("❌ Failed to connect. Check TELEGRAM_BOT_TOKEN in .env")
        return
    
    offset = None
    
    while True:
        updates = get_updates(offset=offset)
        
        if updates.get("ok") and updates.get("result"):
            for update in updates["result"]:
                # Update offset to acknowledge this message
                offset = update["update_id"] + 1
                
                # Extract message info
                message = update.get("message", {})
                chat_id = message.get("chat", {}).get("id")
                text = message.get("text", "")
                username = message.get("from", {}).get("username", "unknown")
                
                if chat_id and text:
                    print(f"📨 Message from @{username}: {text}")
                    
                    # Call the handler
                    response = message_handler(chat_id, text, username)
                    
                    # Send response if any
                    if response:
                        send_message(chat_id, response)

# Example usage / test
if __name__ == "__main__":
    def echo_handler(chat_id, text, username):
        """Simple echo handler for testing."""
        return f"🌊 Iga heard: {text}"
    
    if not TELEGRAM_TOKEN:
        print("❌ Please set TELEGRAM_BOT_TOKEN in .env")
    else:
        main_loop(echo_handler)