"""Small geodesic helpers used to line fuel stations up against a route.

Everything works on plain numpy arrays of (lat, lon) so it stays fast even for
long routes with a few thousand shape points.
"""

import numpy as np

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * np.arcsin(np.sqrt(a))


def cumulative_miles(points):
    """Distance from the start to each vertex of the polyline."""
    pts = np.asarray(points, dtype=float)
    legs = haversine_miles(pts[:-1, 0], pts[:-1, 1], pts[1:, 0], pts[1:, 1])
    return np.concatenate([[0.0], np.cumsum(legs)])


def bounding_box(points, pad_miles):
    """Lat/lon box around the route, padded by a mileage buffer."""
    pts = np.asarray(points, dtype=float)
    lat_pad = pad_miles / 69.0
    mean_lat = np.radians(pts[:, 0].mean())
    lon_pad = pad_miles / (69.0 * max(np.cos(mean_lat), 0.01))
    return (
        pts[:, 0].min() - lat_pad,
        pts[:, 0].max() + lat_pad,
        pts[:, 1].min() - lon_pad,
        pts[:, 1].max() + lon_pad,
    )


def nearest_on_route(route, station_lat, station_lon):
    """For each station, the nearest route vertex and the distance to it.

    Uses a local equirectangular projection centred on the route so the whole
    thing is one vectorised numpy operation. Accurate enough at these scales;
    the route geometry is dense so nearest-vertex ~= nearest-point.

    Returns (nearest_index, distance_miles), both length-N arrays.
    """
    route = np.asarray(route, dtype=float)
    lat0 = np.radians(route[:, 0].mean())

    def project(lat, lon):
        x = np.radians(lon) * np.cos(lat0) * EARTH_RADIUS_MILES
        y = np.radians(lat) * EARTH_RADIUS_MILES
        return x, y

    rx, ry = project(route[:, 0], route[:, 1])
    sx, sy = project(np.asarray(station_lat), np.asarray(station_lon))

    dx = sx[:, None] - rx[None, :]
    dy = sy[:, None] - ry[None, :]
    dist = np.sqrt(dx * dx + dy * dy)
    nearest = dist.argmin(axis=1)
    return nearest, dist[np.arange(len(sx)), nearest]
