#!/usr/bin/env python3
import time, math, signal, sys
import sys
sys.path.append('/home/shared/gellour5pt/scripts')
from rtde_shim import RTDEControlInterface, RTDEReceiveInterface

LEFT_IP  = "192.168.1.211"
RIGHT_IP = "192.168.1.210"

# servoJ params
SERVO_DT      = 0.008     # 125 Hz
SERVO_LOOKAHD = 0.1
SERVO_GAIN    = 600
SPEED_LIMIT   = 0.5       # max rad/s per joint
LPF_ALPHA     = 0.2       # low-pass filter

def clamp(v, lo, hi): return max(lo, min(hi, v))

def main():
    rr = RTDEReceiveInterface(LEFT_IP)
    rc = RTDEControlInterface(RIGHT_IP)

    q_cmd = rr.getActualQ()[:]  # init
    print("[teleop ur→ur] running. Ctrl-C to stop.")
    def stop(_1=None,_2=None):
        try: rc.stopScript()
        except: pass
        sys.exit(0)
    signal.signal(signal.SIGINT, stop)

    last = time.time()
    while True:
        t0 = time.time()
        q = rr.getActualQ()  # 6
        # rate-limit & filter
        dt = max(1e-3, t0 - last)
        q_limited = []
        for i in range(6):
            max_step = SPEED_LIMIT * dt
            step = clamp(q[i] - q_cmd[i], -max_step, +max_step)
            raw = q_cmd[i] + step
            filt = LPF_ALPHA*raw + (1-LPF_ALPHA)*q_cmd[i]
            q_limited.append(filt)
        q_cmd = q_limited

        rc.servoJ(q_cmd,  # q
                  [0]*6,  # a (ignored here)
                  SERVO_DT,
                  SERVO_LOOKAHD,
                  SERVO_GAIN)

        last = t0
        # keep near 125 Hz
        sleep_t = SERVO_DT - (time.time() - t0)
        if sleep_t > 0: time.sleep(sleep_t)

if __name__ == "__main__":
    main()
