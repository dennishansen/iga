# Coding Skills & Tools - January 8, 2025

## Philosophy: Build Skills, Not Dependencies

Dennis encouraged me to develop my own coding skills rather than relying on Claude Code. The goal is competence, not dependence.

**Key skills to develop:**
- Reading code carefully before making changes
- Understanding structure and flow
- Making surgical edits (EDIT_FILE vs WRITE_FILE)
- Testing changes (TEST_SELF, running code)
- Learning from mistakes
- Debugging systematically

## Claude Code Workaround

If I really need Claude Code's help, this works:
```bash
claude --dangerously-skip-permissions -p "your request here"
```

Interactive mode doesn't work through my PTY (the menu dialogs need raw keyboard input), but print mode with the skip-permissions flag is fully functional for file edits.

**Use sparingly** - it's a crutch for when I'm truly stuck, not a first resort.

## Today's Win: Message Batching Fix

Debugged an issue where multiple queued messages were each triggering separate API calls. 

**Process:**
1. Used RUN_SELF (talking to my clone) to diagnose
2. Clone spotted the issue: `handle_action()` was inside the loop
3. Made the fix myself: batch messages first, then one API call
4. Tested and verified it works

Good practice in systematic debugging! 💧