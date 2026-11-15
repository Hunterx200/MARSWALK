import React, { useState, useEffect, useRef } from 'react';
import {
  RoutePlanRequest,
  RoutePlanResponse,
  Waypoint,
  RouteProfile,
  TerrainSummary,
  SaveMissionResponse
} from '../../types/api';
import { MarswalkApiClient } from '../../services/apiClient';
import { MarsMapController, getRouteProfileColor } from '../../services/mapManager';
import {
  Navigation,
  Flag,
  Target,
  ShieldCheck,
  Zap,
  Scale,
  Microscope,
  AlertTriangle,
  CheckCircle,
  ListOrdered,
  XCircle,
  Activity,
  Save,
  Mountain,
  TableProperties
} from 'lucide-react';

interface RoutePlannerPanelProps {
  controller: MarsMapController;
  startPoint: { lat: number; lon: number; name?: string };
  setStartPoint: (pt: { lat: number; lon: number; name?: string }) => void;
  goalPoint: { lat: number; lon: number; name?: string };
  setGoalPoint: (pt: { lat: number; lon: number; name?: string }) => void;
  plannedRoute: RoutePlanResponse | null;
  setPlannedRoute: (route: RoutePlanResponse | null) => void;
  onSelectWaypoint: (wp: Waypoint) => void;
  terrainSummary?: TerrainSummary | null;
  onActiveWaypointsChange?: (waypoints: Waypoint[]) => void;
  onOpenReport?: () => void;
  activeAlternativeId?: string;
  setActiveAlternativeId?: (id: string) => void;
  onActiveProfileChange?: (profile: RouteProfile) => void;
}

const PRESET_LOCATIONS = [
  { name: 'Octavia E. Butler Landing (Sol 0)', lat: 18.4447, lon: 77.4508 },
  { name: 'Three Forks Sample Depot', lat: 18.4550, lon: 77.4190 },
  { name: 'Enchanted Lake (Delta Base)', lat: 18.4482, lon: 77.4121 },
  { name: 'Skinner Ridge (Delta Scarp)', lat: 18.4526, lon: 77.4019 },
  { name: 'Kodiak Butte (Delta Remnant)', lat: 18.4118, lon: 77.4485 },
  { name: 'Belva Crater South Rim', lat: 18.5204, lon: 77.3752 },
  { name: 'Artuby Ridge / Séítah Corridor', lat: 18.4325, lon: 77.4410 },
];

