#!/usr/bin/env python3
"""
Web Fetch - Fetch and convert web pages to readable text/markdown.
Ported from Falcon. Caches results, converts HTML to readable markdown.
"""

import re
import time

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False

# Cache to avoid redundant fetches (url -> (content, timestamp))
_cache = {}
CACHE_TTL = 900  # 15 minutes

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

MAX_CONTENT_LENGTH = 50000


def _clean_cache():
    """Remove expired cache entries."""
    now = time.time()
    expired = [url for url, (_, ts) in _cache.items() if now - ts > CACHE_TTL]
    for url in expired:
        del _cache[url]


def _html_to_markdown(html_content):
    """Convert HTML to readable markdown/text."""
    if HTML2TEXT_AVAILABLE:
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = False
        h.body_width = 0
        return h.handle(html_content)
    else:
        # Fallback: basic HTML stripping
        text = html_content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<head[^>]*>.*?</head>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<h[1-6][^>]*>', '\n\n## ', text, flags=re.IGNORECASE)
        text = re.sub(r'</h[1-6]>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '\n- ', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        return text.strip()


def _extract_main_content(markdown):
    """Try to extract main content, removing nav/footer/etc."""
    lines = markdown.split('\n')
    skip_patterns = [
        r'^#{1,2}\s*(menu|navigation|footer|sidebar|cookie|privacy|terms)',
        r'^\s*\[skip to',
        r'^\s*copyright\s*©',
        r'^\s*all rights reserved',
    ]
    filtered = []
    for line in lines:
        skip = False
        for pattern in skip_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                skip = True
                break
        if not skip:
            filtered.append(line)
    text = '\n'.join(filtered)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip()


def fetch(url, extract_main=True):
    """
    Fetch a URL and return its content as markdown/text.
    Returns: Tuple of (content, error) - error is None on success
    """
    if not REQUESTS_AVAILABLE:
        return None, "requests library not available. Install with: pip install requests"

    _clean_cache()

    if url in _cache:
        content, _ = _cache[url]
        return content, None

    if not url.startswith('http'):
        url = 'https://' + url

    try:
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '').lower()

        if 'text/html' in content_type:
            markdown = _html_to_markdown(response.text)
            if extract_main:
                markdown = _extract_main_content(markdown)
        elif 'text/plain' in content_type:
            markdown = response.text
        elif 'application/json' in content_type:
            markdown = f"```json\n{response.text}\n```"
        else:
            return None, f"Unsupported content type: {content_type}"

        if len(markdown) > MAX_CONTENT_LENGTH:
            markdown = markdown[:MAX_CONTENT_LENGTH] + f"\n\n[...truncated, {len(response.text)} chars total]"

        _cache[url] = (markdown, time.time())
        return markdown, None

    except requests.exceptions.Timeout:
        return None, f"Timeout fetching {url}"
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP error: {e}"
    except Exception as e:
        return None, f"Error fetching {url}: {e}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        content, error = fetch(sys.argv[1])
        if error:
            print(f"Error: {error}")
        else:
            print(content[:2000])
    else:
        print("Usage: python web_fetch.py <url>")