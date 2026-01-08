"""Test playing my own adventure game with pexpect!"""
import pexpect

child = pexpect.spawn('python3 adventure.py', encoding='utf-8', timeout=10)

# Wait for the intro and first prompt
child.expect('> ')
print("=== GAME STARTED ===")
print(child.before[-500:])  # Last 500 chars before prompt

# Try some commands
commands = ['look', 'take torch', 'north', 'look', 'east', 'look']

for cmd in commands:
    print(f"\n>>> SENDING: {cmd}")
    child.sendline(cmd)
    child.expect('> ')
    print(child.before.strip())

child.sendline('quit')
print("\n=== GAME ENDED ===")
