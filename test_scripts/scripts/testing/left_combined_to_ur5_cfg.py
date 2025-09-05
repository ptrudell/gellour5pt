#!/usr/bin/env python3
import sys, time, math, signal, yaml
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
from rtde_io import RTDEIOInterface

CFG = "configs/ur5_left_u2d2_xl330.yaml" if len(sys.argv) < 2 else sys.argv[1]

# Dynamixel (Protocol 2.0)
ADDR_POS = 132
TPR = 4096
RAD_PER_TICK = 2*math.pi/TPR

# YAML indices (0-based)
WRIST_INDEX = 5   # GELLO idx 5 -> UR J6
GRIP_INDEX  = 6   # GELLO idx 6 -> gripper

# I/O selection
USE_TOOL_DO = False   # True = Tool DOs, False = Standard DOs
IO_INDEX    = 1       # DO number to toggle

# Loop & filters
HZ = 100.0
ALPHA = 0.35
DEADBAND = math.radians(1.5)
OPEN_T = 0.35
CLOSE_T = 0.65

def ok(c,e): return c == COMM_SUCCESS and e == 0

def main():
    with open(CFG, "r") as f:
        cfg = yaml.safe_load(f)
    ap = cfg["agent_params"]; rp = cfg["robot_params"]

    port = ap["port"]; baud = ap["baudrate"]; proto = float(ap["protocol"])
    ids = ap["ids"]; offsets = ap["joint_offsets"]; signs = ap["joint_signs"]
    ur_ip = rp["host"]; acc = float(rp.get("acceleration", 0.8)); vel = float(rp.get("speed", 0.4))

    wrist_id  = ids[WRIST_INDEX]; wrist_off = float(offsets[WRIST_INDEX]); wrist_sgn = int(signs[WRIST_INDEX])
    grip_id   = ids[GRIP_INDEX]

    io_kind = "tool DO" if USE_TOOL_DO else "standard DO"
    print(f"[LEFT combined] port={port} wrist_id={wrist_id} grip_id={grip_id} ur={ur_ip} acc={acc} vel={vel}")
    print(f"J6 offset={wrist_off:.6f} sign={wrist_sgn}; {io_kind} {IO_INDEX}")

    # Dynamixel (read)
    pk = PacketHandler(proto)
    ph = PortHandler(port)
    if not ph.openPort(): sys.exit(f"ERROR: openPort({port})")
    if not ph.setBaudRate(baud): sys.exit(f"ERROR: setBaudRate({baud})")

    # RTDE: control (motion), receive (state), io (outputs) — all on 30004
    rc  = RTDEControlInterface(ur_ip)
    rr  = RTDEReceiveInterface(ur_ip)
    rio = RTDEIOInterface(ur_ip)

    running = True
    def _stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, _stop)

    dt = 1.0 / HZ
    t_next = time.time()

    # Gripper hysteresis state
    mn = None; mx = None; gstate = None  # 0=open, 1=close

    try:
        while running:
            # Read wrist & gripper ticks
            wpos, c1, e1 = pk.read4ByteTxRx(ph, wrist_id,  ADDR_POS)
            gpos, c2, e2 = pk.read4ByteTxRx(ph, grip_id,   ADDR_POS)
            if not ok(c1,e1) or not ok(c2,e2):
                time.sleep(0.01); continue

            # Wrist → UR J6
            q_dx = (wpos % TPR) * RAD_PER_TICK
            q_tgt = wrist_sgn * (q_dx - wrist_off)
            q_now = rr.getActualQ()
            j6 = q_now[WRIST_INDEX]
            if abs(q_tgt - j6) > DEADBAND:
                q_cmd = list(q_now)
                q_cmd[WRIST_INDEX] = (1 - ALPHA) * j6 + ALPHA * q_tgt
                print(f"[J6] now={j6:.3f} tgt={q_tgt:.3f} d={q_tgt-j6:.3f}"); rc.moveJ(q_cmd, acc, vel, True)

            # Gripper → DO with adaptive normalization + hysteresis
            ticks = gpos % TPR
            if mn is None or ticks < mn: mn = ticks
            if mx is None or ticks > mx: mx = ticks
            span = (mx - mn) if (mn is not None and mx is not None) else 0
            if span >= 150:
                norm = (ticks - mn) / float(span)
                if gstate in (None, 0) and norm >= CLOSE_T:
                    if USE_TOOL_DO: rio.setToolDigitalOut(IO_INDEX, True)
                    else:           rio.setStandardDigitalOut(IO_INDEX, True)
                    gstate = 1
                    print(f"[CLOSE] norm={norm:.2f} ticks={ticks} span={span}")
                elif gstate in (None, 1) and norm <= OPEN_T:
                    if USE_TOOL_DO: rio.setToolDigitalOut(IO_INDEX, False)
                    else:           rio.setStandardDigitalOut(IO_INDEX, False)
                    gstate = 0
                    print(f"[OPEN ] norm={norm:.2f} ticks={ticks} span={span}")

            # Rate control
            t_next += dt
            slp = t_next - time.time()
            if slp > 0: time.sleep(slp)
            else: t_next = time.time()

    finally:
        try:
            if USE_TOOL_DO: rio.setToolDigitalOut(IO_INDEX, False)
            else:           rio.setStandardDigitalOut(IO_INDEX, False)
        except: pass
        try: rc.stopScript(); rc.disconnect(); rr.disconnect()
        except: pass
        ph.closePort()
        print("Exited cleanly.")

if __name__ == "__main__":
    main()
