#!/bin/bash
# Quick teleop demo launcher for streamdeck_pedal_watch_work.py
# Usage: ./teleop_demo.sh [safe|normal|fast|pedals]

cd /home/shared/gellour5pt

# Common parameters
LEFT_UR="192.168.1.211"
RIGHT_UR="192.168.1.210"
LEFT_PORT="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0"
RIGHT_PORT="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0"
SCRIPT="scripts/streamdeck_pedal_watch_work.py"

case "${1:-safe}" in
    safe)
        echo "🛡️ Running SAFE mode (very slow, test mode enabled)"
        UR_VMAX=0.05 UR_AMAX=0.8 \
        python $SCRIPT \
            --ur-left $LEFT_UR --ur-right $RIGHT_UR \
            --left-port "$LEFT_PORT" --right-port "$RIGHT_PORT" \
            --baud 1000000 --joints-passive --no-dashboard --test-mode
        ;;
    
    normal)
        echo "🚀 Running NORMAL mode (moderate speed, test mode enabled)"
        UR_VMAX=0.7 UR_AMAX=2.0 \
        python $SCRIPT \
            --ur-left $LEFT_UR --ur-right $RIGHT_UR \
            --left-port "$LEFT_PORT" --right-port "$RIGHT_PORT" \
            --baud 1000000 --joints-passive --no-dashboard --test-mode
        ;;
    
    fast)
        echo "⚡ Running FAST mode (full speed, test mode enabled)"
        UR_VMAX=1.4 UR_AMAX=4.0 \
        python $SCRIPT \
            --ur-left $LEFT_UR --ur-right $RIGHT_UR \
            --left-port "$LEFT_PORT" --right-port "$RIGHT_PORT" \
            --baud 1000000 --joints-passive --no-dashboard --test-mode
        ;;
    
    pedals)
        echo "🎮 Running with PEDALS (safe speed, no test mode)"
        UR_VMAX=0.5 UR_AMAX=1.5 \
        python $SCRIPT \
            --ur-left $LEFT_UR --ur-right $RIGHT_UR \
            --left-port "$LEFT_PORT" --right-port "$RIGHT_PORT" \
            --baud 1000000 --joints-passive --no-dashboard
        ;;
    
    *)
        echo "Usage: $0 [safe|normal|fast|pedals]"
        echo ""
        echo "Options:"
        echo "  safe   - Very slow speeds, auto-start (default)"
        echo "  normal - Moderate speeds, auto-start"
        echo "  fast   - Full speeds, auto-start"
        echo "  pedals - Safe speeds, requires pedals"
        exit 1
        ;;
esac
