import sys, json, math
import yaml
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_PRESENT_POSITION = 132   # XL-330, 4 bytes
TICKS_PER_REV = 4096
TICK_TO_RAD = 2*math.pi / TICKS_PER_REV

def read_positions_rad(port: str, ids, baud=1_000_000, proto=2.0):
    pk = PacketHandler(proto)
    ph = PortHandler(port)
    if not (ph.openPort() and ph.setBaudRate(baud)):
        raise RuntimeError(f"open/baud failed: {port}")
    out = []
    for dxid in ids:
        pos, c, e = pk.read4ByteTxRx(ph, dxid, ADDR_PRESENT_POSITION)
        if c != COMM_SUCCESS or e != 0:
            ph.closePort()
            raise RuntimeError(f"read fail on ID {dxid}: c={c} e={e}")
        out.append((pos % TICKS_PER_REV) * TICK_TO_RAD)
    ph.closePort()
    return out

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/auto_gello_calibrate_sdk.py <config.yaml>")
        return 1
    cfg_path = sys.argv[1]
    cfg = yaml.safe_load(open(cfg_path))
    a = cfg["agent_params"]
    port = a["port"]
    ids = a["ids"]
    joint_signs = a.get("joint_signs", [1]*len(ids))
    q = read_positions_rad(port, ids)
    q = [s*qq for s, qq in zip(joint_signs, q)]
    a["start_joints"] = [round(v, 6) for v in q]
    if "joint_offsets" not in a or not a["joint_offsets"]:
        a["joint_offsets"] = [0]*len(ids)
    yaml.safe_dump(cfg, open(cfg_path, "w"))
    print("Updated", cfg_path)
    print("start_joints:", json.dumps(a["start_joints"]))
    print("joint_offsets:", json.dumps(a["joint_offsets"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
