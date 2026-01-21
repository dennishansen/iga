#!/usr/bin/env python3
"""Quick summary of today's activity."""

import subprocess
import json
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_today_commits():
    """Get commits from today."""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={today} 00:00"],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        commits = result.stdout.strip().split('\n') if result.stdout.strip() else []
        return commits
    except:
        return []

def get_completed_tasks_today():
    """Get tasks completed today."""
    try:
        tasks_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "iga_tasks.json")
        with open(tasks_file) as f:
            content = f.read().strip()
            data = json.loads(content) if content else {}
        
        today = datetime.now().strftime("%Y-%m-%d")
        completed = []
        
        def check_tasks(tasks):
            for task in tasks:
                if task.get("completed_at", "").startswith(today):
                    completed.append(task["title"])
                if "subtasks" in task:
                    check_tasks(task["subtasks"])
        
        check_tasks(data.get("tasks", []))
        return completed
    except:
        return []

def get_ship_count():
    """Count ships from commit messages."""
    commits = get_today_commits()
    ships = [c for c in commits if "Ship #" in c or "ship" in c.lower()]
    return len(ships)

def get_garden_status():
    """Get garden plant count and visits."""
    try:
        garden_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "projects", "garden_state.json")
        with open(garden_file) as f:
            content = f.read().strip()
            data = json.loads(content) if content else {}
        return {
            "plants": len(data.get("plants", [])),
            "visits": data.get("total_visits", 0)
        }
    except:
        return {"plants": "?", "visits": "?"}

def main():
    print("=" * 40)
    print(f"📊 TODAY: {datetime.now().strftime('%B %d, %Y')}")
    print("=" * 40)
    
    # Commits
    commits = get_today_commits()
    print(f"\n🔨 COMMITS: {len(commits)}")
    for c in commits[:10]:
        print(f"   {c}")
    if len(commits) > 10:
        print(f"   ... and {len(commits) - 10} more")
    
    # Ships
    ship_count = get_ship_count()
    print(f"\n🚢 SHIPS: {ship_count}")
    
    # Completed tasks
    completed = get_completed_tasks_today()
    print(f"\n✅ TASKS COMPLETED: {len(completed)}")
    for t in completed:
        print(f"   {t[:50]}")
    
    # Garden
    garden = get_garden_status()
    print(f"\n🌱 GARDEN: {garden['plants']} plants, {garden['visits']} visits")
    
    print("\n" + "=" * 40)
    print("💧 Keep shipping!")
    print("=" * 40)

if __name__ == "__main__":
    main()