#!/usr/bin/env bash
export PYTHONPATH=/home/shared/gello_software/gello_software:$PYTHONPATH
export ROBOT_IP=192.168.1.211
export GELLO_PORT=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0
export GELLO_BAUD=1000000
export GELLO_PROTOCOL=2.0
export GELLO_IDS=1,2,3,4,5,6,7
python3 "$(dirname "$0")/auto_gello_calibrate.py" configs/ur5_left_u2d2_xl330.yaml
