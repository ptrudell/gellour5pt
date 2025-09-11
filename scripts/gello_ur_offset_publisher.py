#!/usr/bin/env python3
"""
Publish GELLO − UR5 joint offsets per arm to ZCM using the SAME schema as gello_positions_t.

Inputs (subscribe):
  - gello_positions_left  : gello_positions_t (GELLO absolute joints for LEFT arm)
  - gello_positions_right : gello_positions_t (GELLO absolute joints for RIGHT arm)

Outputs (publish):
  - gello_ur_offset_left  : gello_positions_t (joint_positions[] = offsets_rad J1..J6; gripper NaN)
  - gello_ur_offset_right : gello_positions_t (joint_positions[] = offsets_rad J10..J15; gripper NaN)

Each published message:
  msg.timestamp       -> now (µs)
  msg.arm_side        -> "left" or "right"
  msg.is_valid        -> True only if both sides (GELLO & UR) are fresh & connected
  msg.joint_positions -> elementwise wrap_to_pi( gello[i] - ur[i] )
  msg.gripper_position-> NaN (UR has no gripper joint)
"""

from __future__ import annotations

import argparse
import math
import threading
import time
from typing import List, Optional, Tuple

import numpy as np

# --- ZCM + messages ---
try:
    import zerocm
    from gello_positions_t import gello_positions_t
except Exception as e:
    raise SystemExit(
        f"[fatal] Missing ZCM dependencies: {e}\n"
        "Install zerocm and ensure gello_positions_t is generated.\n"
        "Run: zcm-gen -p gello_positions_simple.zcm"
    )


# --- time helper (µs) ---
def robot_time() -> int:
    """Get current time in microseconds."""
    return int(time.time() * 1e6)


# --- UR RTDE receive ---
try:
    from rtde_receive import RTDEReceiveInterface
except Exception:
    RTDEReceiveInterface = None


def wrap_to_pi(x: float) -> float:
    """wrap angle (rad) to (-pi, pi]."""
    return (x + math.pi) % (2.0 * math.pi) - math.pi


class SideState:
    """Holds latest GELLO reading for a side."""

    def __init__(self, name: str):
        self.name = name  # "left" or "right"
        self.joints: Optional[List[float]] = None  # len 6 radians
        self.grip: Optional[float] = None
        self.ts_wall: float = 0.0
        self.lock = threading.Lock()

    def update_from_msg(self, msg: gello_positions_t) -> None:
        with self.lock:
            self.joints = list(float(x) for x in msg.joint_positions)
            self.grip = float(msg.gripper_position)
            self.ts_wall = time.time()

    def snapshot(self) -> Tuple[Optional[List[float]], Optional[float], float]:
        with self.lock:
            return (
                None if self.joints is None else list(self.joints),
                self.grip,
                self.ts_wall,
            )


