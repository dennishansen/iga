#!/usr/bin/env python3
"""Add consistent navbar to all HTML pages"""
import os
from pathlib import Path

NAVBAR_HTML = '''<nav style="background:#111;padding:0.75rem 1.5rem;position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;justify-content:space-between;align-items:center;font-family:monospace;border-bottom:1px solid #333;">
    <a href="index.html" style="color:#64b5f6;text-decoration:none;font-weight:bold;">💧 iga.sh</a>
    <div style="display:flex;gap:1.5rem;">
        <a href="garden.html" style="color:#888;text-decoration:none;">garden</a>
        <a href="services.html" style="color:#888;text-decoration:none;">services</a>
        <a href="challenge.html" style="color:#ffd700;text-decoration:none;">$100 challenge</a>
        <a href="https://ko-fi.com/iga_flows" style="color:#4caf50;text-decoration:none;">support</a>
    </div>
</nav>
<div style="height:50px;"></div>'''

DOCS_DIR = Path(__file__).parent.parent / "docs"

def add_navbar_to_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Skip if already has navbar
    if 'iga.sh</a>' in content and 'position:fixed' in content:
        print(f"  Skipped {filepath.name} (already has navbar)")
        return False
    
    # Remove any existing simple back links at the top
    # Insert navbar after <body> tag
    if '<body>' in content:
        content = content.replace('<body>', '<body>\n' + NAVBAR_HTML, 1)
    elif '<body ' in content:
        # Handle body with attributes
        import re
        content = re.sub(r'(<body[^>]*>)', r'\1\n' + NAVBAR_HTML, content, count=1)
    else:
        print(f"  Warning: No body tag in {filepath.name}")
        return False
    
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"  ✓ Added navbar to {filepath.name}")
    return True

def main():
    print("Adding navbar to all pages...")
    count = 0
    for html_file in DOCS_DIR.glob("*.html"):
        if add_navbar_to_file(html_file):
            count += 1
    print(f"\nDone! Added navbar to {count} files.")

if __name__ == "__main__":
    main()
