# UR5-GELLO Offset Tools

## Overview
This document describes the tools for retrieving UR5 angles and calculating/displaying offsets between UR5 and GELLO positions.

## Available Scripts

### 1. `get_ur_angles.py` - Get UR5 Joint Angles
Retrieves current UR5 joint positions and displays them in both radians and degrees.

**Basic Usage:**
```bash
# Get angles from default UR (192.168.1.210)
python scripts/get_ur_angles.py

# Specify IP address
python scripts/get_ur_angles.py --ip 192.168.1.211

# Get both arms
python scripts/get_ur_angles.py --both

# Continuous monitoring at 10Hz
python scripts/get_ur_angles.py --continuous

# Output as JSON for scripting
python scripts/get_ur_angles.py --json
```

**Example Output:**
```
UR5 (192.168.1.210) Joint Positions:
--------------------------------------------------
Joint    Radians      Degrees     
--------------------------------------------------
J1       -0.7854       -45.00°
J2       -1.5708       -90.00°
J3        0.0000         0.00°
J4       -1.5708       -90.00°
J5        1.5708        90.00°
J6        0.0000         0.00°
--------------------------------------------------

As arrays:
Radians: [-0.7854, -1.5708, 0.0000, -1.5708, 1.5708, 0.0000]
Degrees: [-45.00, -90.00, 0.00, -90.00, 90.00, 0.00]
```

### 2. `show_ur_gello_offset.py` - Real-time Offset Monitor
Continuously displays the offset between UR5 and GELLO positions in real-time.

**Usage:**
```bash
# Monitor both arms
python scripts/show_ur_gello_offset.py

# Monitor left arm only
python scripts/show_ur_gello_offset.py --left

# Monitor right arm only
python scripts/show_ur_gello_offset.py --right

# Custom IP and ports
python scripts/show_ur_gello_offset.py \
    --left-ur-ip 192.168.1.211 \
    --left-gello-port /dev/ttyUSB0
```

**Features:**
- Real-time 10Hz updates
- Color-coded offsets:
  - 🟢 Green: < 2° (good alignment)
  - 🟡 Yellow: 2-5° (medium offset)
  - 🔴 Red: > 5° (large offset)
- RMS error calculation
- Dual arm simultaneous monitoring

### 3. `calc_ur_gello_offsets.py` - Calculate Calibration Offsets
Calculates precise offsets between UR5 and GELLO for calibration purposes.

**Usage:**
```bash
# Calculate offsets for both arms
python scripts/calc_ur_gello_offsets.py

# Calculate for left arm only
python scripts/calc_ur_gello_offsets.py --left

# Save offsets to file
python scripts/calc_ur_gello_offsets.py --save configs/offsets.json

# With custom connections
python scripts/calc_ur_gello_offsets.py \
    --left-ur-ip 192.168.1.211 \
    --left-gello-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT7WBEIA-if00-port0
```

**Features:**
- Averages 10 samples for accuracy
- Calculates offsets in both radians and degrees
- Saves calibration data to JSON
- Shows RMS error for quality assessment

**Example Output:**
```
LEFT ARM OFFSET CALCULATION
============================================================

Joint    UR5 (deg)    GELLO (deg)  Offset (deg)
--------------------------------------------------
J1          -45.00°      -44.50°       -0.50°
J2          -90.00°      -89.80°       -0.20°
J3            0.00°        0.10°       -0.10°
J4          -90.00°      -90.30°        0.30°
J5           90.00°       89.70°        0.30°
J6            0.00°        0.20°       -0.20°
--------------------------------------------------
RMS Error: 0.31°

Offset arrays for configuration:
Radians: [-0.008727, -0.003491, -0.001745, 0.005236, 0.005236, -0.003491]
Degrees: [-0.50, -0.20, -0.10, 0.30, 0.30, -0.20]
```

## Usage Workflow

### For Teleoperation Setup

1. **Check UR5 positions:**
   ```bash
   python scripts/get_ur_angles.py --both
   ```

2. **Align GELLO to match UR5 pose**

3. **Calculate offsets:**
   ```bash
   python scripts/calc_ur_gello_offsets.py --save configs/calibration_offsets.json
   ```

4. **Monitor alignment during operation:**
   ```bash
   python scripts/show_ur_gello_offset.py
   ```

### For Debugging

1. **Check if UR5 is responding:**
   ```bash
   python scripts/get_ur_angles.py --ip 192.168.1.211 --continuous
   ```

2. **Monitor offset drift during teleop:**
   ```bash
   python scripts/show_ur_gello_offset.py --left
   ```

3. **Verify calibration quality:**
   ```bash
   python scripts/calc_ur_gello_offsets.py
   # Look for RMS error < 2° for good calibration
   ```

## Default Connections

### Left Arm
- UR5 IP: `192.168.1.211`
- GELLO Port: `/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT7WBEIA-if00-port0`

### Right Arm
- UR5 IP: `192.168.1.210`
- GELLO Port: `/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT8J0XJV-if00-port0`

## Existing Related Scripts

- `get_ur_start.py` - Simple script to get UR5 positions (uses ROBOT_IP env var)
- `calc_offsets.py` - Original offset calculator for GELLO calibration
- `align_gello_to_ur.py` - Helps align GELLO to match UR5 pose

## Tips

1. **For best calibration:**
   - Put both robots in the same neutral pose
   - Use `calc_ur_gello_offsets.py` to measure offsets
   - Save offsets for use in teleop configuration

2. **During teleoperation:**
   - Use `show_ur_gello_offset.py` to monitor drift
   - Large offsets indicate calibration issues or communication delays

3. **Troubleshooting:**
   - If UR5 not responding: Check network and ExternalControl.urp
   - If GELLO not responding: Check USB connection and port permissions
   - If offsets are large: Recalibrate or check mechanical alignment

---
*These tools help ensure accurate teleoperation by monitoring and correcting position offsets between UR5 and GELLO robots.*

