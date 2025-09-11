#!/usr/bin/env python3
import time
import zerocm
from robot_data_t import robot_data_t

zcm = zerocm.ZCM()
if not zcm.good():
    print("ZCM init failed")
    exit(1)

zcm.start()

# Create and populate message
msg = robot_data_t()
msg.timestamp = int(time.time() * 1e6)
msg.robot_id = "UR5_LEFT"
msg.joint_angles = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
msg.temperature = 25.5
msg.is_moving = True

# Publish
zcm.publish("robot_data", msg)
print(f"Published robot_data: {msg.robot_id} @ {msg.temperature}°C")

time.sleep(0.1)
zcm.stop()
