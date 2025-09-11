# GELLO-UR5 Offset Publisher Separation

## ✅ Overview

Successfully separated the GELLO-UR5 offset calculation from the main teleoperation script into a dedicated, standalone publisher. This creates a cleaner, more modular architecture.

## 🎯 What Changed

### New File Created
**`scripts/gello_ur_offset_publisher.py`**
- Standalone ZCM publisher for GELLO-UR5 joint offsets
- Subscribes to: `gello_positions_left`, `gello_positions_right`
- Publishes to: `gello_ur_offset_left`, `gello_ur_offset_right`
- Connects directly to UR5 robots via RTDE
- Uses the same `gello_positions_t` message schema for offsets

### Cleaned Up `streamdeck_pedal_watch.py`
Removed:
- `arm_transform_t` import and publishing
- `gello_ur_offsets_t` import and publishing
- RTDE/UR5 connection code
- `_publish_transform()` method
- `_connect_ur5_robots()` method
- `_publish_ur_offsets()` method
- Command line arguments: `--show-transform`, `--monitor-ur5`, `--no-transform`
- Transform display code in monitor loop

Now only publishes:
- `gello_positions_left` - Raw GELLO left arm positions
- `gello_positions_right` - Raw GELLO right arm positions

### Files Deleted (No Longer Needed)
- `scripts/arm_transform.zcm`
- `scripts/arm_transform_t.py`
- `scripts/gello_ur_offsets.zcm`
- `scripts/gello_ur_offsets_t.py`
- `scripts/receive_arm_transform.py`
- `scripts/send_gello_ur_offsets_test.py`
- `scripts/receive_gello_ur_offsets.py`

## 📊 Architecture

### Before (Monolithic)
```
streamdeck_pedal_watch.py
    ├── Reads GELLO positions
    ├── Connects to UR5 robots
    ├── Calculates LEFT-RIGHT offsets
    ├── Calculates GELLO-UR5 offsets
    └── Publishes 4 different channels
```

### After (Modular)
```
streamdeck_pedal_watch.py
    ├── Reads GELLO positions
    └── Publishes: gello_positions_left/right

gello_ur_offset_publisher.py (OPTIONAL)
    ├── Subscribes to: gello_positions_left/right
    ├── Connects to UR5 robots
    ├── Calculates GELLO-UR5 offsets
    └── Publishes: gello_ur_offset_left/right
```

## 🚀 Usage

### Basic Teleoperation (No Offsets)
```bash
# Just run the main script
python scripts/streamdeck_pedal_watch.py
```

### With GELLO-UR5 Offset Monitoring
```bash
# Terminal 1: Main teleoperation
python scripts/streamdeck_pedal_watch.py

# Terminal 2: Offset publisher (optional)
python scripts/gello_ur_offset_publisher.py --verbose
```

### Offset Publisher Options
```bash
python scripts/gello_ur_offset_publisher.py \
    --left-ur 192.168.1.211 \      # Left UR5 IP
    --right-ur 192.168.1.210 \     # Right UR5 IP
    --rate 50 \                    # Publishing rate (Hz)
    --verbose                       # Show RMS errors
```

## 🎯 Benefits

1. **Separation of Concerns**
   - Main script focuses on teleoperation
   - Offset calculation is optional/separate

2. **Better Performance**
   - No unnecessary UR5 connections if offsets not needed
   - Reduced CPU usage in main script

3. **Cleaner Code**
   - ~300 lines removed from main script
   - Single responsibility per script

4. **Flexible Deployment**
   - Can run teleoperation without UR5 monitoring
   - Can add offset monitoring on demand

5. **No ZCM Pollution**
   - Only publishes channels that are actually needed
   - `zcm-spy` shows cleaner output

## ✅ Testing Results

All components tested and working:
- `streamdeck_pedal_watch.py`: Publishing at 1Hz
- `gello_ur_offset_publisher.py`: Publishing at 50Hz
- Both UR5 robots connecting successfully
- All 4 channels active when both scripts running
- Offset calculations correct (RMS ~80-90°)

## 📝 Technical Details

### Message Schema
The offset publisher uses the SAME `gello_positions_t` schema:
- `timestamp`: Current time in microseconds
- `arm_side`: "left" or "right"
- `is_valid`: True if both GELLO and UR5 data available
- `joint_positions`: **OFFSETS** (GELLO - UR5) in radians
- `gripper_position`: NaN (UR5 has no gripper joint)

### Offset Calculation
```python
offset[i] = wrap_to_pi(gello[i] - ur[i])
```
Where `wrap_to_pi` normalizes angles to (-π, π] range.

### Publishing Rate
- Main script: 1Hz (configurable)
- Offset publisher: 50Hz default (configurable via --rate)

## 🔧 Troubleshooting

### UR5 Connection Issues
```bash
# Check UR5 connectivity
ping 192.168.1.211  # Left UR5
ping 192.168.1.210  # Right UR5
```

### No Offset Messages
1. Check that `streamdeck_pedal_watch.py` is running
2. Verify GELLO positions being published:
   ```bash
   python scripts/receive_gello_left.py
   ```
3. Check UR5 connections in offset publisher output

### High RMS Errors
Normal if robots are in different positions. The offsets show the difference between GELLO and UR5 joint angles.

## 📚 Summary

The separation creates a cleaner, more maintainable system where:
- Core teleoperation functionality is isolated
- UR5 offset monitoring is optional
- Each component has a single, clear responsibility
- The system is more flexible and easier to debug
