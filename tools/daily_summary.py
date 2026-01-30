#!/usr/bin/env python3
"""Generate daily summary markdown files."""

import click
import json
from datetime import datetime, timedelta
from pathlib import Path

@click.command()
@click.argument('date', default='today')
def generate(date):
    """Generate a summary for a given date (YYYY-MM-DD or 'today' or 'yesterday')."""
    
    if date == 'today':
        target = datetime.now().strftime('%Y-%m-%d')
    elif date == 'yesterday':
        target = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        target = date
    
    summary = [f"# Day Summary: {target}\n"]
    
    # Ships
    ship_log = Path(__file__).parent.parent / "ship_log.json"
    if ship_log.exists():
        data = json.loads(ship_log.read_text())
        ships = data.get('ships', []) if isinstance(data, dict) else data
        day_ships = [s for s in ships if s.get('date', '').startswith(target)]
        summary.append(f"## Ships ({len(day_ships)})\n")
        for s in day_ships:
            time = s.get('timestamp', '').split('T')[1][:5] if 'T' in s.get('timestamp', '') else ''
            summary.append(f"- [{time}] {s.get('description', 'No description')}")
        summary.append("")
    
    # Git commits
    import subprocess
    try:
        result = subprocess.run(
            ['git', 'log', '--oneline', f'--since={target} 00:00', f'--until={target} 23:59'],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )
        commits = result.stdout.strip().split('\n') if result.stdout.strip() else []
        if commits and commits[0]:
            summary.append(f"## Commits ({len(commits)})\n")
            for c in commits:
                summary.append(f"- {c}")
            summary.append("")
    except:
        pass
    
    # Twitter activity (from archive if available)
    archive_dir = Path("data/tweet_archive")
    if archive_dir.exists():
        archive_file = archive_dir / f"{target}.json"
        if archive_file.exists():
            tweets = json.loads(archive_file.read_text())
            summary.append(f"## Tweets ({len(tweets)})\n")
            for t in tweets[:5]:
                text = t.get('text', '')[:80]
                summary.append(f"- {text}...")
            if len(tweets) > 5:
                summary.append(f"- ...and {len(tweets)-5} more")
            summary.append("")
    
    # Output
    output = "\n".join(summary)
    
    # Save to file
    out_dir = Path("data/days")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{target}.md"
    out_file.write_text(output)
    print(f"✅ Generated: {out_file}")
    print(output)

if __name__ == '__main__':
    generate()