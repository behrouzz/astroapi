"""SOFA Time Scale and Calendar Tools (27 functions)."""
from core import build_router

FUNCTIONS = """
    cal2jd d2dtf dat dtdb dtf2d epb epb2jd epj epj2jd jd2cal jdcalf taitt taiut1 taiutc
    tcbtdb tcgtt tdbtcb tdbtt tttai tttcg tttdb ttut1 ut1tai ut1tt ut1utc utctai utcut1
""".split()

router = build_router("time", "SOFA Time Scale and Calendar Tools", FUNCTIONS)
