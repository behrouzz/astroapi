"""Vercel entrypoint: expose the FastAPI app that lives in the astroapi/ folder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "astroapi"))

from main import app  # noqa: E402,F401
