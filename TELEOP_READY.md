# UR5 Teleoperation System - READY TO USE

## Quick Start

### 1. Start Teleoperation
```bash
cd /home/shared/gellour5pt
python3 scripts/run_teleop.py
```

Or use the quick start script:
```bash
cd /home/shared/gellour5pt
./scripts/start_teleop.sh
```

### 2. Test Mode (Without Pedals)
```bash
python3 scripts/run_teleop.py --test-mode
```

## Gripper Control

### Manual Gripper Commands

#### Using the convenience script:
```bash
# Open/close individual grippers
./scripts/gripper_commands.sh left open
./scripts/gripper_commands.sh left close
./scripts/gripper_commands.sh right open
./scripts/gripper_commands.sh right close

# Control both grippers
./scripts/gripper_commands.sh both open
./scripts/gripper_commands.sh both close
```

#### Direct commands:
```bash
# Close left gripper
python3 debug_tools/send_gripper_cmd.py -o gripper_command_left --position -0.075

# Open left gripper  
python3 debug_tools/send_gripper_cmd.py -o gripper_command_left --position 0.25

# Close right gripper
python3 debug_tools/send_gripper_cmd.py -o gripper_command_right --position -0.075

# Open right gripper
python3 debug_tools/send_gripper_cmd.py -o gripper_command_right --position 0.25
```

### Test Gripper System
```bash
python3 scripts/test_gripper_control.py
```

## Configuration

### Current Setup
- **GELLO DXL IDs**: 
  - Left arm: 1-6 (joints) + 7 (gripper)
  - Right arm: 10-15 (joints) + 16 (gripper)

- **Gripper Serial Ports**:
  - Right gripper: `/dev/ttyUSB1` (4500000 bps)
  - Left gripper: `/dev/ttyUSB3` (4500000 bps)

- **UR Robots**:
  - Left UR5: 192.168.1.211
  - Right UR5: 192.168.1.210

### Configuration File
Main config: `configs/teleop_dual_ur5.yaml`

## StreamDeck Pedal Controls

- **LEFT Pedal (Button 4)**: Interrupt - stops URs for external program control
- **CENTER Pedal (Button 5)**:
  - 1st tap: Capture baselines, gentle params, prep/align
  - 2nd tap: Start teleop streaming (full-speed)
- **RIGHT Pedal (Button 6)**: Stop teleop and return to passive

## Troubleshooting

### Check USB Ports
```bash
ls -la /dev/ttyUSB*
```

### Check GELLO DXL Ports
```bash
ls -la /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_*
```

### Test DXL Servos
```bash
python3 scripts/run_teleop.py --dxl-test
```

### Check UR Connections
```bash
python3 scripts/test_ur_connection.py
```

## System Status Checks

1. **Verify all components**:
   ```bash
   python3 scripts/verify_teleop_setup.py
   ```

2. **Check gripper status**:
   ```bash
   # Check if command files exist
   ls -la /tmp/gripper_command_*.json
   ```

3. **Monitor teleop logs**:
   - Watch console output during teleop for error messages
   - Gripper state changes are printed when detected

## Notes

- Gripper commands are sent via serial communication to USB ports
- The system automatically detects gripper state changes during teleop
- Gripper control is integrated into the main teleop loop
- JSON files are saved to `/tmp/` for monitoring/debugging

## Quick Commands Reference

```bash
# Start teleop
cd /home/shared/gellour5pt && python3 scripts/run_teleop.py

# Test mode (no pedals)
python3 scripts/run_teleop.py --test-mode

# Test grippers
python3 scripts/test_gripper_control.py

# Manual gripper control
./scripts/gripper_commands.sh both open
./scripts/gripper_commands.sh both close
```
