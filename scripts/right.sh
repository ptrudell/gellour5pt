#!/usr/bin/env bash
export PYTHONPATH=/home/shared/gello_software/gello_software:$PYTHONPATH
export ROBOT_IP=192.168.1.210
export GELLO_PORT=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0
export GELLO_BAUD=1000000
export GELLO_PROTOCOL=2.0
export GELLO_IDS=10,11,12,13,14,15,16
python3 "$(dirname "$0")/auto_gello_calibrate.py" configs/ur5_right_u2d2_xl330.yaml
