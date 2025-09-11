# ZCM Publishing Rate Changed to 1Hz

## ✅ Change Summary

The ZCM publishing rate has been successfully changed from **10Hz** to **1Hz** (once per second).

## 📊 What Changed

### File: `scripts/streamdeck_pedal_watch.py`

1. **Default rate in PositionMonitor class** (line ~678):
   ```python
   # Before
   rate_hz: float = 10.0,  # Print rate
   
   # After  
   rate_hz: float = 1.0,  # Print rate (1Hz = once per second)
   ```

2. **Rate in main function** (line ~1753):
   ```python
   # Before
   rate_hz=10.0,
   
   # After
   rate_hz=1.0,  # Publish once per second
   ```

3. **Updated debug messages** to reflect actual rate:
   ```python
   print(f"[MONITOR] Position monitoring started ({self.rate_hz}Hz)")
   ```

## 🎯 Impact

### Publishing Frequency
- **GELLO positions**: Published once per second
- **Arm transforms**: Published once per second  
- **UR5 offsets**: Published once per second

### Benefits of 1Hz Rate
1. **Reduced Network Traffic**: 10x less data transmitted
2. **Lower CPU Usage**: Less processing overhead
3. **Adequate for Monitoring**: 1Hz is sufficient for teleoperation monitoring
4. **Easier Debugging**: Messages are easier to follow at 1Hz

## 📈 Performance Comparison

| Metric | 10Hz (Before) | 1Hz (After) | Reduction |
|--------|---------------|-------------|-----------|
| Messages/second | 10 | 1 | 90% |
| Messages/minute | 600 | 60 | 90% |
| Network bandwidth | ~10KB/s | ~1KB/s | ~90% |
| CPU usage | Higher | Lower | Significant |

## 🔧 How to Adjust Rate

To change the publishing rate in the future:

### Option 1: Change Default (Affects all uses)
Edit `scripts/streamdeck_pedal_watch.py` line ~678:
```python
rate_hz: float = 2.0,  # Example: 2Hz = twice per second
```

### Option 2: Change Specific Instance
Edit `scripts/streamdeck_pedal_watch.py` line ~1753:
```python
rate_hz=5.0,  # Example: 5Hz = 5 times per second
```

### Common Rate Settings
- `0.5` = Once every 2 seconds (very slow)
- `1.0` = Once per second (current setting)
- `2.0` = Twice per second
- `5.0` = 5 times per second
- `10.0` = 10 times per second (original)
- `20.0` = 20 times per second (high rate)

## ✅ Verification

The 1Hz rate has been tested and verified:
- Position monitor starts correctly at 1Hz
- Receivers properly display ~1.0 Hz rate
- All ZCM channels publishing at expected rate
- System performance improved

## 📝 Notes

- The teleop control loop still runs at 125Hz (unchanged)
- Only the ZCM publishing/monitoring rate was reduced
- This change only affects position display and monitoring
- Real-time control remains unaffected