export const RoutePlannerPanel: React.FC<RoutePlannerPanelProps> = ({
  controller,
  startPoint,
  setStartPoint,
  goalPoint,
  setGoalPoint,
  plannedRoute,
  setPlannedRoute,
  onSelectWaypoint,
  terrainSummary,
  onActiveWaypointsChange,
  onOpenReport,
  activeAlternativeId: propsActiveId,
  setActiveAlternativeId: propsSetActiveId,
  onActiveProfileChange,
}) => {
  const [profile, setProfile] = useState<RouteProfile>('balanced');
  const [maxSlope, setMaxSlope] = useState<number>(15.0);
  const [avoidDunes, setAvoidDunes] = useState<boolean>(true);
  const [isPlanning, setIsPlanning] = useState<boolean>(false);
  const [internalActiveId, setInternalActiveId] = useState<string>('primary');
  const planRequestIdRef = useRef<number>(0);

  const activeAlternativeId = propsActiveId ?? internalActiveId;
  const setActiveAlternativeId = (id: string) => {
    setInternalActiveId(id);
    propsSetActiveId?.(id);
  };

  // Save Mission state
  const [missionName, setMissionName] = useState<string>('Jezero Surface Traverse');
  const [missionNotes, setMissionNotes] = useState<string>('Perseverance research traverse path');
  const [isSavingMission, setIsSavingMission] = useState<boolean>(false);
  const [savedMission, setSavedMission] = useState<SaveMissionResponse | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Auto-populate default mission name based on profile and locations
  useEffect(() => {
    if (plannedRoute?.status === 'success') {
      const startLabel = startPoint.name?.split('(')[0]?.trim() || 'Start';
      const goalLabel = goalPoint.name?.split('(')[0]?.trim() || 'Goal';
      setMissionName(`${startLabel} to ${goalLabel} [${profile.toUpperCase()}]`);
    }
  }, [plannedRoute, profile, startPoint.name, goalPoint.name]);

  const handleSelectRoute = (routeId: string, currentPlan: RoutePlanResponse | null = plannedRoute) => {
    if (!currentPlan) return;
    setActiveAlternativeId(routeId);

    const isPrimary = (routeId === 'primary');
    const selectedAlt = isPrimary ? null : (currentPlan.alternatives || []).find(a => a.id === routeId);

    const selectedProfile = isPrimary
      ? (currentPlan.profile || profile)
      : (selectedAlt?.profile || 'balanced');

    // Keep active trajectory profile button strictly synchronized with selected route
    setProfile(selectedProfile);
    onActiveProfileChange?.(selectedProfile);

    const waypoints = isPrimary
      ? (currentPlan.waypoints || [])
      : (selectedAlt?.waypoints || []);
    onActiveWaypointsChange?.(waypoints);

    controller.setPlannedRoute(
      currentPlan.path_coordinates,
      currentPlan.waypoints,
      currentPlan.alternatives || [],
      routeId,
      currentPlan.profile || profile
    );
  };

  const handleProfileSelect = (newProfile: RouteProfile) => {
    setProfile(newProfile);
    onActiveProfileChange?.(newProfile);

    // If route results already exist, immediately activate corresponding route geometry
    if (plannedRoute && plannedRoute.status === 'success') {
      const primaryProf = (plannedRoute.profile || 'balanced').toLowerCase();
      if (primaryProf === newProfile) {
        handleSelectRoute('primary', plannedRoute);
        return;
      }

      const matchingAlt = (plannedRoute.alternatives || []).find(
        a => a.profile.toLowerCase() === newProfile
      );
      if (matchingAlt) {
        handleSelectRoute(matchingAlt.id, plannedRoute);
      }
    }
  };

  const handlePlanRoute = async () => {
    const thisRequestId = ++planRequestIdRef.current;
    setIsPlanning(true);
    setSavedMission(null);
    setSaveError(null);

    const req: RoutePlanRequest = {
      start: startPoint,
      goal: goalPoint,
      profile: profile,
      max_slope_deg: maxSlope,
      avoid_sand_dunes: avoidDunes,
      rover_model: 'Perseverance-Class',
    };

    try {
      const response = await MarswalkApiClient.planRoute(req);
      // Discard stale in-flight response if a newer calculation was launched
      if (thisRequestId !== planRequestIdRef.current) {
        return;
      }
      setPlannedRoute(response);
      handleSelectRoute('primary', response);
    } catch (err) {
      if (thisRequestId === planRequestIdRef.current) {
        console.error('Failed to plan route:', err);
      }
    } finally {
      if (thisRequestId === planRequestIdRef.current) {
        setIsPlanning(false);
      }
    }
  };

  const handleSaveMission = async () => {
    if (!plannedRoute) return;
    setIsSavingMission(true);
    setSaveError(null);

    try {
      const res = await MarswalkApiClient.saveMission({
        region_id: 'jezero_crater',
        name: missionName.trim() || 'Jezero Mission Traverse',
        route_id: plannedRoute.route_id,
        notes: missionNotes.trim() || undefined,
      });
      setSavedMission(res);
    } catch (err: any) {
      console.error('Failed to save mission:', err);
      setSaveError(err?.message || 'Failed to save mission plan to backend.');
    } finally {
      setIsSavingMission(false);
    }
  };

  const activeWaypoints = activeAlternativeId === 'primary'
    ? (plannedRoute?.waypoints || [])
    : (plannedRoute?.alternatives?.find(a => a.id === activeAlternativeId)?.waypoints || []);

  const activeSummary = activeAlternativeId === 'primary'
    ? plannedRoute?.summary
    : plannedRoute?.alternatives?.find(a => a.id === activeAlternativeId) && {
      total_distance_m: plannedRoute.alternatives.find(a => a.id === activeAlternativeId)!.distance_m,
      estimated_duration_sols: plannedRoute.alternatives.find(a => a.id === activeAlternativeId)!.duration_sols,
      max_slope_deg: plannedRoute.alternatives.find(a => a.id === activeAlternativeId)!.max_slope_deg,
      avg_slope_deg: plannedRoute.alternatives.find(a => a.id === activeAlternativeId)!.avg_slope_deg,
      overall_risk_score: plannedRoute.alternatives.find(a => a.id === activeAlternativeId)!.risk_score,
      risk_category: plannedRoute.alternatives.find(a => a.id === activeAlternativeId)!.risk_category,
    };

  return (
    <div className="space-y-4 text-xs select-none">
      {/* Terrain Elevation & Topography Summary (from actual backend MOLA DEM) */}
      {terrainSummary && (
        <div className="p-3 rounded-xl bg-space-900 border border-space-750 space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="font-mono font-bold text-slate-300 text-[11px] uppercase tracking-wider flex items-center">
              <Mountain className="w-3.5 h-3.5 text-telemetry-cyan mr-1.5" />
              Jezero Topography Summary
            </h4>
            <span className="text-[10px] text-slate-500 font-mono">
              NASA MOLA 128ppd
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
            <div className="p-2 rounded bg-space-850 border border-space-750">
              <span className="text-[9px] text-slate-500 uppercase">Elevation Datum</span>
              <div className="text-slate-200 font-bold mt-0.5">
                {terrainSummary.min_elevation_m}m <span className="text-slate-500">to</span> {terrainSummary.max_elevation_m}m
              </div>
            </div>

            <div className="p-2 rounded bg-space-850 border border-space-750">
              <span className="text-[9px] text-slate-500 uppercase">Gradient (Mean / Peak)</span>
              <div className="text-amber-400 font-bold mt-0.5">
                {terrainSummary.mean_slope_deg}° <span className="text-slate-500">/</span> {terrainSummary.max_slope_deg}°
              </div>
            </div>

            <div className="p-2 rounded bg-space-850 border border-space-750">
              <span className="text-[9px] text-slate-500 uppercase">DEM Spatial Cell</span>
              <div className="text-slate-300 font-bold mt-0.5">
                {terrainSummary.sample_resolution_m} m/pixel
              </div>
            </div>

            <div className="p-2 rounded bg-space-850 border border-space-750">
              <span className="text-[9px] text-slate-500 uppercase">Dataset Coverage</span>
              <div className="text-emerald-400 font-bold mt-0.5">
                {terrainSummary.data_coverage_percent}% Verified
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Start / Goal Coordinates Section */}
      <div className="space-y-3 p-3 rounded-xl bg-space-850/80 border border-space-700/80">
        <h4 className="font-mono font-bold text-slate-300 text-[11px] uppercase tracking-wider flex items-center">
          <Navigation className="w-3.5 h-3.5 text-mars-400 mr-1.5" />
          Mission Waypoint Constraints
        </h4>

        {/* Start Point */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span className="flex items-center text-emerald-400 font-semibold">
              <Flag className="w-3 h-3 mr-1" />
              Start Point (Rover Origin)
            </span>
            <span className="font-mono text-[10px] text-slate-500">
              {startPoint.lat.toFixed(4)}°N, {startPoint.lon.toFixed(4)}°E
            </span>
          </div>
          <select
            className="w-full bg-space-900 border border-space-700 rounded-md px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-emerald-500 font-mono"
            value={startPoint.name || ''}
            onChange={e => {
              const preset = PRESET_LOCATIONS.find(p => p.name === e.target.value);
              if (preset) {
                setStartPoint(preset);
                controller.setMissionPins(preset, goalPoint);
                controller.panTo(preset.lon, preset.lat, 13);
              }
            }}
          >
            {PRESET_LOCATIONS.map(p => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* Goal Point */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-slate-400 text-[11px]">
            <span className="flex items-center text-amber-400 font-semibold">
              <Target className="w-3 h-3 mr-1" />
              Target Destination (Science Goal)
            </span>
            <span className="font-mono text-[10px] text-slate-500">
              {goalPoint.lat.toFixed(4)}°N, {goalPoint.lon.toFixed(4)}°E
            </span>
          </div>
          <select
            className="w-full bg-space-900 border border-space-700 rounded-md px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-amber-500 font-mono"
            value={goalPoint.name || ''}
            onChange={e => {
              const preset = PRESET_LOCATIONS.find(p => p.name === e.target.value);
              if (preset) {
                setGoalPoint(preset);
                controller.setMissionPins(startPoint, preset);
                controller.panTo(preset.lon, preset.lat, 13);
              }
            }}
          >
            {PRESET_LOCATIONS.map(p => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Pathfinding Optimization Profile */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-[11px] font-mono text-slate-400 font-semibold uppercase tracking-wider">
            A* Trajectory Profile
          </label>
          <span className="text-[10px] font-mono text-slate-400">
            Active: <span className="font-bold uppercase text-white">{profile}</span>
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {/* Balanced */}
          <button
            type="button"
            onClick={() => handleProfileSelect('balanced')}
            className={`p-2.5 rounded-lg border text-left transition-all cursor-pointer relative ${
              profile === 'balanced'
                ? 'bg-cyan-950/80 border-cyan-400 text-white shadow-[0_0_12px_rgba(6,182,212,0.35)] ring-1 ring-cyan-500/50'
                : 'bg-space-850/60 border-space-750 text-slate-400 hover:text-slate-200 hover:border-space-650'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5 font-bold text-xs">
                <Scale className={`w-3.5 h-3.5 ${profile === 'balanced' ? 'text-cyan-400' : 'text-slate-500'}`} />
                <span className={profile === 'balanced' ? 'text-cyan-200' : 'text-slate-300'}>Balanced</span>
              </div>
              {profile === 'balanced' ? (
                <CheckCircle className="w-3.5 h-3.5 text-cyan-400 animate-in zoom-in-75 flex-shrink-0" />
              ) : (
                <div className="w-3 h-3 rounded-full border border-space-650 flex-shrink-0" />
              )}
            </div>
            <p className="text-[10px] text-slate-400 mt-1">Cyan route • Nominal trade-off</p>
          </button>

          {/* Safest -> safe */}
          <button
            type="button"
            onClick={() => handleProfileSelect('safe')}
            className={`p-2.5 rounded-lg border text-left transition-all cursor-pointer relative ${
              profile === 'safe'
                ? 'bg-emerald-950/80 border-emerald-400 text-white shadow-[0_0_12px_rgba(16,185,129,0.35)] ring-1 ring-emerald-500/50'
                : 'bg-space-850/60 border-space-750 text-slate-400 hover:text-slate-200 hover:border-space-650'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5 font-bold text-xs">
                <ShieldCheck className={`w-3.5 h-3.5 ${profile === 'safe' ? 'text-emerald-400' : 'text-slate-500'}`} />
                <span className={profile === 'safe' ? 'text-emerald-200' : 'text-slate-300'}>Safest</span>
              </div>
              {profile === 'safe' ? (
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400 animate-in zoom-in-75 flex-shrink-0" />
              ) : (
                <div className="w-3 h-3 rounded-full border border-space-650 flex-shrink-0" />
              )}
            </div>
            <p className="text-[10px] text-slate-400 mt-1">Green route • Slope &lt;8° &amp; hazard avoidance</p>
          </button>

          {/* Fastest -> direct */}
          <button
            type="button"
            onClick={() => handleProfileSelect('direct')}
            className={`p-2.5 rounded-lg border text-left transition-all cursor-pointer relative ${
              profile === 'direct'
                ? 'bg-amber-950/80 border-amber-400 text-white shadow-[0_0_12px_rgba(249,115,22,0.35)] ring-1 ring-amber-500/50'
                : 'bg-space-850/60 border-space-750 text-slate-400 hover:text-slate-200 hover:border-space-650'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5 font-bold text-xs">
                <Zap className={`w-3.5 h-3.5 ${profile === 'direct' ? 'text-amber-400' : 'text-slate-500'}`} />
                <span className={profile === 'direct' ? 'text-amber-200' : 'text-slate-300'}>Fastest</span>
              </div>
              {profile === 'direct' ? (
                <CheckCircle className="w-3.5 h-3.5 text-amber-400 animate-in zoom-in-75 flex-shrink-0" />
              ) : (
                <div className="w-3 h-3 rounded-full border border-space-650 flex-shrink-0" />
              )}
            </div>
            <p className="text-[10px] text-slate-400 mt-1">Orange route • Direct Euclidean traverse</p>
          </button>

          {/* Science Max -> Disabled (Strictly maintained per specification) */}
          <button
            type="button"
            disabled
            title="Disabled: Science Max route profile is not yet implemented in backend/algorithms"
            className="p-2.5 rounded-lg border text-left opacity-40 cursor-not-allowed bg-space-900 border-space-800 text-slate-500"
          >
            <div className="flex items-center justify-between font-bold text-xs">
              <div className="flex items-center space-x-1.5">
                <Microscope className="w-3.5 h-3.5 text-slate-600" />
                <span>Science Max</span>
              </div>
              <span className="text-[8px] uppercase tracking-wider px-1 py-0.5 rounded bg-space-800 text-slate-500 font-mono">
                Disabled
              </span>
            </div>
            <p className="text-[10px] text-slate-600 mt-1">Pending backend algorithm</p>
          </button>
        </div>
      </div>

      {/* Constraints: Max Slope Slider & Dune Avoidance */}
      <div className="p-3 rounded-lg bg-space-850/80 border border-space-700/80 space-y-2.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-300 font-medium">Max Rover Slope Limit:</span>
          <span className="font-mono font-bold text-amber-400">{maxSlope}°</span>
        </div>
        <input
          type="range"
          min="8"
          max="25"
          step="1"
          value={maxSlope}
          onChange={e => setMaxSlope(parseFloat(e.target.value))}
          className="w-full h-1.5 bg-space-750 rounded-lg appearance-none cursor-pointer accent-mars-500"
        />
        <div className="flex justify-between text-[10px] font-mono text-slate-500">
          <span>8° (Conservative)</span>
          <span>15° (Standard)</span>
          <span>25° (Limit)</span>
        </div>

        <div className="pt-2 border-t border-space-750 flex items-center justify-between">
          <span className="text-xs text-slate-300">Avoid Active Sand Ripples (Séítah)</span>
          <input
            type="checkbox"
            checked={avoidDunes}
            onChange={e => setAvoidDunes(e.target.checked)}
            className="w-4 h-4 rounded bg-space-900 border-space-700 text-mars-500 focus:ring-0 cursor-pointer"
          />
        </div>
      </div>

      {/* Plan Route Action Button */}
      <button
        type="button"
        onClick={handlePlanRoute}
        disabled={isPlanning}
        className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-mars-600 via-mars-500 to-mars-600 hover:from-mars-500 hover:to-mars-400 text-white font-bold font-mono text-xs uppercase tracking-wider flex items-center justify-center space-x-2 shadow-lg shadow-mars-950/60 border border-mars-400/40 transition-all disabled:opacity-50 cursor-pointer"
      >
        {isPlanning ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            <span>Computing A* Path...</span>
          </>
        ) : (
          <>
            <Navigation className="w-4 h-4" />
            <span>Calculate A* Mission Route</span>
          </>
        )}
      </button>

      {/* Unreachable / Failed Route Banner */}
      {plannedRoute && plannedRoute.status === 'failed' && (
        <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/50 text-xs text-rose-200 space-y-1.5 font-mono">
          <div className="flex items-center space-x-1.5 font-bold text-rose-400">
            <XCircle className="w-4 h-4" />
            <span>TRAVERSE UNREACHABLE</span>
          </div>
          <p className="text-[11px] text-rose-300 leading-relaxed">
            {plannedRoute.message || 'No passable route could be planned within slope and hazard constraints.'}
          </p>
        </div>
      )}

      {/* Route Telemetry & Results Section */}
      {plannedRoute && plannedRoute.status === 'success' && activeSummary && (
        <div className="space-y-3 pt-2">
          {/* Live Engine vs Demo Mode Badge */}
          <div className="flex items-center justify-between">
            {plannedRoute.isLiveBackend ? (
              <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/60 text-[10px] text-emerald-300 font-mono font-bold">
                <Activity className="w-3 h-3 text-emerald-400" />
                <span>LIVE BACKEND CALCULATION (A* Engine)</span>
              </div>
            ) : (
              <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-amber-950/80 border border-amber-500/60 text-[10px] text-amber-300 font-mono font-bold">
                <AlertTriangle className="w-3 h-3 text-amber-400" />
                <span>DEMO SIMULATION (Backend Offline)</span>
              </div>
            )}
            <span className="text-[10px] text-slate-500 font-mono">
              {plannedRoute.algorithm}
            </span>
          </div>

          {/* Separate Route Information Cards */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
              <span className="font-bold text-slate-200 uppercase tracking-wider flex items-center">
                <Navigation className="w-3.5 h-3.5 mr-1 text-telemetry-cyan" />
                TRAVERSE ROUTE OPTIONS
              </span>
              <span className="text-slate-500">
                {(plannedRoute.alternatives || []).length + 1} Routes Available
              </span>
            </div>

            {/* Primary Route Card */}
            {(() => {
              const isSelected = activeAlternativeId === 'primary';
              const primaryProf = plannedRoute.profile || profile;
              const styleConfig = getRouteProfileColor(primaryProf);

              return (
                <div
                  key="card_primary"
                  onClick={() => handleSelectRoute('primary')}
                  className={`p-3 rounded-xl border transition-all cursor-pointer font-mono ${
                    isSelected
                      ? primaryProf === 'direct'
                        ? 'bg-space-850 border-amber-500 shadow-[0_0_15px_rgba(249,115,22,0.25)]'
                        : primaryProf === 'safe'
                        ? 'bg-space-850 border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.25)]'
                        : 'bg-space-850 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.25)]'
                      : 'bg-space-900/90 border-space-750 hover:border-space-600 hover:bg-space-850/60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{
                          backgroundColor: styleConfig.main,
                          boxShadow: isSelected ? `0 0 8px ${styleConfig.main}` : undefined,
                        }}
                      />
                      <span className="font-bold text-xs text-white">
                        Primary ({primaryProf.toUpperCase()})
                      </span>
                    </div>

                    <div className="flex items-center space-x-1.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${styleConfig.badgeClass}`}>
                        {styleConfig.label}
                      </span>
                      {isSelected ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/50 text-[10px] font-bold flex items-center space-x-1">
                          <CheckCircle className="w-3 h-3 text-emerald-400" />
                          <span>ACTIVE</span>
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500 hover:text-slate-300 underline">
                          Select
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Metrics Grid */}
                  <div className="grid grid-cols-2 gap-1.5 text-[11px] mt-2">
                    <div className="p-1.5 rounded bg-space-950/60 border border-space-800">
                      <span className="text-[9px] text-slate-500 uppercase block">Distance</span>
                      <span className="font-bold text-white">
                        {(plannedRoute.summary.total_distance_m / 1000).toFixed(2)} km
                      </span>
                      <span className="text-[9px] text-slate-500 ml-1">
                        ({plannedRoute.summary.total_distance_m.toLocaleString()}m)
                      </span>
                    </div>

                    <div className="p-1.5 rounded bg-space-950/60 border border-space-800">
                      <span className="text-[9px] text-slate-500 uppercase block">Travel Time</span>
                      <span className="font-bold text-telemetry-cyan">
                        {plannedRoute.summary.estimated_duration_sols} sols
                      </span>
                    </div>

                    <div className="p-1.5 rounded bg-space-950/60 border border-space-800">
                      <span className="text-[9px] text-slate-500 uppercase block">Slope (Avg / Max)</span>
                      <span className="font-bold text-amber-400">
                        {plannedRoute.summary.avg_slope_deg}° / {plannedRoute.summary.max_slope_deg}°
                      </span>
                    </div>

                    <div className="p-1.5 rounded bg-space-950/60 border border-space-800">
                      <span className="text-[9px] text-slate-500 uppercase block">Hazard Risk</span>
                      <span className={`font-bold ${
                        plannedRoute.summary.risk_category === 'HIGH'
                          ? 'text-rose-400'
                          : plannedRoute.summary.risk_category === 'MEDIUM'
                          ? 'text-amber-400'
                          : 'text-emerald-400'
                      }`}>
                        {plannedRoute.summary.risk_category} ({plannedRoute.summary.overall_risk_score}/100)
                      </span>
                    </div>
                  </div>

                  {/* Energy estimate when supplied by backend */}
                  {plannedRoute.summary.energy_budget_kwh !== undefined && (
                    <div className="mt-1.5 px-2 py-1 rounded bg-space-950/40 border border-space-800/80 flex items-center justify-between text-[10px]">
                      <span className="text-slate-400 flex items-center">
                        <Zap className="w-3 h-3 text-amber-400 mr-1" />
                        Energy Estimate:
                      </span>
                      <span className="text-amber-300 font-bold">
                        {plannedRoute.summary.energy_budget_kwh} kWh
                      </span>
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Alternative Route Cards */}
            {(plannedRoute.alternatives || []).map(alt => {
              const isSelected = activeAlternativeId === alt.id;
              const styleConfig = getRouteProfileColor(alt.profile);

              // Honest check: verify whether alternative path is identical to primary route
              const isIdentical = (
                (alt.distance_m === plannedRoute.summary.total_distance_m &&
                 alt.max_slope_deg === plannedRoute.summary.max_slope_deg &&
                 alt.avg_slope_deg === plannedRoute.summary.avg_slope_deg) ||
                (alt.path_coordinates?.length === plannedRoute.path_coordinates?.length &&
                 alt.path_coordinates?.length > 1 &&
                 alt.path_coordinates.every((pt, i) =>
                   Math.abs(pt[0] - plannedRoute.path_coordinates[i][0]) < 1e-4 &&
                   Math.abs(pt[1] - plannedRoute.path_coordinates[i][1]) < 1e-4
                 ))
              );

              return (
                <div
                  key={alt.id}
                  onClick={() => handleSelectRoute(alt.id)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer font-mono ${
                    isSelected
                      ? alt.profile === 'direct'
                        ? 'bg-space-850 border-amber-500 shadow-[0_0_15px_rgba(249,115,22,0.25)]'
                        : alt.profile === 'safe'
                        ? 'bg-space-850 border-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.25)]'
                        : 'bg-space-850 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.25)]'
                      : 'bg-space-900/90 border-space-750 hover:border-space-600 hover:bg-space-850/60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{
                          backgroundColor: styleConfig.main,
                          boxShadow: isSelected ? `0 0 8px ${styleConfig.main}` : undefined,
                        }}
                      />
                      <span className="font-bold text-xs text-white">
                        {alt.name}
                      </span>
                    </div>

                    <div className="flex items-center space-x-1.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${styleConfig.badgeClass}`}>
                        {styleConfig.label}
                      </span>
                      {isSelected ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-500/50 text-[10px] font-bold flex items-center space-x-1">
                          <CheckCircle className="w-3 h-3 text-emerald-400" />
                          <span>ACTIVE</span>
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500 hover:text-slate-300 underline">
                          Select
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Honest geometry identity notice if alternatives overlap identically */}
                  {isIdentical && (
                    <div className="mb-2 p-1.5 rounded bg-amber-950/40 border border-amber-500/30 flex items-start space-x-1.5 text-[10px] text-amber-300/90">
                      <AlertTriangle className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5" />
                      <span>Topography Constrained: Path geometry is identical to Primary route under current slope bounds.</span>
                    </div>
                  )}

                  {/* Metrics Grid */}
                  <div className="grid grid-cols-2 gap-1.5 text-[11px] mt-2">
                    <div className="p-1.5 rounded bg-space-950/60 border border-space-800">
                      <span className="text-[9px] text-slate-500 uppercase block">Distance</span>
                      <span className="font-bold text-white">
                        {(alt.distance_m / 1000).toFixed(2)} km
                      </span>
                      <span className="text-[9px] text-slate-500 ml-1">
                        ({alt.distance_m.toLocaleString()}m)
                      </span>
                    </div>

                    <div className="p-1.5 rounded bg-space-950/60 border border-space-800">
                      <span className="text-[9px] text-slate-500 uppercase block">Travel Time</span>
                      <span className="font-bold text-telemetry-cyan">
                        {alt.duration_sols} sols
                      </span>
                    </div>

                    <div className="p-1.5 rounded bg-space-950/60 border border-space-800">
                      <span className="text-[9px] text-slate-500 uppercase block">Slope (Avg / Max)</span>
                      <span className="font-bold text-amber-400">
                        {alt.avg_slope_deg}° / {alt.max_slope_deg}°
                      </span>
                    </div>

                    <div className="p-1.5 rounded bg-space-950/60 border border-space-800">
                      <span className="text-[9px] text-slate-500 uppercase block">Hazard Risk</span>
                      <span className={`font-bold ${
                        alt.risk_category === 'HIGH'
                          ? 'text-rose-400'
                          : alt.risk_category === 'MEDIUM'
                          ? 'text-amber-400'
                          : 'text-emerald-400'
                      }`}>
                        {alt.risk_category} ({alt.risk_score}/100)
                      </span>
                    </div>
                  </div>

                  {/* Energy estimate when supplied by backend */}
                  {alt.energy_budget_kwh !== undefined && (
                    <div className="mt-1.5 px-2 py-1 rounded bg-space-950/40 border border-space-800/80 flex items-center justify-between text-[10px]">
                      <span className="text-slate-400 flex items-center">
                        <Zap className="w-3 h-3 text-amber-400 mr-1" />
                        Energy Estimate:
                      </span>
                      <span className="text-amber-300 font-bold">
                        {alt.energy_budget_kwh} kWh
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Alternative Profile Comparison Table (When available from backend) */}
          {plannedRoute.comparison && plannedRoute.comparison.length > 0 && (
            <div className="p-3 rounded-xl bg-space-900 border border-space-750 space-y-2">
              <div className="flex items-center space-x-1.5 text-[11px] font-mono text-slate-300 font-bold">
                <TableProperties className="w-3.5 h-3.5 text-telemetry-cyan" />
                <span>Multi-Profile Comparison Matrix</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-[10px] border-collapse">
                  <thead>
                    <tr className="border-b border-space-750 text-slate-500">
                      <th className="py-1 px-1.5">Profile</th>
                      <th className="py-1 px-1.5">Dist</th>
                      <th className="py-1 px-1.5">Max Slope</th>
                      <th className="py-1 px-1.5">Avg Slope</th>
                      <th className="py-1 px-1.5">Risk</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-space-800">
                    {plannedRoute.comparison.map(comp => (
                      <tr
                        key={comp.profile}
                        className={`hover:bg-space-800/40 ${
                          (comp.profile.toLowerCase() === profile ||
                            (activeAlternativeId !== 'primary' &&
                              plannedRoute.alternatives?.find(a => a.id === activeAlternativeId)?.profile === comp.profile.toLowerCase()))
                            ? 'text-telemetry-cyan font-bold bg-space-800/20'
                            : 'text-slate-300'
                        }`}
                      >
                        <td className="py-1 px-1.5 uppercase">{comp.profile}</td>
                        <td className="py-1 px-1.5">{(comp.distance_m / 1000).toFixed(2)} km</td>
                        <td className="py-1 px-1.5">{comp.max_slope_deg}°</td>
                        <td className="py-1 px-1.5">{comp.avg_slope_deg}°</td>
                        <td className="py-1 px-1.5">
                          <span className={comp.estimated_risk_score > 50 ? 'text-rose-400' : 'text-emerald-400'}>
                            {Math.round(comp.estimated_risk_score)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Save Mission to Backend Section (Priority 2) */}
          <div className="p-3 rounded-xl bg-space-850 border border-space-700/80 space-y-2.5">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-200 font-bold">
              <span className="flex items-center text-mars-400">
                <Save className="w-3.5 h-3.5 mr-1.5" />
                Save Mission Plan
              </span>
              <span className="text-[10px] text-slate-500 font-normal">POST /api/missions</span>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] text-slate-400 font-mono">Mission Name:</label>
              <input
                type="text"
                value={missionName}
                onChange={e => setMissionName(e.target.value)}
                maxLength={120}
                placeholder="E.g. Jezero Delta Front Traverse"
                className="w-full bg-space-900 border border-space-700 rounded px-2.5 py-1 text-slate-200 text-xs font-mono focus:outline-none focus:border-mars-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] text-slate-400 font-mono">Operational Notes:</label>
              <input
                type="text"
                value={missionNotes}
                onChange={e => setMissionNotes(e.target.value)}
                placeholder="Tactical objectives, science target notes..."
                className="w-full bg-space-900 border border-space-700 rounded px-2.5 py-1 text-slate-200 text-xs font-mono focus:outline-none focus:border-mars-500"
              />
            </div>

            <button
              type="button"
              onClick={handleSaveMission}
              disabled={isSavingMission}
              className="w-full py-2 px-3 rounded-lg bg-space-750 hover:bg-space-700 text-white font-mono font-bold text-xs uppercase tracking-wider flex items-center justify-center space-x-1.5 border border-space-600 transition-all cursor-pointer disabled:opacity-50"
            >
              {isSavingMission ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Saving Mission...</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Save Mission Plan</span>
                </>
              )}
            </button>

            {/* Saved Mission Banner */}
            {savedMission && (
              <div className="p-2.5 rounded bg-emerald-950/60 border border-emerald-500/50 text-[11px] text-emerald-200 font-mono space-y-1">
                <div className="flex items-center justify-between font-bold text-emerald-300">
                  <span className="flex items-center">
                    <CheckCircle className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                    Mission Stored: {savedMission.id}
                  </span>
                  <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-emerald-900 border border-emerald-500/40">
                    {savedMission.status}
                  </span>
                </div>
                <p className="text-[10px] text-emerald-100/90 leading-tight">
                  Automated mission brief generated ({savedMission.report?.sections?.length || 4} sections).
                </p>
                {onOpenReport && (
                  <button
                    type="button"
                    onClick={onOpenReport}
                    className="mt-1 text-[10px] text-telemetry-cyan hover:underline font-bold flex items-center cursor-pointer"
                  >
                    Open Generated Mission Report &rarr;
                  </button>
                )}
              </div>
            )}

            {saveError && (
              <div className="p-2 rounded bg-rose-950/50 border border-rose-500/40 text-[10px] text-rose-300 font-mono">
                {saveError}
              </div>
            )}
          </div>

          {/* Waypoints List */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
              <span className="flex items-center">
                <ListOrdered className="w-3.5 h-3.5 mr-1 text-telemetry-cyan" />
                WAYPOINT SEQUENCE
              </span>
              <span>{activeWaypoints.length} nodes</span>
            </div>

            <div className="max-h-48 overflow-y-auto space-y-1 pr-1 font-mono text-[11px]">
              {activeWaypoints.map(wp => (
                <div
                  key={wp.index}
                  onClick={() => {
                    onSelectWaypoint(wp);
                    controller.panTo(wp.lon, wp.lat, 14);
                  }}
                  className="p-2 rounded bg-space-900 hover:bg-space-800 border border-space-750 flex items-center justify-between cursor-pointer transition-all"
                >
                  <div className="flex items-center space-x-2">
                    <span className="w-5 h-5 rounded-full bg-space-750 flex items-center justify-center text-[10px] text-slate-300 font-bold">
                      {wp.index}
                    </span>
                    <div>
                      <div className="text-slate-200 font-medium">
                        {wp.notes || `WP-${wp.index}`}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        {wp.lat.toFixed(4)}°N, {wp.lon.toFixed(4)}°E &bull; {wp.elevation_m}m
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-amber-400 font-bold">{wp.slope_deg}°</div>
                    <div className="text-[10px] text-slate-500">{wp.cumulative_distance_m}m</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Safety Warnings & Provenance Notice */}
          <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-600/40 text-[11px] text-amber-300 space-y-1">
            <div className="flex items-center space-x-1.5 font-bold font-mono text-[11px]">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>SAFETY LIMITATIONS NOTICE</span>
            </div>
            <p className="text-[10px] leading-relaxed text-amber-200/90">
              Generated path is a computational research mission planning estimate. Not guaranteed safe for autonomous traversal.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
