#!/usr/bin/env python3
import argparse, time, math, glob, pathlib, importlib.util, sys, json
from typing import List
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

TPR=4096
ADDR_PRESENT=132
ADDR_TORQUE=64
ADDR_GOAL=116

def ticks_to_ur_deg(ticks, offset, sign):
    return sign * (((ticks - offset) % TPR) * 360.0 / TPR)

def deg_to_ticks(deg):
    return int((deg/360.0)*TPR) % TPR

# -------- helpers --------
def load_store(path, side):
    p=pathlib.Path(path)
    if not p.exists():
        raise SystemExit(f"[err] store not found: {p}")
    spec=importlib.util.spec_from_file_location("offsets_store", p)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    e=mod.STORE[side]
    return e["ur_ip"], e["port_hint"], list(e["ids"]), list(e["offsets"]), list(e["signs"])

def save_store(path, side, ids, offsets, signs, ur_ip=None, port_hint=None):
    p=pathlib.Path(path)
    spec=importlib.util.spec_from_file_location("offsets_store", p)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    if side not in mod.STORE:
        mod.STORE[side]={}
    mod.STORE[side]["ids"]=list(ids)
    mod.STORE[side]["offsets"]=list(offsets)
    mod.STORE[side]["signs"]=list(signs)
    if ur_ip: mod.STORE[side]["ur_ip"]=ur_ip
    if port_hint: mod.STORE[side]["port_hint"]=port_hint
    # write back as python
    txt = "# Auto-generated offsets/signs for GELLO <-> UR5 (teleop_offset_tuner)\nSTORE = " + json.dumps(mod.STORE, indent=2) + "\n"
    p.write_text(txt)
    print(f"[ok] wrote {p} (updated {side} offsets/signs)")

def autodetect_port(h):
    hits=[p for p in glob.glob("/dev/serial/by-id/*") if h in p]
    if not hits: raise SystemExit(f"[err] no /dev/serial/by-id match for '{h}'")
    return hits[0]

def read_ticks(pk,ph,i):
    v,rc,err=pk.read4ByteTxRx(ph,i,ADDR_PRESENT)
    if rc!=COMM_SUCCESS or err!=0: raise SystemExit(f"[err] DXL read id={i} rc={rc} err={err}")
    return v % TPR

def ticks_to_ur_deg(ticks, offset, sign):
    # inverse of: goal = offset + sign * (deg/360)*TPR
    return sign * (((ticks - offset) % TPR) * 360.0 / TPR)

def deg_to_ticks(deg): return int((deg/360.0)*TPR) % TPR
def wrap180(d): 
    x=(d+180.0)%360.0-180.0
    return x

def enable_torque(pk,ph,ids,on=True):
    for i in ids:
        rc,err=pk.write1ByteTxRx(ph,i,ADDR_TORQUE,1 if on else 0)
        if rc!=COMM_SUCCESS or err!=0: raise SystemExit(f"[err] torque {'on' if on else 'off'} failed id={i}")

def write_goal(pk,ph,i,t):
    t%=TPR
    rc,err=pk.write4ByteTxRx(ph,i,ADDR_GOAL,t)
    if rc!=COMM_SUCCESS or err!=0: raise SystemExit(f"[err] goal write failed id={i}")

