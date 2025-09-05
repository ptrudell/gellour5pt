#!/usr/bin/env python3
"""
Calibrate GELLO <-> UR5 joint mapping: per-joint offset + sign.

Usage (LEFT):
  python3 gello/scripts/calibrate_offsets.py --ur-ip 192.168.1.211 --side left \
      --dxl-port-auto FTAAMNTI --ids 1,2,3,4,5,6 --wrap 360 --nudge-deg 2

Usage (RIGHT):
  python3 gello/scripts/calibrate_offsets.py --ur-ip 192.168.1.210 --side right \
      --dxl-port-auto FTAAMNUF --ids 10,11,12,13,14,15 --wrap 360 --nudge-deg 2

Notes
- Default is MANUAL nudge: you jog the UR a tiny +Δdeg per joint then press <Enter>.
- If you pass --auto-nudge, it will command a small move on the UR (be sure it's safe).
- It never commands Dynamixels; it only reads their Present Position.
- Emits BOTH ticks and degrees so downstream tools/configs can choose.
"""

import sys, time, math, glob, argparse
from typing import List, Tuple

# --- UR RTDE (support both layouts) ---
try:
    from ur_rtde import rtde_receive, rtde_control
except ImportError:
    # Some older wheels expose modules at top-level names
    import rtde_receive, rtde_control  # type: ignore

# --- Dynamixel SDK ---
try:
    from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
except ImportError:
    print("ERROR: dynamixel_sdk not installed. Do: pip install dynamixel-sdk")
    sys.exit(1)

TPR = 4096  # ticks per revolution for X-series

def deg2ticks(deg: float) -> float:
    return (deg / 360.0) * TPR

def ticks2deg(ticks: float) -> float:
    return (ticks / TPR) * 360.0

def wrap_angle(deg: float, wrap: int) -> float:
    """wrap in [-wrap/2, wrap/2) if wrap==180 else [0, wrap) if wrap==360."""
    if wrap == 180:
        return (deg + 180.0) % 360.0 - 180.0
    return deg % 360.0

def wrap_ticks(ticks: float) -> int:
    """Return int ticks wrapped to [0..TPR)."""
    return int(ticks) % TPR

def open_dxl_port(port: str, baud: int) -> Tuple[PortHandler, PacketHandler]:
    ph = PortHandler(port)
    if not ph.openPort():
        raise RuntimeError(f"Failed to open DXL port: {port}")
    if not ph.setBaudRate(baud):
        raise RuntimeError(f"Failed to set baud {baud} on {port}")
    pk = PacketHandler(2.0)
    return ph, pk

def autodetect_port(hint: str) -> str:
    cand = glob.glob("/dev/serial/by-id/*")
    hits = [c for c in cand if hint in c]
    if not hits:
        raise RuntimeError(f"No serial device matched '{hint}'. Found: {cand}")
    if len(hits) > 1:
        print(f"WARNING: Multiple matches for '{hint}', picking first:\n{hits}")
    return hits[0]

def read_pos_ticks(pk: PacketHandler, ph: PortHandler, dxl_id: int) -> int:
    ADDR_POS = 132  # Present Position (4 bytes)
    pos, rc, err = pk.read4ByteTxRx(ph, dxl_id, ADDR_POS)
    if rc != COMM_SUCCESS or err != 0:
        raise RuntimeError(f"DXL read pos failed id={dxl_id} rc={rc} err={err}")
    return pos

def get_ur_deg(rr) -> List[float]:
    q = rr.getActualQ()  # radians, len=6
    return [math.degrees(v) for v in q]

