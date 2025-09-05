#!/usr/bin/env python3
import os, sys, time
from typing import List, Tuple, Optional
try:
    from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
except Exception as e:
    print(f"[fatal] dynamixel_sdk missing: {e}")
    sys.exit(1)

DEFAULT_LEFT  = os.environ.get("DXL_LEFT_PORT",  "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0")
DEFAULT_RIGHT = os.environ.get("DXL_RIGHT_PORT", "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0")

# Protocol 2.0 addrs (X/XL series)
ADDR_MODEL = 0            # 2B
ADDR_TORQUE_ENABLE = 64   # 1B
ADDR_OP_MODE = 11         # 1B
ADDR_PRESENT_POS = 132    # 4B

PROTO = 2.0
BAUDS = [2_000_000, 1_000_000, 115_200, 57_600]
ID_RANGE = (1, 253)

def open_bus(port: str, baud: int) -> Optional[Tuple[object, object]]:
    ph = PortHandler(port)
    if not ph.openPort():
        return None
    if not ph.setBaudRate(baud):
        ph.closePort()
        return None
    pk = PacketHandler(PROTO)
    return ph, pk

def close_bus(ph):
    try: ph.closePort()
    except: pass

def ping(pk, ph, dxl_id: int) -> bool:
    try:
        _m, rc, err = pk.ping(ph, dxl_id)
        return rc == COMM_SUCCESS and err == 0
    except:
        return False

def read1(pk, ph, dxl_id, addr) -> Tuple[int,int,int]:
    try:
        v, rc, err = pk.read1ByteTxRx(ph, dxl_id, addr)
        return v, rc, err
    except:
        return 0, -1, -1

def read2(pk, ph, dxl_id, addr) -> Tuple[int,int,int]:
    try:
        v, rc, err = pk.read2ByteTxRx(ph, dxl_id, addr)
        return v, rc, err
    except:
        return 0, -1, -1

def read4(pk, ph, dxl_id, addr) -> Tuple[int,int,int]:
    try:
        v, rc, err = pk.read4ByteTxRx(ph, dxl_id, addr)
        return v, rc, err
    except:
        return 0, -1, -1

def scan_port(port: str) -> Tuple[List[int], Optional[int]]:
    print(f"[dxl] scanning {port}")
    for baud in BAUDS:
        bus = open_bus(port, baud)
        if not bus:
            print(f"  @ {baud}: open failed")
            continue
        ph, pk = bus
        lo, hi = ID_RANGE
        found = []
        for i in range(lo, hi+1):
            if ping(pk, ph, i):
                found.append(i)
        print(f"  @ {baud}: IDs={found if found else 'none'}")
        if found:
            # brief details
            for i in found:
                model, rcM, eM = read2(pk, ph, i, ADDR_MODEL)
                mode,  rcO, eO = read1(pk, ph, i, ADDR_OP_MODE)
                pos,   rcP, eP = read4(pk, ph, i, ADDR_PRESENT_POS)
                info = []
                if rcM==COMM_SUCCESS and eM==0: info.append(f"model={model}")
                if rcO==COMM_SUCCESS and eO==0: info.append(f"opmode={mode}")
                if rcP==COMM_SUCCESS and eP==0: info.append(f"pos={pos}")
                print(f"    id={i}: " + (", ".join(info) if info else "ok"))
            close_bus(ph)
            return found, baud
        close_bus(ph)
    return [], None

def main():
    left  = os.environ.get("DXL_LEFT_PORT",  DEFAULT_LEFT)
    right = os.environ.get("DXL_RIGHT_PORT", DEFAULT_RIGHT)
    if not (left and right):
        print("Set DXL_LEFT_PORT and DXL_RIGHT_PORT first")
        sys.exit(2)
    L, Lbaud = scan_port(left)
    R, Rbaud = scan_port(right)
    print("\n=== Summary ===")
    print(f"LEFT:  port={left}  baud={Lbaud}  ids={L if L else 'none'}")
    print(f"RIGHT: port={right} baud={Rbaud}  ids={R if R else 'none'}")
    if not L: print("⚠️ LEFT bus dead or different baud/IDs. Check power/cable/chain.")
    if not R: print("⚠️ RIGHT bus dead or different baud/IDs. Check power/cable/chain.")
    if L and R: print("✅ Both buses alive.")
    if __name__ == "__main__":
        main()
