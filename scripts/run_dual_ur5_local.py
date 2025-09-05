#!/usr/bin/env python3
import os, subprocess, time, sys
from pathlib import Path

def add_project_root():
    scripts_dir = Path(__file__).resolve().parent
    project_root = scripts_dir.parent  # .../gello
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    # also set working directory to project root so relative paths match
    os.chdir(project_root)
    return project_root

def main():
    project_root = add_project_root()
    print(f"[launcher] project root: {project_root}")

    UR5_LEFT_IP  = os.getenv("UR5_LEFT_IP",  "192.168.0.101")
    UR5_RIGHT_IP = os.getenv("UR5_RIGHT_IP", "192.168.0.102")
    GELLO_CFG_MODULE = os.getenv("GELLO_CFG_MODULE", "configs.gello_dual_ur5_local")

    # optional clamps for first run
    env = os.environ.copy()
    env["GELLO_CFG_MODULE"] = GELLO_CFG_MODULE
    env.setdefault("UR_VMAX", "0.3")
    env.setdefault("UR_AMAX", "2.0")

    # Launch UR5 nodes
    left = subprocess.Popen(
        ["python", "experiments/launch_nodes.py", "--robot", "ur5", "--ip", UR5_LEFT_IP, "--name", "left"],
        env=env
    )
    time.sleep(1)
    right = subprocess.Popen(
        ["python", "experiments/launch_nodes.py", "--robot", "ur5", "--ip", UR5_RIGHT_IP, "--name", "right"],
        env=env
    )
    time.sleep(2)

    # Run env with gello agent
    try:
        subprocess.run(["python", "experiments/run_env.py", "--agent", "gello", "--hz", "125"],
                       env=env, check=True)
    finally:
        for p in (left, right):
            p.terminate()
        for p in (left, right):
            try:
                p.wait(timeout=3)
            except Exception:
                p.kill()

if __name__ == "__main__":
    sys.exit(main())
