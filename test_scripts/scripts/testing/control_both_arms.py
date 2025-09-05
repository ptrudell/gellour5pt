"""
control_both_arms.py

- Connects to TWO UR robots concurrently
- Reads current joints
- (Optional) moves a chosen joint on each arm

Edit the ROBOTS list below (IPs + per-arm params).
"""

from concurrent.futures import ThreadPoolExecutor
import rtde_receive
import rtde_control
import time

# ---- per-arm config ----
ROBOTS = [
    {  # LEFT
        "name": "left",
        "ip": "192.168.1.211",
        "do_move": False,     # set True to enable small move
        "joint_index": -1,    # -1 = J6
        "delta": 0.05,
        "speed": 0.5,
        "accel": 0.5,
    },
    {  # RIGHT
        "name": "right",
        "ip": "192.168.1.210",
        "do_move": False,     # set True to enable small move
        "joint_index": -1,
        "delta": 0.05,
        "speed": 0.5,
        "accel": 0.5,
    },
]
# ------------------------

def read_and_optionally_move(cfg):
    name = cfg["name"]
    ip = cfg["ip"]
    do_move = cfg["do_move"]
    j_idx = cfg["joint_index"]
    delta = cfg["delta"]
    speed = cfg["speed"]
    accel = cfg["accel"]

    print(f"\n=== {name.upper()} @ {ip} ===")
    rtde_r = rtde_receive.RTDEReceiveInterface(ip)
    try:
        q = rtde_r.getActualQ()
        print(f"{name} joints:", q)

        if do_move:
            if not (-6 <= j_idx <= 5):
                raise ValueError("joint_index must be in [-6..5]")
            j = j_idx if j_idx >= 0 else 6 + j_idx
            q_target = list(q)
            q_target[j] += delta

            rtde_c = rtde_control.RTDEControlInterface(ip)
            try:
                print(f"{name}: moving J{j+1} by {delta} rad (speed={speed}, accel={accel})…")
                rtde_c.moveJ(q_target, speed, accel)
            finally:
                rtde_c.disconnect()
    finally:
        rtde_r.disconnect()

def main():
    # Optional safety: tiny stagger so both don’t start motion at the exact same ms
    with ThreadPoolExecutor(max_workers=len(ROBOTS)) as ex:
        futures = []
        for i, cfg in enumerate(ROBOTS):
            # small stagger
            time.sleep(0.05 * i)
            futures.append(ex.submit(read_and_optionally_move, cfg))
        for f in futures:
            try:
                f.result()
            except Exception as e:
                print("Error:", e)

if __name__ == "__main__":
    # Flip the flags above to True when you're ready.
    # Keep speeds small and E-stop handy.
    if any(r["do_move"] for r in ROBOTS):
        print("MOVE MODE ENABLED FOR AT LEAST ONE ARM. Ensure workspace is clear.")
        input("Type Enter to proceed…")
    main()
