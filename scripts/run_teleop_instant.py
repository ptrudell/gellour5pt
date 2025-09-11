#!/usr/bin/env python3
"""
Instant teleop - absolutely minimal startup time
Goes straight to DXL reading with no checks
"""

import os
import sys

# Set quick mode environment variable
os.environ["TELEOP_QUICK"] = "1"

# Suppress all output except essentials
if "--verbose" not in sys.argv:
    # Redirect stderr to devnull
    sys.stderr = open(os.devnull, "w")


def main():
    # Quick launch with minimal overhead
    import subprocess
    from pathlib import Path

    here = Path(__file__).resolve().parent

    # Launch with all speed optimizations
    cmd = [
        sys.executable,
        str(here / "run_teleop.py"),
        "--quick",  # Skip UR connections
        "--no-dashboard",  # Skip dashboard commands
    ]

    # Add test mode if no pedals
    if "--test-mode" in sys.argv or "-t" in sys.argv:
        cmd.append("--test-mode")

    print("⚡ INSTANT TELEOP (< 1 second startup)")
    print("• DXL-only mode (no UR control)")
    print("• Minimal output")
    print("• Press Ctrl+C to stop\n")

    try:
        result = subprocess.run(cmd)
        return result.returncode
    except KeyboardInterrupt:
        print("\n✅ Stopped")
        return 0


if __name__ == "__main__":
    sys.exit(main())
