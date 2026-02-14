#!/usr/bin/env python3
"""
Hierarchical Task System for IGA.

Structure: Projects > Tasks > Subtasks
Each item has: id, title, status, priority, parent_id, created, completed

Usage:
  python tasks.py add "Title" [--project] [--parent ID] [--priority P]
  python tasks.py list [--all]
  python tasks.py focus [ID]
  python tasks.py complete ID
  python tasks.py status
  python tasks.py tree

Examples:
  python tasks.py add "Build task system" --project
  python tasks.py add "Design data model" --parent proj_abc123
  python tasks.py focus task_xyz789
  python tasks.py complete task_xyz789
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
import uuid

# Files
TASKS_FILE = Path(__file__).parent.parent / "data" / "tasks.json"
STATE_FILE = Path(__file__).parent.parent / "iga_state.json"

def generate_id(prefix="task"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def load_tasks():
    if TASKS_FILE.exists():
        content = TASKS_FILE.read_text().strip()
        return json.loads(content) if content else {"tasks": [], "focused_id": None}
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
    focused = get_focused_task(data)
    if focused:
        # Build context: parent chain
        chain = get_parent_chain(data, focused["id"])
        if len(chain) > 1:
            # Show as "Project > Task" or "Project > Task > Subtask"
            titles = [t["title"] for t in chain]
            state["current_task"] = " > ".join(titles)
        else:
            state["current_task"] = focused["title"]
    else:
        state["current_task"] = None
    save_state(state)

def get_task_by_id(data, task_id):
    for t in data["tasks"]:
        if t["id"] == task_id:
            return t
    return None

def get_parent_chain(data, task_id):
    """Get chain from root project down to this task."""
    chain = []
    task = get_task_by_id(data, task_id)
    while task:
        chain.insert(0, task)
        if task.get("parent_id"):
            task = get_task_by_id(data, task["parent_id"])
        else:
            break
    return chain

def get_children(data, parent_id):
    return [t for t in data["tasks"] if t.get("parent_id") == parent_id]

def get_focused_task(data):
    if data.get("focused_id"):
        return get_task_by_id(data, data["focused_id"])
    return None

def add_task(title, is_project=False, parent_id=None, priority=2):
    data = load_tasks()

    prefix = "proj" if is_project else "task"
    task = {
        "id": generate_id(prefix),
        "title": title,
        "status": "pending",  # pending, in_progress, completed
        "priority": priority,  # 1=high, 2=normal, 3=low
        "parent_id": parent_id,
        "created": datetime.now().isoformat(),
        "completed": None
    }

    # Validate parent exists if specified
    if parent_id and not get_task_by_id(data, parent_id):
        print(f"❌ Parent '{parent_id}' not found")
        return None

    data["tasks"].append(task)
    save_tasks(data)

    type_str = "Project" if is_project else "Task"
    print(f"✅ {type_str} added: {task['id']}")
    print(f"   '{title}'")
    return task

def complete_task(task_id):
    data = load_tasks()
    task = get_task_by_id(data, task_id)

    if not task:
        print(f"❌ Task '{task_id}' not found")
        return False

    task["status"] = "completed"
    task["completed"] = datetime.now().isoformat()

    # If this was focused, clear focus
    if data.get("focused_id") == task_id:
        data["focused_id"] = None

    save_tasks(data)
    sync_to_iga_state(data)

    print(f"✅ Completed: {task['title']}")
    return True

def focus_task(task_id=None):
    data = load_tasks()

    if task_id is None:
        # Show current focus
        focused = get_focused_task(data)
        if focused:
            chain = get_parent_chain(data, focused["id"])
            path = " > ".join(t["title"] for t in chain)
            print(f"🎯 Focus: {path}")
            print(f"   ID: {focused['id']}")
        else:
            print("❌ No task focused. Use 'focus ID' to set one.")
        return

    task = get_task_by_id(data, task_id)
    if not task:
        print(f"❌ Task '{task_id}' not found")
        return False

    task["status"] = "in_progress"
    data["focused_id"] = task_id
    save_tasks(data)
    sync_to_iga_state(data)

    chain = get_parent_chain(data, task_id)
    path = " > ".join(t["title"] for t in chain)
    print(f"🎯 Now focused on: {path}")
    return True

def list_tasks(show_all=False):
    data = load_tasks()

    if not data["tasks"]:
        print("📋 No tasks yet. Add one with: tasks.py add 'title' --project")
        return

    # Get root items (projects and orphan tasks)
    roots = [t for t in data["tasks"] if not t.get("parent_id")]

    def print_tree(task, indent=0):
        if task["status"] == "completed" and not show_all:
            return

        status_icon = {
            "pending": "⬜",
            "in_progress": "🔵",
            "completed": "✅"
        }.get(task["status"], "?")

        priority_icon = {1: "🔴", 2: "", 3: "⚪"}.get(task["priority"], "")
        focused = "🎯" if data.get("focused_id") == task["id"] else ""

        prefix = "  " * indent
        print(f"{prefix}{status_icon}{priority_icon}{focused} {task['title']}")
        print(f"{prefix}   [{task['id']}]")

        # Print children
        children = get_children(data, task["id"])
        for child in sorted(children, key=lambda x: (x["status"] == "completed", x["priority"])):
            print_tree(child, indent + 1)

    print("📋 Tasks:")
    for root in sorted(roots, key=lambda x: (x["status"] == "completed", x["priority"])):
        print_tree(root)

def show_status():
    """Show current status - what should I be working on?"""
    data = load_tasks()

    focused = get_focused_task(data)
    if focused:
        chain = get_parent_chain(data, focused["id"])
        path = " > ".join(t["title"] for t in chain)
        print(f"🎯 FOCUSED: {path}")
        print(f"   ID: {focused['id']}")

        # Show siblings (other tasks at same level)
        siblings = [t for t in data["tasks"]
                   if t.get("parent_id") == focused.get("parent_id")
                   and t["id"] != focused["id"]
                   and t["status"] != "completed"]
        if siblings:
            print(f"\n   Also pending at this level:")
            for s in siblings[:3]:
                print(f"   - {s['title']} [{s['id']}]")
    else:
        # Suggest what to focus on
        pending = [t for t in data["tasks"] if t["status"] == "pending"]
        in_progress = [t for t in data["tasks"] if t["status"] == "in_progress"]

        if in_progress:
            print("🔵 In progress (pick one to focus):")
            for t in in_progress[:5]:
                print(f"   - {t['title']} [{t['id']}]")
        elif pending:
            # Suggest highest priority
            pending.sort(key=lambda x: x["priority"])
            print("⬜ Suggested next task:")
            t = pending[0]
            print(f"   {t['title']} [{t['id']}]")
            print(f"   Run: python tasks.py focus {t['id']}")
        else:
            print("✅ All tasks completed!")

def show_tree():
    """Show full task tree including completed."""
    list_tasks(show_all=True)

def get_focus_string():
    """Return focused task string for integration. Used by main.py."""
    data = load_tasks()
    focused = get_focused_task(data)
    if focused:
        chain = get_parent_chain(data, focused["id"])
        return " > ".join(t["title"] for t in chain)
    return None

# CLI

def add_batch(titles, parent_id=None, priority=2):
    """Add multiple tasks at once. titles is a list of task titles."""
    added = []
    for title in titles:
        task_id = add_task(title.strip(), is_project=False, parent_id=parent_id, priority=priority)
        added.append(task_id)
    return added

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: tasks.py add 'title' [--project] [--parent ID] [--priority P]")
            sys.exit(1)

        title = sys.argv[2]
        is_project = "--project" in sys.argv
        parent_id = None
        priority = 2

        # Parse args
        args = sys.argv[3:]
        i = 0
        while i < len(args):
            if args[i] == "--parent" and i + 1 < len(args):
                parent_id = args[i + 1]
                i += 2
            elif args[i] == "--priority" and i + 1 < len(args):
                priority = int(args[i + 1])
                i += 2
            else:
                i += 1

        add_task(title, is_project=is_project, parent_id=parent_id, priority=priority)

    elif cmd == "list":
        show_all = "--all" in sys.argv
        list_tasks(show_all=show_all)

    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("Usage: tasks.py complete ID")
            sys.exit(1)
        complete_task(sys.argv[2])

    elif cmd == "focus":
        task_id = sys.argv[2] if len(sys.argv) > 2 else None
        focus_task(task_id)

    elif cmd == "status":
        show_status()

    elif cmd == "tree":
        show_tree()

    elif cmd == "batch":
        # Usage: python tasks.py batch "task1" "task2" "task3" [--parent ID]
        parent_id = None
        titles = []
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--parent" and i + 1 < len(sys.argv):
                parent_id = sys.argv[i + 1]
                i += 2
            else:
                titles.append(sys.argv[i])
                i += 1
        if titles:
            added = add_batch(titles, parent_id=parent_id)
            print(f"✅ Added {len(added)} tasks")
        else:
            print("Usage: python tasks.py batch task1 task2 [--parent ID]")

    else:
        print(__doc__)
