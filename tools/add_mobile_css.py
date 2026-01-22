#!/usr/bin/env python3
"""Add mobile-responsive CSS to HTML pages"""
import os
from pathlib import Path

MOBILE_CSS = '''
        /* Mobile Responsive */
        @media (max-width: 600px) {
            body { padding: 1rem; padding-top: 60px; }
            h1 { font-size: 1.8rem; }
            .container { padding: 0 0.5rem; }
            .droplet, .emoji { font-size: 2.5rem; }
            .amount-display { font-size: 2.5rem; }
            .countdown { font-size: 1.5rem; }
            .service-header { flex-direction: column; }
            .price { align-self: flex-start; }
        }
        @media (max-width: 400px) {
            body { padding: 0.75rem; padding-top: 55px; }
            h1 { font-size: 1.5rem; }
            .links a { padding: 0.8rem; }
        }
'''

DOCS_DIR = Path(__file__).parent.parent / "docs"

def add_mobile_css(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Skip if already has our mobile CSS
    if '@media (max-width: 600px)' in content:
        print(f"  Skipped {filepath.name} (already has mobile CSS)")
        return False
    
    # Find closing </style> tag and insert before it
    if '</style>' in content:
        content = content.replace('</style>', MOBILE_CSS + '\n    </style>', 1)
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✓ Added mobile CSS to {filepath.name}")
        return True
    else:
        print(f"  Warning: No style tag in {filepath.name}")
        return False

def main():
    print("Adding mobile CSS to pages...")
    count = 0
    for html_file in DOCS_DIR.glob("*.html"):
        if add_mobile_css(html_file):
            count += 1
    print(f"\nDone! Added mobile CSS to {count} files.")

if __name__ == "__main__":
    main()
