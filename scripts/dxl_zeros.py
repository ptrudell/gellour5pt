# gello/scripts/dxl_zeros.py
import json, time, pathlib
from typing import List, Dict
from dynamixel_sdk import (
    PortHandler, PacketHandler, GroupSyncRead,
    COMM_SUCCESS
)

DEFAULT_CACHE = pathlib.Path("~/.gello/dxl_zeros.json").expanduser()
ADDR_POS = 132          # XL-330, X-series present position (4 bytes) on Protocol 2.0
LEN_POS  = 4
FIRST_REOPEN_DELAY_S = 0.10   # brief pause after opening the port helps some USB hubs
PER_ID_RETRIES = 3
SYNC_READ_RETRIES = 2

def _key(port_path, ids): 
    return f"{pathlib.Path(port_path).name}::{','.join(map(str,ids))}"

def _load(cache_path):
    p = pathlib.Path(cache_path)
    if not p.exists(): 
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}

def _save(cache_path, data):
    p = pathlib.Path(cache_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))

def _open_bus(port: str, baud: int):
    ph = PortHandler(port)
    if not ph.openPort():
        raise RuntimeError(f"open failed: {port}")
    if not ph.setBaudRate(baud):
        try: ph.closePort()
        except: pass
        raise RuntimeError(f"baud failed: {baud} on {port}")
    time.sleep(FIRST_REOPEN_DELAY_S)
    return ph

def _ping_all(ph: PortHandler, pk: PacketHandler, ids: List[int]) -> Dict[int, bool]:
    status = {}
    for i in ids:
        _, comm, err = pk.ping(ph, i)
        status[i] = (comm == COMM_SUCCESS and err == 0)
        # tiny spacing to be gentle on bus after long idle
        time.sleep(0.005)
    return status

def _sync_read_positions(ph: PortHandler, pk: PacketHandler, ids: List[int]) -> Dict[int, int]:
    """Try a GroupSyncRead first; if any miss, raise for fallback path."""
    gsr = GroupSyncRead(ph, pk, ADDR_POS, LEN_POS)
    for i in ids:
        if not gsr.addParam(i):
            raise RuntimeError(f"group addParam failed for ID {i}")
    for _ in range(SYNC_READ_RETRIES):
        # one shot read for all
        if gsr.txRxPacket() != COMM_SUCCESS:
            time.sleep(0.02)
            continue
        # collect
        out = {}
        missing = []
        for i in ids:
            if not gsr.isAvailable(i, ADDR_POS, LEN_POS):
                missing.append(i)
            else:
                out[i] = gsr.getData(i, ADDR_POS, LEN_POS)
        if not missing:
            return out
        # brief retry if anything missed (USB autosuspend waking up, etc.)
        time.sleep(0.03)
    raise RuntimeError(f"sync read missing IDs: {missing}")

def _per_id_positions(ph: PortHandler, pk: PacketHandler, ids: List[int]) -> Dict[int, int]:
    """Robust per-ID read with retries; returns dict for IDs that succeeded."""
    out = {}
    for i in ids:
        got = False; last_err = ""
        for _ in range(PER_ID_RETRIES):
            pos, comm, err = pk.read4ByteTxRx(ph, i, ADDR_POS)
            if comm == COMM_SUCCESS and err == 0:
                out[i] = pos
                got = True
                break
            else:
                last_err = f"comm={comm}, err={err}"
                time.sleep(0.02)
        if not got:
            # don’t abort yet; collect as missing and continue
            out[i] = None  # mark missing
    # filter None and report if any missing
    missing = [i for i,v in out.items() if v is None]
    if missing:
        raise RuntimeError(f"per-id read missing IDs: {missing}")
    return out

def get_or_create_zeros(port: str, baud: int, proto: float, ids: List[int], cache_path=DEFAULT_CACHE) -> Dict[int,int]:
    """
    Ensures zeros exist for this (port, ids) tuple. On first run (or cache miss),
    it reads present positions and saves them as zeros. On subsequent runs, it
    validates the bus is alive but returns cached zeros even if validation fails.
    Raises RuntimeError with detailed diagnostics if the first-time read fails.
    """
    data = _load(cache_path)
    k = _key(port, ids)

    # open bus
    ph = _open_bus(port, baud)
    pk = PacketHandler(proto)

    # If cached, quickly validate bus and return cache
    if k in data and isinstance(data[k], dict) and data[k]:
        try:
            # quick ping sweep; ignore result but keeps adapter awake
            _ = _ping_all(ph, pk, ids)
            # quick one-shot read to “warm” the line
            try:
                _ = _sync_read_positions(ph, pk, ids)
            except Exception:
                # ignore; cache is valid, and we just wanted to wake the bus
                pass
        finally:
            ph.closePort()
        return {int(i): int(v) for i,v in data[k].items()}

    # No cache: do a full robust read path
    pings = _ping_all(ph, pk, ids)
    dead = [i for i,ok in pings.items() if not ok]
    if dead:
        ph.closePort()
        raise RuntimeError(f"DXL ping failed on IDs {dead} (port={port}, baud={baud}, proto={proto})")

    # Try sync read, then fallback to per-ID if needed
    try:
        zeros = _sync_read_positions(ph, pk, ids)
    except Exception:
        zeros = _per_id_positions(ph, pk, ids)

    ph.closePort()

    # Save cache
    data[k] = zeros
    _save(cache_path, data)
    return zeros
