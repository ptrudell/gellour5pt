#!/usr/bin/env python3
# gello/scripts/verify_gello_ur5_setup.py

import sys, os, json, importlib.util, socket
from pathlib import Path

OK = "\u2705"; FAIL = "\u274C"

SCRIPTS_DIR = Path(__file__).resolve().parent
GELLO_DIR   = SCRIPTS_DIR.parent
CFG_PATH    = GELLO_DIR / "configs" / "gello_dual_ur5_local.py"
OFFSETS     = GELLO_DIR / "configs" / "offsets.json"

def check_imports():
    ok = True
    try:
        import dynamixel_sdk
        print(f"{OK} import dynamixel_sdk")
    except Exception as e:
        print(f"{FAIL} import dynamixel_sdk: {e}"); ok = False

    # RTDE: package or top-level modules
    try:
        from ur_rtde import rtde_receive  # noqa
        print(f"{OK} import ur_rtde")
    except Exception:
        try:
            import rtde_receive  # noqa
            print(f"{OK} import rtde_receive (top-level)")
        except Exception as e:
            print(f"{FAIL} import ur_rtde/rtde_receive: {e}"); ok = False

    try:
        import yaml  # noqa
        print(f"{OK} import yaml")
    except Exception:
        try:
            import ruamel.yaml  # noqa
            print(f"{OK} import ruamel.yaml")
        except Exception as e:
            print(f"{FAIL} import yaml/ruamel: {e}"); ok = False
    return ok

def load_cfg():
    if not CFG_PATH.exists():
        print(f"{FAIL} missing {CFG_PATH}")
        return None
    spec = importlib.util.spec_from_file_location("gello_dual_cfg", CFG_PATH)
    cfg  = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(cfg)  # type: ignore
    print(f"{OK} loaded config from {CFG_PATH}")
    return cfg

def check_offsets():
    if OFFSETS.exists():
        try:
            obj = json.loads(OFFSETS.read_text())
            L, R = obj.get("left"), obj.get("right")
            if isinstance(L, list) and isinstance(R, list) and len(L)==6 and len(R)==6:
                print(f"{OK} offsets.json ok (6 left, 6 right)")
                return True
            print(f"{FAIL} offsets.json wrong shape: {obj}")
            return False
        except Exception as e:
            print(f"{FAIL} read offsets.json: {e}")
            return False
    else:
        print(f"{FAIL} {OFFSETS} missing (warning only; you can still run)")
        return True  # not fatal

def check_serial(path):
    p = Path(path)
    if p.exists():
        print(f"{OK} serial present: {path}"); return True
    print(f"{FAIL} serial NOT found: {path}"); return False

def read_once(port, baud, proto, ids):
    from dynamixel_sdk import PortHandler, PacketHandler, GroupSyncRead, COMM_SUCCESS
    import math
    ADDR_POS, LEN_POS = 132, 4
    TPR=4096; RAD=2*math.pi/TPR
    ph = PortHandler(port)
    assert ph.openPort() and ph.setBaudRate(baud), f"open/baud failed {port}"
    pk = PacketHandler(proto)
    gsr= GroupSyncRead(ph, pk, ADDR_POS, LEN_POS)
    for i in ids: gsr.addParam(i)
    if gsr.txRxPacket()!=COMM_SUCCESS: raise RuntimeError("GroupSyncRead error")
    out=[]
    for i in ids:
        raw=gsr.getData(i, ADDR_POS, LEN_POS); rad=(raw%TPR)*RAD
        if rad>math.pi: rad -= 2*math.pi
        out.append(rad)
    ph.closePort()
    return out

def main():
    print(f"{OK} gello dir: {GELLO_DIR}")
    print(f"{OK} python: {sys.executable}")

    ok = check_imports()
    cfg = load_cfg()
    if cfg is None: return 1

    req = ["LEFT","RIGHT","UR5_LEFT_IP","UR5_RIGHT_IP"]
    miss = [k for k in req if not hasattr(cfg,k)]
    if miss:
        print(f"{FAIL} config missing attrs: {miss}"); return 1
    print(f"{OK} config attrs present: {req}")

    ok &= check_offsets()
    ok &= check_serial(cfg.LEFT.port)
    ok &= check_serial(cfg.RIGHT.port)

    print("\n=== Dynamixel snapshot ===")
    try:
        L = read_once(cfg.LEFT.port, cfg.LEFT.baud, cfg.LEFT.proto, cfg.LEFT.joint_ids)
        R = read_once(cfg.RIGHT.port,cfg.RIGHT.baud,cfg.RIGHT.proto,cfg.RIGHT.joint_ids)
        print(f"{OK} left:  {[round(x,3) for x in L]}")
        print(f"{OK} right: {[round(x,3) for x in R]}")
    except Exception as e:
        print(f"{FAIL} Dynamixel read failed: {e}")
        return 1

    print("\n=== UR5 RTDE check ===")
    try:
        try:
            from ur_rtde import rtde_receive
        except Exception:
            import rtde_receive  # type: ignore
        rrL = rtde_receive.RTDEReceiveInterface(cfg.UR5_LEFT_IP)
        rrR = rtde_receive.RTDEReceiveInterface(cfg.UR5_RIGHT_IP)
        print(f"{OK} UR5 left q:  {[round(v,3) for v in rrL.getActualQ()]}")
        print(f"{OK} UR5 right q: {[round(v,3) for v in rrR.getActualQ()]}")
    except Exception as e:
        print(f"{FAIL} UR5 RTDE check failed: {e}")
        return 1

    print("\n=== RESULT ===")
    if ok:
        print(f"{OK} All checks passed (or only offsets warning)."); return 0
    else:
        print(f"{FAIL} Some non-fatal checks failed; fix before running."); return 1

if __name__ == "__main__":
    raise SystemExit(main())
