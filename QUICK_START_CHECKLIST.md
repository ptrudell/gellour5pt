# Teleop Quick Start Checklist

Based on the comprehensive troubleshooting experience, here's what to check:

## Pre-Launch Checklist

### 1. Hardware
- [ ] DXL servos powered (5V, check LEDs)
- [ ] USB adapters connected and recognized: `ls -la /dev/serial/by-id/`
- [ ] UR robots powered on
- [ ] StreamDeck pedal connected

### 2. UR Pendant Setup (Each Robot)
- [ ] Load ExternalControl.urp (NOT freedrive.urp)
- [ ] External Control node: Host IP = YOUR PC's IP (e.g., 192.168.1.100)
- [ ] Press Play button (▶)
- [ ] Enable Remote Control (green indicator)
- [ ] Clear any Protective Stops

### 3. Software Dependencies
```bash
pip install hidapi dynamixel_sdk
```

### 4. Permissions (Linux)
```bash
# For pedals
sudo bash -c 'echo "SUBSYSTEM==\"hidraw\", ATTRS{idVendor}==\"0fd9\", ATTRS{idProduct}==\"0086\", MODE=\"0666\"" > /etc/udev/rules.d/99-streamdeck-pedal.rules'
sudo udevadm control --reload-rules && sudo udevadm trigger

# For USB serial
sudo chmod 666 /dev/serial/by-id/usb-FTDI*
```

## Launch Commands

### Safe Test Mode (Recommended First Run)
```bash
UR_VMAX=0.05 UR_AMAX=0.8 \
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive --pedal-debug
```

### With Auto-Start (Bypass Pedals)
```bash
AUTO_START=1 UR_VMAX=0.05 UR_AMAX=0.8 \
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive
```

### DXL Test Only
```bash
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --dxl-test
```

## Expected Output Sequence

### 1. Startup
```
TELEOP STARTUP DIAGNOSTICS
Speed Limits: VMAX=0.05 rad/s, AMAX=0.8 rad/s²
  → SAFE MODE: Very slow for testing
[dxl] LEFT: open ... @ 1000000
[dxl] RIGHT: open ... @ 1000000
[dash] 192.168.1.211: play sequence sent
[dash] 192.168.1.210: play sequence sent
```

### 2. Pedal Ready
```
STREAMDECK PEDAL CONTROL READY
```

### 3. After CENTER First Tap
```
🟡 [CENTER PEDAL - FIRST TAP] Preparing teleop...
✓ LEFT arm: 7/7 joints captured
✓ RIGHT arm: 7/7 joints captured
```

### 4. After CENTER Second Tap
```
🟢 [CENTER PEDAL - SECOND TAP] Starting teleop!
[dash] 192.168.1.211: programState → PLAYING ExternalControl.urp
[dash] 192.168.1.210: programState → PLAYING ExternalControl.urp
✅ LEFT UR: READY FOR CONTROL
✅ RIGHT UR: READY FOR CONTROL
```

## Common Failure Points

### No Pedal Response
- Missing `hidapi`: `pip install hidapi`
- No udev rule: See permissions above
- Use `AUTO_START=1` to bypass

### DXL rc=-3001
- Wrong baud: Try `--baud 57600`
- No power: Check 5V supply
- Wrong IDs: `LEFT_IDS=1 RIGHT_IDS=10` to test single servo

### UR "STOPPED freedrive.urp"
- Manually load ExternalControl.urp on pendant
- Check Host IP = YOUR PC (not robot IP!)
- Enable Remote Control

### "Control script not running"
- ExternalControl not PLAYING
- Wrong Host IP in External Control node
- Remote Control disabled

## Quick Fixes

```bash
# Force load ExternalControl on URs
bash gello/scripts/force_load_external_control.sh

# Test DXL with different baud
--baud 57600

# Test single servo
LEFT_IDS=1 RIGHT_IDS=10

# Bypass pedals
AUTO_START=1 or --auto-start

# Slow speed for safety
UR_VMAX=0.05 UR_AMAX=0.8
```

## Success Criteria

When everything works, you should see:
1. Both arms capture all joints
2. Both URs show READY FOR CONTROL
3. Moving GELLO arm causes UR to mirror motion
4. No error messages in continuous loop

If any step fails, use the specific troubleshooting for that component.

