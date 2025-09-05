#!/usr/bin/env python3
import sys, time, math, signal, yaml
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface

CFG = "configs/ur5_left_u2d2_xl330.yaml" if len(sys.argv)<2 else sys.argv[1]
WRIST_INDEX = 5  # UR J6 (0-based); GELLO wrist servo is ID 6 in your YAML ids

ADDR_POS = 132
TPR = 4096
RAD_PER_TICK = 2*math.pi/TPR
HZ = 50.0
ALPHA = 0.2
DEADBAND = math.radians(0.5)

def ok(c,e): return c==COMM_SUCCESS and e==0

def main():
    with open(CFG, "r") as f:
        cfg = yaml.safe_load(f)
    ap = cfg["agent_params"]; rp = cfg["robot_params"]

    port = ap["port"]; baud = ap["baudrate"]; proto = float(ap["protocol"])
    ids = ap["ids"]; offsets = ap["joint_offsets"]; signs = ap["joint_signs"]
    ur_ip = rp["host"]; acc = float(rp.get("acceleration",1.0)); vel = float(rp.get("speed",0.8))

    wrist_id = ids[WRIST_INDEX]     # expects index 5 -> value 6 per your YAML
    wrist_off = float(offsets[WRIST_INDEX])
    wrist_sign = int(signs[WRIST_INDEX])

    print(f"[wrist→UR6] port={port} id={wrist_id} ur={ur_ip} acc={acc} vel={vel}")
    print(f"offset(J6)={wrist_off:.6f}  sign(J6)={wrist_sign}")

    pk = PacketHandler(proto)
    ph = PortHandler(port)
    if not ph.openPort(): sys.exit(f"ERROR: openPort({port})")
    if not ph.setBaudRate(baud): sys.exit(f"ERROR: setBaudRate({baud})")

    rtde_c = RTDEControlInterface(ur_ip)
    rtde_r = RTDEReceiveInterface(ur_ip)

    running = True
    signal.signal(signal.SIGINT, lambda *_: globals().__setitem__("running", False))

    dt = 1.0/HZ
    t_next = time.time()
    try:
        while running:
            pos, c, e = pk.read4ByteTxRx(ph, wrist_id, ADDR_POS)
            if not ok(c,e): time.sleep(0.01); continue
            q_dx = (pos % TPR) * RAD_PER_TICK

            q_target = wrist_sign * (q_dx - wrist_off)

            q_now = rtde_r.getActualQ()
            delta = q_target - q_now[WRIST_INDEX]
            if abs(delta) > DEADBAND:
                q_cmd = list(q_now)
                q_cmd[WRIST_INDEX] = (1-ALPHA)*q_now[WRIST_INDEX] + ALPHA*q_target
                rtde_c.moveJ(q_cmd, acc, vel, True)

            t_next += dt
            slp = t_next - time.time()
            if slp > 0: time.sleep(slp)
            else: t_next = time.time()
    finally:
        try: rtde_c.stopScript(); rtde_c.disconnect(); rtde_r.disconnect()
        except: pass
        ph.closePort()
        print("Exited cleanly.")

if __name__ == "__main__":
    main()
