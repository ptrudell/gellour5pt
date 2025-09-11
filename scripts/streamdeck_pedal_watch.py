#!/usr/bin/env python3

"""
Optimized DXL→UR joint teleop using GELLO software patterns.
StreamDeck pedal control with interrupt-first flow and smooth tracking.

Pedal Controls:
- **Left (4)**  → *Interrupt*: stops URs for external program control
- **Center (5)**
    • 1st tap → capture baselines, gentle params, prep/align (no streaming yet)
    • 2nd tap → start teleop streaming (full-speed params)
- **Right (6)** → stop teleop and return to passive

Optimizations based on GELLO software:
- YAML-based configuration
- Fixed-rate scheduler with perf_counter
- Optimized Dynamixel driver with sync read/write
- Smooth motion profiling
- Better error handling and recovery
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
from contextlib import closing
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import yaml

# Try to import ZCM for message publishing
try:
    import zerocm
    from gello_positions_t import gello_positions_t

    ZCM_AVAILABLE = True
except ImportError:
    print(
        "[warn] zerocm not installed or message types not generated, position publishing disabled"
    )
    print("      Install with: pip install zerocm")
    print("      Generate messages with:")
    print("      zcm-gen -p gello_positions_simple.zcm")
    ZCM_AVAILABLE = False

# RTDE imports removed - now handled by separate gello_ur_offset_publisher.py

# Import optimized components
from hardware.control_loop import (
    FixedRateScheduler,
    MotionProfile,
    SmoothMotionController,
)
from hardware.ur_dynamixel_robot import (
    DynamixelDriver,  # DynamixelDriver for testing mode
)

# Import connection clearing utility
try:
    from clear_ur_connections import clear_robots_quietly
except ImportError:
    # Fallback if module not found
    def clear_robots_quietly(hosts: List[str]) -> bool:
        return True


# --- HID imports for pedals ---
try:
    import hid  # type: ignore
except ImportError:
    print("[warn] python-hidapi not installed, pedal control disabled")
    hid = None  # type: ignore


# ---------------- Config Management ----------------
class Config:
    """Configuration container with defaults."""

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        if config_dict is None:
            config_dict = {}

        # Extract sub-configs
        self.left_robot = config_dict.get("left_robot", {})
        self.right_robot = config_dict.get("right_robot", {})
        self.dynamixel = config_dict.get("dynamixel", {})
        self.control = config_dict.get("control", {})
        self.motion_shaping = config_dict.get("motion_shaping", {})
        self.pedal = config_dict.get("pedal", {})
        self.safety = config_dict.get("safety", {})
        self.debug = config_dict.get("debug", {})

        # Control parameters (with env var override)
        self.dt = self.control.get("dt", 0.008)
        self.hz = self.control.get("hz", 125)
        self.lookahead = self.control.get("lookahead", 0.15)
        self.gain = self.control.get("gain", 340)
        self.vmax = float(
            os.environ.get("UR_VMAX", str(self.control.get("velocity_max", 1.4)))
        )
        self.amax = float(
            os.environ.get("UR_AMAX", str(self.control.get("acceleration_max", 4.0)))
        )

        # Gripper configuration
        self.gripper_enabled = self.control.get("gripper_enabled", True)
        self.gripper_threshold = self.control.get(
            "gripper_threshold", 0.5
        )  # For open/close

        # Motion shaping
        self.ema_alpha = self.motion_shaping.get("ema_alpha", 0.12)
        self.softstart_time = self.motion_shaping.get("softstart_time", 0.20)
        self.deadband_deg = self.motion_shaping.get(
            "deadband_deg", [1, 1, 1, 1, 1, 2, 1]
        )
        self.scale = self.motion_shaping.get("scale", [1, 1, 1, 1, 1, 1, 1])
        self.clamp_rad = self.motion_shaping.get(
            "clamp_rad", [None, None, None, None, None, 0.8, None]
        )

        # Convert degrees to radians
        self.deadband_rad = [
            np.radians(d) if d is not None else None for d in self.deadband_deg
        ]

        # Pedal mapping
        button_map = self.pedal.get("button_mapping", {})
        self.pedal_left = button_map.get("left", 4)
        self.pedal_center = button_map.get("center", 5)
        self.pedal_right = button_map.get("right", 6)


# -------------- State Management --------------
class TeleopState(Enum):
    IDLE = "idle"
    PREP = "prep"  # After center-first (baselines captured, ready to align)
    RUNNING = "running"  # After center-second (teleop active)


# -------------- Helpers --------------
def load_config(config_path: Optional[str]) -> Config:
    """Load configuration from YAML file or use defaults."""
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
        print(f"[config] Loaded from {config_path}")
        return Config(config_dict)
    else:
        print("[config] Using default configuration")
        return Config()


def _parse_int_csv(s: str) -> List[int]:
    return [int(x) for x in s.split(",") if x]


def _parse_signs(s: Optional[str], n: int, default: Sequence[int]) -> List[int]:
    if not s:
        return list(default)
    vals = [int(x) for x in s.split(",") if x]
    if len(vals) != n or not all(v in (-1, 1) for v in vals):
        raise ValueError("--*signs must be comma list of ±1 with length matching IDs")
    return vals


def _parse_offsets_deg(
    s: Optional[str], n: int, default: Sequence[float]
) -> List[float]:
    if not s:
        return list(default)
    vals = [float(x) for x in s.split(",") if x]
    if len(vals) != n:
        raise ValueError("--*offsets-deg must match number of IDs")
    return vals


def _dashboard_play(host: str):
    """Kick the UR Dashboard to a known good state and press play."""
    try:
        s = socket.create_connection((host, 29999), timeout=2)
        s.recv(4096)  # Welcome message
        for cmd in [
            "stop",
            "close safety popup",
            "unlock protective stop",
            "power on",
            "brake release",
            "play",
        ]:
            s.send((cmd + "\n").encode())
            s.recv(4096)
        s.close()
        print(f"[dash] {host}: play sequence sent")
    except Exception as e:
        print(f"[dash] {host}: dashboard error: {e}")


def _dashboard_load_play(host: str, program: str) -> None:
    """Load a UR program by name and press play via Dashboard."""
    try:
        s = socket.create_connection((host, 29999), timeout=2)
        s.recv(4096)  # Welcome message
        for cmd in [
            "stop",
            "close safety popup",
            "unlock protective stop",
            "power on",
            "brake release",
            f"load {program}",
            "play",
        ]:
            s.send((cmd + "\n").encode())
            response = s.recv(4096)
            if b"Error" in response or b"File not found" in response:
                print(f"[dash] {host}: WARNING - {response.decode().strip()}")
        s.close()
        print(f"[dash] {host}: load '{program}' + play sent")
    except Exception as e:
        print(f"[dash] {host}: load+play error: {e}")


# --- Enhanced Dashboard helpers (query + program control) ---
def _dash_cmd(host: str, cmd: str, timeout: float = 2.0) -> str:
    """Send a single dashboard command and return response line (stripped)."""
    try:
        s = socket.create_connection((host, 29999), timeout=timeout)
        s.recv(4096)  # welcome
        s.send((cmd + "\n").encode())
        resp = s.recv(4096).decode(errors="ignore").strip()
        s.close()
        return resp
    except Exception as e:
        return f"<dash-error {e}>"


def _dash_exec(host: str, *cmds: str, wait: float = 0.15) -> List[str]:
    """Execute multiple dashboard commands in sequence."""
    out = []
    try:
        with closing(socket.create_connection((host, 29999), timeout=2.0)) as s:
            s.recv(4096)  # banner
            for c in cmds:
                s.sendall((c + "\n").encode())
                time.sleep(wait)
                try:
                    out.append(s.recv(4096).decode(errors="ignore").strip())
                except Exception:
                    out.append("")
    except Exception as e:
        out.append(f"[dash] {host}: error {e}")
    return out


def _dash_get_program_state(host: str) -> str:
    """Query program state - returns e.g. 'STOPPED', 'PLAYING' (normalized upper-case)."""
    resp = _dash_cmd(host, "programState")
    return resp.upper()


def _dash_get_robot_mode(host: str) -> str:
    """Get robot mode - returns mode string."""
    resp = _dash_cmd(host, "robotmode")
    return resp


def _dash_get_safety_mode(host: str) -> str:
    """Get safety mode - returns safety string."""
    resp = _dash_cmd(host, "safetystatus")
    return resp


def _prepare_for_autonomous(host: str, no_dashboard: bool = False) -> bool:
    """Prepare robot for autonomous control by ensuring clean state."""
    if no_dashboard:
        return True

    try:
        # Send minimal commands to ensure robot is ready
        cmds = _dash_exec(host, "stop", "close safety popup", wait=0.1)

        # Check if we got reasonable responses
        for cmd in cmds:
            if "error" in cmd.lower() and "no safety" not in cmd.lower():
                print(f"[autonomous] {host}: Warning - {cmd}")
                return False

        return True
    except Exception as e:
        print(f"[autonomous] {host}: Failed to prepare - {e}")
        return False


def _check_external_control(host: str) -> bool:
    """Check if ExternalControl.urp is PLAYING. Returns True if PLAYING."""
    # Just check status, don't modify anything
    try:
        state_lines = _dash_exec(host, "get loaded program", "programState")
        loaded = "\n".join(state_lines)
        print(f"[dash] {host}: Current state: {loaded}")

        if "PLAYING" in loaded.upper() and (
            "EXTERNAL" in loaded.upper() or "CONTROL" in loaded.upper()
        ):
            print(f"[dash] {host}: ✓ ExternalControl is PLAYING")
            return True
        else:
            print(f"[dash] {host}: ✗ ExternalControl not playing")
            if "freedrive" in loaded.lower():
                print("       Note: freedrive.urp is loaded instead")
            print("       MANUAL ACTION REQUIRED:")
            print("       1. On pendant: File → Load Program → ExternalControl.urp")
            print("       2. Press Play (▶)")
            print("       3. Enable Remote Control")
            print("       4. Set Host IP = YOUR PC's IP (not robot's IP)")
            return False
    except Exception as e:
        print(f"[dash] {host}: Error checking status: {e}")
        return False


def _safe_get_q(robot) -> Optional[np.ndarray]:
    """Safely get current joint positions from robot."""
    try:
        positions = robot.ur.get_joint_positions()
        return positions if positions is not None else None
    except Exception:
        return None


def _set_gentle_mode(config: Config) -> Tuple[float, float, float]:
    """Set gentler control parameters for test movements."""
    old_values = (config.gain, config.vmax, config.amax)
    config.gain, config.vmax, config.amax = (
        220,
        0.35,
        0.9,
    )  # Slightly faster than before but still gentle
    return old_values


def _restore_mode(config: Config, old_values: Tuple[float, float, float]):
    """Restore original control parameters."""
    config.gain, config.vmax, config.amax = old_values


# DxlBus and URSide classes replaced by URDynamixelRobot from hardware.ur_dynamixel_robot


# URSide class replaced by URRobot from hardware.ur_dynamixel_robot


class PedalMonitor:
    """Monitor StreamDeck pedals for teleop control (robust decoder)."""

    def __init__(
        self, vendor_id: int = 0x0FD9, product_id: int = 0x0086, debug: bool = False
    ):
        """Initialize pedal monitor.

        Args:
            vendor_id: StreamDeck pedal vendor ID
            product_id: StreamDeck pedal product ID
            debug: Enable debug mode to print raw HID packets
        """
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.debug = debug
        self.device: Optional[Any] = None
        self.state = TeleopState.IDLE
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_buttons = set()
        self.last_change_ts = 0.0  # For debouncing
        self.last_left_edge_ts = 0.0  # For CENTER ghost suppression
        self.stable_since = 0.0  # For state stabilization
        self.debounce_s = 0.08  # 80ms debounce
        self.stabilize_s = 0.018  # 18ms stabilization
        self.suppress_center_after_left_s = 0.16  # 160ms CENTER suppression after LEFT
        self.cb_left: Optional[Any] = None
        self.cb_center_1: Optional[Any] = None
        self.cb_center_2: Optional[Any] = None
        self.cb_right: Optional[Any] = None

        # Default button mapping
        self.PEDAL_LEFT = 4
        self.PEDAL_CENTER = 5
        self.PEDAL_RIGHT = 6

    def connect(self) -> bool:
        """Connect to pedal device with better error handling."""
        if not hid:
            print("[pedal] hidapi module not available")
            return False

        # First check if device exists
        devices = hid.enumerate(self.vendor_id, self.product_id)
        if not devices:
            print(
                f"[pedal] No StreamDeck pedal found (VID:{self.vendor_id:04x} PID:{self.product_id:04x})"
            )
            print("[pedal] Check: lsusb | grep -i elgato  (or grep 0fd9)")
            return False

        print(f"[pedal] Found {len(devices)} StreamDeck pedal device(s)")

        # Try multiple connection attempts
        last_error = None
        for attempt in range(3):
            try:
                # Try to pick the best interface path (prefer :1.0 which has button endpoint)
                chosen = None
                backup = None
                for d in devices:
                    p = d.get("path")
                    if not backup and p:
                        backup = d
                    # Prefer interface path ending with ":1.0" or ":01.00"
                    if p and (p.endswith(b":1.0") or p.endswith(b":01.00")):
                        chosen = d
                        break

                if not chosen:
                    chosen = backup

                self.device = hid.device()

                # Try different connection methods
                if chosen and chosen.get("path"):
                    try:
                        self.device.open_path(chosen["path"])  # prefer stable path
                    except OSError as e:
                        if "Permission denied" in str(e) or "open failed" in str(e):
                            print(
                                f"[pedal] Attempt {attempt + 1}: Permission denied - need udev rules"
                            )
                            print("[pedal] Fix with:")
                            print("       sudo usermod -a -G plugdev $USER")
                            print(
                                '       echo \'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0fd9", MODE="0666"\' | sudo tee /etc/udev/rules.d/99-streamdeck.rules'
                            )
                            print(
                                "       sudo udevadm control --reload-rules && sudo udevadm trigger"
                            )
                            print("       Then unplug and replug the pedal")
                            # Try opening without path as fallback
                            self.device.open(self.vendor_id, self.product_id)
                        else:
                            raise
                else:
                    self.device.open(self.vendor_id, self.product_id)

                self.device.set_nonblocking(True)
                print(
                    f"[pedal] Connected to StreamDeck pedal {self.vendor_id:04x}:{self.product_id:04x}"
                )
                if self.debug:
                    print("[pedal] Debug ON — printing raw packets on changes")
                return True

            except Exception as e:
                last_error = e
                if attempt < 2:
                    print(
                        f"[pedal] Connection attempt {attempt + 1} failed: {e}, retrying..."
                    )
                    time.sleep(0.5)
                    continue

        print(f"[pedal] Failed to connect after 3 attempts: {last_error}")
        return False

    def start_monitoring(self) -> None:
        """Start monitoring thread."""
        if not self.device:
            if not self.connect():
                print("[pedal] Cannot start monitoring without device")
                return

        self._stop.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print("[pedal] Monitoring started")

    def stop_monitoring(self) -> None:
        """Stop monitoring thread."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self.device:
            self.device.close()
            self.device = None
        print("[pedal] Monitoring stopped")

    def _decode_buttons(self, data: List[int]) -> set:
        """Return set of buttons {4,5,6} currently pressed using multiple layouts."""
        btns = set()
        n = len(data)
        if n == 0:
            return btns

        # Preferred layout: byte-per-pedal at indices [4], [5], [6]
        if n >= 7:
            # Check if we have the byte-per-pedal format
            if any(data[i] in (0, 1) for i in (4, 5, 6)):
                if data[4] == 1:
                    btns.add(self.PEDAL_LEFT)
                if data[5] == 1:
                    btns.add(self.PEDAL_CENTER)
                if data[6] == 1:
                    btns.add(self.PEDAL_RIGHT)
                # If we detected buttons this way, return early
                if btns:
                    return btns

        # Fallback A: bitmask in byte 1 (bits 0..2)
        if not btns and n >= 2:
            m = data[1]
            if m & 0x01:
                btns.add(self.PEDAL_LEFT)
            if m & 0x02:
                btns.add(self.PEDAL_CENTER)
            if m & 0x04:
                btns.add(self.PEDAL_RIGHT)

        # Fallback B: bitmask in byte 4 (bits 0..2) - older format
        if not btns and n >= 5:
            m = data[4]
            if m & 0x01:
                btns.add(self.PEDAL_LEFT)
            if m & 0x02:
                btns.add(self.PEDAL_CENTER)
            if m & 0x04:
                btns.add(self.PEDAL_RIGHT)

        return btns

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        self.stable_since = time.monotonic()
        self.last_raw_print = 0.0
        while not self._stop.is_set():
            try:
                data = self.device.read(64, timeout_ms=50)  # nonblocking
                if data:
                    now = time.monotonic()
                    if self.debug:
                        # Only print raw on actual button changes, not constantly
                        current = self._decode_buttons(data)
                        if (
                            current != self.last_buttons
                            and (now - self.last_raw_print) > 0.1
                        ):
                            # Show raw data but format it better
                            # Map button numbers to names correctly
                            button_names = {4: "LEFT", 5: "CENTER", 6: "RIGHT"}
                            buttons_str = (
                                ", ".join(
                                    [
                                        f"{b}({button_names.get(b, '?')})"
                                        for b in sorted(current)
                                    ]
                                )
                                if current
                                else "none"
                            )
                            print(
                                f"[pedal-debug] raw: {list(data[:8])} → buttons: {buttons_str}"
                            )
                            self.last_raw_print = now
                    self._process_buttons(list(data))
            except Exception:
                pass  # Ignore read errors
            time.sleep(0.01)

    def _process_buttons(self, data: List[int]) -> None:
        """Process button presses from HID data with debouncing and single-edge filtering."""
        current_buttons = self._decode_buttons(data)
        now = time.monotonic()

        # Check if state has changed
        if current_buttons == self.last_buttons:
            # State unchanged - check if we've stabilized long enough
            if now - self.stable_since >= self.stabilize_s:
                pass  # State is stable
            return
        else:
            # State changed - reset stabilize timer
            self.stable_since = now

            # Only act if state persists beyond debounce window
            if now - self.last_change_ts < self.debounce_s:
                self.last_buttons = current_buttons
                return

        # Compute button changes
        added = current_buttons - self.last_buttons
        removed = self.last_buttons - current_buttons

        # Only process single-button changes (ignore multi-button noise)
        if len(added) + len(removed) != 1:
            if self.debug and (added or removed):
                print(f"[pedal] Multi-edge ignored: added={added}, removed={removed}")
            self.last_change_ts = now
            self.last_buttons = current_buttons
            return

        # Process single button press/release
        if added:
            button = next(iter(added))
            self.last_change_ts = now

            if button == self.PEDAL_LEFT and self.cb_left:
                print("\n⏸️ [LEFT PEDAL] Interrupt - URs stopped")
                print("   Purpose: Interrupt for external program control")
                print("   State: IDLE (ready for new sequence)")
                self.state = TeleopState.IDLE  # Reset state
                self.last_left_edge_ts = now  # Track for CENTER suppression
                self.cb_left()

            elif button == self.PEDAL_CENTER:
                # Suppress CENTER ghosts after LEFT press
                if now - self.last_left_edge_ts < self.suppress_center_after_left_s:
                    if self.debug:
                        print("   [CENTER suppressed - too soon after LEFT]")
                else:
                    if self.state == TeleopState.IDLE and self.cb_center_1:
                        print("\n🟡 [CENTER PEDAL - FIRST TAP] Preparing teleop...")
                        print("   ✓ Capturing baselines")
                        print("   ✓ Setting gentle mode")
                        print("   → Align robots, then press CENTER again to start")
                        self.cb_center_1()
                        self.state = TeleopState.PREP

                    elif self.state == TeleopState.PREP and self.cb_center_2:
                        print("\n🟢 [CENTER PEDAL - SECOND TAP] Starting teleop!")
                        print("   ✓ Full speed mode activated")
                        print("   ✓ Streaming at 125Hz")
                        print("   → Move GELLO arms to control UR robots")
                        self.cb_center_2()
                        self.state = TeleopState.RUNNING

            elif button == self.PEDAL_RIGHT and self.cb_right:
                print("\n⏹️ [RIGHT PEDAL] Stopping teleop")
                print("   ✓ Streaming stopped")
                print("   ✓ GELLO arms now passive")
                print("   State: IDLE (ready for new sequence)")
                self.cb_right()
                self.state = TeleopState.IDLE

        self.last_buttons = current_buttons


