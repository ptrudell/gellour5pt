# Teleop Troubleshooting Guide

Based on your error output, you have two issues to fix:

## Issue 1: DXL Servos Not Responding (rc=-3001)

The timeout error means servos aren't responding at all. This is a hardware/configuration issue.

### Quick Tests

#### 1. Test DXL Connection
```bash
# Test with diagnostic mode
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --dxl-test
```

#### 2. Try Different Baud Rate
XL330s often default to 57600:
```bash
# Test with 57600 baud
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 57600 --dxl-test
```

#### 3. Test Single Servo
```bash
# Test just ID 1 on LEFT
LEFT_IDS=1 PYTHONPATH=. python gello/scripts/run_teleop.py \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --baud 1000000 --dxl-test
```

#### 4. Scan for Servos
```bash
# Scan LEFT arm
python gello/test_scripts/test_dxl_connection.py \
  /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --scan --baud 1000000

# Try with 57600 if above fails
python gello/test_scripts/test_dxl_connection.py \
  /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --scan --baud 57600
```

### Common Fixes

1. **Power**: Ensure servos have 5V power (check LED on servos)
2. **Baud Rate**: Try 57600 instead of 1000000
3. **IDs**: Verify servo IDs (use Dynamixel Wizard if needed)
4. **USB**: Check connections, try different USB ports
5. **Permissions**: `sudo chmod 666 /dev/serial/by-id/usb-FTDI*`

## Issue 2: UR Stuck on freedrive.urp

The robots won't load ExternalControl.urp via dashboard commands.

### Quick Fix - Force Load Script
```bash
# Run the force load script
bash gello/scripts/force_load_external_control.sh
```

### Manual Fix (Most Reliable)

**On Each UR Pendant:**

1. **Stop Current Program**
   - Press red Stop button
   - Clear any popups

2. **Load ExternalControl**
   - Menu (≡) → Run Program
   - File browser → Select `ExternalControl.urp`
   - If not there, check `/programs/` folder

3. **Configure External Control Node**
   - Open program tree (if not visible)
   - Click External Control node at top
   - Set **Host IP** = Your PC's IP (e.g., 192.168.1.100)
   - **NOT** the robot's IP!

4. **Start Program**
   - Press green Play button (▶)
   - Should show "Program Running"

5. **Enable Remote Control**
   - Settings → System → Remote Control
   - Toggle ON (green indicator on status bar)

### Test UR Connection
```bash
# Test if ExternalControl loads
python gello/test_scripts/test_force_external_control.py 192.168.1.211
python gello/test_scripts/test_force_external_control.py 192.168.1.210
```

## Complete Test Sequence

Once both issues are fixed:

### 1. Test with Slow Speed + Auto-Start
```bash
UR_VMAX=0.05 UR_AMAX=0.8 \
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive --auto-start
```

### 2. If DXL Still Fails, Try 57600 Baud
```bash
UR_VMAX=0.05 UR_AMAX=0.8 \
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 57600 --joints-passive --auto-start
```

### 3. Success Indicators

**DXL Working:**
```
✓ LEFT arm: 7 joints captured
✓ RIGHT arm: 7 joints captured
```

**UR Working:**
```
[dash] 192.168.1.211: programState → PLAYING ExternalControl.urp
[dash] 192.168.1.210: programState → PLAYING ExternalControl.urp
✅ LEFT UR: READY FOR CONTROL
✅ RIGHT UR: READY FOR CONTROL
```

## If Everything Else Fails

### Nuclear Option - Full Reset

1. **Power cycle both UR robots**
2. **Unplug/replug USB adapters**
3. **On pendants:**
   - Clear all errors
   - Load ExternalControl.urp manually
   - Press Play
   - Enable Remote Control
4. **Test with single servo:**
   ```bash
   LEFT_IDS=1 RIGHT_IDS=10 PYTHONPATH=. python gello/scripts/run_teleop.py \
     --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
     --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
     --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
     --baud 57600 --joints-passive --auto-start
   ```

## Debug Commands Reference

```bash
# Test DXL only
--dxl-test

# Override servo IDs
LEFT_IDS=1,2,3 RIGHT_IDS=10,11,12

# Try different baud rates
--baud 57600
--baud 1000000

# Auto-start (bypass pedals)
--auto-start

# Slow speeds for safety
UR_VMAX=0.05 UR_AMAX=0.8
```

The most likely fixes:
1. **DXL**: Wrong baud rate (try 57600) or no power
2. **UR**: Need to manually load ExternalControl.urp on pendant

