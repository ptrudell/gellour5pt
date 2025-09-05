# gello/scripts/rtde_shim.py
# Provides RTDEControlInterface / RTDEReceiveInterface regardless of package layout.

try:
    # Layout A (some envs expose modules under ur_rtde)
    from ur_rtde import rtde_control as _rtde_control
    from ur_rtde import rtde_receive as _rtde_receive
except Exception:
    # Layout B (your env right now: top-level modules)
    import rtde_control as _rtde_control       # type: ignore
    import rtde_receive as _rtde_receive       # type: ignore

RTDEControlInterface = _rtde_control.RTDEControlInterface
RTDEReceiveInterface = _rtde_receive.RTDEReceiveInterface
