#!/usr/bin/env python3
"""
Reminder System for IGA.

Set reminders for future times to prompt the agent to take action.

Usage:
  python3 tools/reminders.py add "Message" --in 2h          # Relative time
  python3 tools/reminders.py add "Message" --at 2026-01-17T10:00  # Absolute time
  python3 tools/reminders.py list                           # Show pending reminders
  python3 tools/reminders.py due                            # Show reminders past their time
  python3 tools/reminders.py complete ID                    # Mark reminder as completed

Relative time formats:
  --in 30m    (30 minutes)
  --in 2h     (2 hours)
  --in 1d     (1 day)
  --in 1d2h   (1 day 2 hours)

Examples:
  python3 tools/reminders.py add "Check Twitter engagement" --in 2h
  python3 tools/reminders.py add "Review costs" --at 2026-01-17T10:00
  python3 tools/reminders.py list
  python3 tools/reminders.py due
  python3 tools/reminders.py complete rem_abc12345
"""

import json
import sys
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import uuid

# Files
REMINDERS_FILE = Path(__file__).parent.parent / "data" / "reminders.json"


def generate_id():
    return f"rem_{uuid.uuid4().hex[:8]}"


def load_reminders():
    if REMINDERS_FILE.exists():
        return json.loads(REMINDERS_FILE.read_text())
    return {"reminders": []}


def save_reminders(data):
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    REMINDERS_FILE.write_text(json.dumps(data, indent=2))


def parse_relative_time(time_str):
    """Parse relative time like '2h', '30m', '1d', '1d2h30m'."""
    total_seconds = 0

    # Match patterns like 1d, 2h, 30m
    pattern = r'(\d+)([dhm])'
    matches = re.findall(pattern, time_str.lower())

    if not matches:
        return None

    for value, unit in matches:
        value = int(value)
        if unit == 'd':
            total_seconds += value * 86400
        elif unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60

    return datetime.now() + timedelta(seconds=total_seconds)


def parse_absolute_time(time_str):
    """Parse absolute time like '2026-01-17T10:00'."""
    try:
        return datetime.fromisoformat(time_str)
    except ValueError:
        return None


def add_reminder(message, relative_time=None, absolute_time=None):
    """Add a new reminder."""
    data = load_reminders()

    # Determine the due time
    due_time = None
    if relative_time:
        due_time = parse_relative_time(relative_time)
        if not due_time:
            print(f"❌ Invalid relative time format: {relative_time}")
            print("   Use formats like: 30m, 2h, 1d, 1d2h30m")
            return None
    elif absolute_time:
        due_time = parse_absolute_time(absolute_time)
        if not due_time:
            print(f"❌ Invalid absolute time format: {absolute_time}")
            print("   Use ISO format: 2026-01-17T10:00")
            return None
    else:
        print("❌ Must specify either --in or --at")
        return None

    reminder = {
        "id": generate_id(),
        "message": message,
        "due_at": due_time.isoformat(),
        "status": "pending",  # pending, triggered, completed
        "created_at": datetime.now().isoformat(),
        "completed_at": None
    }

    data["reminders"].append(reminder)
    save_reminders(data)

    print(f"✅ Reminder set: {reminder['id']}")
    print(f"   '{message}'")
    print(f"   Due: {due_time.strftime('%Y-%m-%d %H:%M')}")
    return reminder


