#!/usr/bin/env python3
import json, sys
from pathlib import Path

# example: pass 12 numbers on the CLI, left then right (degrees)
# python calibration/write_offsets_json.py 0 0 0 0 0 0  1.2 -0.5 0 0 0 0
if __name__ == "__main__":
    vals = [float(x) for x in sys.argv[1:]]
    if len(vals) != 12:
        print("need 12 numbers: left(6) right(6) in degrees")
        sys.exit(1)
    left = vals[:6]; right = vals[6:]
    out = {"left": left, "right": right}
    Path("configs").mkdir(exist_ok=True)
    Path("configs/offsets.json").write_text(json.dumps(out, indent=2))
    print("wrote configs/offsets.json")
