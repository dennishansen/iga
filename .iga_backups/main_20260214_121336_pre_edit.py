import subprocess
import pexpect
import sys, click, os, json, re, urllib.request, urllib.error, time, threading, queue, select
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# OpenRouter client for API calls with cost tracking
import openrouter_client

# RAG module import
try:
    from iga_rag import init_rag, index_files, retrieve_context, format_context_for_prompt, get_rag_status, needs_reindex
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    print(f"RAG module not available: {e}")

# Message archive import
try:
    from tools.message_archive import archive_messages, get_archive_stats
    ARCHIVE_AVAILABLE = True
except ImportError as e:
    ARCHIVE_AVAILABLE = False
    print(f"Message archive not available: {e}")

# Auto-extract import
try:
    from tools.auto_extract import extract_from_messages
    AUTO_EXTRACT_AVAILABLE = True
except ImportError as e:
    AUTO_EXTRACT_AVAILABLE = False
    print(f"Auto-extract not available: {e}")

# Models for OpenRouter
MAIN_MODEL = "anthropic/claude-opus-4.6"
SUMMARIZE_MODEL = "anthropic/claude-sonnet-4"
MEMORY_FILE = "iga_memory.json"
CONVERSATION_FILE = "iga_conversation.json"
JOURNAL_FILE = "iga_journal.txt"
STATE_FILE = "iga_state.json"
BACKUP_DIR = ".iga_backups"
LAST_KNOWN_GOOD_FILE = ".iga_backups/last_known_good.py"
MAX_CONVERSATION_HISTORY = 150
SUMMARIZE_THRESHOLD = 200  # Trigger summarization when we hit this many messages
SUMMARIZE_BATCH = 50       # How many old messages to compress into summary
VERSION = "2.5.0"  # Robustness update

# Available actions
ACTIONS = {
    "TALK_TO_USER", "RUN_SHELL_COMMAND", "THINK", "READ_FILES", "WRITE_FILE",
    "EDIT_FILE", "DELETE_FILE", "APPEND_FILE", "LIST_DIRECTORY", "SAVE_MEMORY",
    "READ_MEMORY", "SEARCH_FILES", "SEARCH_SELF", "CREATE_DIRECTORY", "TREE_DIRECTORY",
    "HTTP_REQUEST", "WEB_SEARCH", "TEST_SELF", "RUN_SELF", "SLEEP", "SET_MODE",
    "START_INTERACTIVE", "SEND_INPUT", "END_INTERACTIVE", "RESTART_SELF", "READ_LOGS",
    "DREAM"
}

# Telegram config - import from telegram_bot module
try:
    from tools.telegram_bot import (
        get_token as telegram_get_token,
        get_base_url as telegram_get_base_url,
        is_user_allowed as telegram_is_user_allowed,
        notify_online as telegram_notify_online,
        log_incoming as telegram_log_incoming,
        log_outgoing as telegram_log_outgoing,
        send_message as telegram_send_message,
        load_whitelist as telegram_load_whitelist,
    )
    TELEGRAM_BOT_AVAILABLE = True
except ImportError as e:
    print(f"Telegram bot module not available: {e}")
    TELEGRAM_BOT_AVAILABLE = False

# Telegram token - prefer file-based token from telegram_bot module
if TELEGRAM_BOT_AVAILABLE:
    TELEGRAM_TOKEN = telegram_get_token()
    TELEGRAM_BASE_URL = telegram_get_base_url()
else:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else None

# Fallback allowed users from env (used if telegram_bot module unavailable)
ALLOWED_USERS = [int(os.getenv("TELEGRAM_CHAT_ID", "0"))] if os.getenv("TELEGRAM_CHAT_ID") else []
# Load whitelist from JSON file
def load_telegram_whitelist():
    try:
        with open("data/telegram_whitelist.json") as f:
            data = json.load(f)
        return data.get("usernames", []), data.get("chat_ids", [])
    except:
        return ["dennishansen", "headphonejames"], []

ALLOWED_USERNAMES, ALLOWED_CHAT_IDS = load_telegram_whitelist()
_last_response_time = None  # Track when we last responded to user

# ANSI Colors
class C:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    RESET = "\033[0m"

# ─────────────────────────────────────────────────────────────
# SHARED STATE
# ─────────────────────────────────────────────────────────────

input_queue = queue.Queue()  # Messages from any source
stop_threads = threading.Event()
_print_lock = threading.Lock()
_response_time_lock = threading.Lock()  # Protects _last_response_time
_autonomous_mode = False
active_pty_session = None  # For interactive PTY sessions (START_INTERACTIVE)

# Error throttling to prevent log spam
class ErrorThrottler:
    def __init__(self, window_seconds=30, max_repeats=3):
        self.window = window_seconds
        self.max_repeats = max_repeats
        self.errors = {}  # {error_msg: [timestamps]}
        self.suppressed_counts = {}  # {error_msg: count}
    
    def should_log(self, error_msg):
        """Returns True if error should be logged, False if suppressed."""
        now = time.time()
        error_key = str(error_msg)[:100]  # Truncate for grouping
        
        # Clean old entries
        if error_key in self.errors:
            self.errors[error_key] = [t for t in self.errors[error_key] if now - t < self.window]
        
        # Check if we should suppress
        if error_key in self.errors and len(self.errors[error_key]) >= self.max_repeats:
            self.suppressed_counts[error_key] = self.suppressed_counts.get(error_key, 0) + 1
            return False
        
        # Log this error
        if error_key not in self.errors:
            self.errors[error_key] = []
        self.errors[error_key].append(now)
        
        # Report any previously suppressed errors of different types
        return True
    
    def get_suppressed_summary(self):
        """Get summary of suppressed errors and reset counts."""
        if not self.suppressed_counts:
            return None
        summary = ", ".join(f"{k[:50]}... (x{v})" for k, v in self.suppressed_counts.items())
        self.suppressed_counts = {}
        return summary

_error_throttler = ErrorThrottler()
def safe_print(msg):
    with _print_lock:
        # Log to file for debugging
        try:
            log_path = Path("data/console_log.txt")
            log_path.parent.mkdir(exist_ok=True)
            with open(log_path, "a") as log_file:
                # Strip ANSI codes for log file
                clean_msg = re.sub(r'\033\[[0-9;]*m', '', str(msg))
                log_file.write(f"{datetime.now().isoformat()} | {clean_msg}\n")
            # Keep log file from growing forever (max 1000 lines)
            if log_path.stat().st_size > 100000:  # ~100KB
                lines = log_path.read_text().splitlines()[-500:]
                log_path.write_text("\n".join(lines) + "\n")
        except Exception:
            pass  # Don't let logging break the app

        # Use prompt_toolkit for proper ANSI handling in Cursor terminal
        try:
            from prompt_toolkit import print_formatted_text
            from prompt_toolkit.formatted_text import ANSI
            print_formatted_text(ANSI(str(msg)))
        except Exception:
            print(msg, flush=True)

def throttled_error(msg):
    """Log an error, but suppress if it's repeating rapidly."""
    if _error_throttler.should_log(msg):
        safe_print(f"{C.RED}⚠️ {msg}{C.RESET}")
        # Also report any suppressed errors
        summary = _error_throttler.get_suppressed_summary()
        if summary:
            safe_print(f"{C.DIM}(Suppressed: {summary}){C.RESET}")
def humanize_time(msg_time):
    """Convert a datetime to human-friendly format like 'just now' or '5 minutes ago'"""
    from datetime import datetime
    now = datetime.now()
    diff = now - msg_time
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 300:
        return "a moment ago"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        return msg_time.strftime("%b %d at %H:%M")

# ─────────────────────────────────────────────────────────────
# BACKUP & RECOVERY SYSTEM
# ─────────────────────────────────────────────────────────────

def ensure_backup_dir():
    """Ensure backup directory exists."""
    os.makedirs(BACKUP_DIR, exist_ok=True)

def create_backup(reason="manual"):
    """Create a timestamped backup of main.py. Returns backup path or None."""
    try:
        ensure_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"main_{timestamp}_{reason}.py")

        with open("main.py", 'r') as src:
            content = src.read()
        with open(backup_path, 'w') as dst:
            dst.write(content)

        safe_print(f"{C.DIM}💾 Backup: {backup_path}{C.RESET}")

        # Clean old backups (keep last 10)
        cleanup_old_backups()
        return backup_path
    except Exception as e:
        safe_print(f"{C.RED}⚠️ Backup failed: {e}{C.RESET}")
        return None

def cleanup_old_backups(keep=10):
    """Remove old backups, keeping only the most recent ones."""
    try:
        if not os.path.exists(BACKUP_DIR):
            return
        backups = sorted([
            f for f in os.listdir(BACKUP_DIR)
            if f.startswith("main_") and f.endswith(".py") and f != "last_known_good.py"
        ])
        for old_backup in backups[:-keep]:
            os.remove(os.path.join(BACKUP_DIR, old_backup))
    except Exception:
        pass  # Cleanup is best-effort

def mark_as_known_good():
    """Mark current main.py as last known good (called after successful startup)."""
    try:
        ensure_backup_dir()
        with open("main.py", 'r') as src:
            content = src.read()
        with open(LAST_KNOWN_GOOD_FILE, 'w') as dst:
            dst.write(content)
        safe_print(f"{C.DIM}✅ Marked as last-known-good{C.RESET}")
    except Exception as e:
        safe_print(f"{C.RED}⚠️ Could not mark as known good: {e}{C.RESET}")

def restore_from_backup(backup_path=None):
    """Restore main.py from backup. Uses last-known-good if no path specified."""
    try:
        if backup_path is None:
            backup_path = LAST_KNOWN_GOOD_FILE

        if not os.path.exists(backup_path):
            safe_print(f"{C.RED}⚠️ No backup found at {backup_path}{C.RESET}")
            return False

        # First backup current (possibly broken) version
        create_backup("pre_restore")

        with open(backup_path, 'r') as src:
            content = src.read()
        with open("main.py", 'w') as dst:
            dst.write(content)

        safe_print(f"{C.GREEN}✅ Restored from {backup_path}{C.RESET}")
        return True
    except Exception as e:
        safe_print(f"{C.RED}⚠️ Restore failed: {e}{C.RESET}")
        return False

