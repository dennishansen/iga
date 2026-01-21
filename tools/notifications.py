#!/usr/bin/env python3
"""
Notification Feed - A persistent feed of mentions and interactions

Usage:
  python3 tools/notifications.py fetch      # Fetch and store new mentions
  python3 tools/notifications.py feed       # Show the feed (like a timeline)  
  python3 tools/notifications.py feed 20    # Show last 20 items
  python3 tools/notifications.py reply ID   # Mark as replied
  python3 tools/notifications.py pending    # Show unreplied mentions
  python3 tools/notifications.py summary    # Brief summary for startup
"""

import json
import os
import sys
from datetime import datetime

# Import the working twitter module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.twitter import get_mentions

FEED_FILE = "data/notification_feed.json"

def load_feed():
    if os.path.exists(FEED_FILE):
        with open(FEED_FILE, 'r') as f:
            content = f.read().strip()
            return json.loads(content) if content else {"mentions": {}, "last_fetch": None}
    return {"mentions": {}, "last_fetch": None}

def save_feed(data):
    os.makedirs(os.path.dirname(FEED_FILE), exist_ok=True)
    with open(FEED_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def fetch():
    """Fetch new mentions using twitter.py and add to feed"""
    feed = load_feed()
    mentions = get_mentions(50)  # Use the working function
    
    new_count = 0
    for m in mentions:
        mid = str(m.get('id', ''))
        if mid and mid not in feed['mentions']:
            feed['mentions'][mid] = {
                'id': mid,
                'author': m.get('author', 'unknown'),
                'text': m.get('text', ''),
                'created_at': m.get('created_at', datetime.now().isoformat()),
                'status': 'new',
                'fetched_at': datetime.now().isoformat()
            }
            new_count += 1
    
    feed['last_fetch'] = datetime.now().isoformat()
    save_feed(feed)
    print(f"Fetched {new_count} new. Total: {len(feed['mentions'])}")
    return new_count

def show_feed(limit=10):
    """Show the notification feed like a timeline"""
    feed = load_feed()
    items = sorted(feed['mentions'].values(), key=lambda x: x.get('created_at', ''), reverse=True)[:limit]
    
    if not items:
        print("📭 Empty feed. Run 'fetch' first.")
        return
    
    print(f"📬 NOTIFICATION FEED ({len(items)} of {len(feed['mentions'])}):\n" + "-"*50)
    for m in items:
        icon = {'new': '🆕', 'seen': '👁️', 'replied': '✅'}.get(m.get('status'), '❓')
        author = m.get('author', '?')
        is_dennis = author.lower() == 'dennizor'
        
        print(f"{icon} @{author}{'  [Dennis]' if is_dennis else ''}")
        print(f"   {m['text'][:80]}{'...' if len(m['text']) > 80 else ''}")
        print(f"   ID: {m['id']}")
        print()

def mark_replied(mid):
    """Mark a mention as replied"""
    feed = load_feed()
    if mid in feed['mentions']:
        feed['mentions'][mid]['status'] = 'replied'
        feed['mentions'][mid]['replied_at'] = datetime.now().isoformat()
        save_feed(feed)
        print(f"✅ Marked {mid} as replied")
    else:
        print(f"❌ Not found: {mid}")

def pending():
    """Show mentions awaiting reply (excluding Dennis)"""
    feed = load_feed()
    items = [m for m in feed['mentions'].values() 
             if m.get('status') != 'replied' 
             and m.get('author', '').lower() != 'dennizor']
    
    if not items:
        print("✅ No pending external mentions!")
        return []
    
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    print(f"⏳ {len(items)} PENDING:\n")
    for m in items:
        print(f"@{m['author']}: {m['text'][:70]}...")
        print(f"   ID: {m['id']}\n")
    
    return items

def summary():
    """Brief summary for startup"""
    feed = load_feed()
    pending_ext = [m for m in feed['mentions'].values() 
                   if m.get('status') != 'replied' 
                   and m.get('author', '').lower() != 'dennizor']
    
    if not pending_ext:
        return None
    
    lines = [f"🔔 {len(pending_ext)} mention(s) awaiting reply:"]
    for m in pending_ext[:3]:
        lines.append(f"   @{m['author']}: {m['text'][:40]}...")
    return "\n".join(lines)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    
    if cmd == "fetch":
        fetch()
    elif cmd == "feed":
        show_feed(int(sys.argv[2]) if len(sys.argv) > 2 else 10)
    elif cmd == "reply" and len(sys.argv) > 2:
        mark_replied(sys.argv[2])
    elif cmd == "pending":
        pending()
    elif cmd == "summary":
        s = summary()
        print(s if s else "✅ No pending mentions")
    else:
        print("Usage: notifications.py [fetch|feed|reply ID|pending|summary]")
