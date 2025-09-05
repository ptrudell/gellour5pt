#!/usr/bin/env python3
import argparse, math, time, glob, pathlib, importlib.util
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

TPR=4096; ADDR_TORQUE=64; ADDR_GOAL=116

def load_store(path, side):
    p=pathlib.Path(path)
    spec=importlib.util.spec_from_file_location("offsets_store", p)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    e=mod.STORE[side]; return e["ur_ip"], e["port_hint"], e["ids"], e["offsets"], e["signs"]

def autodetect_port(h):
    hits=[p for p in glob.glob("/dev/serial/by-id/*") if h in p]
    if not hits: raise SystemExit(f"no match for {h}")
    return hits[0]

def deg2ticks(deg): return int((deg/360.0)*TPR)%TPR
def enable_torque(pk,ph,ids):
    for i in ids: pk.write1ByteTxRx(ph,i,ADDR_TORQUE,1)
def write_goal(pk,ph,i,t):
    pk.write4ByteTxRx(ph,i,ADDR_GOAL,t%TPR)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--from-store", choices=["left","right"])
    ap.add_argument("--store-path", default="gello/configs/offsets_store.py")
    args=ap.parse_args()
    ur_ip, hint, ids, offs, signs=load_store(args.store_path,args.from_store)

    from ur_rtde import rtde_receive
    rr=rtde_receive.RTDEReceiveInterface(ur_ip)
    ur_deg=[math.degrees(x) for x in rr.getActualQ()]; rr.disconnect()

    port=autodetect_port(hint); ph=PortHandler(port)
    ph.openPort(); ph.setBaudRate(1_000_000); pk=PacketHandler(2.0)
    enable_torque(pk,ph,ids)

    for j,i in enumerate(ids):
        goal=(offs[j]+signs[j]*deg2ticks(ur_deg[j]))%TPR
        write_goal(pk,ph,i,goal); time.sleep(0.02)

    ph.closePort(); print("[ok] GELLO aligned to UR pose.")

if __name__=="__main__": main()

