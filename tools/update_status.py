#!/usr/bin/env python3
"""
Update online/offline status for the website.
Creates a small JSON file that can be fetched by the website.
"""

import json
import os
from datetime import datetime
from pathlib import Path

STATUS_FILE = Path(__file__).parent.parent / 'docs' / 'status.json'

def update_status(online: bool, message: str = None):
    """Update the status file."""
    status = {
        'online': online,
        'timestamp': datetime.now().isoformat(),
        'message': message or ('Awake and active 💧' if online else 'Resting... 🌙'),
    }
    
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2)
    
    print(f"Status updated: {'online' if online else 'offline'}")

def get_status():
    """Get current status."""
    if STATUS_FILE.exists():
        with open(STATUS_FILE) as f:
            return json.load(f)
    return {'online': False, 'timestamp': None, 'message': 'Unknown'}

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        status = get_status()
        print(f"Status: {'🟢 Online' if status['online'] else '🔴 Offline'}")
        print(f"Since: {status['timestamp']}")
        print(f"Message: {status['message']}")
    elif sys.argv[1] == 'online':
        msg = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
        update_status(True, msg)
    elif sys.argv[1] == 'offline':
        msg = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
        update_status(False, msg)
    else:
        print("Usage: update_status.py [online|offline] [message]")
