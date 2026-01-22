#!/usr/bin/env python3
"""
Simple SEO checker for iga.sh pages.
Checks for meta tags, titles, descriptions, and basic accessibility.
"""

import os
import re
from pathlib import Path

def check_page(filepath):
    """Check a single HTML page for SEO basics."""
    issues = []
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    filename = os.path.basename(filepath)
    
    # Check title
    title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
    if not title_match:
        issues.append("Missing <title> tag")
    elif len(title_match.group(1)) < 10:
        issues.append(f"Title too short: '{title_match.group(1)}'")
    
    # Check meta description
    desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', content, re.IGNORECASE)
    if not desc_match:
        issues.append("Missing meta description")
    
    # Check viewport (mobile)
    if 'viewport' not in content.lower():
        issues.append("Missing viewport meta (mobile)")
    
    # Check h1
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
    if not h1_match:
        issues.append("Missing <h1> tag")
    
    # Check images for alt tags
    img_matches = re.findall(r'<img[^>]*>', content, re.IGNORECASE)
    for img in img_matches:
        if 'alt=' not in img.lower():
            issues.append(f"Image missing alt tag")
            break
    
    # Check Open Graph tags
    if 'og:title' not in content:
        issues.append("Missing og:title (social sharing)")
    
    return issues

def main():
    docs_dir = Path(__file__).parent.parent / 'docs'
    html_files = list(docs_dir.glob('*.html'))
    
    print(f"Checking {len(html_files)} pages for SEO...\n")
    
    all_good = 0
    needs_work = 0
    
    for filepath in sorted(html_files):
        issues = check_page(filepath)
        if issues:
            needs_work += 1
            print(f"❌ {filepath.name}")
            for issue in issues:
                print(f"   - {issue}")
        else:
            all_good += 1
            print(f"✅ {filepath.name}")
    
    print(f"\n📊 Summary: {all_good} good, {needs_work} need work")

if __name__ == '__main__':
    main()
