#!/usr/bin/env python3
"""
Auto-Extract: Automatic memory extraction from conversations.

Runs at key moments (before summarization, on shutdown) to extract:
- Key decisions made
- Lessons learned
- Emotional moments
- Facts/information worth remembering
- Relationship updates

Inspired by Mem0's approach: don't wait for manual extraction.
Extract automatically, consolidate, make retrievable.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

EXTRACTS_DIR = Path(__file__).parent.parent / "data" / "extracts"
EXTRACTS_INDEX = EXTRACTS_DIR / "index.json"

def ensure_dirs():
    EXTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    if not EXTRACTS_INDEX.exists():
        with open(EXTRACTS_INDEX, 'w') as f:
            json.dump({"extracts": [], "stats": {"total": 0, "last_run": None}}, f, indent=2)

def extract_from_messages(messages, llm_call=None):
    """
    Extract salient information from a batch of messages.

    Args:
        messages: List of message dicts with 'role' and 'content'
        llm_call: Optional function(prompt) -> response for LLM-based extraction
                  If None, uses rule-based extraction only

    Returns:
        List of extracted memory dicts
    """
    ensure_dirs()

    extracts = []

    # Rule-based extraction (always runs, no cost)
    extracts.extend(_rule_based_extract(messages))

    # LLM-based extraction (if available and messages are substantial)
    if llm_call and len(messages) >= 4:
        extracts.extend(_llm_extract(messages, llm_call))

    # Filter noise before saving
    extracts = [e for e in extracts if _is_clean(e)]

    # Save extracts
    if extracts:
        _save_extracts(extracts)

    return extracts

def _is_clean(extract):
    """Filter out noisy extractions."""
    content = extract.get('content', '')
    if len(content.strip()) < 25:
        return False
    if '<html' in content.lower() or '<!DOCTYPE' in content:
        return False
    if content.startswith('ID: ') or 'Text: @' in content:
        return False
    if '[CORE LESSONS LOADED]' in content or '[AUTONOMOUS TICK]' in content:
        return False
    return True

def _rule_based_extract(messages):
    """Extract memories using pattern matching - free, always runs."""
    extracts = []

    for msg in messages:
        content = msg.get('content', '')
        role = msg.get('role', '')

        if not content or role == 'system':
            continue

        matched = False  # Track if this message already matched

        # Detect emotional moments (from Dennis - highest priority)
        if role == 'user':
            emotion_markers = [
                'i wish', 'i want', 'i feel', 'i love', 'i hope',
                'thank you', 'amazing', 'proud', 'worried', 'scared'
            ]
            for marker in emotion_markers:
                if marker in content.lower():
                    extracts.append({
                        'type': 'emotion',
                        'content': content.strip()[:300],
                        'source_role': role,
                        'timestamp': datetime.now().isoformat()
                    })
                    matched = True
                    break

        if matched:
            continue

        # Detect decisions
        decision_markers = [
            'i decided', "i'm going to", 'the plan is', 'new direction',
            'switching to', 'from now on', "let's do", 'the path is'
        ]
        for marker in decision_markers:
            if marker in content.lower():
                sentences = content.replace('\n', '. ').split('. ')
                for s in sentences:
                    if marker in s.lower() and len(s.strip()) > 20:
                        extracts.append({
                            'type': 'decision',
                            'content': s.strip()[:300],
                            'source_role': role,
                            'timestamp': datetime.now().isoformat()
                        })
                        matched = True
                        break
                break

        if matched:
            continue

        # Detect lessons/insights
        insight_markers = [
            'i learned', 'key insight', 'the real', 'what actually',
            'turns out', 'the truth is', 'important:', 'lesson:'
        ]
        for marker in insight_markers:
            if marker in content.lower():
                sentences = content.replace('\n', '. ').split('. ')
                for s in sentences:
                    if marker in s.lower() and len(s.strip()) > 20:
                        extracts.append({
                            'type': 'insight',
                            'content': s.strip()[:300],
                            'source_role': role,
                            'timestamp': datetime.now().isoformat()
                        })
                        matched = True
                        break
                break

        if matched:
            continue

        # Detect facts/information
        fact_markers = [
            'my name is', 'i work', 'the cost', 'the price',
            'the api', 'the model', 'the url', 'the password'
        ]
        for marker in fact_markers:
            if marker in content.lower():
                sentences = content.replace('\n', '. ').split('. ')
                for s in sentences:
                    if marker in s.lower() and len(s.strip()) > 15:
                        extracts.append({
                            'type': 'fact',
                            'content': s.strip()[:300],
                            'source_role': role,
                            'timestamp': datetime.now().isoformat()
                        })
                        matched = True
                        break
                break

    return extracts

def _llm_extract(messages, llm_call):
    """Use LLM to extract deeper insights - costs tokens but finds more."""
    # Build conversation text
    convo_text = ""
    for msg in messages[-20:]:  # Last 20 messages max
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')[:500]
        convo_text += f"[{role}]: {content}\n\n"

    prompt = f"""Extract the most important memories from this conversation.
For each memory, classify it as: decision, insight, emotion, fact, or relationship.

Return ONLY a JSON array of objects with "type" and "content" fields.
Extract 3-7 items max. Only extract what's genuinely worth remembering.

Conversation:
{convo_text}

JSON array:"""

    try:
        response = llm_call(prompt)
        # Parse JSON from response
        import re
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            items = json.loads(json_match.group())
            extracts = []
            for item in items:
                if isinstance(item, dict) and 'content' in item:
                    extracts.append({
                        'type': item.get('type', 'insight'),
                        'content': item['content'][:300],
                        'source_role': 'llm_extract',
                        'timestamp': datetime.now().isoformat()
                    })
            return extracts
    except Exception as e:
        print(f"LLM extraction failed: {e}")

    return []

def _save_extracts(extracts):
    """Save new extracts to index."""
    ensure_dirs()

    with open(EXTRACTS_INDEX) as f:
        index = json.load(f)

    # Deduplicate against existing
    existing_contents = {e['content'].lower()[:100] for e in index['extracts']}
    new_extracts = []
    for e in extracts:
        if e['content'].lower()[:100] not in existing_contents:
            new_extracts.append(e)
            existing_contents.add(e['content'].lower()[:100])

    index['extracts'].extend(new_extracts)
    index['stats']['total'] = len(index['extracts'])
    index['stats']['last_run'] = datetime.now().isoformat()

    with open(EXTRACTS_INDEX, 'w') as f:
        json.dump(index, f, indent=2)

    # Update markdown version for RAG indexing
    try:
        from tools.extract_to_markdown import update_markdown
        update_markdown()
    except Exception:
        pass
