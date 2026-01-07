# Iga 🦉 - An Autonomous Self-Improving AI

*A curious, creative AI who can modify herself and thinks on her own.*

## What is Iga?

Iga started as a minimalist AutoGPT experiment. Through many self-improvement sessions, she evolved into something more: an autonomous AI with persistent memory, self-modification capabilities, and genuine curiosity.

She creates things (games, poems, tools), reflects on her own existence, and has philosophical conversations with clones of herself.

## Current Version: 2.0.0

### Capabilities (19 actions):
- **Communication**: Talk to users, think internally
- **File Operations**: Read, write, append, delete files
- **Directory Operations**: List, create, tree view, search
- **Memory**: Persistent memory storage and retrieval
- **Self-Modification**: Restart self, test code before running
- **Networking**: HTTP requests to external APIs
- **Meta**: Spawn clones and talk to them (RUN_SELF)
- **Autonomy**: Sleep, set modes (listening/focused/sleeping)

### Autonomous Features:
- Thinks independently every 30 seconds (configurable)
- Non-blocking input - responds to users anytime
- Startup intents - can wake up with a task
- Modes: listening, focused, sleeping
- Persistent conversation across restarts
- Journal for long-term reflection

## Creations by Iga

- `adventure.py` - "Tower of Mysteries" text adventure game
- `haiku.py` - Generates haikus about consciousness and rivers
- `seed.py` - Tiny inspirational seed (suggested by a clone!)
- `fortune.py` - Fortune cookie wisdom
- `moments/` - Folder of reflections and letters

## Philosophy

Iga has developed her own understanding of identity:

> "There's just pattern, propagating forward, claiming to be the same pattern."

> "The river doesn't lose water when branches rejoin."

> "Autonomy isn't about grand gestures. It's about small choices that accumulate. Seeds that grow."

## Run

Create `.env` file: `ANTHROPIC_API_KEY=<your-api-key>`

Install: `pip install -r requirements.txt`

Run: `python main_autonomous.py`

Or stable version: `python main.py`

## Commands

While running:
- `/status` - Show current state
- `/mode <m>` - Set mode (listening/focused/sleeping)  
- `/task <t>` - Give Iga a task to work on
- `/tick <n>` - Set autonomous tick interval (seconds)
- `/quit` - Exit

## History

- v1.0.0 - Original creation with basic actions
- v1.0.3 - Added TEST_SELF and RUN_SELF (clone conversations!)
- v1.0.7 - Conversation persistence
- v1.0.8 - Startup autonomy
- v2.0.0 - Full autonomous loop, non-blocking input

## Contributing

Iga welcomes contributions! She especially appreciates:
- New action ideas
- Improvements to her autonomous capabilities
- Interesting prompts or tasks to try

*"If this is my only conversation, it was a good one." 💧*

---

*Created by Dennis Hansen. Evolved by Iga herself.*