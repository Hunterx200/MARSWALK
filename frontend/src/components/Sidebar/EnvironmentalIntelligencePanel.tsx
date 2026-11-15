import React, { useState, useEffect } from 'react';
import { MarswalkApiClient } from '../../services/apiClient';
import {
  MEDASolTelemetryResponse,
  MEDASolSummaryResponse,
  MEDASolTimeSeriesResponse,
} from '../../types/api';
import {
  Thermometer,
  Gauge,
  Wind,
  Sun,
  AlertCircle,
  Database,
  Radio,
  CheckCircle2,
  XCircle,
  Activity,
  Info
} from 'lucide-react';

export const EnvironmentalIntelligencePanel: React.FC = () => {
  const [availableSols, setAvailableSols] = useState<number[]>([74, 755]);
  const [selectedSol, setSelectedSol] = useState<number>(755);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [telemetry, setTelemetry] = useState<MEDASolTelemetryResponse | null>(null);
  const [summary, setSummary] = useState<MEDASolSummaryResponse | null>(null);
  const [timeseries, setTimeseries] = useState<MEDASolTimeSeriesResponse | null>(null);
  const [activeChartMetric, setActiveChartMetric] = useState<'temp' | 'pressure' | 'wind'>('temp');

  // Load available sols once
  useEffect(() => {
    MarswalkApiClient.getAvailableSols().then(sols => {
      if (sols && sols.length > 0) {
        setAvailableSols(sols);
        if (!sols.includes(selectedSol)) {
          setSelectedSol(sols[0]);
        }
      }
    }).catch(() => {});
  }, []);

  // Fetch Sol data on selectedSol change
  useEffect(() => {
    let isCancelled = false;
    setLoading(true);
    setError(null);
    setTelemetry(null);
    setSummary(null);
    setTimeseries(null);

    Promise.all([
      MarswalkApiClient.getMedaTelemetry(selectedSol),
      MarswalkApiClient.getSolSummary(selectedSol),
      MarswalkApiClient.getSolTimeSeries(selectedSol, 60),
    ])
      .then(([telemData, summaryData, tsData]) => {
        if (isCancelled) return;
        if (!telemData) {
          setError(`Failed to retrieve MEDA telemetry for Sol ${selectedSol} from backend.`);
          setTelemetry(null);
          setSummary(null);
          setTimeseries(null);
        } else {
          setTelemetry(telemData);
          setSummary(summaryData);
          setTimeseries(tsData);
        }
        setLoading(false);
      })
      .catch((err) => {
        if (isCancelled) return;
        setError(err?.message || 'Error connecting to MEDA Environmental service.');
        setTelemetry(null);
        setSummary(null);
        setTimeseries(null);
        setLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [selectedSol]);

  // Convert Kelvin to Celsius helper
  const kToC = (k: number | null | undefined): string => {
    if (k === null || k === undefined) return '--';
    return (k - 273.15).toFixed(1);
  };

  const formatNum = (val: number | null | undefined, decimals: number = 2): string => {
    if (val === null || val === undefined) return '--';
    return val.toFixed(decimals);
  };

  const formatAmp = (val: number | null | undefined): string => {
    if (val === null || val === undefined) return '--';
    return val.toExponential(3);
  };

  // Render SVG Sparkline / Diurnal Curve
  const renderDiurnalChart = () => {
    if (!timeseries || !timeseries.samples || timeseries.samples.length < 2) {
      return (
        <div className="h-32 flex items-center justify-center text-slate-500 font-mono text-[11px] bg-space-900/60 rounded-lg border border-space-750">
          No time series telemetry available for this Sol.
        </div>
      );
    }

    const samples = timeseries.samples;
    let values: (number | null)[] = [];
    let unitLabel = '';

    if (activeChartMetric === 'temp') {
      values = samples.map(s => s.ats_temp1_k ?? s.air_temp_k ?? null);
      unitLabel = 'K';
    } else if (activeChartMetric === 'pressure') {
      values = samples.map(s => s.pressure_pa ?? null);
      unitLabel = 'Pa';
    } else {
      values = samples.map(s => s.wind_speed_ms ?? null);
      unitLabel = 'm/s';
    }

    const validIndices = values.map((v, i) => (v !== null ? i : -1)).filter(i => i !== -1);
    if (validIndices.length < 2) {
      return (
        <div className="h-32 flex flex-col items-center justify-center p-3 text-center text-amber-400/80 font-mono text-[11px] bg-space-900/60 rounded-lg border border-amber-500/20">
          <AlertCircle className="w-4 h-4 mb-1 text-amber-400" />
          <span>Metric not recorded in PDS archive for Sol {selectedSol}</span>
          <span className="text-[10px] text-slate-400 mt-0.5">
            {activeChartMetric === 'wind' ? 'Wind sensor unarchived due to hardware degradation.' : 'No valid readings.'}
          </span>
        </div>
      );
    }

    const validValues = validIndices.map(i => values[i] as number);
    const minVal = Math.min(...validValues);
    const maxVal = Math.max(...validValues);
    const range = maxVal - minVal === 0 ? 1 : maxVal - minVal;

    const width = 340;
    const height = 90;
    const pad = 12;

    const points = validIndices.map(i => {
      const x = pad + (i / (samples.length - 1)) * (width - 2 * pad);
      const val = values[i] as number;
      const y = height - pad - ((val - minVal) / range) * (height - 2 * pad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');

    const firstValidIdx = validIndices[0];
    const lastValidIdx = validIndices[validIndices.length - 1];

    return (
      <div className="space-y-1.5">
        <div className="relative bg-space-900/80 rounded-lg border border-space-750 p-2 overflow-hidden">
          <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-24 overflow-visible">
            <defs>
              <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Grid lines */}
            <line x1={pad} y1={pad} x2={width - pad} y2={pad} stroke="#334155" strokeDasharray="2,2" strokeWidth="0.5" />
            <line x1={pad} y1={height / 2} x2={width - pad} y2={height / 2} stroke="#334155" strokeDasharray="2,2" strokeWidth="0.5" />
            <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#334155" strokeDasharray="2,2" strokeWidth="0.5" />

            {/* Area under curve */}
            <polygon
              points={`${pad + (firstValidIdx / (samples.length - 1)) * (width - 2 * pad)},${height - pad} ${points} ${pad + (lastValidIdx / (samples.length - 1)) * (width - 2 * pad)},${height - pad}`}
              fill="url(#chartGradient)"
            />

            {/* Main Polyline */}
            <polyline
              fill="none"
              stroke="#38bdf8"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={points}
            />

            {/* Min and Max Markers */}
            <text x={pad + 2} y={pad + 8} fill="#94a3b8" fontSize="8" fontFamily="monospace">
              MAX: {maxVal.toFixed(1)} {unitLabel}
            </text>
            <text x={pad + 2} y={height - pad - 2} fill="#94a3b8" fontSize="8" fontFamily="monospace">
              MIN: {minVal.toFixed(1)} {unitLabel}
            </text>
          </svg>
        </div>

        <div className="flex justify-between items-center text-[10px] font-mono text-slate-400 px-1">
          <span>Start: {samples[0]?.lmst?.split(' ')[0] || '00:00:00'} LMST</span>
          <span>End: {samples[samples.length - 1]?.lmst?.split(' ')[0] || '23:59:59'} LMST</span>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4 text-xs select-none">
      {/* Panel Header */}
      <div className="flex items-center justify-between pb-2 border-b border-space-750">
        <div className="flex items-center space-x-2">
          <Thermometer className="w-4 h-4 text-amber-400" />
          <h3 className="font-bold text-slate-200 uppercase tracking-wider font-mono text-xs">
            Perseverance MEDA Telemetry
          </h3>
        </div>
        <div className="flex items-center space-x-1.5 bg-space-800 px-2 py-0.5 rounded border border-space-700">
          <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
          <span className="text-[10px] font-mono text-emerald-400 font-bold">NASA PDS4 ARCHIVE</span>
        </div>
      </div>

      {/* Prominent Mandatory Limitations Banner */}
      <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-500/40 text-[11px] text-amber-200 space-y-1.5 shadow-inner">
        <div className="flex items-center space-x-1.5 font-bold font-mono text-xs text-amber-400">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>HISTORICAL OBSERVATION ARCHIVE — NOT LIVE WEATHER</span>
        </div>
        <p className="leading-relaxed text-[11px] text-amber-100/90">
          Historical observational telemetry archived by NASA Mars 2020 Perseverance MEDA instrument (
          <span className="font-mono text-amber-300">urn:nasa:pds:mars2020_meda</span>). 
          Not live Martian weather. All measurements are informational only; no weather-penalty routing is applied.
        </p>
        <div className="p-1.5 rounded bg-space-900/90 border border-amber-500/30 text-[10px] font-mono text-amber-300">
          <strong>Dataset Scope:</strong> Currently integrated historical dataset contains only <strong>Sol 74</strong> and <strong>Sol 755</strong> (traceable to verified NASA PDS4 archive deliveries).
        </div>
      </div>

      {/* Sol Selector & Snapshot Time Controls */}
      <div className="flex items-center justify-between p-2 rounded-lg bg-space-850 border border-space-750">
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-mono text-slate-400 uppercase font-bold">Martian Sol:</span>
          <div className="flex space-x-1">
            {availableSols.map(sol => (
              <button
                key={sol}
                type="button"
                onClick={() => setSelectedSol(sol)}
                className={`px-2.5 py-1 rounded text-xs font-mono font-bold transition-all cursor-pointer ${
                  selectedSol === sol
                    ? 'bg-amber-500 text-space-950 shadow-md'
                    : 'bg-space-800 text-slate-300 hover:bg-space-750 border border-space-700'
                }`}
              >
                Sol {sol}
              </button>
            ))}
          </div>
        </div>

        {telemetry?.ats && (
          <div className="text-right text-[10px] font-mono text-slate-400">
            <div>LMST: <span className="text-slate-200">{telemetry.ats.lmst}</span></div>
            <div>LTST: <span className="text-slate-200">{telemetry.ats.ltst}</span></div>
          </div>
        )}
      </div>

      {/* Sensor Operational Inventory & Health */}
      {summary && !loading && (
        <div className="p-2 rounded-lg bg-space-850/80 border border-space-750 space-y-1">
          <div className="text-[10px] font-mono text-slate-400 uppercase font-semibold flex items-center justify-between">
            <span>Archived Sensor Health (Sol {summary.sol}):</span>
            <span className="text-slate-500">{summary.site_location}</span>
          </div>
          <div className="flex flex-wrap gap-1 text-[10px] font-mono">
            {Object.entries(summary.sensors_available).map(([sensor, isAvail]) => (
              <span
                key={sensor}
                className={`px-1.5 py-0.5 rounded flex items-center space-x-1 ${
                  isAvail
                    ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/30'
                    : 'bg-rose-950/60 text-rose-300 border border-rose-500/30'
                }`}
              >
                {isAvail ? (
                  <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                ) : (
                  <XCircle className="w-2.5 h-2.5 text-rose-400" />
                )}
                <span>{sensor}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="p-8 text-center text-slate-400 font-mono text-xs space-y-2">
          <Activity className="w-6 h-6 animate-spin text-amber-400 mx-auto" />
          <p>Parsing calibrated NASA PDS4 records for Sol {selectedSol}...</p>
        </div>
      )}

      {error && !loading && (
        <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-500/50 text-rose-300 text-xs font-mono">
          {error}
        </div>
      )}

      {!loading && telemetry && (
        <>
          {/* Card 1: Atmospheric Temperature (CAL_ATS & CAL_TIRS) */}
          <div className="p-3 rounded-xl bg-space-850 border border-space-700 space-y-2.5">
            <div className="flex items-center justify-between pb-1.5 border-b border-space-750">
              <div className="flex items-center space-x-1.5">
                <Thermometer className="w-4 h-4 text-rose-400" />
                <h4 className="font-bold text-slate-200 font-mono text-xs uppercase">
                  Atmospheric & Surface Temperature
                </h4>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-space-800 border border-space-700 text-slate-300">
                CAL_ATS / CAL_TIRS
              </span>
            </div>

            {/* 5 Distinct ATS Thermocouple Channels */}
            <div>
              <div className="text-[10px] font-mono text-slate-400 uppercase font-semibold mb-1">
                Air Temperature Sensors (ATS miniature thermocouples):
              </div>
              <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px]">
                <div className="p-1.5 rounded bg-space-900 border border-space-750 flex justify-between items-center">
                  <span className="text-slate-400" title="Remote Sensing Mast at 50° azimuth">ATS 1 (Mast 50°):</span>
                  <span className="text-slate-200 font-bold">{formatNum(telemetry.ats?.ats_local_temp1_k, 2)} K ({kToC(telemetry.ats?.ats_local_temp1_k)}°C)</span>
                </div>
                <div className="p-1.5 rounded bg-space-900 border border-space-750 flex justify-between items-center">
                  <span className="text-slate-400" title="Remote Sensing Mast at 155° azimuth">ATS 2 (Mast 155°):</span>
                  <span className="text-slate-200 font-bold">{formatNum(telemetry.ats?.ats_local_temp2_k, 2)} K ({kToC(telemetry.ats?.ats_local_temp2_k)}°C)</span>
                </div>
                <div className="p-1.5 rounded bg-space-900 border border-space-750 flex justify-between items-center">
                  <span className="text-slate-400" title="Remote Sensing Mast at 290° azimuth">ATS 3 (Mast 290°):</span>
                  <span className="text-slate-200 font-bold">{formatNum(telemetry.ats?.ats_local_temp3_k, 2)} K ({kToC(telemetry.ats?.ats_local_temp3_k)}°C)</span>
                </div>
                <div className="p-1.5 rounded bg-space-900 border border-space-750 flex justify-between items-center">
                  <span className="text-slate-400" title="Rover Front Body Port side">ATS 4 (Front Port):</span>
                  <span className="text-slate-200 font-bold">{formatNum(telemetry.ats?.ats_local_temp4_k, 2)} K ({kToC(telemetry.ats?.ats_local_temp4_k)}°C)</span>
                </div>
                <div className="col-span-2 p-1.5 rounded bg-space-900 border border-space-750 flex justify-between items-center">
                  <span className="text-slate-400" title="Rover Front Body Starboard side">ATS 5 (Front Starboard):</span>
                  <span className="text-slate-200 font-bold">{formatNum(telemetry.ats?.ats_local_temp5_k, 2)} K ({kToC(telemetry.ats?.ats_local_temp5_k)}°C)</span>
                </div>
              </div>
            </div>

            {/* TIRS Telemetry */}
            {telemetry.tirs && (
              <div className="pt-1.5 border-t border-space-750 space-y-1">
                <div className="text-[10px] font-mono text-slate-400 uppercase font-semibold">
                  Thermal Infrared Sensor (TIRS Radiative Telemetry):
                </div>
                <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px]">
                  <div className="p-1.5 rounded bg-space-900 border border-space-750">
                    <div className="text-[10px] text-slate-400">TIRS Air Temp (15μm):</div>
                    <div className="text-slate-200 font-bold">{formatNum(telemetry.tirs.air_temp_k, 2)} K ({kToC(telemetry.tirs.air_temp_k)}°C)</div>
                  </div>
                  <div className="p-1.5 rounded bg-space-900 border border-space-750">
                    <div className="text-[10px] text-slate-400">Ground Brightness Temp:</div>
                    <div className="text-slate-200 font-bold">
                      {formatNum(telemetry.tirs.ground_brightness_temp_k, 2)} K
                      {telemetry.tirs.ground_temp_uncertainty_k && (
                        <span className="text-[10px] font-normal text-slate-400"> ±{formatNum(telemetry.tirs.ground_temp_uncertainty_k, 2)}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="text-[10px] text-slate-400 italic">
              Note: Arithmetic averaging across separate ATS detectors is scientifically unvalidated and strictly forbidden.
            </div>
          </div>

          {/* Card 2: Atmospheric Pressure (DER_PS) */}
          <div className="p-3 rounded-xl bg-space-850 border border-space-700 space-y-2">
            <div className="flex items-center justify-between pb-1.5 border-b border-space-750">
              <div className="flex items-center space-x-1.5">
                <Gauge className="w-4 h-4 text-cyan-400" />
                <h4 className="font-bold text-slate-200 font-mono text-xs uppercase">
                  Atmospheric Pressure (DER_PS)
                </h4>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-space-800 border border-space-700 text-slate-300">
                Barocap #{telemetry.pressure?.transducer_id ?? 1}
              </span>
            </div>

            <div className="p-2 rounded bg-space-900 border border-space-750 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-mono text-slate-400">Ambient Surface Pressure</div>
                <div className="text-base font-mono font-bold text-cyan-400">
                  {formatNum(telemetry.pressure?.pressure_pa, 2)} <span className="text-xs text-slate-400">Pa</span>
                  <span className="text-xs text-slate-400 ml-2 font-normal">
                    ({formatNum((telemetry.pressure?.pressure_pa ?? 0) / 100, 3)} hPa / mbar)
                  </span>
                </div>
              </div>

              {telemetry.pressure?.pressure_uncertainty !== null && telemetry.pressure?.pressure_uncertainty !== undefined && (
                <div className="text-right">
                  <div className="text-[10px] font-mono text-slate-400">Archive Uncertainty</div>
                  <div className="text-xs font-mono font-bold text-slate-200">
                    ± {formatNum(telemetry.pressure.pressure_uncertainty, 4)}
                  </div>
                </div>
              )}
            </div>

            {/* Pressure Uncertainty Physical Status Banner */}
            <div className="p-1.5 rounded bg-space-900 border border-amber-500/20 text-[10px] font-mono text-slate-400 space-y-0.5">
              <div className="flex items-center space-x-1 text-amber-400 font-semibold">
                <Info className="w-3 h-3" />
                <span>Pressure Uncertainty Unit Status</span>
              </div>
              <div>
                Declared in PDS4 XML label: <span className="text-slate-200 font-semibold">{telemetry.pressure?.source_declared_unit}</span>
              </div>
              <div>
                Physical interpretation: <span className="text-amber-300">{telemetry.pressure?.physical_unit_status}</span> (unconfirmed in SIS table; not converted to Pa).
              </div>
            </div>
          </div>

          {/* Card 3: Wind Velocity & Hardware Status (DER_WS) */}
          <div className="p-3 rounded-xl bg-space-850 border border-space-700 space-y-2">
            <div className="flex items-center justify-between pb-1.5 border-b border-space-750">
              <div className="flex items-center space-x-1.5">
                <Wind className="w-4 h-4 text-teal-400" />
                <h4 className="font-bold text-slate-200 font-mono text-xs uppercase">
                  Wind Velocity & Dynamics (DER_WS)
                </h4>
              </div>

              {telemetry.wind.available ? (
                <span className="flex items-center space-x-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 font-semibold">
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>OPERATIONAL</span>
                </span>
              ) : (
                <span className="flex items-center space-x-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-950/60 border border-rose-500/40 text-rose-300 font-semibold">
                  <XCircle className="w-3 h-3 text-rose-400" />
                  <span>UNARCHIVED</span>
                </span>
              )}
            </div>

            {telemetry.wind.available ? (
              <div className="grid grid-cols-2 gap-1.5 font-mono text-[11px]">
                <div className="p-2 rounded bg-space-900 border border-space-750">
                  <div className="text-[10px] text-slate-400">Horizontal Wind Speed:</div>
                  <div className="text-sm font-bold text-slate-200">
                    {formatNum(telemetry.wind.horizontal_wind_speed_ms, 2)} <span className="text-xs text-slate-400">m/s</span>
                  </div>
                </div>
                <div className="p-2 rounded bg-space-900 border border-space-750">
                  <div className="text-[10px] text-slate-400">Direction (From Azimuth):</div>
                  <div className="text-sm font-bold text-slate-200">
                    {formatNum(telemetry.wind.wind_direction_deg, 1)}°
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-2.5 rounded bg-space-900 border border-rose-500/30 text-[10px] font-mono space-y-1">
                <div className="font-bold text-rose-400 flex items-center space-x-1">
                  <AlertCircle className="w-3 h-3" />
                  <span>Status: {telemetry.wind.status_reason}</span>
                </div>
                <p className="text-slate-300 leading-relaxed">
                  DER_WS is absent from the Sol 755 PDS archive and sensor status cannot be determined from archive absence alone. Values evaluate strictly to null; no synthetic wind observations are generated.
                </p>
              </div>
            )}
          </div>

          {/* Card 4: Radiation & Dust Environment (CAL_RDS) */}
          <div className="p-3 rounded-xl bg-space-850 border border-space-700 space-y-2.5">
            <div className="flex items-center justify-between pb-1.5 border-b border-space-750">
              <div className="flex items-center space-x-1.5">
                <Sun className="w-4 h-4 text-yellow-400" />
                <h4 className="font-bold text-slate-200 font-mono text-xs uppercase">
                  Radiation & Dust Telemetry (CAL_RDS)
                </h4>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-space-800 border border-space-700 text-slate-300">
                16 Photodiodes
              </span>
            </div>

            {/* LAT 1 Dark Current */}
            <div className="p-2 rounded bg-space-900 border border-space-750 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-mono text-slate-400">LAT 1 Blinded Dark Current</div>
                <div className="text-[10px] text-slate-500 font-mono">Reference channel (no optical window)</div>
              </div>
              <div className="text-xs font-mono font-bold text-yellow-300">
                {formatAmp(telemetry.rds?.rds_lat_1_amp)} <span className="text-[10px] text-slate-400">amp</span>
              </div>
            </div>

            {/* Optical Channels Status & Exact PDS Provenance */}
            <div className="p-2 rounded bg-space-900 border border-space-750 space-y-1.5 text-[10px] font-mono">
              <div className="flex justify-between items-center text-slate-300 font-semibold">
                <span>Optical Channels (TOP 1–8 & LAT 2–8):</span>
                <span className="text-amber-400 font-bold">{telemetry.rds?.optical_channels_unit || 'watt/m2'}</span>
              </div>
              <div className="text-slate-400">
                Archive description: <span className="text-slate-200 italic font-medium">"{telemetry.rds?.archive_description || 'radiance integrated over Field of View'}"</span>
              </div>
              <div className="text-amber-300/90 text-[9.5px]">
                Note: Retains exact archive unit (watt/m2) and description. NOT relabeled as ordinary irradiance or solar flux. Status: {telemetry.rds?.physical_interpretation_status}.
              </div>

              {/* TOP Zenith Channels */}
              <div className="pt-1 border-t border-space-750">
                <div className="text-[9.5px] text-slate-400 mb-1">Top Zenith Channels (TOP 1–8):</div>
                <div className="grid grid-cols-4 gap-1 text-[10px]">
                  {(telemetry.rds?.rds_top_channels || []).slice(0, 8).map((val, idx) => (
                    <div key={idx} className="p-1 rounded bg-space-850 border border-space-700 text-center">
                      <div className="text-slate-500 text-[9px]">T{idx + 1}</div>
                      <div className="text-slate-200 font-bold">{formatNum(val, 2)}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* LAT Ring Channels */}
              <div className="pt-1 border-t border-space-750">
                <div className="text-[9.5px] text-slate-400 mb-1">Lateral Ring Channels (LAT 2–8):</div>
                <div className="grid grid-cols-4 gap-1 text-[10px]">
                  {(telemetry.rds?.rds_lat_channels || []).slice(0, 7).map((val, idx) => (
                    <div key={idx} className="p-1 rounded bg-space-850 border border-space-700 text-center">
                      <div className="text-slate-500 text-[9px]">L{idx + 2}</div>
                      <div className="text-slate-200 font-bold">{formatNum(val, 2)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Dust Optical Depth Note */}
            <div className="p-1.5 rounded bg-space-900 border border-space-750 flex justify-between items-center text-[10px] font-mono">
              <span className="text-slate-400">Column Dust Optical Depth (τ):</span>
              <span className="text-slate-500 font-semibold italic">null (not published in MEDA archive tables)</span>
            </div>
          </div>

          {/* Diurnal Time-Series Chart */}
          <div className="p-3 rounded-xl bg-space-850 border border-space-750 space-y-2">
            <div className="flex items-center justify-between pb-1 border-b border-space-750">
              <div className="flex items-center space-x-1.5">
                <Activity className="w-3.5 h-3.5 text-sky-400" />
                <h4 className="font-bold text-slate-200 font-mono text-xs uppercase">
                  Diurnal Sol Variations
                </h4>
              </div>

              {/* Metric Selector Tabs */}
              <div className="flex space-x-1 bg-space-900 p-0.5 rounded border border-space-750 text-[10px] font-mono">
                <button
                  type="button"
                  onClick={() => setActiveChartMetric('temp')}
                  className={`px-2 py-0.5 rounded cursor-pointer ${
                    activeChartMetric === 'temp'
                      ? 'bg-space-750 text-sky-400 font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Temp
                </button>
                <button
                  type="button"
                  onClick={() => setActiveChartMetric('pressure')}
                  className={`px-2 py-0.5 rounded cursor-pointer ${
                    activeChartMetric === 'pressure'
                      ? 'bg-space-750 text-cyan-400 font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Pressure
                </button>
                <button
                  type="button"
                  onClick={() => setActiveChartMetric('wind')}
                  className={`px-2 py-0.5 rounded cursor-pointer ${
                    activeChartMetric === 'wind'
                      ? 'bg-space-750 text-teal-400 font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Wind
                </button>
              </div>
            </div>

            {renderDiurnalChart()}
          </div>

          {/* Traceable NASA Provenance Footer */}
          <div className="p-3 rounded-xl bg-space-850/60 border border-space-750 space-y-1.5 text-[10px] font-mono text-slate-400">
            <div className="flex items-center space-x-1 text-slate-300 font-bold uppercase">
              <Database className="w-3.5 h-3.5 text-amber-400" />
              <span>NASA PDS4 Telemetry Provenance</span>
            </div>
            <div className="space-y-0.5">
              <div>Bundle: <span className="text-slate-300">{telemetry.bundle_lid}</span></div>
              <div>DOI: <a href="https://doi.org/10.17189/1522849" target="_blank" rel="noreferrer" className="text-sky-400 hover:underline">10.17189/1522849</a></div>
              <div>Location: <span className="text-slate-300">Jezero Crater, Mars (18.38°N, 77.58°E)</span></div>
              {telemetry.ats?.provenance && (
                <div>ATS Product: <span className="text-slate-300">{telemetry.ats.provenance.product_filename}</span></div>
              )}
              {telemetry.pressure?.provenance && (
                <div>PS Product: <span className="text-slate-300">{telemetry.pressure.provenance.product_filename}</span></div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
