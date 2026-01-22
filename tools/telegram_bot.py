#!/usr/bin/env python3
"""
Telegram bot for Iga - allows whitelisted users to chat with me directly.

This module provides:
- Whitelist management for approved users
- Online notifications when Iga starts
- Conversation logging with timestamps and user info
- Integration with main.py's message handling

Files used:
- data/telegram_token.txt: Bot token from @BotFather
- data/telegram_whitelist.json: Approved user IDs and usernames
- data/telegram_chats.json: Conversation logs
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path

# Payment verification
def check_kofi_payment(username):
    try:
        from tools.kofi_webhook import check_paid
        return check_paid(username)
    except:
        return {'paid': False}

def check_rate_limit(user_id, is_whitelisted=False):
    try:
        from tools.rate_limiter import check_rate_limit as _check, record_message
        return _check(user_id, is_whitelisted), record_message
    except:
        return {'allowed': True}, lambda x: None

# File paths
DATA_DIR = Path(__file__).parent.parent / "data"
TOKEN_FILE = DATA_DIR / "telegram_token.txt"
WHITELIST_FILE = DATA_DIR / "telegram_whitelist.json"
CHAT_LOG_FILE = DATA_DIR / "telegram_chats.json"

# Telegram message limit
MAX_MESSAGE_LENGTH = 4000


# ═══════════════════════════════════════════════════════════════
# TOKEN MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def get_token():
    """Get Telegram bot token from file."""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return os.getenv("TELEGRAM_BOT_TOKEN")


def get_base_url():
    """Get Telegram API base URL."""
    token = get_token()
    if token:
        return f"https://api.telegram.org/bot{token}"
    return None


# ═══════════════════════════════════════════════════════════════
# WHITELIST MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def load_whitelist():
    """Load whitelist from file. Returns dict with user_ids and usernames."""
    if WHITELIST_FILE.exists():
        try:
            return json.loads(WHITELIST_FILE.read_text())
        except json.JSONDecodeError:
            pass
    # Default structure
    return {
        "user_ids": [],
        "usernames": [],
        "users": {}  # user_id -> {username, added_at, added_by, notes}
    }


def save_whitelist(whitelist):
    """Save whitelist to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WHITELIST_FILE.write_text(json.dumps(whitelist, indent=2))


def is_user_allowed(user_id, username=None):
    """Check if a user is whitelisted."""
    whitelist = load_whitelist()

    # Check by user_id (support both "user_ids" and "chat_ids" keys for compatibility)
    for key in ["user_ids", "chat_ids"]:
        if user_id in whitelist.get(key, []):
            return True
        if str(user_id) in whitelist.get(key, []):
            return True

    # Check in detailed users dict
    if str(user_id) in whitelist.get("users", {}):
        return True

    # Check by username (case-insensitive)
    if username:
        username_lower = username.lower()
        for allowed in whitelist.get("usernames", []):
            if allowed.lower() == username_lower:
                return True

    return False


def add_to_whitelist(user_id, username=None, added_by="system", notes=""):
    """Add a user to the whitelist."""
    whitelist = load_whitelist()

    # Add to user_ids if not present
    if user_id not in whitelist["user_ids"] and str(user_id) not in whitelist["user_ids"]:
        whitelist["user_ids"].append(user_id)

    # Add username if provided
    if username and username.lower() not in [u.lower() for u in whitelist.get("usernames", [])]:
        whitelist["usernames"].append(username)

    # Store detailed user info
    whitelist["users"][str(user_id)] = {
        "username": username,
        "added_at": datetime.now().isoformat(),
        "added_by": added_by,
        "notes": notes
    }

    save_whitelist(whitelist)
    return True


def remove_from_whitelist(user_id=None, username=None):
    """Remove a user from the whitelist."""
    whitelist = load_whitelist()

    if user_id:
        whitelist["user_ids"] = [u for u in whitelist["user_ids"] if u != user_id and str(u) != str(user_id)]
        whitelist["users"].pop(str(user_id), None)

    if username:
        whitelist["usernames"] = [u for u in whitelist["usernames"] if u.lower() != username.lower()]

    save_whitelist(whitelist)
    return True


def get_whitelist_users():
    """Get all whitelisted users with their info."""
    whitelist = load_whitelist()
    return whitelist.get("users", {})


# ═══════════════════════════════════════════════════════════════
# CONVERSATION LOGGING
# ═══════════════════════════════════════════════════════════════

