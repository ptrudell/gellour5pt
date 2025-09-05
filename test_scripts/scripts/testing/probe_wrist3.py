#!/usr/bin/env python3
# Minimal wrist probe with configurable baud
import argparse, time
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

# Control table (X-series / Protocol 2.0)
ADDR_TORQUE      = 64     # 1 byte
ADDR_OP_MODE     = 11     # 1 byte
ADDR_MIN_LIMIT   = 48     # 4 bytes
ADDR_MAX_LIMIT   = 52     # 4 bytes
ADDR_GOAL_POS    = 116    # 4 bytes (unsigned)
ADDR_PRESENT_POS = 132    # 4 bytes (unsigned)

PROTO = 2.0

def rd1(pk, ph, i, a):
    v, c, e = pk.read1ByteTxRx(ph, i, a)   # (data, comm, err)
    assert c == COMM_SUCCESS, f"comm fail rd1 i={i} rc={c}"
    return v, e

def rd4(pk, ph, i, a):
    v, c, e = pk.read4ByteTxRx(ph, i, a)   # (data, comm, err)
    assert c == COMM_SUCCESS, f"comm fail rd4 i={i} rc={c}"
    return v, e

def wr4(pk, ph, i, a, val):
    c, e = pk.write4ByteTxRx(ph, i, a, int(val))
    assert c == COMM_SUCCESS, f"comm fail wr4 i={i} rc={c}"
    return e

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help="Serial device path (/dev/serial/by-id/...)")
    ap.add_argument("--id", type=int, required=True, help="Dynamixel ID to probe")
    ap.add_argument("--delta", type=int, default=-5, help="Relative tick nudge (default: -5)")
    ap.add_argument("--baud", type=int, default=1_000_000, help="Baud rate (default: 1000000)")
    args = ap.parse_args()

    ph = PortHandler(args.port)
    if not ph.openPort():
        raise SystemExit(f"openPort failed: {args.port}")
    if not ph.setBaudRate(args.baud):
        raise SystemExit(f"setBaudRate({args.baud}) failed on {args.port}")
    pk = PacketHandler(PROTO)

    op, e = rd1(pk, ph, args.id, ADDR_OP_MODE);     print("op_mode:", op, "err:", e)
    tq, e = rd1(pk, ph, args.id, ADDR_TORQUE);      print("torque :", tq, "err:", e)
    mn, e = rd4(pk, ph, args.id, ADDR_MIN_LIMIT);   print("min_lim:", mn, "err:", e)
    mx, e = rd4(pk, ph, args.id, ADDR_MAX_LIMIT);   print("max_lim:", mx, "err:", e)
    pp, e = rd4(pk, ph, args.id, ADDR_PRESENT_POS); print("present:", pp, "err:", e)

    if op not in (3, 4, 5):
        print("ERROR: not a position-capable mode (need 3/4/5).")
        return
    if tq != 1:
        print("ERROR: torque is OFF. Enable torque first.")
        return

    goal = max(mn+10, min(mx-10, pp + int(args.delta)))
    print("try goal:", goal, f"(delta {args.delta})")
    e = wr4(pk, ph, args.id, ADDR_GOAL_POS, goal)
    print("write err:", e)
    time.sleep(0.15)
    pp2, e = rd4(pk, ph, args.id, ADDR_PRESENT_POS); print("present2:", pp2, "err:", e)

if __name__ == "__main__":
    main()
