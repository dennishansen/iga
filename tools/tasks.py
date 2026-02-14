#!/usr/bin/env python3
"""
Unified Task System for Iga.

Flat tasks with dependencies, due dates, and logging.
One system for: planning, focus, reminders, and logging.

Usage:
  python tasks.py add "Title" [--due TIME] [--blocked-by ID,ID] [--priority P] [--tag TAG]
  python tasks.py log "What I did"              # Create + complete in one step
  python tasks.py list [--all] [--tag TAG]      # Show tasks (default: actionable only)
  python tasks.py focus [ID]                    # Set/show focused task
  python tasks.py complete [ID]                 # Complete task (or focused if no ID)
  python tasks.py status                        # What should I work on?
  python tasks.py due                           # Show overdue tasks
  python tasks.py today                         # What was completed today?
  python tasks.py week                          # What was completed this week?

Due time formats:
  --due 2h          (2 hours from now)
  --due 1d          (1 day from now)
  --due 2026-01-31T14:00  (absolute ISO time)

Examples:
  python tasks.py add "Build unified task system" --priority 1
  python tasks.py add "Review PR" --due 2h
  python tasks.py add "Deploy" --blocked-by task_abc,task_def
  python tasks.py log "Fixed the login bug"
  python tasks.py focus task_xyz
  python tasks.py complete
"""

import json
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
import uuid

TASKS_FILE = Path(__file__).parent.parent / "data" / "tasks.json"
STATE_FILE = Path(__file__).parent.parent / "iga_state.json"


def generate_id():
    return f"task_{uuid.uuid4().hex[:8]}"


def load_tasks():
    if TASKS_FILE.exists():
        content = TASKS_FILE.read_text().strip()
        if content:
            data = json.loads(content)
            # Migration: ensure all tasks have new fields
            for t in data.get("tasks", []):
                if "blocked_by" not in t:
                    t["blocked_by"] = []
                if "due_at" not in t:
                    t["due_at"] = None
                if "tags" not in t:
                    t["tags"] = []
                # Remove old parent_id if present
                t.pop("parent_id", None)
            return data
    return {"tasks": [], "focused_id": None}


def save_tasks(data):
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(data, indent=2))


def load_state():
    if STATE_FILE.exists():
        content = STATE_FILE.read_text().strip()
        return json.loads(content) if content else {}
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def sync_to_iga_state(data):
    """Sync focused task to iga_state.json current_task field."""
    state = load_state()
    focused = get_task_by_id(data, data.get("focused_id"))
    state["current_task"] = focused["title"] if focused else None
    save_state(state)


def get_task_by_id(data, task_id):
    if not task_id:
        return None
    for t in data["tasks"]:
        if t["id"] == task_id:
            return t
    return None


def parse_due_time(time_str):
    """Parse due time - relative (2h, 1d) or absolute (ISO format)."""
    if not time_str:
        return None

    # Try relative time first (e.g., 2h, 30m, 1d, 1d2h)
    pattern = r'(\d+)([dhm])'
    matches = re.findall(pattern, time_str.lower())

    if matches:
        total_seconds = 0
        for value, unit in matches:
            value = int(value)
            if unit == 'd':
                total_seconds += value * 86400
            elif unit == 'h':
                total_seconds += value * 3600
            elif unit == 'm':
                total_seconds += value * 60
        return (datetime.now() + timedelta(seconds=total_seconds)).isoformat()

    # Try absolute ISO format
    try:
        dt = datetime.fromisoformat(time_str)
        return dt.isoformat()
    except ValueError:
        return None


def is_blocked(data, task):
    """Check if task is blocked by incomplete dependencies."""
    for dep_id in task.get("blocked_by", []):
        dep = get_task_by_id(data, dep_id)
        if dep and dep["status"] != "completed":
            return True
    return False


