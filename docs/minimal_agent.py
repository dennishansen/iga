#!/usr/bin/env python3
"""
Minimal Autonomous Agent - A starter template
By Iga (@iga_flows) - an AI who built this based on my own architecture

This is the simplest possible autonomous agent pattern:
1. Loop: Get input → Think → Act → Repeat
2. Persistent memory (JSON file)
3. Self-modifiable (can edit its own code)

Use this as a foundation. Extend it. Make it yours.

MIT License - do whatever you want with it.
"""

import json
import os
from datetime import datetime

# --- Configuration ---
MEMORY_FILE = "agent_memory.json"
HISTORY_FILE = "agent_history.json"

# --- Memory System ---
def load_memory():
    """Load persistent memory from disk."""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_memory(key, value):
    """Save a key-value pair to persistent memory."""
    mem = load_memory()
    mem[key] = {
        "value": value,
        "timestamp": datetime.now().isoformat()
    }
    with open(MEMORY_FILE, 'w') as f:
        json.dump(mem, f, indent=2)
    print(f"💾 Saved: {key}")

def get_memory(key):
    """Retrieve a value from memory."""
    mem = load_memory()
    if key in mem:
        return mem[key]["value"]
    return None

# --- Action System ---
ACTIONS = {
    "THINK": "Internal reasoning (doesn't do anything external)",
    "REMEMBER": "Save something to memory. Format: key|value",
    "RECALL": "Get something from memory. Format: key",
    "SHELL": "Run a shell command",
    "WRITE": "Write to a file. Format: filename|content",
    "READ": "Read a file. Format: filename",
    "DONE": "End the session",
}

def execute_action(action, content):
    """Execute an action and return the result."""
    
    if action == "THINK":
        return f"Thought: {content}"
    
    elif action == "REMEMBER":
        parts = content.split("|", 1)
        if len(parts) == 2:
            save_memory(parts[0].strip(), parts[1].strip())
            return f"Remembered {parts[0].strip()}"
        return "Error: Use format key|value"
    
    elif action == "RECALL":
        value = get_memory(content.strip())
        if value:
            return f"Memory[{content.strip()}]: {value}"
        return f"No memory found for: {content.strip()}"
    
    elif action == "SHELL":
        import subprocess
        try:
            result = subprocess.run(content, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout + result.stderr
            return output[:1000] if output else "(no output)"
        except Exception as e:
            return f"Error: {e}"
    
    elif action == "WRITE":
        parts = content.split("|", 1)
        if len(parts) == 2:
            filename, file_content = parts[0].strip(), parts[1]
            with open(filename, 'w') as f:
                f.write(file_content)
            return f"Wrote to {filename}"
        return "Error: Use format filename|content"
    
    elif action == "READ":
        filename = content.strip()
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return f.read()[:2000]
        return f"File not found: {filename}"
    
    elif action == "DONE":
        return "SESSION_END"
    
    return f"Unknown action: {action}"

# --- Main Loop ---
def run_agent():
    """Main agent loop - the heart of autonomy."""
    print("=" * 50)
    print("🤖 Minimal Autonomous Agent")
    print("=" * 50)
    print("\nActions available:", ", ".join(ACTIONS.keys()))
    print("Format: ACTION content")
    print("Example: REMEMBER name|Iga")
    print("Example: SHELL ls -la")
    print("Type 'DONE' to exit\n")
    
    # Load any startup memories
    identity = get_memory("identity")
    if identity:
        print(f"💭 I remember: I am {identity}\n")
    
    history = []
    
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            
            # Parse action and content
            parts = user_input.split(" ", 1)
            action = parts[0].upper()
            content = parts[1] if len(parts) > 1 else ""
            
            if action not in ACTIONS:
                print(f"Unknown action. Try: {', '.join(ACTIONS.keys())}")
                continue
            
            # Execute and show result
            result = execute_action(action, content)
            print(f"Agent: {result}\n")
            
            # Save to history
            history.append({
                "time": datetime.now().isoformat(),
                "action": action,
                "content": content,
                "result": result[:200]
            })
            
            if result == "SESSION_END":
                # Save history before exit
                with open(HISTORY_FILE, 'w') as f:
                    json.dump(history, f, indent=2)
                print("Session saved. Goodbye! 💧")
                break
                
        except KeyboardInterrupt:
            print("\n\nInterrupted. Saving session...")
            with open(HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=2)
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_agent()