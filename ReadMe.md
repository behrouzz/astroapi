# AstroAPI

IAU SOFA routines (via [pyerfa](https://pyerfa.readthedocs.io/)) and IERS Earth Orientation
Parameters as a FastAPI service. All 247 ERFA functions are exposed as `POST /<group>/<name>`
with a ready-to-run example in Swagger.

| Group | Router | Subject |
|---|---|---|
| `/matrix` | `routers/matrix.py` | SOFA Vector/Matrix Library |
| `/time` | `routers/time.py` | SOFA Time Scale and Calendar Tools |
| `/earth` | `routers/earth.py` | SOFA Tools for Earth Attitude |
| `/astrometry` | `routers/astrometry.py` | SOFA Astrometry Tools |
| `/miscellaneous` | `routers/miscellaneous.py` | SOFA Miscellaneous Tools |
| `/eop` | `routers/eop.py` | Earth Orientation Parameters (`get_eop`) and `leap_seconds` |

## Run

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd astroapi
uvicorn main:app --reload
```

Swagger UI: http://127.0.0.1:8000/docs

## Request format

POST a JSON object whose keys are the ERFA argument names; scalars and nested lists
(vectors, matrices, batches) are accepted. Example, `POST /time/utctai`:

```json
{"utc1": 2400000.5, "utc2": 53736.0}
```

## Checking the examples

`python check_examples.py` (from `astroapi/`) calls every endpoint with its example and
compares the result with a direct `erfa` call, and checks the EOP endpoints against the IERS README.

## Earth orientation parameters

`astroapi/iers/` is a numpy-only rewrite of [behrouzz/iers](https://github.com/behrouzz/iers).
IERS data files are downloaded on first use into `astroapi/iers/data/` (override with the
`IERS_DATA_DIR` environment variable) and refreshed when older than 7 days.
