#!/bin/bash
# Test script for the fixed streamdeck_pedal_watch.py
# This version has optimized RTDE connection without URScript fallback

echo "================================================"
echo "TESTING FIXED TELEOP (streamdeck_pedal_watch.py)"
echo "================================================"
echo ""
echo "This version includes:"
echo "  - Fixed RTDE connection (no URScript conflicts)"
echo "  - All performance optimizations from original"
echo "  - Bulk DXL reads with caching"
echo "  - Connection clearing utility"
echo "  - Full pedal support"
echo ""
echo "Using very slow speeds for safety (VMAX=0.05, AMAX=0.8)"
echo "Test mode will auto-start after 5 seconds if no pedals"
echo ""
echo "Press Ctrl+C to stop at any time"
echo "================================================"
echo ""

# Change to the gellour5pt directory
cd /home/shared/gellour5pt

# Run the fixed version directly
UR_VMAX=0.05 UR_AMAX=0.8 \
python scripts/streamdeck_pedal_watch.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 \
  --joints-passive \
  --no-dashboard \
  --test-mode