class PositionMonitor:
    """Background thread to continuously monitor and print GELLO arm positions."""

    def __init__(
        self,
        left_robot,  # Any robot type with dxl attribute
        right_robot,  # Any robot type with dxl attribute
        rate_hz: float = 10.0,  # Print rate (10Hz = 10 times per second)
        publish_zcm: bool = True,  # Enable ZCM publishing
    ):
        self.left_robot = left_robot
        self.right_robot = right_robot
        self.rate_hz = rate_hz
        self.publish_zcm = publish_zcm and ZCM_AVAILABLE
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # For angle unwrapping to fix multi-turn issues
        self.prev_left_continuous = None  # List of continuous angles for left arm
        self.prev_right_continuous = None  # List of continuous angles for right arm

        # Initialize ZCM if available
        self.zcm = None
        self.left_channel = "gello_positions_left"
        self.right_channel = "gello_positions_right"

        if self.publish_zcm:
            try:
                self.zcm = zerocm.ZCM()
                if self.zcm.good():
                    self.zcm.start()
                    print("[ZCM] Publishing to channels:")
                    print(f"      - {self.left_channel} (left arm positions)")
                    print(f"      - {self.right_channel} (right arm positions)")
                else:
                    print("[ZCM] Failed to initialize ZCM")
                    self.zcm = None
                    self.publish_zcm = False
            except Exception as e:
                print(f"[ZCM] Error initializing: {e}")
                self.zcm = None
                self.publish_zcm = False

    def start(self) -> None:
        """Start the monitoring thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="position_monitor"
        )
        self._thread.start()
        print(f"[MONITOR] Position monitoring started ({self.rate_hz}Hz)")

    def stop(self) -> None:
        """Stop the monitoring thread."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        # Clean up ZCM
        if self.zcm:
            try:
                self.zcm.stop()
            except Exception:
                pass

    def update_robots(
        self,
        left_robot,  # Any robot type with dxl attribute
        right_robot,  # Any robot type with dxl attribute
    ) -> None:
        """Update robot references (for when robots are rebuilt)."""
        self.left_robot = left_robot
        self.right_robot = right_robot

    def _publish_positions(
        self, channel: str, positions: Optional[List[float]], arm_side: str
    ) -> None:
        """Publish GELLO positions to ZCM channel.

        Args:
            channel: ZCM channel name
            positions: List of positions [j1, j2, j3, j4, j5, j6, gripper] in radians
            arm_side: "left" or "right"
        """
        if not self.publish_zcm or not self.zcm or positions is None:
            return

        try:
            # Create message
            msg = gello_positions_t()
            msg.timestamp = int(time.time() * 1e6)  # microseconds
            msg.arm_side = arm_side

            if positions is not None and len(positions) >= 6:
                # Set joint positions (first 6 values)
                msg.joint_positions = list(positions[:6])

                # Set gripper position if available
                if len(positions) > 6:
                    msg.gripper_position = float(positions[6])
                else:
                    msg.gripper_position = 0.0

                # Zero velocities for now (could be computed later)
                msg.joint_velocities = [0.0] * 6
                msg.is_valid = True
            else:
                # Invalid data - set defaults
                msg.joint_positions = [0.0] * 6
                msg.gripper_position = 0.0
                msg.joint_velocities = [0.0] * 6
                msg.is_valid = False

            # Publish the message
            self.zcm.publish(channel, msg)

        except Exception:
            # Silently ignore publish errors to not interfere with operation
            pass

    # Transform and UR5 offset publishing methods removed
    # Now handled by separate gello_ur_offset_publisher.py
    
    def _wrap_to_pi(self, angle_rad: float) -> float:
        """Wrap angle to [-pi, pi] range."""
        import math
        return ((angle_rad + math.pi) % (2 * math.pi)) - math.pi
    
    def _unwrap_angle(self, prev_continuous: Optional[float], curr_wrapped: float) -> float:
        """Unwrap angle to maintain continuity (no jumps).
        
        Args:
            prev_continuous: Previous continuous angle (None for first reading)
            curr_wrapped: Current wrapped angle in [-pi, pi]
        
        Returns:
            Continuous angle that doesn't jump
        """
        import math
        
        if prev_continuous is None:
            return curr_wrapped
        
        # Calculate the smallest delta considering wrapping
        delta = curr_wrapped - (prev_continuous % (2 * math.pi) - math.pi)
        if delta > math.pi:
            delta -= 2 * math.pi
        elif delta < -math.pi:
            delta += 2 * math.pi
            
        return prev_continuous + delta
    
    def _fix_multiturn_positions(self, positions: Optional[List[float]], 
                                 prev_continuous: Optional[List[float]],
                                 side: str) -> Optional[List[float]]:
        """Fix multi-turn accumulation issues in joint positions.
        
        Args:
            positions: Raw positions from Dynamixel (may have multi-turn accumulation)
            prev_continuous: Previous continuous positions for this arm
            side: 'left' or 'right' for debugging
            
        Returns:
            Fixed positions with proper wrapping/unwrapping
        """
        if positions is None:
            return None
            
        import math
        
        # Initialize previous if needed
        if prev_continuous is None:
            prev_continuous = [None] * len(positions)
        
        fixed_positions = []
        for i, raw_pos in enumerate(positions):
            # First wrap to [-pi, pi]
            wrapped = self._wrap_to_pi(raw_pos)
            
            # Check for bogus values (like the 377 million degrees issue)
            if abs(raw_pos) > 100 * 2 * math.pi:  # More than 100 rotations is suspicious
                # Use wrapped value directly for bogus readings
                continuous = wrapped
                if i < len(prev_continuous):
                    prev_continuous[i] = continuous
            else:
                # Unwrap to maintain continuity
                prev = prev_continuous[i] if i < len(prev_continuous) else None
                continuous = self._unwrap_angle(prev, wrapped)
                
                # Sanity check: reject impossible jumps (more than 90 degrees in one sample)
                if prev is not None and abs(continuous - prev) > math.pi/2:
                    # Keep previous value on suspicious jump
                    continuous = prev
                
                # Update previous
                if i < len(prev_continuous):
                    prev_continuous[i] = continuous
            
            fixed_positions.append(continuous)
        
        return fixed_positions

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        # Minimal sleep for maximum responsiveness
        sleep_time = 0.002  # 2ms minimum sleep (can handle up to 500Hz)
        debug_counter = 0
        simulate_positions = (
            True  # Flag to use simulated data when robots not available
        )
        last_publish_time = 0  # Track time for rate limiting ZCM publishes

        while not self._stop.is_set():
            try:
                # Read positions from both arms
                left_pos = None
                right_pos = None

                if self.left_robot and self.left_robot.dxl:
                    try:
                        raw_left = self.left_robot.dxl.read_positions()
                        if raw_left is not None:
                            # Fix multi-turn accumulation issues
                            if self.prev_left_continuous is None:
                                self.prev_left_continuous = [None] * len(raw_left)
                            left_pos = self._fix_multiturn_positions(
                                raw_left, self.prev_left_continuous, 'left'
                            )
                            simulate_positions = False  # Got real data
                    except Exception as e:
                        if debug_counter % 100 == 0:  # Print every 10 seconds at 10Hz
                            print(f"[MONITOR] Left DXL read error: {e}")

                if self.right_robot and self.right_robot.dxl:
                    try:
                        raw_right = self.right_robot.dxl.read_positions()
                        if raw_right is not None:
                            # Fix multi-turn accumulation issues
                            if self.prev_right_continuous is None:
                                self.prev_right_continuous = [None] * len(raw_right)
                            right_pos = self._fix_multiturn_positions(
                                raw_right, self.prev_right_continuous, 'right'
                            )
                            simulate_positions = False  # Got real data
                    except Exception as e:
                        if debug_counter % 100 == 0:  # Print every 10 seconds at 10Hz
                            print(f"[MONITOR] Right DXL read error: {e}")

                # If no real data available, use simulated positions for testing
                if simulate_positions and self.publish_zcm:
                    import math

                    phase = debug_counter * 0.01  # Slow sine wave

                    # Simulated left arm positions (7 joints: 6 arm + 1 gripper)
                    left_pos = [
                        -0.785 + 0.1 * math.sin(phase),  # J1
                        -1.571 + 0.05 * math.cos(phase),  # J2
                        0.0 + 0.02 * math.sin(phase * 2),  # J3
                        -1.571 + 0.05 * math.cos(phase),  # J4
                        1.571 + 0.05 * math.sin(phase),  # J5
                        0.0 + 0.02 * math.cos(phase * 2),  # J6
                        0.5 + 0.3 * math.sin(phase * 0.5),  # Gripper
                    ]

                    # Simulated right arm positions (slightly different phase)
                    right_pos = [
                        -0.790 + 0.1 * math.sin(phase + 0.5),  # J1
                        -1.570 + 0.05 * math.cos(phase + 0.5),  # J2
                        0.001 + 0.02 * math.sin(phase * 2 + 0.5),  # J3
                        -1.572 + 0.05 * math.cos(phase + 0.5),  # J4
                        1.570 + 0.05 * math.sin(phase + 0.5),  # J5
                        0.001 + 0.02 * math.cos(phase * 2 + 0.5),  # J6
                        0.6 + 0.3 * math.sin(phase * 0.5 + 0.5),  # Gripper
                    ]

                    if debug_counter == 0 or debug_counter == 10:
                        print(
                            "[MONITOR] Using SIMULATED positions for ZCM (no robots connected)"
                        )

                # Debug: Print publishing status periodically
                if debug_counter % 100 == 0:  # Every 10 seconds at 10Hz
                    mode = "SIMULATED" if simulate_positions else "REAL"
                    print(
                        f"[ZCM DEBUG] Mode={mode}, publish_zcm={self.publish_zcm}, zcm={self.zcm is not None}, left_pos={left_pos is not None}, right_pos={right_pos is not None}"
                    )

                # Publish positions to ZCM at specified rate
                current_time = time.time()
                publish_interval = 1.0 / self.rate_hz  # 10Hz = 0.1 seconds
                
                if self.publish_zcm and (current_time - last_publish_time) >= publish_interval:
                    self._publish_positions(self.left_channel, left_pos, "left")
                    self._publish_positions(self.right_channel, right_pos, "right")
                    last_publish_time = current_time

                    # Debug: Count successful publishes
                    if debug_counter % 500 == 0 and (left_pos or right_pos):  # Adjusted for faster loop
                        mode = "SIMULATED" if simulate_positions else "REAL"
                        print(
                            f"[ZCM] Publishing {mode} data: left={left_pos is not None}, right={right_pos is not None}"
                        )

                # Format and print positions at 10Hz (separate from loop rate)
                if (current_time - last_publish_time) < publish_interval * 0.9:
                    # Skip printing if we're not near a publish time
                    pass
                else:
                    timestamp = time.strftime("%H:%M:%S")

                    # Build position strings
                    left_str = "DISCONNECTED"
                    right_str = "DISCONNECTED"

                    if left_pos is not None:
                        # Format: J1:xx.x° J2:xx.x° ... J7:xx.x° (gripper)
                        left_joints = [
                            f"J{i + 1}:{np.degrees(p):6.1f}°"
                            for i, p in enumerate(left_pos[:6])
                        ]
                        left_gripper = (
                            f"J7:{np.degrees(left_pos[6]):6.1f}°"
                            if len(left_pos) > 6
                            else "J7:---"
                        )
                        left_str = " ".join(left_joints) + " " + left_gripper

                    if right_pos is not None:
                        # Format: J10:xx.x° J11:xx.x° ... J16:xx.x° (gripper)
                        right_joints = [
                            f"J{i + 10}:{np.degrees(p):6.1f}°"
                            for i, p in enumerate(right_pos[:6])
                        ]
                        right_gripper = (
                            f"J16:{np.degrees(right_pos[6]):6.1f}°"
                            if len(right_pos) > 6
                            else "J16:---"
                        )
                        right_str = " ".join(right_joints) + " " + right_gripper

                    # Print in a clean format
                    print(f"\r[{timestamp}] GELLO LEFT:  {left_str}", end="")
                    print(f"\n           GELLO RIGHT: {right_str}", end="")

                    print("\033[1A", end="", flush=True)  # Move cursor up 1 line

            except Exception as e:
                # Log errors periodically
                if debug_counter % 100 == 0:
                    print(f"[MONITOR] Loop error: {e}")

            debug_counter += 1
            time.sleep(sleep_time)


