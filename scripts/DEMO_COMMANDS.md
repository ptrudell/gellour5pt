# Teleop Demo Commands

## Quick Reference for Running Different Versions

### 🚀 Option 1: Run the Demo Script (Easiest)
```bash
# Run streamdeck_pedal_watch_work.py with safe settings
./scripts/run_demo_work.sh
```

### 💻 Option 2: Direct Command - Work Version (Optimized)
```bash
# Run streamdeck_pedal_watch_work.py directly
cd /home/shared/gellour5pt

UR_VMAX=0.05 UR_AMAX=0.8 \
python scripts/streamdeck_pedal_watch_work.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 \
  --joints-passive \
  --no-dashboard \
  --test-mode
```

### 🎮 Option 3: With Pedals Only (No Test Mode)
```bash
# For actual operation with pedals
cd /home/shared/gellour5pt

UR_VMAX=0.05 UR_AMAX=0.8 \
python scripts/streamdeck_pedal_watch_work.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 \
  --joints-passive \
  --no-dashboard
```

### 🏃 Option 4: Normal Speed Version
```bash
# Faster speeds for experienced operators (VMAX=1.4, AMAX=4.0)
cd /home/shared/gellour5pt

python scripts/streamdeck_pedal_watch_work.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 \
  --joints-passive \
  --no-dashboard
```

### 🔧 Option 5: With Dashboard Control
```bash
# Allow dashboard commands (auto-play, auto-load programs)
cd /home/shared/gellour5pt

UR_VMAX=0.05 UR_AMAX=0.8 \
python scripts/streamdeck_pedal_watch_work.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 \
  --joints-passive \
  --test-mode
# Note: No --no-dashboard flag means dashboard control is ENABLED
```

### 🎯 Option 6: Single Arm Testing
```bash
# Test with just LEFT arm
cd /home/shared/gellour5pt

UR_VMAX=0.05 UR_AMAX=0.8 \
python scripts/streamdeck_pedal_watch_work.py \
  --ur-left 192.168.1.211 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --left-ids 1,2,3,4,5,6,7 \
  --baud 1000000 \
  --joints-passive \
  --no-dashboard \
  --test-mode
```

### 📊 Option 7: DXL Servo Diagnostic
```bash
# Test DXL servos only (no UR control)
cd /home/shared/gellour5pt

python scripts/streamdeck_pedal_watch_work.py \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 \
  --dxl-test
```

### 🐛 Option 8: Debug Mode (Pedal Packets)
```bash
# Debug pedal HID packets
cd /home/shared/gellour5pt

UR_VMAX=0.05 UR_AMAX=0.8 \
python scripts/streamdeck_pedal_watch_work.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 \
  --joints-passive \
  --no-dashboard \
  --pedal-debug
```

## Speed Settings

### Environment Variables
- `UR_VMAX`: Maximum velocity (rad/s)
  - `0.05` = Very slow (safe for testing)
  - `0.5` = Gentle
  - `1.4` = Normal (default)
  - `2.0` = Fast

- `UR_AMAX`: Maximum acceleration (rad/s²)
  - `0.8` = Very gentle
  - `1.0` = Gentle
  - `4.0` = Normal (default)
  - `8.0` = Fast

### Examples
```bash
# Very slow and safe
UR_VMAX=0.05 UR_AMAX=0.8 python scripts/streamdeck_pedal_watch_work.py ...

# Medium speed
UR_VMAX=0.7 UR_AMAX=2.0 python scripts/streamdeck_pedal_watch_work.py ...

# Fast (experienced operators only)
UR_VMAX=2.0 UR_AMAX=8.0 python scripts/streamdeck_pedal_watch_work.py ...
```

## Command Line Options

### Essential Options
- `--ur-left IP`: Left UR robot IP address
- `--ur-right IP`: Right UR robot IP address
- `--left-port PATH`: Left DXL servo serial port
- `--right-port PATH`: Right DXL servo serial port

### Control Options
- `--joints-passive`: Keep DXL servos torque OFF (free movement)
- `--torque-on`: Force DXL servos torque ON (overrides --joints-passive)
- `--no-dashboard`: Disable UR dashboard commands
- `--test-mode`: Auto-start teleop after 3 seconds (no pedals needed)

### Testing Options
- `--dxl-test`: Test DXL servos and exit
- `--pedal-debug`: Show raw pedal HID packets

### Advanced Options
- `--left-ids`: Comma-separated DXL IDs for left (default: 1,2,3,4,5,6,7)
- `--right-ids`: Comma-separated DXL IDs for right (default: 10,11,12,13,14,15,16)
- `--baud`: DXL baud rate (default: 1000000)
- `--left-signs`: Joint direction signs (comma-separated ±1)
- `--right-signs`: Joint direction signs (comma-separated ±1)
- `--left-offsets-deg`: Joint offset angles in degrees
- `--right-offsets-deg`: Joint offset angles in degrees

## Pedal Controls

When pedals are connected:
- **LEFT PEDAL (Button 4)**: Interrupt - stops URs for external control
- **CENTER PEDAL (Button 5)**:
  - 1st tap: Capture baselines, set gentle mode
  - 2nd tap: Start full-speed teleop
- **RIGHT PEDAL (Button 6)**: Stop teleop, return to passive

## Quick Troubleshooting

### If RTDE won't connect:
1. Check ExternalControl.urp is loaded and playing on pendant
2. Verify Host IP = your PC's IP (not robot's IP)
3. Enable Remote Control on pendant
4. Clear any protective stops

### If DXL servos don't respond:
1. Check 5V power supply
2. Try different baud rate: `--baud 57600`
3. Test single servo: `LEFT_IDS=1 python ...`
4. Check USB connections

### If pedals don't work:
1. Check USB: `lsusb | grep 0fd9`
2. Set permissions: `sudo usermod -a -G plugdev $USER`
3. Add udev rule for StreamDeck pedal
4. Use `--test-mode` to bypass pedals
