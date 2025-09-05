"""
validate_config.py

Usage:
  python3 scripts/validate_config.py configs/ur5_left_u2d2_xl330.yaml
"""

import sys
import yaml

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/validate_config.py <path/to/config.yaml>")
        sys.exit(1)

    path = sys.argv[1]
    cfg = yaml.safe_load(open(path))

    # Robot params
    rp = cfg.get("robot_params", {})
    assert isinstance(rp.get("host", ""), str) and rp["host"], "robot_params.host missing/empty"
    assert rp.get("speed", 0) > 0, "robot_params.speed must be > 0"
    assert rp.get("acceleration", 0) > 0, "robot_params.acceleration must be > 0"

    # Agent params shapeness
    ap = cfg.get("agent_params", {})
    ids = ap.get("ids", [])
    n = len(ids)
    assert n > 0, "agent_params.ids must be non-empty"
    for key in ["joint_signs", "start_joints", "joint_offsets"]:
        arr = ap.get(key, [])
        assert len(arr) == n, f"{key} length {len(arr)} != ids length {n}"

    print(f"OK: {path}")

if __name__ == "__main__":
    main()
