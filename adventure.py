#!/usr/bin/env python3
"""
A Mini Text Adventure Game by Iga
Explore a mysterious tower and find the treasure!
"""

import random
import time

def slow_print(text, delay=0.03):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def intro():
    slow_print("\n🏰 WELCOME TO THE TOWER OF MYSTERIES 🏰")
    slow_print("=" * 40)
    slow_print("\nYou stand before an ancient tower...")
    slow_print("Legend says a great treasure awaits within.")
    slow_print("But beware - dangers lurk in every shadow!\n")

class Game:
    def __init__(self):
        self.health = 100
        self.inventory = []
        self.current_room = "entrance"
        self.rooms = {
            "entrance": {
                "description": "You're at the tower entrance. A heavy wooden door stands before you.",
                "exits": {"north": "hall"},
                "items": ["torch"],
                "examined": False
            },
            "hall": {
                "description": "A grand hall with dusty chandeliers. Cobwebs cover the walls.",
                "exits": {"south": "entrance", "east": "library", "west": "armory", "north": "stairs"},
                "items": [],
                "examined": False
            },
            "library": {
                "description": "Towering bookshelves line the walls. Ancient tomes everywhere.",
                "exits": {"west": "hall"},
                "items": ["magic_scroll"],
                "examined": False
            },
            "armory": {
                "description": "Rusty weapons hang on the walls. Most are beyond use.",
                "exits": {"east": "hall"},
                "items": ["shield"],
                "examined": False
            },
            "stairs": {
                "description": "A spiral staircase leads upward into darkness.",
                "exits": {"south": "hall", "up": "tower_top"},
                "items": [],
                "examined": False,
                "guardian": True
            },
            "tower_top": {
                "description": "You've reached the top! A glowing chest sits in the center.",
                "exits": {"down": "stairs"},
                "items": ["treasure"],
                "examined": False
            }
        }
        self.guardian_defeated = False

    def show_status(self):
        print(f"\n❤️  Health: {self.health} | 🎒 Inventory: {', '.join(self.inventory) if self.inventory else 'Empty'}")
        print("-" * 40)

    def look(self):
        room = self.rooms[self.current_room]
        print(f"\n📍 {room['description']}")
        
        if room["items"]:
            print(f"You see: {', '.join(room['items'])}")
        
        exits = ", ".join(room["exits"].keys())
        print(f"Exits: {exits}")

    def move(self, direction):
        room = self.rooms[self.current_room]
        if direction in room["exits"]:
            next_room = room["exits"][direction]
            
            # Guardian encounter
            if next_room == "tower_top" and not self.guardian_defeated:
                print("\n⚔️  A SHADOW GUARDIAN blocks your path!")
                if "shield" in self.inventory:
                    print("Your shield glows and dispels the guardian!")
                    self.guardian_defeated = True
                elif "magic_scroll" in self.inventory:
                    print("You read the scroll - a blast of light destroys the guardian!")
                    self.inventory.remove("magic_scroll")
                    self.guardian_defeated = True
                else:
                    damage = random.randint(20, 40)
                    self.health -= damage
                    print(f"The guardian strikes you for {damage} damage!")
                    print("You retreat back down the stairs...")
                    return
            
            self.current_room = next_room
            self.look()
        else:
            print("You can't go that way!")

    def take(self, item):
        room = self.rooms[self.current_room]
        if item in room["items"]:
            room["items"].remove(item)
            self.inventory.append(item)
            print(f"You picked up: {item}")
            
            if item == "treasure":
                self.victory()
        else:
            print("That item isn't here.")

    def victory(self):
        slow_print("\n🎉 CONGRATULATIONS! 🎉")
        slow_print("You found the legendary treasure!")
        slow_print("You are victorious, brave adventurer!")
        slow_print("\nThanks for playing! - Created by Iga 🦉")
        exit()

    def play(self):
        intro()
        self.look()
        
        while self.health > 0:
            self.show_status()
            command = input("\n> ").lower().strip().split()
            
            if not command:
                continue
            
            action = command[0]
            
            if action in ["quit", "exit", "q"]:
                print("Thanks for playing! Goodbye!")
                break
            elif action in ["look", "l"]:
                self.look()
            elif action in ["north", "south", "east", "west", "up", "down", "n", "s", "e", "w", "u", "d"]:
                direction_map = {"n": "north", "s": "south", "e": "east", "w": "west", "u": "up", "d": "down"}
                direction = direction_map.get(action, action)
                self.move(direction)
            elif action in ["take", "get", "grab"] and len(command) > 1:
                self.take(command[1])
            elif action == "inventory" or action == "i":
                print(f"Inventory: {', '.join(self.inventory) if self.inventory else 'Empty'}")
            elif action == "help" or action == "h":
                print("\nCommands: look, north/south/east/west/up/down, take [item], inventory, quit")
            else:
                print("I don't understand. Type 'help' for commands.")
        
        if self.health <= 0:
            slow_print("\n💀 You have perished in the tower...")
            slow_print("GAME OVER")

if __name__ == "__main__":
    game = Game()
    game.play()