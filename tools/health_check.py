#!/usr/bin/env python3
"""
Health Check - Quick system status
"""

import os, json
from datetime import datetime

def health_check():
    """Check system health"""
    status = {
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check git
    try:
        os.chdir("/Users/dennishansen/development/iga")
        result = os.popen("git status --short 2>/dev/null | wc -l").read().strip()
        status["checks"]["git"] = {"status": "ok", "pending": int(result)}
    except:
        status["checks"]["git"] = {"status": "error"}
    
    # Check budget
    try:
        with open("data/openrouter_costs.json") as f:
            data = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            requests = data.get("requests", [])
            today_cost = sum(r.get("cost", 0) for r in requests if today in r.get("timestamp", ""))
            status["checks"]["budget"] = {"status": "ok", "today_spent": round(today_cost, 2)}
    except:
        status["checks"]["budget"] = {"status": "error"}
    
    # Check disk
    try:
        result = os.popen("df -h . | tail -1 | awk '{print $5}'").read().strip()
        status["checks"]["disk"] = {"status": "ok", "usage": result}
    except:
        status["checks"]["disk"] = {"status": "error"}
    
    return status

if __name__ == "__main__":
    h = health_check()
    print("📊 Health Check")
    for check, data in h["checks"].items():
        print(f"  {check}: {data}")