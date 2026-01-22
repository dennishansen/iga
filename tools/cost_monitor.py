#!/usr/bin/env python3
"""
Cost monitor for Iga - tracks OpenRouter API usage in real-time.
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
COST_LOG = DATA_DIR / "cost_log.json"

def get_openrouter_usage():
    """Get current usage from OpenRouter API."""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        return {"error": "No API key"}
    
    r = requests.get(
        "https://openrouter.ai/api/v1/auth/key",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    
    if r.status_code == 200:
        return r.json().get('data', {})
    return {"error": f"API error: {r.status_code}"}

def log_usage():
    """Log current usage with timestamp."""
    usage = get_openrouter_usage()
    
    if "error" in usage:
        print(f"Error: {usage['error']}")
        return
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "usage_total": usage.get('usage', 0),
        "usage_daily": usage.get('usage_daily', 0),
        "usage_weekly": usage.get('usage_weekly', 0),
        "usage_monthly": usage.get('usage_monthly', 0)
    }
    
    # Load existing log
    if COST_LOG.exists():
        with open(COST_LOG) as f:
            log = json.load(f)
    else:
        log = {"entries": []}
    
    log["entries"].append(entry)
    
    # Keep last 1000 entries
    log["entries"] = log["entries"][-1000:]
    
    with open(COST_LOG, 'w') as f:
        json.dump(log, f, indent=2)
    
    return entry

def print_status():
    """Print current cost status."""
    usage = get_openrouter_usage()
    
    if "error" in usage:
        print(f"Error: {usage['error']}")
        return
    
    print("=" * 40)
    print("OPENROUTER COST STATUS")
    print("=" * 40)
    print(f"Total usage:   ${usage.get('usage', 0):.2f}")
    print(f"Today:         ${usage.get('usage_daily', 0):.2f}")
    print(f"This week:     ${usage.get('usage_weekly', 0):.2f}")
    print(f"This month:    ${usage.get('usage_monthly', 0):.2f}")
    print("=" * 40)
    
    # Calculate averages
    daily = usage.get('usage_daily', 0)
    print(f"\nAt today's rate (${daily:.2f}/day):")
    print(f"  Weekly:  ${daily * 7:.2f}")
    print(f"  Monthly: ${daily * 30:.2f}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "log":
        entry = log_usage()
        if entry:
            print(f"Logged: ${entry['usage_daily']:.2f} today, ${entry['usage_total']:.2f} total")
    else:
        print_status()
