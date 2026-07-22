from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from routing.models import FuelStation
from routing.services import planner
from routing.tests.factories import point_at_fraction, straight_route

ROUTE = straight_route((35.0, -90.0), (39.0, -105.0))
DISTANCE_MI = 900.0


def seed_station(route, fraction, price, **extra):
    lat, lon = point_at_fraction(route, fraction)
    return FuelStation.objects.create(
        opis_id=extra.get("opis_id", 1),
        name=extra.get("name", "Test Stop"),
        city=extra.get("city", "Somewhere"),
        state=extra.get("state", "MO"),
        retail_price=price,
        latitude=lat,
        longitude=lon,
    )


class PlannerTests(TestCase):
    def setUp(self):
        cache.clear()
        self.patchers = [
            mock.patch(
                "routing.services.geocoding.geocode",
                side_effect=[ROUTE[0], ROUTE[-1]],
            ),
            mock.patch(
                "routing.services.directions.route",
                return_value={"points": ROUTE, "distance_mi": DISTANCE_MI},
            ),
        ]
        for p in self.patchers:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patchers])

    def test_buys_full_trip_and_picks_cheaper_station(self):
        seed_station(ROUTE, 0.10, 4.90, name="Pricey", city="Early")
        seed_station(ROUTE, 0.45, 3.00, name="Bargain", city="Middle")

        result = planner.plan_trip("Start City", "Finish City")

        # 900 miles at 10 mpg -> 90 gallons for the whole trip.
        self.assertEqual(result["total_gallons"], 90.0)
        self.assertGreater(result["total_fuel_cost"], 0)

        used = {s.get("name") for s in result["fuel_stops"]}
        self.assertIn("Bargain", used)  # the cheap station must be used

    def test_far_off_route_station_is_ignored(self):
        seed_station(ROUTE, 0.45, 3.00, name="On Route", city="Middle")
        # Same longitude but ~2 degrees north of the line -> well outside buffer.
        lat, lon = point_at_fraction(ROUTE, 0.45)
        FuelStation.objects.create(
            opis_id=99, name="Way Off", city="North", state="MO",
            retail_price=1.50, latitude=lat + 2.0, longitude=lon,
        )

        result = planner.plan_trip("Start City", "Finish City")
        names = {s.get("name") for s in result["fuel_stops"]}
        self.assertNotIn("Way Off", names)  # cheap-but-distant station not chosen

    def test_route_hits_upstream_only_once(self):
        seed_station(ROUTE, 0.45, 3.00)
        with mock.patch(
            "routing.services.directions.route",
            return_value={"points": ROUTE, "distance_mi": DISTANCE_MI},
        ) as route_mock:
            planner.plan_trip("A", "B")
            planner.plan_trip("A", "B")  # cached the second time
            self.assertEqual(route_mock.call_count, 1)
