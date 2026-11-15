"""NASA PDS and observation service."""
import logging
from typing import List, Optional
import httpx

from app.config import settings
from app.core.provenance import get_current_utc_iso, DEMO_OBSERVATION_LIMITATION
from app.schemas.common import ProvenanceMetadata
from app.schemas.observation import ObservationItem

logger = logging.getLogger(__name__)

# Small clearly-labeled demonstration dataset for Jezero Crater rover exploration
DEMO_OBSERVATIONS = [
    {
        "id": "demo_perseverance_octavia_butler",
        "title": "Octavia E. Butler Landing Site (Sol 0)",
        "type": "science_target",
        "longitude": 77.4509,
        "latitude": 18.4447,
        "sol": 0,
        "acquired_at": "2021-02-18T20:55:00Z",
        "description": "Touchdown location of the Mars 2020 Perseverance Rover in Jezero Crater.",
        "thumbnail_url": "https://mars.nasa.gov/system/resources/detail_files/25679_PIA24424-web.jpg",
    },
    {
        "id": "demo_perseverance_delta_front",
        "title": "Kodiak Mesa Science Outcrop",
        "type": "imagery",
        "longitude": 77.3980,
        "latitude": 18.4230,
        "sol": 74,
        "acquired_at": "2021-05-04T12:00:00Z",
        "description": "Stratified sedimentary delta deposit displaying preserved lacustrine bedding.",
        "thumbnail_url": "https://mars.nasa.gov/system/resources/detail_files/26250_PIA24838-web.jpg",
    },
    {
        "id": "demo_perseverance_belva_crater",
        "title": "Belva Impact Crater Rim",
        "type": "rover_observation",
        "longitude": 77.3400,
        "latitude": 18.5200,
        "sol": 765,
        "acquired_at": "2023-04-15T10:30:00Z",
        "description": "Large impact crater exposing deep Jezero crustal stratigraphy and hydrothermal boulders.",
        "thumbnail_url": "https://mars.nasa.gov/system/resources/detail_files/27447_PIA25847-web.jpg",
    },
    {
        "id": "demo_perseverance_sample_depot",
        "title": "Three Forks Sample Cache Depot",
        "type": "science_target",
        "longitude": 77.4200,
        "latitude": 18.4600,
        "sol": 660,
        "acquired_at": "2022-12-21T14:15:00Z",
        "description": "First sample depot created on another world, with 10 sealed titanium sample tubes.",
        "thumbnail_url": "https://mars.nasa.gov/system/resources/detail_files/27238_PIA25667-web.jpg",
    },
]


class NasaPdsService:
    async def check_service_health(self) -> str:
        """Probe NASA PDS API. Returns 'available' or 'unavailable'."""
        try:
            async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
                r = await client.get("https://pds-imaging.jpl.nasa.gov/tools/atlas/documentation/docs/api/search")
                if r.status_code == 200:
                    return "available"
                return "unavailable"
        except Exception as e:
            logger.warning(f"NASA PDS health probe failed: {e}")
            return "unavailable"

    async def get_observations(
        self,
        region_id: str,
        limit: int = 50,
        source_filter: Optional[str] = None
    ) -> List[ObservationItem]:
        """Fetch observations. If source is live or unspecified, try live query; fall back to demo dataset."""
        now_iso = get_current_utc_iso()
        
        # Check if live query is explicitly requested and attempted
        if source_filter and "nasa" in source_filter.lower():
            try:
                async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as client:
                    url = "https://pds-imaging.jpl.nasa.gov/api/search/atlas/_search"
                    query = {
                        "query": {
                            "match": {"target.name": "Mars"}
                        },
                        "size": min(limit, 20)
                    }
                    resp = await client.post(url, json=query)
                    if resp.status_code == 200:
                        hits = resp.json().get("hits", {}).get("hits", [])
                        live_items: List[ObservationItem] = []
                        for h in hits:
                            src = h.get("_source", {})
                            obs_id = h.get("_id", "pds_record")
                            uri = src.get("uri", "")

                            # Extract geographic coordinates if available in PDS product metadata
                            lon = (
                                src.get("westernmost_longitude")
                                or src.get("easternmost_longitude")
                                or src.get("longitude")
                            )
                            lat = (
                                src.get("maximum_latitude")
                                or src.get("minimum_latitude")
                                or src.get("latitude")
                            )
                            if lon is None or lat is None:
                                continue
                            try:
                                lon_f = float(lon)
                                lat_f = float(lat)
                            except (ValueError, TypeError):
                                continue

                            # Filter strictly by Jezero region bounds
                            if not (settings.min_lon <= lon_f <= settings.max_lon and settings.min_lat <= lat_f <= settings.max_lat):
                                continue

                            live_items.append(
                                ObservationItem(
                                    id=f"pds_{obs_id}",
                                    title=f"NASA PDS Atlas Product {obs_id[:12]}",
                                    type="imagery",
                                    longitude=round(lon_f, 6),
                                    latitude=round(lat_f, 6),
                                    sol=None,
                                    acquired_at=None,
                                    source="NASA PDS Imaging Atlas",
                                    source_url=f"https://pds-imaging.jpl.nasa.gov/atlas/search?q={obs_id}",
                                    dataset_id=src.get("bundle_id"),
                                    description=f"PDS4 product archived at URI {uri}",
                                    thumbnail_url=None,
                                    provenance=ProvenanceMetadata(
                                        retrieved_at=now_iso,
                                        verification_status="verified",
                                        limitations=["Live metadata from NASA PDS Imaging Node search API."]
                                    )
                                )
                            )
                        if live_items:
                            return live_items[:limit]
            except Exception as e:
                logger.info(f"Live PDS query failed or timed out, returning labeled demo dataset: {e}")

        # Return small clearly labeled local demonstration dataset
        demo_items: List[ObservationItem] = []
        for d in DEMO_OBSERVATIONS[:limit]:
            demo_items.append(
                ObservationItem(
                    id=d["id"],
                    title=d["title"],
                    type=d["type"],
                    longitude=d["longitude"],
                    latitude=d["latitude"],
                    sol=d.get("sol"),
                    acquired_at=d.get("acquired_at"),
                    source="MARSWALK demo dataset",
                    source_url="https://mars.nasa.gov/mars2020/",
                    dataset_id="MARSWALK-JEZERO-DEMO-2026",
                    description=d["description"],
                    thumbnail_url=d.get("thumbnail_url"),
                    provenance=ProvenanceMetadata(
                        retrieved_at=now_iso,
                        verification_status="simulated",
                        limitations=[
                            DEMO_OBSERVATION_LIMITATION,
                            "Synthesized science waypoint markers for mission-planning UI demonstration."
                        ]
                    )
                )
            )
        return demo_items


nasa_pds_service = NasaPdsService()
