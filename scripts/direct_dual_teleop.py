#!/usr/bin/env python3
# gello/scripts/direct_dual_teleop.py
"""
Dual-arm teleop (pedal-friendly, gentle, with gripper control).

Safeties & niceties
- Auto-arm with countdown (--auto-arm / --arm-delay)
- Caps from env: UR_VMAX (rad/s), UR_AMAX (rad/s^2)
- Smooth profile: low-pass filter + per-tick slew limit + fade-in
- Conservative joint excursion limit from base pose
- Robust to transient read/RTDE hiccups (won't crash)
- Optional gripper control using ID7 / ID16 deltas -> UR digital outputs

Env knobs (optional)
- TELEOP_KP                (default 0.6)
- TELEOP_DEADBAND_DEG      (default 1.2)
- TELEOP_LPF_BETA          (default 0.20)
- TELEOP_MAX_STEP_RAD      (default 0.004)
- TELEOP_FADE_S            (default 3.0)
- LEFT_GRIP_DO, RIGHT_GRIP_DO  (digital output indices)
- GRIP_OPEN_RAD, GRIP_CLOSE_RAD, GRIP_HYST_RAD (defaults: 0.10, 0.10, 0.03)
"""

import os, sys, time, math, signal, argparse, pathlib, importlib.util

# ---------------- signal handling ----------------
SHOULD_RUN = True
def _handle_sig(_sig, _frm):
    global SHOULD_RUN
    SHOULD_RUN = False
signal.signal(signal.SIGINT, _handle_sig)
signal.signal(signal.SIGTERM, _handle_sig)

# ---------------- UR RTDE imports ----------------
try:
    from rtde_shim import RTDEControlInterface, RTDEReceiveInterface
except Exception:
    import rtde_control  # type: ignore
    import rtde_receive  # type: ignore

# ---------------- Dynamixel imports ----------------
try:
    from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
    HAVE_DXL = True
except Exception:
    HAVE_DXL = False
    PortHandler = PacketHandler = object  # type: ignore
    COMM_SUCCESS = 0

# ---------------- config ----------------
HERE = pathlib.Path(__file__).resolve().parent
GELLO = HERE.parent
CFG_PATH = (GELLO / "configs" / "gello_dual_ur5_local.py").resolve()

_spec = importlib.util.spec_from_file_location("gello_dual_cfg", CFG_PATH)
if not _spec or not _spec.loader:
    print(f"❌ could not load config at {CFG_PATH}")
    sys.exit(1)
cfg = importlib.util.module_from_spec(_spec)  # type: ignore
_spec.loader.exec_module(cfg)                 # type: ignore

UR_LEFT_IP  = getattr(cfg, "UR5_LEFT_IP")
UR_RIGHT_IP = getattr(cfg, "UR5_RIGHT_IP")

# Optional serial paths (prefer /dev/serial/by-id/…)
DXL_LEFT_PORT  = getattr(cfg, "DXL_LEFT_PORT",  None)
DXL_RIGHT_PORT = getattr(cfg, "DXL_RIGHT_PORT", None)

# Handheld joint IDs (first 6 map to UR joints; ID7/16 used for “grip axis”)
LEFT_IDS  = [1,2,3,4,5,6,7]
RIGHT_IDS = [10,11,12,13,14,15,16]

# X-series present position register
PRESENT_POS_ADDR = 132   # 4 bytes, little-endian (unsigned)
TICKS2RAD = 0.088 * math.pi / 180.0  # 0.088 deg/tick

# Per-joint sign & scale (tune if axes feel inverted or too sensitive)
SIGN_L  = [+1, +1, +1, +1, +1, +1]
SIGN_R  = [+1, +1, +1, +1, +1, +1]
SCALE_L = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
SCALE_R = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

# ---------------- helpers ----------------
def clamp_vec(v, lim):
    lim = float(lim)
    return [max(-lim, min(lim, float(x))) for x in v]

def add_vec(a, b):
    return [float(x)+float(y) for x,y in zip(a,b)]

def lpf(prev, target, beta):
    b = max(0.0, min(1.0, float(beta)))
    return [float(prev[i]) + b * (float(target[i]) - float(prev[i])) for i in range(len(prev))]

def slew_limit(prev, target, max_step):
    out, ms = [], abs(float(max_step))
    for i, t in enumerate(target):
        d = float(t) - float(prev[i])
        if d > ms:  d = ms
        if d < -ms: d = -ms
        out.append(float(prev[i]) + d)
    return out

