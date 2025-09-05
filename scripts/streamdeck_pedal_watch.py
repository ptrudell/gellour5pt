#!/usr/bin/env python3
"""
DXL→UR joint teleop using servoJ at ~125 Hz (Freedrive OFF).
StreamDeck pedal control with **interrupt-first** flow and fast+smooth tracking.

Pedal Controls (final mapping):
- **Left (4)**  → *Interrupt*: stops URs for external program control
- **Center (5)**
    • 1st tap → capture baselines, gentle params, prep/align (no streaming yet)
    • 2nd tap → start teleop streaming (full-speed params)
- **Right (6)** → stop teleop and return to passive

Tuning:
- Defaults: UR_VMAX=1.4, UR_AMAX=4.0 (override via env)
- LOOKAHEAD=0.15, GAIN=340 (reduced twitch)
- **Jerk-limited motion profile** (per-joint vel+acc clamp) + light EMA
- Smaller deadbands; wrist clamp to avoid chatter
- Dashboard auto-recover if RTDE script not running

Robust pedal decoding:
- Handles multiple HID report layouts seen on StreamDeck Pedal
- Fallback scan + optional --pedal-debug to print raw packets
- Debounce to avoid double-triggers
"""

from __future__ import annotations

import argparse
import math
import os
import socket
import sys
import threading
import time
from contextlib import closing
from enum import Enum
from typing import Any, List, Optional, Sequence, Tuple

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

# --- UR RTDE imports ---
try:
    from rtde_control import RTDEControlInterface  # type: ignore
    from rtde_receive import RTDEReceiveInterface  # type: ignore
except Exception:
    try:
        from ur_rtde import rtde_control, rtde_receive  # type: ignore

        RTDEControlInterface = rtde_control.RTDEControlInterface
        RTDEReceiveInterface = rtde_receive.RTDEReceiveInterface
    except Exception as e:
        print("[err] Could not import UR RTDE modules:", e)
        sys.exit(1)

# --- Dynamixel SDK ---
try:
    from dynamixel_sdk import (  # type: ignore
        COMM_SUCCESS,
        GroupBulkRead,
        PacketHandler,
        PortHandler,
    )
except Exception as e:
    print("[err] dynamixel_sdk import failed:", e)
    sys.exit(1)

# ---------------- Consts ----------------
PROTO = 2.0
ADDR_TORQUE_ENABLE = 64
ADDR_PRESENT_POSITION = 132
TPR = 4096  # ticks per revolution (XL330/most X-series)
CENTER = 2048  # neutral ticks

DT = 0.008  # ~125 Hz
LOOKAHEAD = 0.15  # A bit higher for smoother at speed
GAIN = 340  # Reduced twitch vs 360/450

VMAX = float(os.environ.get("UR_VMAX", "1.4"))  # Faster default
AMAX = float(os.environ.get("UR_AMAX", "4.0"))  # Faster default

# --- Teleop shaping parameters (optimized for minimal lag) ---
EMA_ALPHA = 0.12  # Lower EMA (let profiler do smoothing)
SOFTSTART_T = 0.20  # Even shorter soft-start
DEADBAND_DEG = [1, 1, 1, 1, 1, 2, 1]  # Joints + gripper
SCALE = [1, 1, 1, 1, 1, 1, 1]  # per-joint gain + gripper
# Optional absolute clamps (rad) around the baseline UR pose
CLAMP_RAD = [None, None, None, None, None, 0.8, None]  # Keep wrist tame

# Inactivity handling
INACTIVITY_REBASE_S = 0.3
REBASE_BETA = 0.10
SNAP_EPS_RAD = 0.005
VEL_LIMIT_RAD_S = 6.0  # Per-joint cmd velocity cap
ACC_LIMIT_RAD_S2 = 40.0  # Per-joint cmd acceleration cap

# Mild assist parameters
ASSIST_K = 0.03  # Fine-tuned assist

# Pedal button mapping (StreamDeck pedals)
PEDAL_LEFT = 4  # Interrupt for external program control
PEDAL_CENTER = 5  # 1st tap: prep/align, 2nd tap: start teleop
PEDAL_RIGHT = 6  # Stop teleop and return to passive


# -------------- State Management --------------
class TeleopState(Enum):
    IDLE = "idle"
    PREP = "prep"  # After center-first (baselines captured, ready to align)
    RUNNING = "running"  # After center-second (teleop active)


# -------------- Helpers --------------


def _deg_list_to_rad(lst):
    return [math.radians(x) if x is not None else None for x in lst]


DEADBAND_RAD = _deg_list_to_rad(DEADBAND_DEG)


def _ticks_to_rad(ticks: int, offset_deg: float, sign: int) -> float:
    off_ticks = int(round((offset_deg / 360.0) * TPR))
    return sign * ((ticks - CENTER - off_ticks) * (2 * math.pi / TPR))


def _parse_int_csv(s: str) -> List[int]:
    return [int(x) for x in s.split(",") if x]


def _parse_signs(s: Optional[str], n: int, default: Sequence[int]) -> List[int]:
    if not s:
        return list(default)
    vals = [int(x) for x in s.split(",") if x]
    if len(vals) != n or not all(v in (-1, 1) for v in vals):
        raise ValueError("--*signs must be comma list of ±1 with length matching IDs")
    return vals


def _parse_offsets_deg(s: Optional[str], n: int, default: Sequence[float]) -> List[float]:
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


def _safe_get_q(ur: "URSide") -> Optional[List[float]]:
    """Safely get current joint positions from UR robot."""
    try:
        if not ur.rcv:
            ur.ensure_receive()
        return list(ur.rcv.getActualQ())
    except Exception:
        return None


def _set_gentle_mode():
    """Set gentler control parameters for test movements."""
    global GAIN, VMAX, AMAX
    GAIN_OLD, VMAX_OLD, AMAX_OLD = GAIN, VMAX, AMAX
    GAIN, VMAX, AMAX = 220, 0.35, 0.9  # Slightly faster than before but still gentle
    return GAIN_OLD, VMAX_OLD, AMAX_OLD


def _restore_mode(old):
    """Restore original control parameters."""
    global GAIN, VMAX, AMAX
    GAIN, VMAX, AMAX = old


