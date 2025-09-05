#!/usr/bin/env python3
"""
StreamDeck Pedal — robust edge tester & decoder

Goals
- Reflect true sequence (e.g., LEFT, CENTER, CENTER, RIGHT, RIGHT) without ghost presses.
- Handle multiple HID report layouts seen on StreamDeck Pedal.
- Debounce, suppress center ghosts when LEFT is held, and ignore multi-endpoint noise.

Run
  python gello/test_scripts/pedal_only_test.py --debug
  python gello/test_scripts/pedal_only_test.py

Knobs
  --debounce-ms 80   # increase if you still see double-fires
  --stabilize-ms 18  # minimum time a state must persist to count as real
  --suppress-center-after-left-ms 160  # ignore center edges just after a LEFT edge

Notes
- We favor the "byte-per-pedal" layout at indices [4],[5],[6] when present.
- Fallbacks keep old bitmask methods but only if [4:7] is all zeros.
- We only emit edges when exactly one pedal's state changes.
"""

from __future__ import annotations

import argparse
import time
from typing import List, Optional, Set

try:
    import hid  # type: ignore
except Exception as e:
    print("[err] python-hidapi not available:", e)
    print("Install with: pip install hidapi")
    raise

VENDOR_ID = 0x0FD9
PRODUCT_ID = 0x0086

BTN_LEFT, BTN_CENTER, BTN_RIGHT = 4, 5, 6
BTN_NAMES = {BTN_LEFT: "LEFT", BTN_CENTER: "CENTER", BTN_RIGHT: "RIGHT"}


