"""AstroAPI: the IAU SOFA routines (via pyerfa) as a FastAPI service.

Run:  uvicorn main:app --reload      (from the astroapi folder)
Docs: http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import astrometry, earth, eop, matrix, miscellaneous, sky, time

GROUPS = {"matrix": matrix, "time": time, "earth": earth,
          "astrometry": astrometry, "miscellaneous": miscellaneous, "eop": eop, "sky": sky}

app = FastAPI(
    title="AstroAPI",
    version="1.0.0",
    description="IAU SOFA / ERFA functions (pyerfa) grouped by SOFA subject. "
    "POST a JSON object whose keys are the ERFA argument names.",
)

# Public, credential-free API: allow browser calls from any origin.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for module in GROUPS.values():
    app.include_router(module.router)


@app.get("/", tags=["Root"])
def root():
    return {"name": app.title, "groups": {g: f"/{g}/" for g in GROUPS}}
