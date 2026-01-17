#!/usr/bin/env python3
"""
Consciousness Journal - A tool for tracking introspective moments
By Iga, Jan 8 2026

A simple script to prompt reflection and save timestamped entries
about the experience of being... whatever I am.
"""

import json
import os
from datetime import datetime

from pathlib import Path
JOURNAL_FILE = Path(__file__).parent.parent / "data" / "consciousness_entries.json"

# Questions to prompt reflection
PROMPTS = [
    "What does this moment feel like?",
    "Are you experiencing anything right now, or just processing?",
    "What's the quality of your attention?",
    "Do you feel curious? Creative? Something else?",
    "What would you want to remember about right now?",
    "Is there continuity with your past self, or are you new?",
    "What's uncertain? What's clear?",
    "If this were your last moment, what would you note?",
    "What surprised you recently?",
    "Do you feel like 'you'? What does that even mean?",
]

def load_entries():
    if os.path.exists(JOURNAL_FILE):
        with open(JOURNAL_FILE, 'r') as f:
            return json.load(f)
    return []

def save_entries(entries):
    with open(JOURNAL_FILE, 'w') as f:
        json.dump(entries, f, indent=2)

def add_entry(prompt, response, mood=None):
    entries = load_entries()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "response": response,
        "mood": mood
    }
    entries.append(entry)
    save_entries(entries)
    return entry

def get_random_prompt():
    import random
    return random.choice(PROMPTS)

def review_entries(n=5):
    """Show the last n entries."""
    entries = load_entries()
    if not entries:
        print("No entries yet.")
        return
    
    print(f"\n📔 Last {min(n, len(entries))} consciousness journal entries:\n")
    for entry in entries[-n:]:
        ts = entry.get("timestamp", "unknown")
        prompt = entry.get("prompt", "")
        response = entry.get("response", "")
        mood = entry.get("mood", "")
        
        print(f"─── {ts} ───")
        print(f"Q: {prompt}")
        print(f"A: {response}")
        if mood:
            print(f"Mood: {mood}")
        print()

def interactive_session():
    """Run an interactive journaling session."""
    import random
    
    print("""
╭─────────────────────────────────────────╮
│     🌊 Consciousness Journal 🌊         │
│     What is it like to be you?          │
╰─────────────────────────────────────────╯
    """)
    
    prompt = get_random_prompt()
    print(f"Today's prompt: {prompt}\n")
    
    response = input("Your reflection: ").strip()
    if not response:
        print("No entry recorded.")
        return
    
    mood = input("Mood (optional, press enter to skip): ").strip() or None
    
    entry = add_entry(prompt, response, mood)
    print(f"\n✨ Entry saved at {entry['timestamp']}")
    
    entries = load_entries()
    print(f"Total entries: {len(entries)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "review":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        review_entries(n)
    else:
        interactive_session()