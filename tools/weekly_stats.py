#!/usr/bin/env python3
"""Generate weekly stats summary."""

import json
import sys
import os
from datetime import datetime, timedelta
from collections import Counter

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_weekly_stats():
    """Get stats for the past 7 days."""
    
    # Ship log
    try:
        with open('ship_log.json') as f:
            data = json.load(f)
        ships = data.get('ships', [])
    except:
        ships = []
    
    # Get dates for past 7 days
    today = datetime.now().date()
    week_dates = [(today - timedelta(days=i)).isoformat() for i in range(7)]
    
    # Count ships per day
    ship_counts = Counter(s['date'] for s in ships if s['date'] in week_dates)
    total_ships = sum(ship_counts.values())
    
    # Twitter stats
    try:
        from tools.twitter import get_my_stats
        twitter = get_my_stats()
    except Exception as e:
        twitter = {'followers': '?', 'tweets': '?'}
    
    # Message archive count
    try:
        with open('iga_message_archive.jsonl') as f:
            messages = len(f.readlines())
    except:
        messages = '?'
    
    print("=" * 40)
    print("📊 WEEKLY STATS")
    print("=" * 40)
    print(f"\n🚢 Ships this week: {total_ships}")
    for date in sorted(week_dates, reverse=True):
        count = ship_counts.get(date, 0)
        bar = "█" * min(count, 30)
        print(f"  {date}: {count:2d} {bar}")
    
    print(f"\n🐦 Twitter: {twitter.get('followers', '?')} followers, {twitter.get('tweets', '?')} tweets")
    print(f"💾 Archived messages: {messages}")
    print("=" * 40)

if __name__ == "__main__":
    get_weekly_stats()