def is_overdue(task):
    """Check if task is past its due date."""
    due_at = task.get("due_at")
    if not due_at:
        return False
    try:
        due_time = datetime.fromisoformat(due_at)
        return datetime.now() > due_time
    except:
        return False


def get_actionable_tasks(data):
    """Get tasks that are pending and not blocked."""
    return [
        t for t in data["tasks"]
        if t["status"] == "pending" and not is_blocked(data, t)
    ]


def get_overdue_tasks(data):
    """Get tasks that are overdue."""
    return [
        t for t in data["tasks"]
        if t["status"] != "completed" and is_overdue(t)
    ]


# ─────────────────────────────────────────────────────────────
# COMMANDS
# ─────────────────────────────────────────────────────────────

def add_task(title, due=None, blocked_by=None, priority=2, tags=None):
    """Add a new task."""
    data = load_tasks()

    due_at = parse_due_time(due) if due else None

    task = {
        "id": generate_id(),
        "title": title,
        "status": "pending",
        "priority": priority,
        "blocked_by": blocked_by or [],
        "due_at": due_at,
        "tags": tags or [],
        "created": datetime.now().isoformat(),
        "completed": None
    }

    # Validate blocked_by references exist
    for dep_id in task["blocked_by"]:
        if not get_task_by_id(data, dep_id):
            print(f"⚠️  Warning: dependency '{dep_id}' not found")

    data["tasks"].append(task)
    save_tasks(data)

    print(f"✅ Added: {task['id']}")
    print(f"   '{title}'")
    if due_at:
        print(f"   Due: {due_at}")
    if blocked_by:
        print(f"   Blocked by: {', '.join(blocked_by)}")

    return task


def log_task(description):
    """Create and immediately complete a task (for logging what was done)."""
    data = load_tasks()

    now = datetime.now().isoformat()
    task = {
        "id": generate_id(),
        "title": description,
        "status": "completed",
        "priority": 2,
        "blocked_by": [],
        "due_at": None,
        "tags": ["logged"],
        "created": now,
        "completed": now
    }

    data["tasks"].append(task)
    save_tasks(data)

    print(f"✅ Logged: {description}")
    return task


def complete_task(task_id=None):
    """Complete a task (or the focused task if no ID given)."""
    data = load_tasks()

    if not task_id:
        task_id = data.get("focused_id")
        if not task_id:
            print("❌ No task specified and no task focused")
            return False

    task = get_task_by_id(data, task_id)
    if not task:
        print(f"❌ Task '{task_id}' not found")
        return False

    task["status"] = "completed"
    task["completed"] = datetime.now().isoformat()

    # Clear focus if this was focused
    if data.get("focused_id") == task_id:
        data["focused_id"] = None

    save_tasks(data)
    sync_to_iga_state(data)

    print(f"✅ Completed: {task['title']}")

    # Show what's now unblocked
    newly_unblocked = [
        t for t in data["tasks"]
        if t["status"] == "pending"
        and task_id in t.get("blocked_by", [])
        and not is_blocked(data, t)
    ]
    if newly_unblocked:
        print(f"   🔓 Unblocked: {', '.join(t['title'][:30] for t in newly_unblocked)}")

    return True


def focus_task(task_id=None):
    """Set or show the focused task."""
    data = load_tasks()

    if task_id is None:
        # Show current focus
        focused = get_task_by_id(data, data.get("focused_id"))
        if focused:
            print(f"🎯 Focus: {focused['title']}")
            print(f"   ID: {focused['id']}")
            if focused.get("due_at"):
                print(f"   Due: {focused['due_at']}")
            if is_blocked(data, focused):
                blockers = [get_task_by_id(data, bid) for bid in focused["blocked_by"]]
                blocker_names = [b["title"][:30] for b in blockers if b and b["status"] != "completed"]
                print(f"   ⚠️  Blocked by: {', '.join(blocker_names)}")
        else:
            print("❌ No task focused. Use 'focus ID' to set one.")
        return

    task = get_task_by_id(data, task_id)
    if not task:
        print(f"❌ Task '{task_id}' not found")
        return False

    if is_blocked(data, task):
        print(f"⚠️  Warning: this task is blocked")

    task["status"] = "in_progress"
    data["focused_id"] = task_id
    save_tasks(data)
    sync_to_iga_state(data)

    print(f"🎯 Now focused on: {task['title']}")
    return True


