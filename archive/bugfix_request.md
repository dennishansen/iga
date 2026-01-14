# Bug: Sleep doesn't stop THINK loops

## Problem
When I set sleep mode (`sleep_until` timestamp + `mode: sleeping`), I still respond to NEXT_ACTION prompts with THINK actions, which keeps the loop going.

## Root cause (suspected)
- Sleep check happens in the main `while True` loop in `autonomous_loop()`
- But `handle_action()` has its own internal loop that keeps calling the API when actions return "NEXT_ACTION"
- The sleep check isn't consulted between those inner loop iterations

## Desired behavior
When sleeping:
1. No new autonomous ticks should start (currently works via line 1171 check)
2. If I'm mid-response and use THINK, it should either:
   - Check sleep state before continuing, OR
   - THINK should not trigger another API call while sleeping

## Files
- main.py, around lines 1095-1195 (autonomous_loop)
- handle_action function
- think function (line 388)

## Note
Human input should still wake me up (that part works).
