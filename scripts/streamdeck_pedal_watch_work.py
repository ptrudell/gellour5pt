#!/usr/bin/env python3
"""
DXL→UR joint teleop using servoJ at ~125 Hz (Freedrive OFF).
Optimized version with faster RTDE connection and streamlined pedal control.

Pedal Controls:
- Left (4): Interrupt for external program control
- Center (5): 1st tap = capture baselines (gentle), 2nd tap = start teleop (full speed)
- Right (6): Stop teleop and return to passive

Key optimizations:
- Simplified RTDE connection (no URScript fallback that causes conflicts)
- Faster DXL reads with bulk operations and caching
- Streamlined connection checking
- Removed problematic auto-recovery attempts
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
TPR = 4096  # ticks per revolution
CENTER = 2048  # neutral ticks

DT = 0.008  # ~125 Hz
LOOKAHEAD = 0.15
GAIN = 340

VMAX = float(os.environ.get("UR_VMAX", "1.4"))
AMAX = float(os.environ.get("UR_AMAX", "4.0"))

# --- Teleop shaping parameters ---
EMA_ALPHA = 0.12  # Lower EMA for smoother motion
SOFTSTART_T = 0.20  # Short soft-start
DEADBAND_DEG = [1, 1, 1, 1, 1, 2, 1]  # Joints + gripper
SCALE = [1, 1, 1, 1, 1, 1, 1]  # per-joint gain + gripper
CLAMP_RAD = [None, None, None, None, None, 0.8, None]  # Wrist clamp

# Inactivity handling
INACTIVITY_REBASE_S = 0.3
REBASE_BETA = 0.10
SNAP_EPS_RAD = 0.005
VEL_LIMIT_RAD_S = 6.0
ACC_LIMIT_RAD_S2 = 40.0

# Mild assist
ASSIST_K = 0.03

# Pedal button mapping
PEDAL_LEFT = 4
PEDAL_CENTER = 5
PEDAL_RIGHT = 6


# -------------- State Management --------------
class TeleopState(Enum):
    IDLE = "idle"
    PREP = "prep"
    RUNNING = "running"


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
    GAIN, VMAX, AMAX = 220, 0.35, 0.9
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
        self.bulk_warned = False
        self.last_read_time = 0.0
        self.last_positions: Optional[List[float]] = None
        self.read_dt = 0.008  # 8 ms cache window

    def open(self) -> None:
        self.pk = PacketHandler(PROTO)
        self.ph = PortHandler(self.port)
        ok = self.ph.openPort() and self.ph.setBaudRate(self.baud)
        if not ok:
            raise RuntimeError(f"open/baud failed for {self.name} @ {self.port} {self.baud}")
        print(f"[dxl] {self.name}: open {self.port} @ {self.baud}")

        # Prepare bulk reader
        self.bulk = GroupBulkRead(self.ph, self.pk)
        for i in self.ids:
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

        # Use cached value if recent enough
        import time

        now = time.monotonic()
        if self.last_positions and (now - self.last_read_time) < self.read_dt:
            return self.last_positions

        # Try bulk read first
        if self.bulk is not None:
            if self.bulk.txRxPacket():
                out: List[float] = []
                for j, i in enumerate(self.ids):
                    if self.bulk.isAvailable(i, ADDR_PRESENT_POSITION, 4):
                        pos = self.bulk.getData(i, ADDR_PRESENT_POSITION, 4)
                        out.append(_ticks_to_rad(int(pos), self.offsets_deg[j], self.signs[j]))
                    else:
                        break
                else:
                    self.last_positions = out
                    self.last_read_time = now
                    return out

        # Fallback to individual reads
        if not self.bulk_warned:
            print(f"[dxl] {self.name}: Using individual reads with cache")
            self.bulk_warned = True

        out: List[float] = []
        for j, i in enumerate(self.ids):
            pos, rc, er = self.pk.read4ByteTxRx(self.ph, i, ADDR_PRESENT_POSITION)
            if rc != COMM_SUCCESS or er != 0:
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
        """Simplified control connection - no complex retries."""
        if self.ctrl is not None:
            try:
                # Quick test if connection is alive
                self.ctrl.getJointTemp()
                return True
            except Exception:
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
        """Immediately stop the robot."""
        try:
            if self.ctrl:
                self.ctrl.stopJ(AMAX)
        except Exception:
            pass


class PedalMonitor:
    """Monitor StreamDeck pedals for teleop control."""

    def __init__(self, vendor_id: int = 0x0FD9, product_id: int = 0x0086, debug: bool = False):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.debug = debug
        self.device: Optional[Any] = None
        self.state = TeleopState.IDLE
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_buttons = set()
        self.last_change_ts = 0.0
        self.debounce_s = 0.08
        self.cb_left: Optional[Any] = None
        self.cb_center_1: Optional[Any] = None
        self.cb_center_2: Optional[Any] = None
        self.cb_right: Optional[Any] = None

    def connect(self) -> bool:
        """Connect to pedal device."""
        if not hid:
            return False

        try:
            devices = hid.enumerate(self.vendor_id, self.product_id)
            if not devices:
                print("[pedal] No StreamDeck pedal found")
                return False

            print(f"[pedal] Found {len(devices)} StreamDeck pedal device(s)")

            # Pick best interface
            chosen = None
            for d in devices:
                p = d.get("path")
                if p and (p.endswith(b":1.0") or p.endswith(b":01.00")):
                    chosen = d
                    break
            if not chosen and devices:
                chosen = devices[0]

            self.device = hid.device()
            if chosen and chosen.get("path"):
                self.device.open_path(chosen["path"])
            else:
                self.device.open(self.vendor_id, self.product_id)

            self.device.set_nonblocking(True)
            print("[pedal] Connected to StreamDeck pedal")
            return True

        except Exception as e:
            print(f"[pedal] Failed to connect: {e}")
            return False

    def start_monitoring(self) -> None:
        """Start monitoring thread."""
        if not self.device:
            if not self.connect():
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
        """Decode button presses from HID data."""
        btns = set()
        n = len(data)
        if n == 0:
            return btns

        # Check multiple layouts
        if n >= 7:
            if any(data[i] in (0, 1) for i in (4, 5, 6)):
                if data[4] == 1:
                    btns.add(PEDAL_LEFT)
                if data[5] == 1:
                    btns.add(PEDAL_CENTER)
                if data[6] == 1:
                    btns.add(PEDAL_RIGHT)
                if btns:
                    return btns

        if not btns and n >= 2:
            m = data[1]
            if m & 0x01:
                btns.add(PEDAL_LEFT)
            if m & 0x02:
                btns.add(PEDAL_CENTER)
            if m & 0x04:
                btns.add(PEDAL_RIGHT)

        return btns

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop.is_set():
            try:
                data = self.device.read(64, timeout_ms=50)
                if data:
                    self._process_buttons(list(data))
            except Exception:
                pass
            time.sleep(0.01)

    def _process_buttons(self, data: List[int]) -> None:
        """Process button presses with debouncing."""
        current_buttons = self._decode_buttons(data)
        now = time.monotonic()

        if current_buttons == self.last_buttons:
            return

        # Debounce
        if now - self.last_change_ts < self.debounce_s:
            self.last_buttons = current_buttons
            return

        # Process single button changes
        added = current_buttons - self.last_buttons
        if len(added) != 1:
            self.last_buttons = current_buttons
            return

        button = next(iter(added))
        self.last_change_ts = now

        if button == PEDAL_LEFT and self.cb_left:
            print("\n⏸️ [LEFT PEDAL] Interrupt - URs stopped")
            self.state = TeleopState.IDLE
            self.cb_left()

        elif button == PEDAL_CENTER:
            if self.state == TeleopState.IDLE and self.cb_center_1:
                print("\n🟡 [CENTER PEDAL - FIRST TAP] Preparing teleop...")
                self.cb_center_1()
                self.state = TeleopState.PREP

            elif self.state == TeleopState.PREP and self.cb_center_2:
                print("\n🟢 [CENTER PEDAL - SECOND TAP] Starting teleop!")
                self.cb_center_2()
                self.state = TeleopState.RUNNING

        elif button == PEDAL_RIGHT and self.cb_right:
            print("\n⏹️ [RIGHT PEDAL] Stopping teleop")
            self.cb_right()
            self.state = TeleopState.IDLE

        self.last_buttons = current_buttons


class FollowThread:
    def __init__(
        self,
        left: Optional[Tuple[DxlBus, URSide]],
        right: Optional[Tuple[DxlBus, URSide]],
    ):
        self.left = left
        self.right = right
        self._stop = threading.Event()
        self._th: Optional[threading.Thread] = None

        # Baselines
        self.q0_dxl_L: Optional[List[float]] = None
        self.q0_ur_L: Optional[List[float]] = None
        self.q0_dxl_R: Optional[List[float]] = None
        self.q0_ur_R: Optional[List[float]] = None

        # Timing
        self.t0_L: Optional[float] = None
        self.t0_R: Optional[float] = None

        # Profiled targets
        self.y_L: Optional[List[float]] = None
        self.v_L: Optional[List[float]] = None
        self.y_R: Optional[List[float]] = None
        self.v_R: Optional[List[float]] = None

        # Motion tracking
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
        """Calculate soft-start ramp factor."""
        if not t0:
            return 1.0
        dt = max(0.0, time.monotonic() - t0)
        return min(1.0, dt / max(1e-6, SOFTSTART_T))

    def _clamp_about(self, base: List[float], q: List[float]) -> List[float]:
        """Optional absolute clamps around baseline."""
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
        """Motion profiling with velocity and acceleration limits."""
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

            v_des = (qt - yj) / DT
            dv = max(-ACC * DT, min(ACC * DT, v_des - vj))
            vj = vj + dv

            if vj > VMAX_CMD:
                vj = VMAX_CMD
            if vj < -VMAX_CMD:
                vj = -VMAX_CMD

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
        # Stop URs
        for pair in (self.left, self.right):
            if pair and pair[1].ctrl:
                try:
                    pair[1].ctrl.stopJ(AMAX)
                except Exception:
                    pass

    def _ensure_ur_ready(self, ur: URSide) -> bool:
        """Simple UR readiness check - no complex fallbacks."""
        ur.ensure_receive()
        if not ur.ensure_control():
            print(f"[follow] {ur.host}: RTDE control not available")
            return False
        ur.end_teach()
        return True

    def _run(self) -> None:
        # Try to set higher priority
        try:
            import os

            os.nice(-5)
        except Exception:
            pass

        # Simple readiness check
        ready_any = False
        for pair in (self.left, self.right):
            if pair and self._ensure_ur_ready(pair[1]):
                ready_any = True

        if not ready_any:
            print("[follow] No UR control available")
            return

        # Fixed-rate scheduler
        import time as _t

        next_t = _t.perf_counter()

        while not self._stop.is_set():
            # LEFT side
            if self.left:
                busL, urL = self.left
                qL = busL.read_present_positions()
                if qL and urL.ctrl:
                    # Auto-init baselines if needed
                    if self.q0_dxl_L is None or self.q0_ur_L is None:
                        self.q0_dxl_L = list(qL)
                        qs = _safe_get_q(urL)
                        if qs:
                            self.q0_ur_L = list(qs)
                        else:
                            self.q0_ur_L = [0.0] * len(qL)
                        self.t0_L = time.monotonic()

                    # Motion detection
                    now = time.monotonic()
                    moved = False
                    if self.last_qL is not None:
                        max_step = max(abs(a - b) for a, b in zip(qL, self.last_qL))
                        if max_step > 0.0025:
                            self.last_move_ts_L = now
                            moved = True
                    self.last_qL = list(qL)

                    # Inactivity rebase
                    if not moved and (now - self.last_move_ts_L) > INACTIVITY_REBASE_S:
                        self.q0_dxl_L = [
                            (1.0 - REBASE_BETA) * q0 + REBASE_BETA * q
                            for q0, q in zip(self.q0_dxl_L, qL)
                        ]

                    # Calculate target
                    dq = [ql - q0 for ql, q0 in zip(qL, self.q0_dxl_L)]
                    dq = self._apply_deadband_scale(dq)
                    q_target = [q0u + d for q0u, d in zip(self.q0_ur_L, dq)]
                    q_target = self._clamp_about(self.q0_ur_L, q_target)

                    # Snap small movements
                    q_target = [
                        q0u if abs(qt - q0u) < SNAP_EPS_RAD else qt
                        for q0u, qt in zip(self.q0_ur_L, q_target)
                    ]

                    # Assist
                    q_target = [
                        qt + ASSIST_K * (q0u - qt) for q0u, qt in zip(self.q0_ur_L, q_target)
                    ]

                    # Velocity limit
                    if self.y_L is not None:
                        max_step = VEL_LIMIT_RAD_S * DT
                        q_target = [
                            y + max(-max_step, min(max_step, qt - y))
                            for y, qt in zip(self.y_L, q_target)
                        ]

                    # Softstart
                    s = self._soft_ramp(self.t0_L)
                    q_target = [q0u + s * (qt - q0u) for q0u, qt in zip(self.q0_ur_L, q_target)]

                    # Profile
                    self.y_L, self.v_L = self._profile(self.y_L, self.v_L, q_target)

                    try:
                        ur_joints = self.y_L[:6] if len(self.y_L) > 6 else self.y_L
                        urL.ctrl.servoJ(ur_joints, VMAX, AMAX, DT, LOOKAHEAD, GAIN)
                    except Exception as e:
                        if "control script is not running" in str(e).lower():
                            print("\n⚠️ LEFT UR: control script not running")
                            print("   Please ensure ExternalControl.urp is PLAYING")
                            self._stop.set()
                            return

            # RIGHT side (similar logic)
            if self.right:
                busR, urR = self.right
                qR = busR.read_present_positions()
                if qR and urR.ctrl:
                    if self.q0_dxl_R is None or self.q0_ur_R is None:
                        self.q0_dxl_R = list(qR)
                        qs = _safe_get_q(urR)
                        if qs:
                            self.q0_ur_R = list(qs)
                        else:
                            self.q0_ur_R = [0.0] * len(qR)
                        self.t0_R = time.monotonic()

                    now = time.monotonic()
                    moved = False
                    if self.last_qR is not None:
                        max_step = max(abs(a - b) for a, b in zip(qR, self.last_qR))
                        if max_step > 0.0025:
                            self.last_move_ts_R = now
                            moved = True
                    self.last_qR = list(qR)

                    if not moved and (now - self.last_move_ts_R) > INACTIVITY_REBASE_S:
                        self.q0_dxl_R = [
                            (1.0 - REBASE_BETA) * q0 + REBASE_BETA * q
                            for q0, q in zip(self.q0_dxl_R, qR)
                        ]

                    dq = [qr - q0 for qr, q0 in zip(qR, self.q0_dxl_R)]
                    dq = self._apply_deadband_scale(dq)
                    q_target = [q0u + d for q0u, d in zip(self.q0_ur_R, dq)]
                    q_target = self._clamp_about(self.q0_ur_R, q_target)

                    q_target = [
                        q0u if abs(qt - q0u) < SNAP_EPS_RAD else qt
                        for q0u, qt in zip(self.q0_ur_R, q_target)
                    ]

                    q_target = [
                        qt + ASSIST_K * (q0u - qt) for q0u, qt in zip(self.q0_ur_R, q_target)
                    ]

                    if self.y_R is not None:
                        max_step = VEL_LIMIT_RAD_S * DT
                        q_target = [
                            y + max(-max_step, min(max_step, qt - y))
                            for y, qt in zip(self.y_R, q_target)
                        ]

                    s = self._soft_ramp(self.t0_R)
                    q_target = [q0u + s * (qt - q0u) for q0u, qt in zip(self.q0_ur_R, q_target)]

                    self.y_R, self.v_R = self._profile(self.y_R, self.v_R, q_target)

                    try:
                        ur_joints = self.y_R[:6] if len(self.y_R) > 6 else self.y_R
                        urR.ctrl.servoJ(ur_joints, VMAX, AMAX, DT, LOOKAHEAD, GAIN)
                    except Exception as e:
                        if "control script is not running" in str(e).lower():
                            print("\n⚠️ RIGHT UR: control script not running")
                            print("   Please ensure ExternalControl.urp is PLAYING")
                            self._stop.set()
                            return

            # Fixed-rate sleep
            next_t += DT
            now = _t.perf_counter()
            delay = next_t - now
            if delay > 0:
                _t.sleep(delay)
            else:
                next_t = now


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
    ap = argparse.ArgumentParser(description="Optimized DXL→UR teleop with pedal control")
    ap.add_argument("--ur-left", type=str, default=None, help="UR IP for LEFT arm")
    ap.add_argument("--ur-right", type=str, default=None, help="UR IP for RIGHT arm")
    ap.add_argument(
        "--left-port", type=str, default=None, help="/dev/serial/by-id/... for LEFT DXL"
    )
    ap.add_argument(
        "--right-port", type=str, default=None, help="/dev/serial/by-id/... for RIGHT DXL"
    )
    ap.add_argument("--left-ids", type=str, default=None, help="Comma IDs for LEFT")
    ap.add_argument("--right-ids", type=str, default=None, help="Comma IDs for RIGHT")
    ap.add_argument("--left-signs", type=str, default=None, help="Comma ±1 per joint")
    ap.add_argument("--right-signs", type=str, default=None, help="Comma ±1 per joint")
    ap.add_argument("--left-offsets-deg", type=str, default=None, help="Comma offsets(deg)")
    ap.add_argument("--right-offsets-deg", type=str, default=None, help="Comma offsets(deg)")
    ap.add_argument("--baud", type=int, default=1_000_000)
    ap.add_argument("--joints-passive", action="store_true", help="Leave DXL torque OFF")
    ap.add_argument("--no-dashboard", action="store_true", help="Skip dashboard commands")
    ap.add_argument("--test-mode", action="store_true", help="Auto-start without pedals")
    ap.add_argument("--pedal-debug", action="store_true", help="Debug pedal packets")

    args = ap.parse_args(argv)

    # Parse IDs with defaults
    left_ids = _parse_int_csv(args.left_ids) if args.left_ids else []
    right_ids = _parse_int_csv(args.right_ids) if args.right_ids else []

    if args.left_port and not left_ids:
        left_ids = [1, 2, 3, 4, 5, 6, 7]  # Including gripper
    if args.right_port and not right_ids:
        right_ids = [10, 11, 12, 13, 14, 15, 16]  # Including gripper

    # ENV override for debugging
    if os.environ.get("LEFT_IDS"):
        left_ids = _parse_int_csv(os.environ["LEFT_IDS"])
    if os.environ.get("RIGHT_IDS"):
        right_ids = _parse_int_csv(os.environ["RIGHT_IDS"])

    # Parse signs and offsets
    default_signs = [1, 1, -1, 1, 1, 1, 1]
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

    # Build UR sides
    urL = URSide(args.ur_left) if args.ur_left else None
    urR = URSide(args.ur_right) if args.ur_right else None

    if not (busL or busR):
        print("[exit] No DXL buses configured")
        return 2
    if not (urL or urR):
        print("[exit] No UR IPs provided")
        return 2

    # Print startup info
    print("\n" + "=" * 60)
    print("OPTIMIZED TELEOP READY")
    print("=" * 60)
    print(f"Speed: VMAX={VMAX:.2f} rad/s, AMAX={AMAX:.1f} rad/s²")
    if args.no_dashboard:
        print("Dashboard: DISABLED (manual control required)")
    print("=" * 60 + "\n")

    try:
        # Setup torque
        if not args.joints_passive:
            if busL:
                busL.torque(True)
            if busR:
                busR.torque(True)
        else:
            print("[dxl] joints-passive: torque OFF")

        # Prepare URs
        for ur in (urL, urR):
            if ur:
                ur.ensure_receive()

        ft = FollowThread(
            left=(busL, urL) if (busL and urL) else None,
            right=(busR, urR) if (busR and urR) else None,
        )

        # Setup pedals
        pedal_monitor = PedalMonitor(debug=args.pedal_debug)
        _saved_mode = None

        def on_left_interrupt():
            """Interrupt for external control."""
            if ft._th and ft._th.is_alive():
                ft.stop()
            for ur in (urL, urR):
                if ur:
                    ur.stop_now()

        def on_center_first():
            """Capture baselines and set gentle mode."""
            nonlocal _saved_mode
            _saved_mode = _set_gentle_mode()

            # Capture baselines
            if ft.left:
                bus, ur = ft.left
                for retry in range(3):
                    ft.q0_dxl_L = bus.read_present_positions()
                    if ft.q0_dxl_L:
                        break
                    time.sleep(0.1)
                if ur:
                    ft.q0_ur_L = _safe_get_q(ur)
                    ft.t0_L = time.monotonic()
                if ft.q0_dxl_L:
                    print(f"   ✓ LEFT arm: {len(ft.q0_dxl_L)} joints captured")

            if ft.right:
                bus, ur = ft.right
                for retry in range(3):
                    ft.q0_dxl_R = bus.read_present_positions()
                    if ft.q0_dxl_R:
                        break
                    time.sleep(0.1)
                if ur:
                    ft.q0_ur_R = _safe_get_q(ur)
                    ft.t0_R = time.monotonic()
                if ft.q0_dxl_R:
                    print(f"   ✓ RIGHT arm: {len(ft.q0_dxl_R)} joints captured")

        def on_center_second():
            """Start full-speed teleop."""
            nonlocal _saved_mode
            if _saved_mode is not None:
                _restore_mode(_saved_mode)
                _saved_mode = None

            # Quick check that we have DXL data
            dxl_ok = False
            if ft.q0_dxl_L and len(ft.q0_dxl_L) > 0:
                dxl_ok = True
            if ft.q0_dxl_R and len(ft.q0_dxl_R) > 0:
                dxl_ok = True

            if not dxl_ok:
                print("\n⚠️ ERROR: No DXL servos responding!")
                return

            print("\n✅ Starting teleoperation!")
            ft.start()

        def on_right_stop():
            """Stop teleop."""
            ft.stop()
            for bus in (busL, busR):
                if bus:
                    bus.torque(False)

        # Assign callbacks
        pedal_monitor.cb_left = on_left_interrupt
        pedal_monitor.cb_center_1 = on_center_first
        pedal_monitor.cb_center_2 = on_center_second
        pedal_monitor.cb_right = on_right_stop

        # Start monitoring
        pedal_connected = pedal_monitor.connect()
        if pedal_connected:
            pedal_monitor.start_monitoring()
            print("\n🎮 Pedal Controls:")
            print("   ⏸️  LEFT   → Interrupt")
            print("   🟡 CENTER → Tap 1: Prepare | Tap 2: Start")
            print("   ⏹️  RIGHT  → Stop\n")
            print("Ready for pedal input... (Ctrl+C to exit)\n")
        else:
            print("\n[warn] No pedals found.")

            if args.test_mode:
                print("\n⚠️ TEST MODE: Auto-starting in 3 seconds...")
                time.sleep(3)
                print("\n[TEST] Capturing baselines...")
                on_center_first()
                time.sleep(1)
                print("\n[TEST] Starting teleop...")
                on_center_second()
                print("\nTeleop running! Move GELLO arms to control URs")
                print("Press Ctrl+C to stop\n")

        # Main loop
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[exit] Shutting down...")
            ft.stop()
            if pedal_monitor.device:
                pedal_monitor.stop_monitoring()

    finally:
        if busL:
            busL.close()
        if busR:
            busR.close()

        # Clean disconnect
        if urL and urL.ctrl:
            try:
                urL.ctrl.stopJ(AMAX)
                urL.ctrl.disconnect()
            except Exception:
                pass
        if urR and urR.ctrl:
            try:
                urR.ctrl.stopJ(AMAX)
                urR.ctrl.disconnect()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