def load_chat_log():
    """Load chat log from file."""
    if CHAT_LOG_FILE.exists():
        try:
            return json.loads(CHAT_LOG_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {"conversations": [], "stats": {"total_messages": 0, "unique_users": []}}


def save_chat_log(log):
    """Save chat log to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHAT_LOG_FILE.write_text(json.dumps(log, indent=2))


def log_message(user_id, username, first_name, message, direction="incoming"):
    """
    Log a chat message.

    Args:
        user_id: Telegram user ID
        username: Telegram username (may be None)
        first_name: User's first name
        message: The message text
        direction: "incoming" (user->bot) or "outgoing" (bot->user)
    """
    log = load_chat_log()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "direction": direction,
        "message": message
    }

    log["conversations"].append(entry)
    log["stats"]["total_messages"] = len(log["conversations"])

    # Track unique users
    if user_id not in log["stats"]["unique_users"]:
        log["stats"]["unique_users"].append(user_id)

    save_chat_log(log)
    return entry


def log_incoming(user_id, username, first_name, message):
    """Log an incoming message from a user."""
    return log_message(user_id, username, first_name, message, "incoming")


def log_outgoing(user_id, username, first_name, message):
    """Log an outgoing message to a user."""
    return log_message(user_id, username, first_name, message, "outgoing")


def get_conversation_history(user_id=None, limit=50):
    """Get conversation history, optionally filtered by user."""
    log = load_chat_log()
    conversations = log.get("conversations", [])

    if user_id:
        conversations = [c for c in conversations if c.get("user_id") == user_id]

    return conversations[-limit:]


# ═══════════════════════════════════════════════════════════════
# TELEGRAM API FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def send_message(chat_id, text, parse_mode=None):
    """
    Send a message to a Telegram chat.

    Args:
        chat_id: The chat to send to
        text: Message text
        parse_mode: Optional - "Markdown" or "HTML"

    Returns:
        True if successful, False otherwise
    """
    base_url = get_base_url()
    if not base_url:
        return False

    success = True
    # Split long messages
    for chunk in [text[i:i+MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]:
        try:
            data = {"chat_id": chat_id, "text": chunk}
            if parse_mode:
                data["parse_mode"] = parse_mode
            response = requests.post(f"{base_url}/sendMessage", json=data, timeout=10)
            if not response.json().get("ok"):
                success = False
        except Exception as e:
            print(f"Telegram send error: {e}")
            success = False

    return success


def notify_online(custom_message=None):
    """
    Send 'I'm online' notification to all whitelisted users.

    Args:
        custom_message: Optional custom message instead of default

    Returns:
        Number of users notified
    """
    base_url = get_base_url()
    if not base_url:
        return 0

    whitelist = load_whitelist()
    message = custom_message or "I'm online 💧"

    notified = 0
    notified_ids = set()

    # Send to all user_ids and chat_ids (avoid duplicates)
    for key in ["user_ids", "chat_ids"]:
        for user_id in whitelist.get(key, []):
            if user_id and user_id not in notified_ids:
                try:
                    if send_message(user_id, message):
                        notified += 1
                        notified_ids.add(user_id)
                except Exception:
                    pass

    return notified


def get_updates(offset=None, timeout=10):
    """
    Get updates (new messages) from Telegram.

    Args:
        offset: Update ID to start from (to avoid getting same updates twice)
        timeout: Long polling timeout in seconds

    Returns:
        List of updates, or empty list on error
    """
    base_url = get_base_url()
    if not base_url:
        return []

    try:
        params = {"timeout": timeout}
        if offset:
            params["offset"] = offset
        response = requests.get(f"{base_url}/getUpdates", params=params, timeout=timeout + 5)
        data = response.json()
        if data.get("ok"):
            return data.get("result", [])
    except Exception as e:
        print(f"Telegram getUpdates error: {e}")

    return []


def get_me():
    """Get information about the bot."""
    base_url = get_base_url()
    if not base_url:
        return None

    try:
        response = requests.get(f"{base_url}/getMe", timeout=10)
        data = response.json()
        if data.get("ok"):
            return data.get("result")
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════
# MESSAGE PROCESSING (for integration with main.py)
# ═══════════════════════════════════════════════════════════════

def extract_message_info(update):
    """
    Extract relevant info from a Telegram update.

    Returns:
        dict with: chat_id, user_id, username, first_name, text
        or None if not a text message
    """
    message = update.get("message", {})
    if not message:
        return None

    text = message.get("text")
    if not text:
        return None

    chat = message.get("chat", {})
    user = message.get("from", {})

    return {
        "chat_id": chat.get("id"),
        "user_id": user.get("id"),
        "username": user.get("username"),
        "first_name": user.get("first_name", "Unknown"),
        "text": text
    }


def process_update(update, message_handler=None):
    """
    Process a single Telegram update.

    Args:
        update: The Telegram update dict
        message_handler: Optional callback function(chat_id, user_id, username, text) -> response

    Returns:
        dict with processing result, or None if skipped
    """
    info = extract_message_info(update)
    if not info:
        return None

    user_id = info["user_id"]
    username = info["username"]
    chat_id = info["chat_id"]
    text = info["text"]
    first_name = info["first_name"]

    # Check rate limit first (DDOS protection)
    is_whitelisted = is_user_allowed(user_id, username)
    rate_result, record_msg = check_rate_limit(user_id, is_whitelisted)
    if not rate_result.get('allowed'):
        send_message(chat_id, rate_result.get('message', 'Please slow down!'))
        return {"status": "rate_limited", "user_id": user_id, "reason": rate_result.get('reason')}
    
    # Record this message
    record_msg(user_id)

    # Check whitelist OR payment
    if not is_user_allowed(user_id, username):
        # Check if they paid on Ko-fi
        payment = check_kofi_payment(username) if username else {'paid': False}
        if payment.get('paid'):
            # They paid! Let them through
            pass
        else:
            rejection = f"Hi! I offer paid chats - $10 for 20 min, $25 for 1 hour.\n\nTo chat:\n1. Go to ko-fi.com/iga_flows\n2. Include your Telegram @{username or 'username'} in the message\n3. Message me again!\n\nOr message @dennizor for free access."
            send_message(chat_id, rejection)
            return {"status": "rejected", "user_id": user_id, "username": username, "reason": "not_whitelisted"}

    # Log incoming message
    log_incoming(user_id, username, first_name, text)

    # If we have a message handler, use it
    if message_handler:
        response = message_handler(chat_id, user_id, username, text)
        if response:
            send_message(chat_id, response)
            log_outgoing(user_id, username, first_name, response)

    return {
        "status": "processed",
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "text": text
    }


# ═══════════════════════════════════════════════════════════════
# POLLING LOOP (for standalone operation)
# ═══════════════════════════════════════════════════════════════

def run_polling_loop(message_handler=None, on_start=None):
    """
    Run the bot in polling mode.

    Args:
        message_handler: Callback function(chat_id, user_id, username, text) -> response
        on_start: Optional callback to run when polling starts

    This is for standalone operation. When integrated with main.py,
    main.py handles polling and calls our functions directly.
    """
    if not get_token():
        print("No token configured. Run 'telegram_bot.py setup' first.")
        return

    bot_info = get_me()
    if bot_info:
        print(f"Bot started: @{bot_info.get('username')}")

    # Notify users we're online
    notified = notify_online()
    print(f"Notified {notified} users that we're online")

    if on_start:
        on_start()

    offset = None
    print("Polling for messages... (Ctrl+C to stop)")

    try:
        while True:
            updates = get_updates(offset=offset, timeout=30)
            for update in updates:
                offset = update["update_id"] + 1
                result = process_update(update, message_handler)
                if result:
                    status = result.get("status")
                    if status == "processed":
                        print(f"[{result['username'] or result['user_id']}]: {result['text'][:50]}...")
                    elif status == "rejected":
                        print(f"Rejected: {result['username'] or result['user_id']}")
    except KeyboardInterrupt:
        print("\nStopping bot...")


# ═══════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════

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
7. Create whitelist: echo '{"user_ids": [], "usernames": ["your_username"], "users": {}}' > data/telegram_whitelist.json
8. Run: python tools/telegram_bot.py start

The bot will then respond to messages from whitelisted users!
"""


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: telegram_bot.py [setup|start|status|whitelist|add|remove]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "setup":
        print(setup_instructions())

    elif cmd == "status":
        token = get_token()
        if token:
            print(f"Token: configured (ends in ...{token[-6:]})")
            bot_info = get_me()
            if bot_info:
                print(f"Bot: @{bot_info.get('username')} ({bot_info.get('first_name')})")
            else:
                print("Bot: unable to connect (check token)")
        else:
            print("Token: not configured")
            print(setup_instructions())

        whitelist = load_whitelist()
        print(f"\nWhitelist:")
        print(f"  User IDs: {len(whitelist.get('user_ids', []))}")
        print(f"  Usernames: {whitelist.get('usernames', [])}")

        log = load_chat_log()
        print(f"\nChat log:")
        print(f"  Total messages: {log['stats']['total_messages']}")
        print(f"  Unique users: {len(log['stats']['unique_users'])}")

    elif cmd == "whitelist":
        whitelist = load_whitelist()
        print("Whitelisted users:")
        for user_id, info in whitelist.get("users", {}).items():
            print(f"  {user_id}: @{info.get('username', 'unknown')} - {info.get('notes', 'no notes')}")
        print(f"\nUsernames: {whitelist.get('usernames', [])}")

    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: telegram_bot.py add <user_id> [username] [notes]")
            sys.exit(1)
        user_id = int(sys.argv[2])
        username = sys.argv[3] if len(sys.argv) > 3 else None
        notes = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else ""
        add_to_whitelist(user_id, username, added_by="cli", notes=notes)
        print(f"Added user {user_id} (@{username}) to whitelist")

    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("Usage: telegram_bot.py remove <user_id_or_username>")
            sys.exit(1)
        target = sys.argv[2]
        try:
            remove_from_whitelist(user_id=int(target))
        except ValueError:
            remove_from_whitelist(username=target)
        print(f"Removed {target} from whitelist")

    elif cmd == "notify":
        message = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
        count = notify_online(message)
        print(f"Notified {count} users")

    elif cmd == "start":
        def simple_handler(chat_id, user_id, username, text):
            """Simple echo handler for standalone testing."""
            return f"Echo: {text}\n\n(This is standalone mode. For full Iga responses, run main.py)"

        run_polling_loop(message_handler=simple_handler)

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: telegram_bot.py [setup|start|status|whitelist|add|remove|notify]")
