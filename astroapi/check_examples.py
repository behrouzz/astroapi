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
    return bad + check_eop(client)


README_EOP = {"px": 0.0069811804398159285, "py": 0.40801708148148286,
              "ut1_utc": -0.01803119438657428, "dx": 0.2808885416666599,
              "dy": -0.16251909722223354}  # iers README, '2024-05-02 21:37:50', kind=1, bulletin B


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
