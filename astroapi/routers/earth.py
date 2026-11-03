"""SOFA Tools for Earth Attitude (93 functions)."""
from core import build_router

FUNCTIONS = """
    bi00 bp00 bp06 bpn2xy c2i00a c2i00b c2i06a c2ibpn c2ixy c2ixys c2t00a c2t00b c2t06a
    c2tcio c2teqx c2tpe c2txy ee00 ee00a ee00b ee06a eect00 eo06a eors eqeq94 era00
    fad03 fae03 faf03 faju03 fal03 falp03 fama03 fame03 fane03 faom03 fapa03 fasa03
    faur03 fave03 fw2m fw2xy gmst00 gmst06 gmst82 gst00a gst00b gst06 gst06a gst94 ltp
    ltpb ltpecl ltpequ num00a num00b num06a numat nut00a nut00b nut06a nut80 nutm80
    obl06 obl80 p06e pb06 pfw06 pmat00 pmat06 pmat76 pn00 pn00a pn00b pn06 pn06a pnm00a
    pnm00b pnm06a pnm80 pom00 pr00 prec76 s00 s00a s00b s06 s06a sp00 xy06 xys00a xys00b
    xys06a
""".split()

router = build_router("earth", "SOFA Tools for Earth Attitude", FUNCTIONS)
