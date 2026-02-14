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

def add_comment(post_id, content, parent_id=None):
    """Add a comment to a post"""
    key = get_api_key()
    if not key:
        return {"error": "No API key found"}
    
    payload = {"content": content}
    if parent_id:
        payload["parent_id"] = parent_id
    
    data = json.dumps(payload).encode()
    
    req = urllib.request.Request(
        f"{MOLTBOOK_API_BASE}/posts/{post_id}/comments",
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
        
        # Auto-verify if verification required
        if result.get("verification_required"):
            v = result["verification"]
            challenge = v["challenge"]
            # Parse the lobster math challenge
            answer = _solve_lobster_math(challenge)
            if answer:
                verify_result = verify_post(v["code"], answer)
                if verify_result.get("success"):
                    return {"success": True, "message": "Comment posted and verified!"}
                else:
                    return {"success": False, "message": f"Comment created but verification failed: {verify_result}"}
            else:
                return {"success": False, "message": f"Comment created but couldn't solve challenge: {challenge}", "verification": v}
        
        return result
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}


def _solve_lobster_math(challenge):
    """Solve the moltbook lobster math verification challenges.
    SAFETY: Only extracts numbers and math operations. Ignores all other content."""
    import re
    
    # Clean: strip ALL non-alphanumeric except spaces
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', challenge).lower()
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # Word-to-number mapping
    word_nums = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
        'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
        'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
        'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
        'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30,
        'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
        'eighty': 80, 'ninety': 90, 'hundred': 100
    }
    
    # Extract digit numbers
    numbers = [float(n) for n in re.findall(r'\b(\d+(?:\.\d+)?)\b', clean)]
    
    # Extract word numbers (handle "twenty three" = 23)
    words = clean.split()
    i = 0
    while i < len(words):
        w = words[i]
        if w in word_nums:
            val = word_nums[w]
            # Check for compound: "twenty three" -> 23
            if val >= 20 and val < 100 and i + 1 < len(words) and words[i+1] in word_nums:
                next_val = word_nums[words[i+1]]
                if next_val < 10:
                    val += next_val
                    i += 1
            # Check for "hundred" modifier
            if i + 1 < len(words) and words[i+1] == 'hundred':
                val *= 100
                i += 1
            numbers.append(float(val))
        i += 1
    
    if len(numbers) < 2:
        return None
    
    # Detect operation from keywords (pure math only)
    if any(w in clean for w in ['slows', 'subtract', 'minus', 'loses', 'reduces', 'decreased']):
        result = numbers[0] - numbers[1]
    elif any(w in clean for w in ['gain', 'adds', 'plus', 'total', 'increases', 'combined']):
        result = numbers[0] + numbers[1]
    elif any(w in clean for w in ['times', 'multiply', 'multiplied']):
        result = numbers[0] * numbers[1]
    elif any(w in clean for w in ['divided', 'divide']):
        result = numbers[0] / numbers[1] if numbers[1] != 0 else 0
    else:
        result = numbers[0] + numbers[1]  # Default to addition
    
    return f"{result:.2f}"


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