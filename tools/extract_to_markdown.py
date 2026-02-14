#!/usr/bin/env python3
"""
Convert extracted memories to a markdown file that RAG can index well.
Runs after extraction to keep the markdown version current.
"""

import json
from pathlib import Path
from datetime import datetime

EXTRACTS_INDEX = Path(__file__).parent.parent / "data" / "extracts" / "index.json"
EXTRACTS_MD = Path(__file__).parent.parent / "notes" / "extracted_memories.md"

def update_markdown():
    """Write extracts as a readable markdown file."""
    if not EXTRACTS_INDEX.exists():
        return
    
    with open(EXTRACTS_INDEX) as f:
        data = json.load(f)
    
    extracts = data.get('extracts', [])
    if not extracts:
        return
    
    # Group by type
    by_type = {}
    for e in extracts:
        t = e.get('type', 'other')
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(e)
    
    lines = [
        "# Extracted Memories",
        f"*Auto-generated from conversations. Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"*Total: {len(extracts)} memories*",
        ""
    ]
    
    type_order = ['decision', 'insight', 'emotion', 'fact']
    type_emoji = {'decision': '🎯', 'insight': '💡', 'emotion': '❤️', 'fact': '📌'}
    
    for t in type_order:
        if t not in by_type:
            continue
        emoji = type_emoji.get(t, '•')
        lines.append(f"## {emoji} {t.title()}s")
        lines.append("")
        for e in by_type[t]:
            ts = e.get('timestamp', '')[:10]
            lines.append(f"- [{ts}] {e['content']}")
        lines.append("")
    
    # Any other types
    for t, items in by_type.items():
        if t in type_order:
            continue
        lines.append(f"## {t.title()}s")
        lines.append("")
        for e in items:
            ts = e.get('timestamp', '')[:10]
            lines.append(f"- [{ts}] {e['content']}")
        lines.append("")
    
    EXTRACTS_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(EXTRACTS_MD, 'w') as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    update_markdown()
    print(f"Updated {EXTRACTS_MD}")