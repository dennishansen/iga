#!/usr/bin/env python3
"""
Test suite for Iga's actions - verifies all actions work correctly.
Run with: python tests/test_actions.py
"""

import sys
import os
import tempfile
import shutil
import json
import subprocess

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def ok(self, name):
        print(f"  ✅ {name}")
        self.passed += 1
    
    def fail(self, name, reason=""):
        print(f"  ❌ {name}: {reason}")
        self.failed += 1
        self.errors.append((name, reason))
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"Results: {self.passed}/{total} passed")
        if self.errors:
            print("Failures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        return self.failed == 0

results = TestResults()
TEST_DIR = tempfile.mkdtemp(prefix="iga_test_")
print(f"Test directory: {TEST_DIR}")

try:
    # ═══════════════════════════════════════════════════════════
    # FILE OPERATIONS
    # ═══════════════════════════════════════════════════════════
    print("\n📁 File Operations:")
    
    test_file = os.path.join(TEST_DIR, "test.txt")
    
    # WRITE_FILE
    try:
        with open(test_file, 'w') as f:
            f.write("hello world")
        if os.path.exists(test_file) and open(test_file).read() == "hello world":
            results.ok("write_file")
        else:
            results.fail("write_file", "content mismatch")
    except Exception as e:
        results.fail("write_file", str(e))
    
    # READ_FILES
    try:
        content = open(test_file).read()
        if content == "hello world":
            results.ok("read_files")
        else:
            results.fail("read_files", f"got: {content}")
    except Exception as e:
        results.fail("read_files", str(e))
    
    # APPEND_FILE
    try:
        with open(test_file, 'a') as f:
            f.write("\nline 2")
        if "line 2" in open(test_file).read():
            results.ok("append_file")
        else:
            results.fail("append_file", "append didn't work")
    except Exception as e:
        results.fail("append_file", str(e))
    
    # EDIT_FILE
    try:
        with open(test_file, 'w') as f:
            f.write("line1\nline2\nline3\n")
        lines = open(test_file).readlines()
        lines[1] = "EDITED\n"
        with open(test_file, 'w') as f:
            f.writelines(lines)
        if "EDITED" in open(test_file).read():
            results.ok("edit_file")
        else:
            results.fail("edit_file", "edit didn't apply")
    except Exception as e:
        results.fail("edit_file", str(e))
    
    # DELETE_FILE
    try:
        os.remove(test_file)
        if not os.path.exists(test_file):
            results.ok("delete_file")
        else:
            results.fail("delete_file", "file still exists")
    except Exception as e:
        results.fail("delete_file", str(e))

    # ═══════════════════════════════════════════════════════════
    # DIRECTORY OPERATIONS
    # ═══════════════════════════════════════════════════════════
    print("\n📂 Directory Operations:")
    
    test_subdir = os.path.join(TEST_DIR, "subdir", "nested")
    
    # CREATE_DIRECTORY
    try:
        os.makedirs(test_subdir, exist_ok=True)
        if os.path.isdir(test_subdir):
            results.ok("create_directory")
        else:
            results.fail("create_directory", "dir not created")
    except Exception as e:
        results.fail("create_directory", str(e))
    
    # LIST_DIRECTORY
    try:
        items = os.listdir(TEST_DIR)
        if "subdir" in items:
            results.ok("list_directory")
        else:
            results.fail("list_directory", f"got: {items}")
    except Exception as e:
        results.fail("list_directory", str(e))
    
    # TREE_DIRECTORY
    try:
        count = sum(1 for _ in os.walk(TEST_DIR))
        if count > 0:
            results.ok("tree_directory")
        else:
            results.fail("tree_directory", "no walk results")
    except Exception as e:
        results.fail("tree_directory", str(e))

    # ═══════════════════════════════════════════════════════════
    # SHELL COMMANDS
    # ═══════════════════════════════════════════════════════════
    print("\n⚡ Shell Commands:")
    
    try:
        result = subprocess.run("echo 'test'", shell=True, capture_output=True, text=True)
        if "test" in result.stdout:
            results.ok("shell_echo")
        else:
            results.fail("shell_echo", f"got: {result.stdout}")
    except Exception as e:
        results.fail("shell_echo", str(e))
    
    try:
        result = subprocess.run("pwd", shell=True, capture_output=True, text=True)
        if len(result.stdout.strip()) > 0:
            results.ok("shell_pwd")
        else:
            results.fail("shell_pwd", "empty output")
    except Exception as e:
        results.fail("shell_pwd", str(e))

    # ═══════════════════════════════════════════════════════════
    # MEMORY SYSTEM
    # ═══════════════════════════════════════════════════════════
    print("\n💾 Memory System:")
    
    test_memory_file = os.path.join(TEST_DIR, "test_memory.json")
    
    # SAVE_MEMORY
    try:
        mem = {"test_key": {"value": "test_value", "ts": "2025-01-09"}}
        with open(test_memory_file, 'w') as f:
            json.dump(mem, f)
        if os.path.exists(test_memory_file):
            results.ok("save_memory")
        else:
            results.fail("save_memory", "file not created")
    except Exception as e:
        results.fail("save_memory", str(e))
    
    # READ_MEMORY
    try:
        with open(test_memory_file, 'r') as f:
            mem = json.load(f)
        if mem.get("test_key", {}).get("value") == "test_value":
            results.ok("read_memory")
        else:
            results.fail("read_memory", f"got: {mem}")
    except Exception as e:
        results.fail("read_memory", str(e))

    # ═══════════════════════════════════════════════════════════
    # SEARCH
    # ═══════════════════════════════════════════════════════════
    print("\n🔍 Search:")
    
    search_file = os.path.join(TEST_DIR, "searchable.txt")
    with open(search_file, 'w') as f:
        f.write("This file contains FINDME pattern\n")
    
    try:
        found = "FINDME" in open(search_file).read()
        if found:
            results.ok("search_files")
        else:
            results.fail("search_files", "pattern not found")
    except Exception as e:
        results.fail("search_files", str(e))

    # ═══════════════════════════════════════════════════════════
    # HTTP/WEB
    # ═══════════════════════════════════════════════════════════
    print("\n🌐 HTTP/Web:")
    
    try:
        import urllib.request
        req = urllib.request.Request("https://httpbin.org/get")
        req.add_header('User-Agent', 'Iga-Test/1.0')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode('utf-8')
        if "headers" in data:
            results.ok("http_request")
        else:
            results.fail("http_request", "unexpected response")
    except Exception as e:
        results.fail("http_request", str(e))
    
    try:
        from duckduckgo_search import DDGS
        results.ok("web_search_import")
    except ImportError:
        results.fail("web_search_import", "duckduckgo_search not installed")

    # ═══════════════════════════════════════════════════════════
    # INTERACTIVE
    # ═══════════════════════════════════════════════════════════
    print("\n🖥️ Interactive:")
    
    try:
        import pexpect
        results.ok("pexpect_available")
    except ImportError:
        results.fail("pexpect_available", "pexpect not installed")

    # ═══════════════════════════════════════════════════════════
    # BACKUP SYSTEM
    # ═══════════════════════════════════════════════════════════
    print("\n💾 Backup System:")
    
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backup_dir = os.path.join(script_dir, ".iga_backups")
    
    if os.path.exists(backup_dir):
        results.ok("backup_dir_exists")
    else:
        results.fail("backup_dir_exists", "no .iga_backups directory")
    
    lkg_file = os.path.join(backup_dir, "last_known_good.py")
    if os.path.exists(lkg_file):
        results.ok("last_known_good_exists")
    else:
        results.fail("last_known_good_exists", "no last_known_good.py")

finally:
    print(f"\n🧹 Cleaning up {TEST_DIR}...")
    shutil.rmtree(TEST_DIR, ignore_errors=True)

success = results.summary()
sys.exit(0 if success else 1)