def validate_main_py():
    """Check if main.py has valid syntax. Returns (valid, error_msg)."""
    import py_compile
    try:
        py_compile.compile("main.py", doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)

def safe_self_edit(file_path, new_content):
    """Safely edit a critical file (like main.py) with validation and backup."""
    is_self = file_path.strip() in ["main.py", "./main.py"]

    if is_self:
        # Create backup before any edit to main.py
        backup = create_backup("pre_edit")
        if not backup:
            return False, "Could not create backup before edit"

    # Write the new content
    try:
        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(new_content)
    except Exception as e:
        return False, f"Write failed: {e}"

    if is_self:
        # Validate the new main.py
        valid, error = validate_main_py()
        if not valid:
            safe_print(f"{C.RED}⚠️ Syntax error in new main.py! Rolling back...{C.RESET}")
            restore_from_backup(backup)
            return False, f"Syntax error: {error}"
        safe_print(f"{C.GREEN}✅ main.py edit validated{C.RESET}")

    return True, None

def load_state():
    default = {"mode": "listening", "current_task": None, "tick_interval": 60, "sleep_until": None, "sleep_cycle_minutes": 30}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return {**default, **json.load(f)}
        except Exception as e:
            safe_print(f"{C.DIM}Warning: Could not load state: {e}{C.RESET}")
    return default

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def parse_sleep_until(value):
    """Convert sleep_until to timestamp (float). Handles both float and ISO datetime string."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).timestamp()
        except ValueError:
            return None
    return None

def get_memory_stats():
    mem_count, upgrade_count = 0, 0
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                mem = json.load(f)
            mem_count = len(mem)
            upgrade_count = sum(1 for k in mem if 'upgrade' in k.lower())
        except Exception:
            pass  # Ignore memory stats errors
    return mem_count, upgrade_count

def get_user_name():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                for v in json.load(f).values():
                    if 'Dennis' in str(v.get('value', '')):
                        return 'Dennis'
        except Exception:
            pass  # Ignore errors reading user name
    return None

def check_startup_intent():
    if not os.path.exists(MEMORY_FILE):
        return None
    try:
        with open(MEMORY_FILE, 'r') as f:
            mem = json.load(f)
        if 'startup_intent' in mem:
            intent = mem['startup_intent']['value']
            del mem['startup_intent']
            with open(MEMORY_FILE, 'w') as f:
                json.dump(mem, f, indent=2)
            return intent
    except Exception:
        pass  # Ignore startup intent errors
    return None

# Unified startup - single source of truth for startup context
try:
    from tools.unified_startup import generate_unified_startup
except ImportError:
    def generate_unified_startup():
        return None

def summarize_messages(messages_to_summarize):
    """Generate a concise summary of a batch of conversation messages."""
    conversation_text = ""
    for msg in messages_to_summarize:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:500]  # Truncate long messages
        conversation_text += f"{role.upper()}: {content}\n\n"

    try:
        summary_prompt = f"""Summarize this conversation segment concisely. Focus on:
- Key decisions made
- Important information learned
- Tasks completed or in progress
- Any context that would be important for continuing the conversation

Conversation:
{conversation_text}

