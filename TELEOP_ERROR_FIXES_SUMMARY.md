# Teleoperation Error Fixes Summary

## Date: 2024

## Issues Fixed

### 1. ✅ DXL Servo Connection Issues
**Problem:** DXL servos weren't responding after pressing LEFT pedal (interrupt)
**Root Cause:** Robot connections were disconnected but not properly rebuilt
**Solution:** 
- Added retry logic for DXL connections in `_build_robot()` function
- Robot references are now cleared and rebuilt when needed
- Better error handling with detailed diagnostic messages

### 2. ✅ Center Pedal Baseline Capture Errors
**Problem:** CENTER pedal first tap showed "Failed to read positions" errors
**Solution:**
- Modified `on_center_first()` to rebuild robot connections if they were disconnected
- Added proper error checking in `capture_baselines()` with detailed error messages
- Returns success status to track if baselines were captured

### 3. ✅ Gripper Integration
**Problem:** Gripper control wasn't integrated with teleop
**Solution:**
- Added gripper position mapping from DXL servo (ID 7 for left, ID 16 for right)
- Normalized gripper position from DXL range to 0-1 for UR control
- Added gripper_enabled flag in config
- Prepared infrastructure for UR gripper control (Robotiq/other)

### 4. ✅ Motion Drift Reduction
**Problem:** UR5 robots exhibited drift when GELLO arms stopped moving
**Solution in `hardware/control_loop.py`:**
- Faster inactivity detection: 50ms (was 300ms)
- Lower motion threshold: 0.001 rad
- Slower rebaselining: beta=0.02 (was 0.1)
- 70% damping when stopped

**Solution in `configs/teleop_dual_ur5.yaml`:**
- Reduced EMA alpha: 0.08 (was 0.12) for less lag
- Faster softstart: 0.15s (was 0.20s)
- Tighter deadbands: 0.5° for most joints (was 1°)

## Testing

### DXL Servo Test Script
Created `scripts/test_dxl_connection.py` for quick diagnostics:
```bash
python scripts/test_dxl_connection.py
```

### Current Status
- ✅ All 14 servos detected (7 per arm including grippers)
- ✅ LEFT: IDs [1,2,3,4,5,6,7]
- ✅ RIGHT: IDs [10,11,12,13,14,15,16]

## Usage

### Normal Operation
```bash
# Standard operation with pedals
python scripts/run_teleop.py

# Test mode without pedals
python scripts/run_teleop.py --test-mode
```

### Pedal Functions
- **LEFT (Button 4)**: Interrupt - stops URs for external control
- **CENTER (Button 5)**: 
  - Tap 1: Rebuild connections, capture baselines, gentle mode
  - Tap 2: Start full-speed teleop
- **RIGHT (Button 6)**: Stop teleop, return to idle

## Key Code Changes

### `scripts/streamdeck_pedal_watch.py`
1. `_build_robot()`: Added retry logic and better error handling
2. `on_left_interrupt()`: Clears robot references for rebuild
3. `on_center_first()`: Rebuilds disconnected robots
4. `capture_baselines()`: Better error reporting
5. Gripper position mapping in `_run()` loop

### `hardware/control_loop.py`
1. Faster motion detection (50ms threshold)
2. Lower motion threshold (0.001 rad)
3. Strong damping when stopped (70%)
4. Improved velocity damping

### `configs/teleop_dual_ur5.yaml`
1. Tighter deadbands for drift reduction
2. Faster response parameters
3. Gripper control enabled

## Troubleshooting

If DXL servos stop responding:
1. Run diagnostic: `python scripts/test_dxl_connection.py`
2. Check power supply (12V for servos)
3. Check U2D2 USB connections
4. Verify servo IDs match configuration

If drift persists:
1. Adjust deadband_deg in config (lower = less drift but more sensitive)
2. Tune ema_alpha (lower = less smoothing lag)
3. Check mechanical backlash in GELLO arms

## Next Steps
- Implement actual UR gripper control (Robotiq/other)
- Add gripper force feedback if available
- Fine-tune motion parameters based on user feedback
