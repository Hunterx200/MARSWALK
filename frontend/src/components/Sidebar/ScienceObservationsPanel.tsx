import React, { useState } from 'react';
import { Observation } from '../../types/api';
import { MarsMapController } from '../../services/mapManager';
import { Microscope, TestTube2, Compass } from 'lucide-react';

interface ScienceObservationsPanelProps {
  observations: Observation[];
  controller: MarsMapController;
  onSelectObservation: (obs: Observation) => void;
}

export const ScienceObservationsPanel: React.FC<ScienceObservationsPanelProps> = ({
  observations = [],
  controller,
  onSelectObservation,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const safeObservations = Array.isArray(observations) ? observations : [];
  const term = (searchTerm || '').toLowerCase();

  const filteredObservations = safeObservations.filter(obs => {
    if (!obs) return false;
    const name = (obs.target_name || '').toLowerCase();
    const desc = (obs.description || '').toLowerCase();
    const insts = Array.isArray(obs.instruments) ? obs.instruments : [];
    return name.includes(term) || desc.includes(term) || insts.some(i => (i || '').toLowerCase().includes(term));
  });

  return (
    <div className="space-y-4 text-xs select-none">
      <div className="flex items-center justify-between pb-2 border-b border-space-750">
        <div className="flex items-center space-x-2">
          <Microscope className="w-4 h-4 text-telemetry-cyan" />
          <h3 className="font-bold text-slate-200 uppercase tracking-wider font-mono text-xs">
            NASA PDS Science Targets
          </h3>
        </div>
        <span className="text-[10px] text-slate-400 font-mono">
          {safeObservations.length} TARGETS
        </span>
      </div>

      {/* Search Input */}
      <div>
        <input
          type="text"
          placeholder="Filter by target, instrument, or sol..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="w-full bg-space-900 border border-space-750 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-telemetry-cyan font-mono"
        />
      </div>

      {/* Observations List */}
      <div className="space-y-2.5 max-h-[60vh] overflow-y-auto pr-1">
        {filteredObservations.map(obs => (
          <div
            key={obs.id}
            onClick={() => {
              onSelectObservation(obs);
              controller.panTo(obs.lon ?? 77.4508, obs.lat ?? 18.4447, 14.5);
            }}
            className="p-3 rounded-xl bg-space-850 hover:bg-space-800 border border-space-700/80 hover:border-space-600 transition-all cursor-pointer group"
          >
            <div className="flex items-start justify-between">
              <div>
                <h4 className="font-bold text-slate-200 group-hover:text-white text-xs">
                  {obs.target_name || 'Science Target'}
                </h4>
                <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                  {(obs.lat ?? 18.4447).toFixed(4)}°N, {(obs.lon ?? 77.4508).toFixed(4)}°E &bull; Elev {obs.elevation_m ?? -2520}m
                </div>
              </div>

              <div className="flex flex-col items-end space-y-1">
                <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-500/30 text-[10px] font-mono font-bold">
                  SOL {obs.sol ?? 0}
                </span>
                {obs.sample_tube_id && (
                  <span className="flex items-center text-[9px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/30">
                    <TestTube2 className="w-2.5 h-2.5 mr-0.5" />
                    CORE
                  </span>
                )}
              </div>
            </div>

            <p className="text-[11px] text-slate-300 mt-2 leading-relaxed">
              {obs.description || 'Verified Jezero exploration observation target.'}
            </p>

            {/* Instruments */}
            <div className="mt-2 flex flex-wrap gap-1">
              {(obs.instruments || []).map(inst => (
                <span
                  key={inst}
                  className="px-1.5 py-0.5 rounded bg-space-900 border border-space-750 text-slate-400 text-[10px] font-mono"
                >
                  {inst}
                </span>
              ))}
            </div>

            <div className="mt-2.5 pt-2 border-t border-space-750/60 flex items-center justify-between text-[10px] text-slate-500 font-mono">
              <span>{obs.nasa_pds_reference || 'NASA PDS'}</span>
              <span className="text-telemetry-cyan flex items-center group-hover:translate-x-0.5 transition-transform">
                <Compass className="w-3 h-3 mr-0.5" />
                Fly To Site
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
