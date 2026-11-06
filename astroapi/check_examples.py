"""Verify every example: POST it to the endpoint and compare with a direct erfa call.

Run from the astroapi folder:  python check_examples.py
"""
import math
import sys
import warnings

import erfa
import numpy as np
from fastapi.testclient import TestClient

from examples import EXAMPLES
from main import GROUPS
from routers import eop as eop_router
from routers import sky as sky_router


def direct(name: str, body: dict):
    """Call erfa.<name> directly with a straightforward conversion of the example."""
    def conv(v):
        if isinstance(v, str):
            return np.array(v.encode())
        if isinstance(v, dict) and "bm1" in v:  # eraASTROM
            a = np.zeros((), dtype=erfa.dt_eraASTROM)
            for k, x in v.items():
                a[k] = x
            return a
        if isinstance(v, list) and v and isinstance(v[0], dict):  # eraLDBODY list
            a = np.zeros(len(v), dtype=erfa.dt_eraLDBODY)
            for i, d in enumerate(v):
                a[i]["bm"], a[i]["dl"] = d["bm"], d["dl"]
                a[i]["pv"]["p"], a[i]["pv"]["v"] = d["pv"]["p"], d["pv"]["v"]
            return a
        arr = np.asarray(v)
        if arr.shape == (2, 3):  # position-velocity
            pv = np.zeros((), dtype=erfa.dt_pv)
            pv["p"], pv["v"] = arr[0], arr[1]
            return pv
        return arr.astype(np.int32) if arr.dtype.kind == "i" else arr

    func = getattr(erfa, name)
    args = [conv(v) for v in body.values()]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return func(*args)
    except KeyError:  # tpors/tporv: pyerfa lacks a status table, use the raw ufunc
        return getattr(erfa.ufunc, name)(*args)


