# Deadband Tuning Guide

## Current Settings: 2.5-5 Degrees

The deadbands have been reduced to provide better responsiveness while maintaining stability.

## Deadband Values by Joint

| Joint | Deadband (degrees) | Purpose |
|-------|-------------------|---------|
| Joint 1 (Base) | 2.5° | Most precise - base rotation |
| Joint 2 (Shoulder) | 2.5° | Precise shoulder movement |
| Joint 3 (Elbow) | 3.0° | Slightly more filtering |
| Joint 4 (Wrist 1) | 3.5° | Moderate filtering |
| Joint 5 (Wrist 2) | 4.0° | More filtering for wrist |
| Joint 6 (Wrist 3) | 5.0° | Most filtering - finest joint |
| Gripper | 3.0° | Moderate for gripper control |

## How to Adjust

Edit `/home/shared/gellour5pt/configs/teleop_dual_ur5.yaml`:

```yaml
motion_shaping:
  deadband_deg: [2.5, 2.5, 3, 3.5, 4, 5, 3]  # Adjust these values
```

## Tuning Guidelines

### If robot is too jittery:
- **Increase** deadband values (e.g., 5-10 degrees)
- **Decrease** EMA alpha (e.g., 0.02 for more smoothing)
- **Increase** softstart time (e.g., 0.15s)

### If robot is not responsive enough:
- **Decrease** deadband values (current: 2.5-5 degrees)
- **Increase** EMA alpha (e.g., 0.05 for less smoothing)
- **Decrease** softstart time (e.g., 0.08s)

## Related Parameters

### EMA (Exponential Moving Average)
- **Current:** 0.03
- **Range:** 0.01 (heavy smoothing) to 0.20 (minimal smoothing)
- Controls how much current input affects output

### Softstart Time
- **Current:** 0.10s
- **Range:** 0.05s (quick start) to 0.30s (gentle start)
- Ramps up movement speed gradually

### Inactivity Handling
- **Wait time:** 2.0s before considering inactive
- **Rebase rate:** 0.0005 (very slow baseline adjustment)
- **Snap threshold:** 0.001 rad (tight snapping to targets)

## Common Deadband Ranges

| Scenario | Typical Range | Use Case |
|----------|--------------|----------|
| Ultra-precise | 1-3° | High-precision tasks, stable environment |
| Responsive | 2.5-5° | **Current setting** - balanced |
| Moderate | 5-10° | Some jitter present |
| Conservative | 10-15° | Noisy environment |
| Very conservative | 15-20° | High drift/jitter issues |

## Testing Your Settings

After adjusting:
```bash
python scripts/run_teleop.py
```

Watch for:
1. **Jitter at rest** - Should be minimal
2. **Small movement response** - Should track well
3. **Stopping behavior** - Should settle quickly
4. **Drift over time** - Should be negligible

## Quick Adjustment Commands

```bash
# For more responsiveness (smaller deadbands)
sed -i 's/deadband_deg: .*/deadband_deg: [2, 2, 2.5, 3, 3.5, 4, 2.5]/' configs/teleop_dual_ur5.yaml

# For more stability (larger deadbands)
sed -i 's/deadband_deg: .*/deadband_deg: [5, 5, 6, 7, 8, 10, 5]/' configs/teleop_dual_ur5.yaml

# For high jitter environments
sed -i 's/deadband_deg: .*/deadband_deg: [10, 10, 12, 14, 15, 18, 10]/' configs/teleop_dual_ur5.yaml
```

## Notes

- Joints closer to the base (1-3) typically need smaller deadbands for precision
- Wrist joints (4-6) can tolerate larger deadbands
- Joint 6 (wrist roll) often needs the largest deadband as it's most sensitive
- Gripper deadband affects open/close sensitivity

Remember: There's always a tradeoff between responsiveness and stability!
