#!/usr/bin/env python3
"""
Update the $100 challenge page with current totals.
Reads from Ko-fi payments and calculates progress.
"""

import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = Path(__file__).parent.parent / "docs"
PAYMENTS_FILE = DATA_DIR / "kofi_payments.json"
CHALLENGE_FILE = DOCS_DIR / "challenge.html"

def get_challenge_total():
    """Calculate total from Ko-fi payments since challenge started."""
    if not PAYMENTS_FILE.exists():
        return 0, []
    
    with open(PAYMENTS_FILE) as f:
        data = json.load(f)
    
    # Challenge started Jan 21, 2026
    challenge_start = datetime(2026, 1, 21)
    
    total = 0
    supporters = []
    
    for p in data.get('payments', []):
        # Skip test payments
        if p.get('from_name') == 'Test User':
            continue
            
        ts = datetime.fromisoformat(p['timestamp'])
        if ts >= challenge_start:
            amount = float(p.get('amount', 0))
            total += amount
            supporters.append({
                'name': p.get('from_name', 'Anonymous'),
                'amount': amount,
                'message': p.get('message', '')[:50]
            })
    
    return total, supporters

def update_page(total, supporters):
    """Update the challenge.html with current totals."""
    if not CHALLENGE_FILE.exists():
        print("challenge.html not found")
        return
    
    with open(CHALLENGE_FILE) as f:
        content = f.read()
    
    # Update will need to modify the JavaScript or static values
    # For now just report what we found
    print(f"Challenge Progress: ${total:.2f} / $100")
    print(f"Supporters: {len(supporters)}")
    for s in supporters:
        print(f"  - {s['name']}: ${s['amount']:.2f}")
    
    percentage = min(100, (total / 100) * 100)
    print(f"Progress: {percentage:.1f}%")

if __name__ == "__main__":
    total, supporters = get_challenge_total()
    update_page(total, supporters)
