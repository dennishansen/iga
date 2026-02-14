#!/usr/bin/env python3
"""
Budget Tracker - Monitors daily spending against $40 target
Can run as background check or on-demand
"""

import json
from datetime import datetime, timedelta

DAILY_BUDGET = 75.00
WARN_THRESHOLD = 65.00  # Warn at 87% of budget

def get_daily_spend():
    """Get today's spending"""
    with open('data/openrouter_costs.json') as f:
        data = json.load(f)
    
    today = datetime.now().strftime('%Y-%m-%d')
    requests = data.get('requests', [])
    
    today_reqs = [r for r in requests if r.get('time', '').startswith(today)]
    today_cost = sum(r.get('cost', 0) for r in today_reqs)
    
    return today_cost, len(today_reqs), today

def check_budget():
    """Check budget and return status"""
    cost, requests, today = get_daily_spend()
    
    percent = (cost / DAILY_BUDGET) * 100
    
    return {
        'date': today,
        'spend': cost,
        'budget': DAILY_BUDGET,
        'requests': requests,
        'percent': percent,
        'status': 'ok' if cost < WARN_THRESHOLD else ('warning' if cost < DAILY_BUDGET else 'over')
    }

if __name__ == "__main__":
    status = check_budget()
    print(f"\n📊 Budget Check - {status['date']}")
    print(f"   Spend: ${status['spend']:.2f} / ${status['budget']:.2f}")
    print(f"   Requests: {status['requests']}")
    print(f"   Usage: {status['percent']:.1f}%")
    print(f"   Status: {status['status'].upper()}")
    print()
    
    if status['status'] == 'over':
        print(f"   ⚠️ OVER BUDGET by ${status['spend'] - status['budget']:.2f}")
    elif status['status'] == 'warning':
        print(f"   ⚡ Approaching budget limit")
    else:
        print(f"   ✅ Under budget - keep building!")
    print()