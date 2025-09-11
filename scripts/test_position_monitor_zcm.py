#!/usr/bin/env python3
"""
Test the PositionMonitor class directly to verify ZCM publishing.
"""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the PositionMonitor from streamdeck_pedal_watch
from scripts.streamdeck_pedal_watch import PositionMonitor


def main():
    print("=" * 60)
    print("POSITION MONITOR ZCM TEST")
    print("=" * 60)

    print("\nCreating PositionMonitor with no robots (will use simulated data)...")

    # Create monitor with no robots - should trigger simulated data
    monitor = PositionMonitor(
        left_robot=None, right_robot=None, rate_hz=10.0, publish_zcm=True
    )

    print("Starting monitor...")
    monitor.start()

    print("\nMonitor is running and should be publishing simulated data.")
    print("In another terminal, run:")
    print("  python scripts/receive_gello_both.py")
    print("\nPress Ctrl+C to stop\n")

    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        monitor.stop()
        print("Done!")


if __name__ == "__main__":
    main()
