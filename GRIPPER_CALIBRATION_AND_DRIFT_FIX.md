# Gripper Calibration and Drift Fix Summary

## 🎯 Issues Fixed

### 1. Gripper Control Not Working in Teleop
**Problem:** The gripper commands weren't being triggered during teleop despite the test scripts working.

**Root Cause:** The gripper threshold was set to 0.0 radians, but your actual gripper positions are:
- **LEFT Gripper:** 2.5112 rad (closed) to 3.4316 rad (open)
- **RIGHT Gripper:** 4.1050 rad (closed) to 5.0929 rad (open)

**Solution:** Updated the thresholds based on actual hardware ranges:
- LEFT threshold: 2.97 rad (midpoint between 2.51 and 3.43)
- RIGHT threshold: 4.60 rad (midpoint between 4.10 and 5.09)

### 2. Terrible Drift Issues
**Problem:** The robot was drifting significantly when the GELLO arm was stationary.

**Solutions Implemented:**

#### A. Ultra-Aggressive Motion Damping
In `hardware/control_loop.py`:
- **Stationary threshold:** 0.0003 rad (was 0.001) - ULTRA tight
- **Stationary damping:** 100% (delta * 0.0) - NO movement when truly still
- **Nearly stationary threshold:** 0.001 rad (was 0.003)
- **Nearly stationary damping:** 99.5% reduction (delta * 0.005)
- **Slow movement threshold:** 0.003 rad
- **Slow movement damping:** 95% reduction (delta * 0.05)
- **Regular stopped damping:** 85% reduction (delta * 0.15)

#### B. Tighter Motion Parameters
In `configs/teleop_dual_ur5.yaml`:
- **EMA alpha:** 0.03 (was 0.06) - Ultra smooth filtering
- **Softstart time:** 0.15s (was 0.10) - Slower startup to prevent jerks
- **Deadbands:** [0.8°, 0.8°, 0.8°, 0.8°, 0.8°, 1.2°, 0.8°] - Much larger to eliminate micro-movements
- **Inactivity rebase time:** 1.0s (was 0.3) - Wait longer before rebaselining
- **Rebase beta:** 0.001 (was 0.10) - VERY slow baseline adjustment
- **Velocity damping:** 50% (was 70%) - More aggressive velocity damping

#### C. Delayed Rebaselining
- Now waits 3 seconds (was 1 second) before starting to rebaseline
- Rebaselining is 100x slower to prevent drift from baseline adjustment

## 📊 Gripper Calibration Values

### LEFT Gripper (ID 7)
- **Closed position:** 2.5112 rad (143.9°)
- **Open position:** 3.4316 rad (196.6°)
- **Range:** 0.9204 rad (52.7°)
- **Threshold:** 2.97 rad
- **Commands:** -0.1 (closed), 0.25 (open)

### RIGHT Gripper (ID 16)
- **Closed position:** 4.1050 rad (235.2°)
- **Open position:** 5.0929 rad (291.8°)
- **Range:** 0.9879 rad (56.6°)
- **Threshold:** 4.60 rad
- **Commands:** -0.1 (closed), 0.25 (open)

## 🚀 Testing Instructions

1. **Test the gripper control:**
   ```bash
   python scripts/run_teleop.py
   ```
   - Watch for gripper state messages in console
   - Should see: `[LEFT GRIPPER] Changed to: CLOSED (pos: 2.5xx rad, cmd: -0.1)`
   - Should see: `[LEFT GRIPPER] Changed to: OPEN (pos: 3.4xx rad, cmd: 0.25)`

2. **Verify drift reduction:**
   - Start teleop and move the GELLO arms
   - Stop moving and hold still
   - The UR robots should come to a complete stop with NO drift
   - Leave stationary for 10+ seconds - should remain perfectly still

3. **If drift persists, you can make it even more aggressive:**
   - In `hardware/control_loop.py`, change line 130: `delta = delta * 0.0` (already at 100% damping)
   - In `configs/teleop_dual_ur5.yaml`, increase deadbands further: `[1.0, 1.0, 1.0, 1.0, 1.0, 1.5, 1.0]`

## 🔧 Fine-Tuning

### If grippers don't trigger correctly:
- Adjust thresholds in `streamdeck_pedal_watch.py`:
  - Line 887: `gripper_threshold = 2.97` (LEFT)
  - Line 972: `gripper_threshold = 4.60` (RIGHT)

### If motion feels too sluggish:
- Reduce deadbands slightly in `configs/teleop_dual_ur5.yaml`
- Increase `ema_alpha` slightly (e.g., to 0.04 or 0.05)

### If ANY drift remains:
- Increase deadbands even more
- Set `rebase_beta: 0.0` to completely disable rebaselining

## ✅ Summary
- Gripper control now uses correct threshold values based on actual hardware ranges
- Drift reduction is EXTREMELY aggressive - 100% damping when stationary
- System should now be rock-solid stable when not moving
- Gripper commands execute via your dexgpt script as requested
