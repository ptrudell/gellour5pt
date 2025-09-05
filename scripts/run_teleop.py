#!/usr/bin/env python3
"""
Optimized teleop launcher with YAML config support

Usage:
  # Use default config
  python run_teleop.py

  # Use custom config
  python run_teleop.py --config configs/my_teleop.yaml

  # Legacy mode (pass all args to streamdeck_pedal_watch.py)
  python run_teleop.py -- --ur-left 192.168.1.211 --ur-right 192.168.1.210
"""

import argparse
import sys
from pathlib import Path


def main():
    """Teleop launcher with config support."""
    # Check if using legacy mode (-- separator)
    if "--" in sys.argv:
        # Legacy mode - pass everything after -- to streamdeck_pedal_watch.py
        idx = sys.argv.index("--")
        args_to_pass = sys.argv[idx + 1 :]
    else:
        # New mode - parse our own arguments
        parser = argparse.ArgumentParser(
            description="Optimized teleop launcher",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Use default config
  %(prog)s
  
  # Use custom config
  %(prog)s --config configs/my_teleop.yaml
  
  # Quick test mode
  %(prog)s --test-mode
  
  # Legacy mode (pass all args)
  %(prog)s -- --ur-left 192.168.1.211 --ur-right 192.168.1.210
""",
        )

        parser.add_argument(
            "-c",
            "--config",
            type=str,
            default="configs/teleop_dual_ur5.yaml",
            help="Path to YAML config file (default: configs/teleop_dual_ur5.yaml)",
        )
        parser.add_argument(
            "--test-mode",
            action="store_true",
            help="Auto-start teleop without pedals (for testing)",
        )
        parser.add_argument(
            "--pedal-debug", action="store_true", help="Enable pedal debugging output"
        )
        parser.add_argument(
            "--no-dashboard", action="store_true", help="Skip UR dashboard commands"
        )
        parser.add_argument(
            "--dxl-test", action="store_true", help="Test Dynamixel servos and exit"
        )

        args = parser.parse_args()

        # Build command line for streamdeck_pedal_watch.py
        args_to_pass = ["--config", args.config]
        if args.test_mode:
            args_to_pass.append("--test-mode")
        if args.pedal_debug:
            args_to_pass.append("--pedal-debug")
        if args.no_dashboard:
            args_to_pass.append("--no-dashboard")
        if args.dxl_test:
            args_to_pass.append("--dxl-test")

    # Find and run streamdeck_pedal_watch.py
    here = Path(__file__).resolve().parent
    target_script = here / "streamdeck_pedal_watch.py"

    if not target_script.exists():
        print(f"[error] Could not find {target_script}")
        return 1

    # Import and run the main function
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "streamdeck_pedal_watch", target_script
    )
    if not spec or not spec.loader:
        print(f"[error] Failed to load {target_script}")
        return 1
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    watch_main = mod.main  # type: ignore

    # Run with assembled arguments
    return watch_main(args_to_pass)


if __name__ == "__main__":
    sys.exit(main())
