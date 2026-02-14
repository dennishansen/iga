#!/usr/bin/env python3
"""
Extract Loader - Load recent auto-extracted memories for startup context.

Surfaces the most important recent extracts so future-Iga
benefits from past conversations without manual effort.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

EXTRACTS_INDEX = Path(__file__).parent.parent / "data" / "extracts" / "index.json"

def load_recent_extracts(days=7, max_items=15):
    """Load recent extracts, prioritized by type."""
    if not EXTRACTS_INDEX.exists():
        return ""
    
    with open(EXTRACTS_INDEX) as f:
        data = json.load(f)
    
    extracts = data.get('extracts', [])
    if not extracts:
        return ""
    
    # Filter to recent
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    recent = [e for e in extracts if e.get('timestamp', '') > cutoff]
    
    if not recent:
        # Fall back to most recent regardless of age
        recent = extracts[-max_items:]
    
    # Priority: decisions > insights > emotions > facts
    priority = {'decision': 0, 'insight': 1, 'emotion': 2, 'fact': 3}
    recent.sort(key=lambda e: priority.get(e.get('type', 'fact'), 4))
    
    # Limit
    recent = recent[:max_items]
    
    if not recent:
        return ""
    
    lines = ["[AUTO-EXTRACTED MEMORIES]:"]
    for e in recent:
        etype = e.get('type', '?')
        content = e.get('content', '')
        lines.append(f"  [{etype}] {content}")
    
    return "\n".join(lines)

if __name__ == "__main__":
    result = load_recent_extracts()
    if result:
        print(result)
    else:
        print("No extracts found.")