def move_ur_joint(rc, rr, joint_idx: int, delta_deg: float, speed: float = 0.2, accel: float = 0.5):
    """Small relative move on UR joint 'joint_idx' (0..5)."""
    q_now = rr.getActualQ()  # radians
    q_target = list(q_now)
    q_target[joint_idx] = q_target[joint_idx] + math.radians(delta_deg)
    rc.moveJ(q_target, speed, accel)
    # wait until close
    while True:
        q = rr.getActualQ()
        if abs(q[joint_idx] - q_target[joint_idx]) < math.radians(0.2):
            break
        time.sleep(0.02)
    time.sleep(0.1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ur-ip", required=True, help="UR controller IP (e.g., 192.168.1.211)")
    ap.add_argument("--side", choices=["left","right"], required=True, help="Which arm you are calibrating")
    ap.add_argument("--ids", default=None, help="Comma list of DXL joint IDs (e.g., '1,2,3,4,5,6').")
    ap.add_argument("--dxl-port", default=None, help="Exact DXL port path (e.g., /dev/serial/by-id/...FTAAMNTI...)")
    ap.add_argument("--dxl-port-auto", default=None, help="Substring under /dev/serial/by-id for auto-pick (e.g., FTAAMNTI).")
    ap.add_argument("--baud", type=int, default=1_000_000, help="DXL baud")
    ap.add_argument("--wrap", type=int, choices=[180,360], default=360, help="Angle wrap used for degree presentation")
    ap.add_argument("--nudge-deg", type=float, default=2.0, help="Small positive nudge for sign detection")
    ap.add_argument("--auto-nudge", action="store_true", help="If set, command the UR for the small nudge per joint")
    ap.add_argument("--sleep", type=float, default=0.2, help="Pause (s) after reads")
    ap.add_argument("--snapshot-only", action="store_true", help="No nudges; compute offsets at current pose only.")
    ap.add_argument("--signs", default=None, help="Comma 6 ints (±1). If set with --snapshot-only, reuse these signs.")
    args = ap.parse_args()

    reuse_signs = None
    if args.signs:
        reuse_signs = [int(x.strip()) for x in args.signs.split(",")]
        assert len(reuse_signs) == 6, "--signs needs 6 integers (±1) for J1..J6"

    # Decide DXL port
    if args.dxl_port:
        port = args.dxl_port
    elif args.dxl_port_auto:
        port = autodetect_port(args.dxl_port_auto)
    else:
        raise SystemExit("Provide --dxl-port or --dxl-port-auto")

    # Default ID lists if not provided
    if args.ids:
        dxl_ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
    else:
        dxl_ids = [1,2,3,4,5,6] if args.side == "left" else [10,11,12,13,14,15]

    print(f"[info] UR IP={args.ur_ip}  side={args.side}  DXL port={port}  ids={dxl_ids}")
    print(f"[info] Using wrap={args.wrap}°, nudge={args.nudge_deg}°, auto_nudge={args.auto_nudge}")

    # Connect UR
    rr = rtde_receive.RTDEReceiveInterface(args.ur_ip)
    rc = rtde_control.RTDEControlInterface(args.ur_ip) if args.auto_nudge else None

    # Connect DXL
    ph, pk = open_dxl_port(port, args.baud)

    signs: List[int] = []
    offsets_ticks: List[int] = []
    offsets_deg_wrapped: List[float] = []

    print("\n=== STEP 1: Initial snapshot for offsets at CURRENT POSE ===")
    ur_deg0 = get_ur_deg(rr)  # 6 values
    print(f"[ur] deg0={['%.2f'%d for d in ur_deg0]}")

    for j_idx, dxl_id in enumerate(dxl_ids):
        time.sleep(args.sleep)
        ticks = read_pos_ticks(pk, ph, dxl_id)
        deg_ur = ur_deg0[j_idx]

        # First guess (assuming sign = +1) — only for logging
        est_offset_ticks = wrap_ticks(ticks - deg2ticks(deg_ur))
        print(f"\n[joint {j_idx+1} | DXL id {dxl_id}] UR={deg_ur:.2f}°, DXL={ticks} ticks "
              f"(~{ticks2deg(ticks):.2f}°), first offset guess={est_offset_ticks} ticks")

        # === SNAPSHOT-ONLY PATH ===
        if args.snapshot_only:
            sign = reuse_signs[j_idx] if reuse_signs else 1
            offset_ticks = wrap_ticks(ticks - sign * deg2ticks(deg_ur))
        else:
            # === NUDGE PATH (sign detection) ===
            if args.auto_nudge:
                input("  -> Will auto-nudge +%.2f° now; ensure space is clear. Press <Enter> to proceed." % args.nudge_deg)
            else:
                input(f"  -> Manually jog UR joint {j_idx+1} by +{args.nudge_deg}° then press <Enter>")

            ticks_before = read_pos_ticks(pk, ph, dxl_id)
            ur_before = get_ur_deg(rr)[j_idx]

            if args.auto_nudge:
                move_ur_joint(rc, rr, j_idx, +args.nudge_deg)
            else:
                print("  Waiting for your manual nudge…")
                time.sleep(1.0)

            ticks_after = read_pos_ticks(pk, ph, dxl_id)
            ur_after = get_ur_deg(rr)[j_idx]

            d_ur_deg = ur_after - ur_before
            d_dx_ticks = ticks_after - ticks_before
            # Use degrees on both for clarity
            d_dx_deg = ticks2deg(d_dx_ticks)

            print(f"    observed ΔUR={d_ur_deg:.3f}°   ΔDXL_ticks={d_dx_ticks} (~{d_dx_deg:.3f}°)")

            # If UR increases but DXL decreases (or vice versa), sign = -1
            sign = +1 if (d_ur_deg == 0 or d_dx_deg == 0 or (d_ur_deg > 0 and d_dx_deg > 0) or (d_ur_deg < 0 and d_dx_deg < 0)) else -1
            offset_ticks = wrap_ticks(ticks - sign * deg2ticks(deg_ur))

        # Degree representation (wrapped for readability)
        off_deg_wrapped = wrap_angle(ticks2deg(offset_ticks), args.wrap)

        signs.append(sign)
        offsets_ticks.append(offset_ticks)
        offsets_deg_wrapped.append(off_deg_wrapped)

        sgn_txt = "OK" if sign == 1 else "FLIPPED (-1)"
        print(f"    -> sign={sign} [{sgn_txt}]   "
              f"offset_ticks={offset_ticks}   "
              f"(~{off_deg_wrapped:.2f}° wrapped)")

    # Done
    ph.closePort()
    if 'rc' in locals() and rc:
        try:
            rc.disconnect()
        except Exception:
            pass
    rr.disconnect()

    # Emit ready-to-paste tuples in BOTH units
    print("\n=== RESULT: paste into your DynamixelRobotConfig (choose units) ===")
    offsets_ticks_tuple = "(" + ",".join(str(v) for v in offsets_ticks) + ")"
    offsets_deg_tuple   = "(" + ",".join(f"{v:.3f}" for v in offsets_deg_wrapped) + ")"
    signs_tuple         = "(" + ",".join(str(v) for v in signs) + ")"

    print(f"joint_offsets_ticks = {offsets_ticks_tuple}")
    print(f"joint_offsets_deg   = {offsets_deg_tuple}")
    print(f"joint_signs         = {signs_tuple}")

    print("\nTips:")
    print("- Use degrees for configs that expect deg math (most of your earlier code).")
    print("- If your control path consumes ticks directly, use ticks instead.")
    print("- If left/right ID ordering differs, pass --ids to match your wiring.")

if __name__ == "__main__":
    main()