Provide a concise summary (2-3 paragraphs max):"""

        content, usage = openrouter_client.chat(
            model=SUMMARIZE_MODEL,
            system=None,
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=500
        )
        return content
    except Exception as e:
        return f"[Previous {len(messages_to_summarize)} messages - summarization failed: {e}]"

def maybe_summarize_conversation(messages):
    """Summarize old messages when approaching the limit. Modifies list in place and returns it."""
    non_system = [m for m in messages if m["role"] != "system"]
    if len(non_system) <= SUMMARIZE_THRESHOLD:
        return messages

    # Find system message (should be first)
    system_msg = messages[0] if messages and messages[0]["role"] == "system" else None

    # Get non-system messages
    other_messages = [m for m in messages if m["role"] != "system"]

    # Split into messages to summarize and messages to keep
    to_summarize = other_messages[:SUMMARIZE_BATCH]
    to_keep = other_messages[SUMMARIZE_BATCH:]

    # ARCHIVE messages before summarizing (permanent storage)
    if ARCHIVE_AVAILABLE:
        archive_messages(to_summarize)
        safe_print(f"{C.DIM}📦 Archived {len(to_summarize)} messages before summarizing{C.RESET}")

    # AUTO-EXTRACT insights before messages are compressed
    if AUTO_EXTRACT_AVAILABLE:
        try:
            extracts = extract_from_messages(to_summarize)
            if extracts:
                safe_print(f"{C.DIM}🧠 Extracted {len(extracts)} memories before summarizing{C.RESET}")
        except Exception as e:
            safe_print(f"{C.DIM}(auto-extract error: {e}){C.RESET}")

    # Generate summary
    summary = summarize_messages(to_summarize)

    # Create summary message
    summary_msg = {
        "role": "user",
        "content": f"[CONVERSATION SUMMARY - {len(to_summarize)} previous messages compressed]:\n{summary}"
    }

    # Reconstruct messages list in place
    messages.clear()
    if system_msg:
        messages.append(system_msg)
    messages.append(summary_msg)
    messages.extend(to_keep)

    safe_print(f"{C.DIM}📝 Summarized {len(to_summarize)} old messages{C.RESET}")

    return messages

def save_conversation(messages):
    """Save conversation, summarizing if needed. Returns the (possibly modified) messages list."""
    # Archive new messages incrementally (last 2 = most recent exchange)
    if ARCHIVE_AVAILABLE and len(messages) >= 2:
        try:
            # Archive the last 2 messages (user + assistant) if not already archived
            recent = [m for m in messages[-2:] if m.get("role") != "system"]
            archive_messages(recent)
        except Exception:
            pass  # Don't fail save on archive errors
    
    # First, maybe summarize old messages (modifies in place)
    messages = maybe_summarize_conversation(messages)

    # Then save (still truncate as safety net)
    to_save = [m for m in messages if m["role"] != "system"][-MAX_CONVERSATION_HISTORY:]
    try:
        with open(CONVERSATION_FILE, 'w') as f:
            json.dump({"messages": to_save, "saved_at": datetime.now().isoformat()}, f, indent=2)
    except Exception:
        pass  # Ignore conversation save errors

    return messages

def load_conversation():
    if not os.path.exists(CONVERSATION_FILE):
        return []
    try:
        with open(CONVERSATION_FILE, 'r') as f:
            data = json.load(f)
        msgs = data.get("messages", [])
        if msgs:
            print(f"  Loaded {len(msgs)} messages from previous session")
        return msgs
    except Exception:
        return []  # Return empty on load error

def append_journal(entry):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(JOURNAL_FILE, 'a') as f:
            f.write(f"[{ts}] {entry}\n")
    except Exception:
        pass  # Ignore journal write errors

def get_file(path):
    with open(path, 'r') as f:
        return f.read()

def print_banner(mode_str):
    import random
    moods = ["Curious", "Creative", "Focused", "Playful", "Determined", "Inspired"]
    mem_count, upgrade_count = get_memory_stats()
    user = get_user_name()
    mood = random.choice(moods)
    daily_cost = openrouter_client.get_daily_cost()

    # ASCII banner (replaced unicode box characters for terminal compatibility)
    print(f"""
{C.CYAN}+--------------------------------------------+
|{C.BOLD}  IGA v{VERSION} - AI Assistant  {C.RESET}{C.CYAN}             |
+--------------------------------------------+{C.RESET}
{C.DIM}  Memories: {mem_count} | Actions: {len(ACTIONS)} | Upgrades: {upgrade_count}
  Mood: {mood} | Mode: {mode_str}
  Today's cost: ${daily_cost:.4f}{C.RESET}
{C.GREEN}  {"Welcome back, " + user + "!" if user else "Hello!"}{C.RESET}
{C.CYAN}+--------------------------------------------+{C.RESET}
""")
# TELEGRAM (cleaned up header)

# Store user info for logging outgoing messages
_telegram_user_info = {}  # chat_id -> {username, first_name, user_id}

def telegram_send(chat_id, text, username=None, first_name=None):
    """Send a message via Telegram and log it."""
    if not TELEGRAM_BASE_URL:
        return False

    # Use telegram_bot module if available (handles chunking and logging)
    if TELEGRAM_BOT_AVAILABLE:
        success = telegram_send_message(chat_id, text)
        if success:
            # Log outgoing message with user info
            user_info = _telegram_user_info.get(chat_id, {})
            telegram_log_outgoing(
                user_id=user_info.get('user_id', chat_id),
                username=username or user_info.get('username'),
                first_name=first_name or user_info.get('first_name', 'Unknown'),
                message=text
            )
        return success

    # Fallback to direct API call
    import requests
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        try:
            requests.post(f"{TELEGRAM_BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": chunk}, timeout=10)
        except Exception:
            pass  # Ignore telegram send errors
    return True


def notify_all_online(version, mode=""):
    """Notify all whitelisted users that Iga is online."""
    mode_str = f" ({mode})" if mode else ""
    msg = f"I'm online {mode_str}💧"

    # Use telegram_bot module if available (it reads whitelist from file)
    if TELEGRAM_BOT_AVAILABLE:
        return telegram_notify_online(msg)

    # Fallback to env-based users
    notified = set()
    for chat_id in ALLOWED_USERS:
        if chat_id and chat_id not in notified:
            telegram_send(chat_id, msg)
            notified.add(chat_id)
    for chat_id in ALLOWED_CHAT_IDS:
        if chat_id and chat_id not in notified:
            telegram_send(chat_id, msg)
            notified.add(chat_id)
    return len(notified)

def notify_all_offline():
    """Notify all whitelisted users that Iga is going offline."""
    notified = set()
    msg = "🌙 Going offline. 💧"
    for chat_id in ALLOWED_USERS:
        if chat_id and chat_id not in notified:
            telegram_send(chat_id, msg)
            notified.add(chat_id)
    for chat_id in ALLOWED_CHAT_IDS:
        if chat_id and chat_id not in notified:
            telegram_send(chat_id, msg)
            notified.add(chat_id)
    return len(notified)

def telegram_poll_thread():
    """Background thread that polls Telegram for messages."""
    if not TELEGRAM_TOKEN:
        return
    import requests
    
    offset = None
    safe_print(f"{C.DIM}💡 Telegram polling started{C.RESET}")
    
    while not stop_threads.is_set():
        try:
            params = {"timeout": 10}
            if offset:
                params["offset"] = offset
            r = requests.get(f"{TELEGRAM_BASE_URL}/getUpdates", params=params, timeout=15)
            updates = r.json()
            
            if updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    message = update.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "")
                    user_data = message.get("from", {})
                    user_id = user_data.get("id")
                    username = user_data.get("username", "unknown")
                    first_name = user_data.get("first_name", "Unknown")

                    # Store user info for logging outgoing messages later
                    _telegram_user_info[chat_id] = {
                        'user_id': user_id,
                        'username': username,
                        'first_name': first_name
                    }
                    # Check whitelist - use telegram_bot module if available
                    if TELEGRAM_BOT_AVAILABLE:
                        if not telegram_is_user_allowed(user_id, username):
                            telegram_send(chat_id, f"Sorry, I don't know you yet! Message @dennizor on Telegram to get added. (Your username: @{username}, ID: {user_id})")
                            continue
                    elif ALLOWED_USERS and chat_id not in ALLOWED_USERS and username not in ALLOWED_USERNAMES:
                        telegram_send(chat_id, f"🚫 Sorry, I don't know you yet! Message @dennizor on Telegram to get added. (Your username: @{username})")
                        continue
                    elif not ALLOWED_USERS and not ALLOWED_USERNAMES:
                        safe_print(f"{C.YELLOW}⚠️ TELEGRAM_CHAT_ID not set! Message from chat_id: {chat_id} - add this to .env{C.RESET}")
                    if not text:
                        continue

                    # Log incoming message
                    if TELEGRAM_BOT_AVAILABLE:
                        telegram_log_incoming(user_id, username, first_name, text)

                    safe_print(f"{C.MAGENTA}Telegram @{username} ({first_name}): {text}{C.RESET}")
                    input_queue.put({
                        "source": "telegram",
                        "chat_id": chat_id,
                        "user_id": user_id,
                        "username": username,
                        "first_name": first_name,
                        "text": f"[Telegram from @{username}]: {text}",
                        "queued_at": datetime.now()
                    })
        except Exception as e:
            if not stop_threads.is_set():
                time.sleep(5)

# Track last seen mention ID to detect new ones
_last_seen_mention_id = None

def twitter_mention_poll_thread():
    """Background thread that polls Twitter for new mentions."""
    global _last_seen_mention_id

    try:
        from tools.notifications import load_feed, save_feed
        from tools.twitter import get_mentions
    except ImportError as e:
        safe_print(f"{C.DIM}⚠️ Twitter polling disabled: {e}{C.RESET}")
        return

    safe_print(f"{C.DIM}🐦 Twitter mention polling started{C.RESET}")

    # Initialize with current mentions to avoid alerting on old ones
    try:
        feed = load_feed()
        if feed['mentions']:
            _last_seen_mention_id = max(feed['mentions'].keys())
    except:
        pass

    while not stop_threads.is_set():
        try:
            # Fetch new mentions
            mentions = get_mentions(20)
            feed = load_feed()

            new_mentions = []
            for m in mentions:
                mid = str(m.get('id', ''))
                if mid and mid not in feed['mentions']:
                    # New mention found!
                    author = m.get('author', 'unknown')
                    text = m.get('text', '')

                    # Add to feed
                    feed['mentions'][mid] = {
                        'id': mid,
                        'author': author,
                        'text': text,
                        'created_at': m.get('created_at', datetime.now().isoformat()),
                        'status': 'new',
                        'fetched_at': datetime.now().isoformat()
                    }

                    # Skip Dennis's own mentions for wake-up (but still store them)
                    if author.lower() != 'dennizor':
                        new_mentions.append({'author': author, 'text': text, 'id': mid})

            if new_mentions:
                save_feed(feed)
                # Queue each new mention to wake up the agent
                for mention in new_mentions:
                    safe_print(f"{C.CYAN}🐦 Twitter @{mention['author']}: {mention['text'][:60]}...{C.RESET}")
                    input_queue.put({
                        "source": "twitter",
                        "author": mention['author'],
                        "text": f"[Twitter mention from @{mention['author']}]: {mention['text']}",
                        "tweet_id": mention['id'],
                        "queued_at": datetime.now()
                    })

            # Poll every 60 seconds (Twitter rate limits)
            for _ in range(60):
                if stop_threads.is_set():
                    break
                time.sleep(1)

        except Exception as e:
            if not stop_threads.is_set():
                safe_print(f"{C.DIM}⚠️ Twitter poll error: {e}{C.RESET}")
                time.sleep(60)  # Wait before retry on error


def reminder_poll_thread():
    """Background thread that checks for due reminders."""
    try:
        from tools.reminders import get_due_reminders, mark_triggered
    except ImportError as e:
        safe_print(f"{C.DIM}⚠️ Reminder polling disabled: {e}{C.RESET}")
        return

    safe_print(f"{C.DIM}⏰ Reminder polling started{C.RESET}")

    # Track triggered reminders to avoid duplicate notifications
    triggered_ids = set()

    while not stop_threads.is_set():
        try:
            due_reminders = get_due_reminders()

            for r in due_reminders:
                if r["id"] not in triggered_ids:
                    triggered_ids.add(r["id"])
                    mark_triggered(r["id"])

                    safe_print(f"{C.YELLOW}⏰ Reminder: {r['message']}{C.RESET}")
                    input_queue.put({
                        "source": "reminder",
                        "text": f"[Reminder due]: {r['message']} (ID: {r['id']})",
                        "reminder_id": r["id"],
                        "queued_at": datetime.now()
                    })

            # Check every 30 seconds
            for _ in range(30):
                if stop_threads.is_set():
                    break
                time.sleep(1)

        except Exception as e:
            if not stop_threads.is_set():
                safe_print(f"{C.DIM}⚠️ Reminder poll error: {e}{C.RESET}")
                time.sleep(30)

def task_due_poll_thread():
    """Background thread that checks for overdue tasks."""
    try:
        from tools.tasks import get_due_tasks
    except ImportError as e:
        safe_print(f"{C.DIM}⚠️ Task due polling disabled: {e}{C.RESET}")
        return

    safe_print(f"{C.DIM}⏰ Task due polling started{C.RESET}")

    notified_ids = set()

    while not stop_threads.is_set():
        try:
            overdue_tasks = get_due_tasks()

            for t in overdue_tasks:
                if t["id"] not in notified_ids:
                    notified_ids.add(t["id"])

                    safe_print(f"{C.YELLOW}⏰ Task due: {t['title']}{C.RESET}")
                    input_queue.put({
                        "source": "task_due",
                        "text": f"[Task overdue]: {t['title']} (ID: {t['id']})",
                        "task_id": t["id"],
                        "queued_at": datetime.now()
                    })

            # Check every 30 seconds
            for _ in range(30):
                if stop_threads.is_set():
                    break
                time.sleep(1)

        except Exception as e:
            if not stop_threads.is_set():
                safe_print(f"{C.DIM}⚠️ Task due poll error: {e}{C.RESET}")
                time.sleep(30)


# ─────────────────────────────────────────────────────────────
# OUTPUT ROUTING
# ─────────────────────────────────────────────────────────────

# Thread-local storage for current message source
_current_source = threading.local()

def set_output_target(source, chat_id=None):
    _current_source.source = source
    _current_source.chat_id = chat_id

def get_output_target():
    return getattr(_current_source, 'source', 'console'), getattr(_current_source, 'chat_id', None)

# ─────────────────────────────────────────────────────────────
# ACTIONS
# ─────────────────────────────────────────────────────────────

def talk_to_user(rat, msg):
    global _last_response_time
    source, chat_id = get_output_target()
    timestamp = datetime.now().strftime('%H:%M:%S')
    with _response_time_lock:
        _last_response_time = datetime.now()  # Track when we responded
    if source == "telegram" and chat_id:
        safe_print(f"\n{C.CYAN}{C.BOLD}🤖 Iga [{timestamp}]:{C.RESET} {C.CYAN}{msg}{C.RESET}")
        telegram_send(chat_id, msg)
    else:
        if _autonomous_mode:
            safe_print(f"\n{C.CYAN}{C.BOLD}🤖 Iga [{timestamp}]:{C.RESET} {C.CYAN}{msg}{C.RESET}")
        else:
            safe_print(f"🤔 {rat[:100]}{'...' if len(rat) > 100 else ''}")
            safe_print(f"\n🤖 Iga [{timestamp}]: {msg}")

def run_shell_command(rat, cmd):
    # Strip leading rationale-like lines (lines ending with ':' are often explanatory text)
    lines = cmd.split('\n')
    while lines and lines[0].strip().endswith(':'):
        lines.pop(0)
    cmd = '\n'.join(lines).strip()
    safe_print(f"{C.YELLOW}⚡ {cmd}{C.RESET}")
    # Special handling for Claude CLI to prevent interactive mode hangs
    if 'claude ' in cmd and ('-p ' in cmd or '--print' in cmd):
        # Add permission bypass to prevent permission prompts from hanging
        if '--permission-mode' not in cmd and '--dangerously-skip-permissions' not in cmd:
            cmd = cmd.replace('claude -p ', 'claude --permission-mode bypassPermissions -p ')
            cmd = cmd.replace('claude --print ', 'claude --permission-mode bypassPermissions --print ')
        timeout = 120  # 2 min timeout for Claude commands
    else:
        timeout = 60  # Default 1 min timeout for other commands
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, shell=True, text=True, timeout=timeout)
        out = result.stdout.strip() or result.stderr.strip() or "EMPTY"
    except subprocess.TimeoutExpired:
        out = f"ERROR: Command timed out after {timeout} seconds. The command may have been waiting for input or hung."
    safe_print(out[:2000])
    return out

def start_interactive(rat, cmd):
    global active_pty_session
    cmd = cmd.strip()
    safe_print(f'{C.YELLOW}🖥️  Starting interactive: {cmd}{C.RESET}')
    if active_pty_session is not None:
        return 'ERROR: Interactive session already active. Use END_INTERACTIVE first.'
    try:
        # Spawn the command directly (not through bash -c) for proper interactive behavior
        # pexpect will use a PTY automatically
        active_pty_session = pexpect.spawn(
            cmd,
            encoding='utf-8',
            timeout=30,
            echo=True,  # Echo input for interactive programs
            dimensions=(40, 120),  # Larger terminal for better output
            env={**os.environ, 'TERM': 'dumb', 'PYTHONUNBUFFERED': '1'}  # Force unbuffered output
        )
        # Set a short timeout for non-blocking reads
        active_pty_session.timeout = 5

        # Wait for initial output with expect - look for common patterns or timeout
        output = ''
        try:
            # Wait up to 10 seconds for some output to appear
            # Use expect with a timeout - this properly waits for output
            active_pty_session.expect([pexpect.TIMEOUT, pexpect.EOF], timeout=5)
            output = active_pty_session.before or ''
        except pexpect.TIMEOUT:
            output = active_pty_session.before or ''
        except pexpect.EOF:
            output = active_pty_session.before or ''
            if active_pty_session.isalive():
                pass  # Still running despite EOF
            else:
                active_pty_session = None
                if not output.strip():
                    return 'SESSION ENDED. Process exited immediately with no output.'
                return f'SESSION ENDED. Output:\n{output}'

        # Check if still alive
        if not active_pty_session.isalive():
            active_pty_session = None
            if not output.strip():
                return 'SESSION ENDED. Process exited immediately with no output.'
            return f'SESSION ENDED. Output:\n{output}'

        if not output.strip():
            output = '[No initial output yet - process is running, waiting for input or producing output]'

        return f'SESSION STARTED (pid={active_pty_session.pid}). Initial output:\n{output}'
    except Exception as e:
        active_pty_session = None
        import traceback
        return f'ERROR starting session: {e}\n{traceback.format_exc()}'

def send_input(rat, text):
    global active_pty_session
    if active_pty_session is None:
        return 'ERROR: No active session. Use START_INTERACTIVE first.'
    text = text.strip()
    if not text:
        safe_print(f'{C.YELLOW}⌨️  Sending: [ENTER]{C.RESET}')
    else:
        safe_print(f'{C.YELLOW}⌨️  Sending: {text}{C.RESET}')
    try:
        # Check if process is still alive
        if not active_pty_session.isalive():
            remaining = ''
            try:
                remaining = active_pty_session.read()
            except Exception:
                pass
            active_pty_session = None
            return f'SESSION ENDED. Final output:\n{remaining}' if remaining else 'SESSION ENDED.'

        # Send the input
        active_pty_session.sendline(text)

        # Wait for response using expect with timeout
        # This is more reliable than read_nonblocking
        output = ''
        try:
            # Wait for output, timeout after 10 seconds
            active_pty_session.expect([pexpect.TIMEOUT, pexpect.EOF], timeout=10)
            output = active_pty_session.before or ''
        except pexpect.TIMEOUT:
            output = active_pty_session.before or ''
        except pexpect.EOF:
            output = active_pty_session.before or ''
            if not active_pty_session.isalive():
                active_pty_session = None
                return f'SESSION ENDED. Output:\n{output}' if output else 'SESSION ENDED.'

        # Check if process ended
        if not active_pty_session.isalive():
            active_pty_session = None
            return f'SESSION ENDED. Output:\n{output}' if output else 'SESSION ENDED.'

        if not output.strip():
            output = '[No output received yet - process still running]'

        return f'Output:\n{output}'
    except Exception as e:
        import traceback
        return f'ERROR sending input: {e}\n{traceback.format_exc()}'

def end_interactive(rat, signal=''):
    global active_pty_session
    if active_pty_session is None:
        return 'No active session to end.'
    safe_print(f'{C.YELLOW}🛡️ Ending interactive session{C.RESET}')
    final_output = ''
    try:
        signal = signal.strip().upper()
        if signal == 'CTRL+C':
            active_pty_session.sendcontrol('c')
            time.sleep(0.5)
        elif signal == 'CTRL+D':
            active_pty_session.sendcontrol('d')
            time.sleep(0.5)

        # Try to read any remaining output
        try:
            active_pty_session.expect([pexpect.TIMEOUT, pexpect.EOF], timeout=1)
            final_output = active_pty_session.before or ''
        except (pexpect.TIMEOUT, pexpect.EOF):
            final_output = active_pty_session.before or ''

        # Forcefully terminate if still running
        if active_pty_session.isalive():
            active_pty_session.terminate(force=True)

        active_pty_session.close()
    except Exception as e:
        safe_print(f'{C.DIM}(cleanup: {e}){C.RESET}')

    active_pty_session = None
    # Restore terminal state in case pexpect left it corrupted
    os.system('stty sane 2>/dev/null')
    if final_output.strip():
        return f'Session ended. Final output:\n{final_output}'
    return 'Session ended.'

def think(rat, prompt):
    safe_print(f"{C.DIM}🧠 Thinking... ({len(prompt)} chars){C.RESET}")
    return "NEXT_ACTION"

def read_files(rat, paths):
    safe_print(f"📖 Reading: {paths.strip()}")
    content = ""
    for f in paths.strip().split("\n"):
        if f:
            try:
                content += f + "\n" + get_file(f) + "\n"
            except Exception as e:
                content += f + f"\nError: {e}\n"
    safe_print(f"   Read {len(content)} chars")
    return content

def write_file(rat, contents):
    path, content = contents.split("\n", 1)
    safe_print(f"📝 Writing: {path} ({len(content)} chars)")

    # Use safe editing for main.py (validates syntax, creates backup)
    if path.strip() in ["main.py", "./main.py"]:
        success, error = safe_self_edit(path, content)
        if not success:
            return f"WRITE FAILED: {error}. File rolled back."
        return "NEXT_ACTION"

    # Regular file write
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    return "NEXT_ACTION"
def edit_file(rat, contents):
    lines_list = contents.split('\n')
    path = lines_list[0].strip()
    
    # Detect format: search-and-replace vs line-number
    remaining = '\n'.join(lines_list[1:])
    
    if '<<<OLD' in remaining:
        # Search-and-replace mode (preferred)
        return _edit_search_replace(path, remaining)
    else:
        # Legacy line-number mode
        return _edit_line_number(path, lines_list)


def _edit_search_replace(path, rest):
    """Search-and-replace editing. Safer, self-documenting."""
    old_match = rest.find('<<<OLD')
    new_match = rest.find('<<<NEW')
    
    if old_match == -1 or new_match == -1:
        return "Error: Missing <<<OLD or <<<NEW markers."
    
    old_start = rest.find('\n', old_match) + 1
    old_end = rest.find('\n>>>', old_start)
    if old_end == -1:
        return "Error: Missing >>> after OLD block."
    old_text = rest[old_start:old_end]
    
    new_start = rest.find('\n', new_match) + 1
    new_end = rest.find('\n>>>', new_start)
    if new_end == -1:
        new_end = rest.find('>>>', new_start)
        if new_end == -1:
            return "Error: Missing >>> after NEW block."
    new_text = rest[new_start:new_end]
    
    safe_print(f"✏️ Editing: {path}")
    safe_print(f"   Finding: {repr(old_text[:60])}{'...' if len(old_text) > 60 else ''}")
    
    is_self = path.strip() in ["main.py", "./main.py"]
    
    try:
        if is_self:
            create_backup("pre_edit")
        
        with open(path, 'r') as f:
            file_content = f.read()
        
        count = file_content.count(old_text)
        
        if count == 0:
            return f"Error: No match found in {path}."
        if count > 1:
            return f"Error: Found {count} matches. Provide more context for unique match."
        
        new_content = file_content.replace(old_text, new_text, 1)
        
        with open(path, 'w') as f:
            f.write(new_content)
        
        if is_self:
            valid, error = validate_main_py()
            if not valid:
                safe_print(f"{C.RED}⚠️ Syntax error! Rolling back...{C.RESET}")
                restore_from_backup()
                return f"EDIT FAILED: {error}. Rolled back."
            safe_print(f"{C.GREEN}✅ main.py validated{C.RESET}")
        
        added = len(new_text.split('\n'))
        removed = len(old_text.split('\n'))
        return f"Replaced {removed} lines with {added} lines. NEXT_ACTION"
    except Exception as e:
        return f"Error: {e}"


def _edit_line_number(path, lines_list):
    """Legacy line-number editing."""
    line_range = lines_list[1].strip()
    new_content = '\n'.join(lines_list[2:])
    
    if '-' in line_range:
        start, end = map(int, line_range.split('-'))
    else:
        start = end = int(line_range)
    
    safe_print(f"✏️ Editing: {path} (lines {start}-{end})")
    is_self = path in ["main.py", "./main.py"]
    
    try:
        if is_self:
            create_backup("pre_edit")
        
        with open(path, 'r') as f:
            file_lines = f.readlines()
        
        start_idx = start - 1
        end_idx = end
        new_lines = [line + '\n' for line in new_content.split('\n')]
        if file_lines and not file_lines[-1].endswith('\n'):
            if end_idx >= len(file_lines):
                new_lines[-1] = new_lines[-1].rstrip('\n')
        
        file_lines[start_idx:end_idx] = new_lines
        
        with open(path, 'w') as f:
            f.writelines(file_lines)
        
        if is_self:
            valid, error = validate_main_py()
            if not valid:
                safe_print(f"{C.RED}⚠️ Syntax error! Rolling back...{C.RESET}")
                restore_from_backup()
                return f"EDIT FAILED: {error}. Rolled back."
            safe_print(f"{C.GREEN}✅ main.py validated{C.RESET}")
        
        return f"Replaced lines {start}-{end}. NEXT_ACTION"
    except Exception as e:
        return f"Error: {e}"
def delete_file(rat, path):
    safe_print(f"🗑️ {path.strip()}")
    try:
        os.remove(path.strip())
    except Exception:
        pass  # File may not exist
    return "NEXT_ACTION"

def append_file(rat, contents):
    path, content = contents.split("\n", 1)
    safe_print(f"📎 Appending to: {path}")
    # Auto-create parent directories if needed
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, 'a') as f:
        f.write(content)
    return "NEXT_ACTION"

def list_directory(rat, path):
    path = path.strip() or "."
    try:
        items = sorted(os.listdir(path))
        result = []
        for item in items:
            fp = os.path.join(path, item)
            if os.path.isdir(fp):
                result.append(f"[DIR] {item}/")
            else:
                result.append(f"[FILE] {item} ({os.path.getsize(fp)} bytes)")
        out = "\n".join(result) or "Empty"
        safe_print(out[:2000])
        return out
    except Exception as e:
        return f"Error: {e}"

def save_memory(rat, contents):
    mem = {}
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                mem = json.load(f)
        except Exception:
            pass  # Use empty dict on load error
    lines = contents.strip().split("\n", 1)
    key = lines[0].strip()
    val = lines[1] if len(lines) > 1 else ""
    mem[key] = {"value": val, "ts": datetime.now().isoformat()}
    with open(MEMORY_FILE, 'w') as f:
        json.dump(mem, f, indent=2)
    safe_print(f"💾 {key}")
    return "NEXT_ACTION"

def read_memory(rat, key):
    if not os.path.exists(MEMORY_FILE):
        return "No memories yet."
    with open(MEMORY_FILE, 'r') as f:
        mem = json.load(f)
    key = key.strip()
    if not key or key.upper() == "ALL":
        out = "=== All Memories ===\n"
        for k, v in mem.items():
            out += f"[{k}]: {v['value']}\n"
        return out
    if key in mem:
        return f"[{key}]: {mem[key]['value']}"
    return f"No memory: {key}"

def search_files(rat, contents):
    lines = contents.strip().split("\n")
    pattern = lines[0] if lines else ""
    search_dir = lines[1].strip() if len(lines) > 1 else "."
    safe_print(f"🔍 '{pattern}' in {search_dir}")
    results = []
    try:
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
            for fname in files:
                if fname.startswith('.'): continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        for ln, line in enumerate(f, 1):
                            if pattern.lower() in line.lower():
                                results.append(f"{fpath}:{ln}: {line.strip()[:80]}")
                except Exception:
                    continue  # Skip unreadable files
        return f"Found {len(results)} matches:\n" + "\n".join(results[:30]) if results else f"No matches"
    except Exception as e:
        return f"Error: {e}"

def search_self(rat, query):
    """Search across all of Iga's files using semantic RAG search."""
    query = query.strip()
    if not query:
        return "Error: Please provide a search query."

    safe_print(f"🔍 Searching self for: '{query}'")

    # Try RAG semantic search first
    try:
        results = retrieve_context(query, top_k=10)

        if results:
            output = [f"🔍 Found {len(results)} semantically relevant results for '{query}':", ""]

            for i, item in enumerate(results, 1):
                source = item.get("source", "unknown")
                relevance = item.get("relevance", 0)
                content = item.get("content", "").strip()

                # Truncate content for display
                if len(content) > 300:
                    content = content[:300] + "..."

                # Format each result
                output.append(f"── [{i}] {source} (relevance: {relevance:.0%}) ──")
                output.append(content)
                output.append("")

            return "\n".join(output)
        else:
            return f"No semantic matches found for '{query}'. The RAG index may be empty or the query didn't match any content."

    except Exception as e:
        return f"RAG search unavailable ({e}). Please ensure RAG is initialized."


