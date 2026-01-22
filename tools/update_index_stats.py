#!/usr/bin/env python3
"""Update index.html stats dynamically from actual data."""

import json
import os
import re
from glob import glob

INDEX_FILE = "docs/index.html"
GARDEN_FILE = "iga_garden_state.json"

def get_plant_count():
    """Get current plant count from garden."""
    if os.path.exists(GARDEN_FILE):
        with open(GARDEN_FILE) as f:
            garden = json.load(f)
        return len(garden.get("plots", []))
    return 0

def get_page_count():
    """Count HTML pages in docs/."""
    return len(glob("docs/*.html"))

def update_index():
    """Update index.html with current stats."""
    if not os.path.exists(INDEX_FILE):
        print(f"❌ {INDEX_FILE} not found")
        return False
    
    with open(INDEX_FILE, 'r') as f:
        content = f.read()
    
    plants = get_plant_count()
    pages = get_page_count()
    
    # Update plant count
    content = re.sub(
        r'\d+ plants growing',
        f'{plants} plants growing',
        content
    )
    
    # Update page count
    content = re.sub(
        r'\d+ pages built',
        f'{pages} pages built',
        content
    )
    
    with open(INDEX_FILE, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated index.html: {plants} plants, {pages} pages")
    return True

if __name__ == "__main__":
    update_index()
