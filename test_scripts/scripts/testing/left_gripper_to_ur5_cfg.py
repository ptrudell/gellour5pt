#!/usr/bin/env python3
import sys, time, signal, yaml
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
from rtde_control import RTDEControlInterface

CFG = "configs/ur5_left_u2d2_xl330.yaml" if len(sys.argv)<2 else sys.argv[1]
GRIPPER_INDEX = 6   # index of ID 7 in your ids list (0-based)

ADDR_POS = 132
TPR = 4096
HZ = 50.0
OPEN_THRESH = 0.35
CLOSE_THRESH = 0.65
TOOL_DO = 0  # change to standard DO by swapping to setStandardDigitalOut below

def ok(c,e): return c==COMM_SUCCESS and e==0

def main():
    with open(CFG, "r") as f:
        cfg = yaml.safe_load(f)
    ap = cfg["agent_params"]; rp = cfg["robot_params"]

    port = ap["port"]; baud = ap["baudrate"]; proto = float(ap["protocol"])
    ids = ap["ids"]; ur_ip = rp["host"]

    grip_id = ids[GRIPPER_INDEX]
    print(f"[grip→UR DO] port={port} id={grip_id} ur={ur_ip} tool_do={TOOL_DO}")

    pk = PacketHandler(proto)
    ph = PortHandler(port)
    if not ph.openPort(): sys.exit(f"ERROR: openPort({port})")
    if not ph.setBaudRate(baud): sys.exit(f"ERROR: setBaudRate({baud})")

    ur = RTDEControlInterface(ur_ip)

    running = True
    signal.signal(signal.SIGINT, lambda *_: globals().__setitem__("running", False))

    dt = 1.0/HZ
    t_next = time.time()
    mn = None; mx = None; state = None

    try:
        while running:
            pos, c, e = pk.read4ByteTxRx(ph, grip_id, ADDR_POS)
            if not ok(c,e): time.sleep(0.02); continue
            ticks = pos % TPR

            if mn is None or ticks < mn: mn = ticks
            if mx is None or ticks > mx: mx = ticks
            span = (mx - mn) if (mn is not None and mx is not None) else 0

            if span >= 150:
                norm = (ticks - mn) / float(span)
                if state in (None, 0) and norm >= CLOSE_THRESH:
                    ur.setToolDigitalOut(TOOL_DO, True); state = 1
                    print(f"[CLOSE] norm={norm:.2f} ticks={ticks} span={span}")
                elif state in (None, 1) and norm <= OPEN_THRESH:
                    ur.setToolDigitalOut(TOOL_DO, False); state = 0
                    print(f"[OPEN ] norm={norm:.2f} ticks={ticks} span={span}")
            else:
                if int(time.time()*2) % 10 == 0:
                    print(f"Calibrating… span={span} ticks")

            t_next += dt
            slp = t_next - time.time()
            if slp > 0: time.sleep(slp)
            else: t_next = time.time()
    finally:
        try: ur.setToolDigitalOut(TOOL_DO, False)
        except: pass
        try: ur.stopScript(); ur.disconnect()
        except: pass
        ph.closePort()
        print("Exited cleanly.")

if __name__ == "__main__":
    main()

