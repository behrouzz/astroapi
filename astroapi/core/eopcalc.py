import erfa
from iers import EOP
from datetime import datetime


def utc_to_eop(t_str):
    t = datetime.strptime(t_str, '%Y-%m-%dT%H:%M:%S')

    utc1, utc2 = erfa.dtf2d(
        "UTC",
        t.year, t.month, t.day,
        t.hour, t.minute, t.second
    )

    utc_jd = utc1 + utc2

    eop = EOP()

    dc = eop.get_eop(utc_jd)
    #dc = {k:v.item() for (k, v) in dc.items()}

    return dc