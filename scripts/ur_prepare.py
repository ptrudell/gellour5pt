# gello/scripts/ur_prepare.py
# Minimal, dependency-free UR dashboard prepare

import socket, time

READY_TIMEOUT_S = 60
PLAY_RETRIES = 3
RETRY_SLEEP = 1.5

def _dash(ip, cmd, timeout=1.5):
    """Send a single Dashboard command and return the response string (best-effort)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, 29999))
        try: s.recv(4096)  # banner
        except: pass
        s.sendall((cmd + "\n").encode())
        try:
            return s.recv(4096).decode(errors="ignore")
        except:
            return ""
    except Exception:
        return ""
    finally:
        try: s.close()
        except: pass

def _robotmode(ip):     return str(_dash(ip, "robotmode"))
def _safetystatus(ip):  return str(_dash(ip, "safetystatus"))
def _close(ip):
    _dash(ip, "close popup"); _dash(ip, "close safety popup")

def _unlock(ip):        _dash(ip, "unlock protective stop")
def _power_on(ip):      _dash(ip, "power on")
def _brake_release(ip): _dash(ip, "brake release")
def _stop(ip):          _dash(ip, "stop")
def _play(ip):          _dash(ip, "play")
def _load(ip, prog):    _dash(ip, f"load {prog}")

def _wait_for_normal(ip, timeout_s=READY_TIMEOUT_S):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        mode = _robotmode(ip)
        saf  = _safetystatus(ip)
        if "RUNNING" in mode and "NORMAL" in saf:
            return True
        if "EMERGENCY_STOP" in saf:
            _close(ip); _unlock(ip)  # harmless if not needed
        time.sleep(0.5)
    return False

def prepare_ur(ip, program="freedrive.urp"):
    """
    Idempotent prepare:
      - stop/clear popups
      - power on + brake release
      - wait for RUNNING/NORMAL
      - (optional) load program
      - try play a few times, then stop (to prove dashboard is responsive)
    Returns: (ok: bool, msg: str)
    """
    try:
        _stop(ip)
        _close(ip)
        _power_on(ip)
        _brake_release(ip)

        if not _wait_for_normal(ip):
            return False, "Timed out waiting for NORMAL"

        # Load is optional; ignore errors if program not present
        _load(ip, program)

        ok = False
        for _ in range(PLAY_RETRIES):
            _play(ip)
            # brief settle; if socket was touchy, retry helps
            time.sleep(RETRY_SLEEP)
            ok = True
            break

        _stop(ip)  # leave robot ready but not playing
        if not ok:
            return False, "Failed to execute play after retries"
        return True, "OK"
    except Exception as e:
        return False, f"prepare exception: {e}"
