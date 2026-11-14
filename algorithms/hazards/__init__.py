"""Hazard analysis subpackage: proximity transform, risk scoring, and buffer zones."""

from algorithms.hazards.proximity import compute_hazard_distance_grid
from algorithms.hazards.scoring import HazardRiskModel

__all__ = ["compute_hazard_distance_grid", "HazardRiskModel"]
