#!/usr/bin/env python3
# gello/scripts/prepare_ur_dashboard.py
import socket, time, argparse, importlib.util, sys
from pathlib import Path
from typing import Tuple

OK = "✅"; FAIL = "❌"

# Always resolve paths from this file's location
SCRIPTS_DIR = Path(__file__).resolve().parent
GELLO_DIR   = SCRIPTS_DIR.parent
CFG_PATH    = GELLO_DIR / "configs" / "gello_dual_ur5_local.py"

def dash(ip: str, cmd: str, timeout: float = 2.0) -> str:
    """Send a single Dashboard command and return the raw reply text."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((ip, 29999))
    try:
        # swallow the initial hello banner if present
        try:
            s.recv(4096)
        except Exception:
            pass
        s.sendall((cmd + "\n").encode())
        data = s.recv(4096).decode(errors="ignore").strip()
        return data
    finally:
        try: s.close()
        except Exception: pass

def load_cfg():
    if not CFG_PATH.exists():
        raise FileNotFoundError(f"Cannot find config at: {CFG_PATH}")
    spec = importlib.util.spec_from_file_location("gello_dual_cfg", CFG_PATH)
    assert spec and spec.loader, f"Cannot import spec for {CFG_PATH}"
    cfg = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(cfg)                 # type: ignore
    return cfg

def prep_one(ip: str, do_play_stop: bool = True) -> Tuple[bool, str]:
    """Prepare a single UR controller for external control. Returns (ok, summary)."""
    summary = [f"\n=== Preparing UR @ {ip} ==="]

    def q(cmd: str) -> str:
        try:
            r = dash(ip, cmd)
            summary.append(f"{cmd} -> {r}")
            return r
        except Exception as e:
            r = f"ERR: {e}"
            summary.append(f"{cmd} -> {r}")
            return r

    # pre status
    summary.append(f"robotmode(before): {q('robotmode')}")
    summary.append(f"safetystatus: {q('safetystatus')}")
    summary.append(f"programState: {q('programState')}")

    # clear blocks / arm drives
    for cmd in ("close popup", "close safety popup", "unlock protective stop", "stop", "power on", "brake release"):
        q(cmd); time.sleep(0.2)

    if do_play_stop:
        # try play, then stop; if play fails, do a short retry cycle
        reply = q("play"); time.sleep(0.2)
        if "Failed to execute" in (reply or "") or "false" == reply.lower():
            time.sleep(0.5)
            q("stop"); time.sleep(0.2)
            reply2 = q("play"); time.sleep(0.2)
            summary.append(f"play retry → {reply2}")
        q("stop"); time.sleep(0.2)

    # post status
    robotmode    = q("robotmode")
    safetystatus = q("safetystatus")
    programState = q("programState")

    # heuristics
    bad_tokens = ("ProtectiveStop", "Violation", "EMERGENCY_STOP", "SafeguardStop", "Fault")
    looks_bad = any(tok.lower() in (robotmode + safetystatus + programState).lower() for tok in bad_tokens)
    ok_tokens  = ("running", "power on", "normal")
    looks_ok   = any(tok in (robotmode + " " + safetystatus).lower() for tok in ok_tokens)

    ok = (not looks_bad) and looks_ok
    summary.append(f"result: {'OK' if ok else 'NOT OK'}")
    return ok, "\n".join(summary)

def main():
    ap = argparse.ArgumentParser(description="Prepare both UR dashboards for external control")
    ap.add_argument("--no-play", action="store_true", help="Skip the play/stop arming step")
    args = ap.parse_args()

    cfg = load_cfg()
    ips = [cfg.UR5_LEFT_IP, cfg.UR5_RIGHT_IP]

    all_ok = True
    for ip in ips:
        ok, summ = prep_one(ip, do_play_stop=not args.no_play)
        print(summ)
        all_ok &= ok

    print(f"\n{OK if all_ok else FAIL} prepare summary: {'OK' if all_ok else 'NOT OK'}")
    sys.exit(0 if all_ok else 2)

if __name__ == "__main__":
    main()
