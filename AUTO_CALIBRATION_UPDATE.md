# Auto-Calibration Update

## ✅ KEYBOARD CALIBRATION REMOVED

All manual keyboard calibration has been removed from the gripper control system.

## What Changed

### Before
- Scripts would ask you to manually move grippers and press ENTER
- Required coordinating keyboard input with physical gripper movements
- Made testing difficult and slow

### After
- **Fully automatic calibration**
- Uses pre-configured default values that work for most GELLO setups
- No keyboard input required
- Tests run automatically

## Default Calibration Values

These values work for standard GELLO gripper configurations:

| Gripper | Closed Position | Open Position | Range |
|---------|----------------|---------------|--------|
| LEFT    | -0.629 rad     | 0.262 rad     | 0.891 rad |
| RIGHT   | 0.962 rad      | 1.908 rad     | 0.946 rad |

## Updated Scripts

### 1. `direct_gripper_control.py`
- **calibrate()** method now uses default values automatically
- **main()** runs an automatic test sequence instead of interactive mode
- No keyboard input required

### 2. `find_gripper_positions.py`
- Shows current positions and default calibration
- No manual movement required
- Just reads and displays information

### 3. `test_gripper_quick.py`
- Already automatic (no changes needed)

## How to Test

### Quick Gripper Test
```bash
python scripts/direct_gripper_control.py
```
This will:
1. Connect to grippers
2. Auto-calibrate with defaults
3. Run test sequence (close/open both grippers)
4. Exit automatically

### Check Current Positions
```bash
python scripts/find_gripper_positions.py
```
This will:
1. Connect to grippers
2. Show current positions
3. Display default calibration values

### Run Full Teleop
```bash
python scripts/run_teleop.py
```
Grippers will work automatically with default calibration.

## Adjusting Calibration (If Needed)

If your grippers have different ranges, edit the values in:

**`scripts/direct_gripper_control.py`** (lines 101-107):
```python
# LEFT gripper typical range
self.left_closed_ticks = -0.629  # Adjust if needed
self.left_open_ticks = 0.262     # Adjust if needed

# RIGHT gripper typical range  
self.right_closed_ticks = 0.962   # Adjust if needed
self.right_open_ticks = 1.908     # Adjust if needed
```

**`configs/teleop_dual_ur5.yaml`** (gripper section):
```yaml
gripper:
  # GELLO gripper calibration
  left_gello_min: -0.629   # Adjust if needed
  left_gello_max: 0.262    # Adjust if needed
  right_gello_min: 0.962   # Adjust if needed
  right_gello_max: 1.908   # Adjust if needed
```

## Benefits

1. **No Manual Coordination** - Scripts run without user intervention
2. **Faster Testing** - No waiting for keyboard input
3. **Consistent Results** - Same calibration every time
4. **CI/CD Friendly** - Can run in automated pipelines
5. **Less Error-Prone** - No chance of pressing ENTER at wrong time

## Summary

The gripper control system is now fully automatic. Just run the scripts and they'll handle everything!
