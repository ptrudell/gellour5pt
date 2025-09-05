import time
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

CFG = [
  ("/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0", 7),   # LEFT gripper
  ("/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0", 16),  # RIGHT gripper
]
BAUD=1_000_000; PROTO=2.0
ADDR_TQ=64; ADDR_GOAL=116; ADDR_POS=132
DELTA=250  # ticks (~0.38 rad) – adjust if needed

pk = PacketHandler(PROTO)

for port, gid in CFG:
    ph = PortHandler(port); assert ph.openPort() and ph.setBaudRate(BAUD), f"open/baud failed: {port}"
    # torque on
    c,e = pk.write1ByteTxRx(ph, gid, ADDR_TQ, 1); assert c==COMM_SUCCESS and e==0, f"torque on fail {gid}"
    # read current
    pos,c,e = pk.read4ByteTxRx(ph, gid, ADDR_POS); assert c==COMM_SUCCESS and e==0, f"read fail {gid}"
    # open -> close -> back
    for tgt in (pos-DELTA, pos+DELTA, pos):
        c,e = pk.write4ByteTxRx(ph, gid, ADDR_GOAL, int(tgt)%4096)
        assert c==COMM_SUCCESS and e==0, f"goal fail {gid}"
        time.sleep(0.6)
    # torque off
    c,e = pk.write1ByteTxRx(ph, gid, ADDR_TQ, 0); assert c==COMM_SUCCESS and e==0, f"torque off fail {gid}"
    ph.closePort()
print("Grip test done.")
