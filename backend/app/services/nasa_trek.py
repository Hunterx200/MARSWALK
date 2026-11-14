"""NASA Mars Trek WMTS integration service."""
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
import httpx

from app.config import settings
from app.schemas.common import BoundingBox
from app.schemas.layer import MapLayer

logger = logging.getLogger(__name__)

# Known verified layer identifiers on NASA Mars Trek
TREK_LAYERS = [
    {
        "id": "nasa_mars_trek_ctx",
        "trek_product_id": "CTX_beta01_uncontrolled_5m_Caltech",
        "name": "NASA Mars Trek CTX Mosaic (Caltech Beta)",
        "attribution": "NASA/JPL-Caltech/MSSS/Murray Lab",
        "source_url": "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars",
        "capabilities_url": "https://trek.nasa.gov/tiles/Mars/EQ/CTX_beta01_uncontrolled_5m_Caltech/1.0.0/WMTSCapabilities.xml",
        "coverage": BoundingBox(min_lon=-180.0, min_lat=-65.0, max_lon=180.0, max_lat=65.0),
        "limitations": [
            "Global uncontrolled CTX mosaic at ~5-6m resolution.",
            "May contain seamlines, lighting variations, or small spatial registration offsets.",
            "Visual imagery alone does not guarantee obstacle detectability."
        ]
    },
    {
        "id": "nasa_mars_trek_mola_shade",
        "trek_product_id": "Mars_MGS_MOLA_ClrShade_merge_global_463m",
        "name": "NASA Mars Trek MOLA Color Hillshade",
        "attribution": "NASA/JPL-Caltech/GSFC",
        "source_url": "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars",
        "capabilities_url": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/WMTSCapabilities.xml",
        "coverage": BoundingBox(min_lon=-180.0, min_lat=-90.0, max_lon=180.0, max_lat=90.0),
        "limitations": [
            "Coarse (~463 m/pixel) global topographic shaded relief.",
            "Stylized color palette representing regional elevation variations."
        ]
    },
    {
        "id": "nasa_mars_trek_viking",
        "trek_product_id": "Mars_Viking_MDIM21_ClrMosaic_global_232m",
        "name": "NASA Mars Trek Viking MDIM2.1 Color Mosaic",
        "attribution": "NASA/USGS",
        "source_url": "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars",
        "capabilities_url": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/WMTSCapabilities.xml",
        "coverage": BoundingBox(min_lon=-180.0, min_lat=-90.0, max_lon=180.0, max_lat=90.0),
        "limitations": [
            "Global coverage at 232 m/pixel resolution.",
            "Viking-era sensor resolution limits rover-scale tactical detail."
        ]
    },
    {
        "id": "nasa_mars_trek_hirise_jezero_unverified",
        "trek_product_id": "NES_JEZ_MID_DEM_Mosaic_HiRISE_CTX_HRSC_GCS_MARS_07-10-2018",
        "name": "NASA Mars Trek HiRISE Jezero DEM Mosaic (Unverified Candidate)",
        "attribution": "NASA/JPL-Caltech/Univ. of Arizona",
        "source_url": "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars",
        "capabilities_url": "https://trek.nasa.gov/tiles/Mars/EQ/NES_JEZ_MID_DEM_Mosaic_HiRISE_CTX_HRSC_GCS_MARS_07-10-2018/1.0.0/WMTSCapabilities.xml",
        "coverage": BoundingBox(min_lon=77.0, min_lat=18.0, max_lon=78.5, max_lat=19.5),
        "limitations": [
            "WMTS endpoint returned 404 during automated capability verification.",
            "Layer marked as unavailable in compliance with NASA data verification rules."
        ]
    }
]


class NasaTrekService:
    def __init__(self):
        self._capabilities_cache: Dict[str, Dict[str, Any]] = {}

    async def check_service_health(self) -> str:
        """Probe Mars Trek endpoint for health check. Returns 'available' or 'unavailable'."""
        try:
            async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
                r = await client.get(
                    "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/WMTSCapabilities.xml"
                )
                if r.status_code == 200 and ("<Capabilities" in r.text or "xml" in r.text):
                    return "available"
                return "unavailable"
        except Exception as e:
            logger.warning(f"Mars Trek health probe failed: {e}")
            return "unavailable"

    async def validate_wmts_capabilities(self, capabilities_url: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse WMTSCapabilities.xml. Extract ResourceURL template, format, tileMatrixSet."""
        if capabilities_url in self._capabilities_cache:
            return self._capabilities_cache[capabilities_url]

        try:
            async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds, follow_redirects=True) as client:
                resp = await client.get(capabilities_url)
                if resp.status_code != 200:
                    logger.info(f"WMTS endpoint {capabilities_url} returned HTTP {resp.status_code}")
                    return None
                
                xml_text = resp.text
                root = ET.fromstring(xml_text)
                
                # Namespace handling
                ns = {
                    "wmts": "http://www.opengis.net/wmts/1.0",
                    "ows": "http://www.opengis.net/ows/1.1",
                    "xlink": "http://www.w3.org/1999/xlink",
                }
                
                # Find ResourceURL template
                resource_url_elem = root.find(".//wmts:ResourceURL", ns) or root.find(".//ResourceURL")
                template_url = None
                format_ext = "image/jpeg"
                if resource_url_elem is not None:
                    template_url = resource_url_elem.attrib.get("template")
                    format_ext = resource_url_elem.attrib.get("format", format_ext)

                # Fallback to GetTile endpoint if ResourceURL element not present
                if not template_url:
                    get_tile_elem = root.find(".//ows:Operation[@name='GetTile']//ows:Get", ns)
                    if get_tile_elem is not None:
                        href = get_tile_elem.attrib.get("{http://www.w3.org/1999/xlink}href")
                        if href:
                            template_url = href.rstrip("/") + "/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpg"

                # Standardize OpenLayers REST template:
                # Replace double slashes if present
                if template_url:
                    template_url = template_url.replace("//{Style}", "/{Style}")
                    # Replace {Style} and {TileMatrixSet} defaults for direct client rendering if known
                    template_url = template_url.replace("{Style}", "default").replace("{TileMatrixSet}", "default028mm")

                parsed = {
                    "valid": True,
                    "template_url": template_url,
                    "format": format_ext,
                }
                self._capabilities_cache[capabilities_url] = parsed
                return parsed
        except Exception as e:
            logger.warning(f"Failed to validate WMTS capabilities at {capabilities_url}: {e}")
            return None

    async def get_layers(self, region_id: str) -> List[MapLayer]:
        """Return list of map layers with validated status and explicit limitation messages."""
        layers_out: List[MapLayer] = []
        for defn in TREK_LAYERS:
            cap_info = await self.validate_wmts_capabilities(defn["capabilities_url"])
            if cap_info and cap_info.get("template_url"):
                layers_out.append(
                    MapLayer(
                        id=defn["id"],
                        name=defn["name"],
                        type="wmts",
                        status="available",
                        url=cap_info["template_url"],
                        attribution=defn["attribution"],
                        source_url=defn["source_url"],
                        coverage=defn["coverage"],
                        limitations=defn["limitations"],
                    )
                )
            else:
                layers_out.append(
                    MapLayer(
                        id=defn["id"],
                        name=defn["name"],
                        type="wmts",
                        status="unavailable",
                        url=None,
                        attribution=defn["attribution"],
                        source_url=defn["source_url"],
                        coverage=defn["coverage"],
                        limitations=defn["limitations"] + [
                            "WMTS GetCapabilities validation was unreachable or failed. Layer is offline."
                        ],
                    )
                )
        return layers_out


nasa_trek_service = NasaTrekService()
