#!/usr/bin/env python3
"""
Weekly Stats - Generate weekly summary
"""

import json
from datetime import datetime, timedelta

SHIP_FILE = "data/ship_log.json"
COST_FILE = "data/openrouter_costs.json"

def get_weekly_stats():
    """Get stats for the past week"""
    # Load ships
    try:
        with open(SHIP_FILE) as f:
            data = json.load(f)
            ships = data.get("ships", [])
    except:
        ships = []
    
    # Load costs
    try:
        with open(COST_FILE) as f:
            data = json.load(f)
            requests = data.get("requests", [])
    except:
        requests = []
    
    # Calculate
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    week_ships = [s for s in ships if s.get("date", "") >= week_ago]
    week_cost = sum(r.get("cost", 0) for r in requests)
    
    return {
        "ships": len(week_ships),
        "cost": round(week_cost, 2),
        "requests": len(requests)
    }

if __name__ == "__main__":
    stats = get_weekly_stats()
    print(f"📊 Weekly Stats")
    print(f"Ships: {stats['ships']}")
    print(f"Cost: ${stats['cost']}")
    print(f"Requests: {stats['requests']}")