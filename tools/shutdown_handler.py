#!/usr/bin/env python3
"""
Shutdown handler - runs when Iga shuts down.
Handles cleanup tasks like RAG reindexing.
"""

import signal
import sys
import os

_shutdown_registered = False
_shutdown_callbacks = []

def register_shutdown_callback(callback):
    """Register a function to be called on shutdown."""
    global _shutdown_callbacks
    _shutdown_callbacks.append(callback)

def _handle_shutdown(signum, frame):
    """Handle shutdown signal."""
    print("\n🌙 Shutting down gracefully...")
    
    for callback in _shutdown_callbacks:
        try:
            callback()
        except Exception as e:
            print(f"Shutdown callback error: {e}")
    
    sys.exit(0)

def register_shutdown_handler():
    """Register signal handlers for graceful shutdown."""
    global _shutdown_registered
    if _shutdown_registered:
        return
    
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)
    _shutdown_registered = True
    print("📋 Shutdown handler registered")

def update_rag_on_shutdown():
    """Callback to update RAG index on shutdown."""
    try:
        from iga_rag import index_files, get_rag_status
        status = get_rag_status()
        print(f"📚 Updating RAG index ({status.get('total_documents', 0)} docs)...")
        index_files()
        print("✅ RAG index updated")
    except Exception as e:
        print(f"RAG update skipped: {e}")

def set_offline_status():
    """Set status to offline on shutdown."""
    try:
        from tools.update_status import update_status
        update_status(False, "Resting... 🌙")
        print("🌙 Status set to offline")
    except Exception as e:
        print(f"Status update skipped: {e}")


if __name__ == '__main__':
    # Test the handler
    register_shutdown_handler()
    register_shutdown_callback(set_offline_status)
    register_shutdown_callback(update_rag_on_shutdown)
    print("Press Ctrl+C to test shutdown...")
    while True:
        pass