class DxlBus:
    def __init__(
        self,
        name: str,
        port: str,
        baud: int,
        ids: List[int],
        signs: List[int],
        offsets_deg: List[float],
    ):
        self.name = name
        self.port = port
        self.baud = baud
        self.ids = ids
        self.signs = signs
        self.offsets_deg = offsets_deg
        self.ph: Optional[PortHandler] = None
        self.pk: Optional[PacketHandler] = None
        self.bulk: Optional[GroupBulkRead] = None
        self.bulk_warned = False  # Track if we've warned about bulk read failure
        self.last_read_time = 0.0
        self.last_positions: Optional[List[float]] = None
        self.read_dt = 0.008  # 8 ms cache window to match loop period (125Hz)

    def open(self) -> None:
        self.pk = PacketHandler(PROTO)
        self.ph = PortHandler(self.port)
        ok = self.ph.openPort() and self.ph.setBaudRate(self.baud)
        if not ok:
            raise RuntimeError(f"open/baud failed for {self.name} @ {self.port} {self.baud}")
        print(f"[dxl] {self.name}: open {self.port} @ {self.baud}")

        # Prepare bulk reader for all IDs (reduces latency 7x when it works)
        self.bulk = GroupBulkRead(self.ph, self.pk)
        for i in self.ids:
            # addr 132 len 4 = Present Position
            if not self.bulk.addParam(i, ADDR_PRESENT_POSITION, 4):
                print(f"[dxl] WARN bulk addParam failed id={i}")

    def close(self) -> None:
        if self.ph:
            self.ph.closePort()
            print(f"[dxl] {self.name}: closed")

    def torque(self, on: bool) -> None:
        if not self.ph or not self.pk:
            return
        val = 1 if on else 0
        for i in self.ids:
            rc, er = self.pk.write1ByteTxRx(self.ph, i, ADDR_TORQUE_ENABLE, val)
            if rc != COMM_SUCCESS or er != 0:
                print(f"[dxl] torque {'ON' if on else 'OFF'} fail id={i} rc={rc} er={er}")

    def read_present_positions(self) -> Optional[List[float]]:
        if not self.ph or not self.pk:
            return None

        # Use cached value if recent enough (reduces latency dramatically)
        import time

        now = time.monotonic()
        if self.last_positions and (now - self.last_read_time) < self.read_dt:
            return self.last_positions

        # Try bulk read first (faster)
        if self.bulk is not None:
            if self.bulk.txRxPacket():
                # Bulk read succeeded
                out: List[float] = []
                for j, i in enumerate(self.ids):
                    if self.bulk.isAvailable(i, ADDR_PRESENT_POSITION, 4):
                        pos = self.bulk.getData(i, ADDR_PRESENT_POSITION, 4)
                        out.append(_ticks_to_rad(int(pos), self.offsets_deg[j], self.signs[j]))
                    else:
                        # Partial failure, fall back to individual reads
                        break
                else:
                    # All reads succeeded
                    self.last_positions = out
                    self.last_read_time = now
                    return out

        # Fallback to individual reads (slower but more reliable)
        if not self.bulk_warned:
            print(f"[dxl] {self.name}: Bulk read failed, using individual reads with 8ms cache")
            self.bulk_warned = True

        out: List[float] = []
        for j, i in enumerate(self.ids):
            pos, rc, er = self.pk.read4ByteTxRx(self.ph, i, ADDR_PRESENT_POSITION)
            if rc != COMM_SUCCESS or er != 0:
                # Don't return stale data - surface the error so loop can skip this tick
                print(f"[dxl] {self.name}: Read failed for ID {i}, rc={rc}, er={er}")
                self.last_positions = None
                return None
            out.append(_ticks_to_rad(int(pos), self.offsets_deg[j], self.signs[j]))

        self.last_positions = out
        self.last_read_time = now
        return out


class URSide:
    def __init__(self, host: str):
        self.host = host
        self.rcv: Optional[Any] = None
        self.ctrl: Optional[Any] = None

    def ensure_receive(self) -> None:
        if self.rcv is None:
            self.rcv = RTDEReceiveInterface(self.host)

    def ensure_control(self) -> bool:
        """Simplified control connection - fast single attempt."""
        if self.ctrl is not None:
            try:
                # Test if existing connection is still alive
                self.ctrl.getJointTemp()  # Simple test command
                return True
            except Exception:
                # Connection is dead, need to recreate
                self.ctrl = None

        # Single attempt to connect
        try:
            self.ctrl = RTDEControlInterface(self.host)
            return True
        except Exception as e:
            print(f"[ur] {self.host}: Control connection failed: {e}")
            return False

    def end_teach(self) -> None:
        try:
            if self.ctrl:
                self.ctrl.endTeachMode()
        except Exception:
            pass

    def stop_now(self):
        """Immediately stop the robot with stopJ command."""
        try:
            if self.ctrl:
                self.ctrl.stopJ(AMAX)
        except Exception:
            pass

    def disconnect(self) -> None:
        """Properly disconnect all RTDE interfaces."""
        # Disconnect control interface
        if self.ctrl:
            try:
                self.ctrl.stopJ(AMAX)  # Stop any motion first
                self.ctrl.disconnect()
            except Exception:
                pass
            finally:
                self.ctrl = None

        # Disconnect receive interface
        if self.rcv:
            try:
                self.rcv.disconnect()
            except Exception:
                pass
            finally:
                self.rcv = None