def signed_delta(curr_u32, zero_u32):
    """
    Convert difference of two unsigned 32-bit positions into a signed tick delta (wrap-aware),
    then return that delta as *ticks* (not radians).
    """
    d = (int(curr_u32) - int(zero_u32)) & 0xFFFFFFFF
    if d & (1 << 31):  # negative in 2's complement
        d = d - (1 << 32)
    return float(d)

class UR:
    def __init__(self, ip):
        self.ip = ip
        self.rc = None
        self.rr = None
    def connect(self):
        self.rc = rtde_control.RTDEControlInterface(self.ip)
        self.rr = rtde_receive.RTDEReceiveInterface(self.ip)
    def q(self):
        return self.rr.getActualQ() if self.rr else None
    def servoJ(self, q, speed, accel, dt, lookahead=0.12, gain=200.0):
        # positional args per RTDEControlInterface signature
        self.rc.servoJ(list(map(float, q)), float(speed), float(accel), float(dt), float(lookahead), float(gain))
    def set_do(self, pin, value):
        try:
            self.rc.setStandardDigitalOut(int(pin), bool(value))
        except Exception:
            pass
    def stop(self):
        try:
            if self.rc:
                try: self.rc.stopScript()
                except Exception: pass
        finally:
            try:
                if self.rr: self.rr.disconnect()
            except Exception: pass
            try:
                if self.rc: self.rc.disconnect()
            except Exception: pass
            self.rc = None; self.rr = None

class DxlBus:
    def __init__(self, port, baud=1_000_000, proto=2.0):
        self.port = port; self.baud = baud; self.proto = proto
        self.ph = None
        self.pk = None
    def open(self):
        if not HAVE_DXL:
            print("[dxl] skipped (dynamixel_sdk not installed)"); return False
        self.ph = PortHandler(self.port)
        if not self.ph.openPort():
            print(f"[dxl] open FAIL: {self.port}"); self.ph = None; return False
        self.ph.setBaudRate(self.baud)
        self.pk = PacketHandler(self.proto)
        print(f"[dxl] open OK: {self.port} @ {self.baud}")
        return True
    def close(self):
        try:
            if self.ph: self.ph.closePort()
        except Exception: pass
        self.ph = None; self.pk = None
    def read_positions(self, ids):
        if not self.ph or not self.pk: return None
        out = []
        for _id in ids:
            val, comm, err = self.pk.read4ByteTxRx(self.ph, _id, PRESENT_POS_ADDR)
            if comm != COMM_SUCCESS or err != 0:
                return None
            out.append(val & 0xFFFFFFFF)
        return out

def _cleanup(urL, urR, buses):
    try: urL.stop()
    except Exception: pass
    try: urR.stop()
    except Exception: pass
    for b in buses:
        try: b.close()
        except Exception: pass
    print("[teleop] shutdown complete.")

# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto-arm", action="store_true", help="Skip ENTER prompt and arm after countdown")
    ap.add_argument("--arm-delay", type=float, default=3.0, help="Countdown seconds before auto-arm")
    ap.add_argument("--hz", type=float, default=125.0)
    ap.add_argument("--kp", type=float, default=float(os.environ.get("TELEOP_KP", "0.6")))
    ap.add_argument("--vmax", type=float, default=0.2)
    ap.add_argument("--amax", type=float, default=0.8)
    ap.add_argument("--deadband-deg", type=float, default=float(os.environ.get("TELEOP_DEADBAND_DEG", "1.2")))
    ap.add_argument("--lpf-beta", type=float, default=float(os.environ.get("TELEOP_LPF_BETA", "0.20")))
    ap.add_argument("--max-step", type=float, default=float(os.environ.get("TELEOP_MAX_STEP_RAD", "0.004")))
    ap.add_argument("--fade-s", type=float, default=float(os.environ.get("TELEOP_FADE_S", "3.0")))
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    # env caps
    VCAP = float(os.environ.get("UR_VMAX", "0.05"))
    ACAP = float(os.environ.get("UR_AMAX", "0.8"))

    HZ    = max(10.0, args.hz)  # keep ≥10 Hz for RTDE stability
    KP    = float(args.kp)
    VMAX  = min(float(args.vmax), VCAP)
    AMAX  = min(float(args.amax), ACAP)
    DEAD  = math.radians(float(args.deadband_deg))
    BETA  = float(args.lpf_beta)
    MAX_STEP = float(args.max_step)
    FADE_S   = max(0.0, float(args.fade_s))
    DT    = 1.0 / HZ

    # Gripper env config (coerce to ints if present)
    LEFT_GRIP_DO  = os.environ.get("LEFT_GRIP_DO")
    RIGHT_GRIP_DO = os.environ.get("RIGHT_GRIP_DO")
    try:
        LEFT_GRIP_DO  = int(LEFT_GRIP_DO)  if LEFT_GRIP_DO  is not None and LEFT_GRIP_DO  != "" else None
    except Exception:
        LEFT_GRIP_DO = None
    try:
        RIGHT_GRIP_DO = int(RIGHT_GRIP_DO) if RIGHT_GRIP_DO is not None and RIGHT_GRIP_DO != "" else None
    except Exception:
        RIGHT_GRIP_DO = None

    GRIP_OPEN  = float(os.environ.get("GRIP_OPEN_RAD",  "0.10"))
    GRIP_CLOSE = float(os.environ.get("GRIP_CLOSE_RAD", "0.10"))
    GRIP_HYST  = float(os.environ.get("GRIP_HYST_RAD",  "0.03"))

    # Connect URs
    urL, urR = UR(UR_LEFT_IP), UR(UR_RIGHT_IP)
    urL.connect(); urR.connect()
    qL0, qR0 = urL.q(), urR.q()

    if not qL0 or not qR0:
        print("❌ could not read initial UR joint states; check network/RTDE.")
        _cleanup(urL, urR, [])
        sys.exit(2)

    fmt = lambda q: [round(x,3) for x in q] if q else None
    print(f"UR left q:  {fmt(qL0)}")
    print(f"UR right q: {fmt(qR0)}")

    # Open Dynamixel buses
    buses = []
    busL = busR = None
    for port in (DXL_LEFT_PORT, DXL_RIGHT_PORT):
        if port:
            b = DxlBus(port)
            if b.open(): buses.append(b)
            if port == DXL_LEFT_PORT:  busL = b
            if port == DXL_RIGHT_PORT: busR = b
    if not (busL and busR):
        print("❌ DXL buses not both open; check DXL_LEFT_PORT/DXL_RIGHT_PORT in config.")
        _cleanup(urL, urR, buses); sys.exit(3)

    # SAFE START & zeroing
    if args.auto_arm:
        print(f"\n[SAFE START] Auto-arming in {args.arm_delay:.1f}s. Ensure poses match.")
        t0 = time.time()
        while SHOULD_RUN and (time.time() - t0) < args.arm_delay:
            remain = args.arm_delay - (time.time() - t0)
            print(f"  arming in {max(0.0, remain):0.1f}s   \r", end="", flush=True)
            time.sleep(0.1)
        print("\n[armed]")
    else:
        print("\n[SAFE START]\n - Place both URs & handhelds in a safe neutral pose.\n - Press ENTER to ARM.")
        try: input()
        except KeyboardInterrupt:
            _cleanup(urL, urR, buses); return

    # Capture handheld zeros (unsigned ticks)
    zL_ticks = busL.read_positions(LEFT_IDS)
    zR_ticks = busR.read_positions(RIGHT_IDS)
    if zL_ticks is None or zR_ticks is None:
        print("❌ failed to read DXL zeros"); _cleanup(urL, urR, buses); sys.exit(4)

    # Base UR pose & previous (start at base)
    qL_base = list(qL0[:6]); qR_base = list(qR0[:6])
    qL_prev = qL_base[:];    qR_prev = qR_base[:]
    t_start = time.time()

    print(f"[teleop] HZ={int(HZ)} KP={KP:.2f} VMAX={VMAX:.3f} AMAX={AMAX:.3f} DEADBAND_DEG={math.degrees(DEAD):.2f}")
    if (LEFT_GRIP_DO is not None) or (RIGHT_GRIP_DO is not None):
        ldo = LEFT_GRIP_DO if LEFT_GRIP_DO is not None else "-"
        rdo = RIGHT_GRIP_DO if RIGHT_GRIP_DO is not None else "-"
        print(f"[grip] LEFT_DO={ldo} RIGHT_DO={rdo} open<-{GRIP_OPEN:.2f} rad  close>+{GRIP_CLOSE:.2f} rad  hyst=+{GRIP_HYST:.2f} rad")

    # Gripper latch
    left_grip = False
    right_grip = False

    # -------- MAIN LOOP (DXL -> UR mapping) --------
    try:
        while SHOULD_RUN:
            # Read positions; on failure, retry next tick
            pL = busL.read_positions(LEFT_IDS)
            pR = busR.read_positions(RIGHT_IDS)
            if (pL is None) or (pR is None):
                time.sleep(0.005)
                continue

            # Convert to signed deltas (ticks->rad)
            try:
                dL = [signed_delta(p, z) * TICKS2RAD for p, z in zip(pL, zL_ticks)]
                dR = [signed_delta(p, z) * TICKS2RAD for p, z in zip(pR, zR_ticks)]
            except Exception:
                time.sleep(DT)
                continue

            # Deadband for first 6 joints
            for i in range(6):
                if abs(dL[i]) < DEAD: dL[i] = 0.0
                if abs(dR[i]) < DEAD: dR[i] = 0.0

            # Per-joint sign/scale + gain
            dqL = [SIGN_L[i] * SCALE_L[i] * KP * dL[i] for i in range(6)]
            dqR = [SIGN_R[i] * SCALE_R[i] * KP * dR[i] for i in range(6)]

            # Limit excursion from base (very conservative)
            dqL = clamp_vec(dqL, lim=0.35)  # ≤ 0.35 rad from base per joint
            dqR = clamp_vec(dqR, lim=0.35)

            qL_cmd_raw = add_vec(qL_base, dqL)
            qR_cmd_raw = add_vec(qR_base, dqR)

            # Low-pass + slew limiting
            qL_filt = lpf(qL_prev, qL_cmd_raw, BETA)
            qR_filt = lpf(qR_prev, qR_cmd_raw, BETA)
            qL_cmd  = slew_limit(qL_prev, qL_filt, MAX_STEP)
            qR_cmd  = slew_limit(qR_prev, qR_filt, MAX_STEP)

            # Fade-in
            if FADE_S > 0.0:
                fade = (time.time() - t_start) / FADE_S
                if fade < 1.0:
                    k = max(0.0, min(1.0, fade))
                    qL_cmd = [qL_prev[i] + (qL_cmd[i] - qL_prev[i]) * k for i in range(6)]
                    qR_cmd = [qR_prev[i] + (qR_cmd[i] - qR_prev[i]) * k for i in range(6)]

            # Stream to URs (extra gentle hard caps)
            spd = max(0.005, min(VMAX, 0.10))   # ≤0.10 rad/s (slow)
            acc = max(0.08,  min(AMAX, 0.30))  # ≤0.30 rad/s^2
            try:
                urL.servoJ(qL_cmd, spd, acc, DT, 0.12, 200.0)
                urR.servoJ(qR_cmd, spd, acc, DT, 0.12, 200.0)
                qL_prev, qR_prev = qL_cmd, qR_cmd
            except Exception as e:
                if args.debug:
                    print(f"[servo] warn: {e}")
                time.sleep(DT)

            # --- Gripper logic (ID7 / ID16 deltas) ---
            try:
                # Only touch index 6 if we actually have 7 elements
                if len(dL) >= 7 and LEFT_GRIP_DO is not None:
                    gL = float(dL[6])  # ID7 delta in radians
                    # open/close with hysteresis
                    if (not left_grip) and (gL > +GRIP_CLOSE + GRIP_HYST):
                        urL.set_do(LEFT_GRIP_DO, True);  left_grip = True
                    elif left_grip and (gL < -GRIP_OPEN - GRIP_HYST):
                        urL.set_do(LEFT_GRIP_DO, False); left_grip = False

                if len(dR) >= 7 and RIGHT_GRIP_DO is not None:
                    gR = float(dR[6])  # ID16 delta in radians
                    if (not right_grip) and (gR > +GRIP_CLOSE + GRIP_HYST):
                        urR.set_do(RIGHT_GRIP_DO, True);  right_grip = True
                    elif right_grip and (gR < -GRIP_OPEN - GRIP_HYST):
                        urR.set_do(RIGHT_GRIP_DO, False); right_grip = False
            except Exception:
                # never kill teleop for gripper issues
                pass

            time.sleep(DT)
    finally:
        _cleanup(urL, urR, buses)

if __name__ == "__main__":
    main()
