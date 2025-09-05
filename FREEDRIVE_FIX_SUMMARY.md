# Fix for FREEDRIVE.URP Problem

## Problem
Both UR robots had **FREEDRIVE.URP** loaded instead of **ExternalControl.urp**, which prevented RTDE control from working. The logs showed:
```
programState → STOPPED FREEDRIVE.URP
```

RTDE control only works when ExternalControl.urp (with the External Control URCap node) is PLAYING.

## Solution Implemented

### 1. Enhanced Dashboard Execution (`_dash_exec`)
New function that can execute multiple dashboard commands in sequence:
- Clears safety popups
- Powers on the robot
- Loads the correct program
- Starts playing

### 2. Improved `_ensure_external_control()`
Completely rewritten to:
- **Stop** any currently running program
- **Clear** all blockers (safety popup, protective stop, power, brake)
- **Check** what's currently loaded
- **Load** ExternalControl.urp if not already loaded
- **Play** the program and verify it reaches PLAYING state
- **Retry** up to 3 times with diagnostics

### 3. Better Pre-flight Checks
The CENTER pedal (second tap) now:
- Shows current loaded program and state
- Forces ExternalControl.urp to load (replacing FREEDRIVE)
- Verifies program reaches "PLAYING ExternalControl.urp"
- Only then creates RTDE control interface
- Tests with no-op servoJ before starting

## How to Use

### Standard Command
```bash
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive --pedal-debug
```

The default program path is `/programs/ExternalControl.urp`. If your program is elsewhere:

### Custom Program Paths
```bash
--ur-left-program "/programs/MyFolder/ExternalControl.urp" \
--ur-right-program "/programs/MyFolder/ExternalControl.urp"
```

## Testing Tools

### Force Load Test
Test forcing ExternalControl.urp to load on a specific robot:
```bash
python gello/test_scripts/test_force_external_control.py 192.168.1.210
```

### Full Connection Test
```bash
python gello/test_scripts/test_ur_program_load.py 192.168.1.210
```

### Manual Dashboard Commands
```bash
# Check current state
ROBOT=192.168.1.210
{ echo -e "get loaded program\nprogramState\n"; sleep 0.2; } | nc $ROBOT 29999

# Force load & play
{ echo -e "stop\nclose safety popup\nunlock protective stop\nload /programs/ExternalControl.urp\nplay\nprogramState\n"; sleep 0.5; } | nc $ROBOT 29999
```

## What You'll See

### When It Works
```
[dash] 192.168.1.210: Current state: STOPPED FREEDRIVE.URP
[dash] 192.168.1.210: Loading /programs/ExternalControl.urp...
[dash] 192.168.1.210: programState → PLAYING ExternalControl.urp
✅ RIGHT UR: READY FOR CONTROL
```

### When It Fails
```
[dash] 192.168.1.210: programState → STOPPED FREEDRIVE.URP
✗ Program not PLAYING after retries
  → On the pendant: Load & Play ExternalControl.urp
  → Enable Remote Control (green indicator on status bar)
  → Check External Control node Host IP = this PC's IP (not robot's IP)
  → Verify External Control URCap is installed
```

## Critical Pendant Settings

### External Control Node Configuration
1. Open ExternalControl.urp in program tree
2. Select **External Control** node (usually at top)
3. **Host IP**: Must be YOUR COMPUTER'S IP
   - Example: If your PC is 192.168.1.100, use that
   - NOT the robot's IP (192.168.1.210)
4. **Port**: Default 30001 or 30002 is fine

### Enable Remote Control
- Settings → System → Remote Control → Enable
- Look for green "Remote Control" indicator on status bar

### If Program Won't Load
- The path `/programs/ExternalControl.urp` must exist
- Try loading manually on pendant first
- Save the program after configuring External Control node

## How It Fixes the Problem

1. **Detects FREEDRIVE**: Checks current loaded program
2. **Forces Correct Program**: Loads ExternalControl.urp via dashboard
3. **Verifies PLAYING**: Won't proceed until program is actually running
4. **Tests Control**: Does no-op servoJ to verify RTDE works
5. **Clear Diagnostics**: Tells you exactly what's wrong if it fails

The system now automatically handles the transition from FREEDRIVE.URP to ExternalControl.urp, making teleop much more reliable!