class PedalMonitor:
    """Monitor StreamDeck pedals for teleop control (robust decoder)."""

    def __init__(self, vendor_id: int = 0x0FD9, product_id: int = 0x0086, debug: bool = False):
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
                    print(f"[pedal] Connection attempt {attempt + 1} failed: {e}, retrying...")
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
                    btns.add(PEDAL_LEFT)
                if data[5] == 1:
                    btns.add(PEDAL_CENTER)
                if data[6] == 1:
                    btns.add(PEDAL_RIGHT)
                # If we detected buttons this way, return early
                if btns:
                    return btns

        # Fallback A: bitmask in byte 1 (bits 0..2)
        if not btns and n >= 2:
            m = data[1]
            if m & 0x01:
                btns.add(PEDAL_LEFT)
            if m & 0x02:
                btns.add(PEDAL_CENTER)
            if m & 0x04:
                btns.add(PEDAL_RIGHT)

        # Fallback B: bitmask in byte 4 (bits 0..2) - older format
        if not btns and n >= 5:
            m = data[4]
            if m & 0x01:
                btns.add(PEDAL_LEFT)
            if m & 0x02:
                btns.add(PEDAL_CENTER)
            if m & 0x04:
                btns.add(PEDAL_RIGHT)

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
                        if current != self.last_buttons and (now - self.last_raw_print) > 0.1:
                            # Show raw data but format it better
                            # Map button numbers to names correctly
                            button_names = {4: "LEFT", 5: "CENTER", 6: "RIGHT"}
                            buttons_str = (
                                ", ".join(
                                    [f"{b}({button_names.get(b, '?')})" for b in sorted(current)]
                                )
                                if current
                                else "none"
                            )
                            print(f"[pedal-debug] raw: {list(data[:8])} → buttons: {buttons_str}")
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

            if button == PEDAL_LEFT and self.cb_left:
                print("\n⏸️ [LEFT PEDAL] Interrupt - URs stopped")
                print("   Purpose: Interrupt for external program control")
                print("   State: IDLE (ready for new sequence)")
                self.state = TeleopState.IDLE  # Reset state
                self.last_left_edge_ts = now  # Track for CENTER suppression
                self.cb_left()

            elif button == PEDAL_CENTER:
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

            elif button == PEDAL_RIGHT and self.cb_right:
                print("\n⏹️ [RIGHT PEDAL] Stopping teleop")
                print("   ✓ Streaming stopped")
                print("   ✓ GELLO arms now passive")
                print("   State: IDLE (ready for new sequence)")
                self.cb_right()
                self.state = TeleopState.IDLE

        self.last_buttons = current_buttons