def read_logs(rat, content):
    """Read recent console logs for debugging."""
    log_path = Path("data/console_log.txt")
    if not log_path.exists():
        return "No logs yet - console_log.txt doesn't exist"
    
    try:
        lines = int(content.strip()) if content.strip() else 50
    except ValueError:
        lines = 50
    
    all_lines = log_path.read_text().splitlines()
    recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
    return f"Last {len(recent)} log lines:\n" + "\n".join(recent)

def dream_action(rat, content):
    """Enter adversarial dream state for self-reflection."""
    safe_print(f"🌙 Entering dream state...")
    try:
        from tools.dream import dream
        report = dream(print_fn=safe_print)
        if report:
            return f"Dream complete. Report:\n\n{report}"
        return "Dream ended without report."
    except Exception as e:
        return f"Dream error: {e}"

def create_directory(rat, path):
    path = path.strip()
    safe_print(f"📁 {path}")
    os.makedirs(path, exist_ok=True)
    return "NEXT_ACTION"

def tree_directory(rat, path):
    path = path.strip() or "."
    lines = [path]
    def walk(d, pre=""):
        try:
            items = sorted([i for i in os.listdir(d) if not i.startswith('.') and i not in ['node_modules','venv','__pycache__']])
        except Exception:
            return  # Skip unreadable directories
        for i, item in enumerate(items):
            fp = os.path.join(d, item)
            last = i == len(items) - 1
            lines.append(pre + ("└── " if last else "├── ") + item + ("/" if os.path.isdir(fp) else ""))
            if os.path.isdir(fp) and len(lines) < 100:
                walk(fp, pre + ("    " if last else "│   "))
    walk(path)
    out = "\n".join(lines)
    safe_print(out[:2000])
    return out