def flatten(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from flatten(v)
    elif isinstance(x, (list, tuple)):
        for i in x:
            yield from flatten(i)
    elif isinstance(x, np.ndarray) and x.dtype.names:
        for n in x.dtype.names:
            yield from flatten(x[n])
    elif isinstance(x, np.void):
        for n in x.dtype.names:
            yield from flatten(x[n])
    elif isinstance(x, np.ndarray):
        yield from flatten(x.tolist())
    elif isinstance(x, (bytes, np.bytes_)):
        yield x.decode()
    elif isinstance(x, np.generic):
        yield x.item()
    else:
        yield x


def same(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None:
            return (a is None or not math.isfinite(a)) and (b is None or not math.isfinite(b))
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-14)
    return a == b


def main() -> int:
    client = TestClient(next(iter(GROUPS.values())).router and __import__("main").app)
    prefix = {n: g for g, m in GROUPS.items() for n in getattr(m, "FUNCTIONS", [])}
    bad = 0
    for name, body in sorted(EXAMPLES.items()):
        r = client.post(f"/{prefix[name]}/{name}", json=body)
        if r.status_code != 200:
            print(f"FAIL {name}: HTTP {r.status_code} {r.text[:150]}")
            bad += 1
            continue
        api = list(flatten(list(r.json()["result"].values())))
        exp = [None if isinstance(v, float) and not math.isfinite(v) else v
               for v in flatten(direct(name, body))]
        if name in ("tpors", "tporv"):
            pass  # API also reports "nsol", which the direct ufunc call returns last
        if len(api) != len(exp) or not all(same(a, b) for a, b in zip(api, exp)):
            print(f"MISMATCH {name}: api={api[:4]} direct={exp[:4]}")
            bad += 1
    print(f"{len(EXAMPLES) - bad}/{len(EXAMPLES)} ERFA examples OK")
    return bad + check_eop(client) + check_sky(client) + check_solarsystem(client)


README_EOP = {"px": 0.0069811804398159285, "py": 0.40801708148148286,
              "ut1_utc": -0.01803119438657428, "dx": 0.2808885416666599,
              "dy": -0.16251909722223354}  # iers README, '2024-05-02 21:37:50', kind=1, bulletin B


def reference_sky_matrix(utc_year, utc_month, utc_day, utc_hour, utc_minute, utc_second,
                         lat_deg, lon_deg, dut1=0.0, xp=0.0, yp=0.0):
    """The original reference implementation of the sky matrix (kept verbatim for checking)."""
    utc1, utc2 = erfa.dtf2d("UTC", utc_year, utc_month, utc_day, utc_hour, utc_minute, utc_second)
    tai1, tai2 = erfa.utctai(utc1, utc2)
    tt1, tt2 = erfa.taitt(tai1, tai2)
    ut11, ut12 = erfa.utcut1(utc1, utc2, dut1)
    r_c2t = erfa.c2t06a(tt1, tt2, ut11, ut12, xp, yp)
    phi, lam = np.deg2rad(lat_deg), np.deg2rad(lon_deg)
    sin_p, cos_p, sin_l, cos_l = np.sin(phi), np.cos(phi), np.sin(lam), np.cos(lam)
    r_site = np.array([[-sin_p * cos_l, -sin_p * sin_l, cos_p],
                       [-sin_l, cos_l, 0.0],
                       [cos_p * cos_l, cos_p * sin_l, sin_p]])
    return (r_site @ r_c2t).tolist()


def check_sky(client) -> int:
    """/sky/skymatrix vs. the reference implementation, for the Swagger example and others."""
    cases = [sky_router.EXAMPLE,
             dict(utc_year=2006, utc_month=1, utc_day=1, utc_hour=0, utc_minute=0, utc_second=0.0,
                  lat_deg=-33.9, lon_deg=151.2),
             dict(utc_year=2016, utc_month=12, utc_day=31, utc_hour=23, utc_minute=59,
                  utc_second=60.5, lat_deg=0.0, lon_deg=-120.0, dut1=0.4, xp=1e-6, yp=2e-6)]
    bad = 0
    for body in cases:
        r = client.post("/sky/skymatrix", json=body)
        want = reference_sky_matrix(*body.values())
        ok = r.status_code == 200 and np.allclose(r.json()["matrix"], want, rtol=0, atol=1e-13)
        if not ok:
            bad += 1
            print(f"FAIL skymatrix {body}: {r.status_code} {r.text[:150]}")
    print(f"{len(cases) - bad}/{len(cases)} skymatrix checks OK")
    return bad


# NASA JPL Horizons, 2026-11-06 03:00:00 UT, observer lon -79.38318 lat 43.65323 h 0 (airless):
# (azimuth, elevation, elongation S-O-T, phase S-T-O, illuminated %, angular diameter ")
HORIZONS = {
    "sun": (307.663383431, -52.229340745, None, None, None, None),
    "mercury": (313.230260779, -53.102110698, 3.4861, 168.9046, 0.93363, 9.862940),
    "venus": (341.384562520, -57.868124413, 19.8896, 152.1705, 5.78077, 56.88382),
    "moon": (9.792426125, -52.170123251, None, None, None, None),
    "mars": (46.998822910, -16.527587030, 82.5524, 37.9206, 89.44278, 6.735230),
    "jupiter": (45.390193043, -20.100515591, 78.7948, 10.5380, 99.15653, 36.36419),
    "saturn": (182.464227107, 47.422940078, 145.1799, 3.4384, 99.90975, 19.34106),
    "uranus": (101.041411486, 41.775688646, 159.2242, 1.0430, None, 3.808868),
    "neptune": (192.229317647, 45.175524329, 138.2529, 1.2610, None, 2.344258),
}
HORIZONS_MOON_GEOCENTRIC = (184.52990, -5.47725, 37.1264)  # RA, Dec, elongation (geocenter)


def check_solarsystem(client) -> int:
    """/sky/solarsystem vs. JPL Horizons (independent ephemeris) for the Swagger example."""
    r = client.post("/sky/solarsystem", json=sky_router.SOLAR_EXAMPLE)
    if r.status_code != 200:
        print(f"FAIL solarsystem: {r.status_code} {r.text[:150]}")
        return 1
    bodies, bad, total = r.json()["bodies"], 0, 0

    def fail(msg):
        nonlocal bad
        bad += 1
        print("FAIL solarsystem", msg)

    for name, (az, el, elong, phase, illu, diam) in HORIZONS.items():
        b = bodies[name]
        total += 1
        d_az = abs((b["az"] - az + 180) % 360 - 180) * math.cos(math.radians(el))
        if max(d_az, abs(b["alt"] - el)) > 40 / 3600:
            fail(f"{name} alt/az off by more than 40 arcsec: {b['alt']:.4f},{b['az']:.4f} vs {el},{az}")
        for key, ref, tol in (("elongation", elong, 0.02), ("phase_angle", phase, 0.02),
                              ("illumination", illu, 0.03), ("angular_diameter", diam, None)):
            if ref is None:
                continue
            ok = abs(b[key] - ref) <= tol if tol else abs(b[key] / ref - 1) < 0.01
            if not ok:
                fail(f"{name} {key}: {b[key]} vs Horizons {ref}")
    m, (ra, dec, elong) = bodies["moon"], HORIZONS_MOON_GEOCENTRIC
    total += 1
    if abs(m["ra"] - ra) > 0.01 or abs(m["dec"] - dec) > 0.01 or abs(m["elongation"] - elong) > 0.02:
        fail(f"moon geocentric ra/dec/elongation: {m}")
    print(f"{total - bad}/{total} solarsystem checks OK")
    return bad


def _original_iers():
    """The original pandas-based ``iers`` package from site-packages, if installed."""
    import importlib.util
    import sysconfig
    from pathlib import Path
    init = Path(sysconfig.get_paths()["purelib"]) / "iers" / "__init__.py"
    if not init.exists():
        return None
    spec = importlib.util.spec_from_file_location(
        "iers_original", init, submodule_search_locations=[str(init.parent)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["iers_original"] = mod
    spec.loader.exec_module(mod)
    return mod


def check_eop(client) -> int:
    """EOP / leap-second endpoints vs. the iers README and (if installed) the original package."""
    orig = _original_iers()
    if orig is None:
        print("(original pandas-based iers package not installed: skipping cross-check)")
    bad = total = 0

    def fail(msg):
        nonlocal bad
        bad += 1
        print("FAIL", msg)

    for body in eop_router.EopRequest.model_config["json_schema_extra"]["examples"]:
        total += 1
        r = client.post("/eop/get_eop", json=body)
        got = r.json().get("eop") if r.status_code == 200 else None
        if got is None:
            fail(f"get_eop {body}: {r.status_code} {r.text[:150]}")
            continue
        if isinstance(body["t"], str) and not all(
                math.isclose(got[k], v, rel_tol=1e-9) for k, v in README_EOP.items()):
            fail(f"get_eop {body} differs from README: {got}")
        if orig is not None:
            e = orig.EOP(kind=body["kind"])
            want = e.get_eop(body["t"])
            if got.keys() != want.keys() or not all(
                    math.isclose(got[k], float(want[k]), rel_tol=1e-9) for k in want)                     or r.json()["bulletin"] != e.bulletin:
                fail(f"get_eop {body}: api={got} original={want}")
    for kind in (2, 3):  # other tables: same columns and values as the original
        total += 1
        r = client.post("/eop/get_eop", json={"t": 2460556.5, "kind": kind})
        if r.status_code != 200:
            fail(f"get_eop kind={kind}: {r.status_code} {r.text[:150]}")
        elif orig is not None:
            want = orig.EOP(kind=kind).get_eop(2460556.5)
            got = r.json()["eop"]
            if got.keys() != want.keys() or not all(
                    math.isclose(got[k], float(want[k]), rel_tol=1e-9) for k in want):
                fail(f"get_eop kind={kind}: api={got} original={want}")
    for body in eop_router.LeapRequest.model_config["json_schema_extra"]["examples"]:
        total += 1
        r = client.post("/eop/leap_seconds", json=body)
        want = orig.leap_seconds(body["t"]) if orig else 34 if isinstance(body["t"], str) else 37
        if r.status_code != 200 or r.json()["leap_seconds"] != want:
            fail(f"leap_seconds {body}: {r.status_code} {r.text[:150]}")
    if orig is not None:  # sweep 1960-2030 daily-ish
        total += 1
        from iers import leap_seconds as mine
        if any(mine(jd) != orig.leap_seconds(jd) for jd in range(2436934, 2462502, 37)):
            fail("leap_seconds sweep differs from original")
    print(f"{total - bad}/{total} EOP checks OK")
    return bad


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
