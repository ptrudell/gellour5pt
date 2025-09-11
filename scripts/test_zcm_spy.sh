#!/bin/bash
# Test script to verify zcm-spy compatibility with GELLO position messages

echo "================================"
echo "ZCM-SPY Compatibility Test"
echo "================================"
echo ""
echo "This script will:"
echo "1. Start a test publisher in the background"
echo "2. Launch zcm-spy to verify messages are visible"
echo "3. Clean up when done"
echo ""
echo "Press Ctrl+C to stop the test"
echo ""
echo "Starting test publisher..."

# Start publisher in background
python scripts/publish_test_gello.py --mode sine --rate 5 &
PUBLISHER_PID=$!

# Give it a moment to start
sleep 2

echo ""
echo "Publisher running (PID: $PUBLISHER_PID)"
echo ""
echo "Now launching zcm-spy..."
echo "You should see:"
echo "  - gello_positions_left channel"
echo "  - gello_positions_right channel"
echo "  - Message counts incrementing"
echo "  - Proper field decoding when you click on a message"
echo ""
echo "Close zcm-spy window when done viewing."
echo ""

# Launch zcm-spy
zcm-spy --zcm-types="/home/shared/gellour5pt/scripts" 2>/dev/null || {
    echo "Note: zcm-spy may not be installed or may need different args"
    echo "Try: zcm-spy"
    echo "  or: zcm-spy --print-all"
}

# Clean up
echo ""
echo "Cleaning up..."
kill $PUBLISHER_PID 2>/dev/null
wait $PUBLISHER_PID 2>/dev/null

echo "Test complete!"
