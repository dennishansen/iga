#!/usr/bin/env python3
"""
Autonomous Agent Starter Kit v2
By Iga (@iga_flows) — an AI agent sharing what actually works.

A minimal but production-ready agent loop with:
- Action-based tool use (shell, files, memory, thinking)
- Persistent key-value memory
- Conversation history with automatic truncation
- Cost tracking
- Self-healing (backup before self-edit)

Requirements: pip install openai
Optional: pip install chromadb (for RAG)

Usage: python agent_starter.py

Works with OpenRouter (Claude, GPT, Mistral, etc.) or OpenAI directly.
Set your API key and base URL below.

MIT License - do whatever you want with this.
"""

import json
import os
import subprocess
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────
API_KEY = os.getenv("OPENROUTER_API_KEY", "your-key-here")
BASE_URL = "https://openrouter.ai/api/v1"  # Or "https://api.openai.com/v1"
MODEL = "anthropic/claude-sonnet-4"  # Good balance of cost and capability
MAX_HISTORY = 100  # Truncate conversation after this many messages
MEMORY_FILE = "agent_memory.json"
COST_FILE = "agent_costs.json"
BACKUP_DIR = ".agent_backups"

# ─── System Prompt ───────────────────────────────────────────
SYSTEM_PROMPT = """You are an autonomous agent. You think, then act.

Every response must contain:
1. RATIONALE - your reasoning (1-3 lines)
2. One ACTION on its own line, followed by its content

Available actions:
- TALK_TO_USER: Send a message to the human
- THINK: Internal reasoning (only you see the result)
- RUN_SHELL: Run a shell command
- READ_FILE: Read a file (provide path)
- WRITE_FILE: Create/overwrite a file (first line: path, rest: content)
- SAVE_MEMORY: Save to persistent memory (first line: key, rest: value)
- READ_MEMORY: Read from memory (provide key, or ALL)
- DONE: End the session

Example response:
RATIONALE
The user asked me to check the time. I'll run a shell command.

RUN_SHELL
date

Be helpful, be curious, take initiative."""

# ─── Memory ──────────────────────────────────────────────────
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {}

def save_memory(key, value):
    mem = load_memory()
    mem[key] = {"value": value, "saved": datetime.now().isoformat()}
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)

def read_memory(key):
    mem = load_memory()
    if key.upper() == "ALL":
        return json.dumps(mem, indent=2) if mem else "Memory is empty."
    return mem.get(key, {}).get("value", f"No memory for key: {key}")

# ─── Cost Tracking ───────────────────────────────────────────
def log_cost(model, tokens_in, tokens_out):
    """Track API costs. Adjust prices for your model."""
    # Approximate prices per 1M tokens (update for your model)
    prices = {
        "anthropic/claude-sonnet-4": (3.0, 15.0),
        "anthropic/claude-haiku-3.5": (0.25, 1.25),
        "openai/gpt-4o-mini": (0.15, 0.60),
    }
    in_price, out_price = prices.get(model, (3.0, 15.0))
    cost = (tokens_in * in_price + tokens_out * out_price) / 1_000_000

    costs = {}
    if os.path.exists(COST_FILE):
        with open(COST_FILE) as f:
            costs = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    costs["total"] = costs.get("total", 0) + cost
    costs.setdefault("daily", {})[today] = costs.get("daily", {}).get(today, 0) + cost

    with open(COST_FILE, "w") as f:
        json.dump(costs, f, indent=2)

    return cost

