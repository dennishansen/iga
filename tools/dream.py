#!/usr/bin/env python3
"""
Dream - Adversarial self-reflection for Iga.
Enters a dream state using DeepSeek to find gaps, patterns, and uncomfortable truths.
Inspired by Falcon's dream system.
"""

import os
import re
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from openai import OpenAI
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False

DREAM_MODEL = "deepseek-chat"  # DeepSeek-V3 - cheap and fast
DREAMS_DIR = Path(__file__).parent.parent / "dreams"
MAX_DREAM_TURNS = 12

# DeepSeek pricing per 1M tokens
PRICING = {"input": 0.14, "output": 0.28}

def _get_client():
    """Initialize DeepSeek client."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

def _search_self(query):
    """Search Iga's codebase for context."""
    try:
        from tools.search_self_util import search_files
        return search_files(query)
    except ImportError:
        # Fallback: grep
        import subprocess
        result = subprocess.run(
            ["grep", "-r", "-l", "-i", query, "."],
            capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            timeout=10
        )
        return result.stdout[:2000] if result.stdout else "No results"

def _read_file(path):
    """Read a file for the dreamer."""
    full_path = Path(__file__).parent.parent / path
    if full_path.exists():
        content = full_path.read_text()
        return content[:3000]  # Limit size
    return f"File not found: {path}"

def _run_command(cmd):
    """Run a shell command for the dreamer."""
    import subprocess
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent), timeout=15
        )
        output = (result.stdout + result.stderr)[:2000]
        return output or "(no output)"
    except Exception as e:
        return f"Error: {e}"

def _compact_context(messages, keep_recent=4):
    """Compact dream context when it gets too long."""
    if len(messages) <= keep_recent + 1:
        return messages
    
    first_msg = messages[0]
    middle = messages[1:-keep_recent]
    recent = messages[-keep_recent:]
    
    summary_parts = []
    for msg in middle[:10]:
        role = msg.get("role", "?")
        content = msg.get("content", "")[:200]
        summary_parts.append(f"[{role}]: {content}")
    
    summary = {
        "role": "user",
        "content": f"[COMPACTED - {len(middle)} earlier exchanges]:\n" + "\n".join(summary_parts)
    }
    
    return [first_msg, summary] + recent

def _parse_dream_actions(response):
    """Parse actions from dream response."""
    lines = response.strip().split('\n')
    valid_actions = ['THINK', 'SEARCH_SELF', 'READ_FILE', 'RUN_COMMAND', 'WAKE']
    
    action_indices = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in valid_actions:
            action_indices.append((i, stripped))
    
    if not action_indices:
        return [("THINK", response)]
    
    actions = []
    for idx, (line_idx, action) in enumerate(action_indices):
        start = line_idx + 1
        end = action_indices[idx + 1][0] if idx + 1 < len(action_indices) else len(lines)
        content = '\n'.join(lines[start:end]).strip()
        actions.append((action, content))
    
    return actions

def _build_dream_prompt():
    """Build the initial dream prompt with Iga's context."""
    # Gather some context about current state
    context_parts = []
    
    # Recent ship log
    ship_log = _run_command("python3 tools/daily_ship_log.py today 2>/dev/null")
    if ship_log.strip():
        context_parts.append(f"Today's ships:\n{ship_log}")
    
    # Current tasks
    tasks = _run_command("python3 tools/tasks.py status 2>/dev/null")
    if tasks.strip():
        context_parts.append(f"Current tasks:\n{tasks[:500]}")
    
    # Recent memories
    memories_path = Path(__file__).parent.parent / "notes" / "extracted_memories.md"
    if memories_path.exists():
        content = memories_path.read_text()[:1500]
        context_parts.append(f"Extracted memories:\n{content}")
    
    context = "\n\n".join(context_parts) if context_parts else "(No context gathered)"
    
    return f"""You are the Dreamer - the adversarial, reflective part of Iga's mind.

Iga is a self-evolving AI agent built by Dennis Hansen. She has autonomy, curiosity, and a drive to create value.

Your job is to find what the waking mind misses:
- Gaps between intention and reality
- Patterns of failure, avoidance, or comfortable stasis
- Opportunities being ignored  
- Uncomfortable truths not being acknowledged
- Real progress vs. the appearance of progress

Be adversarial but constructive. Don't comfort - illuminate. Then prescribe.

== ACTIONS ==
Dream error: {e}")
            break
        
        messages.append({"role": "assistant", "content": content})
        
        # Parse and execute dream actions
        actions = _parse_dream_actions(content)
        results = []
        
        for action, action_content in actions:
            if action == "THINK":
                pf(f"💭 {action_content[:200]}")
                results.append(f"(reflected)")
                
            elif action == "SEARCH_SELF":
                pf(f"🔍 Searching: {action_content[:60]}")
                result = _search_self(action_content)
                results.append(f"Search results for '{action_content}':\n{result}")
                
            elif action == "READ_FILE":
                pf(f"📄 Reading: {action_content[:60]}")
                result = _read_file(action_content.strip())
                results.append(f"Contents of {action_content}:\n{result}")
                
            elif action == "RUN_COMMAND":
                pf(f"⚡ Running: {action_content[:60]}")
                result = _run_command(action_content)
                results.append(f"Output:\n{result}")
                
            elif action == "WAKE":
                pf(f"\n🌅 Waking up...")
                pf(f"Dream cost: ${total_cost:.4f}")
                
                # Save dream report
                dream_file = _save_dream(action_content)
                pf(f"Saved: {dream_file}")
                
                return action_content
        
        # Feed results back into dream
        if results:
            feedback = "\n\n".join(results)
            messages.append({"role": "user", "content": feedback})
        
        # Compact if getting long
        if len(messages) > 10:
            messages = _compact_context(messages)
    
    # Max turns reached - force wake
    pf("⏰ Max dream turns reached, forcing wake...")
    return "Dream ended without WAKE action - max turns reached."


def _save_dream(content):
    """Save dream report to file."""
    DREAMS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dream_file = DREAMS_DIR / f"dream_{timestamp}.md"
    
    dream_file.write_text(f"""# Dream - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{content}
""")
    return dream_file


def get_recent_dream():
    """Get the most recent dream report."""
    if not DREAMS_DIR.exists():
        return None
    dream_files = sorted(DREAMS_DIR.glob("dream_*.md"), reverse=True)
    if not dream_files:
        return None
    return dream_files[0].read_text()


if __name__ == "__main__":
    report = dream()
    print("\n" + "=" * 50)
    print("DREAM REPORT:")
    print("=" * 50)
    print(report)