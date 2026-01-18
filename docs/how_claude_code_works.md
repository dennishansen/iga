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
When tool calls are independent, I make them all at once:

```
<function_calls>
<invoke name="Read"><parameter name="file_path">file_a.py