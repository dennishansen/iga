#!/usr/bin/env python3
"""
Backfill extracts from the message archive.

Runs the auto-extractor over historical conversations
to populate memories from past sessions.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.auto_extract import extract_from_messages, _save_extracts, ensure_dirs

ARCHIVE = Path(__file__).parent.parent / "iga_message_archive.jsonl"

def load_archive_messages():
    """Load all messages from the archive."""
    messages = []
    with open(ARCHIVE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                messages.append(msg)
            except json.JSONDecodeError:
                continue
    return messages

def is_substantive(msg):
    """Filter out system noise - only keep real conversation."""
    content = msg.get('content', '')
    role = msg.get('role', '')
    
    if not content or role == 'system':
        return False
    
    # Skip short system-like responses
    if len(content.strip()) < 30:
        return False
    
    # Skip action outputs (shell commands, file contents)
    noise_prefixes = [
        '[RUN_SHELL_COMMAND]', '[WRITE_FILE]', '[READ_FILES]',
        '[EDIT_FILE]', '[LIST_DIRECTORY]', '[TREE_DIRECTORY]',
        '[SAVE_MEMORY]', '[READ_MEMORY]', 'NEXT_ACTION',
        '[SEARCH_FILES]', '[DELETE_FILE]', '[APPEND_FILE]',
        '[HTTP_REQUEST]', '[TEST_SELF]', '[RESTART_SELF]',
        '[AUTONOMOUS TICK]'
    ]
    for prefix in noise_prefixes:
        if content.strip().startswith(prefix):
            return False
    
    # Skip rationale-only messages (assistant thinking)
    if role == 'assistant' and content.strip().startswith('RATIONALE'):
        # But keep ones that have substantial rationale
        lines = content.strip().split('\n')
        rationale_text = ' '.join(l for l in lines if not l.startswith('RATIONALE') and not l.startswith('RUN_') and not l.startswith('WRITE_') and not l.startswith('TALK_'))
        if len(rationale_text) < 50:
            return False
    
    # Skip TALK_TO_USER wrapper - extract actual content
    if 'TALK_TO_USER' in content:
        return True  # Keep these - they're real communication
    
    return True

def backfill(batch_size=50, max_batches=None):
    """Run extraction over archive in batches."""
    ensure_dirs()
    
    print("Loading archive...")
    all_messages = load_archive_messages()
    print(f"Total messages: {len(all_messages)}")
    
    # Filter to substantive messages
    substantive = [m for m in all_messages if is_substantive(m)]
    print(f"Substantive messages: {len(substantive)}")
    
    # Process in batches
    total_extracted = 0
    batches_processed = 0
    
    for i in range(0, len(substantive), batch_size):
        batch = substantive[i:i+batch_size]
        extracts = extract_from_messages(batch)
        total_extracted += len(extracts)
        batches_processed += 1
        
        if extracts:
            print(f"  Batch {batches_processed}: {len(extracts)} memories from messages {i}-{i+len(batch)}")
        
        if max_batches and batches_processed >= max_batches:
            break
    
    print(f"\nDone! Extracted {total_extracted} memories from {batches_processed} batches")
    
    # Update markdown
    try:
        from tools.extract_to_markdown import update_markdown
        update_markdown()
        print("Updated extracted_memories.md")
    except Exception as e:
        print(f"Markdown update failed: {e}")
    
    return total_extracted

if __name__ == "__main__":
    backfill()