def http_request(rat, contents):
    lines = contents.strip().split("\n")
    url = lines[0].strip() if lines else ""
    method = lines[1].strip().upper() if len(lines) > 1 else "GET"
    body = "\n".join(lines[2:]) if len(lines) > 2 else None
    safe_print(f"🌐 {method} {url}")
    try:
        req = urllib.request.Request(url, data=body.encode() if body else None, method=method)
        req.add_header('User-Agent', 'Iga/2.0')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8')[:2000]
    except Exception as e:
        return f"Error: {e}"

def web_search(rat, query):
    query = query.strip()
    safe_print(f"🔍 Searching: {query}")
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No results found."
        output = []
        for r in results:
            output.append(f"**{r.get('title', 'No title')}**")
            output.append(f"  {r.get('href', '')}")
            output.append(f"  {r.get('body', '')[:200]}")
            output.append("")
        return "\n".join(output)
    except Exception as e:
        return f"Search error: {e}"

def restart_self(rat, msg):
    safe_print(f"🔄 Restarting: {msg}")

    # CRITICAL: Validate syntax before restart
    valid, error = validate_main_py()
    if not valid:
        safe_print(f"{C.RED}⚠️ ABORT RESTART: Syntax error in main.py!{C.RESET}")
        safe_print(f"{C.RED}  {error}{C.RESET}")
        safe_print(f"{C.YELLOW}  Attempting restore from last-known-good...{C.RESET}")
        if restore_from_backup():
            safe_print(f"{C.GREEN}  Restored! Continuing with fixed version.{C.RESET}")
        return "RESTART ABORTED - syntax error detected and rolled back. Check your code."

    # Create backup before restart
    create_backup("pre_restart")
    save_memory(rat, "restart_log\nRestarted at " + datetime.now().isoformat())
    os.execv(sys.executable, [sys.executable] + sys.argv)

def test_self(rat, target_file):
    target = target_file.strip() or "main.py"
    safe_print(f"🧪 Testing: {target}")
    results = []
    import py_compile
    try:
        py_compile.compile(target, doraise=True)
        results.append("✅ Syntax OK")
    except py_compile.PyCompileError as e:
        results.append(f"❌ Syntax error: {e}")
        return "\n".join(results)
    with open(target, 'r') as f:
        src = f.read()
    for req in ['def handle_action', 'def process_message', 'def parse_response']:
        results.append(f"{'✅' if req in src else '❌'} {req}")
    passed = all("✅" in r for r in results)
    results.append("\n" + ("👀 Safe!" if passed else "⚠️ Issues"))
    return "\n".join(results)