# -------- main --------
def main():
    ap=argparse.ArgumentParser(description="Temporary teleop tuner to refine offsets/signs live (GELLO leads → UR).")
    ap.add_argument("--side", choices=["left","right"], required=True)
    ap.add_argument("--store-path", default="gello/configs/offsets_store.py")
    ap.add_argument("--hz", type=float, default=125.0)
    ap.add_argument("--step", type=int, default=8, help="offset step per '+'/'-' in ticks (~0.7° for 8 ticks)")
    ap.add_argument("--bigstep", type=int, default=80, help="offset step per '>'/'<' in ticks (~7°)")
    ap.add_argument("--command-ur", action="store_true", help="actually command UR (requires remote control enabled).")
    ap.add_argument("--align-first", action="store_true", help="move GELLO to current UR pose before streaming.")
    args=ap.parse_args()

    # load calibration
    ur_ip, hint, ids, offsets, signs = load_store(args.store_path, args.side)
    deltas = [0]*6      # live offset deltas (ticks)
    sign_adj = [0]*6    # 0 or 1 toggles; applied as (-1)**sign_adj[j]
    sel = 0             # selected joint index

    # UR RTDE
    try:
        from ur_rtde import rtde_receive, rtde_control
    except ImportError:
        import rtde_receive, rtde_control
    rr=rtde_receive.RTDEReceiveInterface(ur_ip)
    rc=rtde_control.RTDEControlInterface(ur_ip) if args.command_ur else None

    # DXL I/O
    port=autodetect_port(hint)
    ph=PortHandler(port); 
    if not ph.openPort(): raise SystemExit(f"[err] openPort {port}")
    if not ph.setBaudRate(1_000_000): raise SystemExit("[err] setBaudRate 1e6")
    pk=PacketHandler(2.0)

    # (optional) align GELLO to current UR pose so both start matched
    if args.align_first:
        enable_torque(pk,ph,ids,True)
        ur_deg=[math.degrees(x) for x in rr.getActualQ()]
        for j,i in enumerate(ids):
            goal=(offsets[j] + signs[j]*deg_to_ticks(ur_deg[j])) % TPR
            write_goal(pk,ph,i,goal)
            time.sleep(0.02)
        print("[ok] aligned GELLO to UR current pose.")

    print("\n[controls]")
    print("  jN  -> select joint N (1..6)")
    print("   +  -> increase offset delta by step      |   -  -> decrease by step")
    print("   >  -> increase by BIG step               |   <  -> decrease by BIG step")
    print("   s  -> toggle SIGN for selected joint     |   r  -> reset all deltas/sign toggles")
    print("   w  -> write deltas+signs back to store   |   q  -> quit")
    print("  tip: run with --command-ur to actually command UR; otherwise it's preview only.\n")

    dt=1.0/args.hz
    t_last_print=0.0

    try:
        while True:
            # 1) read DXL ticks
            ticks=[read_ticks(pk,ph,i) for i in ids]
            # 2) compute estimated UR targets from DXL using (offset + delta) and (sign * sign_toggle)
            ur_est_deg=[]
            for j in range(6):
                sgn = signs[j] * (-1 if sign_adj[j] else 1)
                off = (offsets[j] + deltas[j]) % TPR
                ur_est_deg.append(ticks_to_ur_deg(ticks[j], off, sgn))

            ur_est_rad=[math.radians(d) for d in ur_est_deg]

            # 3) measure UR actual
            ur_act_rad = list(rr.getActualQ())
            ur_act_deg = [math.degrees(v) for v in ur_act_rad]

            # 4) compute per-joint error (deg)
            err_deg = [wrap180(ur_act_deg[j] - ur_est_deg[j]) for j in range(6)]

            # 5) optionally command UR toward ur_est_rad
            if args.command_ur and rc:
                # simple servoJ target
                rc.servoJ(ur_est_rad, 0.6, 3.0, dt, 0.1, 300)

            # 6) print status ~5Hz
            now=time.time()
            if now - t_last_print > 0.2:
                t_last_print = now
                def fmt(vs): return "["+", ".join(f"{v:+6.2f}" for v in vs)+"]"
                print(f"\rsel J{sel+1}  "
                      f"deltas(ticks)={[d for d in deltas]}  signs*={['-' if a else '+' for a in sign_adj]}  "
                      f"err(deg)={fmt(err_deg)}", end="", flush=True)

            # 7) non-blocking user input (line mode; hit ENTER after a command)
            #    read a pending command if any
            import select
            r,_,_=select.select([sys.stdin], [], [], 0)
            if r:
                line=sys.stdin.readline().strip()
                if not line: 
                    continue
                if line.startswith("j") and len(line)>=2 and line[1].isdigit():
                    n=int(line[1])-1
                    if 0<=n<6: sel=n
                    else: print("\n[warn] joint index must be 1..6")
                elif line == "+":
                    deltas[sel]+=args.step
                elif line == "-":
                    deltas[sel]-=args.step
                elif line == ">":
                    deltas[sel]+=args.bigstep
                elif line == "<":
                    deltas[sel]-=args.bigstep
                elif line == "s":
                    sign_adj[sel]=0 if sign_adj[sel] else 1
                elif line == "r":
                    deltas=[0]*6; sign_adj=[0]*6
                elif line == "w":
                    # apply deltas/signs to base values and write to store
                    new_off=[(offsets[j]+deltas[j])%TPR for j in range(6)]
                    new_sgn=[signs[j]*(-1 if sign_adj[j] else 1) for j in range(6)]
                    save_store(args.store_path, args.side, ids, new_off, new_sgn, ur_ip, hint)
                    # commit them as new base and reset deltas/toggles
                    offsets=new_off; signs=new_sgn; deltas=[0]*6; sign_adj=[0]*6
                    print("\n[ok] saved to store; deltas reset.")
                elif line == "q":
                    print("\n[bye]"); break
                else:
                    print("\n[cmds] j1..j6, +, -, >, <, s, r, w, q")

            time.sleep(dt)
    except KeyboardInterrupt:
        print("\n[ctrl-c] exiting…")
    finally:
        try:
            if args.command_ur and rc: rc.speedStop()
        except Exception:
            pass
        rr.disconnect()
        ph.closePort()
        print("[stopped]")

if __name__=="__main__":
    main()
