#!/usr/bin/env python3
"""
Simplified launch manager for teleop system based on GELLO patterns.
Provides easy setup, configuration management, and status monitoring.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict

import yaml


class TeleopManager:
    """Manages teleop system lifecycle."""

    def __init__(self, config_path: str = "configs/teleop_dual_ur5.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.processes: Dict[str, subprocess.Popen] = {}

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            print(f"[warn] Config file not found: {self.config_path}")
            print("[warn] Using default configuration")
            return {}

        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def check_requirements(self) -> bool:
        """Check system requirements."""
        print("\n=== System Requirements Check ===")

        all_good = True

        # Check Python packages
        required_packages = [
            ("yaml", "PyYAML"),
            ("dynamixel_sdk", "dynamixel-sdk"),
            ("hid", "hidapi"),
        ]

        print("\nPython packages:")
        for module, package in required_packages:
            try:
                __import__(module)
                print(f"  ✓ {package}")
            except ImportError:
                print(f"  ✗ {package} - install with: pip install {package}")
                all_good = False

        # Check UR RTDE
        try:
            import rtde_control

            print("  ✓ ur_rtde (or rtde)")
        except ImportError:
            try:
                from ur_rtde import rtde_control

                print("  ✓ ur_rtde")
            except ImportError:
                print("  ✗ ur_rtde - install with: pip install ur_rtde")
                all_good = False

        # Check USB devices
        print("\nUSB devices:")

        # Check for Dynamixel USB adapters
        dxl_found = False
        if Path("/dev/serial/by-id/").exists():
            for device in Path("/dev/serial/by-id/").iterdir():
                if "FTDI" in device.name or "USB" in device.name:
                    print(f"  ✓ Found USB serial: {device.name}")
                    dxl_found = True

        if not dxl_found:
            print("  ⚠ No USB serial devices found (needed for Dynamixel)")

        # Check for StreamDeck pedal
        try:
            result = subprocess.run(
                ["lsusb"], capture_output=True, text=True, check=False
            )
            if "0fd9" in result.stdout.lower() or "elgato" in result.stdout.lower():
                print("  ✓ StreamDeck pedal detected")
            else:
                print("  ⚠ StreamDeck pedal not detected (optional)")
        except Exception:
            print("  ⚠ Could not check USB devices")

        return all_good

    def test_connections(self) -> None:
        """Test robot connections."""
        print("\n=== Connection Tests ===")

        # Test UR connections
        left_host = self.config.get("left_robot", {}).get("ur_host")
        right_host = self.config.get("right_robot", {}).get("ur_host")

        for host, name in [(left_host, "LEFT"), (right_host, "RIGHT")]:
            if host:
                print(f"\n{name} UR ({host}):")
                # Ping test
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "1", host],
                    capture_output=True,
                    check=False,
                )
                if result.returncode == 0:
                    print("  ✓ Network reachable")

                    # Dashboard test
                    try:
                        import socket

                        s = socket.create_connection((host, 29999), timeout=1)
                        s.close()
                        print("  ✓ Dashboard port open")
                    except Exception:
                        print("  ✗ Dashboard port closed")
                else:
                    print("  ✗ Network unreachable")

        # Test Dynamixel (basic)
        print("\nDynamixel test:")
        print("  Run with --dxl-test flag for detailed servo test")

    def create_config_template(self, output_path: str) -> None:
        """Create a config template file."""
        template = {
            "left_robot": {
                "ur_host": "192.168.1.211",
                "ur_program": "/programs/ExternalControl.urp",
                "dxl_port": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT3M9NVB-if00-port0",
                "dxl_ids": [1, 2, 3, 4, 5, 6, 7],
                "dxl_signs": [1, 1, -1, 1, 1, 1, 1],
                "dxl_offsets_deg": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
            "right_robot": {
                "ur_host": "192.168.1.210",
                "ur_program": "/programs/ExternalControl.urp",
                "dxl_port": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT7WBEIA-if00-port0",
                "dxl_ids": [10, 11, 12, 13, 14, 15, 16],
                "dxl_signs": [1, 1, -1, 1, 1, 1, 1],
                "dxl_offsets_deg": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
            "dynamixel": {
                "baudrate": 1000000,
                "protocol": 2.0,
            },
            "control": {
                "hz": 125,
                "velocity_max": 1.4,
                "acceleration_max": 4.0,
            },
        }

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w") as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)

        print(f"Created config template: {output}")

    def run_teleop(self, test_mode: bool = False, dxl_test: bool = False) -> None:
        """Run the teleop system."""
        cmd = [sys.executable, "scripts/run_teleop.py"]

        if self.config_path != Path("configs/teleop_dual_ur5.yaml"):
            cmd.extend(["--config", str(self.config_path)])

        if test_mode:
            cmd.append("--test-mode")

        if dxl_test:
            cmd.append("--dxl-test")

        print(f"\nRunning: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\n[manager] Teleop stopped by user")
        except subprocess.CalledProcessError as e:
            print(f"\n[manager] Teleop exited with error: {e}")

    def interactive_setup(self) -> None:
        """Interactive setup wizard."""
        print("\n=== Teleop Setup Wizard ===")

        # Check for existing config
        if self.config_path.exists():
            print(f"\nFound existing config: {self.config_path}")
            response = input("Use this config? [Y/n]: ").strip().lower()
            if response in ["", "y", "yes"]:
                return

        # Create new config
        print("\nLet's create a new configuration.")

        # Left robot
        print("\n--- LEFT Robot ---")
        left_ur = (
            input("LEFT UR IP address [192.168.1.211]: ").strip() or "192.168.1.211"
        )
        left_dxl = input("LEFT DXL port [auto-detect]: ").strip()

        if not left_dxl:
            # Try to auto-detect
            ports = (
                list(Path("/dev/serial/by-id/").glob("*FTDI*"))
                if Path("/dev/serial/by-id/").exists()
                else []
            )
            if ports:
                print("Found USB serial ports:")
                for i, port in enumerate(ports):
                    print(f"  {i + 1}. {port}")
                choice = input("Select LEFT port [1]: ").strip() or "1"
                try:
                    left_dxl = str(ports[int(choice) - 1])
                except (ValueError, IndexError):
                    left_dxl = "/dev/ttyUSB0"
            else:
                left_dxl = "/dev/ttyUSB0"

        # Right robot
        print("\n--- RIGHT Robot ---")
        use_right = input("Configure RIGHT robot? [y/N]: ").strip().lower()

        if use_right in ["y", "yes"]:
            right_ur = (
                input("RIGHT UR IP address [192.168.1.210]: ").strip()
                or "192.168.1.210"
            )
            right_dxl = (
                input("RIGHT DXL port [/dev/ttyUSB1]: ").strip() or "/dev/ttyUSB1"
            )
        else:
            right_ur = None
            right_dxl = None

        # Create config
        config = {
            "left_robot": {
                "ur_host": left_ur,
                "ur_program": "/programs/ExternalControl.urp",
                "dxl_port": left_dxl,
                "dxl_ids": [1, 2, 3, 4, 5, 6, 7],
                "dxl_signs": [1, 1, -1, 1, 1, 1, 1],
                "dxl_offsets_deg": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            },
            "dynamixel": {
                "baudrate": 1000000,
                "protocol": 2.0,
            },
            "control": {
                "hz": 125,
                "velocity_max": 1.4,
                "acceleration_max": 4.0,
            },
        }

        if right_ur and right_dxl:
            config["right_robot"] = {
                "ur_host": right_ur,
                "ur_program": "/programs/ExternalControl.urp",
                "dxl_port": right_dxl,
                "dxl_ids": [10, 11, 12, 13, 14, 15, 16],
                "dxl_signs": [1, 1, -1, 1, 1, 1, 1],
                "dxl_offsets_deg": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            }

        # Save config
        save_path = input(f"\nSave config as [{self.config_path}]: ").strip() or str(
            self.config_path
        )
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"\n✓ Configuration saved to: {save_path}")
        self.config_path = save_path
        self.config = config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Teleop system manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="configs/teleop_dual_ur5.yaml",
        help="Path to config file",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check system requirements")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test connections")

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Interactive setup wizard")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run teleop system")
    run_parser.add_argument(
        "--test-mode", action="store_true", help="Auto-start without pedals"
    )
    run_parser.add_argument(
        "--dxl-test", action="store_true", help="Test servos and exit"
    )

    # Template command
    template_parser = subparsers.add_parser("template", help="Create config template")
    template_parser.add_argument("output", help="Output file path")

    args = parser.parse_args()

    # Create manager
    manager = TeleopManager(args.config)

    # Handle commands
    if args.command == "check":
        if manager.check_requirements():
            print("\n✓ All requirements satisfied")
        else:
            print("\n✗ Some requirements missing")
            sys.exit(1)

    elif args.command == "test":
        manager.test_connections()

    elif args.command == "setup":
        manager.interactive_setup()

    elif args.command == "run":
        manager.run_teleop(test_mode=args.test_mode, dxl_test=args.dxl_test)

    elif args.command == "template":
        manager.create_config_template(args.output)

    else:
        # Default: show help
        parser.print_help()
        print("\nQuick start:")
        print("  1. Check requirements:  python teleop_manager.py check")
        print("  2. Setup config:        python teleop_manager.py setup")
        print("  3. Test connections:    python teleop_manager.py test")
        print("  4. Run teleop:          python teleop_manager.py run")


if __name__ == "__main__":
    main()
