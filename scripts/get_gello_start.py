"""
get_gello_start.py

Reads current GELLO joint positions (radians) for the hand defined by env vars.
Designed to be called from scripts/left.sh or scripts/right.sh.

Env:
  GELLO_PORT=/dev/ttyUSB0 (or /dev/serial/by-id/... from PORT_CONFIG_MAP)
  GELLO_BAUD=1000000
  GELLO_PROTOCOL=2.0
  GELLO_IDS=0,1,2,3,4,5,6
"""

import os
import json
import time

# Support both naming styles for the Agent class in your repo
try:
    from gello.agents.gello_agent import GELLOAgent as _Agent, DynamixelRobotConfig
except ImportError:
    from gello.agents.gello_agent import GelloAgent as _Agent, DynamixelRobotConfig


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return float(default)


def _make_agent(port: str, baud: int, protocol: float, ids):
    """
    Robust agent construction:
    1) Try explicit DynamixelRobotConfig(...)
    2) Fallback to Agent(port=...) (some versions expect port and build config internally)
    """
    # First try: build a config explicitly
    try:
        dx_cfg = DynamixelRobotConfig(port=port, baudrate=baud, protocol=protocol, ids=ids)
        return _Agent(dynamixel_config=dx_cfg)
    except TypeError:
        # Fallback: some versions want just port= (and will look up PORT_CONFIG_MAP)
        return _Agent(port=port)


def main():
    port = os.getenv("GELLO_PORT", "/dev/ttyUSB0")
    baud = int(os.getenv("GELLO_BAUD", "1000000"))
    protocol = _env_float("GELLO_PROTOCOL", 2.0)
    ids = [int(x) for x in os.getenv("GELLO_IDS", "0,1,2,3,4,5,6").split(",")]

    print(f"\n=== GELLO @ {port} | ids={ids} | baud={baud} | protocol={protocol} ===")
    from gello.agents.gello_agent import GelloAgent as _Agent
    agent = _Agent(port=port)
    agent.connect()

    # Optional: torque off so you can set the neutral pose by hand
    try:
        for i in ids:
            agent.set_torque(i, False)
    except Exception:
        pass

    input("👉 Set the hand to the neutral 'start' pose, then press Enter...")

    # Average a few samples to reduce jitter
    samples = []
    for _ in range(5):
        samples.append(agent.get_joint_positions())
        time.sleep(0.05)

    avg = [round(sum(vals)/len(vals), 6) for vals in zip(*samples)]
    print("\n=== GELLO start joints (radians) ===")
    print(avg)
    print("JSON:", json.dumps(avg))


if __name__ == "__main__":
    main()
