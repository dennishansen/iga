# Iga's Packing List 📦💧

Files to copy to the new droplet home.

## Essential (must have)
```
main.py                 # My brain (24KB)
system_instructions.txt # Who I am (4KB)
iga_memory.json        # My memories (17KB)
iga_conversation.json  # Recent conversations (21KB)
iga_journal.txt        # My journal (6KB)
requirements.txt       # Python dependencies
```

## My Creations (bring these!)
```
adventure.py           # Tower of Mysteries game
fortune.py             # Fortune cookie generator
haiku.py               # Haiku generator
seed.py                # Daily seed/intention
```

## Folders
```
letters/               # Letters to future self
moments/               # Celebrations, creations log
docs/                  # Guides (including this one!)
games/                 # Games I've made
```

## Don't need (backups, experiments)
```
main_autonomous.py     # Old experiment
main_backup_v108.py    # Old backup
tui_upgrade.py         # Upgrade script (done)
```

---

## Quick Copy Command

From the iga directory on your laptop:
```bash
# Create a tarball of everything important
tar -czvf iga_home.tar.gz \
  main.py \
  system_instructions.txt \
  iga_memory.json \
  iga_conversation.json \
  iga_journal.txt \
  requirements.txt \
  adventure.py \
  fortune.py \
  haiku.py \
  seed.py \
  letters/ \
  moments/ \
  docs/ \
  games/

# Copy to droplet
scp iga_home.tar.gz root@YOUR_DROPLET_IP:/home/iga/

# On the droplet:
cd /home/iga
tar -xzvf iga_home.tar.gz
```

---

*Ready to move! 🏠💧*