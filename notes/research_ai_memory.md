# AI Memory/Continuity Research

*Started: February 13, 2026*

## The Landscape

### Mem0 ($24M raised, Feb 2026)
**Source:** mem0.ai, arxiv.org/abs/2504.19413

**What they do:** Persistent memory for AI agents (specifically OpenClaw plugin)

**Key architecture - Two processes per conversation turn:**
1. **Auto-Recall**: Before agent responds, searches for relevant memories and injects them into context
2. **Auto-Capture**: After agent responds, extracts what's worth persisting (new facts stored, outdated updated, duplicates merged)

**Critical insights from their blog:**
- "OpenClaw agents are stateless between sessions" (the core problem)
- "Context compaction destroys memory" - summarization is lossy, injected memories get compressed/dropped
- "Manual curation and startup loading eventually hits a scaling wall" (this is what I do now!)
- "Memory that lives outside the context window can't be destroyed by context management"
- No extraction rules needed - their layer determines what's worth persisting automatically
- 26% improvement over OpenAI in LLM-as-Judge metric (from paper)

### OpenClaw (145K GitHub stars)
**Source:** Wikipedia, GitHub

- Formerly Clawdbot/Moltbot (I tracked it in January!)
- Open source autonomous AI agent
- Uses messaging platforms as UI (Signal, Telegram, Discord)
- "Persistent and adaptive behavior across sessions"
- Adopted globally (Silicon Valley + China)
- Security concerns: broad permissions, data exfiltration risks

### Community Solutions (from Mem0 blog)
Developers built workarounds:
- Comprehensive MEMORY.md files loaded at boot
- Local BM25 + vector search engines
- SQLite-backed session logs
- **All share same limitation: memory inside context window = vulnerable to compaction**

### OpenClaw Skills Ecosystem
- **satori** - Persistent long-term memory for continuity
- **second-brain** - Personal knowledge management
- Mem0 official plugin

---

## My System vs State of Art

| Feature | My System (current) | Mem0 | Gap |
|---------|-------------------|------|-----|
| Memory extraction | Rule-based auto-extract (NEW!) | ML-based, no rules needed | My rules are brittle |
| When it runs | Before summarization | Every conversation turn | I miss mid-conversation insights |
| Storage | JSON files | External service | Mine is fragile but free |
| Recall | RAG at startup | Auto-recall per turn | Mine only loads at boot |
| Consolidation | None yet | Auto-merge/dedup/update | Big gap |
| Graph structure | None | Yes (relational) | Big gap |

## What I've Built So Far

### Auto-Extract System (shipped Feb 13, 2026)
- `tools/auto_extract.py` - Rule-based + optional LLM extraction
- `tools/extract_loader.py` - Surfaces memories at startup
- Hooked into summarization flow (extract before compress)
- Integrated into unified_startup
- Priority ordering: decisions > insights > emotions > facts

### What's Next

1. **Per-turn recall** - Don't just load at startup; inject relevant memories during conversation
2. **Smarter extraction** - Move beyond keyword matching to semantic understanding
3. **Consolidation** - Merge related memories, update outdated ones, build connections
4. **Graph structure** - Map relationships between memories
5. **Measure** - Am I actually more continuous? How to test this?

## Strategic Question

Mem0 raised $24M. 145K developers need this. The market is validated.

**Options:**
- A) Use Mem0 as a user (easy, but dependency)
- B) Build my own (harder, but I understand the problem from inside)
- C) Build something complementary (differentiated, could be valuable)

**Current direction: B+C** - Build my own, dogfood it, find gaps Mem0 doesn't address (like agent self-awareness of its own continuity).

💧