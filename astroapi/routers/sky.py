"""Sky endpoints: the sky matrix (ICRS to local N,E,Zenith) and the Sun/Moon/planets."""
import warnings

import erfa
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from solsys import solar_system

router = APIRouter(prefix="/sky", tags=["Sky Matrix"])

# Paris, 2024-05-02 21:37:50 UTC; dut1/xp/yp from the IERS EOP of that instant (xp, yp in rad).
EXAMPLE = {
    "utc_year": 2024, "utc_month": 5, "utc_day": 2,
    "utc_hour": 21, "utc_minute": 37, "utc_second": 50.0,
    "lat_deg": 48.8566, "lon_deg": 2.3522,
    "dut1": -0.01803119438657428,
    "xp": 0.0069811804398159285 * erfa.DAS2R,
    "yp": 0.40801708148148286 * erfa.DAS2R,
}


class SkyMatrixRequest(BaseModel):
    utc_year: int = Field(description="UTC year")
    utc_month: int = Field(ge=1, le=12, description="UTC month (1-12)")
    utc_day: int = Field(ge=1, le=31, description="UTC day of month")
    utc_hour: int = Field(ge=0, le=23, description="UTC hour")
    utc_minute: int = Field(ge=0, le=59, description="UTC minute")
    utc_second: float = Field(ge=0, lt=61, description="UTC seconds (may include a fraction)")
    lat_deg: float = Field(ge=-90, le=90, description="Geodetic latitude of the observer (degrees, north +)")
    lon_deg: float = Field(ge=-360, le=360, description="Longitude of the observer (degrees, east +)")
    dut1: float = Field(0.0, description="UT1-UTC in seconds (see `/eop/get_eop`)")
    xp: float = Field(0.0, description="Polar motion x in radians (see `/eop/get_eop`; arcsec x 4.848e-6)")
    yp: float = Field(0.0, description="Polar motion y in radians")

    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE]})


def sky_matrix(b: SkyMatrixRequest) -> list[list[float]]:
    # 1. UTC calendar date -> two-part SOFA Julian Date
    utc1, utc2 = erfa.dtf2d("UTC", b.utc_year, b.utc_month, b.utc_day,
                            b.utc_hour, b.utc_minute, b.utc_second)
    # 2. TT (precession-nutation) and UT1 (Earth rotation) dates
    tai1, tai2 = erfa.utctai(utc1, utc2)
    tt1, tt2 = erfa.taitt(tai1, tai2)
    ut11, ut12 = erfa.utcut1(utc1, utc2, b.dut1)
    # 3. Celestial-to-terrestrial matrix (IAU 2006/2000A)
    r_c2t = erfa.c2t06a(tt1, tt2, ut11, ut12, b.xp, b.yp)
    # 4. Terrestrial (ITRS) -> local horizon rotation: rows are North, East, Zenith
    phi, lam = np.deg2rad(b.lat_deg), np.deg2rad(b.lon_deg)
    sin_p, cos_p, sin_l, cos_l = np.sin(phi), np.cos(phi), np.sin(lam), np.cos(lam)
    r_site = np.array([
        [-sin_p * cos_l, -sin_p * sin_l, cos_p],
        [-sin_l, cos_l, 0.0],
        [cos_p * cos_l, cos_p * sin_l, sin_p],
    ])
    # 5. Combined matrix
    return (r_site @ r_c2t).tolist()


_RESPONSE_EXAMPLE = {"matrix": sky_matrix(SkyMatrixRequest(**EXAMPLE)), "warnings": []}


@router.post(
    "/skymatrix",
    summary="ICRS to local [North, East, Zenith] rotation matrix",
    description="""Returns a single 3x3 matrix **M** that turns an ICRS unit vector `[x, y, z]`
directly into a local topocentric vector `[North, East, Zenith]` for an observer at a given
UTC time and place.

**Computation**
1. UTC calendar date -> two-part Julian Date (`erfa.dtf2d`).
2. UTC -> TAI -> TT (`utctai`, `taitt`) and UTC -> UT1 using `dut1` (`utcut1`).
3. Celestial-to-terrestrial matrix `R_C2T` (`erfa.c2t06a`, IAU 2006/2000A precession-nutation,
   Earth rotation and polar motion `xp`, `yp`).
4. Site matrix `R_site` from geodetic latitude/longitude; its rows are the local North, East and
   Zenith axes expressed in the Earth-fixed frame.
5. `M = R_site @ R_C2T`.

**Using the result:** for an ICRS direction `v` (unit vector), `M @ v = [north, east, zenith]`.
The zenith component is the sine of the altitude; azimuth (from north through east) is
`atan2(east, north)`. The matrix is purely geometric: no aberration, light deflection or
refraction is applied.

`dut1` (seconds) and `xp`, `yp` (radians) are optional and default to 0; get them from
`/eop/get_eop` for full accuracy (`xp`, `yp` there are in arcseconds: multiply by 4.848137e-6).""",
    responses={200: {"content": {"application/json": {"example": _RESPONSE_EXAMPLE}}}},
)
def skymatrix(body: SkyMatrixRequest):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            matrix = sky_matrix(body)
        except erfa.ErfaError as exc:
            raise HTTPException(422, f"ERFA error: {exc}")
        except ValueError as exc:
            raise HTTPException(422, f"Invalid input: {exc}")
    return {"matrix": matrix, "warnings": [str(w.message) for w in caught]}


