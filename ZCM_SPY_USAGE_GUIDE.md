# ZCM-SPY Usage Guide for GELLO Position Messages

## Overview
This guide explains how to use `zcm-spy` to monitor GELLO arm position messages. The messages are now properly formatted with ZCM type definitions, making them compatible with all ZCM tools including `zcm-spy`.

## Setup Complete
✅ Created proper ZCM type definition file (`gello_positions.zcm`)
✅ Generated Python bindings using `zcm-gen`
✅ Updated all scripts to use generated bindings
✅ Messages now include proper fingerprinting for zcm-spy

## Message Structure

The `gello_positions_t` message contains:
- **timestamp**: int64_t - microseconds since epoch
- **joint_positions[6]**: double - 6 joint angles in radians
- **gripper_position**: double - gripper angle in radians
- **joint_velocities[6]**: double - 6 joint velocities (currently zeros)
- **is_valid**: boolean - data validity flag
- **arm_side**: string - "left" or "right"

## Using zcm-spy

### 1. Basic Usage
```bash
# Open zcm-spy GUI
zcm-spy

# In another terminal, run the teleop or test publisher
python scripts/streamdeck_pedal_watch.py -c configs/teleop_dual_ur5.yaml
# OR for testing:
python scripts/publish_test_gello.py
```

### 2. Command-Line zcm-spy
```bash
# Monitor specific channel
zcm-spy --channel "gello_positions_left"
zcm-spy --channel "gello_positions_right"

# Show all channels
zcm-spy --print-all
```

### 3. With Type Path
If zcm-spy can't find the types automatically:
```bash
# Tell zcm-spy where to find the type definitions
export ZCM_DEFAULT_URL="udpm://239.255.76.67:7667?ttl=1"
zcm-spy --zcm-types="/home/shared/gellour5pt/scripts"
```

### 4. Recording and Playback
```bash
# Record messages to a log file
zcm-logger gello_positions.zcmlog

# Playback recorded messages
zcm-logplayer gello_positions.zcmlog

# View log file with spy
zcm-spy --log-file gello_positions.zcmlog
```

## Channels

- **gello_positions_left**: Left GELLO arm positions
- **gello_positions_right**: Right GELLO arm positions

## Testing

### Quick Test
```bash
# Terminal 1: Start test publisher
python scripts/publish_test_gello.py --mode sine --rate 10

# Terminal 2: Open zcm-spy
zcm-spy

# You should see:
# - gello_positions_left channel
# - gello_positions_right channel
# - Message counts incrementing
# - Proper decoding of message fields
```

### Verify with Receivers
```bash
# Terminal 1: Publisher
python scripts/publish_test_gello.py

# Terminal 2: Left receiver
python scripts/receive_gello_left.py --verbose

# Terminal 3: Right receiver
python scripts/receive_gello_right.py --verbose

# Terminal 4: zcm-spy
zcm-spy
```

## Troubleshooting

### zcm-spy shows "Unknown Type"
- Make sure you're using the generated bindings (gello_msgs.gello_positions_t)
- The .zcm file must be in the same directory or in ZCM's search path
- Try specifying the type path: `zcm-spy --zcm-types="/home/shared/gellour5pt/scripts"`

### No messages appearing
- Check that ZCM is using the correct network interface
- Verify firewall isn't blocking UDP port 7667
- Test with local publisher first

### Decoding errors
- Ensure all scripts use the same message definition
- Regenerate bindings if you modify the .zcm file:
  ```bash
  cd /home/shared/gellour5pt/scripts
  zcm-gen -p gello_positions.zcm
  ```

## File Locations

- **Type Definition**: `/home/shared/gellour5pt/scripts/gello_positions.zcm`
- **Generated Python**: `/home/shared/gellour5pt/scripts/gello_msgs/gello_positions_t.py`
- **Publisher**: `/home/shared/gellour5pt/scripts/streamdeck_pedal_watch.py`
- **Receivers**: `/home/shared/gellour5pt/scripts/receive_gello_*.py`
- **Test Publisher**: `/home/shared/gellour5pt/scripts/publish_test_gello.py`

## Benefits of Proper ZCM Types

✅ **zcm-spy compatibility**: Messages now display properly in the GUI
✅ **Cross-language support**: Can generate bindings for C++, Java, etc.
✅ **Type safety**: Automatic fingerprinting prevents version mismatches
✅ **Standard tools**: Works with zcm-logger, zcm-logplayer, etc.
✅ **Better debugging**: Field names and types visible in zcm-spy

---
*The ZCM messages are now fully compatible with all ZCM ecosystem tools.*
