# Teleoperation Startup Checklist

## Prerequisites

### 1. UR Robot Setup (BOTH robots)
- [ ] Power on both UR robots
- [ ] Clear any errors/safety stops on pendant
- [ ] Load ExternalControl.urp:
  - Program → Load Program → /programs/ExternalControl.urp
  - Press Play (▶) button
  - Should see "ExternalControl is running"
- [ ] Enable Remote Control
- [ ] Set Host IP to your PC's IP (NOT the robot's IP)

### 2. Hardware Connections
- [ ] GELLO arms powered (5V supply to Dynamixel servos)
- [ ] USB cables connected from PC to GELLO arms
- [ ] Network cables connected from PC to UR robots
- [ ] StreamDeck pedal connected (optional)

### 3. Software Check
Run: `python scripts/teleop_manager.py check`
- [ ] All Python packages installed
- [ ] USB devices detected
- [ ] Network connectivity to robots

## Running Teleoperation

### Option 1: With Pedals
```bash
python scripts/run_teleop.py
```
Pedal sequence:
1. Press CENTER once - capture baselines
2. Press CENTER again - start teleop
3. Press RIGHT - stop teleop

### Option 2: Without Pedals (Simple)
```bash
python scripts/simple_teleop.py
```
Starts immediately, Ctrl+C to stop

### Option 3: Test Mode (Auto-start)
```bash
python scripts/run_teleop.py --test-mode
```

## Troubleshooting

### "RTDE control script is not running!"
- ExternalControl.urp is not loaded/playing on the robot
- Check pendant for errors
- Reload and play ExternalControl.urp

### "Failed to connect to Dynamixel servos"
- Check servo power (5V, LEDs should be on)
- Run: `python scripts/run_teleop.py --dxl-test`
- Check USB connections

### Wrong USB ports
- List ports: `ls -la /dev/serial/by-id/`
- Update configs/teleop_dual_ur5.yaml with correct ports

### Network issues
- Ping robots: `ping 192.168.1.211` and `ping 192.168.1.210`
- Check network cables
- Verify PC and robots are on same network

## Current Configuration

From configs/teleop_dual_ur5.yaml:
- LEFT UR: 192.168.1.211
- RIGHT UR: 192.168.1.210
- Speed: VMAX=1.4 rad/s, AMAX=4.0 rad/s²
- Control rate: 125 Hz
