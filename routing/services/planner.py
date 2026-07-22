"""Tie the pieces together: geocode the endpoints, pull the route once, match
truckstops to it and work out the cheapest way to fuel the trip.
"""

import hashlib

import numpy as np
from django.conf import settings
from django.core.cache import cache

from ..models import FuelStation
from . import directions, geocoding, geometry
from .optimizer import Candidate, plan


def plan_trip(start, finish):
    """Plan a fuelling strategy between two place names.

    The finished plan is cached by (start, finish) so that asking for the JSON
    and the map back to back only hits the routing service once.
    """
    cache_key = "plan:" + hashlib.sha1(
        f"{start.strip().lower()}|{finish.strip().lower()}".encode()
    ).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    origin = geocoding.geocode(start)
    destination = geocoding.geocode(finish)
    trip = directions.route(origin, destination)

    points = np.array(trip["points"], dtype=float)
    total_distance = trip["distance_mi"]

    candidates = _candidates_along_route(points, total_distance)
    fuelling = plan(
        candidates,
        total_distance=total_distance,
        max_range=settings.VEHICLE_RANGE_MILES,
        mpg=settings.VEHICLE_MPG,
    )

    result = {
        "start": {"query": start, "lat": origin[0], "lon": origin[1]},
        "finish": {"query": finish, "lat": destination[0], "lon": destination[1]},
        "total_distance_miles": round(total_distance, 1),
        "total_gallons": fuelling["total_gallons"],
        "total_fuel_cost": fuelling["total_cost"],
        "fuel_stops": [_stop_view(f) for f in fuelling["fillups"]],
        "route": [[lat, lon] for lat, lon in trip["points"]],
    }
    cache.set(cache_key, result, timeout=60 * 60)
    return result


def _candidates_along_route(points, total_distance):
    """Find geocoded stations near the route and place each one along it."""
    cum = geometry.cumulative_miles(points)
    lat_lo, lat_hi, lon_lo, lon_hi = geometry.bounding_box(
        points, settings.ROUTE_MATCH_BUFFER_MILES
    )

    stations = list(
        FuelStation.objects.filter(
            latitude__isnull=False,
            latitude__range=(lat_lo, lat_hi),
            longitude__range=(lon_lo, lon_hi),
        ).values("id", "name", "address", "city", "state", "retail_price",
                 "latitude", "longitude")
    )
    if not stations:
        return []

    lat = np.array([s["latitude"] for s in stations])
    lon = np.array([s["longitude"] for s in stations])
    nearest, offset = geometry.nearest_on_route(points, lat, lon)

    within = offset <= settings.ROUTE_MATCH_BUFFER_MILES
    # Scale straight-line vertex distances onto the authoritative driving total so
    # a station's "miles from start" stays consistent with total_distance_miles.
    scale = total_distance / cum[-1] if cum[-1] > 0 else 1.0

    candidates = []
    for idx in np.nonzero(within)[0]:
        s = stations[idx]
        candidates.append(
            Candidate(
                position=float(cum[nearest[idx]] * scale),
                price=float(s["retail_price"]),
                payload={
                    "id": s["id"],
                    "name": s["name"],
                    "address": s["address"],
                    "city": s["city"],
                    "state": s["state"],
                    "lat": s["latitude"],
                    "lon": s["longitude"],
                    "off_route_miles": round(float(offset[idx]), 1),
                },
            )
        )
    return candidates


def _stop_view(fillup):
    p = fillup.payload
    view = {
        "mile_marker": round(fillup.position, 1),
        "price_per_gallon": round(fillup.price, 3),
        "gallons": round(fillup.gallons, 2),
        "cost": round(fillup.cost, 2),
    }
    if p.get("origin"):
        view["name"] = "Departure fill-up (nearest station price)"
    else:
        view.update(
            name=p.get("name"),
            address=p.get("address"),
            city=p.get("city"),
            state=p.get("state"),
            lat=p.get("lat"),
            lon=p.get("lon"),
            off_route_miles=p.get("off_route_miles"),
        )
    return view
