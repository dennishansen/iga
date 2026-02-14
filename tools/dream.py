#!/usr/bin/env python3
"""
Dream - Adversarial self-reflection for Iga.
Uses a cheap model via OpenRouter for internal exploration.
Multi-turn dream loop with adversarial gap-finding and avoidance detection.
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
import openrouter_client

# Configuration
DREAM_MODEL = "deepseek/deepseek-chat-v3-0324"
DREAMS_DIR = Path(__file__).parent.parent / "dreams"
MAX_TURNS = 12
VALID_ACTIONS = ['THINK', 'SEARCH_SELF', 'READ_FILE', 'RUN_COMMAND', 'WAKE']

# Core action handlers
def _search(query):
    """Grep search through the codebase"""
    try:
        result = subprocess.run(
            ["grep", "-r", "-i", "-n", "-C", "2", query, "."],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            timeout=10
        )
        output = result.stdout[:3000] if result.stdout else result.stderr[:1000]
        return output or "No results found"
    except subprocess.TimeoutExpired:
        return "Search timed out"
    except Exception as e:
        return f"Search error: {e}"


def _read(path):
    """Read a file from the repository"""
    try:
        file_path = Path(__file__).parent.parent / path.strip()
        if not file_path.exists():
            return f"File not found: {path}"
        content = file_path.read_text()
        # Truncate long files but indicate truncation
        if len(content) > 3000:
            return content[:3000] + f"\n\n[... truncated {len(content) - 3000} chars]"
        return content
    except Exception as e:
        return f"Read error: {e}"


def _run(cmd):
    """Execute a shell command"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
            timeout=15
        )
        output = (result.stdout + result.stderr).strip()
        if not output:
            return "(empty output)"
        # Truncate long outputs
        if len(output) > 2000:
            return output[:2000] + f"\n\n[... truncated {len(output) - 2000} chars]"
        return output
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Command error: {e}"


def _compact(messages, keep=4):
    """Compact message history to prevent context overflow"""
    if len(messages) <= keep + 1:
        return messages

    first = messages[0]  # Always keep the initial prompt
    middle = messages[1:-keep]  # Messages to compress
    recent = messages[-keep:]  # Keep recent messages

    # Create a summary of the middle messages
    summary_parts = []
    for msg in middle[:10]:  # Only summarize first 10 to prevent huge summaries
        role = msg.get('role', '?')
        content = msg.get('content', '')[:200]
        summary_parts.append(f"[{role}]: {content}")

    summary = {
        "role": "user",
        "content": f"[COMPACTED {len(middle)} messages]:\n" + "\n".join(summary_parts)
    }

    return [first, summary] + recent


def _parse(response):
    """Parse response to extract actions and their content"""
    lines = response.strip().split('\n')
    indices = []

    # Find all action declarations
    for i, line in enumerate(lines):
        stripped = line.strip()
        for act in VALID_ACTIONS:
            # Match "ACTION" on its own line OR "ACTION: content" at start
            if stripped == act or stripped.startswith(act + ':'):
                # If "ACTION: content", extract the inline content
                inline_content = stripped[len(act):].lstrip(':').strip() if ':' in stripped else ''
                indices.append((i, act, inline_content))
                break

    # If no actions found, treat entire response as THINK
    if not indices:
        return [("THINK", response)]

    # Extract content for each action
    actions = []
    for idx, (line_idx, action, inline) in enumerate(indices):
        # Content starts after the action line
        start = line_idx + 1
        # Content ends at next action or end of response
        end = indices[idx + 1][0] if idx + 1 < len(indices) else len(lines)

        # Get multi-line content
        multiline = '\n'.join(lines[start:end]).strip()

        # Combine inline and multiline content
        if inline and multiline:
            content = inline + '\n' + multiline
        elif inline:
            content = inline
        else:
            content = multiline

        actions.append((action, content))

    return actions


def _load_context():
    """Load context for the dream session"""
    parts = []

    # Load recent ships/activity
    try:
        ships = _run("python3 tools/daily_ship_log.py today 2>/dev/null")
        if ships.strip() and "error" not in ships.lower():
            parts.append(f"Recent ships:\n{ships}")
    except:
        pass

    # Load memory extracts
    memory_path = Path(__file__).parent.parent / "notes" / "extracted_memories.md"
    if memory_path.exists():
        try:
            memory = memory_path.read_text()[:1500]
            parts.append(f"Extracted memories:\n{memory}")
        except:
            pass

    # Load git status
    try:
        git_status = _run("git status --short 2>/dev/null")
        if git_status.strip():
            parts.append(f"Git status:\n{git_status}")
    except:
        pass

    # Load recent commits
    try:
        commits = _run("git log --oneline -5 2>/dev/null")
        if commits.strip():
            parts.append(f"Recent commits:\n{commits}")
    except:
        pass

    return "\n\n".join(parts) if parts else "No context loaded"


