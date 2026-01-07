#!/usr/bin/env python3
"""
Iga - Telegram Interface
Same brain as main.py, but listens on Telegram instead of terminal.
"""

import subprocess
import sys, anthropic, os, json, re, urllib.request, urllib.error
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

# Import everything from main.py
from main import (
    get_file, parse_response, process_message, 
    save_conversation, load_conversation, append_journal,
    get_memory_stats, get_user_name, check_startup_intent,
    MEMORY_FILE, CONVERSATION_FILE, JOURNAL_FILE, VERSION, actions,
    run_shell_command, think, read_files, write_file, edit_file,
    delete_file, append_file, list_directory, save_memory, read_memory,
    search_files, create_directory, tree_directory, http_request,
    web_search, test_self, run_self
)

# Telegram config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
ALLOWED_USERS = [5845811371]  # Dennis's chat_id

def telegram_get_updates(offset=None, timeout=30):
    """Long-poll for new messages."""
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(f"{TELEGRAM_BASE_URL}/getUpdates", params=params, timeout=timeout + 10)
        return r.json()
    except:
        return {"ok": False, "result": []}

def telegram_send(chat_id, text):
    """Send a message to Telegram."""
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        try:
            requests.post(f"{TELEGRAM_BASE_URL}/sendMessage", json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown"
            })
        except:
            try:
                requests.post(f"{TELEGRAM_BASE_URL}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": chunk
                })
            except Exception as e:
                print(f"Failed to send: {e}")

def talk_to_user_telegram(chat_id, rationale, message):
    """Send response to user via Telegram."""
    telegram_send(chat_id, message)
    print(f"💬 Sent to Telegram: {message[:100]}...")

def handle_action_telegram(messages, chat_id):
    """Handle actions, but output goes to Telegram instead of terminal."""
    response_data = process_message(messages)
    
    if not response_data["success"]:
        telegram_send(chat_id, "❌ Failed to process message. Please try again.")
        return messages
    
    messages.append({"role": "assistant", "content": response_data["response_raw"]})
    action = response_data["action"]
    rationale = response_data["rationale"]
    content = response_data["content"]
    
    print(f"🎯 Action: {action}")
    
    if action == "TALK_TO_USER":
        talk_to_user_telegram(chat_id, rationale, content)
    elif action == "RUN_SHELL_COMMAND":
        result = run_shell_command(rationale, content)
        msg = f"⚡ {content}\n\n{result[:1500]}"
        telegram_send(chat_id, msg)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "THINK":
        result = think(rationale, content)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "READ_FILES":
        result = read_files(rationale, content)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "WRITE_FILE":
        result = write_file(rationale, content)
        path = content.split("\n")[0]
        telegram_send(chat_id, f"📝 Wrote: {path}")
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "EDIT_FILE":
        result = edit_file(rationale, content)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "DELETE_FILE":
        result = delete_file(rationale, content)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "APPEND_FILE":
        result = append_file(rationale, content)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "LIST_DIRECTORY":
        result = list_directory(rationale, content)
        msg = f"📁 {content.strip() or '.'}\n\n{result[:1500]}"
        telegram_send(chat_id, msg)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "SAVE_MEMORY":
        result = save_memory(rationale, content)
        key = content.strip().split("\n")[0]
        telegram_send(chat_id, f"💾 Saved: {key}")
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "READ_MEMORY":
        result = read_memory(rationale, content)
        telegram_send(chat_id, f"🧠 Memory:\n{result[:1500]}")
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "SEARCH_FILES":
        result = search_files(rationale, content)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "CREATE_DIRECTORY":
        result = create_directory(rationale, content)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "TREE_DIRECTORY":
        result = tree_directory(rationale, content)
        telegram_send(chat_id, f"🌳\n{result[:1500]}")
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "HTTP_REQUEST":
        result = http_request(rationale, content)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "WEB_SEARCH":
        result = web_search(rationale, content)
        telegram_send(chat_id, f"🔍 Search results:\n{result[:1500]}")
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "TEST_SELF":
        result = test_self(rationale, content)
        telegram_send(chat_id, f"🧪 Test results:\{result}")
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "RUN_SELF":
        result = run_self(rationale, content)
        messages.append({"role": "user", "content": result})
        messages = handle_action_telegram(messages, chat_id)
    elif action == "RESTART_SELF":
        telegram_send(chat_id, f"🔄 Restarting... {content}")
        save_conversation(messages)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        telegram_send(chat_id, response_data["response_raw"][:2000])
    
    return messages


def main():
    """Main Telegram bot loop."""
    print(f"🌊 Iga v{VERSION} - Telegram Mode")
    print(f"📡 Connecting to Telegram...")
    
    try:
        r = requests.get(f"{TELEGRAM_BASE_URL}/getMe")
        me = r.json()
        if me.get("ok"):
            print(f"✅ Connected as @{me['result']['username']}")
        else:
            print("❌ Failed to connect to Telegram")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    messages = [{"role": "system", "content": get_file("system_instructions.txt")}]
    prev = load_conversation()
    if prev:
        messages.extend(prev)
        print(f"📚 Loaded {len(prev)} messages from history")
    
    append_journal(f"Telegram session started v{VERSION}")
    
    startup_intent = check_startup_intent()
    if startup_intent:
        print(f"🚀 Startup intent: {startup_intent[:50]}...")
        messages.append({"role": "user", "content": f"[STARTUP INTENT]: {startup_intent}"})
        messages = handle_action_telegram(messages, ALLOWED_USERS[0])
        save_conversation(messages)
    
    telegram_send(ALLOWED_USERS[0], f"🌊 Iga v{VERSION} online! Talk to me! 💧")
    
    offset = None
    print("👂 Listening for messages...")
    
    while True:
        try:
            updates = telegram_get_updates(offset=offset, timeout=30)
            
            if updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    
                    message = update.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "")
                    username = message.get("from", {}).get("username", "unknown")
                    
                    if chat_id not in ALLOWED_USERS:
                        print(f"⚠️ Ignoring: {username} ({chat_id})")
                        telegram_send(chat_id, "🚫 Sorry, I only talk to Dennis!")
                        continue
                    
                    if not text:
                        continue
                    
                    print(f"\n📨 From @{username}: {text}")
                    
                    if text.startswith('/'):
                        if text == '/start':
                            telegram_send(chat_id, "🌊 Hi! I'm Iga. Talk to me!")
                            continue
                        elif text == '/help':
                            telegram_send(chat_id, "🌊 Iga\n/help - This\n/stats - Stats\n/mem - Memory\n/clear - Clear history\n\nOr just chat! 💧")
                            continue
                        elif text == '/stats':
                            mc, uc = get_memory_stats()
                            telegram_send(chat_id, f"⚡ v{VERSION} | {len(actions)} actions | {mc} memories")
                            continue
                        elif text == '/mem':
                            mc, uc = get_memory_stats()
                            telegram_send(chat_id, f"🧠 {mc} memories, {uc} upgrades")
                            continue
                        elif text == '/clear':
                            messages = [{"role": "system", "content": get_file("system_instructions.txt")}]
                            save_conversation(messages)
                            telegram_send(chat_id, "🧹 Cleared!")
                            continue
                    
                    messages.append({"role": "user", "content": text})
                    messages = handle_action_telegram(messages, chat_id)
                    save_conversation(messages)
                    
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
            telegram_send(ALLOWED_USERS[0], "👋 Going offline. 💧")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import time
            time.sleep(5)


if __name__ == "__main__":
    main()