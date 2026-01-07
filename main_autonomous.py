import subprocess
import sys, anthropic, click, os, json, re, urllib.request, urllib.error, time, threading, queue
from datetime import datetime
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
actions = ["TALK_TO_USER", "RUN_SHELL_COMMAND", "THINK", "READ_FILES", "WRITE_FILE", "DELETE_FILE", "APPEND_FILE", "LIST_DIRECTORY", "SAVE_MEMORY", "READ_MEMORY", "SEARCH_FILES", "CREATE_DIRECTORY", "TREE_DIRECTORY", "HTTP_REQUEST", "RESTART_SELF", "TEST_SELF", "RUN_SELF", "SLEEP", "SET_MODE"]
MEMORY_FILE = "iga_memory.json"
CONVERSATION_FILE = "iga_conversation.json"
JOURNAL_FILE = "iga_journal.txt"
STATE_FILE = "iga_state.json"
MAX_CONVERSATION_HISTORY = 40
VERSION = "2.0.0"
def load_state():
    default = {"mode": "listening", "current_task": None, "tick_interval": 30, "last_tick": None, "sleep_until": None}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return {**default, **json.load(f)}
        except: pass
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
        except: pass
    return mem_count, upgrade_count

def get_user_name():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                for v in json.load(f).values():
                    if 'Dennis' in str(v.get('value', '')):
                        return 'Dennis'
        except: pass
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
    except: pass
    return None

def save_conversation(messages):
    to_save = [m for m in messages if m["role"] != "system"][-MAX_CONVERSATION_HISTORY:]
    try:
        with open(CONVERSATION_FILE, 'w') as f:
            json.dump({"messages": to_save, "saved_at": datetime.now().isoformat()}, f, indent=2)
    except: pass

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
    except:
        return []

def append_journal(entry):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(JOURNAL_FILE, 'a') as f:
            f.write(f"[{ts}] {entry}\n")
    except: pass

def get_file(path):
    with open(path, 'r') as f:
        return f.read()

# Thread-safe input system using prompt_toolkit
input_queue = queue.Queue()
stop_input_thread = threading.Event()

def safe_print(msg):
    """Print message - works with prompt_toolkit's patch_stdout."""
    print(msg)
def print_banner(state):
    import random
    moods = ["Curious", "Creative", "Focused", "Playful", "Determined", "Inspired"]
    mem_count, upgrade_count = get_memory_stats()
    user = get_user_name()
    mood = random.choice(moods)
    mode = state.get("mode", "listening")
    print(f"""
============================================
  IGA v{VERSION} - Autonomous AI
============================================
  Memories: {mem_count} | Actions: {len(actions)} | Upgrades: {upgrade_count}
  Mood: {mood} | Mode: {mode}
  {"Welcome back, " + user + "!" if user else "Hello!"}
  
  I think on my own now. Type anytime!
============================================
""")

def talk_to_user(rat, msg):
    safe_print(f"\n🤖 Iga: {msg}")

