"""Example request bodies for every ERFA endpoint (shown in Swagger "Try it out").

Most values follow the SOFA/ERFA validation tests and cookbook examples
(epoch 2006-01-01, a site near longitude -0.5 rad, a star near RA 2.71, Dec 0.174).
``DEFAULTS`` supplies a value per argument name; ``OVERRIDES`` fixes the functions in
which a name means something different (e.g. ``a``/``b`` are vectors in ``pap``).
"""
import re

import erfa
import numpy as np

_I3 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
_R = [[0.9999880436, -0.0044849937, -0.0019486956],
      [0.0044849967, 0.9999899423, -0.0000028666],
      [0.0019486888, -0.0000058733, 0.9999981013]]
_P = [0.3, -0.5, 0.8]
_PV = [[0.3, -0.5, 0.8], [0.0001, -0.0002, 0.0003]]
_JD1, _JD2 = 2400000.5, 53736.0
_SITE = dict(dut1=0.3341, elong=-0.5, phi=0.8, hm=1000.0, xp=2.5e-7, yp=1.5e-6)
_ATMO = dict(phpa=800.0, tc=10.0, rh=0.5, wl=0.55)
_STAR = dict(rc=2.71, dc=0.174, pr=1e-5, pd=5e-6, px=0.1, rv=55.0)


def _struct_to_dict(arr) -> dict:
    return {n: np.asarray(arr[n]).tolist() for n in arr.dtype.names}


# A real eraASTROM computed by erfa.apco13, so every astrometry example is consistent.
ASTROM = _struct_to_dict(erfa.apco13(_JD1, _JD2, 0.3341, -0.5, 0.8, 1000.0, 2.5e-7, 1.5e-6,
                                     800.0, 10.0, 0.5, 0.55)[0])
BODIES = [{"bm": 0.00028574, "dl": 6e-9,
           "pv": {"p": [-7.81014427, -5.60956681, -1.98079819],
                  "v": [0.0030723249, -0.00406995477, -0.00181335842]}}]

DEFAULTS = {
    # dates / times (two-part Julian Dates)
    **{k: _JD1 for k in ("date1", "utc1", "tai1", "tt1", "tcb1", "tcg1", "tdb1", "ut11",
                         "uta", "tta", "dj1", "d1", "date01", "date11", "ep1a", "ep2a")},
    **{k: _JD2 for k in ("date2", "utc2", "tai2", "tt2", "tcb2", "tcg2", "tdb2", "ut12",
                         "utb", "ttb", "dj2", "d2", "date02", "date12")},
    "ep1b": 33282.0, "ep2b": 51544.5,
    "ut": 0.25, "t": 0.2, "dt": 10.0, "dta": -0.1, "dtr": -0.0001,
    "scale": "UTC", "ndp": 3, "days": 0.25, "fd": 0.5,
    "iy": 2006, "im": 1, "id": 1, "ihr": 12, "imn": 30, "sec": 15.25,
    "ihour": 6, "imin": 45, "s": 1.0, "ideg": 45, "iamin": 30, "asec": 12.5,
    "epb": 1957.3, "epj": 2000.0, "bepoch": 1950.0, "angle": 1.2345, "a": 1.2345,
    # observer / site
    **_SITE, **_ATMO, "height": 1000.0, "sp": -3e-5, "theta": 1.6, "era": 1.6, "gst": 1.6,
    "type": "R", "ob1": 2.71, "ob2": 0.174,
    # star
    **_STAR, "ra": 2.71, "dec": 0.174, "ri": 2.71, "di": 0.174, "pmr": 1e-5, "pmd": 5e-6,
    "ra1": 2.71, "dec1": 0.174, "pmr1": 1e-5, "pmd1": 5e-6, "px1": 0.1, "rv1": 55.0,
    # FK4/FK5/Hipparcos
    "r1950": 0.07, "d1950": -0.17, "dr1950": 1e-5, "dd1950": -5e-6, "p1950": 0.1, "v1950": 20.0,
    "r2000": 0.07, "d2000": -0.17, "dr2000": 1e-5, "dd2000": -5e-6, "p2000": 0.1, "v2000": 20.0,
    "r5": 1.76779433, "d5": -0.2917517103, "dr5": -1.91851572e-7, "dd5": -5.8468475e-6,
    "px5": 0.379210, "rv5": -7.6, "dh": -0.0001, "pxh": 0.1, "rvh": 5.0, "ddh": 1e-7, "drh": 1e-7,
    # coordinates
    "dl": 5.1, "db": -0.9, "dr": 5.1, "dd": -0.9, "al": 1.0, "ap": 2.0, "bl": 0.5, "bp": -0.3,
    "az": 5.5, "el": 0.7, "ha": 0.5, "xi": 0.1, "eta": 0.05, "a0": 1.0, "b0": 0.5, "b": 0.5,
    "xyz": [2e6, 3e6, 5e6], "n": 1, "f": 1 / 298.257223563, "np": 3, "bm": 0.00028574,
    "bm1": 0.99998, "dlim": 1e-6, "em": 1.0, "e": [-0.97, 0.20, 0.09], "q": [-0.7, 0.7, 0.1],
    "pob": [-0.1, 0.9, 0.4], "pmt": 8.5, "pnat": [-0.76, -0.60, -0.23], "v": [0.0001, -0.0002, 0.0001],
    "v0": [0.6, 0.5, 0.62], "ob": [-0.9, 0.4, 0.1], "sc": [0.4, 0.5, 0.75], "w": [0.001, -0.002, 0.003],
    "p": _P, "pv": _PV, "r": _R, "u": 0.0, "x": 0.0007, "y": 0.00004, "gamb": -0.0000253,
    "phib": 0.4090, "psi": -0.0000451, "eps": 0.4090, "dpsi": -9.6e-6, "deps": -4.0e-5,
    "epsa": 0.4090, "s1": 2.0, "s2": 0.5,
    # matrices / structs / vector blocks
    "rbpn": _R, "rnpb": _R, "rpom": _R, "rc2i": _R, "astrom": ASTROM,
    "ebpv": [[-0.35, -0.87, -0.38], [0.016, -0.0055, -0.0024]], "ehp": [-0.35, -0.86, -0.37],
    "refa": 2.7e-4, "refb": -3e-7, "rh": 0.5,
}

