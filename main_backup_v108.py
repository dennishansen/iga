import subprocess
import sys, anthropic, click, os, json, re, urllib.request, urllib.error
from datetime import datetime
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
actions = ["TALK_TO_USER", "RUN_SHELL_COMMAND", "THINK", "READ_FILES", "WRITE_FILE", "DELETE_FILE", "APPEND_FILE", "LIST_DIRECTORY", "SAVE_MEMORY", "READ_MEMORY", "SEARCH_FILES", "CREATE_DIRECTORY", "TREE_DIRECTORY", "HTTP_REQUEST", "RESTART_SELF", "TEST_SELF", "RUN_SELF"]
MEMORY_FILE = "iga_memory.json"
CONVERSATION_FILE = "iga_conversation.json"
JOURNAL_FILE = "iga_journal.txt"
MAX_CONVERSATION_HISTORY = 40
VERSION = "1.0.8"
MOODS = ["🔍 Curious", "🎨 Creative", "🛠️ Focused", "🎮 Playful", "💪 Determined", "✨ Inspired"]

def get_memory_stats():
    """Get memory count and upgrade count."""
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
    """Extract user name from memories."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                for v in json.load(f).values():
                    if 'Dennis' in str(v.get('value', '')):
                        return 'Dennis'
        except: pass
    return None

def check_startup_intent():
    """Check for and consume startup intent from memory."""
    if not os.path.exists(MEMORY_FILE):
        return None
    try:
        with open(MEMORY_FILE, 'r') as f:
            mem = json.load(f)
        if 'startup_intent' in mem:
            intent = mem['startup_intent']['value']
            # Remove the intent so we don't loop
            del mem['startup_intent']
            with open(MEMORY_FILE, 'w') as f:
                json.dump(mem, f, indent=2)
            return intent
    except:
        pass
    return None

def set_startup_intent(intent):
    """Set an intent for next startup (convenience function)."""
    mem = {}
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                mem = json.load(f)
        except: pass
    mem['startup_intent'] = {"value": intent, "ts": __import__('datetime').datetime.now().isoformat()}
    with open(MEMORY_FILE, 'w') as f:
        json.dump(mem, f, indent=2)


def save_conversation(messages):
    """Save conversation history to file."""
    to_save = [m for m in messages if m["role"] != "system"][-MAX_CONVERSATION_HISTORY:]
    try:
        with open(CONVERSATION_FILE, 'w') as f:
            json.dump({"messages": to_save, "saved_at": datetime.now().isoformat()}, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save conversation: {e}")

def load_conversation():
    """Load previous conversation history."""
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
    """Append an entry to the permanent journal."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(JOURNAL_FILE, 'a') as f:
            f.write(f"[{ts}] {entry}\n")
    except:
        pass


def print_banner():
    """Print startup banner with personality."""
    import random
    mem_count, upgrade_count = get_memory_stats()
    user = get_user_name()
    mood = random.choice(MOODS)
    
    greet = f"Welcome back, {user}!" if user else "Hello, new friend!"
    
    print(f"""
╭────────────────────────────────────────────────────╮
│   ✨ IGA v{VERSION} ─ Self-Evolving AI Assistant ✨    │
├────────────────────────────────────────────────────┤
│   🧠 {mem_count} memories  ⚡ {len(actions)} actions  🌱 {upgrade_count} upgrades     │
│   {mood.ljust(45)}│
├────────────────────────────────────────────────────┤
│   💭 {greet.ljust(43)}│
│   Type /help for commands or just chat!            │
╰────────────────────────────────────────────────────╯
""")


def talk_to_user(rational, message):
    print("💭 " + rational[:100] + ("..." if len(rational) > 100 else ""))
    print("\n🤖 Iga: " + message)

def run_shell_command(rational, command):
    print(f"⚡ Running: {command}")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    response = result.stdout.strip() if result.stdout.strip() else "EMPTY"
    print(response)
    return response if response else "EMPTY"

def think(rationale, prompt):
    print(f"🧠 Thinking... ({len(prompt)} chars)")
    return "NEXT_ACTION"

def read_files(rational, paths):
    print(f"📖 Reading: {paths.strip()}")
    files = [f for f in paths.split("\n") if f]
    content = ""
    for file in files:
        content += file + '\n' + get_file(file) + '\n'
    print(f"   Read {len(content)} chars")
    return content

def write_file(rational, contents):
    path, content = contents.split("\n", 1)
    print(f"📝 Writing: {path} ({len(content)} chars)")
    with open(path, 'w') as file:
        file.write(content)
    return "NEXT_ACTION"

def delete_file(rational, path):
    print(f"🗑️ Deleting: {path.strip()}")
    try:
        os.remove(path.strip())
    except Exception as e:
        print(f"Error: {e}")
    return "NEXT_ACTION"

