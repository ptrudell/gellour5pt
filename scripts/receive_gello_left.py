#!/usr/bin/env python3
"""
Receive and display GELLO LEFT arm positions from ZCM channel.

Default channel: gello_positions_left
Shows a compact single-line HUD by default. Use --verbose for full detail.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import List

import numpy as np

try:
    import zerocm
    from gello_positions_t import gello_positions_t
except ImportError:
    print(
        "Error: missing dependencies. Install zerocm and ensure gello_positions_t is available."
    )
    print("Run: zcm-gen -p gello_positions_simple.zcm")
    sys.exit(1)


class GelloLeftReceiver:
    def __init__(self, channel: str, verbose: bool = False):
        self.channel = channel
        self.verbose = verbose
        self.msg_count = 0
        self.last_ts_sec: float | None = None

        self.zcm = zerocm.ZCM()
        if not self.zcm.good():
            print("Unable to initialize ZCM")
            sys.exit(1)

        self.zcm.subscribe(self.channel, gello_positions_t, self._on_msg)
        print(f"[ZCM] Listening LEFT arm on '{self.channel}'")
        print("-" * 60)

    def _on_msg(self, ch: str, msg: gello_positions_t) -> None:
        self.msg_count += 1
        now = time.time()

        rate_str = ""
        if self.last_ts_sec is not None:
            dt = now - self.last_ts_sec
            if dt > 0:
                rate_str = f" ({1.0 / dt:.1f} Hz)"
        self.last_ts_sec = now

        joints_deg: List[float] = [float(np.degrees(x)) for x in msg.joint_positions]
        grip_deg = float(np.degrees(msg.gripper_position))
        ok = "✓" if msg.is_valid else "✗"

        if self.verbose:
            print(f"\n[LEFT #{self.msg_count}]{rate_str}")
            print(
                f"  timestamp: {msg.timestamp} µs  side: {msg.arm_side}  valid: {msg.is_valid}"
            )
            for i, (rad, deg) in enumerate(
                zip(msg.joint_positions, joints_deg), start=1
            ):
                print(f"  J{i}: {deg:8.2f}°  ({rad:8.4f} rad)")
            print(
                f"  J7 (gripper): {grip_deg:8.2f}°  ({float(msg.gripper_position):8.4f} rad)"
            )
        else:
            joints_str = " ".join(
                f"J{i + 1}:{d:6.1f}°" for i, d in enumerate(joints_deg)
            )
            print(
                f"\r[LEFT {ok}]{rate_str} {joints_str}  J7:{grip_deg:6.1f}°  (#{self.msg_count})",
                end="",
                flush=True,
            )

    def run(self) -> None:
        print("\nReceiving GELLO LEFT…  (Ctrl+C to stop)\n")
        if not self.verbose:
            print("Tip: add --verbose for detailed per-joint rad/deg.\n")
        try:
            self.zcm.start()
            while True:
                time.sleep(0.01)
        except KeyboardInterrupt:
            print(f"\n\n[Summary] Received {self.msg_count} messages")
        finally:
            self.zcm.stop()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Receive GELLO LEFT arm positions from ZCM"
    )
    ap.add_argument(
        "-c",
        "--channel",
        default="gello_positions_left",
        help="ZCM channel (default: gello_positions_left)",
    )
    ap.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = ap.parse_args()

    GelloLeftReceiver(channel=args.channel, verbose=args.verbose).run()


if __name__ == "__main__":
    main()
