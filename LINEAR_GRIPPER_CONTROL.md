# Linear Gripper Control Implementation

## ✅ COMPLETE: Full Sliding Scale Gripper Control

### What's Implemented

The teleop system now uses **smooth linear mapping** for gripper control, allowing precise partial opening/closing based on exact GELLO gripper positions.

### Key Features

1. **Linear Interpolation**
   - Maps full GELLO range to full UR5 range
   - Smooth transitions between any position (0% to 100% open)
   - No more binary open/closed - supports 25%, 50%, 75%, etc.

2. **Auto-Calibration**
   - Uses calibrated values from testing:
     - LEFT: -0.629 (closed) to 0.262 (open) rad
     - RIGHT: 0.962 (closed) to 1.908 (open) rad
   - Dynamically refines min/max during operation
   - Values stored in `configs/teleop_dual_ur5.yaml`

3. **Smart Command Sending**
   - Minimum change threshold: 0.02 (2% change)
   - Rate limiting: 0.1s between commands
   - Prevents command spam while maintaining smooth control

## Configuration

### In `configs/teleop_dual_ur5.yaml`:
```yaml
gripper:
  # UR5 gripper command range
  ur_closed: -0.075   # UR5 closed command
  ur_open: 0.25       # UR5 open command
  
  # GELLO gripper calibration
  left_gello_min: -0.629   # LEFT GELLO closed
  left_gello_max: 0.262    # LEFT GELLO open
  right_gello_min: 0.962   # RIGHT GELLO closed
  right_gello_max: 1.908   # RIGHT GELLO open
  
  # Control parameters
  min_change: 0.02         # 2% minimum change
  min_interval_s: 0.1      # 100ms rate limit
```

## Testing Scripts

### 1. Test Linear Gripper Control Only
```bash
python scripts/test_linear_gripper.py
```
- Tests smooth linear mapping
- Shows percentage open in real-time
- No arm movement

### 2. Quick Gripper Test (Threshold-based)
```bash
python scripts/test_gripper_only.py
```
- Simple open/closed testing
- Finds calibration values

### 3. Full Teleop with Linear Grippers
```bash
python scripts/run_teleop.py
```
- Complete system with smooth gripper control
- Arms + grippers with linear mapping

## How It Works

### The Mapping Function
```python
def _map_gripper_position(gello_pos, gello_min, gello_max):
    # Normalize to 0-1 range
    normalized = (gello_pos - gello_min) / (gello_max - gello_min)
    normalized = clamp(normalized, 0, 1)
    
    # Map to UR5 command range
    ur_cmd = UR_CLOSED + normalized * (UR_OPEN - UR_CLOSED)
    return ur_cmd
```

### Example Positions
- GELLO fully closed → UR5: -0.075 (0% open)
- GELLO 25% open → UR5: -0.019 (25% open)
- GELLO 50% open → UR5: 0.088 (50% open)
- GELLO 75% open → UR5: 0.194 (75% open)
- GELLO fully open → UR5: 0.25 (100% open)

## Console Output

When grippers move, you'll see:
```
[LEFT GRIPPER] Update: 75% open (pos: 0.123 rad, cmd: 0.194)
[RIGHT GRIPPER] Update: 50% open (pos: 1.435 rad, cmd: 0.088)
```

## Advantages Over Threshold-Based

### Old (Threshold-based):
- Binary: Either fully open OR fully closed
- Sudden transitions at threshold
- No partial positions

### New (Linear Mapping):
- Continuous: Any position from 0% to 100%
- Smooth transitions
- Precise control for delicate operations
- Natural feel - GELLO position directly maps to UR5

## Troubleshooting

### Grippers Not Smooth?
- Check `min_change` in config (lower = smoother but more commands)
- Check `min_interval_s` (lower = faster updates)

### Wrong Range?
- Run `test_linear_gripper.py` to recalibrate
- Update values in `configs/teleop_dual_ur5.yaml`

### Too Sensitive/Not Sensitive?
- Adjust `left_gello_min/max` and `right_gello_min/max`
- Wider range = less sensitive
- Narrower range = more sensitive

## Files Modified

1. **`scripts/streamdeck_pedal_watch.py`**
   - Added `_map_gripper_position()` method
   - Updated gripper control logic for linear mapping
   - Added timing control and rate limiting

2. **`configs/teleop_dual_ur5.yaml`**
   - Added `gripper` section with calibration values
   - Configurable control parameters

3. **`scripts/test_linear_gripper.py`** (NEW)
   - Dedicated test script for linear control
   - Shows percentage open in real-time

## Summary

✅ **Linear gripper control is fully implemented and ready to use!**

The system now provides smooth, proportional gripper control that maps the exact GELLO gripper position to the UR5 gripper command, allowing for precise partial opening/closing during teleoperation.
