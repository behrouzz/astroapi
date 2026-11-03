"""Earth Orientation Parameters from the IERS data centre (numpy + stdlib only)."""
import os
import ssl
import time as _time
import urllib.request
from pathlib import Path

import numpy as np

from .time import any2mjd, leap_seconds_mjd

DEFAULT_DATA_DIR = Path(os.environ.get("IERS_DATA_DIR", Path(__file__).parent / "data"))
_IERS = "https://datacenter.iers.org/data/latestVersion/"
_OBSPM = "https://hpiers.obspm.fr/iers/series/longterm/"

# kind -> (file name, base URL, header lines to skip, {column: (start, end)} 0-based slices)
_FIXED = {
    2: ("EOP_14_C04_IAU2000A_one_file_1962-now.txt", _IERS, 13,
        {"mjd": (14, 19), "px": (21, 30), "py": (32, 41), "ut1_utc": (43, 53),
         "lod": (55, 65), "dx": (67, 76), "dy": (78, 87)}),
    3: ("EOP_C01_IAU2000_1846-now.txt", _IERS, 13,
        {"mjd": (3, 12), "px": (13, 22), "py": (23, 32), "ut1_tai": (33, 44),
         "dx": (49, 58), "dy": (62, 71), "lod": (228, 237)}),
    4: ("nao_a.eop", _OBSPM, 13, {"mjd": (0, 13), "ut1_tai": (33, 48), "lod": (229, 238)}),
}
# finals.all (kind 1): 1-based inclusive column ranges per the USNO readme.finals2000A
_FINALS = ("finals.all.iau2000.txt", _IERS)
_FINALS_COLS = {
    "mjd": (7, 12),
    "px_A": (19, 27), "py_A": (38, 46), "ut1_utc_A": (59, 68), "dx_A": (98, 106), "dy_A": (117, 125),
    "px_B": (135, 144), "py_B": (145, 154), "ut1_utc_B": (155, 165), "dx_B": (166, 175),
    "dy_B": (176, 185),
}
_PARAMS = ["px", "py", "ut1_utc", "dx", "dy"]


def _num(text: str) -> float:
    try:
        return float(text)
    except ValueError:
        return np.nan


class EOP:
    """Earth orientation parameters table + interpolation.

    kind 1: finals.all (IAU2000; Bulletin B where available, else Bulletin A) -> px, py,
            ut1_utc, dx, dy        2: EOP 14 C04 (since 1962)     3: EOP C01 (since 1846)
    kind 4: NAO long-term series.
    The data file is cached in ``data_dir`` and re-downloaded when older than ``max_age_days``
    (an existing stale file is still used if the download fails).
    """

    def __init__(self, kind: int = 1, data_dir=None, max_age_days: float = 7, offline: bool = False):
        if kind not in (1, 2, 3, 4):
            raise ValueError("kind must be 1, 2, 3 or 4")
        self.kind = kind
        self.bulletin = None
        self.table: dict[str, np.ndarray] = {}
        name, base = _FINALS if kind == 1 else _FIXED[kind][:2]
        self.URL = base + name
        self.path = Path(data_dir or DEFAULT_DATA_DIR) / name
        age = _time.time() - self.path.stat().st_mtime if self.path.exists() else None
        if not offline and (age is None or age > max_age_days * 86400):
            try:
                self.download()
            except OSError:
                if age is None:
                    raise
        self.read_table()

    def download(self) -> None:
        """Fetch the data file (atomically replaces any cached copy)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".part")
        try:  # the IERS server's certificate chain only verifies against the certifi bundle
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()
        with urllib.request.urlopen(self.URL, timeout=60, context=ctx) as resp:
            tmp.write_bytes(resp.read())
        tmp.replace(self.path)

    def read_table(self) -> None:
        lines = self.path.read_text(errors="replace").split("\n")
        if self.kind == 1:
            lines = [ln for ln in lines if len(ln.strip()) > 20]
            cols = {c: (a - 1, b) for c, (a, b) in _FINALS_COLS.items()}
        else:
            _, _, skip, cols = _FIXED[self.kind]
            lines = [ln for ln in lines[skip:] if ln.strip()]
        table = {c: np.array([_num(ln[a:b]) for ln in lines]) for c, (a, b) in cols.items()}
        if self.kind == 3:
            table["ut1_tai"][table["ut1_tai"] == 99.99] = np.nan
        keep = ~np.isnan(table["mjd"])
        self.table = {c: v[keep] for c, v in table.items()}

    def lookup(self, t):
        """Interpolated EOP at ``t`` -> (dict of floats, bulletin 'A'/'B'/None). Thread-safe."""
        mjd = any2mjd(t)
        tb = self.table
        x = tb["mjd"]
        if not (x[0] <= mjd <= x[-1]):
            raise ValueError(f"MJD {mjd:.5f} out of range [{x[0]:.1f}, {x[-1]:.1f}]")
        i = int(np.clip(np.searchsorted(x, mjd, side="right") - 1, 0, len(x) - 2))
        bulletin = None
        if self.kind == 1:
            # Bulletin B (final) if both bracketing days have it, else Bulletin A (predictions)
            bulletin = "B" if not np.isnan(tb["px_B"][i:i + 2]).any() else "A"
            cols = {p: tb[f"{p}_{bulletin}"] for p in _PARAMS}
        else:
            cols = {c: v for c, v in tb.items() if c != "mjd"}
        out = {c: self._interp(mjd, x, y, c) for c, y in cols.items()}
        return out, bulletin

    @staticmethod
    def _interp(mjd, x, y, name):
        i = int(np.clip(np.searchsorted(x, mjd, side="right") - 1, 0, len(x) - 2))
        x0, x1, y0, y1 = x[i], x[i + 1], y[i], y[i + 1]
        shift = 0
        if name == "ut1_utc":
            l0, l1 = leap_seconds_mjd(x0), leap_seconds_mjd(x1)
            if l0 != l1:  # UT1-UTC jumps 1 s at a leap second; interpolate continuous UT1-TAI
                y0, y1, shift = y0 - l0, y1 - l1, leap_seconds_mjd(mjd)
        v = y0 + (y1 - y0) * (mjd - x0) / (x1 - x0) + shift
        return float(v) if np.isfinite(v) else None

    def interpolate(self, mjd: float) -> dict:
        res, self.bulletin = self.lookup(float(mjd) + 2400000.5)
        return res

    def get_eop(self, t) -> dict:
        """Interpolated EOP at ``t`` (datetime, JD or ISO string). Sets ``self.bulletin``."""
        res, self.bulletin = self.lookup(t)
        return res
