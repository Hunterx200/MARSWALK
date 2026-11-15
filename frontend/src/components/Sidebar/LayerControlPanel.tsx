import React from 'react';
import { MapLayerConfig } from '../../types/api';
import { MarsMapController } from '../../services/mapManager';
import { Layers, Eye, EyeOff, ShieldCheck, AlertCircle, Info } from 'lucide-react';

interface LayerControlPanelProps {
  layers: MapLayerConfig[];
  controller: MarsMapController;
  onToggleLayer: (layerId: string) => void;
  onUpdateOpacity: (layerId: string, opacity: number) => void;
}

export const LayerControlPanel: React.FC<LayerControlPanelProps> = ({
  layers = [],
  controller,
  onToggleLayer,
  onUpdateOpacity,
}) => {
  const safeLayers = Array.isArray(layers) ? layers : [];

  return (
    <div className="space-y-4 text-xs select-none">
      <div className="flex items-center justify-between pb-2 border-b border-space-750">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-telemetry-cyan" />
          <h3 className="font-bold text-slate-200 uppercase tracking-wider font-mono text-xs">
            Mars Map Layer Controller
          </h3>
        </div>
        <span className="text-[10px] text-slate-400 font-mono">
          {safeLayers.filter(l => l.visible).length} / {safeLayers.length} ACTIVE
        </span>
      </div>

      {/* Layer List */}
      <div className="space-y-2.5">
        {safeLayers.map(layer => (
          <div
            key={layer.id}
            className={`p-3 rounded-lg border transition-all ${
              layer.visible
                ? 'bg-space-850/90 border-space-700 shadow-sm'
                : 'bg-space-900/60 border-space-800 opacity-60'
            }`}
          >
            {/* Header / Visibility Toggle */}
            <div className="flex items-start justify-between">
              <div className="flex-1 pr-2">
                <div className="flex items-center space-x-1.5">
                  <span className="font-semibold text-slate-200 text-xs">{layer.name}</span>
                  {layer.verified_nasa_source ? (
                    <span 
                      className="flex items-center text-[9px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-500/30 font-mono"
                      title="Verified NASA/JPL Data Source"
                    >
                      <ShieldCheck className="w-2.5 h-2.5 mr-0.5" />
                      NASA
                    </span>
                  ) : (
                    <span 
                      className="flex items-center text-[9px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-500/30 font-mono"
                      title="Project Risk Model Derived from MOLA Topography"
                    >
                      <AlertCircle className="w-2.5 h-2.5 mr-0.5" />
                      MODEL
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                  {layer.description}
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  onToggleLayer(layer.id);
                  controller.setLayerVisibility(layer.id, !layer.visible);
                }}
                className={`p-1.5 rounded-md border transition-all cursor-pointer ${
                  layer.visible
                    ? 'bg-telemetry-cyan/20 border-telemetry-cyan/50 text-telemetry-cyan'
                    : 'bg-space-800 border-space-700 text-slate-500 hover:text-slate-300'
                }`}
                title={layer.visible ? 'Hide Layer' : 'Show Layer'}
              >
                {layer.visible ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
              </button>
            </div>

            {/* Opacity Slider */}
            {layer.visible && (
              <div className="mt-3 pt-2 border-t border-space-750/60 flex items-center space-x-2">
                <span className="text-[10px] text-slate-500 font-mono w-14">OPACITY:</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={layer.opacity}
                  onChange={e => {
                    const val = parseFloat(e.target.value);
                    onUpdateOpacity(layer.id, val);
                    controller.setLayerOpacity(layer.id, val);
                  }}
                  className="flex-1 h-1 bg-space-750 rounded-lg appearance-none cursor-pointer accent-telemetry-cyan"
                />
                <span className="text-[10px] font-mono text-slate-400 w-8 text-right">
                  {Math.round(layer.opacity * 100)}%
                </span>
              </div>
            )}

            {/* Layer Metadata / Limitations */}
            <div className="mt-2 text-[10px] text-slate-500 flex flex-wrap gap-x-3">
              <span>Resolution: {layer.resolution || 'Vector'}</span>
              <span>Coverage: {layer.coverage}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Transparent Data Limitations Notice */}
      <div className="p-3 rounded-lg bg-space-900 border border-space-750/80 text-[11px] text-slate-400 space-y-1.5">
        <div className="flex items-center space-x-1.5 text-amber-400 font-semibold font-mono text-xs">
          <Info className="w-3.5 h-3.5" />
          <span>DATA PROVENANCE &amp; LIMITATIONS</span>
        </div>
        <p className="leading-relaxed">
          NASA Mars Trek WMTS provides Viking color and MOLA shaded relief. Local Jezero slope vectors are computed from USGS MOLA areoid DTM models. Imagery does not detect sub-meter boulders or micro-sand traps.
        </p>
      </div>
    </div>
  );
};
