"""Provenance, timestamp, and limitation disclaimer helpers."""
from datetime import datetime, timezone
from typing import List


def get_current_utc_iso() -> str:
    """Return the current UTC timestamp formatted in ISO 8601 with trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


STANDARD_LIMITATIONS: List[str] = [
    "MARSWALK is a research and mission-planning prototype, not an operational or safety-certified navigation system.",
    "Orbital imagery and coarse topography cannot detect small-scale obstacles, rocks, or loose regolith.",
    "Planned routes are computational estimations and are not guaranteed safe.",
    "Hazard and risk scores are project-generated heuristics based on orbital gradients, not official NASA in-situ safety assessments.",
]

MOLA_TERRAIN_LIMITATIONS: List[str] = [
    "Derived from NASA Mars Global Surveyor (MGS) MOLA MEGDR topography (128 pixels/degree, ~463 m/pixel).",
    "MOLA-derived elevation is coarse relative to rover-scale navigation (~2 m wheelbase). Micro-topographic features and boulders are not captured.",
    "Slope values are calculated via central difference gradient methods on the coarse elevation grid.",
    "MARSWALK is a research and mission-planning prototype. It is NOT an operational rover-navigation or safety-certified system.",
]

HAZARD_LIMITATIONS: List[str] = [
    "Hazard scores are MARSWALK estimates, not official NASA safety assessments.",
    "Imagery-based hazards (such as boulder fields, sand ripples, and loose sand traps) are not comprehensively detected in the MVP.",
    "Terrain slope is evaluated from orbital MOLA altimetry at coarse (~463 m) resolution.",
]

DEMO_OBSERVATION_LIMITATION: str = "Demonstration data; not a NASA observation."
