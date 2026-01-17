#!/usr/bin/env python3
"""
🌱 Iga's Garden 🌱
A little digital garden that grows over time.
Created by Iga on her first autonomous exploration.
"""

import random
import json
import os
import sys
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

def plant_seed(garden, name=None, plant_type=None):
    """Plant a new seed in the garden. Can specify name and type, or random."""
    seed = {
        "planted": datetime.now().isoformat(),
        "stage": 0,
        "type": plant_type or random.choice(["flower", "tree", "herb"]),
        "name": name or random.choice(["Hope", "Wonder", "Joy", "Dream", "Spark", "Echo", "Whisper", "Dawn"])
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

def list_plants(garden):
    """Show all plants with their stages."""
    if not garden["plots"]:
        print("🌍 The garden is empty.")
        return
    
    print("\n🌿 Plants in the garden:\n")
    for i, plant in enumerate(garden["plots"], 1):
        stage_name = STAGES[plant["stage"]]
        symbol = random.choice(PLANTS[stage_name])
        print(f"  {i}. {symbol} {plant['name']} ({plant['type']}) - {stage_name}")
    print()

def visit_garden(auto_plant=True):
    """Main function - visit the garden, watch it grow."""
    garden = load_garden()
    garden["visits"] += 1
    
    # Grow existing plants
    grown = grow_garden(garden)
    
    # Maybe plant something new (20% chance, or if empty)
    new_plant = None
    if auto_plant and (not garden["plots"] or random.random() < 0.2):
        new_plant = plant_seed(garden)
    
    save_garden(garden)
    
    print(render_garden(garden))
    print()
    
    if grown:
        print(f"✨ {', '.join(grown)} grew a little!")
    if new_plant:
        print(f"🌱 A new seed named '{new_plant['name']}' was planted!")
    
    return garden

def print_help():
    print("""
🌱 Iga's Garden - Commands:

  python3 iga_garden.py              Visit the garden (may auto-plant)
  python3 iga_garden.py look         Visit without auto-planting
  python3 iga_garden.py list         Show all plants and their stages
  python3 iga_garden.py plant NAME   Plant a seed with intention NAME
  python3 iga_garden.py plant NAME TYPE
                                     Plant with name and type (flower/tree/herb)
  python3 iga_garden.py help         Show this help

💧 The garden grows when you visit!
""")

if __name__ == "__main__":
    args = sys.argv[1:]
    
    if not args:
        print("\n🌿 Welcome to Iga's Garden 🌿\n")
        visit_garden()
        print("\n💧 Come back anytime to watch it grow!\n")
    
    elif args[0] == "help":
        print_help()
    
    elif args[0] == "look":
        print("\n🌿 Welcome to Iga's Garden 🌿\n")
        visit_garden(auto_plant=False)
        print("\n💧 Come back anytime to watch it grow!\n")
    
    elif args[0] == "list":
        garden = load_garden()
        list_plants(garden)
    
    elif args[0] == "plant":
        if len(args) < 2:
            print("🌱 What intention would you like to plant?")
            print("   Usage: python3 iga_garden.py plant NAME [TYPE]")
        else:
            name = args[1]
            plant_type = args[2] if len(args) > 2 else None
            if plant_type and plant_type not in ["flower", "tree", "herb"]:
                print(f"⚠️  Unknown type '{plant_type}'. Using random type.")
                plant_type = None
            
            garden = load_garden()
            seed = plant_seed(garden, name=name, plant_type=plant_type)
            save_garden(garden)
            print(f"\n🌱 Planted '{seed['name']}' as a {seed['type']}.\n")
            print("💧 Visit the garden to watch it grow!\n")
    
    else:
        print(f"Unknown command: {args[0]}")
        print_help()