"""
auto_gello_calibrate.py  (minimal)

Usage:
  python3 scripts/auto_gello_calibrate.py configs/ur5_left_u2d2_xl330.yaml

Steps:
  1) Reads current GELLO pose => writes agent_params.start_joints
  2) Re-measures => writes agent_params.joint_offsets = start - measured
"""

import sys
import time
import yaml

try:
    from gello.agents.gello_agent import GELLOAgent as _Agent, DynamixelRobotConfig
except ImportError:
    from gello.agents.gello_agent import GelloAgent as _Agent, DynamixelRobotConfig


def _avg_positions(agent, n=10, dt=0.05):
    out = []
    for _ in range(n):
        out.append(agent.get_joint_positions())
        time.sleep(dt)
    return [sum(vals)/len(vals) for vals in zip(*out)]


def _make_agent(port: str, baud: int, protocol: float, ids):
    # In this repo, Agent expects only a port that matches PORT_CONFIG_MAP.
    return _Agent(port=port)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/auto_gello_calibrate.py <path/to/config.yaml>")
        sys.exit(1)

    cfg_path = sys.argv[1]
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    ap = cfg["agent_params"]
    port = ap["port"]
    baud = ap["baudrate"]
    protocol = ap.get("protocol", 2.0)
    ids = ap["ids"]

    print(f"\nConnecting GELLO: port={port} baud={baud} protocol={protocol} ids={ids}")
    from gello.agents.gello_agent import GelloAgent as _Agent
    agent = _Agent(port=port)
    agent.connect()


    # Optional: torque off so you can set the neutral pose by hand
    try:
        for i in ids:
            agent.set_torque(i, False)
    except Exception:
        pass

    input("Place the hand in the NEUTRAL 'start' pose, then press Enter...")

    # 1) capture start_joints
    start = [round(x, 6) for x in _avg_positions(agent, n=8)]
    ap["start_joints"] = start
    print("start_joints:", start)

    # 2) compute offsets at the same pose
    measured = _avg_positions(agent, n=12)
    offsets = [round(d - m, 6) for d, m in zip(start, measured)]
    ap["joint_offsets"] = offsets
    print("joint_offsets:", offsets)

    with open(cfg_path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    print(f"\n✅ Updated {cfg_path}")


if __name__ == "__main__":
    main()
