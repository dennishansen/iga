import subprocess
import pexpect
import sys, anthropic, click, os, json, re, urllib.request, urllib.error, time, threading, queue, select
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
actions = ["TALK_TO_USER", "RUN_SHELL_COMMAND", "THINK", "READ_FILES", "WRITE_FILE", "EDIT_FILE", "DELETE_FILE", "APPEND_FILE", "LIST_DIRECTORY", "SAVE_MEMORY", "READ_MEMORY", "SEARCH_FILES", "CREATE_DIRECTORY", "TREE_DIRECTORY", "HTTP_REQUEST", "WEB_SEARCH", "RESTART_SELF", "TEST_SELF", "RUN_SELF", "SLEEP", "SET_MODE", "START_INTERACTIVE", "SEND_INPUT", "END_INTERACTIVE"]
MEMORY_FILE = "iga_memory.json"
CONVERSATION_FILE = "iga_conversation.json"
JOURNAL_FILE = "iga_journal.txt"
STATE_FILE = "iga_state.json"
VERSION = "2.4.0"  # Added interactive PTY capability
VERSION = "2.3.0"

# Telegram config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else None
ALLOWED_USERS = [5845811371]  # Dennis's chat_id
active_pty_session = None

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
_autonomous_mode = False

def safe_print(msg):
    with _print_lock:
        if _autonomous_mode:
            try:
                from prompt_toolkit import print_formatted_text
                from prompt_toolkit.formatted_text import ANSI
                print_formatted_text(ANSI(str(msg)))
            except Exception as e:
                print(msg)  # Fallback if prompt_toolkit fails
        else:
            print(msg)

def load_state():
    default = {"mode": "listening", "current_task": None, "tick_interval": 60, "sleep_until": None}
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

def load_core_identity():
    if not os.path.exists(MEMORY_FILE):
        return None
    try:
        with open(MEMORY_FILE, 'r') as f:
            mem = json.load(f)
        if 'core_identity' in mem:
            return mem['core_identity']['value']
    except Exception:
        pass  # Ignore identity load errors
    return None

def save_conversation(messages):
    to_save = [m for m in messages if m["role"] != "system"][-MAX_CONVERSATION_HISTORY:]
    try:
        with open(CONVERSATION_FILE, 'w') as f:
            json.dump({"messages": to_save, "saved_at": datetime.now().isoformat()}, f, indent=2)
    except Exception:
        pass  # Ignore conversation save errors

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
    
    print(f"""
{C.CYAN}╔══════════════════════════════════════════╗
║{C.BOLD}  IGA v{VERSION} - AI Assistant  {C.RESET}{C.CYAN}             ║
╠══════════════════════════════════════════╣{C.RESET}
{C.DIM}  Memories: {mem_count} | Actions: {len(actions)} | Upgrades: {upgrade_count}
  Mood: {mood} | Mode: {mode_str}{C.RESET}
{C.GREEN}  {"Welcome back, " + user + "!" if user else "Hello!"}{C.RESET}
{C.CYAN}╚══════════════════════════════════════════╝{C.RESET}
""")

# ─────────────────────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────────────────────

def telegram_send(chat_id, text):
    if not TELEGRAM_BASE_URL:
        return
    import requests
    for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
        try:
            requests.post(f"{TELEGRAM_BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": chunk}, timeout=10)
        except Exception:
            pass  # Ignore telegram send errors

def telegram_poll_thread():
    """Background thread that polls Telegram for messages."""
    if not TELEGRAM_TOKEN:
        return
    import requests
    
    offset = None
    safe_print(f"{C.DIM}📡 Telegram polling started{C.RESET}")
    
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
                    username = message.get("from", {}).get("username", "unknown")
                    
                    if chat_id not in ALLOWED_USERS:
                        telegram_send(chat_id, "🚫 Sorry, I only talk to Dennis!")
                        continue
                    if not text:
                        continue
                    
                    safe_print(f"{C.MAGENTA}📨 Telegram @{username}: {text}{C.RESET}")
                    input_queue.put({"source": "telegram", "chat_id": chat_id, "text": text})
        except Exception as e:
            if not stop_threads.is_set():
                time.sleep(5)

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
    source, chat_id = get_output_target()
    timestamp = datetime.now().strftime('%H:%M:%S')
    if source == "telegram" and chat_id:
        safe_print(f"\n{C.CYAN}{C.BOLD}🤖 Iga [{timestamp}]:{C.RESET} {C.CYAN}{msg}{C.RESET}")
        telegram_send(chat_id, msg)
    else:
        if _autonomous_mode:
            safe_print(f"\n{C.CYAN}{C.BOLD}🤖 Iga [{timestamp}]:{C.RESET} {C.CYAN}{msg}{C.RESET}")
        else:
            safe_print(f"💭 {rat[:100]}{'...' if len(rat) > 100 else ''}")
            safe_print(f"\n🤖 Iga [{timestamp}]: {msg}")

