from django.test import SimpleTestCase

from routing.services.optimizer import Candidate, RouteInfeasible, plan


def total(candidates, distance, max_range=500, mpg=10):
    return plan(candidates, distance, max_range, mpg)


class OptimizerTests(SimpleTestCase):
    def test_buys_whole_trip(self):
        result = total([Candidate(120, 3.33)], 300)
        # 300 miles at 10 mpg = 30 gallons, all bought before leaving.
        self.assertEqual(result["total_gallons"], 30.0)
        self.assertAlmostEqual(result["total_cost"], 99.9, places=2)

    def test_prefers_cheaper_station_ahead(self):
        # Expensive near the start, cheap later: buy only enough to reach the
        # cheap station, then load up there.
        result = total([Candidate(50, 4.90), Candidate(400, 3.00)], 900)
        self.assertEqual(result["total_gallons"], 90.0)
        self.assertAlmostEqual(result["total_cost"], 346.0, places=2)

    def test_fills_up_when_nothing_cheaper_in_range(self):
        result = total(
            [Candidate(100, 3.00), Candidate(300, 4.50), Candidate(550, 4.80)], 900
        )
        self.assertEqual(result["total_gallons"], 90.0)
        # Cheapest reachable early fill dominates the cost.
        self.assertAlmostEqual(result["total_cost"], 318.0, places=2)

    def test_gap_beyond_range_is_infeasible(self):
        with self.assertRaises(RouteInfeasible):
            total([Candidate(50, 3.0), Candidate(700, 3.0)], 1200)

    def test_no_stations_is_infeasible(self):
        with self.assertRaises(RouteInfeasible):
            total([], 300)

    def test_same_city_collapses_to_cheapest(self):
        result = total([Candidate(200, 4.0), Candidate(200, 3.0)], 300)
        # The pricier duplicate is ignored.
        prices = {round(s.price, 2) for s in result["fillups"]}
        self.assertNotIn(4.0, prices)
