"""Pick the cheapest set of fuel stops for a trip.

This is the gas-station problem: given the price at each candidate station along
the route and a limited tank, buy the trip's fuel as cheaply as possible without
ever running dry. Prices are known up front, so a look-ahead greedy is optimal --
at every stop either coast to the next cheaper station or fill up and push on to
the cheapest one still in range.

We assume the tank starts empty and you fill up before leaving, so the entire
trip's fuel gets purchased. The starting fill is priced at the first station on
the route.
"""

from dataclasses import dataclass


class RouteInfeasible(Exception):
    """Raised when the route can't be completed within the vehicle's range."""


@dataclass
class Candidate:
    position: float          # miles from the start, measured along the route
    price: float             # USD per gallon
    payload: dict = None     # station details to echo back in the response


@dataclass
class Fillup:
    position: float
    price: float
    gallons: float
    cost: float
    payload: dict


def plan(candidates, total_distance, max_range, mpg):
    stations = _prepare(candidates, total_distance, max_range)
    positions = [s.position for s in stations]

    fuel = 0.0  # miles of range currently in the tank
    fillups = []
    i = 0
    while i < len(stations):
        here = stations[i]
        to_end = total_distance - here.position
        reachable = [
            j for j in range(i + 1, len(stations))
            if positions[j] - here.position <= max_range + 1e-6
        ]

        if to_end <= max_range + 1e-6 and not _cheaper_ahead(stations, i, reachable):
            fuel += _buy(fillups, here, need=to_end - fuel, mpg=mpg)
            break

        cheaper = _cheaper_ahead(stations, i, reachable)
        if cheaper is not None:
            gap = positions[cheaper] - here.position
            fuel += _buy(fillups, here, need=gap - fuel, mpg=mpg)
            fuel -= gap
            i = cheaper
        else:
            if not reachable:
                raise RouteInfeasible("no reachable station ahead")
            fuel += _buy(fillups, here, need=max_range - fuel, mpg=mpg)
            nxt = min(reachable, key=lambda j: stations[j].price)
            fuel -= positions[nxt] - here.position
            i = nxt

    return {
        "fillups": [f for f in fillups if f.gallons > 1e-6],
        "total_gallons": round(sum(f.gallons for f in fillups), 2),
        "total_cost": round(sum(f.cost for f in fillups), 2),
    }


def _prepare(candidates, total_distance, max_range):
    ordered = sorted(candidates, key=lambda c: c.position)
    if not ordered:
        raise RouteInfeasible("no fuel stations found near the route")

    # The origin is itself a fill-up point (you tank up before leaving); price it
    # at the first station on the route.
    stations = [Candidate(0.0, ordered[0].price, {"origin": True})]
    for c in ordered:
        if c.position <= 0.0:
            continue
        # Stations geocoded to the same city collapse to one position; keep the
        # cheapest so the driver always sees the best local price.
        if abs(c.position - stations[-1].position) < 1e-6:
            if c.price < stations[-1].price:
                stations[-1] = c
            continue
        stations.append(c)

    checkpoints = [s.position for s in stations] + [total_distance]
    for a, b in zip(checkpoints, checkpoints[1:]):
        if b - a > max_range + 1e-6:
            raise RouteInfeasible(
                f"no fuel station within range between mile {a:.0f} and {b:.0f}"
            )
    return stations


def _cheaper_ahead(stations, i, reachable):
    return next((j for j in reachable if stations[j].price < stations[i].price), None)


def _buy(fillups, station, need, mpg):
    """Buy `need` miles of range at this station; returns miles actually added."""
    if need <= 1e-9:
        added = 0.0
    else:
        added = need
    gallons = added / mpg
    fillups.append(
        Fillup(
            position=station.position,
            price=station.price,
            gallons=gallons,
            cost=gallons * station.price,
            payload=station.payload or {},
        )
    )
    return added
