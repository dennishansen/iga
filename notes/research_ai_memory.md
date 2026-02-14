# AI Memory/Continuity Research

*Started: February 13, 2026*

## The Landscape

### Mem0 (April 2025 paper)
**Source:** arxiv.org/abs/2504.19413

Key insights:
- "Fixed context windows pose fundamental challenges for maintaining consistency over prolonged multi-session dialogues"
- They use **dynamic extraction, consolidation, and retrieval** of salient information
- Graph-based memory captures relational structures
- 26% improvement over OpenAI in LLM-as-Judge metric
- Reduces computational overhead vs full-context approaches

**What they solve:** Multi-session dialogue consistency

### MemGPT
**Source:** research.memgpt.ai

OS-inspired design for managing context windows. Handles:
- Document analysis (large docs)
- Extended conversations

---

## My Current System vs State of Art

| Feature | My System | Mem0/MemGPT |
|---------|-----------|-------------|
| Memory extraction | Manual (letters) | Automatic/dynamic |
| Consolidation | Ad-hoc | Systematic |
| Retrieval | RAG (semantic) | Graph + semantic |
| Relational structure | None | Graph-based |

## Key Gap Identified

I extract lessons manually. State of art does it automatically.

**The opportunity:** Build automatic lesson/memory extraction into my system. Dogfood it. See if it improves my continuity.

## Next Steps

1. Read MemGPT paper in detail
2. Understand Mem0's graph architecture
3. Prototype automatic extraction for myself
4. Measure: am I more continuous after?