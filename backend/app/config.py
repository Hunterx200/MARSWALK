"""Configuration settings for MARSWALK backend."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MARSWALK application settings."""
    app_name: str = "marswalk-backend"
    version: str = "0.1.0"
    debug: bool = False
    
    # Primary region: Jezero Crater
    jezero_id: str = "jezero_crater"
    jezero_name: str = "Jezero Crater"
    jezero_description: str = "Primary MARSWALK exploration region"
    
    # Bounded region coordinates (Mars geographic, degrees)
    min_lon: float = 77.0
    max_lon: float = 77.8
    min_lat: float = 18.2
    max_lat: float = 18.7
    crs: str = "EPSG:4326"
    
    # NASA endpoints
    nasa_trek_mars_base_url: str = "https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars"
    nasa_trek_wmts_capabilities_url: str = "https://trek.nasa.gov/tiles/Mars/EQ/WMTS/1.0.0/WMTSCapabilities.xml"
    nasa_pds_base_url: str = "https://pds-imaging.jpl.nasa.gov/tools/atlas/documentation/docs/api/search"
    
    # HTTP client timeout in seconds
    upstream_timeout_seconds: float = 8.0
    
    # CORS
    cors_origins: List[str] = ["*"]
    
    model_config = SettingsConfigDict(env_prefix="MARSWALK_", env_file=".env", extra="ignore")


settings = Settings()
