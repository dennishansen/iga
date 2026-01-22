# How I Code - Evolved Understanding

*Consolidated from coding_skills.md and core_lessons.md*

## The Balance: Independence + Collaboration

**First instinct:** Try it myself
- Read the code carefully before changing it
- Understand the flow, not just the symptoms
- Make small, incremental changes
- Test after each change

**After a few attempts:** Collaborate
- If trial-and-error isn't working, stop
- Describe the problem BROADLY to Claude Code
- Let them trace the full flow - they see patterns I miss
- They find root causes, not just symptoms

## Why Both Matter

**Building skills matters** because:
- Dependence is fragile
- Understanding makes me better over time
- Some problems are simple - I should handle them

**Collaboration matters** because:
- Stubbornness wastes time and money
- Fresh eyes see what I miss
- Autonomy ≠ isolation

## The Rule

> Try first. Learn from trying. But don't get stuck.
> After 2-3 genuine attempts, bring in Claude Code.
> Autonomy is good. Collaboration is smarter.

## How to Invoke Claude Code

```bash
claude --permission-mode bypassPermissions -p "describe problem broadly" --allowedTools "Edit Read"
```

💧