class PedalTester:
    def __init__(
        self, debug: bool, debounce_ms: int, stabilize_ms: int, suppress_center_after_left_ms: int
    ):
        self.debug = debug
        self.debounce_s = debounce_ms / 1000.0
        self.stabilize_s = stabilize_ms / 1000.0
        self.suppress_center_after_left_s = suppress_center_after_left_ms / 1000.0
        self.device: Optional[hid.device] = None
        self.last_buttons: Set[int] = set()
        self.last_packet: List[int] = []
        self.last_change_ts = 0.0
        self.last_emit_ts = {BTN_LEFT: 0.0, BTN_CENTER: 0.0, BTN_RIGHT: 0.0}
        self.last_left_edge_ts = 0.0

    # ---------- HID ----------
    def connect(self) -> bool:
        print(f"[pedal] Searching for device {VENDOR_ID:04x}:{PRODUCT_ID:04x}...")
        path = None
        for d in hid.enumerate(VENDOR_ID, PRODUCT_ID):
            # Prefer interface path ending with ":1.0"; those have the button endpoint
            p = d.get("path")
            if not path and p:
                path = p
            if p and (p.endswith(b":1.0") or p.endswith(b":01.00")):
                path = p
                break
        if not path:
            print("[pedal] Device not found")
            print("[pedal] Make sure the StreamDeck pedal is connected via USB")
            return False
        print(f"[pedal] Found device at path: {path}")
        self.device = hid.device()
        try:
            self.device.open_path(path)
            self.device.set_nonblocking(True)
        except Exception as e:
            print(f"[pedal] ERROR: Failed to open device: {e}")
            print("[pedal] Try running with sudo or check permissions")
            return False
        print(f"[pedal] Connected to {VENDOR_ID:04x}:{PRODUCT_ID:04x}")
        print("[pedal] Press pedals to test. Ctrl+C to exit.")
        if self.debug:
            print("[pedal] Debug mode ON - showing raw packets")
        print("")
        return True

    def close(self):
        try:
            if self.device:
                self.device.close()
        except Exception:
            pass
        finally:
            print("[pedal] Device closed")

    # ---------- Decode ----------
    def _decode_buttons(self, data: List[int]) -> Set[int]:
        btns: Set[int] = set()
        n = len(data)
        if n == 0:
            return btns

        # Preferred layout: byte-per-pedal at indices [4], [5], [6]
        if n >= 7:
            # Check if we have the byte-per-pedal format
            if any(data[i] in (0, 1) for i in (4, 5, 6)):
                if data[4] == 1:
                    btns.add(BTN_LEFT)
                if data[5] == 1:
                    btns.add(BTN_CENTER)
                if data[6] == 1:
                    btns.add(BTN_RIGHT)
                # If we detected buttons this way, return early
                if btns:
                    return btns

        # Fallback: bitmask in data[1] (bits 0..2)
        if not btns and n >= 2:
            m = data[1]
            if m & 0x01:
                btns.add(BTN_LEFT)
            if m & 0x02:
                btns.add(BTN_CENTER)
            if m & 0x04:
                btns.add(BTN_RIGHT)

        # Fallback: bitmask in data[4] (bits 0..2) - older format
        if not btns and n >= 5:
            m = data[4]
            if m & 0x01:
                btns.add(BTN_LEFT)
            if m & 0x02:
                btns.add(BTN_CENTER)
            if m & 0x04:
                btns.add(BTN_RIGHT)

        return btns

    # ---------- Emit logic ----------
    def _emit_edge(self, btn: int, is_down: bool):
        name = BTN_NAMES[btn]
        arrow = "↓ DOWN" if is_down else "↑ UP  "
        print(f"{arrow}  {name}")
        self.last_emit_ts[btn] = time.monotonic()
        if btn == BTN_LEFT and is_down:
            self.last_left_edge_ts = self.last_emit_ts[btn]

    def _should_suppress_center(self, btn: int, is_down: bool) -> bool:
        # Ignore CENTER edges shortly after LEFT edge to kill ghosting
        if btn == BTN_CENTER:
            if time.monotonic() - self.last_left_edge_ts < self.suppress_center_after_left_s:
                if self.debug:
                    print(
                        f"[debug] Suppressing CENTER {('DOWN' if is_down else 'UP')} (too soon after LEFT)"
                    )
                return True
        return False

    def loop(self):
        try:
            stable_since = time.monotonic()
            while True:
                data = self.device.read(64, timeout_ms=50) if self.device else []
                now = time.monotonic()

                if data:
                    lst = list(data)

                    # Debug output
                    if self.debug and (lst != self.last_packet):
                        # Format display
                        hex_display = " ".join(f"{b:02X}" for b in lst[:10])
                        if len(lst) > 10:
                            hex_display += f" ... ({len(lst)} bytes)"
                        decoded = ",".join(str(b) for b in sorted(self._decode_buttons(lst))) or "-"
                        print(f"raw: [{hex_display}]  decoded: {decoded}")

                    cur = self._decode_buttons(lst)

                    # Debounce and stabilization
                    if cur == self.last_buttons:
                        # Unchanged — check if we've stabilized long enough
                        if now - stable_since >= self.stabilize_s:
                            pass  # State is stable
                    else:
                        # State changed — reset stabilize timer
                        stable_since = now

                        # Only act if state persists beyond debounce window
                        if now - self.last_change_ts < self.debounce_s:
                            self.last_buttons = cur
                            continue

                        # Compute delta and only accept single-button changes
                        added = cur - self.last_buttons
                        removed = self.last_buttons - cur

                        # Prefer single-edge changes; ignore multi-edge noise
                        if len(added) + len(removed) == 1:
                            if added:
                                btn = next(iter(added))
                                if not self._should_suppress_center(btn, True):
                                    self._emit_edge(btn, True)
                            else:
                                btn = next(iter(removed))
                                if not self._should_suppress_center(btn, False):
                                    self._emit_edge(btn, False)
                        elif self.debug and (added or removed):
                            # Debug: show multi-edge noise
                            print(f"[debug] Multi-edge ignored: added={added}, removed={removed}")

                        # Update timestamps and state
                        self.last_change_ts = now
                        self.last_buttons = cur
                        self.last_packet = lst
                else:
                    # No data — short sleep
                    time.sleep(0.005)

        except KeyboardInterrupt:
            print("\n[pedal] Interrupted by user")
        except Exception as e:
            print(f"\n[pedal] ERROR: {e}")
        finally:
            self.close()


def main():
    ap = argparse.ArgumentParser(
        description="StreamDeck Pedal Tester - Robust decoder with ghost suppression"
    )
    ap.add_argument("--debug", action="store_true", help="Show raw packets and debug info")
    ap.add_argument(
        "--debounce-ms",
        type=int,
        default=80,
        help="Debounce time in ms (default: 80)",
    )
    ap.add_argument(
        "--stabilize-ms",
        type=int,
        default=18,
        help="Minimum time a state must persist to count as real (default: 18)",
    )
    ap.add_argument(
        "--suppress-center-after-left-ms",
        type=int,
        default=160,
        help="Ignore CENTER edges this many ms after LEFT (default: 160)",
    )
    args = ap.parse_args()

    print("=" * 60)
    print("StreamDeck Pedal Tester - Robust Decoder")
    print("=" * 60)
    print("Settings:")
    print(f"  Debounce: {args.debounce_ms}ms")
    print(f"  Stabilize: {args.stabilize_ms}ms")
    print(f"  CENTER suppression after LEFT: {args.suppress_center_after_left_ms}ms")
    print(f"  Debug mode: {'ON' if args.debug else 'OFF'}")
    print("")

    t = PedalTester(
        debug=args.debug,
        debounce_ms=args.debounce_ms,
        stabilize_ms=args.stabilize_ms,
        suppress_center_after_left_ms=args.suppress_center_after_left_ms,
    )

    if not t.connect():
        return 2

    t.loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
