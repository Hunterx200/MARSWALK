"""Demonstration script for MARSWALK Algorithms.

Runs an end-to-end mission planning simulation on the Jezero Crater
benchmark grid and prints comparative route performance metrics.
Also generates a sample GeoJSON file ready for OpenLayers frontend inspection.

Usage:
    python -m algorithms.demo
"""

import json
import os
import sys
import time

from algorithms.grid.sample_jezero_grid import create_sample_jezero_dataset
from algorithms.models import RouteProfile
from algorithms.routing.alternatives import AlternativeRoutePlanner
from algorithms.science.observation_planner import ScienceObservationPlanner


def run_demo() -> None:
    print("=" * 80)
    print("  MARSWALK — Intelligent Mars Exploration & Mission Planning System")
    print("  Subsystem: Algorithms Engine (Developer C)")
    print("  Region: Jezero Crater, Mars (Western Delta Fan)")
    print("=" * 80)

    print("\n[1/5] Initializing Jezero Crater synthetic benchmark dataset...")
    data = create_sample_jezero_dataset(width=80, height=80, resolution_m=10.0)
    dem = data["dem"]
    hazard_mask = data["hazard_mask"]
    transformer = data["transformer"]
    science_targets = data["science_targets"]
    meta = data["metadata"]

    print(f"  • Grid dimensions: {dem.shape[1]} cols x {dem.shape[0]} rows (10.0m / cell)")
    print(f"  • Physical footprint: {dem.shape[1]*10}m E-W x {dem.shape[0]*10}m N-S")
    print(f"  • Center coordinate: ~77.45°E, 18.38°N")
    print(f"  • Elevation range: {dem.min():.1f}m to {dem.max():.1f}m")
    print(f"  • Provenance: {meta['provenance']} (Truth in data: NOT raw flight telemetry)")

    print("\n[2/5] Initializing Alternative Route Planner...")
    planner = AlternativeRoutePlanner(
        dem=dem,
        hazard_mask=hazard_mask,
        resolution_m=10.0,
        coord_transformer=transformer.grid_to_mars,
    )

    # Mission traverse scenario 1:
    # Start: Upper Delta Terrace (x=15, y=20)
    # Destination: Crater Floor Basin (x=65, y=20)
    start_grid = (15, 20)
    goal_grid = (65, 20)
    start_lon, start_lat = transformer.grid_to_mars(*start_grid)
    goal_lon, goal_lat = transformer.grid_to_mars(*goal_grid)

    print(f"\n[3/5] Scenario 1: Planning Traverse from Delta Plateau through Neretva Ramp to Crater Floor:")
    print(f"  • Start (Grid): {start_grid} -> Mars: ({start_lon:.5f}°E, {start_lat:.5f}°N)")
    print(f"  • Goal  (Grid): {goal_grid} -> Mars: ({goal_lon:.5f}°E, {goal_lat:.5f}°N)")

    t0 = time.perf_counter()
    multi_res = planner.plan_multi_routes(
        start=start_grid,
        goal=goal_grid,
        preferred_profile=RouteProfile.BALANCED,
    )
    t_elapsed = (time.perf_counter() - t0) * 1000.0

    print(f"\n[4/5] Multi-Route Planning Completed in {t_elapsed:.2f} ms:")
    print("-" * 80)
    print(f"{'Profile':<12} | {'Found':<6} | {'Distance (m)':<12} | {'Risk (0-100)':<12} | {'Max Slope':<10} | {'Traverse (hr)':<13}")
    print("-" * 80)

    summary = multi_res.to_dict()
    for row in summary["comparison"]:
        print(
            f"{row['profile']:<12} | "
            f"{str(row['found']):<6} | "
            f"{row['distance_m']:<12.1f} | "
            f"{row['estimated_risk_score']:<12.1f} | "
            f"{row['max_slope_deg']:<9.1f}° | "
            f"{row['traverse_time_hr']:<13.2f}"
        )
    print("-" * 80)

    # Mission traverse scenario 2: Navigating around Séítah Sand Ripple Hazard Field
    s2_start = (40, 50)
    s2_goal = (60, 50)
    print(f"\n[4b] Scenario 2: Hazard Avoidance around Séítah Sand Dunes / Boulder Field:")
    print(f"  • Start (Grid): {s2_start} -> Goal (Grid): {s2_goal}")
    res_s2 = planner.plan_multi_routes(start=s2_start, goal=s2_goal, preferred_profile=RouteProfile.BALANCED)
    print("-" * 80)
    print(f"{'Profile':<12} | {'Found':<6} | {'Distance (m)':<12} | {'Risk (0-100)':<12} | {'Max Slope':<10} | {'Min Hazard Dist':<15}")
    print("-" * 80)
    for r in [res_s2.primary] + res_s2.alternatives:
        min_h = min((wp.hazard_dist_m for wp in r.waypoints if wp.hazard_dist_m is not None), default=-1.0)
        print(
            f"{r.profile:<12} | "
            f"{str(r.found):<6} | "
            f"{r.total_distance_m:<12.1f} | "
            f"{r.estimated_risk_score:<12.1f} | "
            f"{r.max_slope_deg:<9.1f}° | "
            f"{min_h:<15.1f}m"
        )
    print("-" * 80)

    # Science opportunities
    sci_planner = ScienceObservationPlanner(science_targets)
    primary = multi_res.primary
    nearby_sci = sci_planner.find_targets_near_path(primary.path_grid, max_distance_cells=10.0)

    print(f"\n[5/5] Scientific Observations along Primary Route:")
    if nearby_sci:
        for t in nearby_sci:
            print(f"  ★ [{t['target_id']}] {t['name']} (Priority {t['scientific_priority']}/5.0)")
            print(f"    - Type: {t['target_type']}")
            print(f"    - Distance to path: {t['distance_to_path_cells']*10.0:.1f} m")
            print(f"    - Science goal: {t['description']}")
    else:
        print("  • No high-priority science targets within 100m corridor.")

    # Export GeoJSON demonstration file
    output_geojson_path = os.path.join(
        os.path.dirname(__file__), "sample_mission_route.geojson"
    )
    geojson_data = multi_res.to_geojson()
    with open(output_geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)

    print(f"\n✓ Exported demonstration GeoJSON: {output_geojson_path}")

    print("\n" + "=" * 80)
    print("  SAFETY CAVEATS & PROVENANCE DISCLAIMER:")
    for lim in primary.limitations:
        print(f"  ! {lim}")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