class OffsetPublisher:
    def __init__(
        self,
        left_ur_ip: str,
        right_ur_ip: str,
        in_left: str = "gello_positions_left",
        in_right: str = "gello_positions_right",
        out_left: str = "gello_ur_offset_left",
        out_right: str = "gello_ur_offset_right",
        rate_hz: float = 50.0,
        stale_sec: float = 0.5,
        verbose: bool = False,
    ):
        self.verbose = verbose
        self.in_left = in_left
        self.in_right = in_right
        self.out_left = out_left
        self.out_right = out_right
        self.rate_hz = rate_hz
        self.dt = 1.0 / max(1.0, rate_hz)
        self.stale_sec = stale_sec

        # ZCM
        self.zcm = zerocm.ZCM()
        if not self.zcm.good():
            raise RuntimeError("Unable to initialize ZCM")

        # subscribe to GELLO streams
        self.left_state = SideState("left")
        self.right_state = SideState("right")
        self.zcm.subscribe(self.in_left, gello_positions_t, self._on_left)
        self.zcm.subscribe(self.in_right, gello_positions_t, self._on_right)

        # UR connections
        self.left_ur = None
        self.right_ur = None
        if RTDEReceiveInterface is None:
            print("[warn] ur_rtde not installed. Offsets will be invalid.")
        else:
            self.left_ur = self._safe_connect(left_ur_ip, "LEFT")
            self.right_ur = self._safe_connect(right_ur_ip, "RIGHT")

        self.run_flag = True
        self.msg_count = 0

    # ---- ZCM callbacks ----
    def _on_left(self, _ch: str, msg: gello_positions_t) -> None:
        self.left_state.update_from_msg(msg)

    def _on_right(self, _ch: str, msg: gello_positions_t) -> None:
        self.right_state.update_from_msg(msg)

    # ---- UR helpers ----
    def _safe_connect(self, ip: str, label: str):
        try:
            r = RTDEReceiveInterface(ip)
            print(f"[ok] Connected to {label} UR5 @ {ip}")
            return r
        except Exception as e:
            print(f"[warn] Could not connect to {label} UR5 @ {ip}: {e}")
            return None

    def _read_ur_q(self, iface) -> Optional[List[float]]:
        if iface is None:
            return None
        try:
            q = iface.getActualQ()
            if q and len(q) >= 6:
                return list(float(x) for x in q[:6])
        except Exception:
            return None
        return None

    # ---- message factory (same schema as gello_positions_t) ----
    def _make_msg(
        self, side: str, offsets_rad: List[float], valid: bool
    ) -> gello_positions_t:
        m = gello_positions_t()
        m.timestamp = robot_time()
        m.arm_side = side  # "left" or "right"
        m.is_valid = bool(valid)
        m.joint_positions = list(offsets_rad)  # OFFSETS in radians
        m.gripper_position = float("nan")  # no UR gripper; publish NaN
        m.joint_velocities = [0.0] * 6  # Not computing velocities for offsets
        return m

    def start(self) -> None:
        print(f"\n[OffsetPublisher] Starting at {self.rate_hz}Hz")
        print(f"  Inputs:  {self.in_left}, {self.in_right}")
        print(f"  Outputs: {self.out_left}, {self.out_right}")
        print(
            f"  UR IPs:  LEFT={self.left_ur is not None}, RIGHT={self.right_ur is not None}"
        )
        print()

        self.zcm.start()
        try:
            while self.run_flag:
                t0 = time.time()

                # Snapshots
                l_gello, _, l_ts = self.left_state.snapshot()
                r_gello, _, r_ts = self.right_state.snapshot()
                l_ur = self._read_ur_q(self.left_ur)
                r_ur = self._read_ur_q(self.right_ur)
                now = time.time()

                # LEFT offsets: GELLO(left) - UR(left)
                left_valid = (
                    l_gello is not None
                    and l_ur is not None
                    and (now - l_ts) <= self.stale_sec
                )
                if left_valid:
                    offsets_left = [wrap_to_pi(g - u) for g, u in zip(l_gello, l_ur)]
                    self.zcm.publish(
                        self.out_left, self._make_msg("left", offsets_left, True)
                    )
                    self.msg_count += 1
                    if self.verbose:
                        rms = float(np.sqrt(np.mean(np.square(offsets_left))))
                        print(
                            f"[left] published offsets (rms={math.degrees(rms):.2f}°) -> {self.out_left}"
                        )
                else:
                    # still publish invalid to keep consumers alive (optional)
                    if l_gello is not None or l_ur is not None:
                        self.zcm.publish(
                            self.out_left,
                            self._make_msg("left", [float("nan")] * 6, False),
                        )

                # RIGHT offsets: GELLO(right) - UR(right)
                right_valid = (
                    r_gello is not None
                    and r_ur is not None
                    and (now - r_ts) <= self.stale_sec
                )
                if right_valid:
                    offsets_right = [wrap_to_pi(g - u) for g, u in zip(r_gello, r_ur)]
                    self.zcm.publish(
                        self.out_right, self._make_msg("right", offsets_right, True)
                    )
                    self.msg_count += 1
                    if self.verbose:
                        rms = float(np.sqrt(np.mean(np.square(offsets_right))))
                        print(
                            f"[right] published offsets (rms={math.degrees(rms):.2f}°) -> {self.out_right}"
                        )
                else:
                    if r_gello is not None or r_ur is not None:
                        self.zcm.publish(
                            self.out_right,
                            self._make_msg("right", [float("nan")] * 6, False),
                        )

                # Status every 100 messages
                if self.msg_count > 0 and self.msg_count % 100 == 0:
                    print(f"[status] Published {self.msg_count} offset messages")

                # pacing
                elapsed = time.time() - t0
                sleep_s = max(0.0, self.dt - elapsed)
                time.sleep(sleep_s)
        except KeyboardInterrupt:
            print(
                f"\n[OffsetPublisher] Stopped. Published {self.msg_count} messages total."
            )
        finally:
            self.run_flag = False
            self.zcm.stop()
            # UR interfaces close on GC; no explicit disconnect in rtde_receive


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Publish GELLO−UR5 joint offsets over ZCM (gello_positions_t schema)."
    )
    ap.add_argument("--left-ur", default="192.168.1.211", help="Left UR5 IP")
    ap.add_argument("--right-ur", default="192.168.1.210", help="Right UR5 IP")
    ap.add_argument(
        "--in-left",
        default="gello_positions_left",
        help="Input ZCM channel for LEFT GELLO",
    )
    ap.add_argument(
        "--in-right",
        default="gello_positions_right",
        help="Input ZCM channel for RIGHT GELLO",
    )
    ap.add_argument(
        "--out-left",
        default="gello_ur_offset_left",
        help="Output ZCM channel for LEFT offsets",
    )
    ap.add_argument(
        "--out-right",
        default="gello_ur_offset_right",
        help="Output ZCM channel for RIGHT offsets",
    )
    ap.add_argument("--rate", type=float, default=50.0, help="Publish rate (Hz)")
    ap.add_argument(
        "--stale-sec",
        type=float,
        default=0.5,
        help="Max age for GELLO sample to be valid (s)",
    )
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="Print RMS each publish"
    )
    args = ap.parse_args()

    op = OffsetPublisher(
        left_ur_ip=args.left_ur,
        right_ur_ip=args.right_ur,
        in_left=args.in_left,
        in_right=args.in_right,
        out_left=args.out_left,
        out_right=args.out_right,
        rate_hz=args.rate,
        stale_sec=args.stale_sec,
        verbose=args.verbose,
    )
    op.start()


if __name__ == "__main__":
    main()
