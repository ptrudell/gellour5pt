# ZCM Position Publishing - Working Guide

## ✅ Confirmed Working

The ZCM position publishing from `streamdeck_pedal_watch.py` is now working! When robots aren't connected, it publishes simulated data for testing.

## Quick Test

### 1. Start the Teleop Script (publishes positions)
```bash
python scripts/streamdeck_pedal_watch.py --test-mode --no-dashboard
```
This will:
- Start the PositionMonitor in the background
- Publish simulated GELLO positions at 10Hz
- Show position updates in the console

### 2. In Another Terminal, Receive the Messages
```bash
# View both arms side-by-side
python scripts/receive_gello_both.py

# Or compact mode
python scripts/receive_gello_both.py --mode compact

# Or just left arm
python scripts/receive_gello_left_v2.py

# Or just right arm  
python scripts/receive_gello_right_v2.py
```

## What You'll See

### Publisher Console (streamdeck_pedal_watch.py):
```
[MONITOR] Using SIMULATED positions for ZCM (no robots connected)
[ZCM DEBUG] Mode=SIMULATED, publish_zcm=True, zcm=True, left_pos=True, right_pos=True
[ZCM] Publishing SIMULATED data: left=True, right=True
[09:34:42] GELLO LEFT:  J1: -45.0° J2: -87.1° J3: 0.0° ...
           GELLO RIGHT: J1: -45.3° J2: -87.0° J3: 0.1° ...
```

### Receiver Console (receive_gello_both.py):
```
[L ✓] J1: -45.0° J2: -87.1° J3: 0.0° J4: -87.1° J5: 90.0° J6: 1.1° G: 28.6° (10.0Hz)
[R ✓] J1: -45.3° J2: -87.0° J3: 0.1° J4: -87.0° J5: 90.1° J6: 1.0° G: 34.4° (10.0Hz)
```

## With Real Robots

When real robots are connected:
1. The PositionMonitor will automatically switch from SIMULATED to REAL data
2. It will publish actual GELLO arm positions from the Dynamixel servos
3. The same receiver scripts will show the real positions

## Debugging

If messages aren't being received:

### 1. Test ZCM is Working
```bash
# Simple loopback test
python scripts/test_zcm_loopback.py
```
Should show: "✅ SUCCESS! Received 3 messages"

### 2. Test Publishing Only
```bash
# Publish test messages
python scripts/test_zcm_publishing.py
```
Then in another terminal, run a receiver.

### 3. Test PositionMonitor Directly
```bash
# Test the monitor class in isolation
python scripts/test_position_monitor_zcm.py
```

## ZCM Channels

The system uses these ZCM channels:
- `gello_positions_left` - Left GELLO arm positions
- `gello_positions_right` - Right GELLO arm positions

## Message Format

Each `gello_positions_t` message contains:
- `timestamp` - Microseconds since epoch
- `arm_side` - "left" or "right"
- `joint_positions[6]` - Joint angles in radians
- `gripper_position` - Gripper angle in radians
- `joint_velocities[6]` - Joint velocities (currently zeros)
- `is_valid` - Data validity flag

## Integration with Other Tools

The ZCM messages can be used by:
- Logging/recording scripts
- Visualization tools
- Remote monitoring
- Synchronization between multiple systems

## Troubleshooting

### No Messages Received
- Check ZCM is installed: `pip install zerocm`
- Verify `gello_positions_t.py` exists in scripts/
- Regenerate if needed: `cd scripts && zcm-gen -p gello_positions_simple.zcm`

### Messages Not Updating
- Check robots are connected (for real data)
- Verify the PositionMonitor thread is running
- Look for error messages in console output

### Wrong Values
- Simulated data uses sine waves for testing
- Real data comes from Dynamixel servo positions
- Check robot connections and calibration
