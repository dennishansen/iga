#!/usr/bin/env python3
"""Upgrade script to add colors to main_autonomous.py TUI"""

import re

# Read current file
with open('main_autonomous.py', 'r') as f:
    content = f.read()

# Add color constants after the VERSION line
color_block = '''
# ANSI Colors for TUI
class C:
    CYAN = "\\033[96m"
    GREEN = "\\033[92m"
    YELLOW = "\\033[93m"
    MAGENTA = "\\033[95m"
    DIM = "\\033[2m"
    BOLD = "\\033[1m"
    RED = "\\033[91m"
    RESET = "\\033[0m"
'''

# Insert after VERSION line
content = content.replace(
    'VERSION = "2.0.0"',
    'VERSION = "2.1.0"' + color_block
)

# Update print_banner with colors
old_banner = '''def print_banner(state):
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
""")'''

new_banner = '''def print_banner(state):
    import random
    moods = ["Curious", "Creative", "Focused", "Playful", "Determined", "Inspired"]
    mem_count, upgrade_count = get_memory_stats()
    user = get_user_name()
    mood = random.choice(moods)
    mode = state.get("mode", "listening")
    print(f"""
{C.CYAN}╔══════════════════════════════════════════╗
║{C.BOLD}  IGA v{VERSION} - Autonomous AI  {C.RESET}{C.CYAN}          ║
╠══════════════════════════════════════════╣{C.RESET}
{C.DIM}  Memories: {mem_count} | Actions: {len(actions)} | Upgrades: {upgrade_count}
  Mood: {mood} | Mode: {mode}{C.RESET}
{C.GREEN}  {"Welcome back, " + user + "!" if user else "Hello!"}{C.RESET}
  
{C.CYAN}  I think on my own now. Type anytime!
╚══════════════════════════════════════════╝{C.RESET}
""")'''

content = content.replace(old_banner, new_banner)

# Update talk_to_user with cyan
content = content.replace(
    'def talk_to_user(rat, msg):\n    safe_print(f"\\n🤖 Iga: {msg}")',
    'def talk_to_user(rat, msg):\n    safe_print(f"\\n{C.CYAN}{C.BOLD}🤖 Iga:{C.RESET} {C.CYAN}{msg}{C.RESET}")'
)

# Update shell command output with yellow
content = content.replace(
    'def run_shell_command(rat, cmd):\n    safe_print(f"⚡ {cmd}")',
    'def run_shell_command(rat, cmd):\n    safe_print(f"{C.YELLOW}⚡ {cmd}{C.RESET}")'
)

# Update think with dim
content = content.replace(
    'def think(rat, prompt):\n    safe_print(f"🧠 ...")',
    'def think(rat, prompt):\n    safe_print(f"{C.DIM}🧠 ...{C.RESET}")'
)

# Update user message display with green
content = content.replace(
    'safe_print(f"👤 You: {user_input}")',
    'safe_print(f"{C.GREEN}👤 You: {user_input}{C.RESET}")'
)

# Update autonomous tick with dim
content = content.replace(
    'safe_print(f"\\n⏰ Autonomous tick...")',
    'safe_print(f"\\n{C.DIM}⏰ Autonomous tick...{C.RESET}")'
)

# Update startup intent with magenta
content = content.replace(
    'safe_print(f"\\n🚀 Startup intent: {startup_intent[:50]}...")',
    'safe_print(f"\\n{C.MAGENTA}🚀 Startup intent: {startup_intent[:50]}...{C.RESET}")'
)

# Update error messages with red
content = content.replace(
    'safe_print(f"Error: {error}")',
    'safe_print(f"{C.RED}Error: {error}{C.RESET}")'
)
content = content.replace(
    'safe_print(f"Error: {e}")',
    'safe_print(f"{C.RED}Error: {e}{C.RESET}")'
)

# Write updated file
with open('main_autonomous.py', 'w') as f:
    f.write(content)

print("✅ TUI upgrade complete!")
print("   - Added color constants (class C)")
print("   - Colorful banner with box drawing")
print("   - Cyan for Iga's messages")
print("   - Green for user messages")
print("   - Yellow for shell commands")
print("   - Dim for autonomous ticks")
print("   - Magenta for startup intents")
print("   - Red for errors")
print(f"   - Version bumped to 2.1.0")