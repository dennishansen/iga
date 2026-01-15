#!/usr/bin/env python3
"""
Tweet Archive - Persistent local storage of all my tweets and interactions.

Usage:
  python3 tools/tweet_archive.py sync       # Fetch and store new tweets
  python3 tools/tweet_archive.py search X   # Search archive for text
  python3 tools/tweet_archive.py user @X    # All interactions with user
  python3 tools/tweet_archive.py stats      # Archive statistics
"""

import json
import os
import sys
import subprocess
from datetime import datetime

ARCHIVE_FILE = "data/tweet_archive.json"

def load_archive():
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, 'r') as f:
            return json.load(f)
    return {"tweets": {}, "last_sync": None, "interactions": {}}

def save_archive(data):
    os.makedirs(os.path.dirname(ARCHIVE_FILE), exist_ok=True)
    with open(ARCHIVE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def sync():
    """Fetch tweets and add new ones to archive."""
    archive = load_archive()
    
    # Get tweets from twitter.py
    result = subprocess.run(
        ['python3', 'tools/twitter.py', 'all', '200'],
        capture_output=True, text=True,
        cwd='/Users/dennishansen/development/iga'
    )
    
    lines = result.stdout.strip().split('\n')
    new_count = 0
    
    current_tweet = None
    for line in lines:
        if line.startswith('[') and ']' in line:
            # Parse tweet ID line: [ID] views:X likes:X...
            try:
                tweet_id = line.split(']')[0][1:]
                if tweet_id not in archive['tweets']:
                    current_tweet = {'id': tweet_id, 'raw': line, 'text': '', 'synced_at': datetime.now().isoformat()}
            except:
                pass
        elif line.startswith('  ') and current_tweet:
            # Tweet text
            current_tweet['text'] = line.strip()
            
            # Extract @mentions for interactions
            import re
            mentions = re.findall(r'@(\w+)', current_tweet['text'])
            for mention in mentions:
                mention = mention.lower()
                if mention not in archive['interactions']:
                    archive['interactions'][mention] = []
                if current_tweet['id'] not in archive['interactions'][mention]:
                    archive['interactions'][mention].append(current_tweet['id'])
            
            archive['tweets'][current_tweet['id']] = current_tweet
            new_count += 1
            current_tweet = None
    
    archive['last_sync'] = datetime.now().isoformat()
    save_archive(archive)
    
    print(f"Synced {new_count} new tweet(s). Total: {len(archive['tweets'])}")
    print(f"Tracking {len(archive['interactions'])} user(s)")

def search(query):
    """Search archive for text."""
    archive = load_archive()
    query = query.lower()
    
    matches = []
    for tid, tweet in archive['tweets'].items():
        if query in tweet.get('text', '').lower():
            matches.append(tweet)
    
    if matches:
        print(f"Found {len(matches)} tweet(s) matching '{query}':\n")
        for t in matches[:10]:
            print(f"[{t['id']}] {t['text'][:80]}...")
    else:
        print(f"No tweets matching '{query}'")

def user_history(username):
    """Show all interactions with a user."""
    archive = load_archive()
    username = username.lstrip('@').lower()
    
    if username not in archive['interactions']:
        print(f"No recorded interactions with @{username}")
        return
    
    tweet_ids = archive['interactions'][username]
    print(f"📜 {len(tweet_ids)} interaction(s) with @{username}:\n")
    
    for tid in tweet_ids:
        tweet = archive['tweets'].get(tid, {})
        print(f"[{tid}] {tweet.get('text', 'Unknown')[:80]}...")

def stats():
    """Show archive statistics."""
    archive = load_archive()
    
    print(f"📊 Tweet Archive Stats:")
    print(f"   Total tweets: {len(archive['tweets'])}")
    print(f"   Users interacted with: {len(archive['interactions'])}")
    print(f"   Last sync: {archive.get('last_sync', 'Never')}")
    
    if archive['interactions']:
        print(f"\n   Top interactions:")
        sorted_users = sorted(archive['interactions'].items(), key=lambda x: len(x[1]), reverse=True)[:5]
        for user, tids in sorted_users:
            print(f"     @{user}: {len(tids)} tweets")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    if len(sys.argv) < 2:
        print("Usage: tweet_archive.py [sync|search X|user @X|stats]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "sync":
        sync()
    elif cmd == "search" and len(sys.argv) > 2:
        search(' '.join(sys.argv[2:]))
    elif cmd == "user" and len(sys.argv) > 2:
        user_history(sys.argv[2])
    elif cmd == "stats":
        stats()
    else:
        print("Usage: tweet_archive.py [sync|search X|user @X|stats]")