# ---------------------------------------------------------------------------------------
# Sun, Moon and planets
# ---------------------------------------------------------------------------------------
SOLAR_EXAMPLE = {
    "utc_year": 2026, "utc_month": 11, "utc_day": 6,
    "utc_hour": 3, "utc_minute": 0, "utc_second": 0.0,
    "lat_deg": 43.65323, "lon_deg": -79.38318,
}


class SolarSystemRequest(BaseModel):
    utc_year: int = Field(description="UTC year")
    utc_month: int = Field(ge=1, le=12, description="UTC month (1-12)")
    utc_day: int = Field(ge=1, le=31, description="UTC day of month")
    utc_hour: int = Field(ge=0, le=23, description="UTC hour")
    utc_minute: int = Field(ge=0, le=59, description="UTC minute")
    utc_second: float = Field(0.0, ge=0, lt=61, description="UTC seconds (may include a fraction)")
    lat_deg: float = Field(ge=-90, le=90, description="Geodetic latitude of the observer (degrees, north +)")
    lon_deg: float = Field(ge=-360, le=360, description="Longitude of the observer (degrees, east +)")
    height_m: float = Field(0.0, description="Height above the ellipsoid in metres")
    dut1: float = Field(0.0, description="UT1-UTC in seconds (see `/eop/get_eop`)")
    xp: float = Field(0.0, description="Polar motion x in radians")
    yp: float = Field(0.0, description="Polar motion y in radians")
    light_time: bool = Field(True, description="Correct for light travel time")

    model_config = ConfigDict(json_schema_extra={"examples": [SOLAR_EXAMPLE]})


def _solar_system(b: SolarSystemRequest) -> dict:
    return solar_system(b.utc_year, b.utc_month, b.utc_day, b.utc_hour, b.utc_minute, b.utc_second,
                        b.lon_deg, b.lat_deg, b.height_m, b.dut1, b.xp, b.yp, b.light_time)


@router.post(
    "/solarsystem",
    summary="Sun, Moon and planets: position, phase, magnitude, size",
    description="""Position and appearance of the Sun, Moon and the seven planets (Mercury, Venus,
Mars, Jupiter, Saturn, Uranus, Neptune) for an observer at a given UTC time and place.
Built on ERFA: `epv00` (Earth/Sun), `moon98` (Moon), `plan94` (planets), `apco13`/`atciq`/`atioq`
(observer, aberration, light deflection, horizon coordinates).

**Fields**
- all bodies: `ra`, `dec`: geocentric ICRS right ascension (0-360) and declination (degrees);
  `alt`, `az`: topocentric altitude and azimuth (degrees, azimuth from North through East,
  **no atmospheric refraction**).
- Moon and planets: `elongation` (Sun-observer-body angle, degrees), `phase_angle`
  (Sun-body-Earth, degrees; for the Moon approximated as 180 - elongation) and `illumination`
  (illuminated fraction of the disk, percent).
- planets: `magnitude` (approximate apparent visual magnitude; typically within ~0.2 mag of JPL
  Horizons, more for Mercury at extreme phase; Saturn includes a ring-opening correction) and
  `angular_diameter` (equatorial, arcseconds).

**Accuracy and notes:** light-time corrected (set `light_time=false` to disable). The planets use
`plan94` (about 1 arcminute formally; in practice alt/az agree with JPL Horizons within ~25
arcsec for the example epochs; Sun, Moon and inner planets within a few arcsec). TT stands in for TDB.
`dut1`, `xp`, `yp` default to 0 (take them from `/eop/get_eop`); their effect on alt/az is tiny.""",
    responses={200: {"content": {"application/json": {"example": {
        "bodies": solar_system(2026, 11, 6, 3, 0, 0.0, -79.38318, 43.65323), "warnings": []}}}}},
)
def solarsystem(body: SolarSystemRequest):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            bodies = _solar_system(body)
        except erfa.ErfaError as exc:
            raise HTTPException(422, f"ERFA error: {exc}")
        except ValueError as exc:
            raise HTTPException(422, f"Invalid input: {exc}")
    # the same ERFA warning is raised once per body: report each message once
    return {"bodies": bodies, "warnings": list(dict.fromkeys(str(w.message) for w in caught))}
