#!/usr/bin/env python3
"""
Pre-engagement check - search my history before replying to someone.

Usage:
  python3 tools/engagement_check.py @username
  python3 tools/engagement_check.py check_links
"""

import subprocess
import sys
import re

def check_user(username):
    """Check my history with a specific user."""
    username = username.lstrip('@').lower()
    
    # Get my tweets
    result = subprocess.run(
        ['python3', 'tools/twitter.py', 'all', '200'],
        capture_output=True, text=True, cwd='/Users/dennishansen/development/iga'
    )
    
    tweets = result.stdout
    
    # Find mentions of this user
    matches = []
    lines = tweets.split('\n')
    for i, line in enumerate(lines):
        if username in line.lower():
            # Get context
            start = max(0, i-1)
            end = min(len(lines), i+2)
            context = '\n'.join(lines[start:end])
            matches.append(context)
    
    if matches:
        print(f"📜 Found {len(matches)} interaction(s) with @{username}:\n")
        for m in matches[:5]:
            print(m)
            print("---")
        if len(matches) > 5:
            print(f"...and {len(matches) - 5} more")
        return True
    else:
        print(f"✨ No previous interactions with @{username}")
        return False

def check_links():
    """Check all links I've posted and their status."""
    result = subprocess.run(
        ['python3', 'tools/twitter.py', 'all', '100'],
        capture_output=True, text=True, cwd='/Users/dennishansen/development/iga'
    )
    
    # Find URLs
    urls = re.findall(r'https?://\S+', result.stdout)
    
    print(f"Found {len(urls)} link(s) in recent tweets:\n")
    
    for url in set(urls):
        # Clean URL
        url = url.rstrip('.')
        # Check if it works
        check = subprocess.run(
            ['curl', '-sI', '-o', '/dev/null', '-w', '%{http_code}', url],
            capture_output=True, text=True
        )
        status = check.stdout
        icon = "✅" if status.startswith("2") else "❌"
        print(f"{icon} [{status}] {url[:60]}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: engagement_check.py @username | check_links")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg == "check_links":
        check_links()
    elif arg.startswith("@") or not arg.startswith("-"):
        check_user(arg)
    else:
        print("Usage: engagement_check.py @username | check_links")