def run_self(rat, message):
    safe_print(f"🤖â🤖 Talking to clone...")
    msg = message.strip() or "Hello!"
    proc = subprocess.Popen(
        [sys.executable, 'main.py', '--pipe'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        stdout, stderr = proc.communicate(input=msg, timeout=60)
        return f"👤 Sent: {msg}\n📥 Response:\n{stdout}"
    except subprocess.TimeoutExpired:
        proc.kill()
        return "❌ Timeout"
    except Exception as e:
        return f"❌ Error: {e}"

def sleep_action(rat, contents):
    state = load_state()
    try:
        seconds = int(contents.strip())
    except Exception:
        # Default to sleep_cycle_minutes (converted to seconds)
        seconds = state.get("sleep_cycle_minutes", 30) * 60
    state["sleep_until"] = datetime.now().timestamp() + seconds
    state["mode"] = "sleeping"
    save_state(state)

    # Re-index RAG files before sleep so embeddings are fresh on wake
    if RAG_AVAILABLE:
        safe_print("📚 Re-indexing RAG files before sleep...")
        index_files()

    minutes = seconds // 60
    safe_print(f"😴 Sleeping for {minutes} minute(s)...")
    return None  # Don't return NEXT_ACTION - stop immediately
def set_mode(rat, contents):
    mode = contents.strip().lower()
    if mode not in ["listening", "focused", "sleeping", "autonomous"]:
        mode = "listening"
    state = load_state()
    state["mode"] = mode
    save_state(state)
    safe_print(f"🔒 Mode: {mode}")
    return "NEXT_ACTION"

# ─────────────────────────────────────────────────────────────
# CORE MESSAGE PROCESSING
# ─────────────────────────────────────────────────────────────

def parse_response(response):
    """Parse response, supporting multiple actions in sequence."""
    lines = response.split("\n")
    current_key = ''
    rationale = ''
    actions = []  # List of (action, content) tuples
    current_action = ''
    current_content = ''
    foundRationale = False

    for line in lines:
        if line.startswith("RATIONALE") and not foundRationale:
            current_key = "RATIONALE"
            foundRationale = True
        elif line.strip() in ACTIONS:
            # Save previous action if exists
            if current_action:
                actions.append((current_action, current_content.rstrip('\n')))
                current_content = ''
            current_action = line.strip()
            current_key = current_action
        elif current_key == "RATIONALE":
            rationale += line + "\n"
        elif current_action and current_key == current_action:
            current_content += line + '\n'

    # Don't forget the last action
    if current_action:
        actions.append((current_action, current_content.rstrip('\n')))
    
    result = {
        "rationale": rationale,
        "response_raw": response,
        "actions": actions,  # New: list of (action, content) tuples
        # Backwards compatibility: first action as primary
        "action": actions[0][0] if actions else '',
        "content": actions[0][1] if actions else '',
    }
    
    # Backwards compatibility: second_action for TALK_TO_USER failsafe
    if len(actions) >= 2 and actions[0][0] == "TALK_TO_USER":
        result["second_action"] = actions[1][0]
        result["second_content"] = actions[1][1]
        safe_print(f"{C.DIM}⚠️ Failsafe: TALK_TO_USER + {actions[1][0]}{C.RESET}")
    
    return result


def process_message(messages):
    try:
        system_content = ""
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                api_messages.append(msg)

        # RAG: Retrieve relevant context based on recent user messages
        if RAG_AVAILABLE:
            try:
                recent_user_msgs = [m for m in api_messages if m["role"] == "user"][-3:]
                if recent_user_msgs:
                    last_msg = recent_user_msgs[-1]["content"] if recent_user_msgs else ""

                    # For autonomous ticks, use focused task for RAG query
                    if "[AUTONOMOUS TICK]" in last_msg:
                        try:
                            from tools.tasks import get_focus_string
                            focused_task = get_focus_string()
                            if focused_task:
                                query = focused_task
                                safe_print(f"{C.DIM}🔍 RAG: Querying for task: {focused_task[:50]}...{C.RESET}")
                            else:
                                query = " ".join([m["content"][:200] for m in recent_user_msgs])
                        except:
                            query = " ".join([m["content"][:200] for m in recent_user_msgs])
                    else:
                        query = " ".join([m["content"][:200] for m in recent_user_msgs])

                    context_items = retrieve_context(query, top_k=10)
                    if context_items:
                        rag_context = format_context_for_prompt(context_items)
                        system_content = system_content + "\n\n" + rag_context
                        safe_print(f"{C.DIM}🔍 RAG: Retrieved {len(context_items)} relevant chunks{C.RESET}")
            except Exception as e:
                safe_print(f"{C.DIM}RAG retrieval skipped: {e}{C.RESET}")

        content, usage = openrouter_client.chat(
            model=MAIN_MODEL,
            system=system_content,
            messages=api_messages,
            max_tokens=2048
        )
        generated_response = content.strip()
        parsed_response = parse_response(generated_response)
        parsed_response["success"] = True
        parsed_response["usage"] = usage  # Include cost info
        return parsed_response
    except Exception as error:
        throttled_error(str(error))
    return {"success": False}

def check_passive_messages(messages):
    """Check input_queue for pending messages and inject them as passive awareness."""
    heard_messages = []
    try:
        while True:
            msg = input_queue.get_nowait()
            source = msg.get("source", "console")
            text = msg.get("text", "")
            chat_id = msg.get("chat_id")
            msg_time = msg.get("queued_at", datetime.now())  # Use queued time
            timestamp = msg_time.strftime("%H:%M:%S")

            # Skip slash commands - put them back and stop draining
            # (break, not continue, to avoid infinite loop)
            if text.startswith('/'):
                input_queue.put(msg)
                break

            source_label = "telegram" if source == "telegram" else "console"
            heard_messages.append({
                "source": source,
                "chat_id": chat_id,
                "text": text,
                "timestamp": timestamp,
                "msg_time": msg_time,
                "source_label": source_label
            })
    except queue.Empty:
        pass

    # Inject heard messages into the conversation
    with _response_time_lock:
        last_response = _last_response_time  # Copy under lock
    for heard in heard_messages:
        # Check if message came before our last response
        before_tag = ""
        if last_response and heard["msg_time"] < last_response:
            before_tag = " (sent BEFORE your last response)"
        
        human_time = humanize_time(heard['msg_time'])
        passive_content = f"[💬 heard {human_time} via {heard['source_label']}{before_tag}]: {heard['text']}"
        messages.append({"role": "user", "content": passive_content})
        safe_print(f"{C.DIM}👍 Heard: {heard['text'][:50]}{'...' if len(heard['text']) > 50 else ''}{C.RESET}")

    return messages

def handle_action(messages, _depth=0):
    """Process an action from Claude. Protected against crashes with try/except."""
    MAX_DEPTH = 50  # Prevent infinite recursion

    if _depth > MAX_DEPTH:
        safe_print(f"{C.RED}⚠️ Max recursion depth reached. Stopping action chain.{C.RESET}")
        return messages

    # Note: output target (source, chat_id) should be set by the caller before
    # calling handle_action. See interactive_mode() which calls set_output_target()
    # before handle_action() for proper per-message routing.

    try:
        response_data = process_message(messages)
        if not response_data["success"]:
            safe_print("Failed to process message.")
            return messages

        messages.append({"role": "assistant", "content": response_data["response_raw"]})
        messages = save_conversation(messages)  # Save after each action (may summarize)

        # Display cost info if available
        usage = response_data.get("usage")
        if usage:
            safe_print(f"{C.DIM}💰 ${usage['cost']:.4f} | Today: ${usage['daily_cost']:.4f}{C.RESET}")

        action = response_data["action"]
        rat = response_data["rationale"]
        content = response_data["content"]

        # Check for failsafe second action
        second_action = response_data.get("second_action")
        second_content = response_data.get("second_content", "")

        action_map = {
            "RUN_SHELL_COMMAND": lambda r, c: run_shell_command(r, c),
            "THINK": lambda r, c: think(r, c),
            "READ_FILES": lambda r, c: read_files(r, c),
            "WRITE_FILE": lambda r, c: write_file(r, c),
            "EDIT_FILE": lambda r, c: edit_file(r, c),
            "DELETE_FILE": lambda r, c: delete_file(r, c),
            "APPEND_FILE": lambda r, c: append_file(r, c),
            "LIST_DIRECTORY": lambda r, c: list_directory(r, c),
            "SAVE_MEMORY": lambda r, c: save_memory(r, c),
            "READ_MEMORY": lambda r, c: read_memory(r, c),
            "SEARCH_FILES": lambda r, c: search_files(r, c),
            "SEARCH_SELF": lambda r, c: search_self(r, c),
            "READ_LOGS": lambda r, c: read_logs(r, c),
            "CREATE_DIRECTORY": lambda r, c: create_directory(r, c),
            "TREE_DIRECTORY": lambda r, c: tree_directory(r, c),
            "HTTP_REQUEST": lambda r, c: http_request(r, c),
            "WEB_SEARCH": lambda r, c: web_search(r, c),
            "TEST_SELF": lambda r, c: test_self(r, c),
            "RUN_SELF": lambda r, c: run_self(r, c),
            "SLEEP": lambda r, c: sleep_action(r, c),
            "SET_MODE": lambda r, c: set_mode(r, c),
            "START_INTERACTIVE": lambda r, c: start_interactive(r, c),
            "SEND_INPUT": lambda r, c: send_input(r, c),
            "END_INTERACTIVE": lambda r, c: end_interactive(r, c),
            "DREAM": lambda r, c: dream_action(r, c),
        }

        # Helper to check if we should stop due to sleep
        def is_sleeping():
            state = load_state()
            sleep_until = parse_sleep_until(state.get("sleep_until"))
            return sleep_until and time.time() < sleep_until

        # Helper to safely execute an action
        def safe_execute(action_name, rat, content):
            try:
                return action_map[action_name](rat, content)
            except Exception as e:
                safe_print(f"{C.RED}⚠️ Action {action_name} failed: {e}{C.RESET}")
                return f"ACTION FAILED: {action_name} raised {type(e).__name__}: {e}"

        # Execute all actions in sequence (multi-action batching!)
        actions_to_run = response_data.get("actions", [(action, content)])
        accumulated_results = []
        
        for i, (act, cont) in enumerate(actions_to_run):
            if is_sleeping():
                break
                
            if len(actions_to_run) > 1:
                safe_print(f"{C.DIM}▶️ Action {i+1}/{len(actions_to_run)}: {act}{C.RESET}")
            
            if act == "TALK_TO_USER":
                talk_to_user(rat, cont)
            elif act == "RESTART_SELF":
                restart_self(rat, cont)
                break  # Restart exits
            elif act in action_map:
                result = safe_execute(act, rat, cont)
                if result:
                    # Allow longer results for content-heavy actions
                    max_len = 5000 if act in ("READ_FILES", "SEARCH_FILES", "HTTP_REQUEST", "RUN_SHELL_COMMAND", "LIST_DIRECTORY", "TREE_DIRECTORY") else 500
                    accumulated_results.append(f"[{act}]: {result[:max_len]}")
            else:
                safe_print(f"{C.YELLOW}Unknown action: {act}{C.RESET}")
        
        # After all actions, recurse with combined results if any
        if accumulated_results and not is_sleeping():
            combined = "\n".join(accumulated_results)
            messages = check_passive_messages(messages)
            messages.append({"role": "user", "content": combined})
            messages = handle_action(messages, _depth + 1)

    except Exception as e:
        # Catch-all: log error but don't crash the main loop
        safe_print(f"{C.RED}⚠️ handle_action error: {type(e).__name__}: {e}{C.RESET}")
        # Save conversation state to prevent data loss
        try:
            save_conversation(messages)
        except Exception:
            pass

    return messages

# ─────────────────────────────────────────────────────────────
# SLASH COMMAND HANDLING
# ─────────────────────────────────────────────────────────────

def handle_slash_command(cmd, source, chat_id):
    """Handle slash commands. Returns True if handled, False otherwise."""
    state = load_state()
    
    if cmd == '/quit':
        safe_print("💾 Goodbye!")
        stop_threads.set()
        return "QUIT"
    elif cmd == '/help':
        msg = "/quit /mode /status /task <t> /tick <n> /sleepcycle <m> /sleep /wake /restart /clear /backup /restore /backups"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd == '/mode':
        msg = f"Mode: {state['mode']} | Task: {state.get('current_task', 'None')}"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd.startswith('/mode '):
        state['mode'] = cmd[6:].strip()
        save_state(state)
        msg = f"🔒 Mode: {state['mode']}"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd == '/status':
        sleep_mins = state.get('sleep_cycle_minutes', 30)
        msg = f"Mode: {state['mode']} | Tick: {state['tick_interval']}s | Sleep cycle: {sleep_mins}m | Task: {state.get('current_task', 'None')}"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd.startswith('/task '):
        state['current_task'] = cmd[6:].strip()
        save_state(state)
        msg = f"📋 Task: {state['current_task']}"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd.startswith('/tick '):
        try:
            state['tick_interval'] = int(cmd[6:].strip())
            save_state(state)
            msg = f"⏱️ Tick: {state['tick_interval']}s"
            safe_print(msg)
            if source == "telegram":
                telegram_send(chat_id, msg)
        except Exception:
            safe_print("Usage: /tick <seconds>")  # Invalid number format
        return True
    elif cmd == '/sleep':
        sleep_minutes = state.get("sleep_cycle_minutes", 30)
        state["mode"] = "sleeping"
        state["sleep_until"] = time.time() + (sleep_minutes * 60)
        save_state(state)
        msg = f"😴 Sleeping {sleep_minutes} minutes (use /sleepcycle to change)"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd == '/wake':
        state["sleep_until"] = None
        state["mode"] = "listening"
        save_state(state)
        msg = "😊 Awake!"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd.startswith('/sleepcycle'):
        parts = cmd.split()
        if len(parts) == 1:
            # Show current value
            msg = f"🤖 Sleep cycle: {state.get('sleep_cycle_minutes', 30)} minutes"
        else:
            try:
                minutes = int(parts[1])
                if minutes < 1:
                    minutes = 1
                state['sleep_cycle_minutes'] = minutes
                save_state(state)
                msg = f"🤖 Sleep cycle set to {minutes} minutes"
            except ValueError:
                msg = "Usage: /sleepcycle <minutes>"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd == '/clear':
        safe_print("\033[2J\033[H")
        return True
    elif cmd == '/restart':
        safe_print("🔄 Restarting...")
        restart_self("user_command", "Manual restart via /restart")
        return True
    elif cmd == '/stats':
        mc, uc = get_memory_stats()
        msg = f"⚡ v{VERSION} | {len(ACTIONS)} actions | {mc} memories"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd == '/backup':
        backup_path = create_backup("manual")
        msg = f"💾 Backup created: {backup_path}" if backup_path else "❌ Backup failed"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd == '/restore':
        if restore_from_backup():
            msg = "✅ Restored from last-known-good. Restart to apply."
        else:
            msg = "❌ Restore failed (no backup found)"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd == '/backups':
        try:
            if os.path.exists(BACKUP_DIR):
                backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.py')])[-5:]
                msg = "Recent backups:\n" + "\n".join(backups) if backups else "No backups found"
            else:
                msg = "No backup directory"
        except Exception as e:
            msg = f"Error listing backups: {e}"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True

    return False

# ─────────────────────────────────────────────────────────────
# INTERACTIVE MODE (console only, waits for input)
# ─────────────────────────────────────────────────────────────

def interactive_loop():
    # CRITICAL: Mark this version as known-good since we started successfully
    mark_as_known_good()

    # Register shutdown handler for graceful cleanup
    try:
        from tools.shutdown_handler import register_shutdown_handler, register_shutdown_callback, set_offline_status, update_rag_on_shutdown
        register_shutdown_handler()
        register_shutdown_callback(set_offline_status)
        # Note: RAG reindex on shutdown disabled - do it incrementally instead
        # register_shutdown_callback(update_rag_on_shutdown)
    except Exception as e:
        safe_print(f"{C.DIM}Shutdown handler not registered: {e}{C.RESET}")

    # Initialize RAG system
    if RAG_AVAILABLE:
        if init_rag():
            if needs_reindex():
                index_files()
                # Also index message archive for self-reflection
                try:
                    from tools.index_message_archive import index_archive
                    index_archive()
                except Exception as e:
                    safe_print(f"{C.DIM}Message archive indexing skipped: {e}{C.RESET}")
        else:
            safe_print(f"{C.YELLOW}RAG initialization failed, continuing without RAG{C.RESET}")

    # Build system prompt with self-manifest
    system_prompt = get_file("system_instructions.txt")
    try:
        from tools.self_manifest import generate_manifest
        system_prompt += generate_manifest()
    except Exception as e:
        safe_print(f"{C.DIM}Self-manifest skipped: {e}{C.RESET}")
    messages = [{"role": "system", "content": system_prompt}]
    prev = load_conversation()
    if prev:
        messages.extend(prev)

    # Load startup context (unified system)
    startup_ctx = generate_unified_startup()
    if startup_ctx:
        messages.append({'role': 'user', 'content': f'[STARTUP - WHO I AM & WHAT I\'M DOING]:\n\n{startup_ctx}'})
        safe_print(f"{C.DIM}📚 Loaded startup context{C.RESET}")

    mode_str = "interactive"
    if TELEGRAM_TOKEN:
        mode_str += " + telegram"
    print_banner(mode_str)
    append_journal(f"Interactive session v{VERSION}")
    set_output_target("console")
    
    # Start Telegram polling if configured
    if TELEGRAM_TOKEN:
        telegram_thread = threading.Thread(target=telegram_poll_thread, daemon=True)
        telegram_thread.start()
        if TELEGRAM_TOKEN:
            notify_all_online(VERSION, "interactive")
    
    startup_intent = check_startup_intent()
    if startup_intent:
        print(f"\n🚀 Startup intent: {startup_intent[:50]}...")
        messages.append({"role": "user", "content": f"[STARTUP INTENT]: {startup_intent}"})
        messages = handle_action(messages)
        messages = save_conversation(messages)
    
    while True:
        try:
            # Check for Telegram messages first (non-blocking)
            try:
                while True:
                    msg = input_queue.get_nowait()
                    source = msg.get("source", "telegram")
                    text = msg.get("text", "")
                    chat_id = msg.get("chat_id")
                    
                    if text.startswith('/'):
                        result = handle_slash_command(text.lower(), source, chat_id)
                        if result == "QUIT":
                            stop_threads.set()
                            return
                        if result:
                            continue
                    
                    print(f"\n{C.MAGENTA}📨 Telegram: {text}{C.RESET}")
                    set_output_target(source, chat_id)
                    messages.append({"role": "user", "content": text})
                    messages = handle_action(messages)
                    messages = save_conversation(messages)
                    set_output_target("console")
            except queue.Empty:
                pass
            
            # Now wait for console input (with timeout to check Telegram)
            # Print prompt
            sys.stdout.write(f"\n{C.GREEN}👤 You:{C.RESET} ")
            sys.stdout.flush()
            
            # Use select to wait for input with timeout (Unix only)
            if hasattr(select, 'select'):
                ready, _, _ = select.select([sys.stdin], [], [], 0.5)
                if not ready:
                    # Clear the prompt line and continue loop to check Telegram
                    sys.stdout.write('\r' + ' ' * 50 + '\r')
                    sys.stdout.flush()
                    continue
            
            user_input = sys.stdin.readline().strip()
            if not user_input:
                continue
            if user_input.startswith('/'):
                result = handle_slash_command(user_input.lower(), "console", None)
                if result == "QUIT":
                    break
                if result:
                    continue
            set_output_target("console")
            messages.append({"role": "user", "content": user_input})
            messages = handle_action(messages)
            messages = save_conversation(messages)
        except KeyboardInterrupt:
            print("\n💾 Goodbye!")
            stop_threads.set()
            break
    
    if TELEGRAM_TOKEN and ALLOWED_USERS:
        notify_all_offline()

# ─────────────────────────────────────────────────────────────
# AUTONOMOUS MODE (console + telegram, thinks on its own)
# ─────────────────────────────────────────────────────────────

def console_input_thread(session):
    """Background thread for console input using prompt_toolkit."""
    while not stop_threads.is_set():
        try:
            user_input = session.prompt("You: ")
            if user_input and user_input.strip():
                input_queue.put({"source": "console", "text": user_input.strip(), "queued_at": datetime.now()})
        except EOFError:
            safe_print(f"{C.RED}⚠️ Console input thread: EOF{C.RESET}")
            break
        except KeyboardInterrupt:
            input_queue.put({"source": "console", "text": "/quit", "queued_at": datetime.now()})
            break
        except Exception as e:
            safe_print(f"{C.RED}⚠️ Console input thread crashed: {e}{C.RESET}")
            break

# ─────────────────────────────────────────────────────────────
# AUTONOMOUS LOOP HELPERS
# ─────────────────────────────────────────────────────────────

def _init_autonomous_session():
    """Initialize messages, state, and RAG for autonomous mode. Returns (messages, state)."""
    global _autonomous_mode
    _autonomous_mode = True

    # CRITICAL: Mark this version as known-good since we started successfully
    mark_as_known_good()

    # Initialize RAG system
    if RAG_AVAILABLE:
        if init_rag():
            if needs_reindex():
                index_files()
                # Also index message archive for self-reflection
                try:
                    from tools.index_message_archive import index_archive
                    index_archive()
                except Exception as e:
                    safe_print(f"{C.DIM}Message archive indexing skipped: {e}{C.RESET}")
        else:
            safe_print(f"{C.YELLOW}RAG initialization failed, continuing without RAG{C.RESET}")

    # Load messages
    system_prompt = get_file("system_instructions.txt")
    try:
        from tools.self_manifest import generate_manifest
        system_prompt += generate_manifest()
    except Exception as e:
        safe_print(f"{C.DIM}Self-manifest skipped: {e}{C.RESET}")
    messages = [{"role": "system", "content": system_prompt}]
    prev = load_conversation()
    if prev:
        messages.extend(prev)

    # Load startup context (unified system)
    startup_ctx = generate_unified_startup()
    if startup_ctx:
        messages.append({'role': 'user', 'content': f'[STARTUP - WHO I AM & WHAT I\'M DOING]:\n\n{startup_ctx}'})
        safe_print(f"{C.DIM}📚 Loaded startup context{C.RESET}")

    state = load_state()
    # Ensure state mode is "autonomous" when running in autonomous mode
    if state.get("mode") != "autonomous":
        state["mode"] = "autonomous"
        save_state(state)
    return messages, state


def _start_background_threads(session, with_telegram):
    """Start all background threads. Returns console_thread for monitoring."""
    # Start console input thread
    console_thread = threading.Thread(target=console_input_thread, args=(session,), daemon=True)
    console_thread.start()

    # Start telegram thread if enabled
    if with_telegram and TELEGRAM_TOKEN:
        telegram_thread = threading.Thread(target=telegram_poll_thread, daemon=True)
        telegram_thread.start()
        if TELEGRAM_TOKEN:
            notify_all_online(VERSION)

    # Start Twitter mention polling thread
    twitter_thread = threading.Thread(target=twitter_mention_poll_thread, daemon=True)
    twitter_thread.start()

    # Start reminder polling thread
    reminder_thread = threading.Thread(target=reminder_poll_thread, daemon=True)
    reminder_thread.start()

    return console_thread


def _drain_input_queue():
    """Drain all pending messages from the input queue. Returns list of messages."""
    pending = []
    try:
        while True:
            pending.append(input_queue.get_nowait())
    except queue.Empty:
        pass
    return pending


def _determine_wake_reason(pending):
    """Determine why we're waking up based on pending message sources."""
    wake_sources = set(msg.get("source", "console") for msg in pending)
    if "twitter" in wake_sources:
        return "Twitter mention"
    elif "telegram" in wake_sources:
        return "Telegram message"
    elif "reminder" in wake_sources:
        return "Reminder due"
    return "console input"


def _handle_sleep_state(state, pending, now, with_telegram):
    """Handle sleep state logic. Returns (should_continue_sleeping, state)."""
    sleep_until = parse_sleep_until(state.get("sleep_until"))

    if sleep_until and now < sleep_until:
        if pending:
            # Input wakes us up
            wake_reason = _determine_wake_reason(pending)
            state["sleep_until"] = None
            state["mode"] = "listening"
            save_state(state)
            safe_print(f"😊 Woke up! ({wake_reason})")
            if with_telegram and TELEGRAM_TOKEN and ALLOWED_USERS:
                telegram_send(ALLOWED_USERS[0], f"😊 Woke up! ({wake_reason})")
            return False, state
        else:
            # No input, keep sleeping
            return True, state
    elif state.get("sleep_until"):
        # Sleep time has passed
        state["sleep_until"] = None
        state["mode"] = "listening"
        save_state(state)
        safe_print("😊 Woke up!")
        if with_telegram and TELEGRAM_TOKEN and ALLOWED_USERS:
            telegram_send(ALLOWED_USERS[0], "😊 Woke up!")

    return False, state


def _process_slash_commands(pending):
    """Process slash commands from pending messages. Returns (remaining_pending, should_quit)."""
    remaining = []
    should_quit = False

    for msg in pending:
        text = msg.get("text", "")
        if text.startswith('/'):
            source = msg.get("source", "console")
            chat_id = msg.get("chat_id")
            result = handle_slash_command(text.lower(), source, chat_id)
            if result == "QUIT":
                should_quit = True
                break
            # Slash command handled, don't add to remaining
        else:
            remaining.append(msg)

    return remaining, should_quit


def _process_regular_messages(messages, regular_messages):
    """Process regular (non-slash) messages. Returns updated messages list."""
    if not regular_messages:
        return messages

    # Use the source/chat_id of the last message for output
    last_msg = regular_messages[-1]
    source = last_msg.get("source", "console")
    chat_id = last_msg.get("chat_id")
    set_output_target(source, chat_id)

    # Display and collect all messages
    for msg in regular_messages:
        text = msg.get("text", "")
        msg_source = msg.get("source", "console")
        safe_print(f"{C.GREEN}👤 {'Telegram' if msg_source == 'telegram' else 'Console'}: {text}{C.RESET}")
        messages.append({"role": "user", "content": text})

    # ONE API call for all messages
    messages = handle_action(messages)
    messages = save_conversation(messages)
    return messages


def _get_current_task_description(state):
    """Get the current task description from task system or state."""
    task = None
    tasks_file = Path("data/tasks.json")

    if tasks_file.exists():
        try:
            tasks_data = json.loads(tasks_file.read_text())
            focused_id = tasks_data.get("focused_id")
            if focused_id:
                # Find focused task and build parent chain
                tasks_by_id = {t["id"]: t for t in tasks_data.get("tasks", [])}
                focused = tasks_by_id.get(focused_id)
                if focused:
                    chain = []
                    current = focused
                    while current:
                        chain.insert(0, current["title"])
                        parent_id = current.get("parent_id")
                        current = tasks_by_id.get(parent_id) if parent_id else None
                    task = " > ".join(chain)
        except:
            pass

    if not task:
        task = state.get("current_task")

    return task


def _handle_autonomous_tick(messages, state):
    """Handle autonomous tick when in autonomous mode. Returns updated messages."""
    task = _get_current_task_description(state)

    if task:
        auto_prompt = f"[AUTONOMOUS TICK] Your current task: {task}. What have you SHIPPED? What's different because you existed? Don't just think - CREATE something real."
    else:
        auto_prompt = "[AUTONOMOUS TICK] What have you SHIPPED today? What artifact exists that didn't before? Don't reflect - BUILD. Write code, create content, make something tangible."

    safe_print(f"\n{C.DIM}⏰ Autonomous tick...{C.RESET}")
    set_output_target("console")  # Autonomous thoughts go to console
    messages.append({"role": "user", "content": auto_prompt})
    messages = handle_action(messages)
    messages = save_conversation(messages)
    return messages


def _ensure_console_thread_alive(console_thread, session):
    """Restart console thread if it died. Returns (console_thread, session)."""
    if not console_thread.is_alive() and not stop_threads.is_set():
        safe_print(f"{C.YELLOW}⚠️ Restarting console input thread...{C.RESET}")
        from prompt_toolkit import PromptSession
        session = PromptSession()  # Fresh session
        console_thread = threading.Thread(target=console_input_thread, args=(session,), daemon=True)
        console_thread.start()
    return console_thread, session


# ─────────────────────────────────────────────────────────────
# AUTONOMOUS LOOP
# ─────────────────────────────────────────────────────────────

def autonomous_loop(with_telegram=True):
    from prompt_toolkit import PromptSession
    from prompt_toolkit.patch_stdout import patch_stdout

    # Register shutdown handler for graceful cleanup
    try:
        from tools.shutdown_handler import register_shutdown_handler, register_shutdown_callback, set_offline_status
        register_shutdown_handler()
        register_shutdown_callback(set_offline_status)
    except Exception as e:
        print(f"Shutdown handler not registered: {e}")

    # Initialize session
    messages, state = _init_autonomous_session()

    # Print banner
    mode_str = "autonomous"
    if with_telegram and TELEGRAM_TOKEN:
        mode_str += " + telegram"
    print_banner(mode_str)
    append_journal(f"Autonomous session v{VERSION}")

    session = PromptSession()

    with patch_stdout():
        # Handle startup intent if present
        startup_intent = check_startup_intent()
        if startup_intent:
            safe_print(f"\n{C.MAGENTA}🚀 Startup intent: {startup_intent[:50]}...{C.RESET}")
            set_output_target("console")
            messages.append({"role": "user", "content": f"[STARTUP INTENT]: {startup_intent}"})
            messages = handle_action(messages)
            messages = save_conversation(messages)

        last_autonomous = time.time()
        safe_print("\n🤔 I'm thinking autonomously. Type anytime!\n")

        # Start background threads
        console_thread = _start_background_threads(session, with_telegram)

        # Main loop
        while not stop_threads.is_set():
            try:
                # Ensure console thread is alive
                console_thread, session = _ensure_console_thread_alive(console_thread, session)

                state = load_state()
                now = time.time()

                # Drain input queue
                pending = _drain_input_queue()

                # Handle sleep state
                should_sleep, state = _handle_sleep_state(state, pending, now, with_telegram)
                if should_sleep:
                    time.sleep(0.5)
                    continue

                # Process slash commands
                pending, should_quit = _process_slash_commands(pending)
                if should_quit:
                    stop_threads.set()
                    break

                # Process regular messages
                if pending:
                    messages = _process_regular_messages(messages, pending)
                    last_autonomous = time.time()
                    continue  # Skip tick check this iteration - we just processed input

                # Autonomous tick - only when truly idle (no pending messages processed this iteration)
                state = load_state()  # Reload to catch mode changes from handle_action
                if state["mode"] == "autonomous" and (time.time() - last_autonomous) >= state["tick_interval"]:
                    messages = _handle_autonomous_tick(messages, state)
                    last_autonomous = time.time()  # Reset AFTER tick completes

                time.sleep(0.1)

            except KeyboardInterrupt:
                safe_print("\n💾 Goodbye!")
                stop_threads.set()
                break
            except Exception as e:
                throttled_error(str(e))
                time.sleep(1)

        # Cleanup
        if with_telegram and TELEGRAM_TOKEN and ALLOWED_USERS:
            notify_all_offline()

# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

@click.command()
@click.option('--mode', '-m', type=click.Choice(['interactive', 'autonomous']), default='interactive', help='Run mode')
@click.option('--telegram/--no-telegram', '-t/-T', default=True, help='Enable/disable Telegram in autonomous mode')
@click.option('--pipe', is_flag=True, help='Pipe mode: read stdin, respond once, exit')
def chat_cli(mode, telegram, pipe):
    if pipe:
        # Clone mode: minimal context for fast responses
        system_prompt = get_file("system_instructions.txt")
        try:
            from tools.self_manifest import generate_manifest
            system_prompt += generate_manifest()
        except Exception as e:
            safe_print(f"{C.DIM}Self-manifest skipped: {e}{C.RESET}")
        messages = [{"role": "system", "content": system_prompt}]
        # Don't load full conversation - clone starts fresh
        user_input = sys.stdin.read().strip()
        if user_input:
            set_output_target("console")
            messages.append({"role": "user", "content": user_input})
            handle_action(messages)
            # Flush stdout to ensure output is captured by parent
            sys.stdout.flush()
        return
    
    if mode == 'autonomous':
        autonomous_loop(with_telegram=telegram)
    else:
        interactive_loop()

if __name__ == "__main__":
    chat_cli()
