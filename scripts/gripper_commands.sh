#!/bin/bash
#
# Quick gripper control commands for testing
# Usage: ./gripper_commands.sh [left|right] [open|close]
#

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
GRIPPER_CMD="$SCRIPT_DIR/../debug_tools/send_gripper_cmd.py"

case "$1" in
    left)
        SIDE="left"
        ;;
    right)
        SIDE="right"
        ;;
    both)
        # Handle both grippers
        case "$2" in
            open)
                echo "Opening both grippers..."
                python3 "$GRIPPER_CMD" -o gripper_command_left --position 0.25
                python3 "$GRIPPER_CMD" -o gripper_command_right --position 0.25
                ;;
            close)
                echo "Closing both grippers..."
                python3 "$GRIPPER_CMD" -o gripper_command_left --position -0.075
                python3 "$GRIPPER_CMD" -o gripper_command_right --position -0.075
                ;;
            *)
                echo "Usage: $0 both [open|close]"
                exit 1
                ;;
        esac
        exit 0
        ;;
    *)
        echo "Usage: $0 [left|right|both] [open|close]"
        echo ""
        echo "Examples:"
        echo "  $0 left open    # Open left gripper"
        echo "  $0 right close  # Close right gripper"
        echo "  $0 both open    # Open both grippers"
        exit 1
        ;;
esac

case "$2" in
    open)
        POSITION="0.25"
        ACTION="Opening"
        ;;
    close)
        POSITION="-0.075"
        ACTION="Closing"
        ;;
    *)
        echo "Usage: $0 [left|right|both] [open|close]"
        exit 1
        ;;
esac

echo "$ACTION $SIDE gripper..."
python3 "$GRIPPER_CMD" -o "gripper_command_$SIDE" --position "$POSITION"
