# ZCM GELLO-UR5 INTEGRATION

## ✅ Overview

The teleoperation system now publishes GELLO-UR5 offset data to ZCM in a format compatible with `zcm-spy`, following the pattern of `send_gripper_cmd.py`.

## 🎯 What Was Implemented

### 1. New ZCM Message Type
Created `gello_ur_offsets.zcm` for GELLO-UR5 offset data:
```
struct gello_ur_offsets_t {
    int64_t timestamp;
    double left_joint_offsets[6];   // J1-J6 offsets
    double left_gripper_position;   // J7 position
    double left_rms_error;
    boolean left_valid;
    
    double right_joint_offsets[6];  // J10-J15 offsets
    double right_gripper_position;  // J16 position
    double right_rms_error;
    boolean right_valid;
    
    string description;
}
```

### 2. Updated `streamdeck_pedal_watch.py`
- Added `--monitor-ur5` flag to enable GELLO-UR5 offset monitoring
- Connects to UR5 robots at:
  - LEFT: 192.168.1.211
  - RIGHT: 192.168.1.210
- Publishes offsets to `gello_ur_offsets` channel
- Calculates GELLO - UR5 for each joint

### 3. New Scripts
- `send_gello_ur_offsets_test.py` - Test publisher for offsets
- `receive_gello_ur_offsets.py` - Receiver to display offset data

## 📊 ZCM Channels

The system now publishes to these channels (all zcm-spy compatible):

| Channel | Message Type | Content |
|---------|-------------|---------|
| `gello_positions_left` | `gello_positions_t` | Left GELLO arm (J1-J7) |
| `gello_positions_right` | `gello_positions_t` | Right GELLO arm (J10-J16) |
| `arm_transform` | `arm_transform_t` | Left-Right GELLO offsets |
| `gello_ur_offsets` | `gello_ur_offsets_t` | GELLO-UR5 offsets |

## 🚀 Usage

### Start Teleoperation with UR5 Monitoring
```bash
python scripts/streamdeck_pedal_watch.py --monitor-ur5
```

This will:
1. Connect to both UR5 robots
2. Read GELLO positions from Dynamixel servos
3. Calculate offsets (GELLO - UR5)
4. Publish to all ZCM channels

### View GELLO-UR5 Offsets
```bash
# In terminal 1: Start teleoperation
python scripts/streamdeck_pedal_watch.py --monitor-ur5

# In terminal 2: View offsets
python scripts/receive_gello_ur_offsets.py
```

Output shows:
```
📍 LEFT ARM (J1-J7 vs UR5):
  ✓ VALID DATA
  Joint Offsets (GELLO - UR5):
    J1:   +1.126° (+0.01966 rad)  [Color coded]
    J2:   +0.159° (+0.00277 rad)
    ...
    J7 (Gripper):   28.65° (GELLO only)
  RMS Error:   0.610°

📍 RIGHT ARM (J10-J16 vs UR5):
  ✓ VALID DATA
  Joint Offsets (GELLO - UR5):
    J10:  +1.362° (+0.02378 rad)  [Color coded]
    J11:  -0.354° (-0.00618 rad)
    ...
    J16 (Gripper):   40.11° (GELLO only)
  RMS Error:   0.741°
```

### View in zcm-spy
```bash
# Terminal 1: Start teleoperation
python scripts/streamdeck_pedal_watch.py --monitor-ur5

# Terminal 2: Run zcm-spy
zcm-spy
```

In zcm-spy, you'll see:
- `gello_positions_left` - Left GELLO positions
- `gello_positions_right` - Right GELLO positions
- `gello_ur_offsets` - GELLO-UR5 offset data
- All messages are properly decoded and viewable

## 🎨 Color Coding

### Joint Offsets
- 🟢 **Green**: < 5° (Good calibration)
- 🟡 **Yellow**: 5-10° (Moderate offset)
- 🔴 **Red**: > 10° (Needs calibration)

### RMS Error
- 🟢 **Green**: < 2° (Excellent)
- 🟡 **Yellow**: 2-5° (Acceptable)
- 🔴 **Red**: > 5° (Needs attention)

## 🧪 Testing

### Test GELLO-UR5 Offset Publishing
```bash
# Send test offset data
python scripts/send_gello_ur_offsets_test.py --sin

# Receive and display
python scripts/receive_gello_ur_offsets.py
```

### Test Full System
```bash
# With real robots
python scripts/streamdeck_pedal_watch.py --monitor-ur5

# With simulated data (no robots needed)
python scripts/streamdeck_pedal_watch.py --test-mode --monitor-ur5
```

## 📝 Command-Line Options

### streamdeck_pedal_watch.py
- `--monitor-ur5` - Enable GELLO-UR5 offset monitoring
- `--show-transform` - Display LEFT-RIGHT offsets inline
- `--no-zcm` - Disable all ZCM publishing
- `--no-transform` - Disable transform publishing
- `--test-mode` - Auto-start without pedals

### receive_gello_ur_offsets.py
- `-v, --verbose` - Show detailed output
- `-c, --channel` - Specify channel (default: gello_ur_offsets)

## 🔧 Technical Details

### Data Flow
```
GELLO Arms (DXL)          UR5 Robots (RTDE)
      ↓                          ↓
PositionMonitor._monitor_loop()
      ↓                          ↓
_publish_positions()    _publish_ur_offsets()
      ↓                          ↓
gello_positions_*       gello_ur_offsets
      ↓                          ↓
    ZCM                        ZCM
      ↓                          ↓
  zcm-spy                    zcm-spy
```

### Update Rate
- GELLO positions: 10 Hz
- UR5 positions: Read at 10 Hz
- ZCM publishing: 10 Hz
- All synchronized in the same control loop

### Message Compatibility
All messages follow the pattern from `send_gripper_cmd.py`:
- Proper ZCM IDL definition (`.zcm` files)
- Generated Python bindings (`zcm-gen -p`)
- Timestamped messages
- Valid fingerprints for zcm-spy

## ✅ Summary

The system now provides complete visibility into:
1. **GELLO positions** for both arms (J1-J7, J10-J16)
2. **GELLO-GELLO offsets** (LEFT - RIGHT)
3. **GELLO-UR5 offsets** for calibration monitoring

All data is published to ZCM in a zcm-spy compatible format, enabling:
- Real-time monitoring
- Calibration verification
- Data logging
- System debugging

The integration is seamless - just add `--monitor-ur5` to enable UR5 offset monitoring!