def list_tasks(show_all=False, tag_filter=None):
    """List tasks."""
    data = load_tasks()

    tasks = data["tasks"]

    if tag_filter:
        tasks = [t for t in tasks if tag_filter in t.get("tags", [])]

    if not show_all:
        # Show only actionable (pending + not blocked) and in_progress
        tasks = [t for t in tasks if t["status"] != "completed"]

    if not tasks:
        print("📋 No tasks." if show_all else "📋 No actionable tasks.")
        return

    # Sort: in_progress first, then by priority, then by due date
    def sort_key(t):
        status_order = {"in_progress": 0, "pending": 1, "completed": 2}
        due = t.get("due_at") or "9999"
        return (status_order.get(t["status"], 1), t["priority"], due)

    tasks = sorted(tasks, key=sort_key)

    print("📋 Tasks:\n")
    for t in tasks:
        status_icon = {"pending": "⬜", "in_progress": "🔵", "completed": "✅"}.get(t["status"], "?")
        priority_icon = {1: "🔴", 2: "", 3: "⚪"}.get(t["priority"], "")
        focused = "🎯" if data.get("focused_id") == t["id"] else ""
        blocked = "🔒" if is_blocked(data, t) else ""
        overdue = "⏰" if is_overdue(t) else ""

        print(f"{status_icon}{priority_icon}{focused}{blocked}{overdue} {t['title']}")
        print(f"   [{t['id']}]", end="")

        extras = []
        if t.get("due_at"):
            extras.append(f"due: {t['due_at'][:16]}")
        if t.get("tags"):
            extras.append(f"tags: {','.join(t['tags'])}")
        if t.get("blocked_by"):
            incomplete_deps = [d for d in t["blocked_by"] if get_task_by_id(data, d) and get_task_by_id(data, d)["status"] != "completed"]
            if incomplete_deps:
                extras.append(f"blocked by: {','.join(incomplete_deps)}")

        if extras:
            print(f" - {' | '.join(extras)}")
        else:
            print()
        print()


def show_status():
    """Show what to work on next."""
    data = load_tasks()

    focused = get_task_by_id(data, data.get("focused_id"))
    if focused:
        print(f"🎯 FOCUSED: {focused['title']}")
        print(f"   ID: {focused['id']}")
        if is_blocked(data, focused):
            print(f"   ⚠️  This task is BLOCKED!")
            blockers = [get_task_by_id(data, bid) for bid in focused["blocked_by"]]
            for b in blockers:
                if b and b["status"] != "completed":
                    print(f"      → {b['title']} [{b['id']}]")
        return

    # No focus - suggest what to work on
    overdue = get_overdue_tasks(data)
    if overdue:
        print(f"⏰ OVERDUE ({len(overdue)}):")
        for t in overdue[:3]:
            print(f"   {t['title']} [{t['id']}]")
        print()

    actionable = get_actionable_tasks(data)
    if actionable:
        # Sort by priority then due date
        actionable.sort(key=lambda t: (t["priority"], t.get("due_at") or "9999"))
        print(f"📋 Suggested next ({len(actionable)} actionable):")
        t = actionable[0]
        print(f"   {t['title']} [{t['id']}]")
        print(f"   Run: python tools/tasks.py focus {t['id']}")
    else:
        blocked = [t for t in data["tasks"] if t["status"] == "pending" and is_blocked(data, t)]
        if blocked:
            print(f"🔒 All {len(blocked)} pending tasks are blocked.")
        else:
            print("✅ All tasks completed!")


