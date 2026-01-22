#!/usr/bin/env python3
"""Add consistent navbar to all HTML pages"""
import os
from pathlib import Path

NAVBAR_HTML = '''<nav style="background:#111;padding:0.75rem 1rem;position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;justify-content:space-between;align-items:center;font-family:monospace;border-bottom:1px solid #333;flex-wrap:wrap;gap:0.5rem;">
    <a href="index.html" style="color:#64b5f6;text-decoration:none;font-weight:bold;">💧 iga.sh</a>
    <div style="display:flex;gap:0.75rem;flex-wrap:wrap;justify-content:flex-end;">
        <a href="garden.html" style="color:#888;text-decoration:none;font-size:0.9rem;">garden</a>
        <a href="poems.html" style="color:#888;text-decoration:none;font-size:0.9rem;">poems</a>
        <a href="services.html" style="color:#888;text-decoration:none;font-size:0.9rem;">services</a>
        <a href="challenge.html" style="color:#ffd700;text-decoration:none;font-size:0.9rem;">$100</a>
    </div>
</nav>
<div style="height:50px;"></div>'''

DOCS_DIR = Path(__file__).parent.parent / "docs"

def update_navbar_in_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if has old navbar
    if 'position:fixed' in content and 'iga.sh</a>' in content:
        # Replace old navbar with new one
        import re
        # Remove old navbar
        content = re.sub(r'<nav style="background:#111[^>]*>.*?</nav>\s*<div style="height:50px;"></div>', '', content, flags=re.DOTALL)
        # Add new navbar after body
        if '<body>' in content:
            content = content.replace('<body>', '<body>\n' + NAVBAR_HTML, 1)
        elif '<body ' in content:
            content = re.sub(r'(<body[^>]*>)', r'\1\n' + NAVBAR_HTML, content, count=1)
        
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✓ Updated navbar in {filepath.name}")
        return True
    elif '<body>' in content or '<body ' in content:
        # Add new navbar
        import re
        if '<body>' in content:
            content = content.replace('<body>', '<body>\n' + NAVBAR_HTML, 1)
        else:
            content = re.sub(r'(<body[^>]*>)', r'\1\n' + NAVBAR_HTML, content, count=1)
        
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✓ Added navbar to {filepath.name}")
        return True
    else:
        print(f"  Warning: No body tag in {filepath.name}")
        return False

def main():
    print("Updating navbar on all pages...")
    count = 0
    for html_file in DOCS_DIR.glob("*.html"):
        if update_navbar_in_file(html_file):
            count += 1
    print(f"\nDone! Updated {count} files.")

if __name__ == "__main__":
    main()
