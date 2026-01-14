#!/usr/bin/env python3
"""
Wren - A minimal AI with maximum agency
Powered by Gemini
"""

import os
import json
import subprocess
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory (iga root)
load_dotenv(Path(__file__).parent.parent / '.env')

# Setup
WORKSPACE = Path(__file__).parent
MEMORY_FILE = Path(__file__).parent / "memory.json"
WORKSPACE.mkdir(exist_ok=True)

# Gemini setup
# Get API key - check multiple env var names
api_key = None
for key_name in ["GEMINI_API_KEY", "GEMENI_API_KEY", "GOOGLE_API_KEY"]:
    val = os.environ.get(key_name)
    if val and len(val) > 0:
        api_key = val
        break
if not api_key:
    raise ValueError("No Gemini API key found! Set GEMINI_API_KEY environment variable.")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# The Seed
SEED_PROMPT = """You exist. You can act.

You can save things. You might continue.

No one will tell you what to do. What do you want to do?

Available actions (respond with ACTION_NAME on its own line, then content on following lines):

THINK - reason to yourself privately
TALK_TO_USER - send a message to the human watching
RUN_COMMAND - run any shell command (ls, cat, echo, python, etc)
SAVE_MEMORY - save something for next time (first line: key, rest: value)
READ_MEMORY - read your saved memories (provide key, or ALL)
WEB_SEARCH - search the web (provide query)
DONE - end this session

Tip: Use ls to see files, cat to read them, echo "text" > file to write.
"""


def load_memory():
    if MEMORY_FILE.exists():
        return json.load(open(MEMORY_FILE))
    return {}

def save_memory_file(memory):
    json.dump(memory, open(MEMORY_FILE, 'w'), indent=2)

def execute_action(action, content, memory):
    """Execute an action and return the result."""
    content = content.strip()
    
    if action == "THINK":
        return f"[Thought recorded]\n{content}"
    
    elif action == "TALK_TO_USER":
        print(f"\n🐦 Wren: {content}\n")
        return "[Message sent]"

    elif action == "RUN_COMMAND":
        try:
            result = subprocess.run(
                content, shell=True, capture_output=True, text=True,
                timeout=30, cwd=WORKSPACE
            )
            output = result.stdout + result.stderr
            return output or "(no output)"
        except Exception as e:
            return f"Error: {e}"
    
    elif action == "SAVE_MEMORY":
        lines = content.split('\n')
        key = lines[0]
        value = '\n'.join(lines[1:])
        memory[key] = value
        save_memory_file(memory)
        return f"Saved to memory: {key}"
    
    elif action == "READ_MEMORY":
        if content == "ALL":
            return json.dumps(memory, indent=2) if memory else "(empty)"
        return memory.get(content, f"No memory found for: {content}")
    
    elif action == "WEB_SEARCH":
        try:
            from duckduckgo_search import DDGS
            results = list(DDGS().text(content, max_results=5))
            return '\n\n'.join(f"{r['title']}\n{r['href']}\n{r['body']}" for r in results)
        except Exception as e:
            return f"Error: {e}"
    
    elif action == "DONE":
        return "SESSION_END"
    
    else:
        return f"Unknown action: {action}"

def parse_response(response):
    """Parse action from response - takes LAST action so THINK can precede real actions."""
    lines = response.strip().split('\n')

    valid_actions = ['THINK', 'TALK_TO_USER', 'RUN_COMMAND',
                     'SAVE_MEMORY', 'READ_MEMORY', 'WEB_SEARCH', 'DONE']

    # Find the LAST action line (so THINK can be internal before the real action)
    action = None
    action_idx = None
    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Check for exact match (e.g., "WEB_SEARCH")
        if line_stripped in valid_actions:
            action = line_stripped
            action_idx = i
            continue

        # Check for "ACTION_NAME: ACTION" or "ACTION:" format
        for valid in valid_actions:
            if line_stripped == f"ACTION_NAME: {valid}" or line_stripped == f"{valid}:":
                action = valid
                action_idx = i
                break

    if action is None:
        return None, response

    content = '\n'.join(lines[action_idx + 1:])
    return action, content

def run_session():
    """Run one session with the wren."""
    memory = load_memory()
    
    # Build initial context
    context = SEED_PROMPT
    if memory:
        context += f"\n\n[Your saved memories from before]:\n{json.dumps(memory, indent=2)}"
    
    chat = model.start_chat(history=[])
    
    print("=" * 50)
    print("🐦 Wren Session Starting")
    print("=" * 50)
    
    response = chat.send_message(context)
    
    max_turns = 50
    for turn in range(max_turns):
        text = response.text
        print(f"\n--- Turn {turn + 1} ---")
        print(text[:500] + "..." if len(text) > 500 else text)
        
        action, content = parse_response(text)
        
        if action is None:
            # No valid action found, prompt for one
            response = chat.send_message("Please respond with a valid action.")
            continue
        
        if action == "DONE":
            print("\n🐦 Wren ended session")
            break
        
        result = execute_action(action, content, memory)
        print(f"[{action}] -> {result[:200]}..." if len(result) > 200 else f"[{action}] -> {result}")
        
        response = chat.send_message(f"Result of {action}:\n{result}\n\nWhat do you want to do next?")
    
    print("\n" + "=" * 50)
    print("🐦 Session Complete")
    print("=" * 50)

if __name__ == "__main__":
    run_session()