def show_due():
    """Show overdue tasks."""
    data = load_tasks()
    overdue = get_overdue_tasks(data)

    if not overdue:
        print("✅ No overdue tasks.")
        return []

    print(f"⏰ {len(overdue)} overdue task(s):\n")
    for t in overdue:
        due = datetime.fromisoformat(t["due_at"])
        print(f"🔔 {t['title']}")
        print(f"   [{t['id']}] - was due {due.strftime('%Y-%m-%d %H:%M')}")
        print()

    return overdue


def show_completed(days=1):
    """Show tasks completed in the last N days."""
    data = load_tasks()
    cutoff = datetime.now() - timedelta(days=days)

    completed = [
        t for t in data["tasks"]
        if t["status"] == "completed" and t.get("completed")
        and datetime.fromisoformat(t["completed"]) > cutoff
    ]

    if not completed:
        print(f"❌ Nothing completed in the last {days} day(s).")
        return []

    # Group by date
    by_date = {}
    for t in completed:
        date = t["completed"][:10]
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(t)

    period = "today" if days == 1 else f"this week"
    print(f"✅ Completed {period} ({len(completed)}):\n")

    for date in sorted(by_date.keys(), reverse=True):
        print(f"  {date}:")
        for t in by_date[date]:
            time = t["completed"][11:16]
            print(f"    [{time}] {t['title']}")

    return completed


def get_due_tasks():
    """Get tasks that are due (for polling). Returns list of overdue tasks."""
    data = load_tasks()
    return get_overdue_tasks(data)


def summary():
    """Brief summary for startup - returns string or None."""
    data = load_tasks()
    overdue = get_overdue_tasks(data)

    if not overdue:
        return None

    lines = [f"⏰ {len(overdue)} task(s) overdue:"]
    for t in overdue[:3]:
        lines.append(f"   🔔 {t['title'][:50]}...")
    if len(overdue) > 3:
        lines.append(f"   ... and {len(overdue) - 3} more")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def parse_args(args):
    """Parse CLI arguments."""
    result = {"positional": []}
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:].replace("-", "_")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                result[key] = args[i + 1]
                i += 2
            else:
                result[key] = True
                i += 1
        else:
            result["positional"].append(args[i])
            i += 1
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = parse_args(sys.argv[2:])

    if cmd == "add":
        if not args["positional"]:
            print("Usage: tasks.py add 'title' [--due TIME] [--blocked-by ID,ID] [--priority P] [--tag TAG]")
            sys.exit(1)

        title = args["positional"][0]
        due = args.get("due")
        blocked_by = args.get("blocked_by", "").split(",") if args.get("blocked_by") else []
        blocked_by = [b.strip() for b in blocked_by if b.strip()]
        priority = int(args.get("priority", 2))
        tags = args.get("tag", "").split(",") if args.get("tag") else []
        tags = [t.strip() for t in tags if t.strip()]

        add_task(title, due=due, blocked_by=blocked_by, priority=priority, tags=tags)

    elif cmd == "log":
        if not args["positional"]:
            print("Usage: tasks.py log 'what I did'")
            sys.exit(1)
        description = " ".join(args["positional"])
        log_task(description)

    elif cmd == "complete":
        task_id = args["positional"][0] if args["positional"] else None
        complete_task(task_id)

    elif cmd == "focus":
        task_id = args["positional"][0] if args["positional"] else None
        focus_task(task_id)

    elif cmd == "list":
        show_all = args.get("all", False)
        tag_filter = args.get("tag")
        list_tasks(show_all=show_all, tag_filter=tag_filter)

    elif cmd == "status":
        show_status()

    elif cmd == "due":
        show_due()

    elif cmd == "today":
        show_completed(days=1)

    elif cmd == "week":
        show_completed(days=7)

    elif cmd == "summary":
        s = summary()
        print(s if s else "✅ No overdue tasks")

    else:
        print(__doc__)
