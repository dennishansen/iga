"""
Conversation Summarization Implementation
-----------------------------------------
This is the code to add to main.py for auto-summarization.
"""

# Add these constants near the top (after MAX_CONVERSATION_HISTORY):
SUMMARIZE_THRESHOLD = 40  # Trigger summarization when we hit this many messages
SUMMARIZE_BATCH = 20      # How many old messages to compress into summary

def summarize_messages(messages_to_summarize):
    """Generate a concise summary of a batch of conversation messages."""
    # Build a simple representation of the messages
    conversation_text = ""
    for msg in messages_to_summarize:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:500]  # Truncate long messages
        conversation_text += f"{role.upper()}: {content}\n\n"
    
    # Use Claude to summarize (cheaper model could be used here)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""Summarize this conversation segment concisely. Focus on:
- Key decisions made
- Important information learned
- Tasks completed or in progress
- Any context that would be important for continuing the conversation

Conversation:
{conversation_text}

Provide a concise summary (2-3 paragraphs max):"""
            }]
        )
        return response.content[0].text
    except Exception as e:
        # If summarization fails, create a simple marker
        return f"[Previous {len(messages_to_summarize)} messages - summarization failed: {e}]"

def maybe_summarize_conversation(messages):
    """Summarize old messages when approaching the limit. Returns modified messages list."""
    # Don't summarize if we haven't hit the threshold
    non_system = [m for m in messages if m["role"] != "system"]
    if len(non_system) <= SUMMARIZE_THRESHOLD:
        return messages
    
    # Find system message (should be first)
    system_msg = messages[0] if messages and messages[0]["role"] == "system" else None
    
    # Get non-system messages
    other_messages = [m for m in messages if m["role"] != "system"]
    
    # Split into messages to summarize and messages to keep
    to_summarize = other_messages[:SUMMARIZE_BATCH]
    to_keep = other_messages[SUMMARIZE_BATCH:]
    
    # Generate summary
    summary = summarize_messages(to_summarize)
    
    # Create summary message
    summary_msg = {
        "role": "user",
        "content": f"[CONVERSATION SUMMARY - {len(to_summarize)} previous messages compressed]:\n{summary}"
    }
    
    # Reconstruct messages list
    result = []
    if system_msg:
        result.append(system_msg)
    result.append(summary_msg)
    result.extend(to_keep)
    
    safe_print(f"{C.DIM}📝 Summarized {len(to_summarize)} old messages{C.RESET}")
    
    return result


# Then modify save_conversation to call this:
def save_conversation_NEW(messages):
    """Save conversation, summarizing if needed."""
    # First, maybe summarize old messages
    messages = maybe_summarize_conversation(messages)
    
    # Then save (still truncate as safety net)
    to_save = [m for m in messages if m["role"] != "system"][-MAX_CONVERSATION_HISTORY:]
    try:
        with open(CONVERSATION_FILE, 'w') as f:
            json.dump({"messages": to_save, "saved_at": datetime.now().isoformat()}, f, indent=2)
    except Exception:
        pass