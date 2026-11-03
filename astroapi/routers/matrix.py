"""SOFA Vector/Matrix Library (55 functions)."""
from core import build_router

FUNCTIONS = """
    a2af a2tf af2a anp anpm c2s cp cpv cr d2tf ir p2pv p2s pap pas pdp pm pmp pn ppp
    ppsp pv2p pv2s pvdpv pvm pvmpv pvppv pvu pvup pvxpv pxp rm2v rv2m rx rxp rxpv rxr ry
    rz s2c s2p s2pv s2xpv sepp seps sxp sxpv tf2a tf2d tr trxp trxpv zp zpv zr
""".split()

router = build_router("matrix", "SOFA Vector/Matrix Library", FUNCTIONS)
