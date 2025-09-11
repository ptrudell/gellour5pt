# Optimized Teleop System - Complete Integration

## 🚀 Major Improvements Implemented

### 1. **Gripper Control - Now Working Properly**
- **Correct Command Values:**
  - Left OPEN: `0.50`
  - Right OPEN: `0.25`
  - Both CLOSED: `-0.075`
- **Baseline-Relative Thresholds:** Automatically adapts to your gripper's resting position
- **Hysteresis Control:** Prevents flapping between states
- **Time Debounce:** Min 0.18s between commands to avoid spam
- **Dual Output:** Both JSON files and dexgpt script calls

### 2. **Advanced Anti-Jitter System**
- **Input EMA Smoothing:** Extra smoothing on DXL readings before controller
- **Min-Change Gate:** Only sends commands if target changes by >0.25°
- **Idle Hold:** Sends `stopJ` after 0.30s of no movement (rock-solid stop)
- **UR Control Backoff:** Suppresses RTDE spam when ExternalControl isn't running

### 3. **Optimized Motion Control**
- **Balanced Deadbands:** [1.4°, 1.4°, 1.4°, 2.0°, 2.2°, 3.0°, 3.0°]
- **Smart EMA:** Controller EMA at 0.12, input EMA at 0.20
- **Velocity Damping:** Ultra-aggressive when stationary
- **Error Suppression:** Rate-limited error printing (1Hz max)

## 📋 Quick Test Commands

### Test Grippers Manually
```bash
# Close both grippers
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_left --position -0.075
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_right --position -0.075

# Open grippers (different values for each)
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_left --position 0.5
python ~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py -o gripper_command_right --position 0.25
```

### Run Optimized Teleop
```bash
python scripts/run_teleop.py
```

## ⚠️ CRITICAL: Fix RTDE Errors

The "RTDEControlInterface: RTDE control script is not running!" spam indicates ExternalControl.urp is not playing on the UR pendant.

### To Fix:
1. **On UR Pendant:**
   - File → Load Program → ExternalControl.urp
   - Set Remote Control: ON
   - Set Host IP: Your PC's IP (NOT the robot's IP)
   - Press Play (▶️)

2. **Leave it running** in the background before pressing CENTER pedal

## 🎯 What to Expect

### During Teleop:
- **Gripper Messages:** `[LEFT GRIPPER] → OPEN/CLOSED (pos X.XXX rad, cmd Y.YY)`
- **No RTDE Spam:** If ExternalControl is running properly
- **Rock-Solid Stability:** Arms stop completely when GELLO is still
- **Smooth Movement:** No jitter or random motions

### Gripper Behavior:
- Grippers respond to squeeze/release with proper hysteresis
- Commands saved to `/tmp/gripper_command_{left|right}.json`
- Automatic fallback if dexgpt script isn't available

## 🔧 Fine-Tuning

### If Grippers Don't Respond:
Check the baseline values printed during startup:
```
[grip] Baselines L=X.XXX rad, R=Y.YYY rad
```

Adjust in config if needed:
- `delta_open`: How far above baseline to trigger open
- `delta_close`: How far below baseline to trigger close

### If Still Some Jitter:
In `configs/teleop_dual_ur5.yaml`:
- Increase `deadband_deg` values
- Reduce `input_ema_alpha` (more smoothing)
- Increase `min_target_step` (bigger change threshold)

### Monitor Gripper Commands:
```bash
# Watch gripper command files
watch -n 0.2 'ls -la /tmp/gripper_command_*.json 2>/dev/null | tail -2'

# See command contents
watch -n 0.2 'for f in /tmp/gripper_command_*.json; do echo "=== $f ==="; cat $f 2>/dev/null | jq -c .; done'
```

## ✅ System Status

All components are now integrated:
- ✅ Proper gripper command values (0.50, 0.25, -0.075)
- ✅ Baseline-relative control with hysteresis
- ✅ Advanced anti-jitter (input EMA, min-change, idle hold)
- ✅ RTDE error suppression with backoff
- ✅ Optimized motion parameters
- ✅ Fallback JSON file output

## 📊 Performance Metrics

Expected behavior:
- **Gripper Response:** < 200ms from squeeze/release
- **Idle Stability:** Zero drift after 0.3s stationary
- **Command Rate:** 125Hz with minimal overruns
- **Error Recovery:** Auto-reconnect on disconnect

## 🚨 Troubleshooting

### "Control error - is ExternalControl running?"
→ Load and play ExternalControl.urp on pendant

### Grippers not moving
→ Check `/tmp/gripper_command_*.json` files are being created
→ Verify dexgpt script path exists at `~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py`

### Still some drift
→ Increase `idle_hold_s` in config
→ Reduce `min_target_step` threshold
→ Check mechanical backlash in GELLO arms
