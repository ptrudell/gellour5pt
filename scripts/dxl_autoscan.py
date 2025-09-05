#!/usr/bin/env python3
import time
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

# Adjust these if needed:
LEFT  = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0"
RIGHT = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0"

BAUDS = [3000000, 2000000, 115200, 1000000, 57600]  # broad sweep
PROTOS = [2.0, 1.0]
ID_RANGE = range(1, 31)

def try_scan(port_path):
    found_any = False
    print(f"\n=== Scan {port_path} ===")
    ph = PortHandler(port_path)
    if not ph.openPort():
        print("  [ERR] openPort failed")
        return False
    for baud in BAUDS:
        if not ph.setBaudRate(baud):
            print(f"  [warn] setBaudRate({baud}) failed; skipping")
            continue
        print(f"  @baud {baud}")
        this_baud_found = []
        for proto in PROTOS:
            pk = PacketHandler(proto)
            hits = []
            # quick spot-check pings: 1, 10, 15 first (fast feedback)
            for tid in [1, 10, 15]:
                try:
                    model, rc, err = pk.ping(ph, tid)
                    if rc == COMM_SUCCESS and err == 0:
                        hits.append((tid, model))
                except Exception:
                    pass
            # If spot-check found nothing, do full range
            if not hits:
                for i in ID_RANGE:
                    try:
                        model, rc, err = pk.ping(ph, i)
                        if rc == COMM_SUCCESS and err == 0:
                            hits.append((i, model))
                    except Exception:
                        pass
            if hits:
                print(f"    proto {proto:.1f}: IDs={[(i,m) for (i,m) in hits]}")
                this_baud_found.extend(hits)
        if this_baud_found:
            found_any = True
    ph.closePort()
    if not found_any:
        print("  (no replies at any baud/proto)")
    return found_any

okL = try_scan(LEFT)
okR = try_scan(RIGHT)
print("\nRESULT:", "LEFT ok" if okL else "LEFT none", "|", "RIGHT ok" if okR else "RIGHT none")
