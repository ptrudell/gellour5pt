# Complete Fix for UR5 and DXL Connection Issues

## Problems Identified

From your output:
1. **DXL Communication Failure**: `rc=-3001` (timeout) on all servo IDs
2. **UR Program Issue**: Both robots stuck at `STOPPED freedrive.urp` instead of `PLAYING ExternalControl.urp`
3. **Pedals Working**: But can't start teleop due to above issues

## Fixes Implemented

### 1. Enhanced UR Program Loading (`_ensure_external_control`)

**Improvements:**
- More aggressive stop/restart sequence
- Powers down and back up if freedrive is stuck
- Tries multiple path formats for loading ExternalControl.urp
- Accepts any External Control variant that's PLAYING
- Increased wait times for program startup

**Key changes:**
```python
# If freedrive is loaded, force stop and restart
_dash_exec(host, "stop", "powerdown")
time.sleep(0.5)
_dash_exec(host, "power on", "brake release")

# Try multiple path formats
1. /programs/ExternalControl.urp
2. programs/ExternalControl.urp  
3. ExternalControl  (just the name)
```

### 2. Auto-Start Flag (Bypass Pedals)

**New feature:** `--auto-start` flag for testing without pedals
```bash
--auto-start  # Automatically starts teleop, bypassing pedal control
```

This immediately:
1. Captures baselines (like CENTER tap 1)
2. Starts streaming (like CENTER tap 2)

### 3. DXL Read Retry Logic

**Improvements:**
- Retries DXL reads up to 3 times during baseline capture
- Better error messages with specific hints
- Handles rc=-3001 timeout errors more gracefully

### 4. DXL Connection Test Script

**New tool:** `/home/shared/gellour5pt/test_scripts/test_dxl_connection.py`

Test individual servos:
```bash
python test_dxl_connection.py /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 --id 1
```

Scan for all servos:
```bash
python test_dxl_connection.py /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 --scan
```

## How to Use

### Test with Auto-Start (Bypasses Pedals)
```bash
UR_VMAX=0.05 UR_AMAX=0.8 \
python scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive --auto-start
```

### Fix DXL Issues (rc=-3001)

The rc=-3001 error means timeout - servos aren't responding. Common causes:

1. **Wrong Baud Rate**: XL330s might be at 57600 instead of 1000000
   ```bash
   # Test with different baud
   --baud 57600
   ```

2. **Power Issue**: XL330 needs 5V power
   - Check U2D2/USB adapter has power
   - Verify servo LED indicators

3. **Wrong IDs**: Scan to find actual IDs
   ```bash
   python test_dxl_connection.py /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 --scan
   ```

4. **USB Permission**: 
   ```bash
   sudo chmod 666 /dev/serial/by-id/usb-FTDI_USB*
   ```

### Fix UR Program Not Playing

If ExternalControl.urp won't transition to PLAYING:

1. **Manual Load on Pendant**:
   - Menu → Run Program
   - Select ExternalControl.urp (NOT freedrive.urp)
   - Press Play ▶
   - Enable Remote Control

2. **Check Program Path**: The script now tries:
   - `/programs/ExternalControl.urp`
   - `programs/ExternalControl.urp`
   - `ExternalControl`
   
   One should work if the program exists.

3. **Verify External Control Node**:
   - Open program tree
   - External Control node at top
   - **Host IP = YOUR PC's IP** (e.g., 192.168.1.100)
   - NOT the robot's IP!

## Quick Debug Checklist

### For DXL Issues:
```bash
# 1. Test LEFT arm servos
python gello/test_scripts/test_dxl_connection.py \
  /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --scan

# 2. Test RIGHT arm servos  
python gello/test_scripts/test_dxl_connection.py \
  /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --scan
```

### For UR Issues:
```bash
# Force load ExternalControl.urp
python gello/test_scripts/test_force_external_control.py 192.168.1.211
python gello/test_scripts/test_force_external_control.py 192.168.1.210
```

### Combined Test:
```bash
# Test with slow speeds and auto-start
UR_VMAX=0.05 UR_AMAX=0.8 \
python scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive --auto-start
```

## Expected Output When Working

```
[dxl] LEFT: open ... @ 1000000
[dxl] RIGHT: open ... @ 1000000
[dash] 192.168.1.211: programState → PLAYING ExternalControl.urp
[dash] 192.168.1.210: programState → PLAYING ExternalControl.urp
✓ LEFT arm: 7 joints captured
✓ RIGHT arm: 7 joints captured
✅ LEFT UR: READY FOR CONTROL
✅ RIGHT UR: READY FOR CONTROL
```

## If Still Not Working

1. **DXL timeout (rc=-3001)**:
   - Servos might need power cycle
   - Try baud 57600 instead of 1000000
   - Check physical connections

2. **UR won't play ExternalControl**:
   - Manually load and play on pendant first
   - Verify Remote Control enabled
   - Check Host IP in External Control node

3. **Use auto-start to bypass pedals**:
   - Add `--auto-start` flag
   - Starts teleop immediately for testing

The enhanced script should now handle both the freedrive → ExternalControl transition and DXL communication issues more robustly!

