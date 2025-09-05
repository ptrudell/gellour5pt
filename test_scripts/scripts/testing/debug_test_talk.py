"""
Minimal UR5 RTDE script:
- Read current joint positions once
- Move last joint (J6) by a small delta
"""
import sys
sys.path.append('/home/shared/gellour5pt/scripts')
from rtde_shim import RTDEReceiveInterface
from rtde_shim import RTDEControlInterface

ROBOT_IP = "192.168.1.210"   # <-- change this to your UR5's IP
DELTA = 0.05                # radians to add to J6
SPEED = 0.5                 # rad/s
ACCEL = 0.5                 # rad/s^2

def main():
    # Connect
    rtde_r = RTDEReceiveInterface(ROBOT_IP)
    rtde_c = RTDEControlInterface(ROBOT_IP)

    # Read current joint positions
    q_now = rtde_r.getActualQ()
    print("Current joint positions:", q_now)

    # Prepare new target
    q_target = list(q_now)
    q_target[-1] += DELTA

    # Send move command
    rtde_c.moveJ(q_target, SPEED, ACCEL)

    # Disconnect
    rtde_c.disconnect()
    rtde_r.disconnect()

if __name__ == "__main__":
    main()