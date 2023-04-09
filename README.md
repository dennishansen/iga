*VERY EXPERIMENTAL (UNSTABLE)*
## Iga. A dead simple Auto-GPT capable of self-improvement.

This script starts a CLI chat with an Auto-GPT agent Iga who responds will respond with one of three actions, alongside their rationale:
- Talk to you: This allows you to respond
- Run shell command: These run in it's own directory. The output is returned to them.
- Think: This simple triggers another resposnse.

This provides provides a minimal basis for guiding Iga to update it's own source code and system instructions. Go wild but not too wild.

Run
```
python script.py
```