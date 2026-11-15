"""Pydantic schemas for MEDA Environmental Intelligence.

Ground truth schemas backed strictly by NASA Planetary Data System (PDS4)
archive specifications for Perseverance MEDA (urn:nasa:pds:mars2020_meda).
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SensorProvenance(BaseModel):
    """PDS4 product provenance for traceable NASA data integrity."""
    bundle_lid: str = "urn:nasa:pds:mars2020_meda"
    product_lid: str
    product_filename: str
    pds_doi: str = "10.17189/1522849"
    processing_level: str  # "Calibrated" or "Derived"


class ATSObservation(BaseModel):
    """Calibrated Air Temperature Sensor (ATS) telemetry.
    
    Five independent miniature thermocouple detectors mounted at distinct positions
    and azimuths on the rover Remote Sensing Mast (RSM) and Rover Front Body (RFB).
    Arithmetic averaging is scientifically unvalidated and strictly forbidden.
    """
    available: bool = True
    sclk: float = Field(..., description="Spacecraft clock timestamp")
    lmst: str = Field(..., description="Local Mean Solar Time")
    ltst: str = Field(..., description="Local True Solar Time")
    ats_local_temp1_k: Optional[float] = Field(None, description="RSM mast detector at 50 deg azimuth (Kelvin)")
    ats_local_temp2_k: Optional[float] = Field(None, description="RSM mast detector at 155 deg azimuth (Kelvin)")
    ats_local_temp3_k: Optional[float] = Field(None, description="RSM mast detector at 290 deg azimuth (Kelvin)")
    ats_local_temp4_k: Optional[float] = Field(None, description="Rover Front Body detector at Port side (Kelvin)")
    ats_local_temp5_k: Optional[float] = Field(None, description="Rover Front Body detector at Starboard side (Kelvin)")
    rover_still: Optional[int] = Field(None, description="1 if rover was stationary, 0 if in motion")
    provenance: SensorProvenance


class PressureObservation(BaseModel):
    """Derived Pressure Sensor (PS) telemetry.
    
    Calibrated atmospheric pressure measured by Barocap silicon micromachined transducer.
    The derived uncertainty unit is declared as 'kelvin' in PDS4 labels; physical unit
    is unconfirmed in SIS tables and is designated as UNRESOLVED_IN_UPSTREAM_METADATA.
    """
    available: bool = True
    sclk: float = Field(..., description="Spacecraft clock timestamp")
    lmst: str = Field(..., description="Local Mean Solar Time")
    ltst: str = Field(..., description="Local True Solar Time")
    pressure_pa: float = Field(..., description="Calibrated ambient atmospheric pressure in Pascals")
    pressure_uncertainty: Optional[float] = Field(None, description="Raw archive uncertainty value")
    source_declared_unit: str = Field("kelvin", description="Unit declared in official PDS4 XML label")
    physical_unit_status: str = Field("UNRESOLVED_IN_UPSTREAM_METADATA", description="Unconfirmed in official SIS table")
    transducer_id: int = Field(1, description="Active Barocap transducer (1=Barocap 1)")
    provenance: SensorProvenance


class TIRSObservation(BaseModel):
    """Thermal Infrared Sensor (TIRS) telemetry.
    
    Preserves calibrated instrument sensor readings (CAL_TIRS) and hemispherical
    blackbody model derived radiative fluxes (DER_TIRS) as separate fields.
    """
    available: bool = True
    sclk: float = Field(..., description="Spacecraft clock timestamp")
    lmst: str = Field(..., description="Local Mean Solar Time")
    ltst: str = Field(..., description="Local True Solar Time")
    air_temp_k: Optional[float] = Field(None, description="TIRS Air Temperature in Kelvin (15um CO2 band, CAL_TIRS)")
    ground_brightness_temp_k: Optional[float] = Field(None, description="TIRS Ground brightness temp in Kelvin (8-14um window, CAL_TIRS)")
    ground_temp_uncertainty_k: Optional[float] = Field(None, description="1-sigma uncertainty in ground brightness temp")
    upward_sw_irradiance_cal_wm2: Optional[float] = Field(None, description="Upward SW irradiance 0.3-3.0um (W/m2, CAL_TIRS)")
    upward_lw_irradiance_cal_wm2: Optional[float] = Field(None, description="Upward LW irradiance 6.5-30.0um (W/m2, CAL_TIRS)")
    upward_lw_flux_derived_wm2: Optional[float] = Field(None, description="Hemispheric total upward LW flux (W/m2, DER_TIRS)")
    downward_lw_flux_derived_wm2: Optional[float] = Field(None, description="Hemispheric total downward LW flux (W/m2, DER_TIRS)")
    sun_outside_tirs_fov: Optional[int] = Field(None, description="1 = sun outside FOV, 0 = solar contamination")
    ground_footprint_not_in_shadow: Optional[int] = Field(None, description="1 = unshadowed ground, 0 = shadowed by rover")
    provenance: SensorProvenance


class WindObservation(BaseModel):
    """Derived Wind Sensor (WS) telemetry.
    
    Reconstructed horizontal wind speed and direction at rover mast height (~1.5 m).
    When products are not published in PDS (e.g. Sol 755), availability is set to false
    with reason PRODUCT_NOT_ARCHIVED_IN_PDS. Sentinels (999999999) evaluate to null.
    """
    available: bool = False
    status_reason: str = Field("PRODUCT_NOT_ARCHIVED_IN_PDS", description="Operational status or PDS archive state")
    sclk: Optional[float] = Field(None, description="Spacecraft clock timestamp")
    lmst: Optional[str] = Field(None, description="Local Mean Solar Time")
    ltst: Optional[str] = Field(None, description="Local True Solar Time")
    horizontal_wind_speed_ms: Optional[float] = Field(None, description="Horizontal wind speed in m/s")
    wind_direction_deg: Optional[float] = Field(None, description="Meteorological wind direction (degrees FROM which wind blows)")
    vertical_wind_speed_ms: Optional[float] = Field(None, description="Vertical wind speed component in m/s")
    rover_still: Optional[int] = Field(None, description="1 = rover stationary, 0 = rover in motion")
    provenance: Optional[SensorProvenance] = None


class RDSObservation(BaseModel):
    """Calibrated Radiation and Dust Sensor (RDS) telemetry.
    
    8 Top Mount zenith channels and 8 Lateral Mount ring channels.
    LAT1 is a blinded reference dark current channel in amperes.
    Optical channels retain archive description: radiance integrated over FOV in W/m2.
    """
    available: bool = True
    sclk: float = Field(..., description="Spacecraft clock timestamp")
    lmst: str = Field(..., description="Local Mean Solar Time")
    ltst: str = Field(..., description="Local True Solar Time")
    rds_lat_1_amp: Optional[float] = Field(None, description="Blinded reference channel dark current in amperes")
    rds_lat_channels: List[Optional[float]] = Field(
        default_factory=list,
        description="Lateral channels 2-8 radiance integrated over FOV (W/m2). Bandpass: 750nm."
    )
    rds_top_channels: List[Optional[float]] = Field(
        default_factory=list,
        description="Top channels 1-8 radiance integrated over FOV (W/m2). Channels: 255, 295, 250-400, 450, 650, 750, 190-1100, 950 nm."
    )
    optical_channels_unit: str = Field("watt/m2", description="Unit declared in official PDS4 XML label")
    archive_description: str = Field("radiance integrated over Field of View", description="Exact description from PDS4 XML label")
    physical_interpretation_status: str = Field("UNRESOLVED_RADIANCE_VS_FLUX", description="Archive defines as radiance integrated over FOV")
    rover_hga_still: Optional[int] = Field(None, description="1 = High Gain Antenna motionless, 0 = moving")
    rover_still: Optional[int] = Field(None, description="1 = rover motionless, 0 = moving")
    provenance: SensorProvenance


class MEDASolTelemetryResponse(BaseModel):
    """Full synchronized or coincident multi-sensor telemetry snapshot for a specific Sol."""
    sol: int = Field(..., description="Martian Sol number since Perseverance landing")
    site_location: str = "Jezero Crater, Mars"
    data_source: str = "NASA Planetary Data System (PDS4 Atmospheres Node)"
    bundle_lid: str = "urn:nasa:pds:mars2020_meda"
    is_historical_archive: bool = True
    ats: Optional[ATSObservation] = None
    pressure: Optional[PressureObservation] = None
    tirs: Optional[TIRSObservation] = None
    wind: WindObservation
    rds: Optional[RDSObservation] = None
    dust_optical_depth: Optional[float] = Field(None, description="Strictly null; not published in MEDA archive tables")
    scientific_disclaimer: str = (
        "Historical observational telemetry archived by NASA Mars 2020 Perseverance MEDA instrument. "
        "Not live Martian weather. All values traceable to official PDS4 labels."
    )


class SensorSummaryStats(BaseModel):
    sensor: str
    available: bool
    status_reason: str
    total_records: int
    valid_records: int
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    unit: str


class MEDASolSummaryResponse(BaseModel):
    """Statistical summary of environmental conditions over a complete Sol."""
    sol: int
    site_location: str = "Jezero Crater, Mars"
    data_source: str = "NASA Planetary Data System (PDS4 Atmospheres Node)"
    bundle_lid: str = "urn:nasa:pds:mars2020_meda"
    is_historical_archive: bool = True
    sensors_available: Dict[str, bool]
    sensor_summaries: Dict[str, SensorSummaryStats]
    time_coverage: Dict[str, Any]
    scientific_disclaimer: str = (
        "Historical observational telemetry archived by NASA Mars 2020 Perseverance MEDA instrument. "
        "All measurements informational only; no route-scoring penalties applied."
    )


class TimeSeriesSample(BaseModel):
    sclk: float
    lmst: str
    ltst: str
    ats_temp1_k: Optional[float] = None
    pressure_pa: Optional[float] = None
    air_temp_k: Optional[float] = None
    ground_brightness_temp_k: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    rds_top_7: Optional[float] = None


class MEDASolTimeSeriesResponse(BaseModel):
    """Uniformly sampled historical time-series for frontend telemetry charts."""
    sol: int
    site_location: str = "Jezero Crater, Mars"
    is_historical_archive: bool = True
    samples: List[TimeSeriesSample]
    total_samples: int

