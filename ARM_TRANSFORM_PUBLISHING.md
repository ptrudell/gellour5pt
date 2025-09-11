# ARM TRANSFORM PUBLISHING SYSTEM

## ✅ System Overview

The `receive_gello_both.py` script now publishes arm transformations (left - right offsets) to ZCM in a format compatible with `zcm-spy`, following the pattern from `send_gripper_cmd.py`.

## 📊 Message Format

### ZCM IDL Definition (`arm_transform.zcm`)
```idl
struct arm_transform_t
{
    int64_t timestamp;          // microseconds since epoch
    double joint_offsets[6];    // radians, left - right for each joint
    double gripper_offset;      // radians, left - right gripper
    double rms_error;           // radians, root mean square error
    boolean transform_valid;    // true if transform is valid
    string description;         // human-readable description
}
```

## 🚀 Quick Start

### 1. Generate ZCM Bindings (if needed)
```bash
cd scripts
zcm-gen -p arm_transform.zcm
```

### 2. Run the System

#### Option A: With Real Robots
```bash
# Terminal 1: Start teleop (publishes GELLO positions)
python scripts/streamdeck_pedal_watch.py

# Terminal 2: Receive positions and publish transforms
python scripts/receive_gello_both.py
```

#### Option B: With Simulated Data
```bash
# Terminal 1: Simulated positions
python scripts/test_position_monitor_zcm.py

# Terminal 2: Receive and transform
python scripts/receive_gello_both.py
```

### 3. Monitor Transforms

#### Using Custom Receiver
```bash
python scripts/receive_arm_transform.py
```

#### Using zcm-spy
```bash
zcm-spy
# Select "arm_transform" channel
# View arm_transform_t messages
```

## 📦 Components

### Publishers
- **`receive_gello_both.py`** - Main script that:
  - Subscribes to `gello_positions_left` and `gello_positions_right`
  - Calculates transformation (left - right)
  - Publishes to `arm_transform` channel

### Receivers
- **`receive_arm_transform.py`** - Displays transform data with color coding
- **`zcm-spy`** - Standard ZCM monitoring tool

### Test Tools
- **`send_arm_transform_test.py`** - Test publisher for transforms
  - `--static` - Send constant transform values
  - `--sin` - Send sinusoidal transforms

## 📈 Data Flow

```
GELLO Left Arm  ─┐
                 ├─> receive_gello_both.py ─> arm_transform channel ─> zcm-spy
GELLO Right Arm ─┘                                                  └─> receive_arm_transform.py
```

## 🔧 Configuration

### Channels
- Input: `gello_positions_left`, `gello_positions_right`
- Output: `arm_transform` (default, configurable)

### Command Line Options
```bash
python scripts/receive_gello_both.py [options]
  --mode {side_by_side,stacked,compact}  # Display mode
  --verbose                               # Detailed output
  --no-transform                          # Disable transform publishing
  --transform-channel CHANNEL            # Custom transform channel
```

## 📊 Example Output

### Transform Receiver Display
```
[Message #1] Rate: 10.0 Hz
----------------------------------------
✓ VALID TRANSFORM

Joint Offsets (LEFT - RIGHT):
  J1:   -1.935° (-0.03377 rad)
  J2:   +0.778° (+0.01358 rad)
  J3:   -0.333° (-0.00581 rad)
  J4:   +0.893° (+0.01558 rad)
  J5:   -1.053° (-0.01838 rad)
  J6:   +0.413° (+0.00720 rad)

Gripper Offset:  -13.322° (-0.23251 rad)
RMS Error:    1.044° ( 0.01822 rad)
Description: Transform: LEFT - RIGHT (RMS: 1.04°)
```

### Color Coding
- 🟢 **Green**: Small offset (< 5°)
- 🟡 **Yellow**: Medium offset (5-10°)
- 🔴 **Red**: Large offset (> 10°)

## 🧪 Testing

### 1. Test Transform Publishing
```bash
# Send test transforms
python scripts/send_arm_transform_test.py --sin

# In another terminal, receive them
python scripts/receive_arm_transform.py
```

### 2. Test Complete Pipeline
```bash
# Terminal 1: Simulated arm positions
python scripts/test_position_monitor_zcm.py

# Terminal 2: Transform and display
python scripts/receive_gello_both.py

# Terminal 3: Monitor transforms
python scripts/receive_arm_transform.py
```

### 3. Verify with zcm-spy
```bash
# Terminal 1: Send test data
python scripts/send_arm_transform_test.py --static

# Terminal 2: Open zcm-spy
zcm-spy
# Look for "arm_transform" channel
# Double-click to view messages
```

## 🔍 Troubleshooting

### No Transform Messages
1. Check both arm positions are being received:
   ```bash
   python scripts/receive_gello_both.py --verbose
   ```
2. Verify ZCM is initialized correctly
3. Check `--no-transform` flag is not set

### Wrong Channel
- Default is `arm_transform`
- Use `--transform-channel` to change:
  ```bash
  python scripts/receive_gello_both.py --transform-channel my_transform
  ```

### zcm-spy Not Showing Messages
1. Regenerate bindings:
   ```bash
   cd scripts && zcm-gen -p arm_transform.zcm
   ```
2. Verify publisher is running
3. Check ZCM transport settings

## 📝 Integration Example

To use transform data in your code:

```python
import zerocm
from arm_transform_t import arm_transform_t

def handle_transform(channel, msg):
    print(f"RMS Error: {np.degrees(msg.rms_error):.2f}°")
    for i, offset in enumerate(msg.joint_offsets):
        print(f"J{i+1} offset: {np.degrees(offset):.2f}°")

zcm = zerocm.ZCM()
zcm.subscribe("arm_transform", arm_transform_t, handle_transform)
zcm.start()
```

## ✅ Summary

The arm transformation system is fully operational and compatible with `zcm-spy`. It provides real-time offset calculations between left and right GELLO arms, making it easy to:
- Monitor arm synchronization
- Detect calibration issues
- Log transformation data
- Integrate with other systems