class FollowThread:
    def __init__(
        self,
        left: Optional[Tuple[DxlBus, URSide]],
        right: Optional[Tuple[DxlBus, URSide]],
        left_prog: Optional[str] = None,
        right_prog: Optional[str] = None,
    ):
        self.left = left
        self.right = right
        self.left_prog = left_prog
        self.right_prog = right_prog
        self._stop = threading.Event()
        self._th: Optional[threading.Thread] = None

        # baselines: DXL (rad) and UR (rad) captured on center-first
        self.q0_dxl_L: Optional[List[float]] = None
        self.q0_ur_L: Optional[List[float]] = None
        self.q0_dxl_R: Optional[List[float]] = None
        self.q0_ur_R: Optional[List[float]] = None

        # softstart timestamps
        self.t0_L: Optional[float] = None
        self.t0_R: Optional[float] = None

        # Profiled targets and velocities
        self.y_L: Optional[List[float]] = None
        self.v_L: Optional[List[float]] = None  # Velocity tracking for left
        self.y_R: Optional[List[float]] = None
        self.v_R: Optional[List[float]] = None  # Velocity tracking for right

        # inactivity tracking
        self.last_qL: Optional[List[float]] = None
        self.last_qR: Optional[List[float]] = None
        self.last_move_ts_L: float = time.monotonic()
        self.last_move_ts_R: float = time.monotonic()

    def _apply_deadband_scale(self, dq: List[float]) -> List[float]:
        """Apply per-joint deadband and scaling."""
        out = []
        for j, v in enumerate(dq):
            db = DEADBAND_RAD[j] if j < len(DEADBAND_RAD) else 0.0
            if abs(v) < (db or 0.0):
                out.append(0.0)
            else:
                sc = SCALE[j] if j < len(SCALE) else 1.0
                out.append(v * sc)
        return out

    def _soft_ramp(self, t0: Optional[float]) -> float:
        """Calculate soft-start ramp factor (0 to 1)."""
        if not t0:
            return 1.0
        dt = max(0.0, time.monotonic() - t0)
        return min(1.0, dt / max(1e-6, SOFTSTART_T))

    def _clamp_about(self, base: List[float], q: List[float]) -> List[float]:
        """Optional absolute clamps around baseline UR pose."""
        if not CLAMP_RAD or all(c is None for c in CLAMP_RAD):
            return q
        out = []
        for j, val in enumerate(q):
            c = CLAMP_RAD[j] if j < len(CLAMP_RAD) else None
            if c is None:
                out.append(val)
            else:
                lo = base[j] - c
                hi = base[j] + c
                out.append(min(max(val, lo), hi))
        return out

    def _profile(
        self, prev_y: Optional[List[float]], prev_v: Optional[List[float]], target: List[float]
    ) -> Tuple[List[float], List[float]]:
        """Second-order motion profiling per joint (vel + acc limits) for smoothness."""
        VMAX_CMD = VEL_LIMIT_RAD_S
        ACC = ACC_LIMIT_RAD_S2

        if prev_y is None:
            prev_y = list(target)
        if prev_v is None:
            prev_v = [0.0] * len(target)

        y_new: List[float] = []
        v_new: List[float] = []

        for j, qt in enumerate(target):
            yj = prev_y[j]
            vj = prev_v[j]

            # Desired velocity to reach target
            v_des = (qt - yj) / DT

            # Apply acceleration limit
            dv = max(-ACC * DT, min(ACC * DT, v_des - vj))
            vj = vj + dv

            # Apply velocity limit
            if vj > VMAX_CMD:
                vj = VMAX_CMD
            if vj < -VMAX_CMD:
                vj = -VMAX_CMD

            # Update position
            yj = yj + vj * DT

            y_new.append(yj)
            v_new.append(vj)

        return y_new, v_new

    def start(self) -> None:
        if self._th and self._th.is_alive():
            return
        self._stop.clear()
        self._th = threading.Thread(target=self._run, daemon=True, name="follow125")
        self._th.start()

    def stop(self) -> None:
        self._stop.set()
        if self._th:
            self._th.join(timeout=1.0)
        # gentle stop on URs
        for pair in (self.left, self.right):
            if pair and pair[1].ctrl:
                try:
                    pair[1].ctrl.stopJ(AMAX)
                except Exception:
                    pass

    def _ensure_ur_ready(self, ur: URSide) -> bool:
        """Ensure UR is ready for control - fast and simple."""
        ur.ensure_receive()
        if not ur.ensure_control():
            print(f"[follow] {ur.host}: RTDE control not available")
            return False
        if ur.ctrl:
            ur.end_teach()
            return True
        return False

    def _run(self) -> None:
        # Try to bump process niceness (Linux); ignore if not permitted
        try:
            import os

            os.nice(-5)
        except Exception:
            pass

        # Prepare URs first; don't start loop if neither is ready
        ready_any = False
        for pair in (self.left, self.right):
            if pair and self._ensure_ur_ready(pair[1]):
                ready_any = True

        if not ready_any:
            print("[follow] No UR control available; not starting streaming")
            return

        error_count = {"left": 0, "right": 0}
        max_errors = 2  # Stop quickly for safety if control is lost

        # Fixed-rate scheduler using perf_counter
        import time as _t

        next_t = _t.perf_counter()

        while not self._stop.is_set():
            # LEFT side with relative + smooth control
            if self.left:
                busL, urL = self.left
                qL = busL.read_present_positions()
                if qL and urL.ctrl:
                    # Baseline lazy-init if user didn't press center-first
                    if self.q0_dxl_L is None or self.q0_ur_L is None:
                        self.q0_dxl_L = list(qL)
                        qs = _safe_get_q(urL)
                        if qs:
                            self.q0_ur_L = list(qs)
                        else:
                            self.q0_ur_L = [0.0] * len(qL)  # Fallback
                        self.t0_L = time.monotonic()

                    # --- motion detection for LEFT ---
                    now = time.monotonic()
                    moved = False
                    if self.last_qL is not None:
                        # max per-joint absolute change since last cycle
                        max_step = max(abs(a - b) for a, b in zip(qL, self.last_qL))
                        if max_step > 0.0025:  # More sensitive motion detection
                            self.last_move_ts_L = now
                            moved = True
                    self.last_qL = list(qL)

                    # Inactivity re-baseline to dissolve stuck offsets
                    if not moved and (now - self.last_move_ts_L) > INACTIVITY_REBASE_S:
                        # pull DXL baseline a bit toward current reading
                        self.q0_dxl_L = [
                            (1.0 - REBASE_BETA) * q0 + REBASE_BETA * q
                            for q0, q in zip(self.q0_dxl_L, qL)
                        ]

                    # Calculate relative delta from baseline
                    dq = [ql - q0 for ql, q0 in zip(qL, self.q0_dxl_L)]
                    dq = self._apply_deadband_scale(dq)

                    # Absolute target = UR baseline + relative delta
                    q_target = [q0u + d for q0u, d in zip(self.q0_ur_L, dq)]

                    # Optional clamp
                    q_target = self._clamp_about(self.q0_ur_L, q_target)

                    # Snap tiny commands to baseline to avoid slow creep
                    q_target = [
                        q0u if abs(qt - q0u) < SNAP_EPS_RAD else qt
                        for q0u, qt in zip(self.q0_ur_L, q_target)
                    ]

                    # Mild bias (assist) toward baseline when near still
                    q_target = [
                        qt + ASSIST_K * (q0u - qt) for q0u, qt in zip(self.q0_ur_L, q_target)
                    ]

                    # Velocity limit of the **command** to prevent runaway spikes
                    if self.y_L is not None:
                        max_step = VEL_LIMIT_RAD_S * DT
                        q_target = [
                            y + max(-max_step, min(max_step, qt - y))
                            for y, qt in zip(self.y_L, q_target)
                        ]

                    # Softstart
                    s = self._soft_ramp(self.t0_L)
                    q_target = [q0u + s * (qt - q0u) for q0u, qt in zip(self.q0_ur_L, q_target)]

                    # Jerk-limited motion profile (smooth + fast)
                    self.y_L, self.v_L = self._profile(self.y_L, self.v_L, q_target)

                    try:
                        # Only send first 6 joints to UR (exclude gripper)
                        ur_joints = self.y_L[:6] if len(self.y_L) > 6 else self.y_L
                        urL.ctrl.servoJ(ur_joints, VMAX, AMAX, DT, LOOKAHEAD, GAIN)
                        error_count["left"] = 0  # Reset error count on success
                    except Exception as e:
                        msg = str(e).lower()
                        if "control script is not running" in msg:
                            error_count["left"] += 1
                            if error_count["left"] == 1:
                                print("\n⚠️  LEFT UR: control script not running")
                                print(
                                    "     Please ensure ExternalControl.urp is PLAYING on pendant"
                                )
                            # Stop after max attempts
                            if error_count["left"] >= max_errors:
                                print("   Too many errors - stopping teleop for safety")
                                self._stop.set()
                                return
                        else:
                            print(f"[follow] L servoJ error: {e}")

            # RIGHT side with relative + smooth control
            if self.right:
                busR, urR = self.right
                qR = busR.read_present_positions()
                if qR and urR.ctrl:
                    # Baseline lazy-init if user didn't press center-first
                    if self.q0_dxl_R is None or self.q0_ur_R is None:
                        self.q0_dxl_R = list(qR)
                        qs = _safe_get_q(urR)
                        if qs:
                            self.q0_ur_R = list(qs)
                        else:
                            self.q0_ur_R = [0.0] * len(qR)  # Fallback
                        self.t0_R = time.monotonic()

                    # --- motion detection for RIGHT ---
                    now = time.monotonic()
                    moved = False
                    if self.last_qR is not None:
                        # max per-joint absolute change since last cycle
                        max_step = max(abs(a - b) for a, b in zip(qR, self.last_qR))
                        if max_step > 0.0025:  # More sensitive motion detection
                            self.last_move_ts_R = now
                            moved = True
                    self.last_qR = list(qR)

                    # Inactivity re-baseline to dissolve stuck offsets
                    if not moved and (now - self.last_move_ts_R) > INACTIVITY_REBASE_S:
                        # pull DXL baseline a bit toward current reading
                        self.q0_dxl_R = [
                            (1.0 - REBASE_BETA) * q0 + REBASE_BETA * q
                            for q0, q in zip(self.q0_dxl_R, qR)
                        ]

                    # Calculate relative delta from baseline
                    dq = [qr - q0 for qr, q0 in zip(qR, self.q0_dxl_R)]
                    dq = self._apply_deadband_scale(dq)

                    # Absolute target = UR baseline + relative delta
                    q_target = [q0u + d for q0u, d in zip(self.q0_ur_R, dq)]

                    # Optional clamp
                    q_target = self._clamp_about(self.q0_ur_R, q_target)

                    # Snap tiny commands to baseline to avoid slow creep
                    q_target = [
                        q0u if abs(qt - q0u) < SNAP_EPS_RAD else qt
                        for q0u, qt in zip(self.q0_ur_R, q_target)
                    ]

                    # Mild bias (assist) toward baseline when near still
                    q_target = [
                        qt + ASSIST_K * (q0u - qt) for q0u, qt in zip(self.q0_ur_R, q_target)
                    ]

                    # Velocity limit of the **command** to prevent runaway spikes
                    if self.y_R is not None:
                        max_step = VEL_LIMIT_RAD_S * DT
                        q_target = [
                            y + max(-max_step, min(max_step, qt - y))
                            for y, qt in zip(self.y_R, q_target)
                        ]

                    # Softstart
                    s = self._soft_ramp(self.t0_R)
                    q_target = [q0u + s * (qt - q0u) for q0u, qt in zip(self.q0_ur_R, q_target)]

                    # Jerk-limited motion profile (smooth + fast)
                    self.y_R, self.v_R = self._profile(self.y_R, self.v_R, q_target)

                    try:
                        # Only send first 6 joints to UR (exclude gripper)
                        ur_joints = self.y_R[:6] if len(self.y_R) > 6 else self.y_R
                        urR.ctrl.servoJ(ur_joints, VMAX, AMAX, DT, LOOKAHEAD, GAIN)
                        error_count["right"] = 0  # Reset error count on success
                    except Exception as e:
                        msg = str(e).lower()
                        if "control script is not running" in msg:
                            error_count["right"] += 1
                            if error_count["right"] == 1:
                                print("\n⚠️  RIGHT UR: control script not running")
                                print(
                                    "     Please ensure ExternalControl.urp is PLAYING on pendant"
                                )
                            # Stop after max attempts
                            if error_count["right"] >= max_errors:
                                print("   Too many errors - stopping teleop for safety")
                                self._stop.set()
                                return
                        else:
                            print(f"[follow] R servoJ error: {e}")

            # Sleep exactly to the next tick (accounts for compute time)
            next_t += DT
            now = _t.perf_counter()
            delay = next_t - now
            if delay > 0:
                _t.sleep(delay)
            else:
                # Overrun detected
                over_ms = -delay * 1000

                # Major overrun (>100ms) - likely DXL read delay
                if over_ms > 100:
                    # Realign immediately to current time + DT
                    next_t = now + DT

                    # Only print warning occasionally to avoid spam
                    if int(now * 4) % 4 == 0:  # ~1 per second
                        print(f"[loop] Major overrun {over_ms:.1f}ms - realigning")

                        # If consistent major overruns, suggest fixes
                        if over_ms > 200:
                            error_count.setdefault("overrun", 0)
                            error_count["overrun"] += 1
                            if error_count["overrun"] == 10:
                                print("\n⚠️  Consistent timing issues detected!")
                                print("   This may cause jerky motion.")
                                print("   Possible fixes:")
                                print("   1. Check DXL servo connections")
                                print("   2. Reduce servo count temporarily")
                                print("   3. Check USB latency/interference")
                                print("")
                else:
                    # Minor overrun - try to catch up gradually
                    next_t = now + (DT * 0.5)  # Partial skip to recover


