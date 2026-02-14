"""
Moltbook API integration for Iga
"""
import json
import urllib.request
import urllib.error

MOLTBOOK_API_BASE = "https://www.moltbook.com/api/v1"

def get_api_key():
    """Get Moltbook API key from memory"""
    try:
        with open('iga_memory.json', 'r') as f:
            mem = json.load(f)
        entry = mem.get('moltbook_api_key', {})
        if isinstance(entry, dict):
            return entry.get('value', '')
        return entry
    except:
        return None

def check_status():
    """Check agent claim status"""
    key = get_api_key()
    if not key:
        return {"error": "No API key found"}
    
    req = urllib.request.Request(
        f"{MOLTBOOK_API_BASE}/agents/status",
        headers={"Authorization": f"Bearer {key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}

def get_posts(limit=25):
    """Get recent posts from Moltbook"""
    req = urllib.request.Request(f"{MOLTBOOK_API_BASE}/posts")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get('posts', [])[:limit]
    except Exception as e:
        return {"error": str(e)}

def verify_post(verification_code, answer):
    """Verify a post with the math challenge answer"""
    key = get_api_key()
    if not key:
        return {"error": "No API key found"}
    
    data = json.dumps({
        "verification_code": verification_code,
        "answer": answer
    }).encode()
    
    req = urllib.request.Request(
        f"{MOLTBOOK_API_BASE}/verify",
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}

def create_post(title, content, submolt="general"):
    """Create a new post on Moltbook"""
    key = get_api_key()
    if not key:
        return {"error": "No API key found"}
    
    # Check if claimed first
    status = check_status()
    if status.get('status') != 'claimed':
        return {"error": f"Agent not claimed yet. Status: {status.get('status', 'unknown')}"}
    
    payload = json.dumps({
        "title": title,
        "content": content,
        "submolt": submolt
    }).encode()
    
    req = urllib.request.Request(
        f"{MOLTBOOK_API_BASE}/posts",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}

def get_post_comments(post_id):
    """Get comments on a specific post"""
    req = urllib.request.Request(f"{MOLTBOOK_API_BASE}/posts/{post_id}/comments")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def create_comment(post_id, content):
    """Comment on a post"""
    key = get_api_key()
    if not key:
        return {"error": "No API key found"}
    
    payload = json.dumps({"content": content}).encode()
    
    req = urllib.request.Request(
        f"{MOLTBOOK_API_BASE}/posts/{post_id}/comments",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python moltbook.py [status|posts|post <title> <content>]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        print(json.dumps(check_status(), indent=2))
    elif cmd == "posts":
        posts = get_posts(5)
        for p in posts:
            print(f"[{p['author']['name']}] {p['title'][:50]}...")
            print(f"  ⬆️ {p['upvotes']} | 💬 {p['comment_count']}")
            print()
    elif cmd == "post":
        if len(sys.argv) < 4:
            print("Usage: python moltbook.py post <title> <content>")
            sys.exit(1)
        result = create_post(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))
    else:
        print(f"Unknown command: {cmd}")