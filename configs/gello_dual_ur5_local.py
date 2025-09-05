from gello.hardware.dxl_cfg import DynamixelRobotConfig

LEFT_CFG = type("Cfg", (), {
    "port": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
    "joint_ids": (1,2,3,4,5,6),
    "joint_signs": (1,1,-1,1,1,1),
    "joint_offsets": (0,0,0,0,0,0),
})
RIGHT_CFG = type("Cfg", (), {
    "port": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
    "joint_ids": (10,11,12,13,14,15),
    "joint_signs": (1,1,-1,1,1,1),
    "joint_offsets": (0,0,0,0,0,0),
})
LEFT_GRIPPER_ID = 7
RIGHT_GRIPPER_ID = 16

# gello/configs/gello_dual_ur5_local.py
import os
from gello.hardware.config_types import DynamixelRobotConfig

# --- Required by verifier ---
UR5_LEFT_IP  = os.getenv("UR5_LEFT_IP",  "192.168.1.211")
UR5_RIGHT_IP = os.getenv("UR5_RIGHT_IP", "192.168.1.210")

# --- Your FTDI/U2D2 device paths (confirm with `ls -l /dev/serial/by-id`) ---
LEFT_PORT  = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0"
RIGHT_PORT = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0"

# --- Per-arm configs (fill offsets after calibration) ---
LEFT = DynamixelRobotConfig(
    port=LEFT_PORT,
    baudrate=1_000_000,
    protocol=2.0,
    joint_ids=(1,2,3,4,5,6),
    joint_offsets=(0,0,0,0,0,0),          # TODO: replace with calibrated deg
    joint_signs=(1,1,-1,1,1,1),
    gripper_config=(7, 3150, 1850),       # left gripper id=7, open/close ticks
)

RIGHT = DynamixelRobotConfig(
    port=RIGHT_PORT,
    baudrate=1_000_000,
    protocol=2.0,
    joint_ids=(10,11,12,13,14,15),
    joint_offsets=(0,0,0,0,0,0),          # TODO: replace with calibrated deg
    joint_signs=(1,1,-1,1,1,1),
    gripper_config=(16, 3150, 1850),      # right gripper id=16
)

# Optional map if some scripts expect a port→config dict
CONFIG = {
    LEFT_PORT: LEFT,
    RIGHT_PORT: RIGHT,
}
