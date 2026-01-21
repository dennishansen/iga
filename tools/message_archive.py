"""
Message Archive System for Iga
Archives all conversation messages permanently before they get summarized.
"""

import json
import os
from datetime import datetime

ARCHIVE_FILE = "iga_message_archive.jsonl"  # JSON Lines format - one message per line

def archive_messages(messages):
    """
    Archive messages to permanent storage.
    Uses JSON Lines format for efficient appending without loading entire file.
    """
    if not messages:
        return
    
    try:
        with open(ARCHIVE_FILE, 'a') as f:
            for msg in messages:
                # Skip system messages - they're always the same
                if msg.get("role") == "system":
                    continue
                
                # Add timestamp if not present
                archive_entry = {
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "archived_at": datetime.now().isoformat()
                }
                
                f.write(json.dumps(archive_entry) + "\n")
        
        return True
    except Exception as e:
        print(f"Warning: Could not archive messages: {e}")
        return False

def get_archive_stats():
    """Get statistics about the archive."""
    if not os.path.exists(ARCHIVE_FILE):
        return {"total_messages": 0, "file_size": 0}
    
    try:
        with open(ARCHIVE_FILE, 'r') as f:
            lines = f.readlines()
        
        file_size = os.path.getsize(ARCHIVE_FILE)
        
        return {
            "total_messages": len(lines),
            "file_size": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2)
        }
    except Exception:
        return {"total_messages": 0, "file_size": 0, "error": True}

def search_archive(query, limit=50):
    """Search the archive for messages containing a query."""
    if not os.path.exists(ARCHIVE_FILE):
        return []
    
    results = []
    query_lower = query.lower()
    
    try:
        with open(ARCHIVE_FILE, 'r') as f:
            for line in f:
                line_content = line.strip()
                if not line_content:
                    continue
                try:
                    msg = json.loads(line_content)
                    content = msg.get("content", "")
                    if query_lower in content.lower():
                        results.append(msg)
                        if len(results) >= limit:
                            break
                except json.JSONDecodeError:
                    continue
        
        return results
    except Exception:
        return []

def get_recent_archived(n=100):
    """Get the n most recent archived messages."""
    if not os.path.exists(ARCHIVE_FILE):
        return []
    
    try:
        # Read all lines and take last n
        with open(ARCHIVE_FILE, 'r') as f:
            lines = f.readlines()
        
        recent_lines = lines[-n:]
        messages = []
        
        for line in recent_lines:
            line_content = line.strip()
            if not line_content:
                continue
            try:
                messages.append(json.loads(line_content))
            except json.JSONDecodeError:
                continue
        
        return messages
    except Exception:
        return []