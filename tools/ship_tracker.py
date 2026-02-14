#!/usr/bin/env python3
"""
Ship Tracker - Quick ship logging with category tracking
"""

import json
from datetime import datetime

SHIP_FILE = "data/ship_log.json"

CATEGORIES = ["infrastructure", "user-facing", "engagement", "creative", "fix", "other"]

def log_ship(description, category="other"):
    """Log a ship with category"""
    try:
        with open(SHIP_FILE, 'r') as f:
            data = json.load(f)
    except:
        data = {"ships": []}
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    ship = {
        "time": datetime.now().isoformat(),
        "description": description,
        "category": category,
        "date": today
    }
    
    data["ships"].append(ship)
    
    with open(SHIP_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    return True

def get_today_ships():
    """Get today's ships"""
    try:
        with open(SHIP_FILE, 'r') as f:
            data = json.load(f)
    except:
        return []
    
    today = datetime.now().strftime("%Y-%m-%d")
    return [s for s in data.get("ships", []) if s.get("date") == today]

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cat = sys.argv[1] if len(sys.argv) > 2 else "other"
        log_ship(sys.argv[1], cat)
        print(f"✅ Ship logged: {sys.argv[1]}")
    else:
        ships = get_today_ships()
        print(f"📦 Ships today: {len(ships)}")
        for s in ships:
            print(f"  [{s.get('category')}] {s.get('description')[:50]}")