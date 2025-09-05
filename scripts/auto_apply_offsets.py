#!/usr/bin/env python3
import argparse, subprocess, re, sys, time, pathlib, shutil

CALIB = pathlib.Path(__file__).with_name("calibrate_offsets.py")

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout

def parse_from_calibrator(output: str):
    mo_deg = re.search(r"joint_offsets_deg\s*=\s*\(([^)]+)\)", output)
    mo_sgn = re.search(r"joint_signs\s*=\s*\(([^)]+)\)", output)
    if not (mo_deg and mo_sgn):
        raise RuntimeError("Could not find joint_offsets_deg / joint_signs in calibrator output.\n---\n"+output)
    offs_deg = tuple(float(x.strip()) for x in mo_deg.group(1).split(","))
    signs    = tuple(int(x.strip())   for x in mo_sgn.group(1).split(","))
    return offs_deg, signs

# ---------- fuzzy config patching ----------
# Strategy:
#  - Find candidate "blocks" by scanning for an opening "(" after a line containing a likely key
#    then balancing parentheses until the matching ")".
#  - A block is a candidate if it contains either:
#       joint_ids=(1,2,3,4,5,6) or gripper_config=(7, ...
#       joint_ids=(10,11,12,13,14,15) or gripper_config=(16, ...
#  - Within the chosen block, replace joint_offsets=(...) and joint_signs=(...)

BLOCK_OPEN = re.compile(r'\b[A-Za-z_][A-Za-z0-9_]*\s*\(')  # any callable( ... )
TUPLE_IDS  = {
    'left_exact':  re.compile(r'joint_ids\s*=\s*\(\s*1\s*,\s*2\s*,\s*3\s*,\s*4\s*,\s*5\s*,\s*6\s*\)'),
    'right_exact': re.compile(r'joint_ids\s*=\s*\(\s*10\s*,\s*11\s*,\s*12\s*,\s*13\s*,\s*14\s*,\s*15\s*\)'),
    'left_hint':   re.compile(r'gripper_config\s*=\s*\(\s*7\s*,'),
    'right_hint':  re.compile(r'gripper_config\s*=\s*\(\s*16\s*,'),
}

def find_paren_block(text: str, start_idx: int):
    """Given index at '(' of callable(, return (start,end) of the full (...) span."""
    # find the first '(' from start_idx
    i = text.find('(', start_idx)
    if i == -1: return None
    depth = 0
    for j in range(i, len(text)):
        c = text[j]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return (i, j)
    return None

def enumerate_blocks(cfg_text: str):
    """Yield dicts: {start,end,block,pre_key_line} for any callable( ... ) block."""
    for m in BLOCK_OPEN.finditer(cfg_text):
        # Confirm we have a paren-balanced region
        par = find_paren_block(cfg_text, m.start())
        if not par: 
            continue
        i, j = par
        block = cfg_text[i:j+1]
        # Heuristic: find "key" on previous few lines (for diagnostics only)
        line_start = cfg_text.rfind('\n', 0, m.start()) + 1
        key_line = cfg_text[line_start:m.start()].strip()
        yield {'start': i, 'end': j, 'block': block, 'key_line': key_line}

def classify_block(block: str):
    is_left  = bool(TUPLE_IDS['left_exact'].search(block)  or TUPLE_IDS['left_hint'].search(block))
    is_right = bool(TUPLE_IDS['right_exact'].search(block) or TUPLE_IDS['right_hint'].search(block))
    if is_left and not is_right:  return 'left'
    if is_right and not is_left:  return 'right'
    return None

def replace_offsets_signs(block: str, offsets_deg, signs):
    off_str = "(" + ",".join(f"{x:.3f}" for x in offsets_deg) + ")"
    new_block = re.sub(r"joint_offsets\s*=\s*\([^)]+\)", "joint_offsets=" + off_str, block)
    new_block = re.sub(r"joint_signs\s*=\s*\([^)]+\)",
                       "joint_signs=(" + ",".join(str(x) for x in signs) + ")", new_block)
    if new_block == block:
        # try inserting if not present
        # insert after first '('
        insert_at = block.find('(') + 1
        injected  = f"\n    joint_offsets={off_str},\n    joint_signs=(" + ",".join(str(x) for x in signs) + "),\n"
        new_block = block[:insert_at] + injected + block[insert_at:]
    return new_block

def patch_config_text(cfg_text: str, desired_side: str, offsets_deg, signs, key_pattern=None):
    blocks = list(enumerate_blocks(cfg_text))
    cand = []
    for b in blocks:
        side = classify_block(b['block'])
        if side == desired_side:
            cand.append(b)
    if key_pattern:
        rp = re.compile(key_pattern)
        cand = [b for b in cand if rp.search(b['key_line']) or rp.search(b['block'])]
    if not cand:
        # diagnostics
        diag = ["No matching blocks. Saw:"]
        for b in blocks:
            diag.append(f"- key_line≈{b['key_line']!r}  side_guess={classify_block(b['block'])}")
        raise RuntimeError("\n".join(diag))
    # Pick the first candidate
    picked = cand[0]
    new_block = replace_offsets_signs(picked['block'], offsets_deg, signs)
    patched = cfg_text[:picked['start']] + new_block + cfg_text[picked['end']+1:]
    return patched, picked

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--side", choices=["left","right"], required=True)
    ap.add_argument("--ur-ip", required=True)
    ap.add_argument("--port-hint", required=True, help="Substring for /dev/serial/by-id to auto-pick the port (calibrator)")
    ap.add_argument("--ids", required=True, help="Comma DXL ids in order for this side (e.g., 1,2,3,4,5,6)")
    ap.add_argument("--wrap", type=int, choices=[180,360], default=360)
    ap.add_argument("--signs", default="1,1,-1,1,1,1")
    ap.add_argument("--key-pattern", default=None, help="Optional regex to further constrain which block to patch")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfgp = pathlib.Path(args.config)
    if not cfgp.exists():
        print(f"[error] Config not found: {cfgp}", file=sys.stderr)
        sys.exit(2)

    # Run calibrator non-interactively
    cmd = [sys.executable, str(CALIB),
           "--ur-ip", args.ur_ip,
           "--side", args.side,
           "--dxl-port-auto", args.port_hint,
           "--ids", args.ids,
           "--wrap", str(args.wrap),
           "--snapshot-only",
           "--signs", args.signs]
    rc, out = run(cmd)
    print(out)
    if rc != 0:
        print(f"[error] Calibrator failed (rc={rc}).", file=sys.stderr)
        sys.exit(rc)

    offs_deg, signs = parse_from_calibrator(out)
    print(f"[info] parsed offsets(deg)={offs_deg}")
    print(f"[info] parsed signs       ={signs}")

    orig = cfgp.read_text()
    try:
        patched, picked = patch_config_text(orig, args.side, offs_deg, signs, key_pattern=args.key_pattern)
    except RuntimeError as e:
        print("[error] Patching failed with diagnostics:\n" + str(e), file=sys.stderr)
        sys.exit(3)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = cfgp.with_suffix(cfgp.suffix + f".bak.{stamp}")
    if args.dry_run:
        print(f"[dry-run] Would patch block whose header line is:\n  {picked['key_line']!r}")
        print(f"[dry-run] Backup would be {bak}")
    else:
        shutil.copy2(cfgp, bak)
        cfgp.write_text(patched)
        print(f"[ok] Updated {cfgp} (backup at {bak})")
        print(f"[ok] Patched block whose header line is:\n  {picked['key_line']!r}")

if __name__ == "__main__":
    main()
