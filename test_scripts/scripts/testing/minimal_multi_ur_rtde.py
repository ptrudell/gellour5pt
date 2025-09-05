"""
minimal_multi_ur_rtde.py

- Reads current joint positions from a UR robot.
- Optional: move last joint (J6) by a small delta.
- Robot IP can be overridden via ROBOT_IP environment variable.

Usage:
  ROBOT_IP=192.168.1.211 python3 minimal_multi_ur_rtde.py
  ROBOT_IP=192.168.1.210 python3 minimal_multi_ur_rtde.py
"""

import os
import rtde_receive
import rtde_control

# --- user settings (defaults) ---
ROBOT_IP = os.getenv("ROBOT_IP", "192.168.1.210")
DO_MOVE = False          # set True to enable motion
JOINT_INDEX = -1         # -1 = J6, 0..5 also allowed
DELTA = 0.05             # radians to add to chosen joint
SPEED = 0.5              # rad/s
ACCEL = 0.5              # rad/s^2
# -------------------------------

def main():
    print(f"\n=== Robot @ {ROBOT_IP} ===")
    rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
    try:
        q_now = rtde_r.getActualQ()
        print("Current joint positions:", q_now)

        if DO_MOVE:
            if not (-6 <= JOINT_INDEX <= 5):
                raise ValueError("JOINT_INDEX must be in [-6..5]")
            j = JOINT_INDEX if JOINT_INDEX >= 0 else 6 + JOINT_INDEX
            q_target = list(q_now)
            q_target[j] += DELTA
            print(f"Moving joint J{j+1} by {DELTA} rad...")
            rtde_c = rtde_control.RTDEControlInterface(ROBOT_IP)
            try:
                rtde_c.moveJ(q_target, SPEED, ACCEL)
            finally:
                rtde_c.disconnect()
    finally:
        rtde_r.disconnect()

if __name__ == "__main__":
    main()