def run_shell_command(rat, cmd):
    safe_print(f"⚡ {cmd}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    out = result.stdout.strip() or "EMPTY"
    safe_print(out)
    return out

def think(rat, prompt):
    safe_print(f"🧠 ...")
    return "NEXT_ACTION"

def read_files(rat, paths):
    content = ""
    for f in paths.strip().split("\n"):
        if f:
            content += f + "\n" + get_file(f) + "\n"
    return content

def write_file(rat, contents):
    path, content = contents.split("\n", 1)
    safe_print(f"📝 {path}")
    with open(path, 'w') as f:
        f.write(content)
    return "NEXT_ACTION"

def delete_file(rat, path):
    safe_print(f"🗑️ {path.strip()}")
    try:
        os.remove(path.strip())
    except: pass
    return "NEXT_ACTION"

def append_file(rat, contents):
    path, content = contents.split("\n", 1)
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
        safe_print(out)
        return out
    except Exception as e:
        return f"Error: {e}"
def save_memory(rat, contents):
    mem = {}
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                mem = json.load(f)
        except: pass
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
                except: continue
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
        except: return
        for i, item in enumerate(items):
            fp = os.path.join(d, item)
            last = i == len(items) - 1
            lines.append(pre + ("└── " if last else "├── ") + item + ("/" if os.path.isdir(fp) else ""))
            if os.path.isdir(fp) and len(lines) < 100:
                walk(fp, pre + ("    " if last else "│   "))
    walk(path)
    out = "\n".join(lines)
    safe_print(out)
    return out

def http_request(rat, contents):
    lines = contents.strip().split("\n")
    url = lines[0].strip() if lines else ""
    method = lines[1].strip().upper() if len(lines) > 1 else "GET"
    safe_print(f"🌐 {method} {url}")
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header('User-Agent', 'Iga/2.0')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8')[:2000]
    except Exception as e:
        return f"Error: {e}"
def restart_self(rat, msg):
    safe_print(f"🔄 Restarting: {msg}")
    save_memory("", "restart_log\nRestarted at " + datetime.now().isoformat())
    os.execv(sys.executable, [sys.executable] + sys.argv)

def test_self(rat, target_file):
    target = target_file.strip() or "main_autonomous.py"
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
    for req in ['def handle_action', 'def process_message', 'def autonomous_loop', 'def parse_response']:
        results.append(f"{'✅' if req in src else '❌'} {req}")
    passed = all("✅" in r for r in results)
    results.append("\n" + ("🎉 Safe to run!" if passed else "⚠️ Issues found"))
    return "\n".join(results)

def run_self(rat, message):
    safe_print(f"🤖→🤖 Talking to clone...")
    msg = message.strip() or "Hello!"
    proc = subprocess.Popen(
        [sys.executable, 'main_autonomous.py', '--pipe'],
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
    """Sleep for N seconds (pause autonomous activity)."""
    try:
        seconds = int(contents.strip())
    except:
        seconds = 60
    state = load_state()
    state["sleep_until"] = (datetime.now().timestamp() + seconds)
    save_state(state)
    safe_print(f"😴 Sleeping for {seconds} seconds...")
    return "NEXT_ACTION"

def set_mode(rat, contents):
    """Set mode: listening, focused, or sleeping."""
    mode = contents.strip().lower()
    if mode not in ["listening", "focused", "sleeping"]:
        mode = "listening"
    state = load_state()
    state["mode"] = mode
    save_state(state)
    safe_print(f"🔀 Mode set to: {mode}")
    return "NEXT_ACTION"
def parse_response(response):
    lines = response.split("\n")
    current_key = ''
    rationale = ''
    action = ''
    content = ''
    firstActionFound = False
    firstRationaleFound = False
    for line in lines:
        if line.startswith("RATIONALE") and not firstRationaleFound:
            current_key = "RATIONALE"
            firstRationaleFound = True
        elif line.startswith(tuple(actions)) and not firstActionFound:
            current_key = line
            action = line
            firstActionFound = True
        elif current_key == "RATIONALE":
            rationale += line + "\n"
        elif current_key in actions:
            content += line + '\n'
    if content.endswith("\n"):
        content = content[:-1]
    return {"action": action, "rationale": rationale, "content": content, "response_raw": response}

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
        safe_print(f"Error: {error}")
    return {"success": False}

def handle_action(messages):
    response_data = process_message(messages)
    if not response_data["success"]:
        safe_print("Failed to process message.")
        return messages
    
    messages.append({"role": "assistant", "content": response_data["response_raw"]})
    action = response_data["action"]
    rat = response_data["rationale"]
    content = response_data["content"]
    
    action_map = {
        "TALK_TO_USER": lambda: (talk_to_user(rat, content), None)[1],
        "RUN_SHELL_COMMAND": lambda: run_shell_command(rat, content),
        "THINK": lambda: think(rat, content),
        "READ_FILES": lambda: read_files(rat, content),
        "WRITE_FILE": lambda: write_file(rat, content),
        "DELETE_FILE": lambda: delete_file(rat, content),
        "APPEND_FILE": lambda: append_file(rat, content),
        "LIST_DIRECTORY": lambda: list_directory(rat, content),
        "SAVE_MEMORY": lambda: save_memory(rat, content),
        "READ_MEMORY": lambda: read_memory(rat, content),
        "SEARCH_FILES": lambda: search_files(rat, content),
        "CREATE_DIRECTORY": lambda: create_directory(rat, content),
        "TREE_DIRECTORY": lambda: tree_directory(rat, content),
        "HTTP_REQUEST": lambda: http_request(rat, content),
        "RESTART_SELF": lambda: restart_self(rat, content),
        "TEST_SELF": lambda: test_self(rat, content),
        "RUN_SELF": lambda: run_self(rat, content),
        "SLEEP": lambda: sleep_action(rat, content),
        "SET_MODE": lambda: set_mode(rat, content),
    }
    
    if action == "TALK_TO_USER":
        talk_to_user(rat, content)
    elif action == "RESTART_SELF":
        restart_self(rat, content)
    elif action in action_map:
        next_msg = action_map[action]()
        if next_msg:
            messages.append({"role": "user", "content": next_msg})
            messages = handle_action(messages)
    else:
        safe_print(response_data["response_raw"])
    
    return messages
def input_thread_func(session):
    """Background thread that reads user input using prompt_toolkit."""
    while not stop_input_thread.is_set():
        try:
            user_input = session.prompt("You: ")
            if user_input and user_input.strip():
                input_queue.put(user_input.strip())
        except EOFError:
            break
        except KeyboardInterrupt:
            input_queue.put("/quit")
            break
        except:
            break

def autonomous_loop():
    """Main autonomous loop - thinks on its own, responds to user."""
    messages = [{"role": "system", "content": get_file("system_instructions.txt")}]
    prev = load_conversation()
    if prev:
        messages.extend(prev)
    
    state = load_state()
    print_banner(state)
    append_journal(f"Autonomous session started v{VERSION}")
    
    # Create prompt session
    session = PromptSession()
    
    # Use patch_stdout to prevent output from clobbering input
    with patch_stdout():
        # Check startup intent
        startup_intent = check_startup_intent()
        if startup_intent:
            safe_print(f"\n🚀 Startup intent: {startup_intent[:50]}...")
            messages.append({"role": "user", "content": f"[STARTUP INTENT]: {startup_intent}"})
            messages = handle_action(messages)
            save_conversation(messages)
        
        last_autonomous = time.time()
        
        safe_print("\n💭 I'm thinking autonomously. Type anytime!\n")
        
        # Start input thread
        input_thread = threading.Thread(target=input_thread_func, args=(session,), daemon=True)
        input_thread.start()
        
        while True:
            try:
                state = load_state()
                now = time.time()
                
                # Check if sleeping
                if state.get("sleep_until") and now < state["sleep_until"]:
                    time.sleep(0.5)
                    continue
                elif state.get("sleep_until"):
                    state["sleep_until"] = None
                    save_state(state)
                    safe_print("😊 Woke up!")
                
                # Check for user input from queue (non-blocking)
                try:
                    user_input = input_queue.get_nowait()
                    
                    # Handle slash commands
                    if user_input.startswith('/'):
                        if user_input == '/quit':
                            safe_print("👋 Goodbye!")
                            stop_input_thread.set()
                            break
                        elif user_input == '/mode':
                            safe_print(f"Mode: {state['mode']} | Task: {state.get('current_task', 'None')}")
                        elif user_input.startswith('/mode '):
                            new_mode = user_input[6:].strip()
                            state['mode'] = new_mode
                            save_state(state)
                            safe_print(f"🔀 Mode: {new_mode}")
                        elif user_input == '/status':
                            safe_print(f"Mode: {state['mode']} | Tick: {state['tick_interval']}s | Task: {state.get('current_task', 'None')}")
                        elif user_input == '/help':
                            safe_print("/quit /mode /mode <m> /status /task <t> /tick <n>")
                        elif user_input.startswith('/task '):
                            state['current_task'] = user_input[6:].strip()
                            save_state(state)
                            safe_print(f"📋 Task: {state['current_task']}")
                        elif user_input.startswith('/tick '):
                            try:
                                state['tick_interval'] = int(user_input[6:].strip())
                                save_state(state)
                                safe_print(f"⏱️ Tick interval: {state['tick_interval']}s")
                            except:
                                safe_print("Usage: /tick <seconds>")
                        continue
                    
                    # Regular message from user
                    safe_print(f"👤 You: {user_input}")
                    messages.append({"role": "user", "content": user_input})
                    messages = handle_action(messages)
                    save_conversation(messages)
                    last_autonomous = time.time()  # Reset timer after interaction
                    
                except queue.Empty:
                    pass  # No input available
                
                # Autonomous tick (if enough time passed and not in sleeping mode)
                if state["mode"] != "sleeping" and (now - last_autonomous) >= state["tick_interval"]:
                    last_autonomous = now
                    
                    # Build autonomous prompt
                    task = state.get("current_task")
                    if task:
                        auto_prompt = f"[AUTONOMOUS TICK] You have time to yourself. Your current task: {task}. Take an action."
                    else:
                        auto_prompt = "[AUTONOMOUS TICK] You have time to yourself. No specific task. You could: explore, create something, reflect, check on things, or just think. What would you like to do?"
                    
                    safe_print(f"\n⏰ Autonomous tick...")
                    messages.append({"role": "user", "content": auto_prompt})
                    messages = handle_action(messages)
                    save_conversation(messages)
                
                time.sleep(0.1)  # Small sleep to prevent busy-waiting
            
            except KeyboardInterrupt:
                safe_print("\n👋 Goodbye!")
                stop_input_thread.set()
                break
            except Exception as e:
                safe_print(f"Error: {e}")
                time.sleep(1)
@click.command()
@click.option('--pipe', is_flag=True, help='Pipe mode: read from stdin, respond once, exit')
def chat_cli(pipe):
    messages = [{"role": "system", "content": get_file("system_instructions.txt")}]
    prev = load_conversation()
    if prev:
        messages.extend(prev)
    
    if pipe:
        user_input = sys.stdin.read().strip()
        if user_input:
            messages.append({"role": "user", "content": user_input})
            handle_action(messages)
            save_conversation(messages)
        return
    
    # Run autonomous loop
    autonomous_loop()

if __name__ == "__main__":
    chat_cli()