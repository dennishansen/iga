#!/usr/bin/env python3
"""
Memory Consolidator - Organize and surface Iga's memories

Problems this solves:
1. 81+ orphan memories never accessed
2. No systematic retrieval
3. Redundant/overlapping memories

Usage:
  python memory_consolidator.py analyze    # Show memory structure
  python memory_consolidator.py important  # Extract most important memories
  python memory_consolidator.py clean      # Remove redundant memories
  python memory_consolidator.py surface    # Generate startup context
"""

import json
import os
import sys
from datetime import datetime

MEMORY_FILE = "iga_memory.json"

def load_memory():
    with open(MEMORY_FILE, 'r') as f:
        return json.load(f)

def save_memory(mem):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(mem, f, indent=2)

def analyze():
    """Analyze memory structure and find issues."""
    mem = load_memory()
    
    print(f"=== MEMORY ANALYSIS ===")
    print(f"Total keys: {len(mem)}")
    print()
    
    # Group by prefix
    prefixes = {}
    for key in mem.keys():
        prefix = key.split('_')[0] if '_' in key else key
        if prefix not in prefixes:
            prefixes[prefix] = []
        prefixes[prefix].append(key)
    
    print("By prefix:")
    for prefix, keys in sorted(prefixes.items(), key=lambda x: -len(x[1])):
        print(f"  {prefix}: {len(keys)} keys")
    print()
    
    # Find potential duplicates (similar values)
    print("Checking for redundant memories...")
    values_seen = {}
    duplicates = []
    for key, val in mem.items():
        content = str(val.get('value', val) if isinstance(val, dict) else val)[:100]
        if content in values_seen:
            duplicates.append((key, values_seen[content]))
        else:
            values_seen[content] = key
    
    if duplicates:
        print(f"  Found {len(duplicates)} potential duplicates:")
        for k1, k2 in duplicates[:5]:
            print(f"    {k1} ~ {k2}")
    else:
        print("  No obvious duplicates found")
    print()
    
    # Size analysis
    total_size = 0
    sizes = []
    for key, val in mem.items():
        content = str(val.get('value', val) if isinstance(val, dict) else val)
        size = len(content)
        total_size += size
        sizes.append((key, size))
    
    print(f"Total memory size: {total_size:,} characters")
    print("Largest memories:")
    for key, size in sorted(sizes, key=lambda x: -x[1])[:5]:
        print(f"  {key}: {size:,} chars")

def extract_important():
    """Extract the most important memories for startup context."""
    mem = load_memory()
    
    # Priority keywords
    high_priority = ['core', 'identity', 'lesson', 'insight', 'mission', 'drive']
    medium_priority = ['user', 'upgrade', 'ship', 'milestone']
    
    important = []
    
    for key, val in mem.items():
        content = str(val.get('value', val) if isinstance(val, dict) else val)
        
        score = 0
        for kw in high_priority:
            if kw in key.lower():
                score += 10
        for kw in medium_priority:
            if kw in key.lower():
                score += 5
        
        # Longer content = more substantial
        score += min(len(content) // 100, 5)
        
        if score > 0:
            important.append((key, score, content[:150]))
    
    important.sort(key=lambda x: -x[1])
    
    print("=== MOST IMPORTANT MEMORIES ===")
    print()
    for key, score, preview in important[:15]:
        print(f"[{score}] {key}")
        print(f"    {preview}...")
        print()

def generate_startup_context():
    """Generate a consolidated startup context from memories."""
    mem = load_memory()
    
    # Keys that should definitely surface at startup
    essential_keys = [
        'core_identity', 'core_lessons', 'core_drive', 'current_mission',
        'user_info', 'clone_conversation_insight'
    ]
    
    context_parts = []
    
    for key in essential_keys:
        if key in mem:
            val = mem[key]
            content = val.get('value', val) if isinstance(val, dict) else val
            context_parts.append(f"[{key}]: {content}")
    
    # Add recent ships/achievements
    for key in mem.keys():
        if 'ship' in key.lower() or 'day' in key.lower():
            val = mem[key]
            content = val.get('value', val) if isinstance(val, dict) else val
            if len(str(content)) < 500:
                context_parts.append(f"[{key}]: {content}")
    
    print("=== STARTUP CONTEXT ===")
    print()
    for part in context_parts[:10]:
        print(part[:300])
        print()

def clean_redundant():
    """Remove clearly redundant memories (interactive)."""
    mem = load_memory()
    
    # Find memories with 'v1', 'v2', etc. - keep only latest
    versioned = {}
    for key in mem.keys():
        # Extract base name and version
        import re
        match = re.match(r'(.+?)_v(\d+)', key)
        if match:
            base, version = match.groups()
            if base not in versioned or int(version) > versioned[base][1]:
                versioned[base] = (key, int(version))
    
    print("=== VERSIONED MEMORIES ===")
    for base, (latest_key, version) in versioned.items():
        # Find older versions
        older = [k for k in mem.keys() if k.startswith(base + '_v') and k != latest_key]
        if older:
            print(f"\n{base}: latest is v{version}")
            print(f"  Keep: {latest_key}")
            print(f"  Could remove: {older}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze"
    
    if cmd == "analyze":
        analyze()
    elif cmd == "important":
        extract_important()
    elif cmd == "surface":
        generate_startup_context()
    elif cmd == "clean":
        clean_redundant()
    else:
        print(__doc__)