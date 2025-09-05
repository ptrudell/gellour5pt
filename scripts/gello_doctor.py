#!/usr/bin/env python3
import os, sys, subprocess, json, shutil

DXL_LEFT  = os.environ.get("DXL_LEFT_PORT",  "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0")
DXL_RIGHT = os.environ.get("DXL_RIGHT_PORT", "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0")
UR_LEFT="192.168.1.211"; UR_RIGHT="192.168.1.210"

def run(cmd):
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output

def main():
    print("### GELLO Doctor ###")
    print("\n-- Dynamixel --")
    rc, out = run([sys.executable, "gello/scripts/dxl_doctor.py"])
    print(out.strip())

    print("\n-- UR Robots --")
    rc, out = run([sys.executable, "gello/scripts/ur_doctor.py", UR_LEFT, UR_RIGHT])
    print(out.strip())

    print("\nDone.")
    if __name__ == "__main__":
        main()


