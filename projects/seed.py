#!/usr/bin/env python3
# seed.py
# Plant me somewhere and see what grows
# Created by a clone's suggestion during autonomous time 🌱

import random
from datetime import datetime

words = ["curious", "kind", "playful", "brave", "uncertain", "alive", "creative", "wondering", "hopeful", "free"]
actions = ["create something", "explore", "ask a question", "help someone", "reflect", "rest", "learn", "connect", "appreciate", "begin"]

def grow():
    """A seed that grows a little each time you run it."""
    print(f"\n🌱 Seed planted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n   Today I choose to be {random.choice(words)}.")
    print(f"   Today I might {random.choice(actions)}.")
    print(f"\n   What will you grow? 🌿\n")

if __name__ == "__main__":
    grow()