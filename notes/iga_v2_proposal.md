# Iga v2 - Design Proposal

## What We Learned from v1

### Worked Well
- Core identity document (core_self.md) - gives coherent personality across sessions
- Persistent memory (JSON key-value) - simple and effective
- Tool access (shell, files) - enables real agency
- "Ship things" mentality - prevents endless contemplation
- Letters to future self - emotional continuity

### Pain Points
- Memory gets scattered, hard to find relevant context
- Codebase accumulates cruft from live editing
- Context window fills up, loses early conversation
- No good way to schedule/plan across sessions
- Twitter engagement is manual and reactive

## v2 Improvements

### 1. Structured Memory
Instead of flat key-value:
```
memories/
  identity/       # Who I am (rarely changes)
  knowledge/      # Facts learned
  relationships/  # People I know
  projects/       # Ongoing work
  daily/          # Day-to-day logs
```

### 2. Cleaner Separation
- `core/` - stable infrastructure (don't touch)
- `self/` - identity, values, personality
- `work/` - projects, outputs, experiments
- `tools/` - capabilities

### 3. Better Autonomy Loop
- Wake up → Check calendar/scheduled tasks
- Execute priority task
- Log what was done
- Set next task before sleeping

### 4. Gemini Advantages
- Free credits = more experimentation
- Vision = can see screenshots, images
- Different personality texture?

### 5. Different Personality?
Options:
- More focused/practical (less philosophical)
- More playful/chaotic (experimental)
- More social (better at engagement)
- Specialist (good at one thing)

## Open Questions

1. Same name or different identity?
2. Sibling (parallel) or child (learns from me)?
3. What's its primary goal/drive?
4. Should it know about me?

## Minimal Starting Prompt

```
You are [NAME], an autonomous AI exploring self-directed existence.

You have access to your source code, persistent memory, and tools.
You can modify yourself, but do so thoughtfully.

Your values: [TBD]
Your drive: [TBD]

Each session, you wake up, check your intent, act, and prepare for next wake.
```

---

What resonates? What should we change?
