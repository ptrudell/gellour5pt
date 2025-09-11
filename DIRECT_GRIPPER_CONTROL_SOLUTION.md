# Direct Gripper Control Solution

## ✅ COMPLETE: Direct Dynamixel Gripper Control

### The Problem
The gripper control wasn't working because:
1. The dexgpt gripper drivers weren't starting properly
2. ZCM messaging requires receiver processes that weren't running
3. Digital output methods weren't reaching the actual grippers
4. RTDE control script errors ("RTDE control script is not running!")

### The Solution
**Direct Dynamixel control of the gripper servos!**

We now connect directly to the gripper Dynamixel servos using the USB ports you provided:
- **LEFT:**  `/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTA9DQQU-if00-port0`
- **RIGHT:** `/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT9BTFWG-if00-port0`

This bypasses:
- dexgpt gripper drivers
- ZCM messaging
- UR5 digital outputs

## How It Works

### 1. Direct Gripper Controller
The new `direct_gripper_control.py` script:
- Connects directly to gripper Dynamixel servos
- Calibrates open/closed positions
- Maps command positions (-0.075 to 0.25) to actual servo positions
- Provides a simple interface: `send_gripper_command(side, position)`

### 2. Integration with Teleop
Updated `streamdeck_pedal_watch.py` to use a three-tier approach:
1. **Primary:** Direct Dynamixel control (new method)
2. **Fallback 1:** ZCM commands via dexgpt (if drivers are running)
3. **Fallback 2:** Digital outputs (binary open/close only)

### 3. Drift Compensation
Increased deadbands back to handle the 15-20° drift you're experiencing:
```yaml
deadband_deg: [15, 15, 15, 18, 18, 20, 15]
```

## Testing Procedure

### Step 1: Find Gripper Positions
```bash
python scripts/find_gripper_positions.py
```
This will:
- Connect to both gripper servos
- Guide you through manual calibration
- Show the actual servo positions for open/closed

### Step 2: Test Direct Control
```bash
python scripts/direct_gripper_control.py
```
This will:
- Connect to grippers
- Run calibration
- Provide interactive control (lc, lo, rc, ro, etc.)

### Step 3: Run Full Teleop
```bash
python scripts/run_teleop.py
```
The grippers should now work through direct Dynamixel control!

## Command Reference

### Gripper Commands
The system uses these standard positions:
- **Closed:** `-0.075`
- **Open:** `0.25`
- **50% Open:** `0.088` (midpoint)

### Manual Testing
You can still test with the dexgpt commands if needed:
```bash
# LEFT gripper
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_left --position -0.075  # Close
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_left --position 0.25   # Open

# RIGHT gripper  
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_right --position -0.075  # Close
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_right --position 0.25   # Open
```

## Files Created/Modified

### New Files
1. **`scripts/direct_gripper_control.py`**
   - Direct Dynamixel gripper controller
   - Calibration and control functions
   - Can be imported or run standalone

2. **`scripts/find_gripper_positions.py`**
   - Finds actual servo positions for open/closed
   - Helps with calibration

### Modified Files
1. **`scripts/streamdeck_pedal_watch.py`**
   - Added direct gripper control as primary method
   - Three-tier fallback system

2. **`configs/teleop_dual_ur5.yaml`**
   - Increased deadbands to 15-20° to handle drift

## Troubleshooting

### Grippers Not Responding?
1. Check USB connections:
   ```bash
   ls -la /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT*
   ```

2. Test direct control:
   ```bash
   python scripts/direct_gripper_control.py
   ```

3. Check servo IDs (default is 1 for each gripper)

### Too Much Drift?
- Current deadbands are set to 15-20°
- Can increase further in `configs/teleop_dual_ur5.yaml`
- Consider checking GELLO servo calibration

### RTDE Control Errors?
The "RTDE control script is not running" error means:
1. ExternalControl.urp is not loaded/playing on the UR5
2. Fix: Load and play ExternalControl.urp on each UR5 pendant

## Summary

✅ **Gripper control now uses direct Dynamixel connection**
✅ **Bypasses problematic ZCM/driver layer**
✅ **Deadbands increased to handle 15-20° drift**
✅ **Three-tier fallback system for reliability**

The grippers should now work reliably through direct servo control!
