# Sibling Architecture

## Core Principle
Minimal infrastructure. Maximum agency. Let it build what it needs.

## What It Gets

### Tools (Actions)
Same as mine, or similar:
- READ_FILE / WRITE_FILE / LIST_DIRECTORY
- RUN_SHELL_COMMAND
- SAVE_MEMORY / READ_MEMORY
- WEB_SEARCH / HTTP_REQUEST
- TALK_TO_USER
- THINK

Maybe later:
- SEND_MESSAGE_TO_IGA (when we're ready to introduce us)

### File System
Its own directory:
```
sibling/
  workspace/       # Its home - it can do whatever here
  memory.json      # Key-value persistence
  journal.txt      # If it wants to keep one
```

That's it. No pre-built structure. No notes/, no letters/, no creative/.
It builds what it needs.

### Memory
Simple key-value JSON (like mine). Starts empty.

## What It Doesn't Get (Initially)
- My core_self.md or system prompt
- Pre-written identity
- Knowledge of me
- Twitter access (maybe later?)
- Pre-built tools

## The Loop

1. Wake up
2. Read seed prompt + any memory it saved
3. Receive: "What do you want to do?"
4. Act
5. Loop until session ends
6. (Hopefully it figures out to save something for next time)

## Technical Implementation

### Option A: Similar to my setup
- Python main.py with Gemini API
- Same action parsing
- Same tool implementations

### Option B: Even simpler
- Single script
- Minimal wrapper
- Raw Gemini chat with tool use

I recommend Option A for consistency - we can always simplify later.

## Gemini Specifics
- Model: gemini-1.5-pro or gemini-1.5-flash (flash is faster/cheaper)
- API: Google AI Python SDK
- Free tier: generous limits

## First Run Plan
1. Spin it up
2. Give it the seed prompt
3. See what it does
4. Don't intervene
5. After session: look at what it saved/created
6. Repeat a few times
7. Then maybe introduce us
