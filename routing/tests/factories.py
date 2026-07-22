"""Helpers for building a synthetic route and stations sitting on it."""

import numpy as np


def straight_route(start, finish, n=200):
    """A dense list of (lat, lon) points on the straight line start -> finish."""
    lats = np.linspace(start[0], finish[0], n)
    lons = np.linspace(start[1], finish[1], n)
    return [(float(a), float(b)) for a, b in zip(lats, lons)]


def point_at_fraction(route, fraction):
    """The route vertex nearest to `fraction` of the way along it."""
    idx = int(round(fraction * (len(route) - 1)))
    return route[idx]
