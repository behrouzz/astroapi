# AstroAPI

IAU SOFA routines (via [pyerfa](https://pyerfa.readthedocs.io/)) as a FastAPI service, plus two
extra groups of endpoints (Earth Orientation Parameters and a sky matrix) that are **not part of
SOFA**. All 247 ERFA functions are exposed as `POST /<group>/<name>`, each with a ready-to-run
example in Swagger.

## Endpoint groups

| Group | Router | Origin | Subject |
|---|---|---|---|
| `/matrix` | `routers/matrix.py` | **SOFA** | SOFA Vector/Matrix Library |
| `/time` | `routers/time.py` | **SOFA** | SOFA Time Scale and Calendar Tools |
| `/earth` | `routers/earth.py` | **SOFA** | SOFA Tools for Earth Attitude |
| `/astrometry` | `routers/astrometry.py` | **SOFA** | SOFA Astrometry Tools |
| `/miscellaneous` | `routers/miscellaneous.py` | **SOFA** | SOFA Miscellaneous Tools |
| `/eop` | `routers/eop.py` | Not SOFA, added by Behrouz Safari | Earth Orientation Parameters (`get_eop`) and `leap_seconds` |
| `/sky` | `routers/sky.py` | Not SOFA, added by Behrouz Safari | `skymatrix`: ICRS to local [North, East, Zenith] rotation matrix |

The groups `/matrix`, `/time`, `/earth`, `/astrometry` and `/miscellaneous` are from SOFA
(the IAU Standards of Fundamental Astronomy, through pyerfa/ERFA). The groups `/eop` and `/sky`
are not part of SOFA: they were added by Behrouz Safari.

## Live deployment

The API is deployed on Vercel at **https://astroapirepo.vercel.app**, and every endpoint
(with request and response examples you can run with *Try it out*) is listed in the Swagger UI at
**https://astroapirepo.vercel.app/docs**. CORS is open, so it can be called from any web page.

## Run

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd astroapi
uvicorn main:app --reload
```

Swagger UI (local): http://127.0.0.1:8000/docs

## Request format

POST a JSON object whose keys are the ERFA argument names; scalars and nested lists
(vectors, matrices, batches) are accepted. Example, `POST /time/utctai`:

```json
{"utc1": 2400000.5, "utc2": 53736.0}
```

## Sky matrix: `POST /sky/skymatrix` (not SOFA; added by Behrouz Safari)

Returns one 3x3 matrix **M** that turns an ICRS unit vector `[x, y, z]` into a local
topocentric vector `[North, East, Zenith]` for an observer at a given UTC time and place:
`M = R_site @ R_C2T`, where `R_C2T` is `erfa.c2t06a` (IAU 2006/2000A, UT1 from `dut1`, polar motion
`xp`, `yp` in radians) and `R_site` is built from the geodetic latitude and longitude.
Then `M @ v = [north, east, zenith]`; zenith is the sine of the altitude and the azimuth is
`atan2(east, north)`. It is purely geometric (no aberration, light deflection or refraction).
Get `dut1`, `xp`, `yp` from `/eop/get_eop` (its `xp`, `yp` are in arcseconds: multiply by 4.848137e-6).

```json
{"utc_year": 2024, "utc_month": 5, "utc_day": 2, "utc_hour": 21, "utc_minute": 37, "utc_second": 50.0,
 "lat_deg": 48.8566, "lon_deg": 2.3522,
 "dut1": -0.01803119438657428, "xp": 3.384e-8, "yp": 1.978e-6}
```

The response is `{"matrix": [[...], [...], [...]], "warnings": []}` (rows are North, East, Zenith).

## Checking the examples

`python check_examples.py` (from `astroapi/`) calls every endpoint with its example and
compares the result with a direct `erfa` call, and checks the EOP endpoints against the IERS README and
`/sky/skymatrix` against its reference implementation.

## Earth orientation parameters (`/eop`, not SOFA; added by Behrouz Safari)

`astroapi/iers/` is a numpy-only rewrite of [behrouzz/iers](https://github.com/behrouzz/iers).
IERS data files are downloaded on first use into `astroapi/iers/data/` (override with the
`IERS_DATA_DIR` environment variable) and refreshed when older than 7 days.
