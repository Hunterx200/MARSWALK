"""Unit tests for Jezero Crater coordinate transformations and sample benchmark datasets."""

import unittest
import numpy as np

from algorithms.grid.coordinate_transform import (
    JezeroCoordinateTransformer,
    create_jezero_default_grid_spec,
)
from algorithms.grid.sample_jezero_grid import create_sample_jezero_dataset


class TestCoordinateTransformAndGrid(unittest.TestCase):
    """Test suite for coordinate transformation and benchmark datasets."""

    def setUp(self) -> None:
        self.spec = create_jezero_default_grid_spec(
            width=100, height=100, resolution_m=10.0, center_lon=77.45, center_lat=18.38
        )
        self.transformer = JezeroCoordinateTransformer(self.spec)

    def test_grid_spec_parameters(self) -> None:
        """Verify grid spec bounds and center."""
        self.assertEqual(self.spec.width, 100)
        self.assertEqual(self.spec.height, 100)
        self.assertEqual(self.spec.resolution_m, 10.0)
        self.assertTrue(self.spec.lon_min < 77.45 < self.spec.lon_max)
        self.assertTrue(self.spec.lat_min < 18.38 < self.spec.lat_max)

    def test_round_trip_grid_to_mars_and_back(self) -> None:
        """Converting grid -> mars -> grid must return original coordinates."""
        test_points = [(0, 0), (50, 50), (99, 99), (25, 75)]

        for orig_x, orig_y in test_points:
            lon, lat = self.transformer.grid_to_mars(orig_x, orig_y)
            rx, ry = self.transformer.mars_to_grid(lon, lat)
            self.assertEqual((rx, ry), (orig_x, orig_y))

    def test_bounds_checking(self) -> None:
        """Check in-bounds and out-of-bounds geographic coordinates."""
        self.assertTrue(self.transformer.is_mars_coord_in_bounds(77.45, 18.38))
        self.assertFalse(self.transformer.is_mars_coord_in_bounds(70.0, 18.38))
        self.assertFalse(self.transformer.is_mars_coord_in_bounds(77.45, 25.0))

        self.assertTrue(self.transformer.is_grid_coord_in_bounds(0, 0))
        self.assertTrue(self.transformer.is_grid_coord_in_bounds(99, 99))
        self.assertFalse(self.transformer.is_grid_coord_in_bounds(-1, 50))
        self.assertFalse(self.transformer.is_grid_coord_in_bounds(100, 50))

    def test_sample_jezero_dataset_generation(self) -> None:
        """Test creation of the benchmark dataset for Jezero Crater."""
        data = create_sample_jezero_dataset(width=100, height=100, resolution_m=10.0)

        self.assertIn("dem", data)
        self.assertIn("hazard_mask", data)
        self.assertIn("grid_spec", data)
        self.assertIn("transformer", data)
        self.assertIn("science_targets", data)
        self.assertIn("metadata", data)

        dem = data["dem"]
        hazard = data["hazard_mask"]

        self.assertEqual(dem.shape, (100, 100))
        self.assertEqual(hazard.shape, (100, 100))

        # Check metadata truthfulness
        meta = data["metadata"]
        self.assertFalse(meta["is_real_nasa_telemetry"])
        self.assertEqual(meta["provenance"], "SYNTHETIC_BENCHMARK_DEM")
        self.assertTrue(len(meta["known_limitations"]) > 0)

        # Check science targets
        self.assertTrue(len(data["science_targets"]) >= 4)
        first_target = data["science_targets"][0]
        self.assertTrue(hasattr(first_target, "name"))
        self.assertTrue(hasattr(first_target, "scientific_priority"))


if __name__ == "__main__":
    unittest.main()
