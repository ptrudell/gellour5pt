#!/usr/bin/env python3
import sys, time, math
from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface

ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.211"

def main():
    rc = RTDEControlInterface(ip)
    rr = RTDEReceiveInterface(ip)
    print("Connected to", ip)

    try:
        q = rr.getActualQ()
        print("q[deg] =", [round(v*180/math.pi,2) for v in q])
        tgt = list(q)
        tgt[5] = q[5] + math.radians(2.0)   # +2 deg on J6
        rc.moveJ(tgt, 0.8, 0.4, True)
        time.sleep(1.0)
        back = list(tgt)
        back[5] = q[5]
        rc.moveJ(back, 0.8, 0.4, True)
        time.sleep(1.0)
        print("Done.")
    finally:
        try: rc.stopScript()
        except: pass
        rc.disconnect()
        rr.disconnect()

if __name__ == "__main__":
    main()