_UNIQUE = {
    "ab": {"s": 0.95, "pnat": [-0.76, -0.60, -0.23]},
    "af2a": {"s": "+"}, "tf2a": {"s": "+"}, "tf2d": {"s": "+"},
    "anp": {"a": -2.0}, "anpm": {"a": 7.5},
    "dtdb": {"v": 3.0, "u": 4000.0, "ut": 0.25, "elong": 5.6},
    "ldn": {"b": BODIES, "ob": [-0.97, 0.20, 0.09], "sc": [-0.76, -0.60, -0.23]},
    "atciqn": {"b": BODIES}, "aticqn": {"b": BODIES},
    "ld": {"p": [-0.76, -0.60, -0.23]}, "ldsun": {"p": [-0.37, -0.91, -0.18]},
    "tpors": {"a": 3.1, "b": -0.9, "xi": -0.03, "eta": 0.07},
    "tporv": {"v": [0.62, 0.50, 0.60], "xi": -0.03, "eta": 0.07},
    "tpxes": {"a": 1.1, "b": 0.7, "a0": 1.0, "b0": 0.5},
    "tpxev": {"v": [0.6, 0.5, 0.62], "v0": [0.62, 0.5, 0.6]},
    "tpsts": {"xi": 0.0, "eta": 0.0},
    "gc2gde": {"a": 6378136.6, "f": 0.0033528106647474807},
    "gd2gce": {"a": 6378136.6, "f": 0.0033528106647474807},
    "rx": {"phi": 0.3456789}, "ry": {"theta": 0.3456789}, "rz": {"psi": 0.3456789},
    "s2p": {"r": 2.0}, "s2pv": {"r": 2.0, "td": 0.1, "pd": -0.2, "rd": 0.3},
    "s2c": {"theta": 3.0123, "phi": -0.999},
    "pvu": {"dt": 2.5}, "pvup": {"dt": 2.5},
    "sxp": {"s": 2.0}, "sxpv": {"s": 2.0}, "s2xpv": {"s1": 2.0, "s2": 0.5},
    "apco": {"x": 0.0007, "y": 0.00004, "s": -0.0000009, "theta": 1.6,
             "elong": -0.5, "phi": 0.8, "hm": 1000.0, "sp": -3e-5},
    "apci": {"x": 0.0007, "y": 0.00004, "s": -0.0000009},
    "pvtob": {"theta": 1.6},
    "eform": {"n": 1}, "gc2gd": {"n": 1}, "gd2gc": {"n": 1},
    "apcs13": {"pv": [[-1.8e-3, 2.4e-3, 1.1e-3], [-7.8e-5, -3.4e-5, -1.5e-5]]},
    "plan94": {"np": 3},
    "c2ixys": {"s": -0.0000009},
    "eors": {"s": -0.0000009},
    "ee00": {"epsa": 0.4090, "dpsi": -9.6e-6},
    "numat": {"epsa": 0.4090, "dpsi": -9.6e-6, "deps": -4.0e-5},
    "fw2m": {"gamb": -0.0000253, "phib": 0.4090, "psi": -0.0000451, "eps": 0.4090},
    "fw2xy": {"gamb": -0.0000253, "phib": 0.4090, "psi": -0.0000451, "eps": 0.4090},
    "dat": {"iy": 2006, "im": 1, "id": 1, "fd": 0.5},
    "epb2jd": {"epb": 1957.3}, "epj2jd": {"epj": 2000.0}, "epb": {}, "epj": {},
    "pmpx": {"pmt": 8.5, "pob": [-0.9, 0.4, 0.1]},
}
# a/b as 3-vectors, pv-vectors, 3x3 matrices
for _n in ("pap", "pdp", "pmp", "ppp", "pxp", "sepp", "ppsp"):
    _UNIQUE.setdefault(_n, {}).update(a=[2.0, 2.0, 3.0], b=[1.0, 3.0, 4.0])
_UNIQUE["ppsp"]["s"] = 5.0
for _n in ("pvdpv", "pvmpv", "pvppv", "pvxpv"):
    _UNIQUE[_n] = dict(a=[[2.0, 2.0, 3.0], [6.0, 0.0, 4.0]], b=[[1.0, 3.0, 4.0], [0.0, 2.0, 8.0]])
_UNIQUE["rxr"] = dict(a=_R, b=[[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
_UNIQUE["apcs"] = {"date1": _JD1, "date2": _JD2,
                   "pv": [[-1.8e-3, 2.4e-3, 1.1e-3], [-7.8e-5, -3.4e-5, -1.5e-5]]}


def _input_names(name: str) -> list[str]:
    doc = getattr(erfa, name).__doc__.partition("Parameters\n")[2].partition("Returns\n")[0]
    return re.findall(r"^(\w+) : ", doc, re.M)[: getattr(erfa.ufunc, name).nin]


EXAMPLES = {}
for _name in dir(erfa):
    if hasattr(erfa.ufunc, _name) and callable(getattr(erfa, _name)):
        _spec = {**DEFAULTS, **_UNIQUE.get(_name, {})}
        EXAMPLES[_name] = {n: _spec[n] for n in _input_names(_name)}
