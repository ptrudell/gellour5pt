# GELLO to UR5 Gripper Mapping Guide

## 🚀 Speed Improvements (NEW!)

**Connection time reduced from 10-15 seconds to < 2 seconds!**
- Skips unnecessary UR robot connection
- Connects only to DXL servos for gripper reading
- Optimized timeouts and connection flow

## 🎯 Quick Start

Run these scripts from `/home/shared/gellour5pt/`:

### 1. ⚡ Instant Test (< 2 sec, uses saved calibration)
```bash
python scripts/test_gripper_instant.py
```
- Ultra-fast with cached calibration
- Auto-calibrates if no cache exists
- Best for repeated testing

### 2. 🚀 Fast Test (< 3 sec, auto-calibration)
```bash
python scripts/test_gripper_fast.py
```
- Direct DXL connection (no URDynamixelRobot overhead)
- Automatic timed calibration
- No manual input needed

### 3. ✓ Standard Test (< 5 sec, manual calibration)
```bash
python scripts/test_gripper_only.py
```
- Tests ONLY gripper control (no arm movement)
- Manual calibration (you control timing)
- Shows exact values to update in `streamdeck_pedal_watch.py`

### 4. Advanced Gripper Mapper (Full featured)
```bash
python scripts/gello_to_ur_gripper_mapper.py
```
- Full calibration and mapping system
- Saves calibration for reuse
- Linear interpolation for smooth control
- Real-time testing

### 5. Quick Position Finder (No UR commands)
```bash
python scripts/quick_gripper_test.py
```
- Just finds GELLO positions
- No UR5 commands sent
- Good for checking hardware

## 📋 How It Works

### GELLO Gripper Positions
Each GELLO gripper (IDs 7 and 16) has a range of motion:
- **CLOSED**: Minimum position (squeezed)
- **OPEN**: Maximum position (released)

### UR5 Gripper Commands
The UR5 grippers use these fixed commands:
- **CLOSED**: `-0.075`
- **OPEN**: `0.25`

### Mapping Strategy

#### Simple Threshold (Current Implementation)
```python
if gello_position < threshold:
    send_command(-0.075)  # CLOSED
else:
    send_command(0.25)    # OPEN
```

#### Linear Interpolation (Smooth Control)
```python
normalized = (gello_pos - min) / (max - min)
ur_command = -0.075 + normalized * (0.25 - (-0.075))
```

## 🔧 Update streamdeck_pedal_watch.py

After running the test scripts, update these lines:

### LEFT Gripper (Line 887)
```python
gripper_threshold = X.XX  # Your calculated value
```

### RIGHT Gripper (Line 972)
```python
gripper_threshold = Y.YY  # Your calculated value
```

## 📊 Typical Values

Based on testing, typical GELLO gripper ranges are:

### LEFT (ID 7)
- CLOSED: ~2.5 rad (144°)
- OPEN: ~3.4 rad (195°)
- Threshold: ~2.97 rad

### RIGHT (ID 16)
- CLOSED: ~4.1 rad (235°)
- OPEN: ~5.1 rad (292°)
- Threshold: ~4.60 rad

## 🧪 Testing Procedure

1. **Find Positions**
   ```bash
   python scripts/test_gripper_only.py
   ```
   - Squeeze grippers closed, press ENTER
   - Release grippers open, press ENTER
   - Note the threshold values

2. **Update Script**
   - Edit `scripts/streamdeck_pedal_watch.py`
   - Update line 887 (left threshold)
   - Update line 972 (right threshold)

3. **Test Full System**
   ```bash
   python scripts/run_teleop.py
   ```
   - Verify grippers respond correctly
   - Check for smooth operation

## 🐛 Troubleshooting

### Grippers Not Responding
- Check GELLO DXL connections
- Verify UR5 external control is running
- Test with `scripts/test_gripper_commands.py`

### Wrong Direction
- If gripper opens when it should close, swap the threshold logic
- Or adjust the comparison operator (< to >)

### Too Sensitive/Not Sensitive Enough
- Adjust threshold values up/down
- Consider using linear interpolation for smoother control

## 📈 Advanced Features

### Hysteresis (Prevent Flapping)
Add two thresholds to prevent rapid switching:
```python
if gello_pos < (threshold - 0.1):
    state = "CLOSED"
elif gello_pos > (threshold + 0.1):
    state = "OPEN"
# else: keep previous state
```

### Deadband (Ignore Small Movements)
Only send commands if position changes significantly:
```python
if abs(new_pos - last_pos) > 0.05:
    send_command(new_pos)
```

### Rate Limiting
Prevent command spam:
```python
if time.time() - last_command_time > 0.2:
    send_command(position)
```

## 📦 Files Created

- `scripts/test_gripper_only.py` - Simple gripper test
- `scripts/gello_to_ur_gripper_mapper.py` - Advanced mapper
- `scripts/quick_gripper_test.py` - Position finder
- `scripts/monitor_gello_grippers.py` - Real-time monitor
- `/tmp/gello_gripper_calibration.json` - Saved calibration
