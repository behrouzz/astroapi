"""Generic machinery that exposes pyerfa (IAU SOFA) functions as FastAPI endpoints.

Every function is published as ``POST /<group>/<name>`` taking a JSON body whose keys are
the ERFA argument names, and returning ``{"function", "result", "warnings"}``.
Scalars and nested lists (vectors / matrices / arrays of values) are all accepted.
"""
import inspect
import math
import re
import warnings
from typing import Any

import erfa
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import ConfigDict, create_model

from examples import EXAMPLES

_PARAM_RE = re.compile(r"^(\w+) : (.+)$", re.M)


class FunctionInfo:
    """Argument/return metadata parsed from an ERFA function's docstring."""

    def __init__(self, name: str):
        self.name = name
        self.func = getattr(erfa, name)
        self.ufunc = getattr(erfa.ufunc, name)
        doc = inspect.cleandoc(self.func.__doc__ or "")  # <3.13 keeps docstring indentation
        head = re.split(r"\n(?:Parameters|Returns|Notes)\n", doc)[0]
        self.summary = " ".join(head.split())
        params = doc.partition("Parameters\n")[2].partition("Returns\n")[0]
        returns, _, notes = doc.partition("Returns\n")[2].partition("Notes\n")
        self.inputs = _PARAM_RE.findall(params)
        self.outputs = _PARAM_RE.findall(returns)
        self.notes = notes.replace("-----\n", "", 1).strip()


def _to_structured(value: Any, dtype: np.dtype) -> np.ndarray:
    """dict (or list of dicts) -> numpy structured array of the given dtype."""
    single = isinstance(value, dict)
    rows = [value] if single else value
    out = np.zeros(len(rows), dtype=dtype)
    for i, row in enumerate(rows):
        for field in dtype.names:
            if field not in row:
                continue
            val = row[field]
            if dtype[field].names:  # nested pv: {"p": [...], "v": [...]} or [[p],[v]]
                p, v = (val["p"], val["v"]) if isinstance(val, dict) else val
                out[i][field]["p"], out[i][field]["v"] = p, v
            else:
                out[i][field] = np.asarray(val, dtype=float)
    return out[0] if single else out


def _to_input(value: Any, kind: str) -> Any:
    if kind == "int array":
        return np.asarray(value, dtype=np.int32)
    if kind in ("char array", "const char array"):
        return np.asarray(value, dtype="S")
    if kind == "eraASTROM array":
        return _to_structured(value, erfa.dt_eraASTROM)
    if kind == "eraLDBODY array":
        return _to_structured(value, erfa.dt_eraLDBODY)
    return np.asarray(value, dtype=float)


def _as_pv(a: Any) -> Any:
    """(...,2,3) float array -> ERFA pv structured array (position, velocity)."""
    if isinstance(a, np.ndarray) and a.dtype.names is None and a.shape[-2:] == (2, 3):
        pv = np.empty(a.shape[:-2], dtype=erfa.dt_pv)
        pv["p"], pv["v"] = a[..., 0, :], a[..., 1, :]
        return pv
    return a


def _call(info: FunctionInfo, args: list) -> Any:
    """Call the ERFA function; position-velocity inputs are retried as pv structs."""
    try:
        return info.func(*args)
    except TypeError:
        return info.func(*[_as_pv(a) for a in args])


def to_json(obj: Any) -> Any:
    """Recursively convert numpy results to JSON-safe python (NaN/inf -> null)."""
    if isinstance(obj, (tuple, list)):
        return [to_json(o) for o in obj]
    if isinstance(obj, np.void) or (isinstance(obj, np.ndarray) and obj.dtype.names):
        if obj.ndim == 0:
            return {n: to_json(obj[n]) for n in obj.dtype.names}
        return [to_json(o) for o in obj]
    if isinstance(obj, np.ndarray):
        return to_json(obj.tolist())
    if isinstance(obj, (bytes, np.bytes_)):
        return obj.decode("ascii", "replace")
    if isinstance(obj, np.generic):
        return to_json(obj.item())
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    return obj


def execute(info: FunctionInfo, payload: dict) -> dict:
    """Run one ERFA function on a JSON payload; raises HTTPException(422) on bad input."""
    in_params = info.inputs[: info.ufunc.nin]
    out_names = ["result" if n == "c_retval" else n for n, _ in info.outputs]
    try:
        args = [_to_input(payload[n], k) for n, k in in_params]
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, f"Bad argument: {exc}")
    names = out_names
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            res = _call(info, args)
        except erfa.ErfaError as exc:
            raise HTTPException(422, f"ERFA error: {exc}")
        except KeyError:
            # pyerfa has no status table for functions whose return code is a count
            # (tpors/tporv): call the raw ufunc and expose the count as "nsol".
            res = info.ufunc(*args)
            names = out_names + ["nsol"]
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, f"Invalid input shape/type: {exc}")
    if len(names) == 1:
        res = (res,)
    return {
        "function": info.name,
        "result": dict(zip(names, to_json(res))),
        "warnings": [str(w.message) for w in caught],
    }


def add_function(router: APIRouter, name: str) -> None:
    info = FunctionInfo(name)
    in_params = info.inputs[: info.ufunc.nin]
    out_names = ["result" if n == "c_retval" else n for n, _ in info.outputs]
    example = EXAMPLES[name]
    Body = create_model(
        f"{name}_in",
        __config__=ConfigDict(extra="forbid", json_schema_extra={"examples": [example]}),
        **{n: (Any, ...) for n, _ in in_params},
    )
    description = (
        f"{info.summary}\n\n**Inputs:** "
        + ", ".join(f"`{n}` ({k.replace(' array', '')})" for n, k in in_params)
        + "\n\n**Outputs:** "
        + ", ".join(f"`{n}`" for n in out_names)
        + (f"\n\n```\n{info.notes}\n```" if info.notes else "")
    )

    def endpoint(body: Body):  # type: ignore[valid-type]
        return execute(info, body.model_dump())

    router.add_api_route(
        f"/{name}",
        endpoint,
        methods=["POST"],
        name=name,
        summary=f"erfa.{name}",
        description=description,
        responses={200: {"content": {"application/json": {"example": execute(info, example)}}}},
    )


def build_router(group: str, title: str, names: list[str]) -> APIRouter:
    """Build a router with one endpoint per ERFA function plus a function index."""
    router = APIRouter(prefix=f"/{group}", tags=[title])
    names = sorted(names)

    @router.get("/", summary=f"List {title} functions")
    def list_functions():
        return {
            "group": title,
            "functions": [{"name": n, "summary": FunctionInfo(n).summary} for n in names],
        }

    for n in names:
        add_function(router, n)
    return router
