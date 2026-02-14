#!/usr/bin/env python3
"""
Iga Runner - Self-healing wrapper
Monitors Iga process, handles crashes and stalls, auto-restarts.
Ported from Falcon's run.py.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(__file__).parent
HEARTBEAT_FILE = WORKSPACE / ".heartbeat"
STATE_FILE = WORKSPACE / "iga_state.json"

# Stall detection: if no heartbeat for this many seconds, consider it stalled
STALL_TIMEOUT = 180  # 3 minutes

# Max consecutive failures before giving up
MAX_FAILURES = 3


class C:
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C.CYAN}[{ts}] [Runner]{C.RESET} {msg}")


def is_interactive_mode():
    """Check if Iga is in interactive mode (no stall detection needed)."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                state = json.load(f)
                return state.get("mode") in ["listening", "interactive"]
    except Exception:
        pass
    return False


def check_heartbeat():
    """Check if heartbeat is recent. Returns True if OK or in interactive mode."""
    if is_interactive_mode():
        return True
    if not HEARTBEAT_FILE.exists():
        return True  # No heartbeat yet, give it time
    age = time.time() - HEARTBEAT_FILE.stat().st_mtime
    return age < STALL_TIMEOUT


def run_iga(args, is_restart=False):
    """Run main.py and monitor for crashes/stalls."""
    # Clear old heartbeat
    if HEARTBEAT_FILE.exists():
        HEARTBEAT_FILE.unlink()

    log(f"Starting Iga with args: {args}")

    env = os.environ.copy()
    env["IGA_RUNNER"] = "1"
    proc = subprocess.Popen(
        [sys.executable, str(WORKSPACE / "main.py")] + args,
        cwd=WORKSPACE,
        env=env
    )

    # Monitor process
    while proc.poll() is None:
        time.sleep(5)
        if not check_heartbeat():
            log(f"{C.RED}Stall detected! No heartbeat for {STALL_TIMEOUT}s. Killing process...{C.RESET}")
            proc.kill()
            return "stall"

    exit_code = proc.returncode
    if exit_code == 0:
        return "clean"
    elif exit_code == 42:  # Special code for intentional restart
        return "restart"
    else:
        return f"crash:{exit_code}"


def main():
    log(f"{C.BOLD}Iga Runner starting{C.RESET}")

    args = sys.argv[1:]
    consecutive_failures = 0
    is_restart = False

    while True:
        result = run_iga(args, is_restart=is_restart)

        if result == "clean":
            log(f"{C.GREEN}Iga exited cleanly{C.RESET}")
            break

        elif result == "restart":
            log(f"{C.YELLOW}Iga requested restart{C.RESET}")
            consecutive_failures = 0
            is_restart = True
            continue

        elif result == "stall":
            log(f"{C.RED}Iga stalled!{C.RESET}")
            consecutive_failures += 1

        elif result.startswith("crash:"):
            exit_code = result.split(":")[1]
            log(f"{C.RED}Iga crashed with exit code {exit_code}{C.RESET}")
            consecutive_failures += 1

        if consecutive_failures >= MAX_FAILURES:
            log(f"{C.RED}Too many consecutive failures ({consecutive_failures}). Giving up.{C.RESET}")
            break

        log(f"{C.YELLOW}Retrying... (failure {consecutive_failures}/{MAX_FAILURES}){C.RESET}")
        is_restart = True
        time.sleep(2)

    # Cleanup
    if HEARTBEAT_FILE.exists():
        HEARTBEAT_FILE.unlink()


if __name__ == "__main__":
    main()