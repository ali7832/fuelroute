import numpy as np
from django.test import SimpleTestCase

from routing.services import geometry
from routing.tests.factories import point_at_fraction, straight_route


class GeometryTests(SimpleTestCase):
    def test_haversine_known_distance(self):
        # NYC to LA is roughly 2450 miles great-circle.
        d = geometry.haversine_miles(40.71, -74.01, 34.05, -118.24)
        self.assertTrue(2300 < float(d) < 2600)

    def test_cumulative_is_monotonic(self):
        route = straight_route((32.0, -96.0), (39.0, -105.0))
        cum = geometry.cumulative_miles(route)
        self.assertEqual(cum[0], 0.0)
        self.assertTrue(np.all(np.diff(cum) >= 0))

    def test_nearest_on_route_flags_offset(self):
        route = straight_route((32.0, -96.0), (39.0, -105.0))
        mid = point_at_fraction(route, 0.5)
        on = mid
        off = (mid[0] + 0.9, mid[1])  # ~60 miles north
        lat = np.array([on[0], off[0]])
        lon = np.array([on[1], off[1]])
        _, dist = geometry.nearest_on_route(route, lat, lon)
        self.assertLess(dist[0], 1.0)
        self.assertGreater(dist[1], 40.0)
