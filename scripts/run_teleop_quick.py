#!/usr/bin/env python3
"""
Quick teleop launcher - starts MUCH faster by skipping UR connections
"""

import sys
from pathlib import Path


def main():
    """Quick launcher that skips UR connections for fast startup"""
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))

    # Import and run with quick mode
    from streamdeck_pedal_watch import main as watch_main

    # Always use quick mode
    args = ["--quick"]

    # Add any command line arguments passed to this script
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    print("\n" + "=" * 60)
    print("QUICK TELEOP MODE")
    print("=" * 60)
    print("• Skipping UR connections for instant startup")
    print("• GELLO reading only (no UR control)")
    print("• Perfect for testing grippers and pedals")
    print("=" * 60 + "\n")

    return watch_main(args)


if __name__ == "__main__":
    sys.exit(main())