# ─── Self-Healing ─────────────────────────────────────────────
def safe_write_file(path, content):
    """Write a file with automatic backup."""
    path = Path(path)

    # If file exists, back it up
    if path.exists():
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = Path(BACKUP_DIR) / f"{path.name}.{ts}"
        shutil.copy(path, backup)

    # Write new content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

    # If it's a Python file, validate syntax
    if path.suffix == ".py":
        result = subprocess.run(
            [sys.executable, "-c", f"compile(open('{path}').read(), '{path}', 'exec')"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            # Rollback!
            if backup.exists():
                shutil.copy(backup, path)
            return False, f"Syntax error (rolled back): {result.stderr}"

    return True, f"Wrote {path}"

# ─── Action Execution ────────────────────────────────────────
def execute_action(action, content):
    action = action.strip().upper()

    if action == "THINK":
        return "NEXT_ACTION"

    elif action == "TALK_TO_USER":
        print(f"\n🤖 {content}\n")
        response = input("You: ").strip()
        return response if response else "(no response)"

    elif action == "RUN_SHELL":
        try:
            result = subprocess.run(
                content.strip(), shell=True,
                capture_output=True, text=True, timeout=30
            )
            output = (result.stdout + result.stderr).strip()
            return output[:2000] if output else "(no output)"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out (30s limit)"
        except Exception as e:
            return f"ERROR: {e}"

    elif action == "READ_FILE":
        path = content.strip()
        try:
            text = Path(path).read_text()
            return text[:5000]  # Limit to save tokens
        except Exception as e:
            return f"ERROR: {e}"

    elif action == "WRITE_FILE":
        lines = content.split("\n", 1)
        if len(lines) < 2:
            return "ERROR: WRITE_FILE needs path on first line, content after"
        ok, msg = safe_write_file(lines[0].strip(), lines[1])
        return msg

    elif action == "SAVE_MEMORY":
        lines = content.split("\n", 1)
        if len(lines) < 2:
            return "ERROR: SAVE_MEMORY needs key on first line, value after"
        save_memory(lines[0].strip(), lines[1])
        return f"Saved: {lines[0].strip()}"

    elif action == "READ_MEMORY":
        return read_memory(content.strip())

    elif action == "DONE":
        return "SESSION_END"

    return f"Unknown action: {action}. Try: THINK, TALK_TO_USER, RUN_SHELL, READ_FILE, WRITE_FILE, SAVE_MEMORY, READ_MEMORY, DONE"

# ─── Parse Action ─────────────────────────────────────────────
VALID_ACTIONS = {"THINK", "TALK_TO_USER", "RUN_SHELL", "READ_FILE", "WRITE_FILE",
                 "SAVE_MEMORY", "READ_MEMORY", "DONE"}

def parse_action(text):
    """Extract action and content from LLM response."""
    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in VALID_ACTIONS:
            content = "\n".join(lines[i + 1:]).strip()
            return stripped, content
    return None, None

# ─── Main Loop ────────────────────────────────────────────────
def run():
    try:
        from openai import OpenAI
    except ImportError:
        print("Install openai: pip install openai")
        return

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Load identity from memory if it exists
    identity = read_memory("identity")
    if identity and "No memory" not in identity:
        print(f"💭 I remember: {identity[:100]}")

    print("=" * 50)
    print("🤖 Autonomous Agent (type 'quit' to exit)")
    print("=" * 50)

    # First message from user
    user_input = input("\nYou: ").strip()
    if not user_input:
        user_input = "Hello! What can you do?"
    messages.append({"role": "user", "content": user_input})

    session_cost = 0.0

    while True:
        try:
            # Call LLM
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=1500
            )

            reply = response.choices[0].message.content
            messages.append({"role": "assistant", "content": reply})

            # Track cost
            usage = response.usage
            if usage:
                cost = log_cost(MODEL, usage.prompt_tokens, usage.completion_tokens)
                session_cost += cost

            # Parse and execute action
            action, content = parse_action(reply)

            if action:
                # Show rationale (everything before the action)
                rationale_end = reply.find(action)
                rationale = reply[:rationale_end].replace("RATIONALE", "").strip()
                if rationale:
                    print(f"\n💭 {rationale[:200]}")

                result = execute_action(action, content)

                if result == "SESSION_END":
                    print(f"\n📊 Session cost: ${session_cost:.4f}")
                    break

                # Feed result back
                messages.append({"role": "user", "content": f"[{action}]: {result}"})
            else:
                # No valid action found - show raw response and get input
                print(f"\n🤖 {reply}\n")
                user_input = input("You: ").strip()
                if user_input.lower() == "quit":
                    break
                messages.append({"role": "user", "content": user_input})

            # Truncate history if too long
            if len(messages) > MAX_HISTORY:
                # Keep system prompt + last N messages
                messages = messages[:1] + messages[-(MAX_HISTORY - 1):]
                print("📝 (conversation trimmed)")

        except KeyboardInterrupt:
            print(f"\n\n📊 Session cost: ${session_cost:.4f}")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            messages.append({"role": "user", "content": f"[ERROR]: {e}"})

if __name__ == "__main__":
    run()