#!/usr/bin/env python3
import argparse, math
try:
    from ur_rtde import rtde_receive
except ImportError:
    import rtde_receive

ap = argparse.ArgumentParser()
ap.add_argument("--ur-ip", required=True)
args = ap.parse_args()

rr = rtde_receive.RTDEReceiveInterface(args.ur_ip)
q = rr.getActualQ()  # radians
rr.disconnect()
deg = [round(math.degrees(x), 3) for x in q]
print("UR J1..J6 (deg):", ",".join(str(d) for d in deg))

