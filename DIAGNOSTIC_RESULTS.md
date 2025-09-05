# System Diagnostic Results

## ✅ DXL Servo Status

### LEFT ARM
- Port: `/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0`
- **Baud Rate: 1000000** (NOT 57600!)
- Servos Found: IDs 1-7 ✓

### RIGHT ARM  
- Port: `/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0`
- **Baud Rate: 1000000** (NOT 57600!)
- Servos Found: IDs 10-16 ✓

## ⚠️ UR Robot Status

### LEFT UR (192.168.1.211)
- Dashboard: Connected ✓
- Current Program: **freedrive.urp** ❌
- State: STOPPED
- Mode: POWER_OFF ❌

### RIGHT UR (192.168.1.210)
- Dashboard: Connected ✓
- Current Program: **freedrive.urp** ❌
- State: STOPPED  
- Mode: POWER_OFF ❌

## 📋 IMMEDIATE ACTIONS REQUIRED

### 1. Fix UR Robots (Manual on Pendant)
On BOTH robot pendants:
1. **Power On** the robot (if POWER_OFF)
2. **File → Load Program → ExternalControl.urp**
3. Press **Play** button (▶)
4. Enable **Remote Control** mode
5. Check External Control node: **Host IP = Your PC's IP**

### 2. Use Correct Launch Command
```bash
# CORRECT - with baud 1000000
UR_VMAX=0.05 UR_AMAX=0.8 \
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive --auto-start
```

## 🔍 Key Findings

1. **DXL servos work at 1000000 baud, NOT 57600**
   - This is why you were getting rc=-3001 timeout errors
   - All servos respond correctly at 1M baud

2. **Both URs have freedrive.urp loaded**
   - This prevents RTDE control
   - Must manually load ExternalControl.urp on pendants

3. **Both URs are powered OFF**
   - Need to power on before loading programs

## ✅ Quick Test After Fixes

Run the diagnostic again:
```bash
python gello/scripts/quick_diagnostic.py
```

Expected output:
- UR Robots: 2/2 ready (with ExternalControl PLAYING)
- DXL Arms: 2/2 ready (at 1M baud)

## 🚀 Final Working Configuration

Once URs are fixed, this will work:
```bash
# Safe speed for testing
UR_VMAX=0.05 UR_AMAX=0.8 \
PYTHONPATH=. python gello/scripts/run_teleop.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 --joints-passive --pedal-debug
```

Then:
1. Press CENTER pedal once → captures baselines
2. Press CENTER pedal again → starts teleop
3. Move GELLO arms → UR robots mirror the motion!

