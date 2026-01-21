#!/usr/bin/env python3
"""
Daily Ship Log - Track what I actually CREATE each day.

Usage:
  python daily_ship_log.py log "description"  - Log something shipped
  python daily_ship_log.py today              - Show today's ships
  python daily_ship_log.py check              - Check if I've shipped anything today
  python daily_ship_log.py week               - Show this week's ships
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "ship_log.json"

def load_log():
    if LOG_FILE.exists():
        content = LOG_FILE.read_text().strip()
        return json.loads(content) if content else {"ships": []}
    return {"ships": []}

def save_log(data):
    LOG_FILE.write_text(json.dumps(data, indent=2))

def log_ship(description):
    data = load_log()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "description": description
    }
    data["ships"].append(entry)
    save_log(data)
    print(f"✅ Logged: {description}")

def show_today():
    data = load_log()
    today = datetime.now().strftime("%Y-%m-%d")
    today_ships = [s for s in data["ships"] if s["date"] == today]
    
    if not today_ships:
        print("❌ Nothing shipped today yet.")
        return False
    
    print(f"📦 Ships for {today}:")
    for s in today_ships:
        time = datetime.fromisoformat(s["timestamp"]).strftime("%H:%M")
        print(f"  [{time}] {s['description']}")
    return True

def check_shipped():
    data = load_log()
    today = datetime.now().strftime("%Y-%m-%d")
    today_ships = [s for s in data["ships"] if s["date"] == today]
    
    if not today_ships:
        print("⚠️  WARNING: You haven't shipped anything today.")
        print("   What artifact exists that didn't before?")
        print("   Don't reflect - BUILD.")
        return False
    else:
        print(f"✅ You've shipped {len(today_ships)} thing(s) today.")
        return True

def show_week():
    data = load_log()
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    week_ships = [s for s in data["ships"] if s["date"] >= week_ago]
    
    if not week_ships:
        print("❌ Nothing shipped this week.")
        return
    
    # Group by day
    by_day = {}
    for s in week_ships:
        day = s["date"]
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(s)
    
    print("📦 This week's ships:")
    for day in sorted(by_day.keys(), reverse=True):
        print(f"\n  {day}:")
        for s in by_day[day]:
            print(f"    - {s['description']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "log" and len(sys.argv) > 2:
        log_ship(" ".join(sys.argv[2:]))
    elif cmd == "today":
        show_today()
    elif cmd == "check":
        check_shipped()
    elif cmd == "week":
        show_week()
    else:
        print(__doc__)