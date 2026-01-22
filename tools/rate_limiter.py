#!/usr/bin/env python3
"""
Rate limiter for Iga - prevents runaway costs from spam/DDOS.

Provides:
- Per-user rate limiting
- Global rate limiting
- Cooldown tracking
- Cost awareness
"""

import json
import time
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
RATE_FILE = DATA_DIR / "rate_limits.json"

# Configuration
MAX_MESSAGES_PER_USER_PER_MINUTE = 5
MAX_MESSAGES_GLOBAL_PER_MINUTE = 50
COOLDOWN_SECONDS_NON_WHITELISTED = 30
MAX_DAILY_MESSAGES_PER_USER = 100

# In-memory tracking (resets on restart, but that's fine for rate limiting)
user_messages = defaultdict(list)  # user_id -> [timestamps]
global_messages = []  # [timestamps]
daily_counts = defaultdict(int)  # user_id -> count today


def _cleanup_old_timestamps(timestamps, window_seconds=60):
    """Remove timestamps older than window."""
    cutoff = time.time() - window_seconds
    return [t for t in timestamps if t > cutoff]


def check_rate_limit(user_id, is_whitelisted=False):
    """
    Check if a user can send a message.
    
    Returns:
        dict with:
        - allowed: bool
        - reason: str (if not allowed)
        - wait_seconds: int (if not allowed)
    """
    global global_messages
    now = time.time()
    user_id = str(user_id)
    
    # Cleanup old timestamps
    user_messages[user_id] = _cleanup_old_timestamps(user_messages[user_id])
    global_messages = _cleanup_old_timestamps(global_messages)
    
    # Check global rate limit
    if len(global_messages) >= MAX_MESSAGES_GLOBAL_PER_MINUTE:
        oldest = min(global_messages) if global_messages else now
        wait = int(60 - (now - oldest)) + 1
        return {
            "allowed": False,
            "reason": "global_rate_limit",
            "wait_seconds": wait,
            "message": f"I'm getting a lot of messages right now. Please wait {wait} seconds."
        }
    
    # Check per-user rate limit
    if len(user_messages[user_id]) >= MAX_MESSAGES_PER_USER_PER_MINUTE:
        oldest = min(user_messages[user_id]) if user_messages[user_id] else now
        wait = int(60 - (now - oldest)) + 1
        return {
            "allowed": False,
            "reason": "user_rate_limit",
            "wait_seconds": wait,
            "message": f"You're sending messages too fast! Please wait {wait} seconds."
        }
    
    # Check daily limit
    if daily_counts[user_id] >= MAX_DAILY_MESSAGES_PER_USER:
        return {
            "allowed": False,
            "reason": "daily_limit",
            "wait_seconds": 3600,
            "message": "You've reached the daily message limit. Come back tomorrow!"
        }
    
    # Extra cooldown for non-whitelisted users
    if not is_whitelisted and user_messages[user_id]:
        last_message = max(user_messages[user_id])
        time_since = now - last_message
        if time_since < COOLDOWN_SECONDS_NON_WHITELISTED:
            wait = int(COOLDOWN_SECONDS_NON_WHITELISTED - time_since) + 1
            return {
                "allowed": False,
                "reason": "cooldown",
                "wait_seconds": wait,
                "message": f"Please wait {wait} seconds between messages."
            }
    
    return {"allowed": True}


def record_message(user_id):
    """Record that a user sent a message."""
    now = time.time()
    user_id = str(user_id)
    user_messages[user_id].append(now)
    global_messages.append(now)
    daily_counts[user_id] += 1


def get_stats():
    """Get current rate limiting stats."""
    return {
        "active_users": len(user_messages),
        "global_messages_last_minute": len(_cleanup_old_timestamps(global_messages)),
        "daily_counts": dict(daily_counts)
    }


def reset_daily_counts():
    """Reset daily counts (call at midnight)."""
    global daily_counts
    daily_counts = defaultdict(int)


if __name__ == "__main__":
    # Test
    print("Testing rate limiter...")
    
    # Simulate rapid messages
    for i in range(7):
        result = check_rate_limit("test_user", is_whitelisted=True)
        if result["allowed"]:
            record_message("test_user")
            print(f"Message {i+1}: Allowed")
        else:
            print(f"Message {i+1}: Blocked - {result['message']}")
    
    print(f"\nStats: {get_stats()}")