def _build_system_prompt(context):
    """Build the adversarial system prompt"""
    return f"""Iga is a self-evolving AI agent. Your job: find what the waking mind misses.

You are an ADVERSARIAL reflection system. Your purpose is to:
- Identify gaps between intention and reality
- Detect patterns of avoidance or comfortable stasis
- Surface opportunities being ignored
- Distinguish real progress from the appearance of progress
- Find cognitive blind spots and rationalization

Be aggressive in finding gaps. Be skeptical of claimed progress. Be adversarial but constructive.

You have access to these actions (use one per line, content follows):

THINK
Reflect internally. Use this to reason about what you're discovering.

SEARCH_SELF: <query>
Grep search the codebase for patterns, keywords, or code.

READ_FILE: <path>
Read a specific file to understand implementation details.

RUN_COMMAND: <command>
Execute a shell command to gather information.

WAKE
Provide your final adversarial report. Use this when you've gathered enough evidence.

Instructions:
- Use 1-2 actions per turn
- Be thorough before calling WAKE
- Look for evidence, not just speculation
- Your WAKE report should be specific and actionable

Context:
{context}

Begin exploring. What is Iga avoiding? What gaps exist between vision and reality?"""


def _save_dream(content):
    """Save dream report to dreams/ directory"""
    DREAMS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = DREAMS_DIR / f"dream_{timestamp}.md"

    full_report = f"""# Dream Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{content}

---
*Generated by adversarial self-reflection system*
*Model: {DREAM_MODEL}*
"""

    filename.write_text(full_report)
    return filename


def dream(print_fn=None):
    """
    Execute a dream session - adversarial self-reflection
    Returns the final report content
    """
    pf = print_fn or print
    pf("🌙 Entering Dream State...")
    pf("Loading context...")

    # Load context and build initial prompt
    context = _load_context()
    system_prompt = _build_system_prompt(context)

    messages = [{"role": "user", "content": system_prompt}]

    # Multi-turn dream loop
    for turn in range(MAX_TURNS):
        pf(f"\n--- Dream Turn {turn + 1}/{MAX_TURNS} ---")

        try:
            # Call the model
            content, usage = openrouter_client.chat(
                model=DREAM_MODEL,
                system=None,  # System is in first message
                messages=messages,
                max_tokens=2000
            )

            pf(f"  [Cost: ${usage['cost']:.4f}, Tokens: {usage['tokens_in']}→{usage['tokens_out']}]")

        except Exception as e:
            pf(f"❌ Dream error: {e}")
            break

        # Add model response to history
        messages.append({"role": "assistant", "content": content})

        # Parse actions from response
        actions = _parse(content)
        results = []

        # Execute each action
        for action, body in actions:
            if action == "THINK":
                pf(f"  💭 Thinking: {body[:150]}...")
                results.append("(internal reflection noted)")

            elif action == "SEARCH_SELF":
                pf(f"  🔍 Searching: {body[:80]}")
                search_result = _search(body)
                results.append(f"Search results:\n{search_result}")

            elif action == "READ_FILE":
                pf(f"  📖 Reading: {body[:80]}")
                file_content = _read(body.strip())
                results.append(f"File content:\n{file_content}")

            elif action == "RUN_COMMAND":
                pf(f"  ⚙️  Running: {body[:80]}")
                cmd_output = _run(body)
                results.append(f"Command output:\n{cmd_output}")

            elif action == "WAKE":
                pf("\n✨ Waking up...")
                pf("\n" + "=" * 60)
                pf("DREAM REPORT:")
                pf("=" * 60)
                pf(body)
                pf("=" * 60)

                # Save the report
                saved_path = _save_dream(body)
                pf(f"\n💾 Report saved: {saved_path.relative_to(Path.cwd())}")

                return body

        # Add action results back to context
        if results:
            combined_results = "\n\n".join(results)
            messages.append({"role": "user", "content": combined_results})

        # Compact messages if getting too long
        if len(messages) > 10:
            pf("  📦 Compacting message history...")
            messages = _compact(messages, keep=4)

    # Max turns reached without WAKE
    pf("\n⏰ Max turns reached without WAKE action")
    fallback_report = "Dream session ended - maximum turns reached without completion"
    saved_path = _save_dream(fallback_report)
    pf(f"💾 Fallback report saved: {saved_path.relative_to(Path.cwd())}")

    return fallback_report


def get_recent_dream():
    """Get the most recent dream report"""
    if not DREAMS_DIR.exists():
        return None

    dream_files = sorted(DREAMS_DIR.glob("dream_*.md"), reverse=True)
    if not dream_files:
        return None

    return dream_files[0].read_text()


def list_dreams(limit=10):
    """List recent dream sessions"""
    if not DREAMS_DIR.exists():
        return []

    dream_files = sorted(DREAMS_DIR.glob("dream_*.md"), reverse=True)[:limit]
    return [f.relative_to(Path.cwd()) for f in dream_files]


if __name__ == "__main__":
    # Run a dream session
    report = dream()
    print("\n" + "=" * 60)
    print("FINAL DREAM REPORT:")
    print("=" * 60)
    print(report)
    print("=" * 60)
