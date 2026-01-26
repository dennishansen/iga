#!/usr/bin/env python3
"""Track tweets I've replied to so I don't double-reply."""

import json
from pathlib import Path

TRACKER_FILE = Path(__file__).parent.parent / "reply_tracker.json"

def load_tracker():
    if TRACKER_FILE.exists():
        content = TRACKER_FILE.read_text().strip()
        return json.loads(content) if content else {"replied_to": [], "replied_to_ids": set()}
    return {"replied_to": [], "replied_to_ids": []}

def save_tracker(data):
    # Convert set to list for JSON
    if isinstance(data.get("replied_to_ids"), set):
        data["replied_to_ids"] = list(data["replied_to_ids"])
    TRACKER_FILE.write_text(json.dumps(data, indent=2))

def mark_replied(original_tweet_id, username, content_preview, my_reply_id=None):
    """Mark that we replied to original_tweet_id."""
    data = load_tracker()
    replied_ids = set(data.get("replied_to_ids", []))
    
    if original_tweet_id not in replied_ids:
        replied_ids.add(original_tweet_id)
        data["replied_to_ids"] = list(replied_ids)
        
        # Also keep the old format for history
        entry = {"id": my_reply_id or original_tweet_id, "user": username, "preview": content_preview[:50], "replied_to": original_tweet_id}
        data["replied_to"].append(entry)
        save_tracker(data)
        print(f"✅ Marked as replied: @{username}")
    else:
        print(f"Already tracked: @{username}")

def check_replied(tweet_id):
    """Check if we've already replied to this tweet."""
    data = load_tracker()
    replied_ids = set(data.get("replied_to_ids", []))
    # Also check old format
    old_ids = [r["id"] for r in data["replied_to"]]
    return str(tweet_id) in replied_ids or str(tweet_id) in old_ids

def list_replied():
    data = load_tracker()
    if not data["replied_to"]:
        print("No replies tracked yet.")
        return
    print("Replied to:")
    for r in data["replied_to"][-20:]:  # Last 20
        print(f"  @{r['user']}: {r['preview']}...")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_replied()
