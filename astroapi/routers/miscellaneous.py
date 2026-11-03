"""SOFA Miscellaneous Tools (14 functions)."""
from core import build_router

FUNCTIONS = """
    ae2hd eform gc2gd gc2gde gd2gc gd2gce hd2ae hd2pa tpors tporv tpsts tpstv tpxes
    tpxev
""".split()

router = build_router("miscellaneous", "SOFA Miscellaneous Tools", FUNCTIONS)
