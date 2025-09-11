#!/bin/bash
#
# Quick start script for UR5 teleoperation with gripper control
#

echo "=========================================="
echo "UR5 TELEOP QUICK START"
echo "=========================================="

# Change to the gellour5pt directory
cd /home/shared/gellour5pt

# Check for USB ports
echo ""
echo "Checking USB ports..."
if [ -e /dev/ttyUSB1 ]; then
    echo "  ✓ Right gripper port (/dev/ttyUSB1) found"
else
    echo "  ✗ Right gripper port (/dev/ttyUSB1) NOT FOUND"
fi

if [ -e /dev/ttyUSB3 ]; then
    echo "  ✓ Left gripper port (/dev/ttyUSB3) found"
else
    echo "  ✗ Left gripper port (/dev/ttyUSB3) NOT FOUND"
fi

# Check for GELLO DXL ports
echo ""
echo "Checking GELLO DXL ports..."
ls -la /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_* 2>/dev/null || echo "  No FTDI converters found"

echo ""
echo "=========================================="
echo "Starting teleoperation..."
echo "=========================================="

# Run the main teleop script with config
python3 scripts/run_teleop.py --config configs/teleop_dual_ur5.yaml

echo ""
echo "Teleoperation ended."
