"""Integration test verifying API and Visualization contracts for Developer A and B."""

import unittest
from typing import Any, Dict

from algorithms.grid.sample_jezero_grid import create_sample_jezero_dataset
from algorithms.models import RouteProfile
from algorithms.routing.alternatives import AlternativeRoutePlanner
from algorithms.science.observation_planner import ScienceObservationPlanner


class TestIntegrationContract(unittest.TestCase):
    """Verifies that the algorithms module satisfies Developer B and Developer A contracts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset = create_sample_jezero_dataset(width=80, height=80, resolution_m=10.0)
        cls.transformer = cls.dataset["transformer"]
        cls.planner = AlternativeRoutePlanner(
            dem=cls.dataset["dem"],
            hazard_mask=cls.dataset["hazard_mask"],
            resolution_m=10.0,
            coord_transformer=cls.transformer.grid_to_mars,
        )

    def test_grid_coordinate_plan_contract(self) -> None:
        """Verify plan executed with grid coordinates produces complete response for Developer B."""
        # Traverse across Jezero from delta terrace (x=15, y=20) down through Neretva ramp to crater floor (x=65, y=20)
        start = (15, 20)
        goal = (65, 20)

        multi_res = self.planner.plan_multi_routes(
            start=start,
            goal=goal,
            preferred_profile=RouteProfile.BALANCED,
        )

        response_dict = multi_res.to_dict()

        # Contract checks for Developer B (FastAPI POST /api/routes/plan response)
        self.assertIn("primary", response_dict)
        self.assertIn("alternatives", response_dict)
        self.assertIn("comparison", response_dict)
        self.assertIn("limitations", response_dict)

        primary = response_dict["primary"]
        self.assertTrue(primary["found"])
        self.assertEqual(primary["status"], "SUCCESS")
        self.assertGreater(primary["total_distance_m"], 0.0)
        self.assertGreaterEqual(primary["estimated_risk_score"], 0.0)
        self.assertLessEqual(primary["estimated_risk_score"], 100.0)
        self.assertIn("waypoints", primary)
        self.assertGreater(len(primary["waypoints"]), 0)

        # Check waypoint fields required by frontend Developer A
        first_wp = primary["waypoints"][0]
        self.assertIn("grid_x", first_wp)
        self.assertIn("grid_y", first_wp)
        self.assertIn("lon", first_wp)
        self.assertIn("lat", first_wp)
        self.assertIn("elevation_m", first_wp)
        self.assertIn("slope_deg", first_wp)
        self.assertIn("risk_score", first_wp)
        self.assertIn("cumulative_distance_m", first_wp)

    def test_geojson_contract_for_frontend_developer_a(self) -> None:
        """Verify GeoJSON FeatureCollection generated for OpenLayers frontend."""
        start = (15, 20)
        goal = (65, 20)

        multi_res = self.planner.plan_multi_routes(start=start, goal=goal)
        geojson = multi_res.to_geojson()

        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertIn("features", geojson)
        self.assertIn("properties", geojson)

        # Features should include at least LineString for each route
        line_features = [
            f for f in geojson["features"] if f["geometry"]["type"] == "LineString"
        ]
        self.assertEqual(len(line_features), 3)  # Balanced, Direct, Safe

        # Coordinates should be [lon, lat, elevation]
        first_coord = line_features[0]["geometry"]["coordinates"][0]
        self.assertEqual(len(first_coord), 3)
        self.assertTrue(77.0 < first_coord[0] < 78.0)  # Mars lon around 77.45
        self.assertTrue(18.0 < first_coord[1] < 19.0)  # Mars lat around 18.38

    def test_science_targets_near_route(self) -> None:
        """Verify science target identification along planned route."""
        start = (15, 20)
        goal = (65, 20)

        multi_res = self.planner.plan_multi_routes(start=start, goal=goal)
        primary = multi_res.primary
        self.assertTrue(primary.found)

        sci_planner = ScienceObservationPlanner(self.dataset["science_targets"])
        nearby = sci_planner.find_targets_near_path(primary.path_grid, max_distance_cells=10.0)

        # Delta Front Fan Base is at (42, 22), Three Forks Sample Depot at (30, 20)
        self.assertTrue(any(t["name"] == "Delta Front Fan Base" for t in nearby))


if __name__ == "__main__":
    unittest.main()
