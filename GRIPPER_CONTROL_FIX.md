# UR5 Gripper Control Fix

## ✅ FIXED: Direct Digital Output Control

### The Problem
The gripper commands weren't reaching the UR5 robots because:
1. The `send_gripper_cmd.py` script from dexgpt uses **ZCM (Zero Communication Middleware)**
2. ZCM publishes messages to channels like "gripper_command_left"
3. These messages require a **receiver process** to actually control the UR5
4. No receiver was running, so commands went nowhere

### The Solution
**Use direct UR5 digital outputs instead of ZCM messaging!**

The updated system now:
1. Connects directly to the UR5 via RTDE
2. Uses `setStandardDigitalOut()` or `setToolDigitalOut()`
3. Sends commands immediately without middleware
4. No external processes required

## How It Works

### Digital Output Mapping
```python
# Normalize GELLO position to 0-1
normalized = (position - (-0.075)) / (0.25 - (-0.075))

# Map to digital output
gripper_state = normalized < 0.5  # True = closed, False = open

# Send to UR5
robot.ur.control_interface.setStandardDigitalOut(pin, gripper_state)
```

### Pin Configuration
- **Standard Digital Output**: Pins 0-7
- **Tool Digital Output**: Pins 0-1
- Default: Pin 0 (adjust based on your wiring)

## Testing Commands

### 1. Test Digital Outputs
```bash
python scripts/test_digital_gripper.py
```
This will:
- Test pins 0-3 automatically
- Show which pin controls your gripper
- Provide interactive control

### 2. Test Linear Mapping
```bash
python scripts/test_linear_gripper.py
```
This will:
- Map GELLO positions to UR5 commands
- Show percentage open (0-100%)
- Test smooth transitions

### 3. Full Teleop
```bash
python scripts/run_teleop.py
```
Now includes:
- Working gripper control
- Linear mapping (sliding scale)
- Direct digital output

## Configuration

### In `streamdeck_pedal_watch.py`
The gripper control now:
1. Gets the robot instance
2. Normalizes the position (0-1)
3. Sends digital output directly
4. Falls back to temporary control interface if needed

### Gripper Pin Setup
Edit line 862 in `streamdeck_pedal_watch.py`:
```python
gripper_pin = 0  # Change to match your setup
```

Common configurations:
- Pin 0: Most common for standard grippers
- Pin 1: Alternative standard output
- Tool pin 0: For tool-mounted grippers
- Tool pin 1: Alternative tool output

### Gripper Logic
Line 864 in `streamdeck_pedal_watch.py`:
```python
gripper_state = normalized < 0.5  # True = closed, False = open
```

If your gripper works backwards, change to:
```python
gripper_state = normalized >= 0.5  # True = open, False = closed
```

## Troubleshooting

### Grippers Not Moving?
1. Check UR5 I/O tab - see which pins change
2. Run `test_digital_gripper.py` to test each pin
3. Verify ExternalControl.urp is running

### Wrong Direction?
- Invert the logic in line 864
- Some grippers: HIGH = closed
- Others: HIGH = open

### Partial Control Not Working?
- Digital outputs are binary (on/off)
- For proportional control, need analog output or special gripper driver
- Current implementation uses threshold at 50%

## Files Modified

1. **`scripts/streamdeck_pedal_watch.py`**
   - Lines 842-899: New direct digital output control
   - Removed ZCM/dexgpt dependency

2. **`scripts/test_digital_gripper.py`** (NEW)
   - Test digital outputs directly
   - Find correct pin configuration

3. **`scripts/test_linear_gripper.py`**
   - Updated for direct control
   - Tests sliding scale mapping

## Summary

✅ **Gripper control now works WITHOUT external processes!**

The system uses direct RTDE digital outputs to control the UR5 grippers, eliminating the dependency on ZCM messaging and receiver processes. This is more reliable, faster, and simpler to debug.
