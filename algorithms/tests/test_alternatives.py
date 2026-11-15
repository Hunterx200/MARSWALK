"""Unit tests for multi-route alternative planning."""

import unittest
import numpy as np

from algorithms.models import MultiRouteResult, RouteProfile
from algorithms.routing.alternatives import AlternativeRoutePlanner


class TestAlternativeRoutePlanner(unittest.TestCase):
    """Test suite for alternative route generation."""

    def setUp(self) -> None:
        """Create a 30x30 synthetic DEM with a central obstacle."""
        self.height = 30
        self.width = 30
        self.resolution_m = 10.0

        # Gentle terrain elevation
        self.dem = np.full((self.height, self.width), -2500.0, dtype=float)

        # Place a hazard boulder/sand region in the center (x: 12..18, y: 10..20)
        self.hazard_mask = np.zeros((self.height, self.width), dtype=bool)
        self.hazard_mask[10:20, 12:18] = True

        self.planner = AlternativeRoutePlanner(
            dem=self.dem,
            hazard_mask=self.hazard_mask,
            resolution_m=self.resolution_m,
        )

    def test_plan_multi_routes_generates_all_profiles(self) -> None:
        """Verify that BALANCED, DIRECT, and SAFE routes are generated."""
        start = (5, 15)
        goal = (25, 15)

        multi_res = self.planner.plan_multi_routes(
            start=start,
            goal=goal,
            preferred_profile=RouteProfile.BALANCED,
        )

        self.assertIsInstance(multi_res, MultiRouteResult)
        self.assertTrue(multi_res.primary.found)
        self.assertEqual(multi_res.primary.profile, RouteProfile.BALANCED.value)
        self.assertEqual(len(multi_res.alternatives), 2)

        profiles = [multi_res.primary.profile] + [
            alt.profile for alt in multi_res.alternatives
        ]
        self.assertIn("balanced", profiles)
        self.assertIn("direct", profiles)
        self.assertIn("safe", profiles)

    def test_safe_profile_keeps_greater_distance_from_hazard(self) -> None:
        """The SAFE profile must stay further from the central hazard than DIRECT."""
        start = (5, 15)
        goal = (25, 15)

        multi_res = self.planner.plan_multi_routes(
            start=start, goal=goal, preferred_profile=RouteProfile.SAFE
        )

        direct_route = next(
            r
            for r in [multi_res.primary] + multi_res.alternatives
            if r.profile == "direct"
        )
        safe_route = next(
            r
            for r in [multi_res.primary] + multi_res.alternatives
            if r.profile == "safe"
        )

        self.assertTrue(direct_route.found)
        self.assertTrue(safe_route.found)

        # Minimum hazard distance along the safe path should be >= direct path
        min_dist_safe = min(
            wp.hazard_dist_m
            for wp in safe_route.waypoints
            if wp.hazard_dist_m is not None
        )
        min_dist_direct = min(
            wp.hazard_dist_m
            for wp in direct_route.waypoints
            if wp.hazard_dist_m is not None
        )

        self.assertGreaterEqual(min_dist_safe, min_dist_direct)
        # Safe route risk score should be <= direct route risk score
        self.assertLessEqual(
            safe_route.estimated_risk_score, direct_route.estimated_risk_score + 1.0
        )

    def test_to_geojson_format(self) -> None:
        """MultiRouteResult.to_geojson() must produce a valid GeoJSON FeatureCollection."""
        start = (2, 2)
        goal = (8, 8)

        multi_res = self.planner.plan_multi_routes(start=start, goal=goal)
        geojson = multi_res.to_geojson()

        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertIn("features", geojson)
        self.assertTrue(len(geojson["features"]) > 0)

        # Check line features
        line_features = [
            f
            for f in geojson["features"]
            if f["geometry"]["type"] == "LineString"
        ]
        self.assertTrue(len(line_features) >= 1)
        self.assertIn("profile", line_features[0]["properties"])
        self.assertIn("estimated_risk_score", line_features[0]["properties"])

    def test_to_dict_format(self) -> None:
        """MultiRouteResult.to_dict() must produce complete serialized summary."""
        start = (2, 2)
        goal = (8, 8)

        multi_res = self.planner.plan_multi_routes(start=start, goal=goal)
        d = multi_res.to_dict()

        self.assertIn("primary", d)
        self.assertIn("alternatives", d)
        self.assertIn("comparison", d)
        self.assertEqual(len(d["comparison"]), 3)


if __name__ == "__main__":
    unittest.main()
