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
        )


hazard_service = HazardService()
