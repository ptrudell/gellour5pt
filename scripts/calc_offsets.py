"""
calc_offsets.py

Usage:
  python3 scripts/calc_offsets.py configs/ur5_left_u2d2_xl330.yaml

Reads YAML:
  agent_params.port / baudrate / protocol / ids / start_joints
Measures current joints, computes:
  joint_offsets = start_joints - measured_current
Writes joint_offsets back to the YAML.
"""

import sys
import time
import yaml

try:
    from gello.agents.gello_agent import GELLOAgent as _Agent, DynamixelRobotConfig
except ImportError:
    from gello.agents.gello_agent import GelloAgent as _Agent, DynamixelRobotConfig


def _avg_samples(agent, n=10, delay=0.05):
    samples = []
    for _ in range(n):
        samples.append(agent.get_joint_positions())
        time.sleep(delay)
    return [sum(v)/len(v) for v in zip(*samples)]


def _make_agent(port: str, baud: int, protocol: float, ids):
    try:
        dx_cfg = DynamixelRobotConfig(port=port, baudrate=baud, protocol=protocol, ids=ids)
        return _Agent(dynamixel_config=dx_cfg)
    except TypeError:
        return _Agent(port=port)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/calc_offsets.py <path/to/config.yaml>")
        sys.exit(1)

    cfg_path = sys.argv[1]
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    ap = cfg["agent_params"]
    port = ap["port"]
    baud = ap["baudrate"]
    protocol = ap.get("protocol", 2.0)
    ids = ap["ids"]
    desired = ap["start_joints"]

    print(f"\nConnecting GELLO: port={port} baud={baud} protocol={protocol} ids={ids}")
    from gello.agents.gello_agent import GelloAgent as _Agent
    agent = _Agent(port=port)
    agent.connect()

    input("👉 Put the hand in the SAME neutral 'start' pose, then press Enter...")

    measured = _avg_samples(agent)
    offsets = [round(d - m, 6) for d, m in zip(desired, measured)]

    print("Measured:", [round(x, 6) for x in measured])
    print("Offsets :", offsets)

    cfg["agent_params"]["joint_offsets"] = offsets
    with open(cfg_path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    print(f"✅ Wrote offsets to {cfg_path}")


if __name__ == "__main__":
    main()
