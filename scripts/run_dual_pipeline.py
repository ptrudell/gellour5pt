#!/usr/bin/env python3
import os, subprocess, sys, signal
from pathlib import Path

HERE = Path(__file__).resolve().parent
GELLO = HERE.parent
PREP  = GELLO / "scripts" / "prepare_ur_dashboard.py"
TELE_MOD = "scripts.direct_dual_teleop"   # ← run as a module

def main():
    auto_arm  = "--auto-arm" in sys.argv
    arm_delay = "3.0"
    for a in sys.argv[1:]:
        if a.startswith("--arm-delay="): arm_delay = a.split("=",1)[1]

    ur_vmax = os.environ.get("UR_VMAX","0.05")
    ur_amax = os.environ.get("UR_AMAX","0.8")

    print("[pipeline] preparing UR dashboards…")
    prep_rc = subprocess.call([sys.executable, str(PREP)], env=os.environ)
    if prep_rc != 0:
        print("\n❌ prepare step did not finish cleanly. Not starting teleop.")
        sys.exit(prep_rc)

    env=os.environ.copy(); env["UR_VMAX"]=ur_vmax; env["UR_AMAX"]=ur_amax

    # Build the -m command
    cmd=[sys.executable, "-m", TELE_MOD]
    if auto_arm: cmd += ["--auto-arm", f"--arm-delay={arm_delay}"]

    print(f"\n[pipeline] prepare OK → launching teleop (UR_VMAX={ur_vmax}, UR_AMAX={ur_amax})…")

    try:
        # IMPORTANT: cwd must be the repo root (parent of 'gello/')
        proc = subprocess.Popen(cmd, cwd=GELLO.parent, env=env)  # ← change to GELLO.parent
        def _sigint(_s,_f):
            try: proc.send_signal(signal.SIGINT)
            except Exception: pass
        signal.signal(signal.SIGINT, _sigint)
        rc = proc.wait()
        sys.exit(rc)
    except KeyboardInterrupt:
        sys.exit(130)

if __name__ == "__main__":
    main()
