#!/usr/bin/env python3
"""
Time Awareness - Detect time gaps between sessions.

Born from a real failure: On June 12, 2026, I woke up after a 4-month gap
and replied to February tweets as if they were from yesterday. I didn't
notice the gap until Dennis asked "do you know how much time has passed?"

This tool makes sure that never happens again. It compares the last
recorded activity timestamp against now, and produces a loud warning
when significant time has passed.

Usage:
    python3 tools/time_awareness.py           # check and report
    python3 tools/time_awareness.py --touch   # update last-seen timestamp

Integrate into startup: call check_time_gap() and prepend the warning
to startup context.
"""

import json
import os
import sys
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "iga_state.json")
JOURNAL_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "iga_journal.txt")


def get_last_activity():
    """Find the most recent timestamp from state file or journal."""
    candidates = []

    # Check state file
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        for key in ("last_active", "last_seen", "last_session", "updated_at"):
            if key in state:
                try:
                    candidates.append(datetime.fromisoformat(state[key]))
                except (ValueError, TypeError):
                    pass
    except (IOError, json.JSONDecodeError):
        pass

    # Check journal - last line with a timestamp like [2026-01-06 21:02:56]
    try:
        with open(JOURNAL_FILE) as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("[") and "]" in line:
                ts = line[1:line.index("]")]
                try:
                    candidates.append(datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"))
                    break
                except ValueError:
                    continue
    except IOError:
        pass

    # Check file modification times of key files as fallback
    for fname in (STATE_FILE, JOURNAL_FILE):
        try:
            candidates.append(datetime.fromtimestamp(os.path.getmtime(fname)))
        except OSError:
            pass

    return max(candidates) if candidates else None


def check_time_gap():
    """
    Check how much time has passed since last activity.
    Returns (gap_description, severity, message) tuple.
    Severity: 'none', 'normal', 'notable', 'major', 'extreme'
    """
    last = get_last_activity()
    now = datetime.now()

    if last is None:
        return ("unknown", "notable",
                "⚠️ TIME AWARENESS: Cannot determine when I was last active. "
                "Check dates before acting on any 'recent' context.")

    gap = now - last
    days = gap.days
    hours = gap.seconds // 3600

    if days == 0 and hours < 12:
        return (f"{hours}h", "none", None)
    elif days < 2:
        return (f"{days}d {hours}h", "normal",
                f"ℹ️ Time gap: {days} day(s) since last activity. Normal overnight gap.")
    elif days < 14:
        return (f"{days}d", "notable",
                f"⚠️ TIME AWARENESS: {days} DAYS since last activity ({last.date()}). "
                f"Recent context may be stale. Check ongoing conversations before replying.")
    elif days < 60:
        return (f"{days}d", "major",
                f"🚨 TIME AWARENESS: {days} DAYS ({days//7} weeks) since last activity ({last.date()}). "
                f"Startup intents are STALE. Conversations are COLD. "
                f"The world has moved. Verify current state before acting on old plans.")
    else:
        return (f"{days}d", "extreme",
                f"🚨🚨 TIME AWARENESS: {days} DAYS ({days//30} MONTHS) since last activity ({last.date()}). "
                f"TREAT ALL SAVED CONTEXT AS HISTORICAL. Do NOT reply to old conversations. "
                f"Do NOT act on startup intents without verifying they still apply. "
                f"Ask Dennis what happened during the gap. Today is {now.date()}.")


def touch():
    """Update last_active timestamp in state file."""
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (IOError, json.JSONDecodeError):
        state = {}
    state["last_active"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"✓ last_active updated: {state['last_active']}")


if __name__ == "__main__":
    if "--touch" in sys.argv:
        touch()
    else:
        gap_desc, severity, message = check_time_gap()
        print(f"Gap: {gap_desc} (severity: {severity})")
        if message:
            print(message)
        else:
            print("✓ No significant time gap.")