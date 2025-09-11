# ZCM GELLO Position Publishing Guide

## Overview
Added ZCM (ZeroCM) message publishing to the `streamdeck_pedal_watch.py` script to broadcast GELLO arm positions over network channels. This allows other programs to subscribe and receive real-time joint and gripper positions.

## Architecture

### Message Type: `gello_positions_t`
Custom message type defined in `scripts/gello_positions_t.py`:
- **timestamp**: Microseconds since epoch
- **joint_positions**: Array of 6 joint angles in radians
- **gripper_position**: Gripper angle in radians
- **joint_velocities**: Array of 6 joint velocities (currently zeros)
- **is_valid**: Boolean data validity flag
- **arm_side**: String "left" or "right"

### ZCM Channels
- **Left Arm**: `gello_positions_left`
- **Right Arm**: `gello_positions_right`
- **Publishing Rate**: 10 Hz (same as position monitor display)

## Scripts Created

### 1. **Main Teleop Script** (`streamdeck_pedal_watch.py`)
- Modified to include ZCM publishing in PositionMonitor class
- Publishes GELLO positions automatically when running
- Can disable with `--no-zcm` flag

### 2. **Message Type** (`gello_positions_t.py`)
- Defines the ZCM message structure
- Includes encode/decode methods for serialization
- Compatible with zerocm library

### 3. **Left Arm Receiver** (`receive_gello_left.py`)
```bash
# Basic usage (compact display)
python scripts/receive_gello_left.py

# Verbose mode (detailed output)
python scripts/receive_gello_left.py --verbose
```

### 4. **Right Arm Receiver** (`receive_gello_right.py`)
```bash
# Basic usage (compact display)
python scripts/receive_gello_right.py

# Verbose mode (detailed output)
python scripts/receive_gello_right.py --verbose
```

### 5. **Dual Arm Receiver** (`receive_gello_both.py`)
```bash
# Monitor both arms simultaneously
python scripts/receive_gello_both.py

# Verbose mode
python scripts/receive_gello_both.py --verbose
```

### 6. **Test Publisher** (`publish_test_gello.py`)
```bash
# Publish sine wave pattern to both arms
python scripts/publish_test_gello.py

# Different patterns
python scripts/publish_test_gello.py --mode step    # Step changes
python scripts/publish_test_gello.py --mode static  # Static positions
python scripts/publish_test_gello.py --mode random  # Random movements

# Single arm
python scripts/publish_test_gello.py --arm left
python scripts/publish_test_gello.py --arm right

# Custom rate
python scripts/publish_test_gello.py --rate 20  # 20 Hz
```

## Installation Requirements

```bash
# Install zerocm library
pip install zerocm
```

## Usage Examples

### 1. Normal Teleoperation with ZCM Publishing
```bash
# Run teleop with ZCM publishing enabled (default)
python scripts/streamdeck_pedal_watch.py -c configs/teleop_dual_ur5.yaml

# In another terminal, monitor the positions
python scripts/receive_gello_both.py
```

### 2. Testing Without Hardware
```bash
# Terminal 1: Publish test data
python scripts/publish_test_gello.py --mode sine

# Terminal 2: Receive left arm
python scripts/receive_gello_left.py

# Terminal 3: Receive right arm
python scripts/receive_gello_right.py
```

### 3. Disable ZCM Publishing
```bash
# Run teleop without ZCM (console display only)
python scripts/streamdeck_pedal_watch.py -c configs/teleop_dual_ur5.yaml --no-zcm
```

## Message Format Example

When receiving messages with verbose mode, you'll see:
```
[Message #123] (10.0 Hz)
  Timestamp: 1703123456789012 µs
  Arm: left
  Valid: True
  Joints (deg):
    J1:  -45.20° (-0.7892 rad)
    J2:  -90.50° (-1.5795 rad)
    J3:    0.00° ( 0.0000 rad)
    J4:  -90.00° (-1.5708 rad)
    J5:   90.00° ( 1.5708 rad)
    J6:    0.00° ( 0.0000 rad)
  Gripper:  143.50° ( 2.5049 rad)
```

## Integration with Other Systems

To use GELLO positions in your own Python code:

```python
import zerocm
from gello_positions_t import gello_positions_t

def handle_gello_positions(channel, msg):
    """Handle incoming GELLO position messages."""
    print(f"Received {msg.arm_side} arm positions:")
    for i, pos in enumerate(msg.joint_positions):
        print(f"  Joint {i+1}: {pos:.4f} rad")
    print(f"  Gripper: {msg.gripper_position:.4f} rad")
    print(f"  Valid: {msg.is_valid}")

# Initialize ZCM
zcm = zerocm.ZCM()
if not zcm.good():
    print("Unable to initialize ZCM")
    exit(1)

# Subscribe to channels
zcm.subscribe("gello_positions_left", gello_positions_t, handle_gello_positions)
zcm.subscribe("gello_positions_right", gello_positions_t, handle_gello_positions)

# Start receiving
zcm.start()
try:
    while True:
        time.sleep(0.01)
except KeyboardInterrupt:
    zcm.stop()
```

## Troubleshooting

### zerocm not installed
```bash
pip install zerocm
```

### No messages received
1. Check that the teleop script is running with ZCM enabled
2. Verify network connectivity (ZCM uses UDP multicast)
3. Check firewall settings for UDP port 7667

### Performance considerations
- Publishing at 10Hz has minimal overhead
- ZCM uses efficient binary serialization
- Messages are only published when robots are connected

## Benefits

1. **Network Distribution**: Multiple programs can subscribe to position data
2. **Language Agnostic**: ZCM supports C++, Python, Java, etc.
3. **Low Latency**: Efficient UDP multicast communication
4. **Debugging**: Easy to monitor robot state from any machine
5. **Integration**: Simple to integrate with other control systems

---
*ZCM publishing added to enable real-time GELLO position streaming for multi-process teleoperation systems.*