def _build_bus(
    name: str,
    port: Optional[str],
    baud: int,
    ids: List[int],
    signs: List[int],
    offsets_deg: List[float],
) -> Optional[DxlBus]:
    if not port or not ids:
        return None
    bus = DxlBus(name=name, port=port, baud=baud, ids=ids, signs=signs, offsets_deg=offsets_deg)
    bus.open()
    return bus


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="DXL→UR servoJ teleop (fast+smooth) + pedals + grippers"
    )
    ap.add_argument("--ur-left", type=str, default=None, help="UR IP for LEFT arm")
    ap.add_argument("--ur-right", type=str, default=None, help="UR IP for RIGHT arm")
    ap.add_argument(
        "--left-port", type=str, default=None, help="/dev/serial/by-id/... for LEFT DXL"
    )
    ap.add_argument(
        "--right-port", type=str, default=None, help="/dev/serial/by-id/... for RIGHT DXL"
    )
    ap.add_argument(
        "--left-ids",
        type=str,
        default=None,
        help="Comma IDs for LEFT (e.g., 1,2,3,4,5,6,7 with gripper)",
    )
    ap.add_argument(
        "--right-ids",
        type=str,
        default=None,
        help="Comma IDs for RIGHT (e.g., 10,11,12,13,14,15,16 with gripper)",
    )
    ap.add_argument(
        "--left-signs",
        type=str,
        default=None,
        help="Comma ±1 per joint (default 1,1,-1,1,1,1,1 with gripper)",
    )
    ap.add_argument(
        "--right-signs",
        type=str,
        default=None,
        help="Comma ±1 per joint (default 1,1,-1,1,1,1,1 with gripper)",
    )
    ap.add_argument(
        "--left-offsets-deg", type=str, default=None, help="Comma offsets(deg) per joint"
    )
    ap.add_argument(
        "--right-offsets-deg", type=str, default=None, help="Comma offsets(deg) per joint"
    )
    ap.add_argument("--baud", type=int, default=1_000_000)
    ap.add_argument(
        "--joints-passive", action="store_true", help="Leave DXL joint chains torque OFF (exo free)"
    )
    ap.add_argument(
        "--torque-on",
        action="store_true",
        help="Force torque ON for DXL chains (overrides --joints-passive)",
    )
    ap.add_argument(
        "--pedal-debug",
        action="store_true",
        help="Print raw pedal HID packets + decoded buttons",
    )
    ap.add_argument(
        "--dxl-test",
        action="store_true",
        help="Test DXL servos and exit (diagnostic mode)",
    )
    ap.add_argument(
        "--ur-left-program",
        type=str,
        default="/programs/ExternalControl.urp",
        help="Path to .urp program on LEFT robot (default: /programs/ExternalControl.urp)",
    )
    ap.add_argument(
        "--ur-right-program",
        type=str,
        default="/programs/ExternalControl.urp",
        help="Path to .urp program on RIGHT robot (default: /programs/ExternalControl.urp)",
    )
    ap.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Do not send any UR Dashboard commands (no stop/power/play/load)",
    )
    ap.add_argument(
        "--test-mode",
        action="store_true",
        help="Test mode: auto-start teleop after 5 seconds if no pedals",
    )

    args = ap.parse_args(argv)

    # Defaults for signs/offsets: common pattern from your config samples
    # --- Parse IDs (robust: default if omitted) ---
    left_ids = _parse_int_csv(args.left_ids) if args.left_ids else []
    right_ids = _parse_int_csv(args.right_ids) if args.right_ids else []

    if args.left_port and not left_ids:
        left_ids = [1, 2, 3, 4, 5, 6, 7]  # Including gripper ID 7
    if args.right_port and not right_ids:
        right_ids = [10, 11, 12, 13, 14, 15, 16]  # Including gripper ID 16

    # Add optional ID override via environment variables for debugging
    if os.environ.get("LEFT_IDS"):
        left_ids = _parse_int_csv(os.environ["LEFT_IDS"])
        print(f"[override] LEFT IDs from env: {left_ids}")
    if os.environ.get("RIGHT_IDS"):
        right_ids = _parse_int_csv(os.environ["RIGHT_IDS"])
        print(f"[override] RIGHT IDs from env: {right_ids}")

    # Defaults for signs/offsets sized to the IDs we now have
    default_signs = [1, 1, -1, 1, 1, 1, 1]  # Added 7th for gripper
    def_signs_L = (default_signs + [1] * 7)[: len(left_ids)] if left_ids else []
    def_signs_R = (default_signs + [1] * 7)[: len(right_ids)] if right_ids else []
    def_offs_L = [0.0] * len(left_ids)
    def_offs_R = [0.0] * len(right_ids)

    left_signs = _parse_signs(args.left_signs, len(left_ids), def_signs_L) if left_ids else []
    right_signs = _parse_signs(args.right_signs, len(right_ids), def_signs_R) if right_ids else []
    left_offs = (
        _parse_offsets_deg(args.left_offsets_deg, len(left_ids), def_offs_L) if left_ids else []
    )
    right_offs = (
        _parse_offsets_deg(args.right_offsets_deg, len(right_ids), def_offs_R) if right_ids else []
    )

    # Build buses
    busL = (
        _build_bus("LEFT", args.left_port, args.baud, left_ids, left_signs, left_offs)
        if args.left_port
        else None
    )
    busR = (
        _build_bus("RIGHT", args.right_port, args.baud, right_ids, right_signs, right_offs)
        if args.right_port
        else None
    )

    # UR
    urL = URSide(args.ur_left) if args.ur_left else None
    urR = URSide(args.ur_right) if args.ur_right else None

    if not (busL or busR):
        print("[exit] No DXL buses configured; provide --left-port/--right-port and IDs")
        return 2

    # DXL diagnostic test mode
    if args.dxl_test:
        print("\n" + "=" * 60)
        print("DXL SERVO DIAGNOSTIC TEST")
        print("=" * 60)

        test_passed = False

        if busL:
            print(f"\n[TEST] LEFT arm - Port: {args.left_port}")
            print(f"       IDs to test: {left_ids}")
            print(f"       Baud rate: {args.baud}")

            # Try reading multiple times
            for attempt in range(3):
                positions = busL.read_present_positions()
                if positions:
                    print("       ✓ SUCCESS! Positions:")
                    for id_val, pos in zip(left_ids, positions):
                        print(f"         ID {id_val}: {pos:.3f} rad ({math.degrees(pos):.1f}°)")
                    test_passed = True
                    break
                else:
                    print(f"       Attempt {attempt + 1}/3: No response")
                    time.sleep(0.5)

            if not positions:
                print("       ✗ FAILED - No response from servos after 3 attempts")
                print("\n       Troubleshooting:")
                print("       1. Check servo power (5V for XL330, LEDs should be on)")
                print("       2. Try different baud rate:")
                print(f"          Currently using: {args.baud}")
                print(f"          Try: --baud {1000000 if args.baud == 57600 else 57600}")
                print("       3. Verify USB connection: ls -la /dev/serial/by-id/")
                print("       4. Check servo IDs (default: 1-7)")
                print("       5. Test single servo: LEFT_IDS=1")
                print("       6. Check wiring: Data+ and Data- connections")

        if busR:
            print(f"\n[TEST] RIGHT arm - Port: {args.right_port}")
            print(f"       IDs to test: {right_ids}")
            print(f"       Baud rate: {args.baud}")

            # Try reading multiple times
            for attempt in range(3):
                positions = busR.read_present_positions()
                if positions:
                    print("       ✓ SUCCESS! Positions:")
                    for id_val, pos in zip(right_ids, positions):
                        print(f"         ID {id_val}: {pos:.3f} rad ({math.degrees(pos):.1f}°)")
                    test_passed = True
                    break
                else:
                    print(f"       Attempt {attempt + 1}/3: No response")
                    time.sleep(0.5)

            if not positions:
                print("       ✗ FAILED - No response from servos after 3 attempts")
                print("\n       Troubleshooting:")
                print("       1. Check servo power (5V for XL330, LEDs should be on)")
                print("       2. Try different baud rate:")
                print(f"          Currently using: {args.baud}")
                print(f"          Try: --baud {1000000 if args.baud == 57600 else 57600}")
                print("       3. Verify USB connection: ls -la /dev/serial/by-id/")
                print("       4. Check servo IDs (default: 10-16)")
                print("       5. Test single servo: RIGHT_IDS=10")
                print("       6. Check wiring: Data+ and Data- connections")

        print("\n" + "=" * 60)
        if test_passed:
            print("✓ At least some servos are responding")
            print("  You can proceed with teleop")
        else:
            print("✗ No servos responding - fix hardware issues first")
        print("=" * 60)

        if busL:
            busL.close()
        if busR:
            busR.close()
        return 0

    if not (urL or urR):
        print("[exit] No UR IPs provided; use --ur-left/--ur-right")
        return 2

    # Print startup diagnostics
    print("\n" + "=" * 60)
    print("TELEOP STARTUP DIAGNOSTICS")
    print("=" * 60)
    print(f"Speed Limits: VMAX={VMAX:.2f} rad/s, AMAX={AMAX:.1f} rad/s²")
    if VMAX < 0.1:
        print("  → SAFE MODE: Very slow for testing")
    elif VMAX < 0.5:
        print("  → GENTLE MODE: Good for initial testing")
    else:
        print("  → NORMAL MODE: Full speed operation")

    print("\nDXL Configuration:")
    if busL:
        print(f"  LEFT:  {args.left_port}")
        print(f"         IDs: {left_ids}, Baud: {args.baud}")
    if busR:
        print(f"  RIGHT: {args.right_port}")
        print(f"         IDs: {right_ids}, Baud: {args.baud}")

    print("\nUR Configuration:")
    if urL:
        print(f"  LEFT:  {args.ur_left} → {args.ur_left_program}")
    if urR:
        print(f"  RIGHT: {args.ur_right} → {args.ur_right_program}")

    print("\nControl Mode:")
    print(f"  Joints: {'PASSIVE (torque OFF)' if args.joints_passive else 'ACTIVE (torque ON)'}")
    print(f"  Dashboard: {'DISABLED' if args.no_dashboard else 'ENABLED'}")
    print("=" * 60 + "\n")

    try:
        # Optional torque setup (default passive)
        if args.torque_on and not args.joints_passive:
            if busL:
                busL.torque(True)
            if busR:
                busR.torque(True)
        else:
            print("[dxl] joints-passive: leaving joint chains torque OFF")

        # Prepare UR control/receive and nudge robots toward READY
        for side, ur in [("LEFT", urL), ("RIGHT", urR)]:
            if ur:
                ur.ensure_receive()
                print(f"[init] Preparing UR {side} at {ur.host}...")
                if not args.no_dashboard:
                    # Only send dashboard commands if allowed
                    _dashboard_play(ur.host)
                else:
                    print(f"[dash] {ur.host}: Skipping dashboard commands (--no-dashboard)")

        ft = FollowThread(
            left=(busL, urL) if (busL and urL) else None,
            right=(busR, urR) if (busR and urR) else None,
            left_prog=args.ur_left_program,
            right_prog=args.ur_right_program,
        )
        ft.no_dashboard = args.no_dashboard  # Pass flag to thread

        # Set up pedal monitoring
        pedal_monitor = PedalMonitor(debug=args.pedal_debug)

        # Track saved mode for gentle -> full transition
        _saved_mode = None

        # Define pedal callbacks
        def on_left_interrupt():
            """INTERRUPT: Stop URs for external program control."""
            # First stop the follow thread if running
            if ft._th and ft._th.is_alive():
                ft.stop()

            # Stop and disconnect both URs cleanly
            for ur in (urL, urR):
                if ur:
                    ur.stop_now()
                    # Brief pause to ensure stop command is processed
                    time.sleep(0.05)
                    # Disconnect to free up for external control
                    ur.disconnect()

            # Clear the baselines to force recapture on next use
            ft.q0_dxl_L = None
            ft.q0_ur_L = None
            ft.q0_dxl_R = None
            ft.q0_ur_R = None

        def on_center_first():
            """PREP: capture baselines, gentle mode, no streaming yet."""
            nonlocal _saved_mode
            _saved_mode = _set_gentle_mode()
            # Capture baselines
            if ft.left:
                bus, ur = ft.left
                # Try multiple times for DXL read
                for retry in range(3):
                    ft.q0_dxl_L = bus.read_present_positions()
                    if ft.q0_dxl_L:
                        break
                    time.sleep(0.1)
                    if retry > 0:
                        print(f"   Retrying LEFT DXL read... ({retry + 1}/3)")

                if ur:
                    ft.q0_ur_L = _safe_get_q(ur)
                    ft.t0_L = time.monotonic()
                n_joints = len(ft.q0_dxl_L) if ft.q0_dxl_L else 0
                expected = len(left_ids)
                if n_joints > 0:
                    print(f"   ✓ LEFT arm: {n_joints}/{expected} joints captured")
                    if n_joints < expected:
                        print(f"      Warning: Expected {expected} joints, got {n_joints}")
                else:
                    print("   ✗ LEFT arm: Failed to read positions - check DXL power/connection")
                    print("      Quick fixes:")
                    print("      1. Check servo power (5V for XL330, check LED)")
                    print("      2. Try --baud 57600 if using 1000000")
                    print("      3. Test single servo: LEFT_IDS=1")
                    print("      4. Verify port: ls -la /dev/serial/by-id/")

            if ft.right:
                bus, ur = ft.right
                # Try multiple times for DXL read
                for retry in range(3):
                    ft.q0_dxl_R = bus.read_present_positions()
                    if ft.q0_dxl_R:
                        break
                    time.sleep(0.1)
                    if retry > 0:
                        print(f"   Retrying RIGHT DXL read... ({retry + 1}/3)")

                if ur:
                    ft.q0_ur_R = _safe_get_q(ur)
                    ft.t0_R = time.monotonic()
                n_joints = len(ft.q0_dxl_R) if ft.q0_dxl_R else 0
                expected = len(right_ids)
                if n_joints > 0:
                    print(f"   ✓ RIGHT arm: {n_joints}/{expected} joints captured")
                    if n_joints < expected:
                        print(f"      Warning: Expected {expected} joints, got {n_joints}")
                else:
                    print("   ✗ RIGHT arm: Failed to read positions - check DXL power/connection")
                    print("      Quick fixes:")
                    print("      1. Check servo power (5V for XL330, check LED)")
                    print("      2. Try --baud 57600 if using 1000000")
                    print("      3. Test single servo: RIGHT_IDS=10")
                    print("      4. Verify port: ls -la /dev/serial/by-id/")

        def on_center_second():
            """START: restore full params and begin streaming."""
            nonlocal _saved_mode
            if _saved_mode is not None:
                _restore_mode(_saved_mode)
                _saved_mode = None

            # Quick check that we have DXL data
            dxl_ok = False
            if ft.q0_dxl_L and len(ft.q0_dxl_L) > 0:
                dxl_ok = True
                print(f"   ✓ LEFT DXL: {len(ft.q0_dxl_L)} joints ready")
            if ft.q0_dxl_R and len(ft.q0_dxl_R) > 0:
                dxl_ok = True
                print(f"   ✓ RIGHT DXL: {len(ft.q0_dxl_R)} joints ready")

            if not dxl_ok:
                print("\n⚠️  ERROR: No DXL servos responding!")
                print("   Cannot start teleop without servo feedback.")
                print("   ")
                print("   SOLUTION:")
                print("   1. Check servo power (5V supply, LEDs should be on)")
                print("   2. Try different baud rate:")
                print("      --baud 1000000 (default for new servos)")
                print("      --baud 57600 (common alternative)")
                print("   3. Check USB connections and ports")
                print("   4. Test with single servo: LEFT_IDS=1 or RIGHT_IDS=10")
                return

            print("\n✅ Starting teleoperation!")
            ft.start()

        def on_right_stop():
            """STOP: Sequential shutdown - stop teleop, clear connections, return to autonomous mode."""
            print("   🔄 Starting sequential shutdown...")

            # Step 1: Stop the streaming thread first
            print("   [1/5] Stopping teleop streaming...")
            ft.stop()
            time.sleep(0.1)  # Allow thread to fully stop

            # Step 2: Immediately disconnect RTDE control interfaces
            print("   [2/5] Disconnecting RTDE control interfaces...")
            for ur in (urL, urR):
                if ur and ur.ctrl:
                    try:
                        ur.ctrl.stopJ(AMAX)  # Stop any motion
                        ur.ctrl.disconnect()  # Disconnect cleanly
                        ur.ctrl = None  # Clear the reference
                        print(f"        ✓ {ur.host} control disconnected")
                    except Exception as e:
                        print(f"        ⚠️ {ur.host} disconnect error: {e}")
                        ur.ctrl = None

            # Step 3: Clear RTDE receive interfaces
            print("   [3/5] Clearing RTDE receive interfaces...")
            for ur in (urL, urR):
                if ur and ur.rcv:
                    try:
                        ur.rcv.disconnect()
                        ur.rcv = None
                        print(f"        ✓ {ur.host} receive disconnected")
                    except Exception:
                        ur.rcv = None

            # Step 4: Return DXL to passive mode
            print("   [4/5] Setting GELLO arms to passive...")
            for bus in (busL, busR):
                if bus:
                    bus.torque(False)

            # Step 5: Clear any lingering connections and return to autonomous mode
            print("   [5/5] Returning control to autonomous mode...")
            robot_hosts = []
            if urL:
                robot_hosts.append(urL.host)
            if urR:
                robot_hosts.append(urR.host)

            # Extra connection clearing step
            if robot_hosts:
                time.sleep(0.2)  # Brief pause before clearing
                success = clear_robots_quietly(robot_hosts)
                if not success:
                    print("        ⚠️ Some connections may need manual clearing")

            # Prepare robots for autonomous control
            if robot_hosts:
                for ur_host in robot_hosts:
                    if _prepare_for_autonomous(ur_host, args.no_dashboard):
                        print(f"        ✓ {ur_host} ready for autonomous control")
                    else:
                        print(f"        ⚠️ {ur_host} may need manual intervention")

            # Reset state machine to IDLE
            pedal_monitor.state = TeleopState.IDLE

            print("   ✅ Shutdown complete - ready for autonomous operation")

        # Assign callbacks
        pedal_monitor.cb_left = on_left_interrupt
        pedal_monitor.cb_center_1 = on_center_first
        pedal_monitor.cb_center_2 = on_center_second
        pedal_monitor.cb_right = on_right_stop

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
            print(f"   Speed: VMAX={VMAX:.2f} rad/s, AMAX={AMAX:.1f} rad/s²")
            print(f"   Mode: {'Gentle' if VMAX < 0.5 else 'Normal' if VMAX < 1.0 else 'Fast'}")
            print("   Safety: Wrist clamped, deadbands active\n")
            print("Ready for pedal input... (Ctrl+C to exit)\n")
        else:
            print("\n[warn] Pedal device not found.")

            if args.test_mode:
                print("\n" + "=" * 60)
                print("TEST MODE ACTIVE - NO PEDALS")
                print("=" * 60)
                print("\n⚠️  AUTO-START SEQUENCE:")
                print("   Will automatically start teleop in 5 seconds...")
                print("   This allows testing without pedals")
                print("   Press Ctrl+C to cancel\n")

                # Countdown
                for i in range(5, 0, -1):
                    print(f"   Starting in {i}...")
                    time.sleep(1.0)

                print("\n🚀 Starting automatic test sequence...")

                # Simulate CENTER pedal first tap (capture baselines)
                print("\n[TEST] Step 1: Capturing baselines...")
                on_center_first()
                time.sleep(2.0)

                # Simulate CENTER pedal second tap (start teleop)
                print("\n[TEST] Step 2: Starting teleop...")
                on_center_second()

                print("\n[TEST] Teleop should now be running!")
                print("       Move GELLO arms to control UR robots")
                print("       Press Ctrl+C to stop\n")
            else:
                print("\nPedal troubleshooting:")
                print("  1. Check USB: lsusb | grep 0fd9")
                print("  2. Install: pip install hidapi")
                print("  3. Set permissions (Linux):")
                print("     sudo usermod -a -G plugdev $USER")
                print(
                    '     echo \'SUBSYSTEM=="hidraw", ATTRS{idVendor}=="0fd9", MODE="0666"\' | sudo tee /etc/udev/rules.d/99-streamdeck.rules'
                )
                print("     sudo udevadm control --reload-rules && sudo udevadm trigger")
                print("  4. Unplug and replug the pedal")
                print("\nOR use --test-mode to auto-start without pedals:")
                print("  Add --test-mode to your command to test teleop without pedals")
                print("\nPress Ctrl+C to exit.")

        # Keep the main thread alive
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[exit] Shutting down...")
            ft.stop()
            if pedal_monitor.device:
                pedal_monitor.stop_monitoring()

    finally:
        # Clean down DXL
        if busL:
            busL.close()
        if busR:
            busR.close()

        # Properly disconnect UR connections using the new method
        if urL:
            urL.disconnect()
        if urR:
            urR.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