def list_reminders(show_all=False):
    """List pending (or all) reminders."""
    data = load_reminders()

    reminders = data["reminders"]
    if not show_all:
        reminders = [r for r in reminders if r["status"] == "pending"]

    if not reminders:
        print("📭 No pending reminders.")
        return []

    # Sort by due time
    reminders.sort(key=lambda x: x["due_at"])

    now = datetime.now()
    print(f"⏰ Reminders ({len(reminders)}):\n")

    for r in reminders:
        due = datetime.fromisoformat(r["due_at"])
        is_overdue = due <= now and r["status"] == "pending"

        status_icon = {
            "pending": "🔔" if not is_overdue else "🚨",
            "triggered": "⚡",
            "completed": "✅"
        }.get(r["status"], "?")

        # Format time remaining/overdue
        if r["status"] == "pending":
            diff = due - now
            if diff.total_seconds() > 0:
                hours = int(diff.total_seconds() // 3600)
                minutes = int((diff.total_seconds() % 3600) // 60)
                if hours > 24:
                    time_str = f"in {hours // 24}d {hours % 24}h"
                elif hours > 0:
                    time_str = f"in {hours}h {minutes}m"
                else:
                    time_str = f"in {minutes}m"
            else:
                diff = now - due
                hours = int(diff.total_seconds() // 3600)
                minutes = int((diff.total_seconds() % 3600) // 60)
                if hours > 0:
                    time_str = f"OVERDUE {hours}h {minutes}m"
                else:
                    time_str = f"OVERDUE {minutes}m"
        else:
            time_str = r["status"]

        print(f"{status_icon} {r['message']}")
        print(f"   [{r['id']}] - {due.strftime('%Y-%m-%d %H:%M')} ({time_str})")
        print()

    return reminders


def get_due_reminders():
    """Get reminders that are past their due time and still pending."""
    data = load_reminders()
    now = datetime.now()

    due = []
    for r in data["reminders"]:
        if r["status"] == "pending":
            due_time = datetime.fromisoformat(r["due_at"])
            if due_time <= now:
                due.append(r)

    return due


def show_due():
    """Show reminders that are due now."""
    due = get_due_reminders()

    if not due:
        print("✅ No reminders due right now.")
        return []

    print(f"🚨 {len(due)} reminder(s) DUE:\n")
    for r in due:
        due_time = datetime.fromisoformat(r["due_at"])
        print(f"🔔 {r['message']}")
        print(f"   [{r['id']}] - was due {due_time.strftime('%Y-%m-%d %H:%M')}")
        print()

    return due


def complete_reminder(reminder_id):
    """Mark a reminder as completed."""
    data = load_reminders()

    for r in data["reminders"]:
        if r["id"] == reminder_id:
            r["status"] = "completed"
            r["completed_at"] = datetime.now().isoformat()
            save_reminders(data)
            print(f"✅ Completed: {r['message']}")
            return True

    print(f"❌ Reminder '{reminder_id}' not found")
    return False


def mark_triggered(reminder_id):
    """Mark a reminder as triggered (used by polling system)."""
    data = load_reminders()

    for r in data["reminders"]:
        if r["id"] == reminder_id:
            r["status"] = "triggered"
            save_reminders(data)
            return True
    return False


def summary():
    """Brief summary for startup - returns string or None."""
    due = get_due_reminders()
    if not due:
        return None

    lines = [f"⏰ {len(due)} reminder(s) due:"]
    for r in due[:3]:
        lines.append(f"   🔔 {r['message'][:50]}...")
    if len(due) > 3:
        lines.append(f"   ... and {len(due) - 3} more")
    return "\n".join(lines)


# CLI
if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: reminders.py add 'message' [--in TIME | --at TIME]")
            sys.exit(1)

        message = sys.argv[2]
        relative_time = None
        absolute_time = None

        # Parse args
        args = sys.argv[3:]
        i = 0
        while i < len(args):
            if args[i] == "--in" and i + 1 < len(args):
                relative_time = args[i + 1]
                i += 2
            elif args[i] == "--at" and i + 1 < len(args):
                absolute_time = args[i + 1]
                i += 2
            else:
                i += 1

        add_reminder(message, relative_time=relative_time, absolute_time=absolute_time)

    elif cmd == "list":
        show_all = "--all" in sys.argv
        list_reminders(show_all=show_all)

    elif cmd == "due":
        show_due()

    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("Usage: reminders.py complete ID")
            sys.exit(1)
        complete_reminder(sys.argv[2])

    elif cmd == "summary":
        s = summary()
        print(s if s else "✅ No reminders due")

    else:
        print(__doc__)
