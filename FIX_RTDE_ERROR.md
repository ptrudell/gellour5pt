# Fix for "RTDE input registers already in use" Error

## Quick Fix Steps

### 1. Run the Automatic Fix Script
```bash
cd /home/shared/gellour5pt
./scripts/fix_teleop.sh
```

This script will:
- Kill existing processes
- Clear RTDE registers
- Load ExternalControl.urp
- Test connections

### 2. If Automatic Fix Fails - Manual Steps

#### On LEFT Robot (192.168.1.211):
1. **On the pendant:**
   - Press STOP button to stop any program
   - Tap Menu → File → Load Program
   - Navigate to `/programs/`
   - Select `ExternalControl.urp`
   - Press Load

2. **Configure External Control:**
   - Menu → Installation → URCaps → External Control
   - Set Host IP = **YOUR COMPUTER's IP** (NOT the robot's IP!)
   - Example: If your computer is 192.168.1.100, enter that
   - Press "Save Installation"

3. **Start the Program:**
   - Press the Play button (▶) on pendant
   - If prompted for Remote Control, enable it

#### On RIGHT Robot (192.168.1.210):
- Repeat the exact same steps as above

### 3. Verify Setup
```bash
# Test RTDE connections
python3 scripts/clear_ur_connections.py

# Should show:
# ✓ ExternalControl already running (for both robots)
```

### 4. Start Teleoperation
```bash
# Test mode (no pedals needed)
python3 scripts/run_teleop.py --test-mode

# Normal mode (with pedals)
python3 scripts/run_teleop.py
```

## Common Issues and Solutions

### Issue: "RTDE input registers already in use"
**Cause:** Previous connection wasn't closed properly or conflicting network adapter.

**Solution:**
```bash
# Fix RTDE registers
python3 scripts/fix_rtde_registers.py
```

### Issue: "ExternalControl not running"
**Cause:** Wrong program loaded on robot.

**Solution:**
- Load ExternalControl.urp manually (see steps above)
- Make sure to press Play after loading

### Issue: "Connection refused"
**Cause:** Robot network settings or firewall.

**Solution:**
1. Check robot is on same network
2. Ping robot: `ping 192.168.1.211`
3. Disable firewall temporarily for testing

### Issue: Programs Keep Getting Stopped
**Cause:** Multiple scripts trying to connect simultaneously.

**Solution:**
```bash
# Kill all Python processes
pkill -f python
# Wait a moment
sleep 2
# Try again
python3 scripts/run_teleop.py --test-mode
```

## Network Configuration

### Find Your Computer's IP:
```bash
# Linux/Mac
ip addr show | grep "inet 192.168"

# Or
hostname -I
```

### Robot Network Settings:
- LEFT Robot: 192.168.1.211
- RIGHT Robot: 192.168.1.210
- Your Computer: Must be on same subnet (192.168.1.x)

## Testing Checklist

1. **Check UR Dashboard Status:**
   ```bash
   # This will show current program state
   python3 scripts/clear_ur_connections.py
   ```

2. **Test RTDE Ports:**
   ```bash
   nc -zv 192.168.1.211 30004  # LEFT robot
   nc -zv 192.168.1.210 30004  # RIGHT robot
   ```

3. **Test DXL Servos:**
   ```bash
   python3 scripts/run_teleop.py --dxl-test
   ```

4. **Test Teleop Without Moving:**
   ```bash
   python3 scripts/run_teleop.py --test-mode --no-dashboard
   ```

## Emergency Stop

If robots start moving unexpectedly:
1. Press EMERGENCY STOP on pendant
2. Kill the script: `Ctrl+C`
3. Run: `pkill -f python`

## Still Having Issues?

1. **Restart Robots:**
   - Power cycle both UR robots
   - Wait 30 seconds
   - Run fix script again

2. **Check Logs:**
   ```bash
   # Watch for specific errors
   python3 scripts/run_teleop.py --test-mode 2>&1 | grep -E "Error|Failed|error"
   ```

3. **Minimal Test:**
   ```bash
   # Test just UR connections
   python3 test_scripts/test_ur_connection.py
   ```

## Success Indicators

When everything is working, you should see:
```
[config] Loaded from configs/teleop_dual_ur5.yaml
Building robot connections...
[left] UR: connected, DXL: connected
[right] UR: connected, DXL: connected
...
✅ Starting teleoperation!
```
