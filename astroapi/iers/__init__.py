"""IERS Earth Orientation Parameters and leap seconds (numpy + stdlib only).

A pandas-free rewrite of https://github.com/behrouzz/iers with the same public API
(``EOP(kind).get_eop(t)``, ``leap_seconds(t)``).
"""
from .core import EOP
from .time import any2mjd, leap_seconds

__all__ = ["EOP", "leap_seconds", "any2mjd"]
