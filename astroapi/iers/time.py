"""Time input parsing and leap seconds."""
import re
from datetime import datetime
from numbers import Real

import numpy as np

_MJD0 = datetime(1858, 11, 17)
_ISO = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}):(\d{2})(\.\d+)?)?\s*$")

# MJD (UTC) of each 0h UTC at which TAI-UTC steps to the next whole-second value.
_LEAP_MJD = np.array([
    41317, 41499, 41683, 42048, 42413, 42778, 43144, 43509, 43874, 44239, 44786, 45151,
    45516, 46247, 47161, 47892, 48257, 48804, 49169, 49534, 50083, 50630, 51179, 53736,
    54832, 56109, 57204, 57754], dtype=float)
_LEAP_SEC = np.arange(10, 10 + len(_LEAP_MJD))  # 10 s on 1972-01-01 ... 37 s on 2017-01-01


def iso_to_datetime(text: str) -> datetime:
    """Parse 'YYYY-MM-DD', 'YYYY-MM-DD HH:MM:SS' or the same with 'T' / fractional seconds."""
    m = _ISO.match(text)
    if not m:
        raise ValueError(f"Cannot parse time {text!r}; use e.g. '2024-02-10 09:30:58'")
    y, mo, d, h, mi, s, frac = m.groups()
    return datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), int(s or 0),
                    int(round(float(frac) * 1e6)) if frac else 0)


def any2mjd(t) -> float:
    """datetime, Julian Date (int/float) or ISO string  ->  Modified Julian Date."""
    if isinstance(t, datetime):
        return (t - _MJD0).total_seconds() / 86400.0
    if isinstance(t, Real) and not isinstance(t, bool):
        return float(t) - 2400000.5
    if isinstance(t, str):
        return any2mjd(iso_to_datetime(t))
    raise TypeError(f"Cannot parse time of type {type(t).__name__}")


def leap_seconds_mjd(mjd):
    """TAI-UTC (whole seconds) at MJD(s) UTC; 0 before 1972-01-01. Vectorised."""
    idx = np.searchsorted(_LEAP_MJD, mjd, side="right") - 1
    return np.where(idx >= 0, _LEAP_SEC[np.clip(idx, 0, None)], 0)


def leap_seconds(t) -> int:
    """Leap seconds (TAI-UTC) at UTC time ``t`` (datetime, JD or ISO string)."""
    return int(leap_seconds_mjd(any2mjd(t)))
