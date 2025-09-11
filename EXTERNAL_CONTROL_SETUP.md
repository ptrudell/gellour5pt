# Complete ExternalControl Setup Guide for UR5 Robots

## Quick Summary

Your system has:
- **GELLO grippers**: ID 7 (left), ID 16 (right) - for reading input positions
- **UR5 grippers**: Controlled via UR tool digital outputs (NOT via USB ports)
  - Note: /dev/ttyUSB1 and /dev/ttyUSB3 have no servos connected

## Step-by-Step Setup for ExternalControl.urp

### On EACH UR5 Robot Pendant (LEFT: 192.168.1.211, RIGHT: 192.168.1.210):

### Step 1: Install URCaps (if not already installed)

**Check if already installed:**
1. Press **hamburger menu (☰)** → **Settings**
2. Go to **System** → **URCaps**
3. Look for **External Control URCap** in the list

**If NOT installed:**
1. Download the URCap file:
   - Go to: https://github.com/UniversalRobots/Universal_Robots_ROS_Driver/releases
   - Download `externalcontrol-1.0.5.urcap` (or latest version)
   - Save to a USB stick

2. Install on the pendant:
   - Insert USB stick into UR controller
   - Go to **Settings** → **System** → **URCaps**
   - Click **+** button
   - Browse to USB and select the `.urcap` file
   - Click **Install**
   - Restart the robot controller when prompted

### Step 2: Create ExternalControl Program

1. **Press hamburger menu (☰)**
2. Select **Program** → **Empty Program**
3. **Name it**: `ExternalControl` (exactly this name)
4. Press **OK**

### Step 3: Add External Control Node

1. In the **Program Tree** on the left:
   - Click on **Robot Program**
   - Click **Structure** tab at bottom
   - Click **URCaps** → **External Control**

2. **Configure the External Control node:**
   ```
   Host IP: 192.168.1.8    ← YOUR PC's IP (not robot's IP!)
   Port: 50002
   ```
   
   **IMPORTANT**: The Host IP must be YOUR COMPUTER's IP address, not the robot's IP!

3. **Save the program:**
   - Click **File** → **Save Program**
   - Confirm name: `ExternalControl`

### Step 4: Run the Program

1. Make sure robot is in **Remote Control** mode:
   - Top right corner should show **Remote Control** enabled
   - If not, enable it in settings

2. **Press the Play button (▶)**
   - The program should start and show "Program Running"
   - You should see "External Control: Ready" or similar

### Step 5: Verify Your PC's IP Address

On your Linux PC, run:
```bash
hostname -I | cut -d' ' -f1
```

This should show: `192.168.1.8`

If it's different, update the Host IP in ExternalControl.urp on both pendants.

### Step 6: Verify Setup on Each Robot

After setting up ExternalControl.urp on each pendant:

1. **Check Program Status:**
   - Should show "Program Running" at top
   - External Control node should show "Ready"

2. **Check Remote Control:**
   - Top right should show "Remote Control: ON"
   - If not, go to Settings → Remote Control → Enable

3. **Test Connection from PC:**
   ```bash
   # Test LEFT robot
   ping 192.168.1.211
   
   # Test RIGHT robot  
   ping 192.168.1.210
   ```
   Both should respond to ping.

## Testing the Connection

### Test 1: Check UR connections only
```bash
python scripts/test_ur_connections.py
```

Expected output:
```
Testing 192.168.1.211...
  ✅ Control interface connected
  ✅ Receive interface connected  
  ✅ Robot responding (6 joints detected)

Testing 192.168.1.210...
  ✅ Control interface connected
  ✅ Receive interface connected
  ✅ Robot responding (6 joints detected)
```

### Test 2: Test GELLO + UR5 Grippers
```bash
python scripts/test_gello_simple.py
```

This shows GELLO positions including grippers (ID 7 and 16).

### Test 3: Full Teleop Test
```bash
# With pedals:
python scripts/run_teleop.py

# Without pedals (auto-start):
python scripts/run_teleop.py --test-mode
```

## Troubleshooting

### Connection Issues

**"RTDE registers already in use" error:**
```bash
python scripts/fix_rtde_registers.py
```
Then reload ExternalControl.urp on the pendant.

**"ur_rtde: Failed to start control script" spam:**
- This means ExternalControl.urp is not playing
- Go to pendant and press Play (▶) button
- Make sure program shows "Running"

