from dataclasses import dataclass
from typing import Sequence, Tuple, Optional

@dataclass(frozen=True)
class DynamixelRobotConfig:
    """
    Minimal config (with backward-compatible aliases):
      - port:            Optional bus identifier (e.g., /dev/serial/by-id/…)
      - baud / baudrate: Bus baud (e.g., 1_000_000)
      - proto / protocol: DXL protocol version (e.g., 2.0)
      - joint_ids:       DXL IDs in bus order
      - joint_offsets:   per-joint offsets in DEGREES
      - joint_signs:     +1/-1 to match UR → DXL direction
      - gripper_config:  optional (wrist_joint_id, open_ticks, close_ticks)
    """
    port: Optional[str] = None

    # Back-compat aliases (either name accepted by configs/scripts)
    baud: Optional[int] = None
    baudrate: Optional[int] = None

    proto: Optional[float] = None
    protocol: Optional[float] = None

    joint_ids: Sequence[int] = ()
    joint_offsets: Sequence[float] = ()
    joint_signs: Sequence[int] = ()
    gripper_config: Optional[Tuple[int, int, int]] = None

    def __post_init__(self):
        # Normalize aliases so both names are available
        # Note: frozen dataclass -> use object.__setattr__
        b = self.baudrate if self.baudrate is not None else self.baud
        p = self.protocol if self.protocol is not None else self.proto
        object.__setattr__(self, "baud", b)
        object.__setattr__(self, "baudrate", b)
        object.__setattr__(self, "proto", p)
        object.__setattr__(self, "protocol", p)
