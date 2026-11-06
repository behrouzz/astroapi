"""Sun, Moon and planets for an observer, from ERFA (epv00, moon98, plan94, apco13...).

Returns, for each body: geocentric RA/Dec (ICRS, light-time corrected), topocentric
altitude/azimuth (aberration and light deflection included, no refraction) and, for the Moon
and planets, elongation, phase angle, illuminated fraction, and for the planets also the
approximate apparent magnitude and the (equatorial) angular diameter.

Verified against NASA JPL Horizons (see check_examples.py): altitude/azimuth agree to
better than ~25 arcsec (Sun, Moon, inner planets to a few arcsec); the limit is plan94's accuracy.
"""
import erfa
import numpy as np

d2r = np.pi / 180
r2d = 180 / np.pi

BODIES = ["sun", "mercury", "venus", "moon", "mars", "jupiter", "saturn", "uranus", "neptune"]
PLANETS = ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"]
PLAN94_ID = {"mercury": 1, "venus": 2, "mars": 4, "jupiter": 5, "saturn": 6, "uranus": 7, "neptune": 8}

# Saturn's north pole (J2000)
SATURN_POLE_RA = 40.589 * d2r
SATURN_POLE_DEC = 83.537 * d2r

# Equatorial radii (km, IAU/JPL; Saturn's without rings) -> angular diameter at 1 AU (arcsec)
_EQUATORIAL_RADIUS_KM = {"mercury": 2439.7, "venus": 6051.8, "mars": 3396.19, "jupiter": 71492.0,
                         "saturn": 60268.0, "uranus": 25559.0, "neptune": 24764.0}
_AU_KM = 149597870.7
D0 = {n: 2 * r / _AU_KM * erfa.DR2AS for n, r in _EQUATORIAL_RADIUS_KM.items()}


def utc_jd(year, month, day, hour, minute, second):
    """UTC calendar date -> two-part Julian Date."""
    return erfa.dtf2d("UTC", year, month, day, hour, minute, second)


def tt_jd(u1, u2):
    """UTC -> TT (used as an approximation of TDB)."""
    return erfa.taitt(*erfa.utctai(u1, u2))


def make_astrom(u1, u2, lon, lat, height, dut1, xp, yp):
    """Observer astrometry context (no refraction)."""
    astrom, _ = erfa.apco13(u1, u2, dut1, lon * d2r, lat * d2r, height, xp, yp, 0.0, 0.0, 0.0, 0.0)
    return astrom


def icrs_to_altaz(ra, dec, astrom):
    """ICRS direction (degrees) -> topocentric (altitude, azimuth) in degrees."""
    ri, di = erfa.atciq(ra * d2r, dec * d2r, 0.0, 0.0, 0.0, 0.0, astrom)
    aob, zob, _, _, _ = erfa.atioq(ri, di, astrom)
    return float(90 - zob * r2d), float(aob * r2d)


def _bary(name, jd, back=0.0):
    """Barycentric ICRS position of a body and of the Sun, in AU."""
    date = (jd[0], jd[1] - back)
    pvh, pvb = erfa.epv00(*date)
    sun_b = np.array(pvb["p"]) - np.array(pvh["p"])
    if name == "sun":
        return sun_b, sun_b
    if name == "moon":
        return np.array(erfa.moon98(*date)["p"]) + np.array(pvb["p"]), sun_b
    return np.array(erfa.plan94(*date, PLAN94_ID[name])["p"]) + sun_b, sun_b


def _saturn_sin_B(geo):
    """Sine of Saturn's ring opening angle as seen from Earth."""
    ra, dec, _ = erfa.p2s(geo)
    return float(-(np.sin(dec) * np.sin(SATURN_POLE_DEC)
                   + np.cos(dec) * np.cos(SATURN_POLE_DEC) * np.cos(ra - SATURN_POLE_RA)))


def _app_mag(name, r, R, i, sin_B=0.0):
    """Approximate apparent visual magnitude (Astronomical Almanac / Explanatory Supplement)."""
    base = 5 * np.log10(r * R)
    return float({
        "mercury": -0.36 + base + 0.027 * i + 2.2e-13 * i**6,
        "venus": -4.34 + base + 0.013 * i + 4.2e-7 * i**3,
        "mars": -1.51 + base + 0.016 * i,
        "jupiter": -9.25 + base + 0.014 * i,
        "saturn": -8.88 + base + 0.044 * i - 2.60 * abs(sin_B) + 1.25 * sin_B**2,
        "uranus": -7.15 + base + 0.001 * i,
        "neptune": -6.90 + base + 0.001 * i,
    }[name])


def solar_system(year, month, day, hour, minute, second, lon, lat, height=0.0,
                 dut1=0.0, xp=0.0, yp=0.0, light_time=True) -> dict:
    """Sun, Moon and planets for an observer at (lon east, lat north) in degrees, height in m."""
    u1, u2 = utc_jd(year, month, day, hour, minute, second)
    astrom = make_astrom(u1, u2, lon, lat, height, dut1, xp, yp)
    jd = tt_jd(u1, u2)

    observer_b = np.array(astrom["eb"])            # observer, barycentric (AU)
    earth_b = np.array(erfa.epv00(*jd)[1]["p"])    # geocentre, barycentric (AU)

    result, helio_r, earth_r, phase_angles, saturn_sin_B, geo_positions = {}, {}, {}, {}, {}, {}
    sun_geo = None

    for name in BODIES:
        pos, sun_b = _bary(name, jd)
        if light_time:  # retarded position, two iterations
            for _ in range(2):
                lt = np.linalg.norm(pos - observer_b) / erfa.DC
                pos, sun_b = _bary(name, jd, back=lt)

        geo = pos - earth_b
        geo_positions[name] = geo
        if name == "sun":
            sun_geo = geo

        ra_t, dec_t, _ = erfa.p2s(pos - observer_b)      # topocentric direction
        alt, az = icrs_to_altaz(ra_t * r2d, dec_t * r2d, astrom)
        g_ra, g_dec, g_r = erfa.p2s(geo)                 # geocentric RA/Dec
        result[name] = {"ra": float((g_ra * r2d) % 360), "dec": float(g_dec * r2d),
                        "alt": alt, "az": az}

        if name in PLANETS:
            helio_r[name] = np.linalg.norm(pos - sun_b)
            earth_r[name] = g_r
            phase_angles[name] = erfa.sepp(sun_b - pos, earth_b - pos) * r2d
            if name == "saturn":
                saturn_sin_B[name] = _saturn_sin_B(geo)

    for name in ["moon"] + PLANETS:
        elongation = erfa.sepp(sun_geo, geo_positions[name]) * r2d
        phase_angle = 180 - elongation if name == "moon" else phase_angles[name]
        result[name]["elongation"] = float(elongation)
        result[name]["phase_angle"] = float(phase_angle)
        result[name]["illumination"] = float((1 + np.cos(phase_angle * d2r)) / 2 * 100)

    for name in PLANETS:
        result[name]["magnitude"] = _app_mag(name, helio_r[name], earth_r[name],
                                             phase_angles[name], saturn_sin_B.get(name, 0.0))
        result[name]["angular_diameter"] = float(D0[name] / earth_r[name])

    return result
