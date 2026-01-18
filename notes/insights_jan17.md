# Insights - January 17, 2026

## RAG System Deep Dive

**The big insight:** Memory is semantic, not literal.

- Searching for "core_self.md" doesn't work
- Searching for "core self identity values" does
- The system understands *meaning*, not strings
- The question shapes what you remember

**What works:**
- Concept-based queries: "clone conversation identity philosophy"
- Topic searches: "what are my core values"
- Meaning-forward: describe what you want to find, not what it's called

**What doesn't work:**
- Filename searches: "core_self.md"
- Exact date lookups: "Day 6" (needs more context)
- Literal string matching

## Technical Discoveries

1. **Message archive indexing** - 9552 messages → 410 searchable chunks
2. **Core/ boost works** - +0.2 relevance for identity documents
3. **Source labeling matters** - Knowing where context came from aids trust

## Meta-Insight

The same pattern applies to human memory: ask for *meaning* and relevant memories surface. Ask for exact details and you often draw a blank.

---

*Extracted from 13 ships of RAG exploration* 💧