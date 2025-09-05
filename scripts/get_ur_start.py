"""
get_ur_start.py

Reads current UR5 joint positions (radians) from ROBOT_IP.
Env:
  ROBOT_IP=192.168.1.211 (left) or 192.168.1.210 (right)
"""

import os
import json
from rtde_shim import RTDEReceiveInterface
def main():
    ip = os.getenv("ROBOT_IP", "192.168.1.210")
    print(f"\n=== UR @ {ip} ===")
    rtde_r = RTDEReceiveInterface(ip)
    try:
        q = rtde_r.getActualQ()  # list of 6 rad
        rounded = [round(v, 6) for v in q]
        print("Joints:", q)
        print("JSON:", json.dumps(rounded))
    finally:
        rtde_r.disconnect()

if __name__ == "__main__":
    main()
