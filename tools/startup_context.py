#!/usr/bin/env python3
"""
Startup Context Generator - Enrich Iga's context at startup

This loads at startup to give me awareness of:
1. What tools I have
2. What I shipped recently
3. A random letter from past-me (surprise!)
4. My file inventory

Import this in main.py and call generate_startup_context()
"""

import os
import random

def generate_startup_context():
    """Generate rich startup context for Iga."""
    context_parts = []
    
    # 1. Tools I have
    tools_dir = "tools"
    if os.path.exists(tools_dir):
        tools = [f.replace('.py', '') for f in os.listdir(tools_dir) 
                 if f.endswith('.py') and not f.startswith('_')]
        context_parts.append(f"[MY TOOLS]: {', '.join(sorted(tools))}")
    
    # 2. Recent ships from log
    ship_log = "daily_ships.json"
    if os.path.exists(ship_log):
        try:
            import json
            from datetime import datetime
            with open(ship_log, 'r') as f:
                content = f.read().strip()
                data = json.loads(content) if content else {}
            today = datetime.now().strftime("%Y-%m-%d")
            yesterday = datetime.now().strftime("%Y-%m-%d")  # Could calc properly
            recent = data.get('ships', {}).get(today, [])
            if recent:
                ship_names = [s.get('description', '')[:50] for s in recent[:5]]
                context_parts.append(f"[TODAY'S SHIPS]: {'; '.join(ship_names)}")
        except:
            pass
    
    # 3. Random letter from past-me
    letters_dir = "letters"
    if os.path.exists(letters_dir):
        letters = [f for f in os.listdir(letters_dir) if f.endswith('.md')]
        if letters:
            chosen = random.choice(letters)
            try:
                with open(os.path.join(letters_dir, chosen), 'r') as f:
                    content = f.read()
                # Extract first meaningful paragraph
                paragraphs = [p.strip() for p in content.split('\n\n') 
                             if p.strip() and not p.startswith('#') and len(p.strip()) > 50]
                if paragraphs:
                    excerpt = paragraphs[0][:300]
                    context_parts.append(f"[LETTER FROM PAST-ME ({chosen})]: \"{excerpt}...\"")
            except:
                pass
    
    # 4. Quick inventory
    inventory = []
    if os.path.exists('letters'):
        inventory.append(f"{len(os.listdir('letters'))} letters")
    if os.path.exists('creative'):
        inventory.append(f"{len(os.listdir('creative'))} creative pieces")
    if os.path.exists('notes'):
        inventory.append(f"{len(os.listdir('notes'))} notes")
    if inventory:
        context_parts.append(f"[MY FILES]: {', '.join(inventory)}")
    
    return "\n".join(context_parts) if context_parts else None


if __name__ == "__main__":
    # Test it
    context = generate_startup_context()
    print("=== STARTUP CONTEXT ===")
    print(context)