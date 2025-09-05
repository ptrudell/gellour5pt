# UR Connection Fix Summary

## Problem
The RIGHT UR was failing with "RTDE control script is not running!" even though the LEFT UR was working fine. This was happening because:
1. The ExternalControl program wasn't loaded/running on the RIGHT UR
2. Dashboard "play" command alone wasn't enough to start the RTDE control script
3. No robust recovery mechanism when connection was lost

## Solution Implemented

### 1. Enhanced Dashboard Control
Added comprehensive dashboard helpers to:
- Query program state (`programState`)
- Check robot and safety modes
- Explicitly load .urp programs
- Clear safety popups and protective stops
- Verify program is actually PLAYING before attempting control

### 2. Robust Program Loading
New `_ensure_external_control()` function that:
- Loads the specified .urp program via dashboard
- Tries alternative path formats if loading fails
- Clears all popups and safety issues
- Verifies program reaches PLAYING state
- Retries up to 3 times with proper diagnostics

### 3. Better Pre-flight Checks
The CENTER pedal (second tap) now:
- Shows robot mode and safety status
- Ensures ExternalControl.urp is loaded and PLAYING
- Recreates RTDE control interface after program is running
- Tests with a no-op servoJ command before starting teleop
- Provides clear guidance when things fail

### 4. Auto-recovery During Teleop
If RTDE control is lost during streaming:
- Attempts to reload and restart the program once
- Continues teleop if recovery succeeds
- Stops safely after 2 failures to prevent unsafe operation

## How to Use

### Basic Command (with auto-loading)
```bash
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive --pedal-debug
```

The default program path is `/programs/ExternalControl.urp`. If your program is elsewhere, specify it:

### Custom Program Paths
```bash
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --ur-left-program "/programs/MyCell/ExternalControl.urp" \
  --ur-right-program "/programs/MyCell/ExternalControl.urp" \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive
```

### Testing Individual Robots
Use the debug scripts to test each UR independently:

```bash
# Test LEFT UR
python gello/test_scripts/test_ur_program_load.py 192.168.1.211

# Test RIGHT UR
python gello/test_scripts/test_ur_program_load.py 192.168.1.210

# Or use the comprehensive debug tool
python gello/test_scripts/ur_connection_debug.py 192.168.1.210 --auto-load
```

## What You'll See

### Successful Connection
```
[dash] 192.168.1.210: programState → PLAYING
✓ Can read position
Robot mode: ROBOTMODE_RUNNING
Safety mode: SAFETYSTATUS_NORMAL
✓ RTDE control established
✅ RIGHT UR: READY FOR CONTROL
```

### Failed Connection (with guidance)
```
[dash] 192.168.1.210: programState → STOPPED
✗ Program not PLAYING after retries
  → On the pendant: Load & Play ExternalControl.urp
  → Enable Remote Control (green indicator on status bar)
  → Clear any Protective Stop (blue/orange banner)
```

## Troubleshooting Checklist

### If RIGHT UR Still Won't Connect:

1. **On the UR Pendant**:
   - Menu (≡) → Run Program → Load `ExternalControl.urp`
   - Press green Play button (▶)
   - Ensure "Program Running" shows in status

2. **Check External Control Node Settings**:
   - Open program tree, select External Control node
   - **Host IP**: Must be YOUR computer's IP on robot subnet (e.g., 192.168.1.xxx)
   - **Port**: Default 30001 or 30002 is fine

3. **Enable Remote Control**:
   - Settings → System → Remote Control → Enable
   - Look for green indicator on status bar

4. **Clear Safety Issues**:
   - If you see blue/orange "Protective Stop" banner
   - Press "Unlock protective stop" button
   - May need to move joints slightly to clear

5. **Network Connectivity**:
   ```bash
   # Test basic connectivity
   ping 192.168.1.210
   
   # Test dashboard port
   nc -zv 192.168.1.210 29999
   
   # Test RTDE ports
   nc -zv 192.168.1.210 30004
   ```

## Key Improvements

- **Reduced Latency**: DXL cache reduced from 16ms to 8ms
- **Better Diagnostics**: Clear status reporting at each step
- **Auto-recovery**: Handles transient failures gracefully
- **Program Loading**: Explicitly loads and verifies programs
- **Safety Handling**: Clears popups and protective stops
- **Loop Monitoring**: Detects and reports timing overruns

## Expected Workflow

1. **LEFT pedal**: Interrupt (stops URs for external control)
2. **CENTER 1st tap**: Captures baselines, sets gentle mode
3. **CENTER 2nd tap**: 
   - Checks robot/safety modes
   - Loads ExternalControl.urp if needed
   - Waits for PLAYING state
   - Tests RTDE control
   - Starts 125Hz streaming
4. **RIGHT pedal**: Stops teleop cleanly

The system now handles most connection issues automatically and provides clear guidance when manual intervention is needed.