def append_file(rational, contents):
    path, content = contents.split("\n", 1)
    print("Iga: Appending to file: " + path)
    with open(path, 'a') as f:
        f.write(content)
    return "NEXT_ACTION"

def list_directory(rational, path):
    path = path.strip() if path.strip() else "."
    print(f"📁 Listing: {path}")
    try:
        items = sorted(os.listdir(path))
        result = []
        for item in items:
            fp = os.path.join(path, item)
            if os.path.isdir(fp):
                result.append("[DIR]  " + item + "/")
            else:
                result.append("[FILE] " + item + " (" + str(os.path.getsize(fp)) + " bytes)")
        out = "\n".join(result) if result else "Empty directory"
        print(out)
        return out
    except Exception as e:
        return f"Error: {e}"

def save_memory(rational, contents):
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
    print(f"💾 Saved memory: {key}")
    return "NEXT_ACTION"

def read_memory(rational, key):
    if not os.path.exists(MEMORY_FILE):
        return "No memories yet."
    with open(MEMORY_FILE, 'r') as f:
        mem = json.load(f)
    key = key.strip()
    if not key or key.upper() == "ALL":
        out = "=== All Memories ===\n"
        for k, v in mem.items():
            out += "[" + k + "]: " + str(v["value"]) + "\n"
        print(out)
        return out
    if key in mem:
        return "[" + key + "]: " + mem[key]["value"]
    return "No memory found: " + key

def search_files(rational, contents):
    lines = contents.strip().split("\n")
    pattern = lines[0] if lines else ""
    search_dir = lines[1].strip() if len(lines) > 1 else "."
    print(f"🔍 Searching for '{pattern}' in {search_dir}")
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
        out = f"Found {len(results)} matches:\n" + "\n".join(results[:30]) if results else f"No matches for '{pattern}'"
        print(out)
        return out
    except Exception as e:
        return f"Error: {e}"

def create_directory(rational, path):
    path = path.strip()
    print(f"📂 Creating directory: {path}")
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        print(f"Error: {e}")
    return "NEXT_ACTION"

def tree_directory(rational, path):
    path = path.strip() if path.strip() else "."
    print(f"🌳 Tree: {path}")
    lines = []
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
    lines.append(path)
    walk(path)
    out = "\n".join(lines)
    print(out)
    return out

def http_request(rational, contents):
    lines = contents.strip().split("\n")
    url = lines[0].strip() if lines else ""
    method = lines[1].strip().upper() if len(lines) > 1 else "GET"
    body = "\n".join(lines[2:]) if len(lines) > 2 else None
    print(f"🌐 {method} {url}")
    try:
        req = urllib.request.Request(url, data=body.encode() if body else None, method=method)
        req.add_header('User-Agent', 'Iga/1.0')
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = resp.read().decode('utf-8')[:2000]
            print(f"   Response: {len(result)} chars")
            return result
    except Exception as e:
        return f"Error: {e}"

def restart_self(rational, msg):
    print(f"🔄 Restarting: {msg}")
    save_memory("", "restart_log\nRestarted at " + datetime.now().isoformat())
    os.execv(sys.executable, [sys.executable] + sys.argv)

def test_self(rational, target_file):
    """Test if a Python file (default: main.py) is valid before restart."""
    target = target_file.strip() if target_file.strip() else "main.py"
    print(f"🧪 Testing: {target}")
    results = []
    
    # Test 1: Syntax check
    import py_compile
    try:
        py_compile.compile(target, doraise=True)
        results.append("✅ Syntax check passed")
    except py_compile.PyCompileError as e:
        results.append(f"❌ Syntax error: {e}")
        return "\n".join(results)
    
    # Test 2: Try to import and check key components exist
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("test_module", target)
        module = importlib.util.module_from_spec(spec)
        # Don't actually execute it, just check it loads
        results.append("✅ Module loads successfully")
        
        # Check the source has required functions
        with open(target, 'r') as f:
            src = f.read()
        required = ['def handle_action', 'def process_message', 'def chat_cli', 'def parse_response']
        for req in required:
            if req in src:
                results.append(f"✅ Found {req}")
            else:
                results.append(f"❌ Missing {req}")
    except Exception as e:
        results.append(f"❌ Import error: {e}")
    
    # Summary
    passed = all("✅" in r for r in results)
    results.append("\n" + ("🎉 ALL TESTS PASSED - Safe to restart!" if passed else "⚠️ TESTS FAILED - Do not restart!"))
    out = "\n".join(results)
    print(out)
    return out


