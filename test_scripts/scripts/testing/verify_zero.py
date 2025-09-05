import sys, math, yaml
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR_PRESENT_POSITION=132; TPR=4096; T2R=2*math.pi/TPR
def read_rad(port, ids, baud=1_000_000, proto=2.0):
    pk=PacketHandler(proto); ph=PortHandler(port)
    assert ph.openPort() and ph.setBaudRate(baud), f"open/baud failed: {port}"
    out=[]
    for i in ids:
        pos,c,e = pk.read4ByteTxRx(ph,i,ADDR_PRESENT_POSITION)
        if c!=COMM_SUCCESS or e!=0: raise RuntimeError(f"read fail id {i}: c={c} e={e}")
        out.append((pos%TPR)*T2R)
    ph.closePort(); return out

def wrap(a): return (a+math.pi)%(2*math.pi)-math.pi

if len(sys.argv)!=2:
    print("Usage: python3 scripts/verify_zero.py <config.yaml>"); sys.exit(1)
cfg=yaml.safe_load(open(sys.argv[1]))
a=cfg["agent_params"]
port=a["port"]; ids=a["ids"]
signs=a.get("joint_signs",[1]*len(ids))
offs=a.get("joint_offsets",[0]*len(ids))
q=read_rad(port, ids)
eff=[wrap(s*q_i + o) for s,q_i,o in zip(signs,q,offs)]
print("raw (rad):", [round(v,4) for v in q])
print("offsets  :", [round(v,4) for v in offs])
print("effective:", [round(v,4) for v in eff])
print("max |eff|:", round(max(abs(v) for v in eff), 6))
