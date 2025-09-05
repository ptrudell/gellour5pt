#!/usr/bin/env python3
"""
Optimized control loop for teleoperation based on GELLO patterns.
Provides fixed-rate control with profiling and smooth motion.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class MotionProfile:
    """Motion profiling parameters."""

    velocity_max: float = 1.4  # rad/s
    acceleration_max: float = 4.0  # rad/s²
    jerk_max: float = 100.0  # rad/s³ (optional)

    # Smoothing
    ema_alpha: float = 0.12
    softstart_time: float = 0.2

    # Deadbands and limits
    deadband_rad: List[float] = None
    scale_factors: List[float] = None
    clamp_rad: List[float] = None

    # Command limits
    vel_limit_cmd: float = 6.0  # rad/s
    acc_limit_cmd: float = 40.0  # rad/s²

    def __post_init__(self):
        if self.deadband_rad is None:
            self.deadband_rad = [0.017] * 7  # ~1 degree default
        if self.scale_factors is None:
            self.scale_factors = [1.0] * 7
        if self.clamp_rad is None:
            self.clamp_rad = [None] * 7


class SmoothMotionController:
    """Smooth motion controller with profiling and deadband handling."""

    def __init__(
        self,
        num_joints: int,
        profile: MotionProfile,
        control_dt: float = 0.008,
    ):
        self.num_joints = num_joints
        self.profile = profile
        self.dt = control_dt

        # State tracking
        self._positions: Optional[np.ndarray] = None
        self._velocities: Optional[np.ndarray] = None
        self._start_time: Optional[float] = None

        # Baseline tracking for relative control
        self._baseline_dxl: Optional[np.ndarray] = None
        self._baseline_ur: Optional[np.ndarray] = None

        # Inactivity detection
        self._last_positions: Optional[np.ndarray] = None
        self._last_move_time = time.monotonic()
        self._inactivity_threshold = 0.3  # seconds
        self._rebase_beta = 0.1

    def reset(self):
        """Reset controller state."""
        self._positions = None
        self._velocities = None
        self._start_time = None
        self._baseline_dxl = None
        self._baseline_ur = None

    def set_baselines(self, dxl_positions: np.ndarray, ur_positions: np.ndarray):
        """Set baseline positions for relative control."""
        self._baseline_dxl = dxl_positions.copy()
        self._baseline_ur = ur_positions.copy()
        self._start_time = time.monotonic()

        # Initialize profiled positions to UR baseline
        self._positions = ur_positions.copy()
        self._velocities = np.zeros_like(ur_positions)

    def update(
        self,
        dxl_positions: np.ndarray,
        ur_positions: np.ndarray,
    ) -> Tuple[np.ndarray, bool]:
        """
        Update controller and compute target positions.

        Returns:
            (target_positions, is_moving): Target joint positions and motion flag
        """
        if self._baseline_dxl is None or self._baseline_ur is None:
            # Auto-initialize baselines on first call
            self.set_baselines(dxl_positions, ur_positions)

        # Detect motion
        is_moving = self._detect_motion(dxl_positions)

        # Handle inactivity rebaselining
        if not is_moving:
            self._handle_inactivity(dxl_positions)

        # Compute relative delta from baseline
        delta = dxl_positions - self._baseline_dxl

        # Apply deadband and scaling
        delta = self._apply_deadband_scale(delta)

        # Compute target = UR baseline + scaled delta
        target = self._baseline_ur + delta

        # Apply optional clamping around baseline
        target = self._apply_clamps(target)

        # Apply soft-start ramping
        target = self._apply_softstart(target)

        # Apply motion profiling for smooth acceleration
        target, self._velocities = self._apply_profile(target, self._velocities)

        return target, is_moving

    def _detect_motion(self, positions: np.ndarray) -> bool:
        """Detect if there's significant motion."""
        if self._last_positions is None:
            self._last_positions = positions.copy()
            return False

        # Check maximum joint change
        max_change = np.abs(positions - self._last_positions).max()
        self._last_positions = positions.copy()

        if max_change > 0.0025:  # ~0.14 degrees
            self._last_move_time = time.monotonic()
            return True

        return False

    def _handle_inactivity(self, positions: np.ndarray):
        """Gradually rebaseline during inactivity to prevent drift."""
        now = time.monotonic()
        if (now - self._last_move_time) > self._inactivity_threshold:
            # Slowly pull baseline toward current position
            self._baseline_dxl = (
                1.0 - self._rebase_beta
            ) * self._baseline_dxl + self._rebase_beta * positions

    def _apply_deadband_scale(self, delta: np.ndarray) -> np.ndarray:
        """Apply per-joint deadband and scaling."""
        result = np.zeros_like(delta)

        for i in range(len(delta)):
            if i < len(self.profile.deadband_rad):
                db = self.profile.deadband_rad[i]
                scale = (
                    self.profile.scale_factors[i]
                    if i < len(self.profile.scale_factors)
                    else 1.0
                )

                if abs(delta[i]) > db:
                    result[i] = delta[i] * scale
                else:
                    result[i] = 0.0
            else:
                result[i] = delta[i]

        return result

    def _apply_clamps(self, target: np.ndarray) -> np.ndarray:
        """Apply optional clamping around baseline."""
        if not any(c is not None for c in self.profile.clamp_rad):
            return target

        result = target.copy()
        for i in range(len(target)):
            if (
                i < len(self.profile.clamp_rad)
                and self.profile.clamp_rad[i] is not None
            ):
                clamp = self.profile.clamp_rad[i]
                center = self._baseline_ur[i]
                result[i] = np.clip(target[i], center - clamp, center + clamp)

        return result

    def _apply_softstart(self, target: np.ndarray) -> np.ndarray:
        """Apply soft-start ramping."""
        if self._start_time is None:
            return target

        elapsed = time.monotonic() - self._start_time
        ramp = min(1.0, elapsed / max(1e-6, self.profile.softstart_time))

        # Ramp from baseline to target
        return self._baseline_ur + ramp * (target - self._baseline_ur)

    def _apply_profile(
        self,
        target: np.ndarray,
        prev_vel: Optional[np.ndarray],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Apply second-order motion profiling for smooth motion."""
        if self._positions is None:
            self._positions = target.copy()
            return target, np.zeros_like(target)

        if prev_vel is None:
            prev_vel = np.zeros_like(target)

        new_pos = np.zeros_like(target)
        new_vel = np.zeros_like(target)

        for i in range(len(target)):
            # Current state
            pos = self._positions[i]
            vel = prev_vel[i]

            # Desired velocity to reach target
            vel_desired = (target[i] - pos) / self.dt

            # Apply acceleration limit
            acc_max = self.profile.acc_limit_cmd
            dv_max = acc_max * self.dt
            dv = np.clip(vel_desired - vel, -dv_max, dv_max)
            vel = vel + dv

            # Apply velocity limit
            vel_max = self.profile.vel_limit_cmd
            vel = np.clip(vel, -vel_max, vel_max)

            # Update position
            pos = pos + vel * self.dt

            new_pos[i] = pos
            new_vel[i] = vel

        self._positions = new_pos
        return new_pos, new_vel


class FixedRateScheduler:
    """Fixed-rate scheduler using perf_counter for precise timing."""

    def __init__(self, frequency: float):
        self.frequency = frequency
        self.dt = 1.0 / frequency
        self._next_time = None
        self._overrun_count = 0
        self._timing_stats = []
        self._stats_window = 1000  # samples

    def start(self):
        """Start the scheduler."""
        self._next_time = time.perf_counter()

    def wait(self) -> float:
        """
        Wait until next tick.

        Returns:
            float: Actual time since last tick (for diagnostics)
        """
        if self._next_time is None:
            self.start()
            return self.dt

        # Calculate next tick time
        self._next_time += self.dt

        # Current time
        now = time.perf_counter()

        # Time to wait
        delay = self._next_time - now

        if delay > 0:
            # We're on time, sleep until next tick
            time.sleep(delay)
            actual_dt = self.dt
        else:
            # We're late (overrun)
            overrun_ms = -delay * 1000

            if overrun_ms > 100:
                # Major overrun - realign
                self._next_time = now + self.dt
                self._overrun_count += 1

                # Print warning occasionally
                if self._overrun_count % 10 == 0:
                    print(
                        f"[scheduler] Major overrun {overrun_ms:.1f}ms (count: {self._overrun_count})"
                    )
            else:
                # Minor overrun - try to catch up
                self._next_time = now + (self.dt * 0.5)

            actual_dt = self.dt - delay

        # Track timing statistics
        self._timing_stats.append(actual_dt)
        if len(self._timing_stats) > self._stats_window:
            self._timing_stats.pop(0)

        return actual_dt

    def get_stats(self) -> dict:
        """Get timing statistics."""
        if not self._timing_stats:
            return {
                "mean_dt": self.dt,
                "std_dt": 0.0,
                "min_dt": self.dt,
                "max_dt": self.dt,
                "overruns": self._overrun_count,
            }

        stats = np.array(self._timing_stats)
        return {
            "mean_dt": float(np.mean(stats)),
            "std_dt": float(np.std(stats)),
            "min_dt": float(np.min(stats)),
            "max_dt": float(np.max(stats)),
            "overruns": self._overrun_count,
            "mean_freq": 1.0 / float(np.mean(stats)),
        }