class FollowThread:
    def __init__(
        self,
        left_robot,  # Any robot type with dxl and ur attributes
        right_robot,  # Any robot type with dxl and ur attributes
        config: Config,
    ):
        self.left_robot = left_robot
        self.right_robot = right_robot
        self.config = config
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Motion controllers
        profile = MotionProfile(
            velocity_max=config.vmax,
            acceleration_max=config.amax,
            ema_alpha=config.ema_alpha,
            softstart_time=config.softstart_time,
            deadband_rad=config.deadband_rad[:6]
            if len(config.deadband_rad) > 6
            else config.deadband_rad,  # Only first 6 for UR
            scale_factors=config.scale[:6]
            if len(config.scale) > 6
            else config.scale,  # Only first 6 for UR
            clamp_rad=config.clamp_rad[:6]
            if len(config.clamp_rad) > 6
            else config.clamp_rad,  # Only first 6 for UR
        )

        self.left_controller = (
            SmoothMotionController(
                num_joints=6,  # UR joints only
                profile=profile,
                control_dt=config.dt,
            )
            if left_robot
            else None
        )

        self.right_controller = (
            SmoothMotionController(
                num_joints=6,  # UR joints only
                profile=profile,
                control_dt=config.dt,
            )
            if right_robot
            else None
        )

        # Fixed-rate scheduler
        self.scheduler = FixedRateScheduler(config.hz)

        # Error tracking
        self.error_count = {"left": 0, "right": 0}
        self.max_errors = config.safety.get("max_control_errors", 2)

        # Gripper state tracking
        self.left_gripper_baseline = 0.0
        self.right_gripper_baseline = 0.0
        self.left_gripper_cmd = 0.0
        self.right_gripper_cmd = 0.0
        self._left_last_gripper_cmd = 0.0
        self._right_last_gripper_cmd = 0.0

    def capture_baselines(self):
        """Capture current positions as baselines."""
        success = False

        # Left robot
        if self.left_robot and self.left_controller:
            try:
                dxl_pos = self.left_robot.dxl.read_positions()
                ur_pos = self.left_robot.ur.get_joint_positions()

                if dxl_pos is not None and ur_pos is not None:
                    # Only first 6 joints for UR
                    self.left_controller.set_baselines(dxl_pos[:6], ur_pos)
                    # Capture gripper baseline if available
                    if len(dxl_pos) > 6:
                        self.left_gripper_baseline = dxl_pos[6]
                    else:
                        self.left_gripper_baseline = 0.0
                    print(
                        f"   ✓ LEFT arm: {min(6, len(dxl_pos))} DXL joints, {len(ur_pos)} UR joints, gripper={len(dxl_pos) > 6}"
                    )
                    success = True
                else:
                    if dxl_pos is None:
                        print("   ✗ LEFT arm: DXL servos not responding")
                    if ur_pos is None:
                        print("   ✗ LEFT arm: UR not responding")
            except Exception as e:
                print(f"   ✗ LEFT arm: Error reading positions - {e}")

        # Right robot
        if self.right_robot and self.right_controller:
            try:
                dxl_pos = self.right_robot.dxl.read_positions()
                ur_pos = self.right_robot.ur.get_joint_positions()

                if dxl_pos is not None and ur_pos is not None:
                    # Only first 6 joints for UR
                    self.right_controller.set_baselines(dxl_pos[:6], ur_pos)
                    # Capture gripper baseline if available
                    if len(dxl_pos) > 6:
                        self.right_gripper_baseline = dxl_pos[6]
                    else:
                        self.right_gripper_baseline = 0.0
                    print(
                        f"   ✓ RIGHT arm: {min(6, len(dxl_pos))} DXL joints, {len(ur_pos)} UR joints, gripper={len(dxl_pos) > 6}"
                    )
                    success = True
                else:
                    if dxl_pos is None:
                        print("   ✗ RIGHT arm: DXL servos not responding")
                    if ur_pos is None:
                        print("   ✗ RIGHT arm: UR not responding")
            except Exception as e:
                print(f"   ✗ RIGHT arm: Error reading positions - {e}")

        return success

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="follow125")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        # Stop robots - COMMENTED OUT FOR TESTING
        # if self.left_robot:
        #     self.left_robot.ur.stop_j(self.config.amax)
        # if self.right_robot:
        #     self.right_robot.ur.stop_j(self.config.amax)

    def _send_gripper_command(self, side: str, position: float):
        """Send gripper command via the dexgpt debug_tools script."""
        try:
            # Call the actual gripper command script from dexgpt
            # Path to the dexgpt gripper command script
            dexgpt_path = os.path.expanduser("~/generalistai/dexgpt")
            script_path = os.path.join(
                dexgpt_path, "debug_tools", "send_gripper_cmd.py"
            )

            # Build the command
            cmd = [
                "python",
                script_path,
                "-o",
                f"gripper_command_{side}",
                "--position",
                str(position),
            ]

            # Execute the command (non-blocking with timeout)
            subprocess.run(
                cmd,
                cwd=dexgpt_path,  # Run from dexgpt directory
                capture_output=True,
                timeout=0.5,  # 500ms timeout to prevent blocking
                check=False,  # Don't raise on non-zero exit
            )

            # Optional: Also save to JSON for debugging/monitoring
            command_file = f"/tmp/gripper_command_{side}.json"
            command_data = {
                "timestamp": time.time(),
                "position": position,
                "side": side,
                "sent_via": "dexgpt",
            }
            with open(command_file, "w") as f:
                json.dump(command_data, f)

        except subprocess.TimeoutExpired:
            # Command took too long, but don't stop teleop
            pass
        except Exception as e:
            # Don't let gripper errors stop teleop
            if self.config.debug.get("verbose", False):
                print(f"[gripper] Error sending command: {e}")
            pass

    def _ensure_ur_ready(self, robot) -> bool:
        """Ensure UR is ready for control."""
        if not robot.ur.ensure_control():
            print(f"[follow] {robot.ur.host}: RTDE control not available")
            return False
        return True

    def _run(self) -> None:
        # Try to bump process niceness (Linux); ignore if not permitted
        try:
            import os

            os.nice(-5)
        except Exception:
            pass

        # Prepare URs first; don't start loop if neither is ready
        ready_any = False
        if self.left_robot and self._ensure_ur_ready(self.left_robot):
            ready_any = True
        if self.right_robot and self._ensure_ur_ready(self.right_robot):
            ready_any = True

        if not ready_any:
            print("[follow] No UR control available; not starting streaming")
            return

        # Start scheduler
        self.scheduler.start()
        loop_count = 0

        while not self._stop.is_set():
            # LEFT robot control
            if self.left_robot and self.left_controller:
                dxl_pos = self.left_robot.dxl.read_positions()
                ur_pos = self.left_robot.ur.get_joint_positions()

                if dxl_pos is not None and ur_pos is not None:
                    print(f"[LEFT] dxl_pos: {dxl_pos}")
                    # Auto-initialize baselines on first run if needed
                    if self.left_controller._baseline_dxl is None:
                        self.left_controller.set_baselines(dxl_pos[:6], ur_pos)
                        if len(dxl_pos) > 6:
                            self.left_gripper_baseline = dxl_pos[6]

                    # Update controller and get target positions (only first 6 joints)
                    target, is_moving = self.left_controller.update(dxl_pos[:6], ur_pos)

                    # Handle gripper if available (7th joint)
                    if self.config.gripper_enabled and len(dxl_pos) > 6:
                        gripper_pos = dxl_pos[6]

                        # Map DXL gripper position to actual gripper commands
                        # Based on actual test results for LEFT gripper:
                        # MIN: 2.5112 rad (closed), MAX: 3.4316 rad (open)
                        gripper_threshold = 2.97  # Midpoint between closed and open

                        # Actual gripper command values (from user testing)
                        GRIPPER_CLOSED = (
                            -0.1
                        )  # Command when GELLO gripper is activated/closed
                        GRIPPER_OPEN = (
                            0.25  # Command when GELLO gripper is released/open
                        )

                        # Determine gripper state based on position
                        # LEFT gripper: lower values = closed, higher values = open
                        if gripper_pos < gripper_threshold:
                            # GELLO gripper is closed/activated
                            gripper_cmd = GRIPPER_CLOSED
                        else:
                            # GELLO gripper is open/released
                            gripper_cmd = GRIPPER_OPEN

                        # Store gripper command for external use
                        self.left_gripper_cmd = gripper_cmd

                        # Send actual gripper command if changed (with hysteresis)
                        if not hasattr(self, "_left_last_sent_cmd"):
                            self._left_last_sent_cmd = gripper_cmd
                            print(
                                f"[LEFT GRIPPER] Initial state: {'CLOSED' if gripper_cmd < 0 else 'OPEN'} (pos: {gripper_pos:.3f} rad, cmd: {gripper_cmd})"
                            )
                            self._send_gripper_command("left", gripper_cmd)
                        elif abs(gripper_cmd - self._left_last_sent_cmd) > 0.05:
                            # Only send if significantly different
                            print(
                                f"[LEFT GRIPPER] Changed to: {'CLOSED' if gripper_cmd < 0 else 'OPEN'} (pos: {gripper_pos:.3f} rad, cmd: {gripper_cmd})"
                            )
                            self._left_last_sent_cmd = gripper_cmd
                            self._send_gripper_command("left", gripper_cmd)

                    # Send servoJ command - COMMENTED OUT FOR TESTING
                    # try:
                    #     success = self.left_robot.ur.servo_j(
                    #         target,
                    #         self.config.vmax,
                    #         self.config.amax,
                    #         self.config.dt,
                    #         self.config.lookahead,
                    #         self.config.gain,
                    #     )
                    #     if success:
                    #         self.error_count["left"] = 0
                    #     else:
                    #         raise RuntimeError("servoJ failed")
                    # except Exception as e:
                    #     self.error_count["left"] += 1
                    #     if self.error_count["left"] == 1:
                    #         print(f"\n⚠️  LEFT UR: Control error - {e}")
                    #         print("     Ensure ExternalControl.urp is PLAYING")
                    #     if self.error_count["left"] >= self.max_errors:
                    #         print("   Too many errors - stopping for safety")
                    #         self._stop.set()
                    #         return
                    self.error_count["left"] = 0  # Keep counter reset

            # RIGHT robot control
            if self.right_robot and self.right_controller:
                dxl_pos = self.right_robot.dxl.read_positions()
                ur_pos = self.right_robot.ur.get_joint_positions()

                if dxl_pos is not None and ur_pos is not None:
                    # Auto-initialize baselines on first run if needed
                    if self.right_controller._baseline_dxl is None:
                        self.right_controller.set_baselines(dxl_pos[:6], ur_pos)
                        if len(dxl_pos) > 6:
                            self.right_gripper_baseline = dxl_pos[6]

                    # Update controller and get target positions (only first 6 joints)
                    target, is_moving = self.right_controller.update(
                        dxl_pos[:6], ur_pos
                    )

                    # Handle gripper if available (7th joint)
                    if self.config.gripper_enabled and len(dxl_pos) > 6:
                        gripper_pos = dxl_pos[6]

                        # Map DXL gripper position to actual gripper commands
                        # Based on actual test results for RIGHT gripper:
                        # MIN: 4.1050 rad (closed), MAX: 5.0929 rad (open)
                        gripper_threshold = 4.60  # Midpoint between closed and open

                        # Actual gripper command values (from user testing)
                        GRIPPER_CLOSED = (
                            -0.1
                        )  # Command when GELLO gripper is activated/closed
                        GRIPPER_OPEN = (
                            0.25  # Command when GELLO gripper is released/open
                        )

                        # Determine gripper state based on position
                        # RIGHT gripper: lower values = closed, higher values = open
                        if gripper_pos < gripper_threshold:
                            # GELLO gripper is closed/activated
                            gripper_cmd = GRIPPER_CLOSED
                        else:
                            # GELLO gripper is open/released
                            gripper_cmd = GRIPPER_OPEN

                        # Store gripper command for external use
                        self.right_gripper_cmd = gripper_cmd

                        # Send actual gripper command if changed (with hysteresis)
                        if not hasattr(self, "_right_last_sent_cmd"):
                            self._right_last_sent_cmd = gripper_cmd
                            print(
                                f"[RIGHT GRIPPER] Initial state: {'CLOSED' if gripper_cmd < 0 else 'OPEN'} (pos: {gripper_pos:.3f} rad, cmd: {gripper_cmd})"
                            )
                            self._send_gripper_command("right", gripper_cmd)
                        elif abs(gripper_cmd - self._right_last_sent_cmd) > 0.05:
                            # Only send if significantly different
                            print(
                                f"[RIGHT GRIPPER] Changed to: {'CLOSED' if gripper_cmd < 0 else 'OPEN'} (pos: {gripper_pos:.3f} rad, cmd: {gripper_cmd})"
                            )
                            self._right_last_sent_cmd = gripper_cmd
                            self._send_gripper_command("right", gripper_cmd)

                    # Send servoJ command - COMMENTED OUT FOR TESTING
                    # try:
                    #     success = self.right_robot.ur.servo_j(
                    #         target,
                    #         self.config.vmax,
                    #         self.config.amax,
                    #         self.config.dt,
                    #         self.config.lookahead,
                    #         self.config.gain,
                    #     )
                    #     if success:
                    #         self.error_count["right"] = 0
                    #     else:
                    #         raise RuntimeError("servoJ failed")
                    # except Exception as e:
                    #     self.error_count["right"] += 1
                    #     if self.error_count["right"] == 1:
                    #         print(f"\n⚠️  RIGHT UR: Control error - {e}")
                    #         print("     Ensure ExternalControl.urp is PLAYING")
                    #     if self.error_count["right"] >= self.max_errors:
                    #         print("   Too many errors - stopping for safety")
                    #         self._stop.set()
                    #         return
                    self.error_count["right"] = 0  # Keep counter reset

            # Wait for next tick
            self.scheduler.wait()

            # Print timing stats occasionally
            loop_count += 1
            if loop_count % 1000 == 0:
                stats = self.scheduler.get_stats()
                print(
                    f"[timing] freq: {stats['mean_freq']:.1f}Hz, "
                    f"overruns: {stats['overruns']}, "
                    f"dt: {stats['mean_dt'] * 1000:.1f}±{stats['std_dt'] * 1000:.1f}ms"
                )


