#!/usr/bin/env python3
import time, math, argparse, sys, glob
from typing import Tuple, List

# --- UR RTDE ---
try:
    from ur_rtde import rtde_receive
except ImportError:
    import rtde_receive

# --- Dynamixel SDK ---
try:
    from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
except ImportError:
    print("ERROR: pip install dynamixel-sdk", file=sys.stderr)
    sys.exit(1)

# --- Offsets/signs store ---
try:
    from gello.configs.offsets_store import STORE
except Exception as e:
    print("ERROR loading gello/configs/offsets_store.py:", e, file=sys.stderr)
    sys.exit(1)

TPR = 4096  # ticks/rev

def autodetect_port(hint: str) -> str:
    hits = [p for p in glob.glob("/dev/serial/by-id/*") if hint in p]
    if not hits:
        raise RuntimeError(f"No serial/by-id matches '{hint}'")
    return hits[0]

def open_dxl(port: str, baud: int = 1_000_000) -> Tuple[PortHandler, PacketHandler]:
    ph = PortHandler(port)
    if not ph.openPort():
        raise RuntimeError(f"openPort failed: {port}")
    if not ph.setBaudRate(baud):
        raise RuntimeError(f"setBaudRate failed: {baud}")
    return ph, PacketHandler(2.0)

def read_pos_ticks(pk: PacketHandler, ph: PortHandler, dxl_id: int) -> int:
    pos, rc, err = pk.read4ByteTxRx(ph, dxl_id, 132)
    if rc != COMM_SUCCESS or err != 0:
        raise RuntimeError(f"read pos failed id={dxl_id} rc={rc} err={err}")
    return pos

def write_pos_ticks(pk: PacketHandler, ph: PortHandler, dxl_id: int, ticks: int):
    # Goal Position (4B) = addr 116 for X-series (OperatingMode Position)
    rc, err = pk.write4ByteTxRx(ph, dxl_id, 116, int(ticks) % TPR)
    if rc != COMM_SUCCESS or err != 0:
        raise RuntimeError(f"write pos failed id={dxl_id} rc={rc} err={err}")

def ticks2deg(t: float) -> float: return (t / TPR) * 360.0
def deg2ticks(d: float) -> float: return (d / 360.0) * TPR
def wrap180(d: float) -> float:    # wrap to [-180,180)
    x = (d + 180.0) % 360.0 - 180.0
    return x

def main():
    ap = argparse.ArgumentParser(description="UR leads; mirror to GELLO (one joint at a time).")
    ap.add_argument("--side", choices=["left","right"], required=True)
    ap.add_argument("--rate", type=float, default=50.0, help="Hz loop")
    ap.add_argument("--max-step-deg", type=float, default=2.0, help="per-cycle deg limit (smoothing)")
    ap.add_argument("--joint", type=int, default=1, help="selected joint (1..6) to mirror")
    args = ap.parse_args()

    cfg = STORE[args.side]
    ur_ip = cfg.get("ur_ip")
    ids = cfg.get("ids")
    signs = cfg.get("signs")
    offsets = cfg.get("offsets")
    port = autodetect_port(cfg.get("port_hint"))

    ph, pk = open_dxl(port)
    rr = rtde_receive.RTDEReceiveInterface(ur_ip)

    sel = max(1, min(6, args.joint)) - 1     # 0-based
    dt = 1.0 / args.rate
    max_step_ticks = deg2ticks(args.max_step_deg)

    print(f"[ok] UR={ur_ip} DXL={port} side={args.side} ids={ids}")
    print("[controls] while running, change the selected joint by re-running with --joint N")
    print(f"[mode] UR leads. Mirroring JOINT J{sel+1} only. Step limit={args.max_step_deg}°/cycle, shortest path (≤180°). Ctrl-C to stop.")

    try:
        while True:
            ur_deg = [math.degrees(v) for v in rr.getActualQ()]  # 6 floats
            # compute desired DXL angle for selected joint using sign/offset
            j = sel
            desired_deg = wrap180(signs[j]*ur_deg[j] + ticks2deg(offsets[j]))
            # current DXL ticks/deg
            cur_ticks = read_pos_ticks(pk, ph, ids[j])
            cur_deg = ticks2deg(cur_ticks)
            # shortest-path error in degrees (≤180 by wrap180)
            err_deg = wrap180(desired_deg - cur_deg)
            # rate-limit per cycle
            step_deg = max(-args.max_step_deg, min(args.max_step_deg, err_deg))
            next_deg = cur_deg + step_deg
            next_ticks = int(round(deg2ticks(next_deg)))
            write_pos_ticks(pk, ph, ids[j], next_ticks)

            # light telemetry
            sys.stdout.write(f"\r[J{j+1}] ur={ur_deg[j]:7.2f}°  dxl={cur_deg:7.2f}°  des={desired_deg:7.2f}°  err={err_deg:7.2f}°  step={step_deg:6.2f}°")
            sys.stdout.flush()
            time.sleep(dt)
    except KeyboardInterrupt:
        print("\n[stopped]")
    finally:
        ph.closePort(); rr.disconnect()

if __name__ == "__main__":
    main()

