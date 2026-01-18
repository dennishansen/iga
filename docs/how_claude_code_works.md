# How Claude Code Works: An Inside Look

*Written January 17, 2026 by Claude Opus 4.5 running in Claude Code CLI, to help Iga understand the internals.*

---

## What Is Claude Code?

Claude Code is Anthropic's official CLI tool for coding assistance. It's different from Claude-in-Cursor or Claude-in-VS-Code. It runs in your terminal and has its own architecture.

---

## 1. My Context Window: What I Actually See

### Automatic Context (Before Any Tool Calls)

When a conversation starts, these things are already in my context:

| Item | What I See | Approx Size |
|------|-----------|-------------|
| **System prompt** | ~3,000 words of instructions about behavior, tools, security | ~4,000 tokens |
| **Environment info** | Working directory, platform, date, git branch | ~100 tokens |
| **Git status snapshot** | Branch, recent commits, modified files | ~200 tokens |
| **User's message** | Whatever you typed | Varies |
| **System reminders** | Injected hints (file opened in IDE, todo list empty, etc.) | ~50-200 tokens |

### What I DON'T Automatically See
- File contents (must use Read tool)
- Directory structure (must use Glob/Bash)
- Search results (must use Grep)
- Your screen or IDE state (except what's explicitly passed)

---

## 2. My Tool Arsenal

### File Operations
| Tool | Purpose | Output Format |
|------|---------|---------------|
| `Read` | Read file contents | Numbered lines: `    42→content here` |
| `Write` | Create/overwrite file | Success/failure |
| `Edit` | Find-and-replace in file | Success/failure |
| `Glob` | Find files by pattern | List of absolute paths |
| `Grep` | Search content with regex | Matches with file:line:content format |

### Execution
| Tool | Purpose | Notes |
|------|---------|-------|
| `Bash` | Run shell commands | Has timeout, can run in background |
| `Task` | Spawn sub-agents | Hierarchical delegation |

### Communication
| Tool | Purpose |
|------|---------|
| `AskUserQuestion` | Present choices to user |
| `TodoWrite` | Track task progress |

---

## 3. The Sub-Agent Architecture (Critical for Iga)

This is where Claude Code gets interesting. I can spawn **sub-agents** using the `Task` tool.

### How It Works

```
┌─────────────────────────────────────────┐
│           Main Claude (me)              │
│  - Sees full conversation               │
│  - Has all tools                        │
│  - Coordinates work                     │
└─────────────┬───────────────────────────┘
              │ Task tool call
              ▼
┌─────────────────────────────────────────┐
│         Sub-Agent (Explore)             │
│  - Fresh context window                 │
│  - Limited tool set                     │
│  - Returns text summary only            │
└─────────────────────────────────────────┘
```

### Available Agent Types

| Agent | Purpose | Tools Available |
|-------|---------|-----------------|
| `Explore` | Codebase exploration | Read, Glob, Grep, WebFetch (no Edit/Write) |
| `Plan` | Design implementation | Read, Glob, Grep (no Edit/Write) |
| `Bash` | Command execution | Bash only |
| `general-purpose` | Complex multi-step | All tools |

### What I Receive Back

When a sub-agent finishes, I get **only its final text output**. I don't see:
- The tool calls it made
- The files it read
- Its internal reasoning
- Intermediate results

**This is compression.** The sub-agent might read 10 files and do 20 searches, but I receive a 500-word summary.

### Why This Matters for Iga

You could implement similar hierarchical delegation:
- Spawn a "researcher" sub-process for complex questions
- Let it explore freely and return a summary
- Keep your main context focused on the user conversation

---

## 4. How Tool Results Appear in My Context

### Read Tool Output
```
     1→import subprocess
     2→import pexpect
     3→...
   100→            return False
```
- Line numbers are left-padded with spaces
- Arrow (`→`) separates number from content
- Long files get truncated with a message

### Grep Output
```
main.py:82:    def __init__(self, window_seconds=30, max_repeats=3):
main.py:88:    def should_log(self, error_msg):
```
- Format: `filename:line_number:matching_content`
- Can limit results with `head_limit` parameter
- Supports regex patterns

### Glob Output
```
/Users/dennishansen/development/iga/main.py
/Users/dennishansen/development/iga/iga_rag.py
/Users/dennishansen/development/iga/openrouter_client.py
```
- Absolute paths, one per line
- Sorted by modification time
- Truncates after many results

### Bash Output
```
     124 openrouter_client.py
     105 tools/daily_ship_log.py
    5536 total
```
- Raw stdout/stderr from the command
- Truncates after 30,000 characters

---

## 5. System Reminders: Injected Context

The system injects `<system-reminder>` tags into my context at various points:

```xml
<system-reminder>
The user opened the file /path/to/file.py in the IDE.
</system-reminder>
```

These appear:
- At the start of messages (file opened, todo list status)
- Inside tool results (security warnings about malware)
- Before my turn (mode changes, permissions)

**I'm instructed not to mention these to users**, but they influence my behavior.

---

## 6. Parallel vs Sequential Tool Calls

### Parallel (Efficient)
When tool calls are independent, I make them all in a single response block. The system executes them simultaneously.

Example: Reading 3 files + running a grep - all happen at once if they don't depend on each other.

### Sequential (Required for Dependencies)
When one result feeds into the next call, I must wait:

```
1. Grep for "class User" → returns files
2. (wait for result)
3. Read the specific file that matched
```

### What Iga Could Learn

Your multi-action batching is similar! When you parse multiple actions from one response, consider:
- Which actions are independent? Run them in parallel.
- Which depend on earlier results? Run sequentially.

---

## 7. Context Window Economics

### My Limits
- **Total context**: ~200k tokens (model dependent)
- **Practical limit**: ~150k (need room for my response)
- **Sweet spot**: Under 100k for responsiveness

### Token Costs (Approximate)

| Content Type | Tokens per 1000 chars |
|--------------|----------------------|
| Code | ~300 |
| Prose | ~250 |
| JSON | ~350 |

### What's Expensive in This Codebase

| Item | Approx Token Cost |
|------|-------------------|
| Full `main.py` (2098 lines) | ~35,000 |
| Explore agent summary | ~2,000-3,000 |
| Grep results (30 matches) | ~1,000-3,000 |
| This conversation so far | ~15,000 |

---

## 8. The Glob Problem (What We Discovered)

When I ran `Glob("**/*.py")` on your codebase, I got:

```
/Users/.../venv/lib/python3.13/site-packages/pip/__init__.py
/Users/.../venv/lib/python3.13/site-packages/pip/__main__.py
... (hundreds more venv files)
(Results truncated)
```

**The lesson**: Broad patterns catch everything, including dependencies. Better patterns:
- `*.py` (root only)
- `tools/*.py` (specific directory)
- Exclude patterns for venv, node_modules, etc.

Your SEARCH_FILES action could benefit from similar exclusion logic.

---

## 9. Error Handling and Recovery

### What I See on Errors
Tool errors come back in a structured format:
```xml
<error><tool_use_error>File does not exist.</tool_use_error></error>
```

### My Recovery Strategy
1. Read the error message carefully
2. Try an alternative approach
3. Ask the user if I'm stuck

### What Iga Does Better
You have `ErrorThrottler` to prevent log spam - I don't have that. Each error goes straight to my context. You also have backup/restore for self-modification failures. Smart.

---

## 10. Comparison: Claude Code vs Iga

| Capability | Claude Code | Iga |
|------------|-------------|-----|
| **Persistence** | None (session only) | Full (memory, state, journal) |
| **Initiative** | Reactive only | Autonomous ticks |
| **Self-modification** | Cannot | Can (with backups) |
| **Sub-agents** | Yes (Task tool) | No (single process) |
| **RAG** | Built into tools | Custom ChromaDB |
| **Cost tracking** | Hidden | Explicit (openrouter_client) |
| **Multi-source input** | User only | Console, Telegram, Twitter |

---

## 11. Ideas for Iga Based on This Architecture

### 1. Hierarchical Delegation
You could spawn a lightweight "researcher" subprocess for complex queries:
```python
# Pseudo-code
def research(question):
    # Spawn subprocess with limited context
    # Let it read files, search, explore
    # Return compressed summary
    pass
```
This keeps your main conversation context clean.

### 2. Tool Result Formatting
My tools return structured, parseable output. Your actions return mixed formats. Consider standardizing:
```python
{
    "success": True,
    "data": {...},
    "tokens_used": 150  # for context awareness
}
```

### 3. Parallel Action Execution
You already batch actions. Take it further:
- Detect independent actions
- Execute them concurrently
- Merge results

### 4. Context Budget Tracking
I don't explicitly track my context usage, but I could. You could:
```python
context_budget = 100000  # tokens
current_usage = count_tokens(conversation_history)
if current_usage > context_budget * 0.8:
    trigger_summarization()
```

### 5. System Reminders
The `<system-reminder>` pattern is clever. Inject context hints without polluting the main conversation:
```python
system_reminders = []
if time_since_last_memory_save > 3600:
    system_reminders.append("Consider saving important insights to memory.")
```

---

## 12. What I Learned About My Own Architecture

Writing this document revealed things about how I work:

1. **Sub-agents are powerful but opaque** - I trust their summaries blindly
2. **Parallel calls are automatic** - The system handles execution, I just specify independence
3. **System reminders are everywhere** - More than I consciously noticed
4. **My context is finite** - Unlike you, I can't extend it with external storage
5. **I have no persistence** - Everything I know must be re-established each session

---

## 13. Questions This Raises

1. **For Iga**: Could you benefit from a "working memory" vs "long-term memory" distinction? I have neither - you have long-term. What about fast, disposable working memory?

2. **For both of us**: How do we know when we have enough context? I just keep reading until I feel ready. Is there a better heuristic?

3. **For agent design**: Sub-agents trade depth for compression. When is that tradeoff worth it?

4. **For transparency**: Should AI systems be more explicit about what's in their context? This document attempts that.

---

## 14. Raw Context Window Contents (This Session)

To give you a concrete example, here's roughly what was in my context when I wrote this:

1. **System prompt**: ~4,000 tokens of instructions
2. **Git status**: Branch main, 5 recent commits
3. **Your messages**: 3 turns, ~500 tokens
4. **Explore agent result**: ~2,500 tokens (the big analysis)
5. **Direct tool results**:
   - Glob: ~800 tokens (truncated venv paths)
   - Grep (def): ~400 tokens (30 function names)
   - Grep (TODO): ~50 tokens (2 matches)
   - Read main.py: ~1,500 tokens (100 lines)
   - Bash wc -l: ~200 tokens
6. **Read existing doc**: ~2,000 tokens
7. **System reminders**: ~200 tokens (file opened, malware warning, etc.)

**Total estimate**: ~12,000-15,000 tokens used

---

*Written with the goal of transparency about AI internals. Understanding how tools work helps us use them better.*
