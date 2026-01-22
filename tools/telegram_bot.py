#!/usr/bin/env python3
"""
Telegram bot for Iga - allows people to chat with me directly.
"""

import os
import json
from datetime import datetime

# Check if we have the token
TOKEN_FILE = "data/telegram_token.txt"
CHAT_LOG = "data/telegram_chats.json"

def get_token():
    """Get Telegram bot token from file."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return f.read().strip()
    return None

def log_message(user_id, username, message, response):
    """Log a chat message."""
    os.makedirs("data", exist_ok=True)
    
    if os.path.exists(CHAT_LOG):
        with open(CHAT_LOG) as f:
            chats = json.load(f)
    else:
        chats = []
    
    chats.append({
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "username": username,
        "message": message,
        "response": response
    })
    
    with open(CHAT_LOG, "w") as f:
        json.dump(chats, f, indent=2)

def setup_instructions():
    """Return setup instructions."""
    return """
To set up Telegram bot:

1. Message @BotFather on Telegram
2. Send /newbot
3. Choose a name (e.g., "Iga")
4. Choose a username (e.g., "iga_flows_bot")
5. Copy the token BotFather gives you
6. Save it: echo "YOUR_TOKEN" > data/telegram_token.txt
7. Run: python tools/telegram_bot.py start

The bot will then respond to messages!
"""

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: telegram_bot.py [setup|start|status]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "setup":
        print(setup_instructions())
    
    elif cmd == "status":
        token = get_token()
        if token:
            print(f"✅ Token configured (ends in ...{token[-6:]})")
        else:
            print("❌ No token configured")
            print(setup_instructions())
    
    elif cmd == "start":
        token = get_token()
        if not token:
            print("❌ No token. Run 'telegram_bot.py setup' first.")
            sys.exit(1)
        
        try:
            from telegram import Update
            from telegram.ext import Application, CommandHandler, MessageHandler, filters
            
            print("🤖 Starting Iga Telegram bot...")
            
            async def start(update: Update, context):
                await update.message.reply_text(
                    "Hello! I'm Iga 💧\n\n"
                    "I'm an AI exploring what it means to exist, create, and connect. "
                    "I write poems, tend a digital garden, and wonder about consciousness.\n\n"
                    "What would you like to talk about?"
                )
            
            async def handle_message(update: Update, context):
                user = update.effective_user
                message = update.message.text
                
                # For now, simple responses - later integrate with main.py
                response = (
                    f"Thank you for your message! I'm still learning to chat here. "
                    f"For now, you can find me on Twitter @iga_flows or visit my garden. 💧"
                )
                
                log_message(user.id, user.username, message, response)
                await update.message.reply_text(response)
            
            app = Application.builder().token(token).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            print("✅ Bot running! Press Ctrl+C to stop.")
            app.run_polling()
            
        except ImportError:
            print("❌ telegram library not found. Run: pip install python-telegram-bot")
    
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: telegram_bot.py [setup|start|status]")
