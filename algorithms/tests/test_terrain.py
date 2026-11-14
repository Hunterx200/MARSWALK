"""Unit tests for terrain analysis: slope, roughness, and cost model."""

import math
import unittest
import numpy as np

from algorithms.terrain.cost_model import TerrainCostModel
from algorithms.terrain.roughness import compute_roughness
from algorithms.terrain.slope import classify_slope_traversability, compute_slope_degrees


class TestTerrainAnalysis(unittest.TestCase):
    """Test suite for slope, roughness, and terrain cost calculations."""

    def test_flat_plane_slope_is_zero(self) -> None:
        """A completely flat elevation surface should have 0.0 degrees slope everywhere."""
        dem = np.full((10, 10), -2500.0, dtype=float)
        slope = compute_slope_degrees(dem, resolution_m=10.0)

        self.assertEqual(slope.shape, (10, 10))
        np.testing.assert_allclose(slope, 0.0, atol=1e-6)

    def test_known_45_degree_incline(self) -> None:
        """Verify that an elevation rise of resolution_m per cell gives 45 degrees slope."""
        # 10m per cell. If z increases by 10m per cell along x: dz/dx = 1.0 -> arctan(1.0) = 45 deg
        res_m = 10.0
        x = np.arange(10) * res_m  # 0, 10, 20, 30...
        dem = np.tile(x, (10, 1)).astype(float)

        slope = compute_slope_degrees(dem, resolution_m=res_m)

        # Check interior pixels (central differences give exactly 1.0 gradient)
        interior_slope = slope[2:8, 2:8]
        np.testing.assert_allclose(interior_slope, 45.0, atol=1e-4)

    def test_slope_traversability_classification(self) -> None:
        """Test classification of slopes into gentle, moderate, steep, and impassable."""
        slope = np.array([
            [2.0, 8.0],
            [17.0, 26.0],
        ])
        classes = classify_slope_traversability(
            slope, max_safe_slope=15.0, max_permissible_slope=20.0
        )

        self.assertTrue(classes["gentle"][0, 0])
        self.assertTrue(classes["moderate"][0, 1])
        self.assertTrue(classes["steep"][1, 0])
        self.assertTrue(classes["impassable"][1, 1])
        self.assertFalse(classes["traversable"][1, 1])
        self.assertTrue(classes["traversable"][0, 0])

    def test_roughness_computation(self) -> None:
        """Roughness on a flat surface should be 0.0; on a checkerboard it should be > 0."""
        flat_dem = np.full((10, 10), 100.0, dtype=float)
        r_flat = compute_roughness(flat_dem, window_size=3)
        np.testing.assert_allclose(r_flat, 0.0, atol=1e-5)

        # Rough surface
        rough_dem = np.zeros((10, 10), dtype=float)
        rough_dem[::2, ::2] = 10.0
        r_rough = compute_roughness(rough_dem, window_size=3)
        self.assertTrue(np.mean(r_rough) > 0.0)

    def test_terrain_cost_model_impassable_cutoff(self) -> None:
        """Cells with slope > max_slope_deg must be set to impassable cost."""
        dem = np.zeros((10, 10), dtype=float)
        # Create an artificial cliff: row 5 has a 50m jump
        dem[5:, :] = 100.0

        model = TerrainCostModel(max_slope_deg=20.0, impassable_cost=1e6)
        cost = model.compute_cost_grid(dem, resolution_m=10.0)

        # The boundary row where cliff occurs should be marked impassable
        self.assertTrue(np.any(cost >= 1e6))
        # Flat area should have cost close to 1.0
        self.assertAlmostEqual(cost[0, 0], 1.0, places=1)


if __name__ == "__main__":
    unittest.main()
