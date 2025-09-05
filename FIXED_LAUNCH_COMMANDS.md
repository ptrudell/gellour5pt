# Fixed Launch Commands for Teleop

## ✅ CORRECT Launch Command (with --no-dashboard flag)

```bash
# With correct baud rate 1000000 and no dashboard control
UR_VMAX=0.05 UR_AMAX=0.8 \
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive --no-dashboard --auto-start
```

## Key Changes Made

### 1. **--no-dashboard flag added**
- Prevents script from sending ANY dashboard commands
- No stop/power/play/load commands will be sent
- You control the UR robots manually via pendant

### 2. **Correct baud rate: 1000000**
- Your servos work at 1M baud, NOT 57600
- This fixes the rc=-3001 timeout errors

### 3. **Simplified _check_external_control**
- Now ONLY checks status, doesn't modify anything
- Just reports if ExternalControl is playing or not
- No power cycling, no program loading

### 4. **Manual UR Control**
With --no-dashboard, you must manually:
1. Power on each robot via pendant
2. Load ExternalControl.urp
3. Press Play (▶)
4. Enable Remote Control
5. Ensure Host IP = YOUR PC's IP

## Testing the Changes

### 1. Quick DXL Test (should work now)
```bash
python gello/scripts/quick_diagnostic.py
```

### 2. DXL-only Test
```bash
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --dxl-test
```

### 3. Full Teleop (after manually setting up URs)
```bash
UR_VMAX=0.05 UR_AMAX=0.8 \
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive --no-dashboard --pedal-debug
```

## Expected Behavior

1. **DXL servos**: Should respond immediately (all 14 servos)
2. **UR robots**: Will only work if you manually have ExternalControl.urp PLAYING
3. **No dashboard messages**: You'll see "Skipping dashboard commands (--no-dashboard)"
4. **Manual control required**: Script won't touch UR power/programs

## Problems Fixed

1. ✅ **rc=-3001 errors** → Fixed with --baud 1000000
2. ✅ **Unwanted UR control** → Fixed with --no-dashboard
3. ✅ **Power cycling** → Removed completely
4. ✅ **Program loading attempts** → Removed completely

## Summary

The script now:
- ONLY reads from DXL servos (no power control needed)
- ONLY connects to UR via RTDE (no dashboard control)
- Requires YOU to manually set up URs via pendant
- Works immediately with correct baud rate

