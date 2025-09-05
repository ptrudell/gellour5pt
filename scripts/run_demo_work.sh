#!/bin/bash
# Demonstration script for running streamdeck_pedal_watch_work.py
# This runs the optimized "work" version for testing/demo purposes

echo "================================================"
echo "RUNNING DEMO: streamdeck_pedal_watch_work.py"
echo "================================================"
echo ""
echo "This is the optimized 'work' version with:"
echo "  - Simplified RTDE connection (fast)"
echo "  - All pedal controls working"
echo "  - Test mode enabled (auto-starts without pedals)"
echo ""
echo "Using SAFE speeds: VMAX=0.05, AMAX=0.8"
echo "================================================"
echo ""

cd /home/shared/gellour5pt

# Run the work version directly
UR_VMAX=0.05 UR_AMAX=0.8 \
python scripts/streamdeck_pedal_watch_work.py \
  --ur-left 192.168.1.211 --ur-right 192.168.1.210 \
  --left-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0 \
  --right-port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0 \
  --baud 1000000 \
  --joints-passive \
  --no-dashboard \
  --test-mode
