"""Hazard assessment service deriving terrain hazards from elevation slopes."""
import numpy as np
from typing import Optional

from app.core.provenance import get_current_utc_iso, HAZARD_LIMITATIONS
from app.schemas.hazard import (
    HazardScoreData,
    HazardType,
    HazardProvenance,
    HazardsResponse,
)
from app.services.terrain_service import terrain_service


class HazardService:
    def __init__(self, terrain_svc=terrain_service):
        self.terrain_svc = terrain_svc

    def get_hazard_score_grid(self) -> Optional[np.ndarray]:
        """Compute heuristic hazard scores (0-100) based on slope gradient."""
        if not self.terrain_svc.is_available or self.terrain_svc._slope is None:
            return None
        
        slope = self.terrain_svc._slope
        # Heuristic formula:
        # Slope 0-5 deg -> Hazard 5 - 20
        # Slope 5-15 deg -> Hazard 20 - 55
        # Slope 15-25 deg -> Hazard 55 - 85
        # Slope > 25 deg -> Hazard 85 - 100
        # Formula: clip(slope / 25.0 * 85.0 + 5.0, 0, 100)
        hazard = np.clip((slope / 25.0) * 85.0 + 5.0, 0.0, 100.0)
        return hazard

    def get_hazards_response(self, region_id: str = "jezero_crater") -> HazardsResponse:
        """Construct standard HazardsResponse adhering to API contract."""
        now_iso = get_current_utc_iso()
        hazard_arr = self.get_hazard_score_grid()

        if hazard_arr is None:
            return HazardsResponse(
                region_id=region_id,
                status="unavailable",
                hazard_score=HazardScoreData(
                    available=False,
                    unit="0-100",
                    method="project-generated heuristic",
                    values=[],
                ),
                hazard_types=[
                    HazardType(
                        id="steep_slope",
                        name="Steep slope",
                        basis="Derived from MOLA elevation gradient",
                        confidence="low",
                        available=False,
                    )
                ],
                provenance=HazardProvenance(
                    retrieved_at=now_iso,
                    limitations=HAZARD_LIMITATIONS + ["Terrain data is unavailable; hazard grid could not be derived."],
                ),
            )

        hazard_list = np.round(hazard_arr, 1).tolist()
        
        # Discrete hazard zones in Jezero for frontend telemetry panel
        discrete_hazards = [
            {
                "id": "haz_jezero_001",
                "name": "Séítah South Active Dune Ripple Field",
                "type": "dune_trap",
                "severity": "CRITICAL",
                "lat": 18.4342,
                "lon": 77.4395,
                "radius_m": 380,
                "slope_deg": 8.5,
                "description": "Deep unconsolidated basaltic sand dunes with ripple spacing 1.5m-3m. High risk of rover wheel embedment.",
                "mobility_risk": "Wheel entrapment / excessive slip (>60%)",
                "mitigation_protocol": "Mandatory 80m standoff perimeter buffer. Traverse along eastern bedrock corridor only.",
                "source_provenance": "MGS MOLA & Perseverance AutoNav slip logs"
            },
            {
                "id": "haz_jezero_002",
                "name": "Hawksbill Gap Scarp Edge",
                "type": "steep_scarp",
                "severity": "HIGH",
                "lat": 18.4542,
                "lon": 77.4095,
                "radius_m": 220,
                "slope_deg": 24.2,
                "description": "Near-vertical erosion scarp in delta fan with slope exceeding 24 degrees and loose scree talus.",
                "mobility_risk": "Rollover danger; exceeds rover static stability threshold (30°) and drive limit (15°)",
                "mitigation_protocol": "Avoid ridge line within 45m. Plan ascending route through switchback ramp.",
                "source_provenance": "MGS MOLA MEGDR Horn Slope Gradient"
            },
            {
                "id": "haz_jezero_003",
                "name": "Belva Crater Rim Boulder Field",
                "type": "boulder_field",
                "severity": "MEDIUM",
                "lat": 18.5240,
                "lon": 77.3780,
                "radius_m": 450,
                "slope_deg": 14.8,
                "description": "Impact ejecta field scattered with sub-meter to 3-meter boulders.",
                "mobility_risk": "Under-chassis clearance strike; potential high-centering.",
                "mitigation_protocol": "Reduce drive speed to 0.02 m/s; execute frequent visual odometry checks.",
                "source_provenance": "NASA Mars Trek CTX / MOLA Terrain Analysis"
            }
        ]

        return HazardsResponse(
            region_id=region_id,
            status="available",
            hazard_score=HazardScoreData(
                available=True,
                unit="0-100",
                method="project-generated heuristic",
                values=hazard_list,
            ),
            hazard_types=[
                HazardType(
                    id="steep_slope",
                    name="Steep slope",
                    basis="Derived from MOLA elevation gradient",
                    confidence="medium",
                    available=True,
                )
            ],
            provenance=HazardProvenance(
                retrieved_at=now_iso,
                limitations=HAZARD_LIMITATIONS,
            ),
            hazards=discrete_hazards,
        )


hazard_service = HazardService()
