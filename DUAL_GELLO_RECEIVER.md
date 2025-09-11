# Dual GELLO Arm Receiver

## Overview

The `receive_gello_both.py` script receives and displays position data from both GELLO arms simultaneously. It subscribes to both `gello_positions_left` and `gello_positions_right` ZCM channels and provides a unified view of both arms' states.

## Features

- **Real-time Monitoring**: Displays joint positions for both arms in real-time
- **Multiple Display Modes**: Three different visualization options
- **Offset Calculation**: Shows the difference between left and right arm positions
- **Message Rate Tracking**: Displays update frequency for each arm
- **Color Coding**: Visual indicators for status and offset magnitudes
- **RMS Error Calculation**: Overall alignment metric between arms

## Usage

### Basic Usage

```bash
# Start the dual receiver
python scripts/receive_gello_both.py
```

### Display Modes

1. **Side-by-Side Mode** (default)
   ```bash
   python scripts/receive_gello_both.py --mode side_by_side
   ```
   - Shows both arms' data side by side
   - Includes offset calculations
   - Best for comparing arm positions

2. **Stacked Mode**
   ```bash
   python scripts/receive_gello_both.py --mode stacked
   ```
   - Shows arms vertically stacked
   - More compact vertical layout
   - Good for narrow terminals

3. **Compact Mode**
   ```bash
   python scripts/receive_gello_both.py --mode compact
   ```
   - Single-line display for each arm
   - Minimal screen space usage
   - Updates in place

### Verbose Output

```bash
python scripts/receive_gello_both.py --verbose
```
- Shows detailed message information
- Includes timestamps and message counts
- Useful for debugging

## Output Format

### Side-by-Side Display
```
[14:32:15.123] DUAL GELLO ARM POSITIONS
================================================================================
LEFT ARM ✓  [ 20.3 Hz] #142    | RIGHT ARM ✓ [ 20.1 Hz] #140
--------------------------------------------------------------------------------
  J1:  -45.20° (-0.7890 rad)   |   J1:  -44.80° (-0.7820 rad)
  J2:  -90.10° (-1.5725 rad)   |   J2:  -89.95° (-1.5699 rad)
  J3:    0.15° ( 0.0026 rad)   |   J3:    0.12° ( 0.0021 rad)
  J4:  -90.30° (-1.5760 rad)   |   J4:  -90.25° (-1.5751 rad)
  J5:   89.85° ( 1.5681 rad)   |   J5:   90.10° ( 1.5725 rad)
  J6:    0.10° ( 0.0017 rad)   |   J6:    0.08° ( 0.0014 rad)
  Gripper: 45.00° (0.7854 rad) |   Gripper: 44.50° (0.7767 rad)
--------------------------------------------------------------------------------

OFFSET (LEFT - RIGHT):
  J1:  -0.40°    J2:  -0.15°    J3:  +0.03°  
  J4:  -0.05°    J5:  -0.25°    J6:  +0.02°  
  RMS: 0.24°
```

### Color Coding

- **Joint Status**:
  - 🟢 Green: Normal range (|angle| < 90°)
  - 🟡 Yellow: Extended range (90° < |angle| < 180°)
  - 🔴 Red: Out of range (|angle| > 180°)

- **Offset Magnitude**:
  - 🟢 Green: Small offset (< 2°)
  - 🟡 Yellow: Medium offset (2-5°)
  - 🔴 Red: Large offset (> 5°)

## Testing

### Test with Simulated Data

```bash
# Terminal 1: Start receiver
python scripts/receive_gello_both.py

# Terminal 2: Send test messages
python scripts/send_gello_test.py --arm both --mode sine
```

### Test with Real Hardware

```bash
# Start teleoperation with ZCM publishing
python scripts/streamdeck_pedal_watch.py

# In another terminal, monitor both arms
python scripts/receive_gello_both.py
```

## Integration with Teleoperation

The dual receiver works seamlessly with the teleoperation system:

1. **During Calibration**: Monitor arm alignment
2. **During Operation**: Verify synchronized movement
3. **For Debugging**: Identify drift or misalignment issues

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-v, --verbose` | Show detailed message info | False |
| `-m, --mode` | Display mode (side_by_side, stacked, compact) | side_by_side |
| `--left-channel` | Left arm ZCM channel name | gello_positions_left |
| `--right-channel` | Right arm ZCM channel name | gello_positions_right |

## Example Workflows

### 1. Monitor During Calibration
```bash
# Check arm alignment during calibration
python scripts/receive_gello_both.py --mode side_by_side
# Look for small offsets (< 2° RMS error)
```

### 2. Debug Communication Issues
```bash
# Verbose mode to see message details
python scripts/receive_gello_both.py --verbose
# Check message rates and validity flags
```

### 3. Continuous Monitoring
```bash
# Compact mode for long-running sessions
python scripts/receive_gello_both.py --mode compact
# Minimal screen usage, updates in place
```

## Troubleshooting

### No Messages Received
- Check that the sender is running (`streamdeck_pedal_watch.py` or `send_gello_test.py`)
- Verify ZCM is properly installed: `pip install zerocm`
- Ensure `gello_positions_t.py` exists in scripts directory

### Import Errors
```bash
# Regenerate ZCM bindings if needed
cd scripts
zcm-gen -p gello_positions_simple.zcm
```

### High Offset Values
- Indicates misalignment between arms
- Run calibration: `python scripts/calc_ur_gello_offsets.py`
- Check mechanical alignment of GELLO arms

## Related Scripts

- `receive_gello_left.py` - Monitor left arm only
- `receive_gello_right.py` - Monitor right arm only
- `send_gello_test.py` - Send test messages
- `streamdeck_pedal_watch.py` - Main teleop with ZCM publishing
- `calc_manual_offsets.py` - Calculate offsets between positions
