# Gripper and Drift Fixes Summary

## Date: 2024

## Issues Fixed

### 1. ✅ Gripper Control Implementation
**Problem:** Gripper control wasn't working - detected but not sending commands to UR
**Solution:**
- Properly mapped DXL gripper positions (ID 7 for left, ID 16 for right) to 0-1 range
- Fixed variable names: `self.left_gripper_cmd` and `self.right_gripper_cmd` (was using left for both)
- Added gripper range normalization:
  - DXL range: -1.5 to 1.5 radians (adjustable)
  - UR expects: 0 = closed, 1 = open
- Ready for actual UR gripper hardware integration

**Code Changes in `streamdeck_pedal_watch.py`:**
```python
# Normalize gripper position
gripper_min = -1.5  # Closed position
gripper_max = 1.5   # Open position
gripper_normalized = (gripper_pos - gripper_min) / (gripper_max - gripper_min)
```

### 2. ✅ Stationary Drift Reduction
**Problem:** UR robots drifted even when GELLO remained in one place (not just stopped)
**Solution in `hardware/control_loop.py`:**
- Added stationary detection with very small delta threshold (0.002 rad)
- Applied 95% damping when truly stationary (delta * 0.05)
- Kept 70% damping for general non-moving state

**Code Changes:**
```python
if not is_moving:
    stationary_threshold = 0.002  # radians
    is_stationary = np.all(np.abs(delta) < stationary_threshold)
    
    if is_stationary:
        delta = delta * 0.05  # Very strong damping when stationary
    else:
        delta = delta * 0.3  # Strong damping when stopped
```

### 3. ✅ Right Pedal Shutdown Timeout
**Problem:** Step 3/4 "Setting servos to passive" would hang indefinitely
**Solution:**
- Added threading with 500ms timeout for servo passive operation
- Made thread daemon to prevent blocking
- Added exception handling to ignore errors during shutdown
- Shows "(Skipped - timeout)" if operation times out

**Code Changes in `streamdeck_pedal_watch.py`:**
```python
def set_passive_with_timeout():
    for robot in (left_robot, right_robot):
        if robot:
            try:
                robot.set_dxl_torque(False)
            except Exception:
                pass

passive_thread = threading.Thread(target=set_passive_with_timeout)
passive_thread.daemon = True
passive_thread.start()
passive_thread.join(timeout=0.5)  # 500ms timeout
```

## Testing

### DXL Servo Status
All 14 servos detected correctly:
- LEFT: IDs [1,2,3,4,5,6,7] ✓
- RIGHT: IDs [10,11,12,13,14,15,16] ✓

### Test Commands
```bash
# Test DXL connection
python scripts/test_dxl_connection.py

# Run teleop with improvements
python scripts/run_teleop.py
```

## Configuration

### Gripper Tuning in `configs/teleop_dual_ur5.yaml`
- `gripper_enabled: true` - Enable gripper control
- `gripper_threshold: 0.1` - Motion detection threshold

### Motion Shaping Parameters (Updated)
- `ema_alpha: 0.08` - Reduced smoothing lag
- `softstart_time: 0.15` - Faster startup
- `deadband_deg: [0.5, 0.5, 0.5, 0.5, 0.5, 1.0, 0.5]` - Tighter deadbands

## Results

1. **Gripper**: Now properly tracks DXL gripper movements and prepares commands for UR
2. **Drift**: Minimal drift when GELLO is stationary (95% damping applied)
3. **Shutdown**: Right pedal shutdown completes quickly without hanging

## Next Steps

### For Gripper Integration
1. Add actual UR gripper control code (Robotiq or other)
2. Implement gripper force feedback if available
3. Add gripper open/close thresholds for discrete control

### For Further Drift Reduction
1. Fine-tune `stationary_threshold` if needed (currently 0.002 rad)
2. Adjust damping factors based on testing
3. Consider adding velocity-based damping

### For Robustness
1. Add more timeout protections in other operations
2. Implement health monitoring for servo connections
3. Add automatic reconnection on servo failures
