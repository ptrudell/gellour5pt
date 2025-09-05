import time, math, yaml
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

ADDR=132; TPR=4096; T2R=2*math.pi/TPR

def read_rad(port, ids, baud=1_000_000, proto=2.0):
    pk=PacketHandler(proto); ph=PortHandler(port)
    assert ph.openPort() and ph.setBaudRate(baud), f"open/baud failed: {port}"
    out=[]
    for i in ids:
        pos,c,e = pk.read4ByteTxRx(ph,i,ADDR)
        if c!=COMM_SUCCESS or e!=0: raise RuntimeError(f"read fail id {i}: c={c} e={e}")
        out.append((pos%TPR)*T2R)
    ph.closePort(); return out

def eff(q, signs, offs):
    wrap=lambda a:(a+math.pi)%(2*math.pi)-math.pi
    return [wrap(s*qi+oi) for s,qi,oi in zip(signs,q,offs)]

cfgL=yaml.safe_load(open("configs/ur5_left_u2d2_xl330.yaml"))["agent_params"]
cfgR=yaml.safe_load(open("configs/ur5_right_u2d2_xl330.yaml"))["agent_params"]

for _ in range(100):  # ~10s at 10Hz
    qL = read_rad(cfgL["port"], cfgL["ids"])
    qR = read_rad(cfgR["port"], cfgR["ids"])
    eL = eff(qL, cfgL.get("joint_signs",[1]*len(qL)), cfgL.get("joint_offsets",[0]*len(qL)))
    eR = eff(qR, cfgR.get("joint_signs",[1]*len(qR)), cfgR.get("joint_offsets",[0]*len(qR)))
    print("L:", [round(v,3) for v in eL], " | R:", [round(v,3) for v in eR])
    time.sleep(0.1)
