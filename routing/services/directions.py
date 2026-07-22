"""Driving directions from OSRM.

One request returns the full route geometry and the driving distance, which is
all the planner needs -- so a trip costs exactly one call to the routing service.
"""

from django.conf import settings

from .http import session

_METERS_PER_MILE = 1609.344


class DirectionsError(Exception):
    pass


def route(origin, destination):
    """Fetch the driving route between two (lat, lon) points.

    Returns a dict with:
        points        list of (lat, lon) along the route
        distance_mi   driving distance in miles
    """
    # OSRM expects lon,lat order in the path.
    coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    url = f"{settings.OSRM_BASE_URL}/route/v1/driving/{coords}"

    resp = session().get(
        url,
        params={"overview": "full", "geometries": "geojson", "annotations": "false"},
        timeout=settings.HTTP_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    body = resp.json()

    if body.get("code") != "Ok" or not body.get("routes"):
        raise DirectionsError(body.get("message", "no route found"))

    leg = body["routes"][0]
    # GeoJSON coordinates are [lon, lat]; flip to (lat, lon).
    points = [(lat, lon) for lon, lat in leg["geometry"]["coordinates"]]
    return {"points": points, "distance_mi": leg["distance"] / _METERS_PER_MILE}
