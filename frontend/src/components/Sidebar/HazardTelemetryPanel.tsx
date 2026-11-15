import React, { useState } from 'react';
import { HazardZone } from '../../types/api';
import { MarsMapController } from '../../services/mapManager';
import { ShieldAlert, AlertTriangle, Crosshair } from 'lucide-react';

interface HazardTelemetryPanelProps {
  hazards: HazardZone[];
  controller: MarsMapController;
  onSelectHazard: (hazard: HazardZone) => void;
}

export const HazardTelemetryPanel: React.FC<HazardTelemetryPanelProps> = ({
  hazards = [],
  controller,
  onSelectHazard,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');

  const safeHazards = Array.isArray(hazards) ? hazards : [];
  const filteredHazards = filterSeverity === 'ALL'
    ? safeHazards
    : safeHazards.filter(h => (h?.severity || '').toUpperCase() === filterSeverity);

  return (
    <div className="space-y-4 text-xs select-none">
      <div className="flex items-center justify-between pb-2 border-b border-space-750">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          <h3 className="font-bold text-slate-200 uppercase tracking-wider font-mono text-xs">
            Terrain Hazard Telemetry
          </h3>
        </div>
        <span className="text-[10px] text-slate-400 font-mono">
          {safeHazards.length} REGION HAZARDS
        </span>
      </div>

      {/* Prominent Mandatory Limitations Banner */}
      <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-500/40 text-[11px] text-rose-200 space-y-1.5 shadow-inner">
        <div className="flex items-center space-x-1.5 font-bold font-mono text-xs text-rose-400">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>TRANSPARENT HAZARD LIMITATIONS</span>
        </div>
        <p className="leading-relaxed text-[11px] text-rose-100/90">
          Risk ratings are project-generated models based on USGS MOLA topography (25m grid) and HiRISE imagery. They do NOT represent flight-certified rover hazard clearances. Imagery does not detect sub-meter boulders or micro-sand traps. Never describe a generated route as guaranteed safe.
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="flex space-x-1 p-1 rounded-lg bg-space-850 border border-space-750 text-[11px] font-mono">
        {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map(sev => (
          <button
            key={sev}
            type="button"
            onClick={() => setFilterSeverity(sev)}
            className={`flex-1 py-1 rounded-md transition-all cursor-pointer ${
              filterSeverity === sev
                ? 'bg-space-700 text-white font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {sev}
          </button>
        ))}
      </div>

      {/* Hazard Cards List */}
      <div className="space-y-2.5 max-h-[60vh] overflow-y-auto pr-1">
        {filteredHazards.map(haz => (
          <div
            key={haz.id}
            onClick={() => {
              onSelectHazard(haz);
              controller.panTo(haz.lon ?? 77.4395, haz.lat ?? 18.4447, 14);
            }}
            className="p-3 rounded-xl bg-space-850 hover:bg-space-800 border border-space-700/80 hover:border-space-600 transition-all cursor-pointer group"
          >
            <div className="flex items-start justify-between">
              <div>
                <h4 className="font-bold text-slate-200 group-hover:text-white text-xs">
                  {haz.name || 'Terrain Hazard'}
                </h4>
                <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                  {(haz.lat ?? 18.4447).toFixed(4)}°N, {(haz.lon ?? 77.4395).toFixed(4)}°E &bull; Radius {haz.radius_m ?? 250}m
                </div>
              </div>

              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                haz.severity === 'CRITICAL'
                  ? 'bg-rose-950 text-rose-400 border border-rose-500/40'
                  : haz.severity === 'HIGH'
                  ? 'bg-amber-950 text-amber-400 border border-amber-500/40'
                  : 'bg-yellow-950 text-yellow-400 border border-yellow-500/40'
              }`}>
                {haz.severity || 'HIGH'}
              </span>
            </div>

            <div className="mt-2.5 space-y-1.5 text-[11px]">
              <div>
                <span className="text-slate-400 font-semibold">Mobility Risk: </span>
                <span className="text-slate-300">{haz.mobility_risk || 'Terrain slope/sand obstacle'}</span>
              </div>

              <div>
                <span className="text-emerald-400 font-semibold">Mitigation: </span>
                <span className="text-slate-300">{haz.mitigation_protocol || 'Maintain standoff buffer.'}</span>
              </div>
            </div>

            <div className="mt-2 pt-2 border-t border-space-750/60 flex items-center justify-between text-[10px] text-slate-500 font-mono">
              <span>{haz.source_provenance}</span>
              <span className="text-telemetry-cyan flex items-center group-hover:translate-x-0.5 transition-transform">
                <Crosshair className="w-3 h-3 mr-0.5" />
                Inspect
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
