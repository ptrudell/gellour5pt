# UR Robot Connection Setup Guide

## Current Status
✅ **GELLO (DXL) servos:** Connected and working
- LEFT: IDs 1-7 (gripper is ID 7)
- RIGHT: IDs 10-16 (gripper is ID 16)

❌ **UR Robots:** Need ExternalControl.urp configuration

## Setup ExternalControl.urp on Each Robot

### For LEFT Robot (192.168.1.211):

1. **On the UR Pendant:**
   - Press the hamburger menu (☰)
   - Select "Program" → "Load Program"
   - If `ExternalControl.urp` exists, load it
   - If not, create a new program:

2. **Create New Program (if needed):**
   - Name it: `ExternalControl`
   - Add URCap node:
     - Click "Structure" tab
     - Click "URCaps" → "External Control"
     - Set **Host IP**: Your PC's IP (check with `hostname -I`)
     - Set **Port**: 50002
   - Save the program

3. **Run the Program:**
   - Press the Play button (▶)
   - Enable "Remote Control" if prompted

### For RIGHT Robot (192.168.1.210):
- Repeat the same steps as above

## Get Your PC's IP Address
```bash
hostname -I | cut -d' ' -f1
```

## Quick Test After Setup

### Test UR connections only:
```bash
python scripts/test_ur_connections.py
```

### Test full teleop (UR + GELLO):
```bash
python scripts/run_teleop.py
```

### Test GELLO-only (skip UR):
```bash
python scripts/run_teleop.py --quick --test-mode
```

## Alternative: Manual Control Script

If you can't create ExternalControl.urp, you can use freedrive mode:

### LEFT Robot:
```bash
# Load freedrive on LEFT
python -c "
import socket
s = socket.socket()
s.connect(('192.168.1.211', 29999))
s.send(b'load freedrive.urp\n')
print(s.recv(1024))
s.send(b'play\n')
print(s.recv(1024))
s.close()
"
```

### RIGHT Robot:
```bash
# Load freedrive on RIGHT
python -c "
import socket
s = socket.socket()
s.connect(('192.168.1.210', 29999))
s.send(b'load freedrive.urp\n')
print(s.recv(1024))
s.send(b'play\n')
print(s.recv(1024))
s.close()
"
```

## Working Without UR (GELLO-Only Mode)

If you need to work without UR robots for now:

```bash
# Quick mode - GELLO only, instant start
python scripts/run_teleop.py --quick --test-mode

# This will:
# - Skip UR connections entirely
# - Read GELLO positions only
# - Start in < 1 second
# - Auto-start without pedals
```

## Summary

Your GELLO is working perfectly! To get full teleop:
1. Set up ExternalControl.urp on both pendants
2. Set Host IP to your PC's IP
3. Play the program
4. Run: `python scripts/run_teleop.py`

Or use quick mode to work with GELLO only:
`python scripts/run_teleop.py --quick --test-mode`
