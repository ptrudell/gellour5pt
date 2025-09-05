#!/usr/bin/env python3
import socket, sys
from typing import Optional
try:
    from rtde_receive import RTDEReceiveInterface
    from rtde_control import RTDEControlInterface
    HAVE_RTDE=True
except Exception:
    HAVE_RTDE=False

DASH_PORT=29999
TIMEOUT=2.0

def dashboard_cmd(host: str, cmd: str) -> Optional[str]:
    try:
        with socket.create_connection((host, DASH_PORT), TIMEOUT) as s:
            s.settimeout(TIMEOUT)
            s.recv(1024)  # hello banner
            s.sendall((cmd+"\n").encode())
            data = s.recv(4096)
            return data.decode(errors="ignore").strip()
    except Exception as e:
        return f"[dash error] {e}"

def check_host(host: str, try_control: bool=False):
    print(f"\n=== UR @ {host} ===")
    for cmd in ("robotmode", "safetystatus", "programState"):
        print(f"{cmd:14s}: {dashboard_cmd(host, cmd)}")
    if not HAVE_RTDE:
        print("RTDE: ur_rtde not installed")
        return
    try:
        rcv = RTDEReceiveInterface(host)
        q = rcv.getActualQ()
        print(f"RTDE receive: ok, q[0]={q[0]:.3f}" if q else "RTDE receive: ok")
    except Exception as e:
        print(f"RTDE receive: ERROR {e}")
        rcv = None
    if try_control:
        try:
            ctrl = RTDEControlInterface(host)
            print("RTDE control: ok (connected)")
            ctrl.disconnect()
        except Exception as e:
            print(f"RTDE control: ERROR {e}")

def main():
    hosts = sys.argv[1:] or ["192.168.1.211","192.168.1.210"]
    try_control = "--control" in hosts
    hosts = [h for h in hosts if h != "--control"]
    for h in hosts:
        check_host(h, try_control=try_control)

    if __name__ == "__main__":
        main()


