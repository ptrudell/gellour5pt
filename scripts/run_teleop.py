#!/usr/bin/env python3
"""
Unified teleop launcher - wraps streamdeck_pedal_watch.py

Usage (typical):
  python run_teleop.py

Direct passthrough to streamdeck_pedal_watch:
  python run_teleop.py -- --ur-left 192.168.1.211 --ur-right 192.168.1.210

All arguments after '--' are passed directly to streamdeck_pedal_watch.py
"""

import sys
from pathlib import Path


def main():
    """Forward all arguments to streamdeck_pedal_watch.py"""
    # Find the target script with robust fallback
    here = Path(__file__).resolve().parent

    # Try different paths where streamdeck_pedal_watch.py might be
    candidates = [
        here / "streamdeck_pedal_watch.py",  # Primary version
        here / "streamdeck_pedal_watch_work.py",  # Fallback to work version if needed
    ]

    target_script = None
    for candidate in candidates:
        if candidate.exists():
            target_script = candidate
            break

    if not target_script:
        print("[error] Could not find streamdeck_pedal_watch.py in any of:")
        for c in candidates:
            print(f"  - {c}")
        return 1

    # Import and run the main function directly from the file
    import importlib.util

    spec = importlib.util.spec_from_file_location("streamdeck_pedal_watch", target_script)
    if not spec or not spec.loader:
        print(f"[error] Failed to load {target_script}")
        return 1
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    watch_main = mod.main  # type: ignore

    # Pass through all command line args (excluding script name)
    return watch_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
