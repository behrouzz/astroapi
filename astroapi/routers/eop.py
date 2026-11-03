"""Earth Orientation Parameters and leap seconds (via the local ``iers`` package)."""
from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from iers import EOP, leap_seconds

router = APIRouter(prefix="/eop", tags=["Earth Orientation Parameters"])

TimeValue = float | str  # Julian Date (float) or a date-time string


@lru_cache(maxsize=4)
def _eop(kind: int) -> EOP:
    """One EOP instance per data kind (loads, and downloads if stale, the IERS table)."""
    return EOP(kind=kind)


class EopRequest(BaseModel):
    t: TimeValue = Field(description="Julian Date (number) or date-time string, e.g. '2024-05-02 21:37:50'")
    kind: Literal[1, 2, 3, 4] = Field(
        1, description="1: finals.all (IAU2000, Bulletins A/B); 2: EOP 14 C04; 3: EOP C01; 4: NAO")

    model_config = ConfigDict(json_schema_extra={"examples": [
        {"t": 2460556.5, "kind": 1},
        {"t": "2024-05-02 21:37:50", "kind": 1},
    ]})


class LeapRequest(BaseModel):
    t: TimeValue = Field(description="UTC as Julian Date (number) or date-time string")

    model_config = ConfigDict(json_schema_extra={"examples": [
        {"t": "2012-01-15 15:40:33"},
        {"t": 2460556.5},
    ]})


def get_eop(t: TimeValue, kind: int = 1) -> dict:
    """Interpolated EOP at ``t`` plus the IERS bulletin used (kind 1 only)."""
    values, bulletin = _eop(kind).lookup(t)
    return {"eop": values, "bulletin": bulletin, "kind": kind}


@router.post(
    "/get_eop",
    summary="Earth orientation parameters at a given time",
    description="Polar motion `px`, `py` (arcsec), `ut1_utc` (s) and celestial pole offsets "
    "`dx`, `dy` (mas), interpolated from the IERS tables (`iers.EOP(kind).get_eop(t)`). "
    "`kind` 3 and 4 return other columns (e.g. `ut1_tai`, `lod`).",
    responses={200: {"content": {"application/json": {"example": {
        "eop": {"px": 0.0069811804398159285, "py": 0.40801708148148286,
                "ut1_utc": -0.01803119438657428, "dx": 0.2808885416666599,
                "dy": -0.16251909722223354},
        "bulletin": "B", "kind": 1}}}}},
)
def eop_endpoint(body: EopRequest):
    try:
        return get_eop(body.t, body.kind)
    except HTTPException:
        raise
    except Exception as exc:  # bad date string, outside table range, download failure...
        raise HTTPException(422, f"Could not compute EOP: {exc}")


@router.post(
    "/leap_seconds",
    summary="Leap seconds (TAI-UTC) at a given UTC time",
    description="Number of leap seconds (`iers.leap_seconds(t)`); 0 before 1972-01-01.",
    responses={200: {"content": {"application/json": {"example": {"leap_seconds": 34}}}}},
)
def leap_seconds_endpoint(body: LeapRequest):
    try:
        return {"leap_seconds": leap_seconds(body.t)}
    except Exception as exc:
        raise HTTPException(422, f"Could not compute leap seconds: {exc}")
