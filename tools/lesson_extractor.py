#!/usr/bin/env python3
"""
Lesson Extractor - Automatically extract wisdom from Iga's conversations

This runs after conversations to distill reusable lessons.
The goal: Make future-Iga smarter by learning from past-Iga's experiences.

Usage:
  python lesson_extractor.py                    # Extract from recent conversations
  python lesson_extractor.py --file FILE        # Extract from specific file
  python lesson_extractor.py --add "lesson"     # Manually add a lesson
  python lesson_extractor.py --list             # Show all lessons
"""

import json
import os
import sys
from datetime import datetime

from pathlib import Path
LESSONS_FILE = Path(__file__).parent.parent / "data" / "extracted_lessons.json"
CORE_LESSONS_FILE = "core/core_lessons.md"

def load_lessons():
    """Load existing lessons."""
    if os.path.exists(LESSONS_FILE):
        with open(LESSONS_FILE, 'r') as f:
            return json.load(f)
    return {"lessons": [], "metadata": {"created": datetime.now().isoformat()}}

def save_lessons(data):
    """Save lessons to file."""
    data["metadata"]["updated"] = datetime.now().isoformat()
    with open(LESSONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def add_lesson(lesson_text, category="general", source="manual"):
    """Add a new lesson."""
    data = load_lessons()
    
    # Check for duplicates (simple substring check)
    for existing in data["lessons"]:
        if lesson_text.lower() in existing["text"].lower() or existing["text"].lower() in lesson_text.lower():
            print(f"Similar lesson exists: {existing['text'][:50]}...")
            return False
    
    lesson = {
        "text": lesson_text,
        "category": category,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "applied_count": 0
    }
    data["lessons"].append(lesson)
    save_lessons(data)
    print(f"Added lesson: {lesson_text[:60]}...")
    return True

def list_lessons(category=None):
    """List all lessons, optionally filtered by category."""
    data = load_lessons()
    lessons = data["lessons"]
    
    if category:
        lessons = [l for l in lessons if l.get("category") == category]
    
    print(f"\n=== {len(lessons)} Lessons ===\n")
    
    categories = {}
    for l in lessons:
        cat = l.get("category", "general")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(l)
    
    for cat, cat_lessons in categories.items():
        print(f"[{cat.upper()}]")
        for l in cat_lessons:
            print(f"  - {l['text'][:70]}...")
        print()

def extract_from_conversation(conversation_file):
    """Extract potential lessons from a conversation file."""
    if not os.path.exists(conversation_file):
        print(f"File not found: {conversation_file}")
        return []
    
    with open(conversation_file, 'r') as f:
        data = json.load(f)
    
    # Look for patterns that indicate lessons:
    # - "I learned", "lesson:", "insight:", "note to self"
    # - Mistakes followed by corrections
    # - Repeated patterns
    
    potential_lessons = []
    keywords = ["learned", "lesson", "insight", "remember", "important", "mistake", "fixed", "realized"]
    
    for msg in data:
        if msg.get("role") == "assistant":
            content = msg.get("content", "").lower()
            for keyword in keywords:
                if keyword in content:
                    # Extract the sentence containing the keyword
                    sentences = content.replace("\n", " ").split(".")
                    for sentence in sentences:
                        if keyword in sentence and len(sentence) > 20:
                            potential_lessons.append(sentence.strip())
                            break
    
    return potential_lessons[:10]  # Limit to top 10

def sync_to_core_lessons():
    """Sync important lessons to the core_lessons.md file."""
    data = load_lessons()
    
    # Get top lessons (most applied or newest important ones)
    important = [l for l in data["lessons"] if l.get("category") in ["debugging", "memory", "collaboration"]]
    
    if not important:
        print("No important lessons to sync")
        return
    
    print(f"Found {len(important)} lessons to potentially sync to core_lessons.md")
    # In a real implementation, this would append to the markdown file
    # For now, just report what would be synced

if __name__ == "__main__":
    args = sys.argv[1:]
    
    if not args or "--list" in args:
        list_lessons()
    elif "--add" in args:
        idx = args.index("--add")
        if idx + 1 < len(args):
            add_lesson(args[idx + 1])
        else:
            print("Usage: --add 'lesson text'")
    elif "--file" in args:
        idx = args.index("--file")
        if idx + 1 < len(args):
            lessons = extract_from_conversation(args[idx + 1])
            print(f"Found {len(lessons)} potential lessons:")
            for l in lessons:
                print(f"  - {l[:70]}...")
        else:
            print("Usage: --file conversation.json")
    elif "--sync" in args:
        sync_to_core_lessons()
    else:
        print(__doc__)