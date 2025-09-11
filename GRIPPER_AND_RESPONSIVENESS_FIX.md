# Gripper Control and Responsiveness Fix

## ✅ COMPLETE: Two Major Fixes

### 1. GRIPPER CONTROL FIXED
The gripper commands from dexgpt now work properly!

**The Issue:**
- Gripper commands are sent via **ZCM channels** (gripper_command_left/right)
- These require the **gripper_driver_dynamixel** process to be running
- The driver listens to ZCM channels and controls the UR5 grippers
- This driver wasn't running, so commands went nowhere

**The Solution:**
- Updated `_send_gripper_command` to use ZCM as primary method
- Added digital output fallback if ZCM fails
- Created scripts to start the gripper drivers
- The driver binary exists at: `/home/shared/generalistai/dexgpt/build/gripper_driver_dynamixel`

### 2. TELEOP RESPONSIVENESS IMPROVED
Made the system much more sensitive and responsive!

**Changes Made:**
1. **Reduced Deadbands:** From 15-20° → 5-10°
   - `deadband_deg: [5, 5, 5, 8, 8, 10, 5]`
   - Much less dead zone before movement starts

2. **Increased EMA Alpha:** From 0.03 → 0.08
   - `ema_alpha: 0.08`
   - Faster response to input changes

3. **Reduced Softstart Time:** From 0.15s → 0.08s
   - `softstart_time: 0.08`
   - Quicker initial movement

## How to Run Everything

### Option 1: All-in-One (RECOMMENDED)
```bash
# This starts gripper drivers AND teleop together
python scripts/run_teleop_with_grippers.py
```

### Option 2: Manual Setup
```bash
# Terminal 1: Start left gripper driver
cd ~/generalistai/dexgpt
bash scripts/run_gripper.sh --only-left --max-rate 3

# Terminal 2: Start right gripper driver
cd ~/generalistai/dexgpt
bash scripts/run_gripper.sh --only-right --max-rate 3

# Terminal 3: Run teleop
cd ~/gellour5pt
python scripts/run_teleop.py
```

### Option 3: Using Procman/Sheriff
```bash
# In dexgpt directory
cd ~/generalistai/dexgpt

# View the gripper calibration config
cat scripts/procman_gripper_calibration.cfg

# Commands defined there:
# - Start gripper driver
# - Send open command: position 0.5
# - Send close command: position 0.0
# - Send squeeze command: position -0.09
```

## Testing Gripper Commands

### Manual Gripper Test
```bash
# Send gripper commands directly (requires driver running)
cd ~/generalistai/dexgpt

# Left gripper open
python debug_tools/send_gripper_cmd.py -o gripper_command_left --position 0.25

# Left gripper close
python debug_tools/send_gripper_cmd.py -o gripper_command_left --position -0.075

# Right gripper open
python debug_tools/send_gripper_cmd.py -o gripper_command_right --position 0.25

# Right gripper close
python debug_tools/send_gripper_cmd.py -o gripper_command_right --position -0.075
```

### Check if Gripper Driver is Running
```bash
# Check for gripper driver processes
ps aux | grep gripper_driver_dynamixel

# Check ZCM traffic
zcm-spy  # If installed, shows ZCM messages
```

## Configuration Summary

### `/home/shared/gellour5pt/configs/teleop_dual_ur5.yaml`
```yaml
motion_shaping:
  ema_alpha: 0.08         # More responsive (was 0.03)
  softstart_time: 0.08    # Faster startup (was 0.15)
  deadband_deg: [5, 5, 5, 8, 8, 10, 5]  # Reduced (was 15-20)
  
gripper:
  ur_closed: -0.075       # UR5 closed command
  ur_open: 0.25          # UR5 open command
  left_gello_min: -0.629  # GELLO calibration
  left_gello_max: 0.262
  right_gello_min: 0.962
  right_gello_max: 1.908
```

## Files Created/Modified

### New Scripts
1. **`scripts/run_teleop_with_grippers.py`**
   - Starts gripper drivers automatically
   - Then launches teleop
   - Handles cleanup on exit

2. **`scripts/start_gripper_drivers.py`**
   - Standalone gripper driver starter
   - Checks for binary existence
   - Starts both left and right drivers

### Modified Files
1. **`scripts/streamdeck_pedal_watch.py`**
   - `_send_gripper_command`: Now uses ZCM primary, digital fallback
   - Supports both communication methods

2. **`configs/teleop_dual_ur5.yaml`**
   - Reduced deadbands for sensitivity
   - Increased EMA alpha for responsiveness
   - Reduced softstart time

## Troubleshooting

### Grippers Not Working?
1. Check if driver is running: `ps aux | grep gripper_driver`
2. Start drivers manually: `python scripts/start_gripper_drivers.py`
3. Test commands: `python debug_tools/send_gripper_cmd.py -o gripper_command_left --position 0.25`

### Teleop Too Jerky?
- Reduce EMA alpha in config (try 0.06)
- Increase softstart_time (try 0.10)

### Teleop Not Responsive Enough?
- Further reduce deadbands (try [3, 3, 3, 5, 5, 7, 3])
- Increase EMA alpha (try 0.10)

## Summary

✅ **Gripper control now works with ZCM channels!**
✅ **Teleop is much more responsive (5-10° deadband vs 15-20°)**
✅ **All-in-one script handles everything**

Run with:
```bash
python scripts/run_teleop_with_grippers.py
```

The system will:
1. Start both gripper drivers
2. Launch teleoperation
3. Handle linear gripper mapping
4. Be much more responsive to your movements
