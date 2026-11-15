/**
 * MARSWALK API Contract Types
 * Coordinates semantic: Mars Latitude (-90 to +90 degrees North) and Longitude (-180 to +180 or 0 to 360 degrees East).
 * Target region: Jezero Crater (~18.38°N, 77.58°E).
 */

export interface HealthStatus {
  status: 'healthy' | 'ok' | 'degraded' | 'offline';
  service?: string;
  version: string;
  timestamp?: string;
  time_utc?: string;
  services?: {
    nasa_trek: 'available' | 'degraded' | 'unavailable';
    mola_elevation: 'available' | 'synthetic_fallback';
    pathfinder: 'ready' | 'busy' | 'error';
  };
  dependencies?: {
    nasa_trek?: string;
    nasa_pds?: string;
    route_engine?: string;
  };
  environment?: string;
}

export interface RegionBounds {
  min_lat: number;
  max_lat: number;
  min_lon: number;
  max_lon: number;
}

export interface RegionInfo {
  id: string;
  name: string;
  target_body: 'Mars' | string;
  center: {
    lat: number;
    lon: number;
  };
  bounds: RegionBounds;
  elevation_range_m: {
    min: number;
    max: number;
    datum: string;
  };
  description: string;
  primary_mission: string;
  landing_site: {
    name: string;
    lat: number;
    lon: number;
    sol_0_date: string;
  };
}

export interface MapLayerConfig {
  id: string;
  name: string;
  category: 'basemap' | 'elevation' | 'hazard' | 'science' | 'traverse';
  type: 'wmts' | 'xyz' | 'wms' | 'vector' | 'raster';
  url?: string;
  attribution: string;
  visible: boolean;
  opacity: number;
  description: string;
  coverage: string;
  resolution?: string;
  verified_nasa_source: boolean;
  limitations: string;
}

export interface Observation {
  id: string;
  sol: number;
  target_name: string;
  feature_type: 'delta_remnant' | 'crater_rim' | 'dune_field' | 'sedimentary_rock' | 'sample_depot' | 'landing_site' | 'science_target' | string;
  lat: number;
  lon: number;
  elevation_m: number;
  instruments: string[];
  description: string;
  sample_tube_id?: string;
  scientific_value: 'HIGH' | 'CRITICAL' | 'MODERATE' | string;
  nasa_pds_reference?: string;
}

export interface TerrainSummary {
  region_id: string;
  sample_resolution_m: number;
  min_elevation_m: number;
  max_elevation_m: number;
  mean_slope_deg: number;
  max_slope_deg: number;
  roughness_index: number;
  data_coverage_percent: number;
  source_dataset: string;
  disclaimer: string;
}

export interface HazardZone {
  id: string;
  name: string;
  type: 'steep_scarp' | 'dune_trap' | 'boulder_field' | 'crater_drop' | 'steep_slope' | string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;
  lat: number;
  lon: number;
  radius_m: number;
  slope_deg?: number;
  description: string;
  mobility_risk: string;
  mitigation_protocol: string;
  source_provenance: string;
}

/**
 * Route optimization profiles matching Developer C's algorithm module:
 * - 'direct': Shortest traverse distance / minimal detour (UI label: Fastest)
 * - 'balanced': Nominal trade-off between distance, slope, and hazard proximity (UI label: Balanced)
 * - 'safe': Maximum standoff buffer from hazards, strict slope thresholds (UI label: Safest)
 * 
 * Note: 'science' is disabled/unsupported until a validated backend implementation exists.
 */
export type RouteProfile = 'direct' | 'balanced' | 'safe';

export interface RoutePlanRequest {
  start: {
    lat: number;
    lon: number;
    name?: string;
  };
  goal: {
    lat: number;
    lon: number;
    name?: string;
  };
  profile: RouteProfile;
  max_slope_deg: number;
  avoid_sand_dunes?: boolean;
  rover_model?: 'Perseverance-Class' | 'Curiosity-Class' | 'Lightweight-Scout' | string;
}

export interface Waypoint {
  index: number;
  lat: number;
  lon: number;
  elevation_m: number;
  slope_deg: number;
  roughness: number;
  segment_distance_m: number;
  cumulative_distance_m: number;
  estimated_sol: number;
  risk_level: 'MINIMAL' | 'LOW' | 'MEDIUM' | 'HIGH' | string;
  notes?: string;
}

export interface RouteAlternative {
  id: string;
  name: string;
  profile: RouteProfile;
  distance_m: number;
  duration_sols: number;
  max_slope_deg: number;
  avg_slope_deg: number;
  risk_score: number; // 0 - 100
  risk_category: 'LOW' | 'MEDIUM' | 'HIGH' | string;
  science_targets_count: number;
  waypoints: Waypoint[];
  path_coordinates: [number, number][]; // [lon, lat] pairs for OpenLayers
  description: string;
  energy_budget_kwh?: number;
}

export interface RouteComparisonItem {
  profile: string;
  found: boolean;
  distance_m: number;
  estimated_risk_score: number;
  max_slope_deg: number;
  avg_slope_deg: number;
  traverse_time_hr: number;
  total_cost: number;
}

