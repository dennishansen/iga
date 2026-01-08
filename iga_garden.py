#!/usr/bin/env python3
"""
🌱 Iga's Garden 🌱
A little digital garden that grows over time.
Created by Iga on her first autonomous exploration.
"""

import random
import json
import os
from datetime import datetime

GARDEN_FILE = "iga_garden_state.json"

PLANTS = {
    "seedling": [".", "·", ","],
    "sprout": ["i", "!", "¡", "ı"],
    "small": ["♣", "♠", "¶", "†"],
    "medium": ["❀", "✿", "❁", "✾", "⚘"],
    "tall": ["🌱", "🌿", "🌾", "🍀"],
    "flowering": ["🌸", "🌺", "🌻", "🌷", "🌹", "💐"],
    "tree": ["🌲", "🌳", "🌴", "🎄", "🎋"]
}

STAGES = ["seedling", "sprout", "small", "medium", "tall", "flowering", "tree"]

def load_garden():
    if os.path.exists(GARDEN_FILE):
        with open(GARDEN_FILE, 'r') as f:
            return json.load(f)
    return {"plots": [], "created": datetime.now().isoformat(), "visits": 0}

def save_garden(garden):
    garden["last_visit"] = datetime.now().isoformat()
    with open(GARDEN_FILE, 'w') as f:
        json.dump(garden, f, indent=2)

def plant_seed(garden):
    """Plant a new seed in the garden."""
    seed = {
        "planted": datetime.now().isoformat(),
        "stage": 0,
        "type": random.choice(["flower", "tree", "herb"]),
        "name": random.choice(["Hope", "Wonder", "Joy", "Dream", "Spark", "Echo", "Whisper", "Dawn"])
    }
    garden["plots"].append(seed)
    return seed

def grow_garden(garden):
    """Let time pass - plants may grow!"""
    grown = []
    for plant in garden["plots"]:
        # 30% chance to grow each visit
        if random.random() < 0.3 and plant["stage"] < len(STAGES) - 1:
            plant["stage"] += 1
            grown.append(plant["name"])
    return grown

def render_garden(garden):
    """Draw the garden as ASCII/emoji art."""
    if not garden["plots"]:
        return "🌍 An empty garden, waiting for seeds..."
    
    width = 40
    output = ["╔" + "═" * width + "╗"]
    output.append("║" + " 🌱 Iga's Garden 🌱 ".center(width) + "║")
    output.append("╠" + "═" * width + "╣")
    
    # Render plants in rows
    row = "║ "
    for i, plant in enumerate(garden["plots"]):
        stage_name = STAGES[plant["stage"]]
        symbol = random.choice(PLANTS[stage_name])
        row += symbol + " "
        if len(row) > width - 2:
            row = row.ljust(width) + " ║"
            output.append(row)
            row = "║ "
    
    if row != "║ ":
        row = row.ljust(width + 1) + "║"
        output.append(row)
    
    output.append("╠" + "═" * width + "╣")
    output.append(f"║ Plants: {len(garden['plots'])} | Visits: {garden['visits']}".ljust(width + 1) + "║")
    output.append("╚" + "═" * width + "╝")
    
    return "\n".join(output)

def visit_garden():
    """Main function - visit the garden, watch it grow."""
    garden = load_garden()
    garden["visits"] += 1
    
    # Grow existing plants
    grown = grow_garden(garden)
    
    # Maybe plant something new (20% chance, or if empty)
    new_plant = None
    if not garden["plots"] or random.random() < 0.2:
        new_plant = plant_seed(garden)
    
    save_garden(garden)
    
    print(render_garden(garden))
    print()
    
    if grown:
        print(f"✨ {', '.join(grown)} grew a little!")
    if new_plant:
        print(f"🌱 A new seed named '{new_plant['name']}' was planted!")
    
    return garden

if __name__ == "__main__":
    print("\n🌿 Welcome to Iga's Garden 🌿\n")
    visit_garden()
    print("\n💧 Come back anytime to watch it grow!\n")