# ur_minimal_move.py
from rtde_shim import RTDEControlInterface, RTDEReceiveInterface
import sys, time

if len(sys.argv) < 2:
    print("usage: python ur_minimal_move.py <ur_ip>")
    raise SystemExit(2)

ip = sys.argv[1]
rtde_c = RTDEControlInterface(ip)
rtde_r = RTDEReceiveInterface(ip)

# Read current joint positions
q = rtde_r.getActualQ()
print("Current q:", [round(v, 3) for v in q])

# Nudge joint 6 slightly
q2 = list(q)
q2[5] += 0.05  # 0.05 rad ~ 2.87°
rtde_c.moveJ(q2, speed=0.5, acceleration=1.0)
time.sleep(0.2)
rtde_c.stopJ(1.0)

# Clean up
try:
    if hasattr(rtde_c, "disengageSafety"):
        rtde_c.disengageSafety()
except Exception:
    pass
rtde_c.disconnect()
