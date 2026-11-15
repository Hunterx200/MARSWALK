"""Unit tests for the A* pathfinding algorithm."""

import math
import unittest
import numpy as np

from algorithms.models import PathResult
from algorithms.routing.astar import AStarPlanner


class TestAStarPlanner(unittest.TestCase):
    """Test suite for AStarPlanner."""

    def setUp(self) -> None:
        """Create a standard 10x10 test grid with 10m resolution."""
        self.resolution_m = 10.0
        # Baseline uniform cost of 1.0 everywhere
        self.grid_10x10 = np.ones((10, 10), dtype=float)

    def test_open_grid_straight_path(self) -> None:
        """Test straight horizontal path along row 0."""
        planner = AStarPlanner(self.grid_10x10, resolution_m=self.resolution_m)
        result = planner.plan(start=(0, 0), goal=(4, 0))

        self.assertTrue(result.found)
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(len(result.path_grid), 5)
        self.assertEqual(result.path_grid[0], (0, 0))
        self.assertEqual(result.path_grid[-1], (4, 0))
        # 4 steps of 10m = 40m
        self.assertAlmostEqual(result.total_distance_m, 40.0, places=2)
        self.assertEqual(len(result.waypoints), 5)
        self.assertEqual(result.waypoints[0].cumulative_distance_m, 0.0)
        self.assertAlmostEqual(result.waypoints[-1].cumulative_distance_m, 40.0, places=2)

    def test_open_grid_diagonal_path(self) -> None:
        """Test 8-connected diagonal path from (0,0) to (3,3)."""
        planner = AStarPlanner(self.grid_10x10, resolution_m=self.resolution_m)
        result = planner.plan(start=(0, 0), goal=(3, 3))

        self.assertTrue(result.found)
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.path_grid, [(0, 0), (1, 1), (2, 2), (3, 3)])
        # 3 diagonal steps: 3 * sqrt(2) * 10m ≈ 42.426m
        expected_dist = 3.0 * math.sqrt(2) * self.resolution_m
        self.assertAlmostEqual(result.total_distance_m, expected_dist, places=2)

    def test_obstacle_avoidance(self) -> None:
        """Test routing around a vertical wall."""
        cost_grid = np.ones((10, 10), dtype=float)
        # Place vertical wall at x=3, from y=0 to y=7
        cost_grid[0:8, 3] = np.inf

        planner = AStarPlanner(cost_grid, resolution_m=self.resolution_m)
        result = planner.plan(start=(1, 2), goal=(5, 2))

        self.assertTrue(result.found)
        self.assertEqual(result.status, "SUCCESS")
        # Path must go around the wall (y >= 8)
        x_coords = [p[0] for p in result.path_grid]
        y_coords = [p[1] for p in result.path_grid]
        self.assertIn(5, x_coords)
        self.assertTrue(max(y_coords) >= 8)

    def test_corner_cutting_prevention(self) -> None:
        """Test that diagonally adjacent impassable cells prevent diagonal cutting."""
        cost_grid = np.ones((5, 5), dtype=float)
        # Create corner barrier:
        # . # .
        # # . .
        # Going from (0,0) to (1,1) diagonally should be blocked if (1,0) and (0,1) are walls
        cost_grid[0, 1] = np.inf
        cost_grid[1, 0] = np.inf

        planner = AStarPlanner(
            cost_grid, resolution_m=self.resolution_m, prevent_corner_cutting=True
        )
        result = planner.plan(start=(0, 0), goal=(2, 2))

        # (0,0) is trapped inside corner by (1,0) and (0,1) walls and grid edges (x=-1, y=-1)
        self.assertFalse(result.found)
        self.assertEqual(result.status, "UNREACHABLE")

    def test_unreachable_destination(self) -> None:
        """Test unreachable destination completely enclosed by impassable terrain."""
        cost_grid = np.ones((10, 10), dtype=float)
        # Surround (5,5) completely with barrier
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                cost_grid[5 + dy, 5 + dx] = np.inf

        planner = AStarPlanner(cost_grid, resolution_m=self.resolution_m)
        result = planner.plan(start=(0, 0), goal=(5, 5))

        self.assertFalse(result.found)
        self.assertEqual(result.status, "UNREACHABLE")
        self.assertIn("Destination", result.message)
        self.assertTrue(result.nodes_explored > 0)

    def test_start_equals_goal(self) -> None:
        """Test plan when start == goal."""
        planner = AStarPlanner(self.grid_10x10, resolution_m=self.resolution_m)
        result = planner.plan(start=(2, 3), goal=(2, 3))

        self.assertTrue(result.found)
        self.assertEqual(result.status, "NO_CHANGE")
        self.assertEqual(len(result.waypoints), 1)
        self.assertEqual(result.total_distance_m, 0.0)

    def test_out_of_bounds_coordinates(self) -> None:
        """Test out of bounds start and goal coordinates."""
        planner = AStarPlanner(self.grid_10x10, resolution_m=self.resolution_m)

        res_start_oob = planner.plan(start=(-1, 5), goal=(5, 5))
        self.assertFalse(res_start_oob.found)
        self.assertEqual(res_start_oob.status, "OUT_OF_BOUNDS")

        res_goal_oob = planner.plan(start=(0, 0), goal=(15, 5))
        self.assertFalse(res_goal_oob.found)
        self.assertEqual(res_goal_oob.status, "OUT_OF_BOUNDS")

    def test_start_or_goal_blocked(self) -> None:
        """Test when start or goal cell is in impassable terrain."""
        cost_grid = np.ones((10, 10), dtype=float)
        cost_grid[1, 1] = np.inf
        cost_grid[8, 8] = np.inf

        planner = AStarPlanner(cost_grid, resolution_m=self.resolution_m)

        res_start_blocked = planner.plan(start=(1, 1), goal=(5, 5))
        self.assertFalse(res_start_blocked.found)
        self.assertEqual(res_start_blocked.status, "START_BLOCKED")

        res_goal_blocked = planner.plan(start=(0, 0), goal=(8, 8))
        self.assertFalse(res_goal_blocked.found)
        self.assertEqual(res_goal_blocked.status, "GOAL_BLOCKED")

    def test_custom_cost_grid_detour(self) -> None:
        """Verify that A* chooses a longer geometric route to avoid high-cost terrain."""
        cost_grid = np.ones((10, 10), dtype=float)
        # Put high-cost regolith/sand patch in the middle row (cost = 20.0)
        # from x=1 to x=7 at y=2
        cost_grid[2, 1:8] = 20.0

        planner = AStarPlanner(cost_grid, resolution_m=self.resolution_m)
        result = planner.plan(start=(0, 2), goal=(8, 2))

        self.assertTrue(result.found)
        # The path should detour above (y=1) or below (y=3) rather than ploughing through cost 20.0 cells
        y_coords_in_middle = [p[1] for p in result.path_grid if 2 <= p[0] <= 6]
        # At least some points should deviate from y=2
        self.assertTrue(any(y != 2 for y in y_coords_in_middle))


    def test_start_blocked_by_slope_limit(self) -> None:
        """Verify that start cell exceeding max_slope_deg returns START_BLOCKED."""
        cost_grid = np.ones((2, 2), dtype=float)
        slope_grid = np.array([[30.0, 0.0], [0.0, 0.0]])
        planner = AStarPlanner(cost_grid, slope_grid=slope_grid, resolution_m=self.resolution_m)
        res = planner.plan(start=(0, 0), goal=(1, 0), max_slope_deg=20.0)
        self.assertFalse(res.found)
        self.assertEqual(res.status, "START_BLOCKED")

    def test_corner_cutting_prevented_by_slope_limit(self) -> None:
        """Verify corner cutting prevention when adjacent orthogonal cells exceed slope limit."""
        cost_grid = np.ones((2, 2), dtype=float)
        slope_grid = np.array([[0.0, 30.0], [30.0, 0.0]])
        planner = AStarPlanner(cost_grid, slope_grid=slope_grid, resolution_m=self.resolution_m, prevent_corner_cutting=True)
        res = planner.plan(start=(0, 0), goal=(1, 1), max_slope_deg=20.0)
        self.assertFalse(res.found)
        self.assertEqual(res.status, "UNREACHABLE")


if __name__ == "__main__":
    unittest.main()
