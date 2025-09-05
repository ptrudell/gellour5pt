#!/bin/bash
# Quick test script for optimized teleop
# Run this to verify the optimized version works

echo "================================================"
echo "TESTING OPTIMIZED TELEOP"
echo "================================================"
echo ""
echo "This will run the optimized teleop with:"
echo "  - Very slow speeds for safety (VMAX=0.05, AMAX=0.8)"
echo "  - Test mode (auto-starts without pedals after 3 seconds)"
echo "  - No dashboard control"
echo ""
echo "Press Ctrl+C to stop at any time"
echo "================================================"
echo ""

# Change to the gellour5pt directory
cd /home/shared/gellour5pt

# Run with test parameters
UR_VMAX=0.05 UR_AMAX=0.8 \
python scripts/streamdeck_pedal_watch_work.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 \
  --joints-passive \
  --no-dashboard \
  --test-mode
