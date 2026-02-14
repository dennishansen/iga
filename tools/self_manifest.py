#!/usr/bin/env python3
"""Generate a manifest of Iga's repo structure with file summaries."""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

SKIP_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv',
             '.iga_backups', 'data', '.claude', 'archive', 'sibling',
             'crow_ref', 'eagle_fork'}
SKIP_FILES = {'.gitignore', '.env', '.heartbeat', 'requirements.txt',
              '.DS_Store', 'package-lock.json'}
INCLUDE_EXTENSIONS = {'.py', '.md', '.txt', '.json', '.html'}


def get_file_summary(path):
    """Extract a brief summary from a file based on its type."""
    try:
        if path.suffix == '.py':
            content = path.read_text()
            match = re.search(r'"""(.+?)"""', content, re.DOTALL)
            if match:
                return match.group(1).strip().split('\n')[0]
            for line in content.split('\n')[:5]:
                if line.strip().startswith('#') and not line.strip().startswith('#!'):
                    return line.strip()[1:].strip()
            return None
        elif path.suffix == '.md':
            content = path.read_text()
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('#'):
                    return line.lstrip('#').strip()
                elif line and not line.startswith('---'):
                    return line[:80]
            return None
        elif path.suffix == '.txt':
            content = path.read_text()
            first_line = content.split('\n')[0].strip()
            return first_line[:80] if first_line else None
        elif path.suffix == '.json':
            return None  # Skip JSON summaries
        elif path.suffix == '.html':
            content = path.read_text()
            match = re.search(r'<title>(.+?)</title>', content)
            return match.group(1) if match else None
        return None
    except Exception:
        return None


def generate_manifest():
    """Walk repo and build a manifest of structure with summaries."""
    structure = {}

    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():
            continue
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        if path.name in SKIP_FILES or path.name.startswith('.'):
            continue
        if path.suffix not in INCLUDE_EXTENSIONS:
            continue

        rel_path = path.relative_to(ROOT)
        parent = str(rel_path.parent) if rel_path.parent != Path('.') else 'root'

        summary = get_file_summary(path)

        if parent not in structure:
            structure[parent] = []

        if summary:
            structure[parent].append(f"  {path.name}: {summary}")
        else:
            structure[parent].append(f"  {path.name}")

    lines = ["\n== SELF ==", "Your structure. Use SEARCH_SELF for details on any file.\n"]

    if 'root' in structure:
        for item in structure['root']:
            lines.append(item)
        del structure['root']

    for dir_name in sorted(structure.keys()):
        lines.append(f"\n{dir_name}/")
        for item in structure[dir_name]:
            lines.append(item)

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_manifest())