def _build_robot(
    config: Config,
    side: str,  # "left" or "right"
    retry_dxl: bool = True,
):  # Returns DynamixelOnlyRobot in testing mode
    """Build a robot from config (DynamixelOnly in testing mode)."""
    robot_config = getattr(config, f"{side}_robot", {})

    if not robot_config:
        return None

    ur_host = robot_config.get("ur_host")
    dxl_port = robot_config.get("dxl_port")

    if not ur_host or not dxl_port:
        return None

    # Get DXL parameters
    dxl_ids = robot_config.get("dxl_ids", [])
    dxl_signs = robot_config.get("dxl_signs", [1] * len(dxl_ids))
    dxl_offsets = robot_config.get("dxl_offsets_deg", [0.0] * len(dxl_ids))

    # Create robot - MODIFIED FOR TESTING: Only Dynamixel, no UR5
    # Using a wrapper class to avoid UR5 connection
    class MockUR:
        """Mock UR class that does nothing"""

        def __init__(self):
            self.host = ur_host

        def get_joint_positions(self):
            return [0.0] * 6  # Return dummy positions

        def servo_j(self, *args, **kwargs):
            return True  # Always succeed

        def stop_j(self, *args):
            pass  # Do nothing

        def ensure_control(self):
            return True  # Always ready

    class DynamixelOnlyRobot:
        def __init__(self, dxl_driver, ur_host):
            self.dxl = dxl_driver
            self.ur = MockUR()  # Mock UR5 object

        def connect(self):
            dxl_ok = self.dxl.connect()
            return False, dxl_ok  # Always return False for UR5

        def disconnect(self):
            self.dxl.disconnect()

        def set_dxl_torque(self, enabled):
            self.dxl.set_torque_enabled(enabled)

    # Import DynamixelDriver

    # Create Dynamixel driver
    dxl_driver = DynamixelDriver(
        port=dxl_port,
        ids=dxl_ids,
        signs=dxl_signs,
        offsets_deg=dxl_offsets,
        baudrate=config.dynamixel.get("baudrate", 1000000),
    )

    # Create wrapper robot
    robot = DynamixelOnlyRobot(dxl_driver, ur_host)

    # Connect with retry logic for DXL
    ur_ok, dxl_ok = robot.connect()

    # If DXL fails, try once more after a short delay
    if not dxl_ok and retry_dxl:
        print(f"[{side}] DXL connection failed, retrying...")
        time.sleep(0.5)
        robot.dxl.disconnect()
        dxl_ok = robot.dxl.connect()

    print(
        f"[{side}] UR: DISABLED (Testing Mode), DXL: {'connected' if dxl_ok else 'FAILED'}"
    )

    if not dxl_ok:
        print(f"[{side}] WARNING: Dynamixel servos not responding")
        print(f"       Port: {dxl_port}")
        print(f"       IDs: {dxl_ids}")
        # Don't return None - let it work with UR only

    return robot


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Optimized DXL→UR teleop with GELLO patterns"
    )
    ap.add_argument(
        "-c",
        "--config",
        type=str,
        default="configs/teleop_dual_ur5.yaml",
        help="Path to YAML configuration file",
    )

    # Legacy command-line arguments (override config if provided)
    ap.add_argument(
        "--ur-left",
        type=str,
        default=None,
        help="UR IP for LEFT arm (overrides config)",
    )
    ap.add_argument(
        "--ur-right",
        type=str,
        default=None,
        help="UR IP for RIGHT arm (overrides config)",
    )
    ap.add_argument(
        "--left-port", type=str, default=None, help="LEFT DXL port (overrides config)"
    )
    ap.add_argument(
        "--right-port", type=str, default=None, help="RIGHT DXL port (overrides config)"
    )
    ap.add_argument(
        "--baud", type=int, default=None, help="DXL baudrate (overrides config)"
    )

    # Control flags
    ap.add_argument(
        "--joints-passive", action="store_true", help="Leave DXL torque OFF"
    )
    ap.add_argument("--torque-on", action="store_true", help="Force DXL torque ON")
    ap.add_argument(
        "--pedal-debug", action="store_true", help="Print raw pedal packets"
    )
    ap.add_argument("--dxl-test", action="store_true", help="Test DXL servos and exit")
    ap.add_argument(
        "--no-dashboard", action="store_true", help="Skip UR dashboard commands"
    )
    ap.add_argument(
        "--test-mode", action="store_true", help="Auto-start without pedals"
    )
    ap.add_argument(
        "--no-zcm", action="store_true", help="Disable ZCM position publishing"
    )

    args = ap.parse_args(argv)

    # Load configuration
    config = load_config(args.config)

    # Apply command-line overrides
    if args.ur_left:
        config.left_robot["ur_host"] = args.ur_left
    if args.ur_right:
        config.right_robot["ur_host"] = args.ur_right
    if args.left_port:
        config.left_robot["dxl_port"] = args.left_port
    if args.right_port:
        config.right_robot["dxl_port"] = args.right_port
    if args.baud:
        config.dynamixel["baudrate"] = args.baud

    # Apply flags
    config.debug["pedal_debug"] = args.pedal_debug

    # Build robots
    print("\nBuilding robot connections...")
    left_robot = _build_robot(config, "left")
    right_robot = _build_robot(config, "right")

    if not (left_robot or right_robot):
        print("[exit] No robots configured - check config file")
        return 2

    # Create position monitor (runs in background at all times)
    position_monitor = PositionMonitor(
        left_robot,
        right_robot,
        rate_hz=10.0,  # Publish 10 times per second
        publish_zcm=(not args.no_zcm),
    )
    position_monitor.start()

    # DXL diagnostic test mode
    if args.dxl_test:
        print("\n" + "=" * 60)
        print("DXL SERVO DIAGNOSTIC TEST")
        print("=" * 60)

        test_passed = False

        if left_robot:
            print("\n[TEST] LEFT arm")
            print(f"       Port: {config.left_robot.get('dxl_port')}")
            print(f"       IDs: {config.left_robot.get('dxl_ids')}")
            print(f"       Baud: {config.dynamixel.get('baudrate')}")

            # Test read
            for attempt in range(3):
                positions = left_robot.dxl.read_positions()
                if positions is not None:
                    print("       ✓ SUCCESS! Positions:")
                    for i, pos in enumerate(positions):
                        print(
                            f"         Joint {i}: {pos:.3f} rad ({np.degrees(pos):.1f}°)"
                        )
                    test_passed = True
                    break
                else:
                    print(f"       Attempt {attempt + 1}/3: No response")
                    time.sleep(0.5)

        if right_robot:
            print("\n[TEST] RIGHT arm")
            print(f"       Port: {config.right_robot.get('dxl_port')}")
            print(f"       IDs: {config.right_robot.get('dxl_ids')}")
            print(f"       Baud: {config.dynamixel.get('baudrate')}")

            # Test read
            for attempt in range(3):
                positions = right_robot.dxl.read_positions()
                if positions is not None:
                    print("       ✓ SUCCESS! Positions:")
                    for i, pos in enumerate(positions):
                        print(
                            f"         Joint {i}: {pos:.3f} rad ({np.degrees(pos):.1f}°)"
                        )
                    test_passed = True
                    break
                else:
                    print(f"       Attempt {attempt + 1}/3: No response")
                    time.sleep(0.5)

        print("\n" + "=" * 60)
        if test_passed:
            print("✓ Servos are responding")
        else:
            print("✗ No servos responding")
        print("=" * 60)

        # Cleanup
        if left_robot:
            left_robot.disconnect()
        if right_robot:
            right_robot.disconnect()
        return 0

    # Print startup diagnostics
    print("\n" + "=" * 60)
    print("TELEOP STARTUP DIAGNOSTICS (UR5 CONTROL DISABLED FOR TESTING)")
    print("=" * 60)
    print(f"Config: {args.config}")
    print(f"Speed: VMAX={config.vmax:.2f} rad/s, AMAX={config.amax:.1f} rad/s²")
    if config.vmax < 0.1:
        print("  → SAFE MODE: Very slow for testing")
    elif config.vmax < 0.5:
        print("  → GENTLE MODE: Good for initial testing")
    else:
        print("  → NORMAL MODE: Full speed operation")

    print("\nRobots:")
    if left_robot:
        print(
            f"  LEFT:  {config.left_robot['ur_host']} + {config.left_robot['dxl_port']}"
        )
    if right_robot:
        print(
            f"  RIGHT: {config.right_robot['ur_host']} + {config.right_robot['dxl_port']}"
        )

    print("\nControl:")
    print(f"  Rate: {config.hz} Hz")
    print(f"  Joints: {'PASSIVE' if args.joints_passive else 'ACTIVE'}")
    print(f"  Dashboard: {'DISABLED' if args.no_dashboard else 'ENABLED'}")
    print("=" * 60 + "\n")

    try:
        # Set DXL torque mode
        if args.torque_on and not args.joints_passive:
            if left_robot:
                left_robot.set_dxl_torque(True)
            if right_robot:
                right_robot.set_dxl_torque(True)
            print("[dxl] Torque ON")
        else:
            print("[dxl] Torque OFF (passive mode)")

        # Prepare UR robots - COMMENTED OUT FOR TESTING
        # if not args.no_dashboard:
        #     for robot, side in [(left_robot, "LEFT"), (right_robot, "RIGHT")]:
        #         if robot:
        #             print(f"[init] Preparing {side} UR at {robot.ur.host}...")
        #             _dashboard_play(robot.ur.host)

        # Create follow thread
        ft = FollowThread(
            left_robot=left_robot,
            right_robot=right_robot,
            config=config,
        )

        # Set up pedal monitoring
        pedal_monitor = PedalMonitor(
            vendor_id=config.pedal.get("vendor_id", 0x0FD9),
            product_id=config.pedal.get("product_id", 0x0086),
            debug=config.debug.get("pedal_debug", False),
        )

        # Track saved mode for gentle -> full transition
        _saved_mode = None

        # Define pedal callbacks
        def on_left_interrupt():
            """INTERRUPT: Stop URs for external program control."""
            nonlocal left_robot, right_robot

            # Stop the follow thread
            if ft._thread and ft._thread.is_alive():
                ft.stop()

            # Stop and disconnect robots - UR STOP COMMENTED OUT FOR TESTING
            for robot in (left_robot, right_robot):
                if robot:
                    # robot.ur.stop_j(config.amax)  # COMMENTED OUT FOR TESTING
                    # time.sleep(0.05)  # COMMENTED OUT FOR TESTING
                    robot.disconnect()

            # Reset controllers
            if ft.left_controller:
                ft.left_controller.reset()
            if ft.right_controller:
                ft.right_controller.reset()

            # Clear robot references so they get rebuilt on next use
            left_robot = None
            right_robot = None

            # Update position monitor to clear references
            position_monitor.update_robots(None, None)

        def on_center_first():
            """PREP: capture baselines, gentle mode, no streaming yet."""
            nonlocal _saved_mode, left_robot, right_robot

            # Rebuild robots if they were disconnected
            if left_robot is None:
                print("[prep] Rebuilding LEFT robot connection...")
                left_robot = _build_robot(config, "left")
                if left_robot:
                    ft.left_robot = left_robot

            if right_robot is None:
                print("[prep] Rebuilding RIGHT robot connection...")
                right_robot = _build_robot(config, "right")
                if right_robot:
                    ft.right_robot = right_robot

            # Update position monitor with new robot references
            position_monitor.update_robots(left_robot, right_robot)

            _saved_mode = _set_gentle_mode(config)

            # Capture baselines with error checking
            ft.capture_baselines()

            # Ensure UR control is ready - COMMENTED OUT FOR TESTING
            # for robot in (left_robot, right_robot):
            #     if robot:
            #         robot.ur.ensure_control()

        def on_center_second():
            """START: restore full params and begin streaming."""
            nonlocal _saved_mode
            if _saved_mode is not None:
                _restore_mode(config, _saved_mode)
                _saved_mode = None

            # Quick DXL check
            dxl_ok = False
            if left_robot and left_robot.dxl.read_positions() is not None:
                dxl_ok = True
                print("   ✓ LEFT DXL ready")
            if right_robot and right_robot.dxl.read_positions() is not None:
                dxl_ok = True
                print("   ✓ RIGHT DXL ready")

            if not dxl_ok:
                print("\n⚠️  ERROR: No DXL servos responding!")
                print("   Check servo power and connections")
                return

            print("\n✅ Starting teleoperation (UR5 CONTROL DISABLED FOR TESTING)!")
            print("   📡 Publishing GELLO positions to ZCM")
            print("   ❌ NOT sending commands to UR5 robots")
            ft.start()

        def on_right_stop():
            """STOP: Clean shutdown and return to idle."""
            print("   🔄 Starting shutdown...")

            # Stop teleop thread
            print("   [1/4] Stopping teleop...")
            ft.stop()
            time.sleep(0.1)

            # Disconnect robots
            print("   [2/4] Disconnecting robots...")
            for robot in (left_robot, right_robot):
                if robot:
                    try:
                        robot.disconnect()
                    except Exception:
                        pass  # Ignore errors during shutdown

            # Set DXL to passive with timeout
            print("   [3/4] Setting servos to passive...")

            def set_passive_with_timeout():
                for robot in (left_robot, right_robot):
                    if robot:
                        try:
                            robot.set_dxl_torque(False)
                        except Exception:
                            pass  # Ignore errors

            # Use threading with timeout to prevent hanging
            import threading

            passive_thread = threading.Thread(target=set_passive_with_timeout)
            passive_thread.daemon = True  # Make it daemon so it doesn't block exit
            passive_thread.start()
            passive_thread.join(timeout=0.5)  # 500ms timeout

            if passive_thread.is_alive():
                print("       (Skipped - timeout)")

            # Clear connections
            print("   [4/4] Clearing connections...")
            robot_hosts = []
            if left_robot:
                robot_hosts.append(left_robot.ur.host)
            if right_robot:
                robot_hosts.append(right_robot.ur.host)

            if robot_hosts:
                try:
                    clear_robots_quietly(robot_hosts)
                except Exception:
                    pass  # Ignore errors

            # Reset state
            pedal_monitor.state = TeleopState.IDLE
            print("   ✅ Shutdown complete")

        # Assign callbacks
        pedal_monitor.cb_left = on_left_interrupt
        pedal_monitor.cb_center_1 = on_center_first
        pedal_monitor.cb_center_2 = on_center_second
        pedal_monitor.cb_right = on_right_stop

        # Update button mapping from config
        pedal_monitor.PEDAL_LEFT = config.pedal_left
        pedal_monitor.PEDAL_CENTER = config.pedal_center
        pedal_monitor.PEDAL_RIGHT = config.pedal_right

        # Start pedal monitoring
        pedal_connected = pedal_monitor.connect()
        if pedal_connected:
            pedal_monitor.start_monitoring()
            print("\n" + "=" * 60)
            print("STREAMDECK PEDAL CONTROL READY")
            print("=" * 60)
            print("\n🎮 Pedal Functions:")
            print("   ⏸️  LEFT   → Interrupt (for external program control)")
            print("   🟡 CENTER → Tap 1: Prepare | Tap 2: Start teleop")
            print("   ⏹️  RIGHT  → Stop teleop (return to idle)\n")
            print("⚙️  Settings:")
            print(
                f"   Speed: VMAX={config.vmax:.2f} rad/s, AMAX={config.amax:.1f} rad/s²"
            )
            print(
                f"   Mode: {'Gentle' if config.vmax < 0.5 else 'Normal' if config.vmax < 1.0 else 'Fast'}"
            )
            print("   Safety: Wrist clamped, deadbands active\n")
            print("Ready for pedal input... (Ctrl+C to exit)\n")
        else:
            print("\n[warn] Pedal device not found.")

            if args.test_mode:
                print("\n" + "=" * 60)
                print("TEST MODE - AUTO START")
                print("=" * 60)

                # Countdown
                for i in range(3, 0, -1):
                    print(f"   Starting in {i}...")
                    time.sleep(1.0)

                print("\n🚀 Auto-starting teleop...")

                # Auto sequence
                print("\n[1/2] Capturing baselines...")
                on_center_first()
                time.sleep(1.0)

                print("\n[2/2] Starting teleop...")
                on_center_second()

                print("\n✅ Teleop running!")
                print("   Move GELLO arms to control robots")
                print("   Press Ctrl+C to stop\n")
            else:
                print("\nPedal troubleshooting:")
                print("  1. Check USB: lsusb | grep 0fd9")
                print("  2. Install: pip install hidapi")
                print("  3. Set permissions (Linux):")
                print("     sudo usermod -a -G plugdev $USER")
                print(
                    '     echo \'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0fd9", MODE="0666"\' | sudo tee /etc/udev/rules.d/99-streamdeck.rules'
                )
                print(
                    "     sudo udevadm control --reload-rules && sudo udevadm trigger"
                )
                print("  4. Unplug and replug the pedal")
                print("\nOR use --test-mode to auto-start without pedals:")
                print("  Add --test-mode to your command to test teleop without pedals")
                print("\nPress Ctrl+C to exit.")

        # Keep the main thread alive
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[exit] User interrupted")
            ft.stop()

    finally:
        # Cleanup
        print("\n[cleanup] Shutting down...")

        # Stop position monitor
        if "position_monitor" in locals():
            position_monitor.stop()

        # Stop pedal monitoring
        if pedal_monitor and pedal_monitor.device:
            pedal_monitor.stop_monitoring()

        # Transform display stops automatically with position monitor

        # Disconnect robots
        if left_robot:
            left_robot.disconnect()
        if right_robot:
            right_robot.disconnect()

        print("[cleanup] Done")

    return 0


if __name__ == "__main__":
    sys.exit(main())
