from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from routing.services import geocoding
from routing.tests.factories import point_at_fraction, straight_route
from routing.tests.test_planner import ROUTE, DISTANCE_MI, seed_station


class RouteApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        seed_station(ROUTE, 0.30, 3.20, name="Cheap", city="Midtown")
        self.patchers = [
            mock.patch("routing.services.geocoding.geocode",
                       side_effect=lambda q, **kw: ROUTE[0] if "start" in q.lower() else ROUTE[-1]),
            mock.patch("routing.services.directions.route",
                       return_value={"points": ROUTE, "distance_mi": DISTANCE_MI}),
        ]
        for p in self.patchers:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patchers])

    def test_post_returns_plan(self):
        resp = self.client.post(
            "/api/route/", {"start": "Start City", "finish": "Finish Town"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total_gallons"], 90.0)
        self.assertIn("map_url", body)
        self.assertIn("/api/route/map/", body["map_url"])
        self.assertGreater(len(body["fuel_stops"]), 0)
        # The heavy route geometry stays out of the JSON payload.
        self.assertNotIn("route", body)

    def test_get_is_supported_for_quick_checks(self):
        resp = self.client.get("/api/route/", {"start": "Start City", "finish": "Finish Town"})
        self.assertEqual(resp.status_code, 200)

    def test_missing_finish_is_a_400(self):
        resp = self.client.post("/api/route/", {"start": "Somewhere"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_unlocatable_place_is_422(self):
        with mock.patch(
            "routing.services.geocoding.geocode",
            side_effect=geocoding.GeocodingError("could not locate 'Narnia'"),
        ):
            resp = self.client.post(
                "/api/route/", {"start": "Narnia", "finish": "Oz"}, format="json"
            )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("error", resp.json())

    def test_map_endpoint_renders_html(self):
        resp = self.client.get(
            "/api/route/map/", {"start": "Start City", "finish": "Finish Town"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"leaflet", resp.content.lower())
