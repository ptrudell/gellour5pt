#!/bin/bash
#
# Master fix script for UR5 teleoperation issues
# This script fixes RTDE register conflicts and prepares robots for teleop
#

echo "=========================================="
echo "UR5 TELEOPERATION FIX UTILITY"
echo "=========================================="

# Change to gellour5pt directory
cd /home/shared/gellour5pt

# Step 1: Kill any existing processes
echo ""
echo "Step 1: Killing existing processes..."
pkill -f "python.*run_teleop" 2>/dev/null
pkill -f "python.*streamdeck" 2>/dev/null
pkill -f "python.*test_ur" 2>/dev/null

# Kill any stopped jobs
for job in $(jobs -p); do
    kill $job 2>/dev/null
done

echo "  ✓ Cleared existing processes"
sleep 1

# Step 2: Run RTDE register fix
echo ""
echo "Step 2: Fixing RTDE registers..."
python3 scripts/fix_rtde_registers.py

# Check exit code
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  RTDE fix incomplete. Manual setup may be required."
    echo ""
    echo "MANUAL STEPS:"
    echo "1. On LEFT robot pendant (192.168.1.211):"
    echo "   - Stop any running program"
    echo "   - File → Load Program → ExternalControl.urp"
    echo "   - Installation → URCaps → External Control"
    echo "   - Set Host IP = YOUR COMPUTER's IP"
    echo "   - Save installation"
    echo "   - Press Play (▶)"
    echo ""
    echo "2. On RIGHT robot pendant (192.168.1.210):"
    echo "   - Repeat the same steps"
    echo ""
    echo "3. After manual setup, run:"
    echo "   python3 scripts/run_teleop.py --test-mode"
    exit 1
fi

# Step 3: Quick connectivity test
echo ""
echo "Step 3: Testing connections..."
echo ""

# Test left robot
echo -n "LEFT robot (192.168.1.211): "
timeout 1 bash -c "echo '' | nc 192.168.1.211 30004" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ RTDE port open"
else
    echo "✗ RTDE port not responding"
fi

# Test right robot
echo -n "RIGHT robot (192.168.1.210): "
timeout 1 bash -c "echo '' | nc 192.168.1.210 30004" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ RTDE port open"
else
    echo "✗ RTDE port not responding"
fi

# Step 4: Check DXL ports
echo ""
echo "Step 4: Checking Dynamixel ports..."
if [ -e "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0" ]; then
    echo "  ✓ LEFT DXL port found"
else
    echo "  ✗ LEFT DXL port not found"
fi

if [ -e "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0" ]; then
    echo "  ✓ RIGHT DXL port found"
else
    echo "  ✗ RIGHT DXL port not found"
fi

echo ""
echo "=========================================="
echo "✅ FIX COMPLETE - READY TO TEST"
echo "=========================================="
echo ""
echo "Now run teleoperation with:"
echo "  python3 scripts/run_teleop.py --test-mode"
echo ""
echo "Or with pedals:"
echo "  python3 scripts/run_teleop.py"
echo ""