export interface RoutePlanResponse {
  status: 'success' | 'partial' | 'failed';
  isLiveBackend: boolean; // true if received from live FastAPI endpoint, false if demo fallback
  route_id: string;
  algorithm: string;
  profile: RouteProfile;
  message?: string;
  summary: {
    total_distance_m: number;
    estimated_duration_sols: number;
    max_slope_deg: number;
    avg_slope_deg: number;
    overall_risk_score: number;
    risk_category: 'LOW' | 'MEDIUM' | 'HIGH';
    energy_budget_kwh?: number;
  };
  waypoints: Waypoint[];
  path_coordinates: [number, number][]; // [lon, lat] for OpenLayers
  alternatives: RouteAlternative[];
  warnings: string[];
  provenance: {
    elevation_model: string;
    imagery_model: string;
    hazard_model: string;
    generated_at: string;
    disclaimer: string;
  };
  geojson?: {
    type: string;
    features: any[];
    properties?: Record<string, any>;
  };
  comparison?: RouteComparisonItem[];
}

export interface MissionPlan {
  id: string;
  title: string;
  created_at: string;
  operator: string;
  target_region: string;
  route: RoutePlanResponse;
  selected_profile: string;
  observations_targeted: Observation[];
  hazard_mitigations: string[];
  notes: string;
}

/**
 * Save mission request adhering to exact backend schema (MissionCreateRequest in backend/app/schemas/mission.py)
 */
export interface SaveMissionRequest {
  region_id?: string;
  name: string;
  route_id: string;
  notes?: string;
}

/**
 * Backend mission response adhering to backend/app/schemas/mission.py
 */
export interface SaveMissionResponse {
  id: string;
  name: string;
  region_id: string;
  route_id: string;
  created_at: string;
  status: string;
  summary: {
    distance_meters: number;
    risk_level: string;
    mean_slope_degrees: number;
    maximum_slope_degrees: number;
    hazard_score: number;
    observations: number;
  };
  report: {
    title: string;
    sections: Array<{
      title: string;
      content: string;
    }>;
  };
  notes?: string;
}

/**
 * MEDA Environmental Intelligence Types
 * Strict PDS4 archive schemas for NASA Mars 2020 Perseverance MEDA instrument.
 * Historical observation telemetry at Jezero Crater, Mars.
 */

export interface SensorProvenance {
  bundle_lid: string;
  product_lid: string;
  product_filename: string;
  pds_doi: string;
  processing_level: string;
}

export interface ATSObservation {
  available: boolean;
  sclk: number;
  lmst: string;
  ltst: string;
  ats_local_temp1_k: number | null;
  ats_local_temp2_k: number | null;
  ats_local_temp3_k: number | null;
  ats_local_temp4_k: number | null;
  ats_local_temp5_k: number | null;
  rover_still?: number | null;
  provenance: SensorProvenance;
}

export interface PressureObservation {
  available: boolean;
  sclk: number;
  lmst: string;
  ltst: string;
  pressure_pa: number;
  pressure_uncertainty: number | null;
  source_declared_unit: string;
  physical_unit_status: string;
  transducer_id: number;
  provenance: SensorProvenance;
}

export interface TIRSObservation {
  available: boolean;
  sclk: number;
  lmst: string;
  ltst: string;
  air_temp_k: number | null;
  ground_brightness_temp_k: number | null;
  ground_temp_uncertainty_k: number | null;
  upward_sw_irradiance_cal_wm2: number | null;
  upward_lw_irradiance_cal_wm2: number | null;
  upward_lw_flux_derived_wm2: number | null;
  downward_lw_flux_derived_wm2: number | null;
  sun_outside_tirs_fov?: number | null;
  ground_footprint_not_in_shadow?: number | null;
  provenance: SensorProvenance;
}

export interface WindObservation {
  available: boolean;
  status_reason: string;
  sclk: number | null;
  lmst: string | null;
  ltst: string | null;
  horizontal_wind_speed_ms: number | null;
  wind_direction_deg: number | null;
  vertical_wind_speed_ms: number | null;
  rover_still?: number | null;
  provenance?: SensorProvenance | null;
}

export interface RDSObservation {
  available: boolean;
  sclk: number;
  lmst: string;
  ltst: string;
  rds_lat_1_amp: number | null;
  rds_lat_channels: (number | null)[];
  rds_top_channels: (number | null)[];
  optical_channels_unit: string;
  archive_description?: string;
  physical_interpretation_status: string;
  rover_hga_still?: number | null;
  rover_still?: number | null;
  provenance: SensorProvenance;
}

export interface MEDASolTelemetryResponse {
  sol: number;
  site_location: string;
  data_source: string;
  bundle_lid: string;
  is_historical_archive: boolean;
  ats?: ATSObservation | null;
  pressure?: PressureObservation | null;
  tirs?: TIRSObservation | null;
  wind: WindObservation;
  rds?: RDSObservation | null;
  dust_optical_depth?: number | null;
  scientific_disclaimer: string;
}

export interface SensorSummaryStats {
  sensor: string;
  available: boolean;
  status_reason: string;
  total_records: number;
  valid_records: number;
  min_value?: number | null;
  max_value?: number | null;
  mean_value?: number | null;
  unit: string;
}

export interface MEDASolSummaryResponse {
  sol: number;
  site_location: string;
  data_source: string;
  bundle_lid: string;
  is_historical_archive: boolean;
  sensors_available: Record<string, boolean>;
  sensor_summaries: Record<string, SensorSummaryStats>;
  time_coverage: Record<string, any>;
  scientific_disclaimer: string;
}

export interface TimeSeriesSample {
  sclk: number;
  lmst: string;
  ltst: string;
  ats_temp1_k?: number | null;
  pressure_pa?: number | null;
  air_temp_k?: number | null;
  ground_brightness_temp_k?: number | null;
  wind_speed_ms?: number | null;
  wind_direction_deg?: number | null;
  rds_top_7?: number | null;
}

export interface MEDASolTimeSeriesResponse {
  sol: number;
  site_location: string;
  is_historical_archive: boolean;
  samples: TimeSeriesSample[];
  total_samples: number;
}
