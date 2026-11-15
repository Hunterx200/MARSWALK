"""Unit tests for hazard distance transforms and risk scoring."""

import unittest
import numpy as np

from algorithms.hazards.proximity import compute_hazard_distance_grid
from algorithms.hazards.scoring import HazardRiskModel


class TestHazardAnalysis(unittest.TestCase):
    """Test suite for hazard distance transform and risk scoring."""

    def test_single_hazard_cell_distance(self) -> None:
        """Verify Euclidean distances from a single point obstacle."""
        mask = np.zeros((5, 5), dtype=bool)
        # Place hazard at center (2, 2)
        mask[2, 2] = True
        res_m = 10.0

        dist = compute_hazard_distance_grid(mask, resolution_m=res_m)

        # Distance at hazard itself must be 0.0
        self.assertEqual(dist[2, 2], 0.0)

        # Distance at immediate orthogonal neighbor (2, 3) must be 10.0m
        self.assertAlmostEqual(dist[2, 3], 10.0, places=2)

        # Distance at diagonal neighbor (3, 3) must be sqrt(2) * 10m ≈ 14.14m
        self.assertAlmostEqual(dist[3, 3], 10.0 * np.sqrt(2), places=2)

    def test_no_hazards_returns_large_distance(self) -> None:
        """When no hazards exist, distance grid should have large safe values."""
        mask = np.zeros((5, 5), dtype=bool)
        dist = compute_hazard_distance_grid(mask, resolution_m=10.0)
        self.assertTrue(np.all(dist >= 1e4))

    def test_hazard_standoff_cost_impassable(self) -> None:
        """Cells within hard_standoff_m must be marked impassable."""
        dist_grid = np.array([
            [0.0, 2.0, 5.0],
            [10.0, 15.0, 25.0],
        ])
        model = HazardRiskModel(
            hazard_buffer_m=20.0, hard_standoff_m=3.0, impassable_cost=1e6
        )
        cost_grid = model.compute_hazard_cost_grid(dist_grid)

        # 0.0m and 2.0m are <= 3.0m -> impassable
        self.assertTrue(cost_grid[0, 0] >= 1e6)
        self.assertTrue(cost_grid[0, 1] >= 1e6)

        # 5.0m and 10.0m are in buffer zone -> cost > 1.0 but < 1e6
        self.assertTrue(1.0 < cost_grid[0, 2] < 1e6)
        self.assertTrue(1.0 < cost_grid[1, 0] < 1e6)

        # 25.0m is outside buffer (> 20.0m) -> cost == 1.0
        self.assertEqual(cost_grid[1, 2], 1.0)

    def test_composite_risk_grid_bounds(self) -> None:
        """Composite risk scores must be clamped strictly within [0.0, 100.0]."""
        slope = np.array([[0.0, 10.0], [20.0, 35.0]])
        hazard_dist = np.array([[50.0, 15.0], [5.0, 0.0]])

        model = HazardRiskModel(hazard_buffer_m=20.0, hard_standoff_m=3.0)
        risk = model.compute_composite_risk_grid(slope, hazard_dist, max_slope_deg=20.0)

        self.assertTrue(np.all(risk >= 0.0))
        self.assertTrue(np.all(risk <= 100.0))

        # Slope > 20.0 automatically hits 100.0
        self.assertEqual(risk[1, 1], 100.0)
        # Flat and far from hazard should have minimal risk
        self.assertAlmostEqual(risk[0, 0], 0.0, places=1)


if __name__ == "__main__":
    unittest.main()
