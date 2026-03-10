# setpoints.py  ─  shared between server.py and client.py
# Holds per-register warn/crit setpoints (0-100).
# Both GUIs import this so they use the same in-memory store.
# If you want setpoints to persist across restarts, call save()/load().

import json, os

NUM_REGS    = 10
_SAVE_FILE  = "setpoints.json"

# defaults
_warn = [80] * NUM_REGS
_crit = [95] * NUM_REGS


def get_warn(idx: int) -> int:
    return _warn[idx]

def get_crit(idx: int) -> int:
    return _crit[idx]

def set_warn(idx: int, v: int):
    _warn[idx] = max(0, min(100, v))

def set_crit(idx: int, v: int):
    _crit[idx] = max(0, min(100, v))

def alarm_state(idx: int, value: int) -> str:
    """Return 'crit', 'warn', or 'ok' for a given register value."""
    if value >= _crit[idx]:
        return "crit"
    if value >= _warn[idx]:
        return "warn"
    return "ok"

def save():
    with open(_SAVE_FILE, "w") as f:
        json.dump({"warn": _warn, "crit": _crit}, f)

def load():
    global _warn, _crit
    if os.path.exists(_SAVE_FILE):
        try:
            data = json.load(open(_SAVE_FILE))
            _warn = data.get("warn", _warn)
            _crit = data.get("crit", _crit)
        except Exception:
            pass

# auto-load on import
load()
