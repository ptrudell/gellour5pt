#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 1) kill anything holding serial
for p in $(lsof -t /dev/serial/by-id/* 2>/dev/null || true); do
  echo "killing serial holder PID $p"; kill -9 "$p" || true
done

# 2) warm the UR dashboards (idempotent)
py() { python - "$@"; }
py <<'PY'
import socket, time
IPs=["192.168.1.211","192.168.1.210"]
def dash(ip,cmd):
    s=socket.socket(); s.settimeout(1.2)
    try:
        s.connect((ip,29999))
        try: s.recv(4096)
        except: pass
        s.sendall((cmd+"\n").encode()); 
        try: s.recv(4096)
        except: pass
    except: pass
    finally:
        try: s.close()
        except: pass
for ip in IPs:
    for cmd in ["stop","close popup","close safety popup","power on","brake release"]:
        dash(ip,cmd)
    time.sleep(0.2)
PY

# 3) optional: cycle usb autosuspend off (if udev not applied yet)
for P in /sys/bus/usb/devices/*/power/control; do
  [[ -w "$P" ]] && echo on | sudo tee "$P" >/dev/null || true
done

echo "✅ reset done"