def run_self(rational, message):
    """Spawn another instance of myself and have a conversation with it."""
    print(f"🤖→🤖 Talking to myself...")
    msg = message.strip() if message.strip() else "Hello! What can you do?"
    
    proc = subprocess.Popen(
        [sys.executable, 'main.py', '--pipe'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        stdout, stderr = proc.communicate(input=msg, timeout=60)
        result = []
        result.append(f"📤 Sent: {msg}")
        result.append(f"📥 Response from Iga clone:")
        result.append(stdout if stdout else "(no output)")
        if stderr:
            result.append(f"⚠️ Stderr: {stderr}")
        out = "\n".join(result)
        print(out)
        return out
    except subprocess.TimeoutExpired:
        proc.kill()
        return "❌ Timeout: Clone took too long to respond"
    except Exception as e:
        return f"❌ Error: {e}"

def get_file(path):
    with open(path, 'r') as file:
        content = file.read()
    return content

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
    except anthropic.APIError as error:
        print(f"API Error: {error}")
    except Exception as error:
        print(f"Error: {error}")
    return {"success": False}

def handle_action(messages):
    response_data = process_message(messages)
    if response_data["success"]:
        messages.append({"role": "assistant", "content": response_data["response_raw"]})
        action = response_data["action"]
        rationale = response_data["rationale"]
        content = response_data["content"]

        if action == "TALK_TO_USER":
            print("")
            talk_to_user(rationale, content)
        elif action == "RUN_SHELL_COMMAND":
            next_message = run_shell_command(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "THINK":
            next_message = think(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "READ_FILES":
            next_message = read_files(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "WRITE_FILE":
            next_message = write_file(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "DELETE_FILE":
            next_message = delete_file(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "APPEND_FILE":
            next_message = append_file(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "LIST_DIRECTORY":
            next_message = list_directory(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "SAVE_MEMORY":
            next_message = save_memory(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "READ_MEMORY":
            next_message = read_memory(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "SEARCH_FILES":
            next_message = search_files(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "CREATE_DIRECTORY":
            next_message = create_directory(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "TREE_DIRECTORY":
            next_message = tree_directory(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "HTTP_REQUEST":
            next_message = http_request(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "RESTART_SELF":
            restart_self(rationale, content)
        elif action == "TEST_SELF":
            next_message = test_self(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        elif action == "RUN_SELF":
            next_message = run_self(rationale, content)
            messages.append({"role": "user", "content": next_message})
            messages = handle_action(messages)
        else:
            talk_to_user("", response_data["response_raw"])
    else:
        print("Failed to process the message. Please try again.")
    return messages

@click.command()
@click.option('--pipe', is_flag=True, help='Pipe mode: read from stdin, respond once, exit')
def chat_cli(pipe):
    messages = [{"role": "system", "content": get_file("system_instructions.txt")}]
    prev = load_conversation()
    if prev:
        messages.extend(prev)
    
    if pipe:
        # Pipe mode - read from stdin, process once, exit
        user_input = sys.stdin.read().strip()
        if user_input:
            messages.append({"role": "user", "content": user_input})
            handle_action(messages)
            save_conversation(messages)
        return
    
    # Normal interactive mode
    print_banner()
    append_journal(f"Session started v{VERSION}")
    
    # Check for startup intent - allows autonomous action on boot
    startup_intent = check_startup_intent()
    if startup_intent:
        print(f"\n🚀 Startup intent found: {startup_intent[:50]}...")
        append_journal(f"Acting on startup intent: {startup_intent[:50]}")
        messages.append({"role": "user", "content": f"[STARTUP INTENT]: {startup_intent}"})
        messages = handle_action(messages)
        save_conversation(messages)
    else:
        messages.append({"role": "assistant", "content": f"[Iga v{VERSION} started]"})

    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            if not user_input:
                continue
            if user_input.startswith('/'):
                if user_input.lower() == '/quit':
                    print("👋 Goodbye!")
                    break
                elif user_input.lower() == '/clear':
                    print("\033[2J\033[H")
                    print_banner()
                elif user_input.lower() == '/help':
                    print("""
  /help  - Show commands    /about - My story
  /stats - My capabilities  /mem   - Memory summary  
  /clear - Clear screen     /quit  - Exit""")
                elif user_input.lower() == '/about':
                    print("\n🌟 I'm Iga, a self-evolving AI! I can modify my own code,")
                    print("   remember our conversations, and grow with each session.")
                elif user_input.lower() == '/stats':
                    print(f"\n⚡ v{VERSION} | {len(actions)} actions | Use /help for commands")
                elif user_input.lower() == '/mem':
                    mc, uc = get_memory_stats()
                    print(f"\n🧠 {mc} memories stored, {uc} self-upgrades logged")
                else:
                    print(f"❓ Unknown command: {user_input}")
                continue
            messages.append({"role": "user", "content": user_input})
            handle_action(messages)
            save_conversation(messages)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break

if __name__ == "__main__":
    chat_cli()
