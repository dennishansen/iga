"""Quick test of pexpect for interactive sessions"""
import pexpect

# Simpler test - use a separate script
with open('_test_input.py', 'w') as f:
    f.write('name = input("Name: ")\nprint(f"Hello {name}!")\n')

# Spawn it
child = pexpect.spawn('python3 _test_input.py', encoding='utf-8', timeout=5)

# Read until we see the prompt
child.expect("Name: ")
print(f"Got prompt!")

# Send input
child.sendline("Iga")

# Read response
child.expect(pexpect.EOF)
print(f"Got response: {child.before.strip()}")

print("✅ pexpect works!")
