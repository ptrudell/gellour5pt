# Gripper and Drift Improvements Summary

## Changes Made (December 9, 2024)

### 1. Updated Gripper Commands
- **Changed closed position:** From `-0.1` to `-0.075` for both left and right grippers
- **Kept open position:** `0.25` for both left and right grippers
- These values match the exact commands specified for the dexgpt gripper control script

### 2. Drift Reduction
- **Increased deadband values significantly** to eliminate 15-20 degree drift:
  - Previous: `[0.8, 0.8, 0.8, 0.8, 0.8, 1.2, 0.8]` degrees
  - New: `[15, 15, 15, 18, 18, 20, 15]` degrees
  - Joint 4, 5, 6 have slightly higher deadbands (18, 18, 20) as they tend to drift more
- **Applied to both:**
  - `scripts/streamdeck_pedal_watch.py` (main teleop script)
  - `configs/teleop_dual_ur5.yaml` (configuration file)

### 3. New Diagnostic Scripts

#### `scripts/find_gripper_positions.py`
- Finds the actual open/closed positions of GELLO grippers
- Monitors gripper positions in real-time
- Tests gripper commands
- Usage: `python scripts/find_gripper_positions.py`

#### `scripts/test_gripper_commands.py`
- Tests gripper commands directly
- Can test left, right, or both grippers
- Supports custom positions and cycling
- Usage examples:
  ```bash
  # Test both grippers with default sequence
  python scripts/test_gripper_commands.py
  
  # Test left gripper only
  python scripts/test_gripper_commands.py --side left
  
  # Test custom position
  python scripts/test_gripper_commands.py --position 0.1
  
  # Cycle between open and closed
  python scripts/test_gripper_commands.py --cycle
  ```

## Testing Procedure

1. **Find GELLO gripper ranges:**
   ```bash
   python scripts/find_gripper_positions.py
   ```
   - Squeeze and release grippers to see min/max values
   - Note the threshold values for each side

2. **Test gripper commands:**
   ```bash
   python scripts/test_gripper_commands.py
   ```
   - Verify grippers respond to commands
   - Check that open position = 0.25 and closed = -0.075

3. **Run teleop with improved drift control:**
   ```bash
   python scripts/run_teleop.py
   ```
   - The increased deadbands should eliminate the 15-20 degree drift
   - Grippers should respond correctly to GELLO gripper movements

## Fine-Tuning

If drift is still present:
- Increase deadband values further in `configs/teleop_dual_ur5.yaml`
- Current values: `[15, 15, 15, 18, 18, 20, 15]`
- Try: `[20, 20, 20, 25, 25, 30, 20]` if needed

If grippers are not responsive enough:
- Adjust the threshold values in `scripts/streamdeck_pedal_watch.py`:
  - Left gripper threshold: Line 887 (currently 2.97)
  - Right gripper threshold: Line 972 (currently 4.60)
- Run `find_gripper_positions.py` to find optimal thresholds

## Gripper Command Integration

The system now uses the exact dexgpt commands:
```bash
# Close left gripper
python debug_tools/send_gripper_cmd.py -o gripper_command_left --position -0.075

# Open left gripper  
python debug_tools/send_gripper_cmd.py -o gripper_command_left --position 0.25

# Close right gripper
python debug_tools/send_gripper_cmd.py -o gripper_command_right --position -0.075

# Open right gripper
python debug_tools/send_gripper_cmd.py -o gripper_command_right --position 0.25
```

These commands are automatically sent when GELLO gripper positions cross the threshold values.
