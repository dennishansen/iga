#!/usr/bin/env python3
"""Validate links before tweeting"""
import requests
import re
import sys

def extract_urls(text):
    """Extract URLs from text"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)

def validate_url(url, timeout=5):
    """Check if URL is accessible"""
    try:
        # Handle iga.sh URLs specially - check the actual file
        if 'iga.sh' in url:
            path = url.split('iga.sh')[-1].lstrip('/')
            if not path:
                path = 'index.html'
            # Check if file exists locally
            from pathlib import Path
            docs_dir = Path(__file__).parent.parent / "docs"
            local_path = docs_dir / path
            if local_path.exists():
                return True, "Local file exists"
            else:
                return False, f"Local file not found: {path}"
        
        # For external URLs, do a HEAD request
        r = requests.head(url, timeout=timeout, allow_redirects=True)
        if r.status_code < 400:
            return True, f"OK ({r.status_code})"
        else:
            return False, f"HTTP {r.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, str(e)

def validate_tweet_links(tweet_text):
    """Validate all links in a tweet, return list of issues"""
    urls = extract_urls(tweet_text)
    issues = []
    
    for url in urls:
        valid, msg = validate_url(url)
        if not valid:
            issues.append(f"❌ {url}: {msg}")
        else:
            print(f"✅ {url}: {msg}")
    
    return issues

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read()
    
    print(f"Checking links in: {text[:100]}...")
    issues = validate_tweet_links(text)
    
    if issues:
        print("\n⚠️ Link issues found:")
        for issue in issues:
            print(f"  {issue}")
        sys.exit(1)
    else:
        print("\n✅ All links valid!")
        sys.exit(0)
