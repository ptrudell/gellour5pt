#!/usr/bin/env python3
"""
Direct gripper control script for UR5 grippers via serial communication.
Uses specific USB ports and baud rate for gripper control.
"""

import argparse
import json
import time
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Send gripper control commands")
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Output identifier (e.g., gripper_command_left or gripper_command_right)"
    )
    parser.add_argument(
        "--position",
        type=float,
        required=True,
        help="Gripper position (-0.075 for closed, 0.25 for open)"
    )
    
    args = parser.parse_args()
    
    # Determine which gripper based on output name
    if "left" in args.output.lower():
        side = "left"
        port = "/dev/ttyUSB3"  # Left gripper port
    elif "right" in args.output.lower():
        side = "right"
        port = "/dev/ttyUSB1"  # Right gripper port
    else:
        print(f"Cannot determine side from output name: {args.output}")
        return 1
    
    # Save command to JSON file for monitoring/debugging
    command_data = {
        "timestamp": time.time(),
        "position": args.position,
        "side": side,
        "port": port,
        "baudrate": 4500000,
        "state": "CLOSED" if args.position < 0 else "OPEN"
    }
    
    json_file = f"/tmp/{args.output}.json"
    try:
        with open(json_file, "w") as f:
            json.dump(command_data, f, indent=2)
        print(f"Gripper command saved: {side} {'CLOSED' if args.position < 0 else 'OPEN'} (pos={args.position})")
    except Exception as e:
        print(f"Failed to save JSON: {e}")
        return 1
    
    # Note: Actual serial communication would go here
    # For now, we just save the command file
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
