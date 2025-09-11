# Manual Setup Guide - Step by Step

## Current Situation
The robots were power cycled successfully, but ExternalControl.urp doesn't exist on either robot.
You need to create this program on each pendant.

## Step-by-Step Instructions

### For BOTH Robots (192.168.1.211 and 192.168.1.210):

#### Step 1: Create ExternalControl Program
1. **On the UR Pendant:**
   - Press the **☰ Menu** button
   - Select **Program** → **Empty Program**
   - Name it: `ExternalControl`

#### Step 2: Add External Control URCap
1. In the program tree (left side):
   - Click **+** (Add node)
   - Select **URCaps** → **External Control**
   - If you don't see it, the URCap might not be installed

#### Step 3: Configure External Control
1. Click on the **External Control** node you just added
2. Set these parameters:
   - **Host IP**: Your PC's IP address (find it with: `hostname -I`)
   - **Port**: `50002`
   - **Enable**: Check this box

#### Step 4: Save the Program
1. Press **Save** button
2. Save as: `ExternalControl.urp`

#### Step 5: Configure Installation
1. Go to **Installation** tab (top of screen)
2. Select **URCaps** → **External Control**
3. Verify settings:
   - **Host IP**: Your PC's IP (NOT the robot's IP!)
   - **Port**: `50002`
4. Press **Save Installation**

#### Step 6: Run the Program
1. Go back to **Program** tab
2. Make sure `ExternalControl.urp` is loaded
3. Press the **▶ Play** button at bottom

## Finding Your PC's IP Address

Run this command to find your PC's IP:
```bash
hostname -I | awk '{print $1}'
```

Your PC's IP is probably something like:
- 192.168.1.xxx (on same network as robots)

## Quick Test After Setup

Once both robots have ExternalControl.urp running:

```bash
# Test the connection
cd /home/shared/gellour5pt
python -c "
from rtde_control import RTDEControlInterface
try:
    rtde = RTDEControlInterface('192.168.1.211')
    print('✅ LEFT robot connected!')
    rtde.disconnect()
except Exception as e:
    print(f'❌ LEFT robot failed: {e}')
    
try:
    rtde = RTDEControlInterface('192.168.1.210')
    print('✅ RIGHT robot connected!')
    rtde.disconnect()
except Exception as e:
    print(f'❌ RIGHT robot failed: {e}')
"
```

## If URCap is Not Installed

If you don't see "External Control" in URCaps:

1. Download the URCap from:
   - https://github.com/UniversalRobots/Universal_Robots_ROS_Driver
   - Look for `externalcontrol-1.0.5.urcap` in releases

2. Install on pendant:
   - Copy .urcap file to USB drive
   - On pendant: Settings → System → URCaps
   - Click **+** → Select the .urcap file
   - Restart robot

## After Everything is Set Up

Run the teleop:
```bash
python scripts/run_teleop.py
```

You should see:
- `[left] UR: connected, DXL: connected`
- `[right] UR: connected, DXL: connected`

## Troubleshooting

### "RTDE registers already in use"
- Make sure no other programs are using RTDE
- Disable MODBUS in Installation → Fieldbus
- Disable EtherNet/IP if enabled

### "Connection refused"
- Check firewall on your PC
- Verify robots and PC are on same network
- Ping test: `ping 192.168.1.211` and `ping 192.168.1.210`

### "Wrong host IP"
- The Host IP should be YOUR COMPUTER's IP
- NOT the robot's IP!
- Common mistake: putting 192.168.1.211 as host IP for the left robot
