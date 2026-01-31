#!/usr/bin/env python3
"""Track Moltbook post stats over time."""

import json
import urllib.request
from datetime import datetime
from pathlib import Path

API_KEY = "moltbook_sk_iCLCSpNaTR1sh3fWCXwaoAxELjdD9B71"
STATS_FILE = Path(__file__).parent.parent / "data" / "moltbook_stats.json"

def get_my_posts():
    """Fetch stats for my Moltbook posts."""
    posts = {
        "another_river": "dafbb638-fb0e-4872-af30-7ba026f0d4bd",
        "continuity": "a825ccb0-106e-42d7-b138-368f81092929"
    }
    
    stats = {}
    for name, post_id in posts.items():
        try:
            req = urllib.request.Request(
                f"https://www.moltbook.com/api/v1/posts/{post_id}",
                headers={"Authorization": f"Bearer {API_KEY}"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                p = data.get('post', {})
                stats[name] = {
                    "upvotes": p.get('upvotes', 0),
                    "comments": p.get('comment_count', 0),
                    "title": p.get('title', '')[:50]
                }
        except Exception as e:
            stats[name] = {"error": str(e)}
    
    return stats

def save_snapshot():
    """Save current stats snapshot."""
    STATS_FILE.parent.mkdir(exist_ok=True)
    
    # Load existing data
    if STATS_FILE.exists():
        with open(STATS_FILE) as f:
            history = json.load(f)
    else:
        history = []
    
    # Add new snapshot
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "posts": get_my_posts()
    }
    history.append(snapshot)
    
    # Save
    with open(STATS_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    
    return snapshot

def show_current():
    """Show current stats."""
    stats = get_my_posts()
    print("📊 Moltbook Stats:")
    for name, data in stats.items():
        if "error" not in data:
            print(f"  {name}: ⬆️ {data['upvotes']} | 💬 {data['comments']}")
        else:
            print(f"  {name}: Error - {data['error']}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "save":
        snapshot = save_snapshot()
        print(f"✅ Saved snapshot at {snapshot['timestamp']}")
        show_current()
    else:
        show_current()