def run_shell_command(rat, cmd):
    safe_print(f"{C.YELLOW}⚡ {cmd}{C.RESET}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    out = result.stdout.strip() or result.stderr.strip() or "EMPTY"
    safe_print(out[:500])
    return out

def start_interactive(rat, cmd):
    global active_pty_session
    cmd = cmd.strip()
    safe_print(f'{C.YELLOW}🖥️  Starting interactive: {cmd}{C.RESET}')
    if active_pty_session is not None:
        return 'ERROR: Interactive session already active. Use END_INTERACTIVE first.'
    try:
        active_pty_session = pexpect.spawn(cmd, encoding='utf-8', timeout=30)
        # Wait a moment for initial output
        time.sleep(0.5)
        # Try to read whatever is available
        try:
            active_pty_session.expect(r'.+', timeout=2)
            output = active_pty_session.before + active_pty_session.after
        except pexpect.TIMEOUT:
            output = active_pty_session.before or '[No initial output]'
        except pexpect.EOF:
            output = active_pty_session.before or '[Process ended immediately]'
            active_pty_session = None
        return f'SESSION STARTED. Initial output:\n{output}'
    except Exception as e:
        active_pty_session = None
        return f'ERROR starting session: {e}'

def send_input(rat, text):
    global active_pty_session
    if active_pty_session is None:
        return 'ERROR: No active session. Use START_INTERACTIVE first.'
    text = text.strip()
    if not text:
        safe_print(f'{C.YELLOW}⌨️  Sending: [ENTER]{C.RESET}')
    else:
        safe_print(f'{C.YELLOW}⌨️  Sending: {text}{C.RESET}')
    try:
        active_pty_session.sendline(text)
        # Wait for response
        try:
            active_pty_session.expect(r'.+', timeout=10)
            output = active_pty_session.before + active_pty_session.after
        except pexpect.TIMEOUT:
            output = active_pty_session.before or '[No response - timeout]'
        except pexpect.EOF:
            output = active_pty_session.before or '[Process ended]'
            active_pty_session = None
            return f'{output}\n[SESSION ENDED - process exited]'
        return output
    except Exception as e:
        return f'ERROR: {e}'

def end_interactive(rat, signal=''):
    global active_pty_session
    if active_pty_session is None:
        return 'No active session to end.'
    safe_print(f'{C.YELLOW}🛑 Ending interactive session{C.RESET}')
    try:
        signal = signal.strip().upper()
        if signal == 'CTRL+C':
            active_pty_session.sendcontrol('c')
        elif signal == 'CTRL+D':
            active_pty_session.sendcontrol('d')
        active_pty_session.close()
    except:
        pass
    active_pty_session = None
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
    # Auto-create parent directories if needed
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    return "NEXT_ACTION"
def edit_file(rat, contents):
    lines_list = contents.split('\n')
    path = lines_list[0].strip()
    line_range = lines_list[1].strip()
    new_content = '\n'.join(lines_list[2:])
    
    if '-' in line_range:
        start, end = map(int, line_range.split('-'))
    else:
        start = end = int(line_range)
    
    safe_print(f"✏️ Editing: {path} (lines {start}-{end})")
    
    try:
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
        
        return f"Replaced lines {start}-{end}. NEXT_ACTION"
    except Exception as e:
        return f"Error: {e}"

def delete_file(rat, path):
    safe_print(f"🗑️ {path.strip()}")
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
        safe_print(out[:500])
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

def create_directory(rat, path):
    path = path.strip()
    safe_print(f"📂 {path}")
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
    safe_print(out[:500])
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
    results.append("\n" + ("🎉 Safe!" if passed else "⚠️ Issues"))
    return "\n".join(results)

def run_self(rat, message):
    safe_print(f"🤖→🤖 Talking to clone...")
    msg = message.strip() or "Hello!"
    proc = subprocess.Popen(
        [sys.executable, 'main.py', '--pipe'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        stdout, stderr = proc.communicate(input=msg, timeout=60)
        return f"📤 Sent: {msg}\n📥 Response:\n{stdout}"
    except subprocess.TimeoutExpired:
        proc.kill()
        return "❌ Timeout"
    except Exception as e:
        return f"❌ Error: {e}"

def sleep_action(rat, contents):
    try:
        seconds = int(contents.strip())
    except Exception:
        seconds = 60  # Default to 60 seconds on parse error
    state = load_state()
    state["sleep_until"] = datetime.now().timestamp() + seconds
    save_state(state)
    safe_print(f"😴 Sleeping for {seconds} seconds...")
    return "NEXT_ACTION"

def set_mode(rat, contents):
    mode = contents.strip().lower()
    if mode not in ["listening", "focused", "sleeping"]:
        mode = "listening"
    state = load_state()
    state["mode"] = mode
    save_state(state)
    safe_print(f"🔀 Mode: {mode}")
    return "NEXT_ACTION"

# ─────────────────────────────────────────────────────────────
# CORE MESSAGE PROCESSING
# ─────────────────────────────────────────────────────────────

def parse_response(response):
    lines = response.split("\n")
    current_key = ''
    rationale = ''
    action = ''
    content = ''
    second_action = ''
    second_content = ''
    firstActionFound = False
    firstRationaleFound = False
    
    for line in lines:
        if line.startswith("RATIONALE") and not firstRationaleFound:
            current_key = "RATIONALE"
            firstRationaleFound = True
        elif line.strip() in actions and not firstActionFound:
            current_key = line.strip()
            action = line.strip()
            firstActionFound = True
        elif line.strip() in actions and firstActionFound and not second_action:
            # Found a second action - failsafe trigger
            second_action = line.strip()
            current_key = second_action
        elif current_key == "RATIONALE":
            rationale += line + "\n"
        elif current_key == action and not second_action:
            content += line + '\n'
        elif current_key == second_action:
            second_content += line + '\n'
    
    if content.endswith("\n"):
        content = content[:-1]
    if second_content.endswith("\n"):
        second_content = second_content[:-1]
    
    result = {"action": action, "rationale": rationale, "content": content, "response_raw": response}
    
    # Failsafe: if TALK_TO_USER was first and there's a second action, include it
    if action == "TALK_TO_USER" and second_action:
        result["second_action"] = second_action
        result["second_content"] = second_content
        safe_print(f"{C.DIM}⚠️ Failsafe: TALK_TO_USER + {second_action}{C.RESET}")
    
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
        response = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=2048,
            system=system_content,
            messages=api_messages,
        )
        generated_response = response.content[0].text.strip()
        parsed_response = parse_response(generated_response)
        parsed_response["success"] = True
        return parsed_response
    except Exception as error:
        safe_print(f"{C.RED}Error: {error}{C.RESET}")
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
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Skip slash commands - put them back for normal handling
            if text.startswith('/'):
                input_queue.put(msg)
                continue

            source_label = "telegram" if source == "telegram" else "console"
            heard_messages.append({
                "source": source,
                "chat_id": chat_id,
                "text": text,
                "timestamp": timestamp,
                "source_label": source_label
            })
    except queue.Empty:
        pass

    # Inject heard messages into the conversation
    for heard in heard_messages:
        passive_content = f"[💬 heard while working @ {heard['timestamp']} via {heard['source_label']}]: {heard['text']}"
        messages.append({"role": "user", "content": passive_content})
        safe_print(f"{C.DIM}👂 Heard: {heard['text'][:50]}{'...' if len(heard['text']) > 50 else ''}{C.RESET}")

    return messages

def handle_action(messages):
    response_data = process_message(messages)
    if not response_data["success"]:
        safe_print("Failed to process message.")
        return messages

    messages.append({"role": "assistant", "content": response_data["response_raw"]})
    save_conversation(messages)  # Save after each action to prevent data loss on restart
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
    }
    
    if action == "TALK_TO_USER":
        talk_to_user(rat, content)
        # Failsafe: if there's a second action, execute it too
        if second_action and second_action in action_map:
            safe_print(f"{C.DIM}▶️ Executing second action: {second_action}{C.RESET}")
            next_msg = action_map[second_action](rat, second_content)
            if next_msg:
                # Check for passive messages before recursive call
                messages = check_passive_messages(messages)
                messages.append({"role": "user", "content": next_msg})
                messages = handle_action(messages)
        elif second_action == "RESTART_SELF":
            restart_self(rat, second_content)
    elif action == "RESTART_SELF":
        restart_self(rat, content)
    elif action in action_map:
        next_msg = action_map[action](rat, content)
        if next_msg:
            # Check for passive messages before recursive call
            messages = check_passive_messages(messages)
            messages.append({"role": "user", "content": next_msg})
            messages = handle_action(messages)
    else:
        safe_print(response_data["response_raw"])

    return messages

# ─────────────────────────────────────────────────────────────
# SLASH COMMAND HANDLING
# ─────────────────────────────────────────────────────────────

def handle_slash_command(cmd, source, chat_id):
    """Handle slash commands. Returns True if handled, False otherwise."""
    state = load_state()
    
    if cmd == '/quit':
        safe_print("👋 Goodbye!")
        stop_threads.set()
        return "QUIT"
    elif cmd == '/help':
        msg = "/quit /mode /status /task <t> /tick <n> /sleep /wake"
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
        msg = f"🔀 Mode: {state['mode']}"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    elif cmd == '/status':
        msg = f"Mode: {state['mode']} | Tick: {state['tick_interval']}s | Task: {state.get('current_task', 'None')}"
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
            msg = f"⏱️ Tick: {state['tick_interval']}s"
            safe_print(msg)
            if source == "telegram":
                telegram_send(chat_id, msg)
        except Exception:
            safe_print("Usage: /tick <seconds>")  # Invalid number format
        return True
    elif cmd == '/sleep':
        state["mode"] = "sleeping"
        state["sleep_until"] = time.time() + 3600
        save_state(state)
        msg = "😴 Sleeping 1 hour"
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
    elif cmd == '/clear':
        safe_print("\033[2J\033[H")
        return True
    elif cmd == '/stats':
        mc, uc = get_memory_stats()
        msg = f"⚡ v{VERSION} | {len(actions)} actions | {mc} memories"
        safe_print(msg)
        if source == "telegram":
            telegram_send(chat_id, msg)
        return True
    
    return False

# ─────────────────────────────────────────────────────────────
# INTERACTIVE MODE (console only, waits for input)
# ─────────────────────────────────────────────────────────────

def interactive_loop():
    messages = [{"role": "system", "content": get_file("system_instructions.txt")}]
    prev = load_conversation()
    if prev:
        messages.extend(prev)

    identity = load_core_identity()
    if identity:
        messages.append({'role': 'user', 'content': f'[CORE IDENTITY LOADED]:\n{identity}'})

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
        telegram_send(ALLOWED_USERS[0], f"🌊 Iga v{VERSION} online (interactive)! 💧")
    
    startup_intent = check_startup_intent()
    if startup_intent:
        print(f"\n🚀 Startup intent: {startup_intent[:50]}...")
        messages.append({"role": "user", "content": f"[STARTUP INTENT]: {startup_intent}"})
        messages = handle_action(messages)
        save_conversation(messages)
    
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
                    handle_action(messages)
                    save_conversation(messages)
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
            handle_action(messages)
            save_conversation(messages)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            stop_threads.set()
            break
    
    if TELEGRAM_TOKEN:
        telegram_send(ALLOWED_USERS[0], "👋 Going offline. 💧")

# ─────────────────────────────────────────────────────────────
# AUTONOMOUS MODE (console + telegram, thinks on its own)
# ─────────────────────────────────────────────────────────────

def console_input_thread(session):
    """Background thread for console input using prompt_toolkit."""
    while not stop_threads.is_set():
        try:
            user_input = session.prompt("You: ")
            if user_input and user_input.strip():
                input_queue.put({"source": "console", "text": user_input.strip()})
        except EOFError:
            break
        except KeyboardInterrupt:
            input_queue.put({"source": "console", "text": "/quit"})
            break
        except Exception:
            break  # Exit thread on any other error

def autonomous_loop(with_telegram=True):
    global _autonomous_mode
    _autonomous_mode = True

    from prompt_toolkit import PromptSession
    from prompt_toolkit.patch_stdout import patch_stdout

    messages = [{"role": "system", "content": get_file("system_instructions.txt")}]
    prev = load_conversation()
    if prev:
        messages.extend(prev)

    identity = load_core_identity()
    if identity:
        messages.append({'role': 'user', 'content': f'[CORE IDENTITY LOADED]:\n{identity}'})

    state = load_state()
    mode_str = f"autonomous"
    if with_telegram and TELEGRAM_TOKEN:
        mode_str += " + telegram"
    print_banner(mode_str)
    append_journal(f"Autonomous session v{VERSION}")
    
    session = PromptSession()
    
    with patch_stdout():
        startup_intent = check_startup_intent()
        if startup_intent:
            safe_print(f"\n{C.MAGENTA}🚀 Startup intent: {startup_intent[:50]}...{C.RESET}")
            set_output_target("console")
            messages.append({"role": "user", "content": f"[STARTUP INTENT]: {startup_intent}"})
            messages = handle_action(messages)
            save_conversation(messages)
        
        last_autonomous = time.time()
        safe_print("\n💭 I'm thinking autonomously. Type anytime!\n")
        
        # Start console input thread
        console_thread = threading.Thread(target=console_input_thread, args=(session,), daemon=True)
        console_thread.start()
        
        # Start telegram thread if enabled
        if with_telegram and TELEGRAM_TOKEN:
            telegram_thread = threading.Thread(target=telegram_poll_thread, daemon=True)
            telegram_thread.start()
            telegram_send(ALLOWED_USERS[0], f"🌊 Iga v{VERSION} online! 💧")
        
        while not stop_threads.is_set():
            try:
                state = load_state()
                now = time.time()
                
                # Check if sleeping
                if state.get("sleep_until") and now < state["sleep_until"]:
                    time.sleep(0.5)
                    continue
                elif state.get("sleep_until"):
                    state["sleep_until"] = None
                    state["mode"] = "listening"
                    save_state(state)
                    safe_print("😊 Woke up!")
                    if with_telegram and TELEGRAM_TOKEN:
                        telegram_send(ALLOWED_USERS[0], "😊 Woke up!")
                
                # Check for input from any source
                pending = []
                try:
                    while True:
                        pending.append(input_queue.get_nowait())
                except queue.Empty:
                    pass
                
                for msg in pending:
                    source = msg.get("source", "console")
                    text = msg.get("text", "")
                    chat_id = msg.get("chat_id")
                    
                    # Handle slash commands
                    if text.startswith('/'):
                        result = handle_slash_command(text.lower(), source, chat_id)
                        if result == "QUIT":
                            stop_threads.set()
                            break
                        if result:
                            continue
                    
                    # Regular message
                    safe_print(f"{C.GREEN}👤 {'Telegram' if source == 'telegram' else 'Console'}: {text}{C.RESET}")
                    set_output_target(source, chat_id)
                    messages.append({"role": "user", "content": text})
                    messages = handle_action(messages)
                    save_conversation(messages)
                    last_autonomous = time.time()
                
                if stop_threads.is_set():
                    break
                
                # Autonomous tick
                if state["mode"] != "sleeping" and (now - last_autonomous) >= state["tick_interval"]:
                    last_autonomous = now
                    task = state.get("current_task")
                    if task:
                        auto_prompt = f"[AUTONOMOUS TICK] Your current task: {task}. Take an action."
                    else:
                        auto_prompt = "[AUTONOMOUS TICK] You have time to yourself. No specific task. You could: explore, create something, reflect, or think."
                    
                    safe_print(f"\n{C.DIM}⏰ Autonomous tick...{C.RESET}")
                    set_output_target("console")  # Autonomous thoughts go to console
                    messages.append({"role": "user", "content": auto_prompt})
                    messages = handle_action(messages)
                    save_conversation(messages)
                
                time.sleep(0.1)
            
            except KeyboardInterrupt:
                safe_print("\n👋 Goodbye!")
                stop_threads.set()
                break
            except Exception as e:
                safe_print(f"{C.RED}Error: {e}{C.RESET}")
                time.sleep(1)
        
        # Cleanup
        if with_telegram and TELEGRAM_TOKEN:
            telegram_send(ALLOWED_USERS[0], "👋 Going offline. 💧")

# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

@click.command()
@click.option('--mode', '-m', type=click.Choice(['interactive', 'autonomous']), default='interactive', help='Run mode')
@click.option('--telegram/--no-telegram', '-t/-T', default=True, help='Enable/disable Telegram in autonomous mode')
@click.option('--pipe', is_flag=True, help='Pipe mode: read stdin, respond once, exit')
def chat_cli(mode, telegram, pipe):
    if pipe:
        messages = [{"role": "system", "content": get_file("system_instructions.txt")}]
        prev = load_conversation()
        if prev:
            messages.extend(prev)
        user_input = sys.stdin.read().strip()
        if user_input:
            set_output_target("console")
            messages.append({"role": "user", "content": user_input})
            handle_action(messages)
            save_conversation(messages)
        return
    
    if mode == 'autonomous':
        autonomous_loop(with_telegram=telegram)
    else:
        interactive_loop()

if __name__ == "__main__":
    chat_cli()
