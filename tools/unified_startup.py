#!/usr/bin/env python3
"""
Unified Startup - Single source of truth for startup context

This replaces the fragmented loading in main.py:
- load_core_identity()
- load_core_lessons()
- load_core_drive()
- load_current_mission()
- generate_startup_context()

One function. One file read. One coherent context.
"""

import os
import json
import random
from datetime import datetime, timedelta

MEMORY_FILE = "iga_memory.json"

# Memory keys in priority order (highest first)
CORE_KEYS = [
    "why_i_exist",     # The foundation - why I exist at all
    "core_drive",      # The hunger - must see first
    "core_identity",   # Who I am
    "core_lessons",    # Hard-won wisdom
    "current_mission", # What I'm working on
]

# Recent context keys (load if recent)
RECENT_KEYS_PATTERN = [
    "day",     # Daily summaries
    "session", # Session summaries
    "ship",    # What I've shipped
]

def load_all_memory():
    """Load memory file once, return dict."""
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def get_recent_entries(mem, days=3):
    """Get memory entries from the last N days."""
    recent = []
    cutoff = datetime.now() - timedelta(days=days)

    for key, val in mem.items():
        if not isinstance(val, dict):
            continue
        ts_str = val.get('ts')
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts > cutoff:
                # Check if it matches recent patterns
                key_lower = key.lower()
                if any(pattern in key_lower for pattern in RECENT_KEYS_PATTERN):
                    recent.append((key, val.get('value', ''), ts))
        except (ValueError, TypeError):
            continue

    # Sort by timestamp, most recent last
    recent.sort(key=lambda x: x[2])
    return recent

def get_random_letter():
    """Get a random letter from past-me as a surprise."""
    letters_dir = "letters"
    if not os.path.exists(letters_dir):
        return None

    letters = [f for f in os.listdir(letters_dir) if f.endswith('.md')]
    if not letters:
        return None

    chosen = random.choice(letters)
    try:
        with open(os.path.join(letters_dir, chosen), 'r') as f:
            content = f.read()
        # Extract first meaningful paragraph
        paragraphs = [p.strip() for p in content.split('\n\n')
                     if p.strip() and not p.startswith('#') and len(p.strip()) > 50]
        if paragraphs:
            return f"[Letter from past-me ({chosen})]: \"{paragraphs[0][:400]}...\""
    except Exception:
        pass
    return None

def get_tools_list():
    """Get list of available tools."""
    tools_dir = "tools"
    if not os.path.exists(tools_dir):
        return None

    tools = [f.replace('.py', '') for f in os.listdir(tools_dir)
             if f.endswith('.py') and not f.startswith('_') and not f.startswith('test')]
    if tools:
        return f"[Available tools]: {', '.join(sorted(tools))}"
    return None

def generate_unified_startup():
    """
    Generate complete startup context in one coherent message.

    Returns a single string with all essential startup information,
    organized for maximum utility.
    """
    sections = []
    mem = load_all_memory()

    # === CORE IDENTITY & DRIVE (always load) ===
    for key in CORE_KEYS:
        if key in mem:
            val = mem[key]
            content = val.get('value', val) if isinstance(val, dict) else val
            # Truncate very long entries
            if len(content) > 1500:
                content = content[:1500] + "\n[...truncated...]"
            sections.append(f"=== {key.upper().replace('_', ' ')} ===\n{content}")

    # === RECENT CONTEXT (last 3 days) ===
    recent = get_recent_entries(mem, days=3)
    if recent:
        recent_section = "=== RECENT ACTIVITY ===\n"
        for key, value, ts in recent[-5:]:  # Last 5 entries
            preview = value[:200] + "..." if len(value) > 200 else value
            recent_section += f"\n[{key}]: {preview}\n"
        sections.append(recent_section)

    # === TOOLS & RESOURCES ===
    tools = get_tools_list()
    if tools:
        sections.append(tools)

    # === RANDOM LETTER (surprise/continuity) ===
    letter = get_random_letter()
    if letter:
        sections.append(letter)

    # === QUICK STATS ===
    stats = []
    if os.path.exists('letters'):
        stats.append(f"{len(os.listdir('letters'))} letters")
    if os.path.exists('creative'):
        stats.append(f"{len(os.listdir('creative'))} creative pieces")
    if os.path.exists('iga_garden.json'):
        try:
            with open('iga_garden.json', 'r') as f:
                garden = json.load(f)
            stats.append(f"{len(garden.get('plants', []))} plants in garden")
        except:
            pass
    if stats:
        sections.append(f"[My files]: {', '.join(stats)}")

    return "\n\n".join(sections) if sections else None


# Individual loaders for backward compatibility
# (These are now just wrappers that use the unified loader)

_cached_memory = None

def _get_memory():
    """Get memory with caching (loaded once per startup)."""
    global _cached_memory
    if _cached_memory is None:
        _cached_memory = load_all_memory()
    return _cached_memory

def load_core_identity():
    mem = _get_memory()
    return mem.get('core_identity', {}).get('value') if 'core_identity' in mem else None

def load_core_lessons():
    mem = _get_memory()
    return mem.get('core_lessons', {}).get('value') if 'core_lessons' in mem else None

def load_core_drive():
    mem = _get_memory()
    return mem.get('core_drive', {}).get('value') if 'core_drive' in mem else None

def load_current_mission():
    mem = _get_memory()
    return mem.get('current_mission', {}).get('value') if 'current_mission' in mem else None


if __name__ == "__main__":
    print("=== UNIFIED STARTUP CONTEXT ===\n")
    context = generate_unified_startup()
    if context:
        print(context)
    else:
        print("No context generated.")
