#!/usr/bin/env python3
"""
UR + Dynamixel Robot implementation following GELLO patterns.
Provides a unified interface for controlling UR robots with Dynamixel GELLO arms.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# Dynamixel SDK imports
try:
    from dynamixel_sdk import (
        COMM_SUCCESS,
        GroupBulkRead,
        GroupSyncRead,
        GroupSyncWrite,
        PacketHandler,
        PortHandler,
    )
except ImportError as e:
    print(f"[error] Failed to import dynamixel_sdk: {e}")
    raise

# UR RTDE imports
try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
except Exception:
    try:
        from ur_rtde import rtde_control, rtde_receive

        RTDEControlInterface = rtde_control.RTDEControlInterface
        RTDEReceiveInterface = rtde_receive.RTDEReceiveInterface
    except Exception as e:
        print(f"[error] Could not import UR RTDE modules: {e}")
        raise


class DynamixelDriver:
    """Optimized Dynamixel driver with retry logic and caching."""

    # Control table addresses
    ADDR_TORQUE_ENABLE = 64
    ADDR_GOAL_POSITION = 116
    ADDR_PRESENT_POSITION = 132
    LEN_POSITION = 4

    # Constants
    PROTOCOL_VERSION = 2.0
    TICKS_PER_REV = 4096
    CENTER_TICKS = 2048

    def __init__(
        self,
        port: str,
        baudrate: int,
        ids: List[int],
        signs: List[int],
        offsets_deg: List[float],
        max_retries: int = 3,
        cache_dt: float = 0.008,  # 8ms cache window
    ):
        self.port = port
        self.baudrate = baudrate
        self.ids = ids
        self.signs = signs
        self.offsets_deg = offsets_deg
        self.max_retries = max_retries
        self.cache_dt = cache_dt

        # Hardware handles
        self.port_handler: Optional[PortHandler] = None
        self.packet_handler: Optional[PacketHandler] = None
        self.sync_read: Optional[GroupSyncRead] = None
        self.sync_write: Optional[GroupSyncWrite] = None

        # Caching
        self._last_positions: Optional[np.ndarray] = None
        self._last_read_time = 0.0
        self._torque_enabled = False

        # Threading
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """Connect to Dynamixel servos with retry logic."""
        for attempt in range(self.max_retries):
            try:
                # Initialize handlers
                self.packet_handler = PacketHandler(self.PROTOCOL_VERSION)
                self.port_handler = PortHandler(self.port)

                # Open port
                if not self.port_handler.openPort():
                    raise RuntimeError(f"Failed to open port {self.port}")

                # Set baudrate
                if not self.port_handler.setBaudRate(self.baudrate):
                    raise RuntimeError(f"Failed to set baudrate {self.baudrate}")

                # Initialize sync read/write
                self.sync_read = GroupSyncRead(
                    self.port_handler,
                    self.packet_handler,
                    self.ADDR_PRESENT_POSITION,
                    self.LEN_POSITION,
                )

                self.sync_write = GroupSyncWrite(
                    self.port_handler,
                    self.packet_handler,
                    self.ADDR_GOAL_POSITION,
                    self.LEN_POSITION,
                )

                # Add all servos to sync read
                for servo_id in self.ids:
                    if not self.sync_read.addParam(servo_id):
                        print(f"[warn] Failed to add ID {servo_id} to sync read")

                print(f"[dxl] Connected to {self.port} @ {self.baudrate} baud")
                return True

            except Exception as e:
                print(
                    f"[dxl] Connection attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if self.port_handler and self.port_handler.is_open:
                    self.port_handler.closePort()
                time.sleep(0.5)

        return False

    def disconnect(self):
        """Disconnect from servos."""
        if self.port_handler and self.port_handler.is_open:
            self.port_handler.closePort()
            print(f"[dxl] Disconnected from {self.port}")

    def set_torque(self, enable: bool):
        """Enable/disable torque for all servos."""
        if not self.packet_handler or not self.port_handler:
            return

        with self._lock:
            value = 1 if enable else 0
            for servo_id in self.ids:
                result, error = self.packet_handler.write1ByteTxRx(
                    self.port_handler, servo_id, self.ADDR_TORQUE_ENABLE, value
                )
                if result != COMM_SUCCESS or error != 0:
                    print(
                        f"[dxl] Torque {'on' if enable else 'off'} failed for ID {servo_id}"
                    )

            self._torque_enabled = enable

    def read_positions(self) -> Optional[np.ndarray]:
        """Read current positions in radians with caching."""
        with self._lock:
            # Check cache
            now = time.monotonic()
            if (
                self._last_positions is not None
                and (now - self._last_read_time) < self.cache_dt
            ):
                return self._last_positions.copy()

            if not self.sync_read:
                return None

            # Perform sync read
            result = self.sync_read.txRxPacket()
            if result != COMM_SUCCESS:
                # Fallback to individual reads
                return self._read_positions_individual()

            # Extract data
            positions = np.zeros(len(self.ids))
            for i, servo_id in enumerate(self.ids):
                if self.sync_read.isAvailable(
                    servo_id, self.ADDR_PRESENT_POSITION, self.LEN_POSITION
                ):
                    ticks = self.sync_read.getData(
                        servo_id, self.ADDR_PRESENT_POSITION, self.LEN_POSITION
                    )
                    positions[i] = self._ticks_to_rad(
                        ticks, self.offsets_deg[i], self.signs[i]
                    )
                else:
                    return self._read_positions_individual()

            # Update cache
            self._last_positions = positions
            self._last_read_time = now
            return positions

    def _read_positions_individual(self) -> Optional[np.ndarray]:
        """Fallback to individual position reads."""
        if not self.packet_handler or not self.port_handler:
            return None

        positions = np.zeros(len(self.ids))
        for i, servo_id in enumerate(self.ids):
            data, result, error = self.packet_handler.read4ByteTxRx(
                self.port_handler, servo_id, self.ADDR_PRESENT_POSITION
            )
            if result != COMM_SUCCESS or error != 0:
                return None
            positions[i] = self._ticks_to_rad(data, self.offsets_deg[i], self.signs[i])

        # Update cache
        now = time.monotonic()
        self._last_positions = positions
        self._last_read_time = now
        return positions

    def write_positions(self, positions_rad: np.ndarray) -> bool:
        """Write goal positions using sync write."""
        if not self.sync_write or not self._torque_enabled:
            return False

        with self._lock:
            # Clear previous data
            self.sync_write.clearParam()

            # Add all servo data
            for i, (servo_id, pos_rad) in enumerate(zip(self.ids, positions_rad)):
                ticks = self._rad_to_ticks(pos_rad, self.offsets_deg[i], self.signs[i])
                data = [
                    ticks & 0xFF,
                    (ticks >> 8) & 0xFF,
                    (ticks >> 16) & 0xFF,
                    (ticks >> 24) & 0xFF,
                ]
                if not self.sync_write.addParam(servo_id, data):
                    print(f"[dxl] Failed to add param for ID {servo_id}")
                    return False

            # Send sync write
            result = self.sync_write.txPacket()
            return result == COMM_SUCCESS

    def _ticks_to_rad(self, ticks: int, offset_deg: float, sign: int) -> float:
        """Convert encoder ticks to radians."""
        offset_ticks = int(round((offset_deg / 360.0) * self.TICKS_PER_REV))
        return sign * (
            (ticks - self.CENTER_TICKS - offset_ticks)
            * (2 * math.pi / self.TICKS_PER_REV)
        )

    def _rad_to_ticks(self, rad: float, offset_deg: float, sign: int) -> int:
        """Convert radians to encoder ticks."""
        offset_ticks = int(round((offset_deg / 360.0) * self.TICKS_PER_REV))
        return int(
            self.CENTER_TICKS
            + offset_ticks
            + (rad * sign * self.TICKS_PER_REV / (2 * math.pi))
        )


class URRobot:
    """UR robot interface with optimized RTDE communication."""

    def __init__(
        self,
        host: str,
        control_frequency: float = 125.0,
    ):
        self.host = host
        self.control_frequency = control_frequency
        self.dt = 1.0 / control_frequency

        # RTDE interfaces
        self.receive_interface: Optional[RTDEReceiveInterface] = None
        self.control_interface: Optional[RTDEControlInterface] = None

        # State
        self._connected = False
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """Connect to UR robot."""
        try:
            # Receive interface (always needed)
            self.receive_interface = RTDEReceiveInterface(self.host)

            # Control interface (might fail if ExternalControl not running)
            try:
                self.control_interface = RTDEControlInterface(self.host)
                self._connected = True
                print(f"[ur] Connected to {self.host}")
                return True
            except Exception as e:
                print(
                    f"[ur] Control interface failed (ExternalControl not running?): {e}"
                )
                self._connected = False
                return False

        except Exception as e:
            print(f"[ur] Failed to connect to {self.host}: {e}")
            return False

    def disconnect(self):
        """Disconnect from UR robot."""
        with self._lock:
            if self.control_interface:
                try:
                    self.control_interface.stopJ(2.0)  # Stop with 2 rad/s² decel
                    self.control_interface.disconnect()
                except Exception:
                    pass
                self.control_interface = None

            if self.receive_interface:
                try:
                    self.receive_interface.disconnect()
                except Exception:
                    pass
                self.receive_interface = None

            self._connected = False
            print(f"[ur] Disconnected from {self.host}")

    def ensure_control(self) -> bool:
        """Ensure control interface is available."""
        if self.control_interface:
            # Test connection
            try:
                self.control_interface.getJointTemp()
                return True
            except Exception:
                self.control_interface = None

        # Try to reconnect
        try:
            self.control_interface = RTDEControlInterface(self.host)
            return True
        except Exception:
            return False

    def get_joint_positions(self) -> Optional[np.ndarray]:
        """Get current joint positions in radians."""
        if not self.receive_interface:
            return None

        try:
            return np.array(self.receive_interface.getActualQ())
        except Exception:
            return None

    def servo_j(
        self,
        q: Sequence[float],
        velocity: float,
        acceleration: float,
        dt: float,
        lookahead_time: float,
        gain: float,
    ) -> bool:
        """Send servoJ command."""
        if not self.control_interface:
            return False

        try:
            self.control_interface.servoJ(
                q, velocity, acceleration, dt, lookahead_time, gain
            )
            return True
        except Exception:
            return False

    def stop_j(self, acceleration: float = 2.0):
        """Stop robot motion."""
        if self.control_interface:
            try:
                self.control_interface.stopJ(acceleration)
            except Exception:
                pass


class URDynamixelRobot:
    """Combined UR + Dynamixel robot with unified interface."""

    def __init__(
        self,
        ur_host: str,
        dxl_port: str,
        dxl_ids: List[int],
        dxl_signs: List[int],
        dxl_offsets_deg: List[float],
        dxl_baudrate: int = 1000000,
        control_frequency: float = 125.0,
    ):
        # Create sub-components
        self.ur = URRobot(ur_host, control_frequency)
        self.dxl = DynamixelDriver(
            port=dxl_port,
            baudrate=dxl_baudrate,
            ids=dxl_ids,
            signs=dxl_signs,
            offsets_deg=dxl_offsets_deg,
        )

        # State
        self.num_ur_joints = 6
        self.num_dxl_joints = len(dxl_ids)
        self.num_joints = self.num_ur_joints + self.num_dxl_joints

    def connect(self) -> Tuple[bool, bool]:
        """Connect to both UR and Dynamixel. Returns (ur_ok, dxl_ok)."""
        ur_ok = self.ur.connect()
        dxl_ok = self.dxl.connect()
        return ur_ok, dxl_ok

    def disconnect(self):
        """Disconnect from both systems."""
        self.ur.disconnect()
        self.dxl.disconnect()

    def get_joint_positions(self) -> Optional[np.ndarray]:
        """Get combined joint positions [UR joints, DXL joints]."""
        ur_pos = self.ur.get_joint_positions()
        if ur_pos is None:
            return None

        dxl_pos = self.dxl.read_positions()
        if dxl_pos is None:
            return None

        return np.concatenate([ur_pos, dxl_pos])

    def get_observations(self) -> Dict[str, np.ndarray]:
        """Get robot observations."""
        positions = self.get_joint_positions()
        if positions is None:
            return {"joint_positions": np.zeros(self.num_joints)}

        return {
            "joint_positions": positions,
            "ur_positions": positions[: self.num_ur_joints],
            "dxl_positions": positions[self.num_ur_joints :],
        }

    def set_dxl_torque(self, enable: bool):
        """Set Dynamixel torque mode."""
        self.dxl.set_torque(enable)