**Connection fails completely:**
1. Check robot is powered on and brake released
2. Verify ExternalControl.urp is PLAYING (not just loaded)
3. Confirm Host IP is YOUR PC's IP (192.168.1.8)
4. Check network connectivity: `ping 192.168.1.211`
5. Try manual connection test:
   ```bash
   python scripts/test_ur_connections.py
   ```

### Teleop Issues

**GELLO not responding:**
- Check servo power is on
- Run: `python scripts/test_gello_simple.py`
- Should show positions for IDs 1-7 (left) and 10-16 (right)

**Grippers not working:**
- Grippers are controlled via tool digital outputs
- Check that ExternalControl.urp is running
- Monitor gripper debug files: `tail -f /tmp/gripper_command_*.json`

**Robot jittery or drifting:**
- This has been fixed in the code
- If still occurring, check GELLO servo connections
- Verify no external forces on GELLO arms

### Common Mistakes

❌ **Wrong**: Setting Host IP to robot's IP (192.168.1.211)
✅ **Right**: Setting Host IP to PC's IP (192.168.1.8)

❌ **Wrong**: Program loaded but not playing
✅ **Right**: Press Play button, program shows "Running"

❌ **Wrong**: Remote control disabled
✅ **Right**: Enable remote control in settings

❌ **Wrong**: Looking for gripper servos on USB ports
✅ **Right**: Grippers controlled via UR tool outputs

## System Architecture

```
GELLO Arms (Input)              UR5 Robots (Output)
------------------              -------------------
Left Joints (IDs 1-6)      →    Left Robot (192.168.1.211)
Left Gripper (ID 7)        →    Left Gripper (Tool Digital Outputs)

Right Joints (IDs 10-15)   →    Right Robot (192.168.1.210)  
Right Gripper (ID 16)      →    Right Gripper (Tool Digital Outputs)
```

**Gripper Control Method:**
- GELLO grippers (ID 7 & 16) are read for position input
- UR5 grippers are controlled via tool digital outputs (pins 0 & 1)
- URScript commands are sent to control gripper open/close

## Quick Commands Reference

```bash
# Test everything step by step:
python scripts/test_gello_simple.py                # Test GELLO reading (should work now)
python scripts/test_ur_connections.py              # Test UR connections (after setup)

# Run full teleop:
python scripts/run_teleop.py --test-mode           # Auto-start for testing
python scripts/run_teleop.py                       # Normal with pedals

# Quick diagnostics:
python scripts/dxl_scan.py /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 1000000  # Left GELLO
python scripts/dxl_scan.py /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 1000000  # Right GELLO
```

## Final Checklist

- [ ] ExternalControl.urp created on LEFT pendant (192.168.1.211)
- [ ] ExternalControl.urp created on RIGHT pendant (192.168.1.210)
- [ ] Host IP set to 192.168.1.8 (your PC) on both
- [ ] Port set to 50002 on both
- [ ] Both programs PLAYING (not just loaded)
- [ ] Remote control enabled on both robots
- [ ] GELLO arms powered and connected
- [ ] UR5 robots powered on with brakes released

When all items are checked, run:
```bash
python scripts/run_teleop.py --test-mode
```

## What to Expect When Everything Works

When properly configured, you should see:

1. **GELLO Connection**: ✅ Both arms detected (IDs 1-7 and 10-16)
2. **UR Connection**: ✅ Both robots connected via RTDE
3. **Motion Control**: 
   - GELLO arm movements → UR5 arm movements (1:1 mapping)
   - No jitter when stationary
   - Instant response to movement
4. **Gripper Control**:
   - GELLO gripper (ID 7) squeeze → LEFT UR5 gripper closes
   - GELLO gripper (ID 16) squeeze → RIGHT UR5 gripper closes
   - Gripper commands sent via tool digital outputs

## Important Notes

- **Gripper Control**: UR5 grippers are controlled through tool digital outputs, NOT through the USB ports
- **Motion Damping**: System includes smart damping to prevent jitter
- **Safety**: Wrist joints are clamped, deadbands are active
- **Speed**: Normal mode runs at VMAX=1.4 rad/s, AMAX=4.0 rad/s²

The system should start immediately and you can control both UR5 robots with smooth, responsive motion!
