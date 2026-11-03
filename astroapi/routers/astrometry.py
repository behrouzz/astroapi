"""SOFA Astrometry Tools (58 functions)."""
from core import build_router

FUNCTIONS = """
    ab apcg apcg13 apci apci13 apco apco13 apcs apcs13 aper aper13 apio apio13 atcc13
    atccq atci13 atciq atciqn atciqz atco13 atic13 aticq aticqn atio13 atioq atoc13
    atoi13 atoiq eceq06 ecm06 epv00 eqec06 fk425 fk45z fk524 fk52h fk54z fk5hip fk5hz
    g2icrs h2fk5 hfk5z icrs2g ld ldn ldsun lteceq ltecm lteqec moon98 plan94 pmpx pmsafe
    pvstar pvtob refco starpm starpv
""".split()

router = build_router("astrometry", "SOFA Astrometry Tools", FUNCTIONS)
