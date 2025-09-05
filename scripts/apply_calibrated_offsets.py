#!/usr/bin/env python3
"""
Run calibrate_offsets.py and automatically write the results into your config.

Supports Python configs that contain blocks like:
"/dev/serial/by-id/...FTAAMNTI...": DynamixelRobotConfig(
    joint_ids=(...),
    joint_offsets=(...),   # <- degrees recommended
    joint_signs=(...),
    gripper_config=(...),
)

Usage (LEFT):
  python gello/scripts/apply_calibrated_offsets.py \
    --config gello/configs/gello_dual_ur5_local.py \
    --side left \
    --ur-ip 192.168.1.211 \
    --port-hint FTAAMNTI \
    --ids 1,2,3,4,5,6 \
    --wrap 360 \
    --nudge-deg 2 \
    --units deg

Usage (RIGHT):
  python gello/scripts/apply_calibrated_offsets.py \
    --config gello/configs/gello_dual_ur5_local.py \
    --side right \
    --ur-ip 192.168.1.210 \
    --port-hint FTAAMNUF \
    --ids 10,11,12,13,14,15 \
    --wrap 360 \
    --nudge-deg 2 \
    --units deg
"""
import argparse, subprocess, re, sys, time, pathlib, shutil

CALIB = pathlib.Path(__file__).with_name("calibrate_offsets.py")

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout

def parse_offsets_signs(calib_output: str, units: str):
    if units == "deg":
        mo_off = re.search(r"joint_offsets_deg\s*=\s*\(([^)]+)\)", calib_output)
    else:
        mo_off = re.search(r"joint_offsets_ticks\s*=\s*\(([^)]+)\)", calib_output)
    mo_sgn = re.search(r"joint_signs\s*=\s*\(([^)]+)\)", calib_output)
    if not (mo_off and mo_sgn):
        raise RuntimeError("Could not find joint_offsets_(deg|ticks) / joint_signs in calibrator output.\n---\n"+calib_output)

    # Parse offsets with float for deg; int for ticks
    if units == "deg":
        offs = tuple(float(x.strip()) for x in mo_off.group(1).split(","))
    else:
        offs = tuple(int(x.strip()) for x in mo_off.group(1).split(","))
    sgns = tuple(int(x.strip()) for x in mo_sgn.group(1).split(","))
    return offs, sgns

def patch_python_config(cfg_text: str, port_hint: str, joint_offsets, joint_signs):
    """
    Locate the block whose key contains port_hint, then replace joint_offsets=(...) and joint_signs=(...).
    We try to be minimal and preserve formatting.
    """
    key_pat = re.compile(r'(["\'])(/dev/serial/by-id/.*?%s.*?)(\1)\s*:\s*DynamixelRobotConfig\(' % re.escape(port_hint))
    m = key_pat.search(cfg_text)
    if not m:
        raise RuntimeError(f"Could not find a DynamixelRobotConfig entry whose key contains '{port_hint}'.")
    start = m.start()

    i = cfg_text.find("DynamixelRobotConfig(", start)
    if i == -1:
        raise RuntimeError("Malformed config: DynamixelRobotConfig( not found after key.")
    depth = 0
    end = None
    for j in range(i, len(cfg_text)):
        c = cfg_text[j]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                end = j
                break
    if end is None:
        raise RuntimeError("Could not find the end of the DynamixelRobotConfig(...) block.")

    block = cfg_text[i:end+1]

    # Build replacements (pretty-print floats with 3 decimals)
    if isinstance(joint_offsets[0], float):
        off_str = "(" + ",".join(f"{x:.3f}" for x in joint_offsets) + ")"
    else:
        off_str = "(" + ",".join(str(x) for x in joint_offsets) + ")"

    new_block = re.sub(r"joint_offsets\s*=\s*\([^)]+\)",
                       "joint_offsets=" + off_str,
                       block)
    new_block = re.sub(r"joint_signs\s*=\s*\([^)]+\)",
                       "joint_signs=(" + ",".join(str(x) for x in joint_signs) + ")",
                       new_block)

    return cfg_text[:i] + new_block + cfg_text[end+1:]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to your Python config file to modify")
    ap.add_argument("--side", choices=["left","right"], required=True)
    ap.add_argument("--ur-ip", required=True)
    ap.add_argument("--port-hint", required=True, help="Substring of /dev/serial/by-id key (e.g., FTAAMNTI or FTAAMNUF)")
    ap.add_argument("--ids", required=True, help="Comma list of DXL IDs in order for this side")
    ap.add_argument("--wrap", type=int, choices=[180,360], default=360)
    ap.add_argument("--nudge-deg", type=float, default=2.0)
    ap.add_argument("--auto-nudge", action="store_true")
    ap.add_argument("--units", choices=["deg","ticks"], default="deg", help="Which offsets to write into config")
    ap.add_argument("--dry-run", action="store_true", help="Compute and show changes but do not write the file")
    ap.add_argument("--snapshot-only", action="store_true",help="Run calibrator in snapshot mode (no manual/auto nudge).")
    ap.add_argument("--signs", default="1,1,-1,1,1,1",help="Comma 6 ints (±1) for J1..J6; used with --snapshot-only.")

    args = ap.parse_args()

    cfgp = pathlib.Path(args.config)
    if not cfgp.exists():
        print(f"[error] Config not found: {cfgp}", file=sys.stderr)
        sys.exit(2)

    # 1) Run calibrator
    cmd = [sys.executable, str(CALIB),
           "--ur-ip", args.ur_ip, "--side", args.side,
           "--dxl-port-auto", args.port_hint, "--ids", args.ids,
           "--wrap", str(args.wrap), "--nudge-deg", str(args.nudge_deg)]
    if args.auto_nudge:
        cmd.append("--auto-nudge")

    rc, out = run(cmd)
    print(out)
    if rc != 0:
        print(f"[error] Calibrator failed (rc={rc}).", file=sys.stderr)
        sys.exit(rc)

    # 2) Parse results in chosen units
    offs, sgns = parse_offsets_signs(out, args.units)
    print(f"[info] parsed offsets({args.units})={offs}  signs={sgns}")

    # 3) Patch config text
    orig = cfgp.read_text()
    patched = patch_python_config(orig, args.port_hint, offs, sgns)

    # 4) Backup + write (unless dry-run)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = cfgp.with_suffix(cfgp.suffix + f".bak.{stamp}")
    if args.dry_run:
        print(f"[dry-run] Would write to {cfgp}. Backup would be {bak}")
    else:
        shutil.copy2(cfgp, bak)
        cfgp.write_text(patched)
        print(f"[ok] Updated {cfgp} (backup at {bak})")

if __name__ == "__main__":
    main()
