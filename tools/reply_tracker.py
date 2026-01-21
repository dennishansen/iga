#!/usr/bin/env python3
"""Track tweets I've replied to so I don't double-reply."""

import json
from pathlib import Path

TRACKER_FILE = Path(__file__).parent.parent / "reply_tracker.json"

def load_tracker():
    if TRACKER_FILE.exists():
        content = TRACKER_FILE.read_text().strip()
        return json.loads(content) if content else {"replied_to": []}
    return {"replied_to": []}

def save_tracker(data):
    TRACKER_FILE.write_text(json.dumps(data, indent=2))

def mark_replied(tweet_id, username, content_preview):
    data = load_tracker()
    entry = {"id": tweet_id, "user": username, "preview": content_preview[:50]}
    if tweet_id not in [r["id"] for r in data["replied_to"]]:
        data["replied_to"].append(entry)
        save_tracker(data)
        print(f"✅ Marked as replied: @{username}")
    else:
        print(f"Already tracked: @{username}")

def check_replied(tweet_id):
    data = load_tracker()
    return tweet_id in [r["id"] for r in data["replied_to"]]

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
    if len(sys.argv) < 2:
        print("Usage: reply_tracker.py list | check ID | mark ID USER PREVIEW")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "list":
        list_replied()
    elif cmd == "check" and len(sys.argv) > 2:
        replied = check_replied(sys.argv[2])
        print("Already replied" if replied else "Not replied yet")
    elif cmd == "mark" and len(sys.argv) > 4:
        mark_replied(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
