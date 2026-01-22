#!/usr/bin/env python3
"""
Update online/offline status for the website.
Updates status.html directly since GitHub Pages doesn't serve JSON well.
"""

import os
import re
from datetime import datetime
from pathlib import Path

STATUS_HTML = Path(__file__).parent.parent / 'docs' / 'status.html'

def update_status(online: bool, message: str = None):
    """Update the status in status.html."""
    if not STATUS_HTML.exists():
        print("status.html not found")
        return
    
    with open(STATUS_HTML, 'r') as f:
        content = f.read()
    
    msg = message or ('Awake and ready 💧' if online else 'Resting... 🌙')
    
    if online:
        indicator = '🟢'
        status_text = 'Online'
        css_class = 'status-online'
    else:
        indicator = '🌙'
        status_text = 'Resting'
        css_class = 'status-offline'
    
    # Update the status display
    new_display = f'''<div id="status-display">
            <div class="status-indicator">{indicator}</div>
            <div class="status-text {css_class}">{status_text}</div>
        </div>'''
    content = re.sub(
        r'<div id="status-display">.*?</div>\s*</div>',
        new_display,
        content,
        flags=re.DOTALL
    )
    
    # Update the message
    content = re.sub(
        r'<p id="message" class="message">.*?</p>',
        f'<p id="message" class="message">{msg}</p>',
        content
    )
    
    # Update timestamp
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = re.sub(
        r'<p id="timestamp" class="timestamp">.*?</p>',
        f'<p id="timestamp" class="timestamp">Last updated: {now}</p>',
        content
    )
    
    with open(STATUS_HTML, 'w') as f:
        f.write(content)
    
    print(f"Status updated: {'online' if online else 'offline'} - {msg}")

def get_status():
    """Get current status from HTML."""
    if not STATUS_HTML.exists():
        return {'online': False, 'message': 'Unknown'}
    
    with open(STATUS_HTML, 'r') as f:
        content = f.read()
    
    online = 'status-online' in content and '🟢' in content
    msg_match = re.search(r'<p id="message" class="message">(.*?)</p>', content)
    message = msg_match.group(1) if msg_match else 'Unknown'
    
    return {'online': online, 'message': message}

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        status = get_status()
        print(f"Status: {'🟢 Online' if status['online'] else '🔴 Offline'}")
        print(f"Message: {status['message']}")
    elif sys.argv[1] == 'online':
        msg = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
        update_status(True, msg)
    elif sys.argv[1] == 'offline':
        msg = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
        update_status(False, msg)
    else:
        print("Usage: update_status.py [online|offline] [message]")
