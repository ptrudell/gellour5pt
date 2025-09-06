# GELLO Gripper Integration Guide

## Overview
The teleop system now integrates with your existing dexgpt gripper control script.

## How It Works

### 1. Gripper Detection
- **LEFT Gripper:** Dynamixel ID 7
- **RIGHT Gripper:** Dynamixel ID 16
- The system monitors these servos continuously during teleop

### 2. Command Execution
When a GELLO gripper is pressed/released, the system executes:

**For LEFT gripper:**
```bash
# When squeezed/closed:
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_left --position -0.1

# When released/open:
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_left --position 0.25
```

**For RIGHT gripper:**
```bash
# When squeezed/closed:
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_right --position -0.1

# When released/open:
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_right --position 0.25
```

### 3. Threshold Detection
- Default threshold: 0.0 radians
- Values < 0.0 = CLOSED (sends -0.1)
- Values ≥ 0.0 = OPEN (sends 0.25)

## Testing Tools

### 1. Test Gripper Range
```bash
python scripts/test_gripper_range.py
```
This helps you find the actual range of your GELLO grippers:
- Shows MIN value when squeezed
- Shows MAX value when released
- Suggests optimal threshold

### 2. Test Gripper Commands
```bash
python scripts/test_gripper_command.py
```
This tests the dexgpt integration directly:
- Sends commands to each gripper
- Shows command output
- Verifies the integration works

### 3. Run Full Teleop
```bash
python scripts/run_teleop.py
```
During teleop, you'll see console output when grippers change state:
```
[LEFT GRIPPER] Changed to: CLOSED (pos: -0.234 rad, cmd: -0.1)
[LEFT GRIPPER] Changed to: OPEN (pos: 0.156 rad, cmd: 0.25)
```

## Tuning the Threshold

If your grippers don't trigger correctly, adjust the threshold in `streamdeck_pedal_watch.py`:

```python
# Around line 885 (left) and 964 (right)
gripper_threshold = 0.0  # Adjust this value based on test_gripper_range.py results
```

### Example Adjustments:
- If gripper range is -2.0 to +2.0 rad → threshold = 0.0 (middle)
- If gripper range is -1.0 to +3.0 rad → threshold = 1.0 (middle)
- If gripper range is -3.0 to -0.5 rad → threshold = -1.75 (middle)

## Features

### Hysteresis
Prevents command spam when gripper position fluctuates:
- Only sends new command if change > 0.05 from last sent command
- Prevents rapid open/close cycles

### Non-blocking
- Commands have 500ms timeout
- Gripper errors don't stop teleop
- Commands run in background

### Debug Output
The system prints gripper state changes:
- Initial state when teleop starts
- Each state change during operation
- Position in radians and command value

## Troubleshooting

### Grippers Not Responding
1. Run `scripts/test_gripper_command.py` to test direct commands
2. Check if dexgpt script exists: `ls ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py`
3. Check dexgpt script permissions
4. Look for error messages in teleop console output

### Wrong Open/Closed Detection
1. Run `scripts/test_gripper_range.py` to find actual ranges
2. Adjust `gripper_threshold` based on results
3. Consider inverting logic if needed (swap CLOSED/OPEN values)

### Commands Sent But Robot Doesn't Move
1. Check if dexgpt script is working manually:
   ```bash
   cd ~/generalistai/dexgpt
   python debug_tools/send_gripper_cmd.py -o gripper_command_left --position -0.1
   ```
2. Verify robot connection
3. Check robot gripper configuration

## File Modifications

### Modified Files:
- `scripts/streamdeck_pedal_watch.py` - Added dexgpt integration
- `hardware/control_loop.py` - Enhanced drift reduction
- `configs/teleop_dual_ur5.yaml` - Optimized parameters

### New Test Files:
- `scripts/test_gripper_range.py` - Calibration tool
- `scripts/test_gripper_command.py` - Integration test

## Next Steps

1. **Run Range Test:** Find your gripper ranges
   ```bash
   python scripts/test_gripper_range.py
   ```

2. **Adjust Threshold:** Update if needed based on test results

3. **Test Commands:** Verify integration works
   ```bash
   python scripts/test_gripper_command.py
   ```

4. **Run Teleop:** Test full system
   ```bash
   python scripts/run_teleop.py
   ```

The system is now configured to call your existing dexgpt gripper commands when GELLO grippers are pressed!
