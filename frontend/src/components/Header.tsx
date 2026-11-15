import React, { useState, useEffect } from 'react';
import { 
  Compass, 
  FileText, 
  RotateCcw, 
  AlertTriangle, 
  CheckCircle2, 
  Radio, 
  Layers,
  Globe2,
  Map as MapIcon
} from 'lucide-react';

interface HeaderProps {
  isBackendConnected: boolean;
  onResetView: () => void;
  onOpenReport: () => void;
  onToggleLayers: () => void;
  showLayers: boolean;
  viewMode?: 'globe' | 'map';
  onToggleViewMode?: (mode: 'globe' | 'map') => void;
}

export const Header: React.FC<HeaderProps> = ({
  isBackendConnected,
  onResetView,
  onOpenReport,
  onToggleLayers,
  showLayers,
  viewMode,
  onToggleViewMode,
}) => {
  const marsSol = 1054;
  const [currentTime, setCurrentTime] = useState(new Date().toUTCString());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toUTCString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-14 bg-space-900 border-b border-space-750 px-4 flex items-center justify-between z-30 select-none shadow-lg">
      {/* Brand & Mission Title */}
      <div className="flex items-center space-x-3">
        <div className="relative flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-mars-600 to-mars-800 border border-mars-500/40 shadow-inner">
          <Compass className="w-5 h-5 text-white animate-spin-slow" />
          <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-telemetry-cyan opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-telemetry-cyan"></span>
          </span>
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-base font-bold tracking-wider text-white font-mono flex items-center">
              MARSWALK
              <span className="ml-2 text-[10px] font-semibold uppercase tracking-widest px-1.5 py-0.5 rounded bg-mars-500/20 text-mars-400 border border-mars-500/30">
                MVP v1.0
              </span>
            </h1>
          </div>
          <p className="text-[11px] text-slate-400 hidden sm:block">
            Intelligent Mars Exploration &amp; Mission Planning &bull; Jezero Crater
          </p>
        </div>
      </div>

      {/* Mission Telemetry & Sols */}
      <div className="hidden md:flex items-center space-x-6 text-xs font-mono">
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-space-850 border border-space-700/60">
          <Radio className="w-3.5 h-3.5 text-mars-400 animate-pulse" />
          <span className="text-slate-400">TARGET:</span>
          <span className="text-mars-300 font-semibold">JEZERO CRATER</span>
          <span className="text-slate-500 text-[10px]">(18.38°N, 77.58°E)</span>
        </div>

        <div className="flex items-center space-x-2 text-slate-300">
          <span className="text-slate-500">SOL:</span>
          <span className="text-telemetry-cyan font-bold">{marsSol}</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400 text-[11px]">{currentTime}</span>
        </div>
      </div>

      {/* Backend & Action Controls */}
      <div className="flex items-center space-x-2.5">
        {/* Backend Status Badge */}
        <div 
          className={`flex items-center space-x-1.5 px-2 py-1 rounded text-xs font-mono border transition-all ${
            isBackendConnected 
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300' 
              : 'bg-amber-950/40 border-amber-500/40 text-amber-300'
          }`}
          title={isBackendConnected ? "Connected to Developer B's FastAPI Backend" : "FastAPI Backend Offline — Operating in Standalone Prototype Simulation Mode"}
        >
          {isBackendConnected ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span className="hidden lg:inline text-[11px]">API: LIVE</span>
            </>
          ) : (
            <>
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span className="hidden lg:inline text-[11px]">DEMO / OFFLINE</span>
            </>
          )}
        </div>

        {/* 3D Globe / 2D Map View Switcher */}
        {onToggleViewMode && (
          <div className="hidden sm:flex items-center p-0.5 rounded bg-space-850 border border-space-700 font-mono text-xs">
            <button
              type="button"
              onClick={() => onToggleViewMode('globe')}
              className={`px-2 py-1 rounded flex items-center space-x-1 transition-all cursor-pointer ${
                viewMode === 'globe'
                  ? 'bg-mars-600 text-white font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="3D Spherical Mars Globe"
            >
              <Globe2 className="w-3.5 h-3.5 text-mars-300" />
              <span className="text-[11px]">3D Globe</span>
            </button>
            <button
              type="button"
              onClick={() => onToggleViewMode('map')}
              className={`px-2 py-1 rounded flex items-center space-x-1 transition-all cursor-pointer ${
                viewMode === 'map'
                  ? 'bg-space-700 text-white font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="2D Surface Map"
            >
              <MapIcon className="w-3.5 h-3.5 text-telemetry-cyan" />
              <span className="text-[11px]">2D Map</span>
            </button>
          </div>
        )}

        {/* Layer Toggle Button */}
        <button
          type="button"
          onClick={onToggleLayers}
          className={`px-2.5 py-1.5 rounded text-xs font-medium flex items-center space-x-1.5 border transition-all cursor-pointer ${
            showLayers 
              ? 'bg-space-700 text-white border-telemetry-cyan/50 shadow-sm shadow-cyan-500/20' 
              : 'bg-space-850 text-slate-300 border-space-700 hover:bg-space-800 hover:text-white'
          }`}
          title="Toggle Layer Controls"
        >
          <Layers className="w-3.5 h-3.5 text-telemetry-cyan" />
          <span className="hidden sm:inline">Layers</span>
        </button>

        {/* Reset Jezero View */}
        <button
          type="button"
          onClick={onResetView}
          className="px-2.5 py-1.5 rounded bg-space-850 hover:bg-space-800 text-slate-300 hover:text-white border border-space-700 text-xs font-medium flex items-center space-x-1.5 transition-all cursor-pointer"
          title="Center on Jezero Crater (Octavia E. Butler Landing)"
        >
          <RotateCcw className="w-3.5 h-3.5 text-mars-400" />
          <span className="hidden sm:inline">Jezero Focus</span>
        </button>

        {/* Mission Report / Export Modal */}
        <button
          type="button"
          onClick={onOpenReport}
          className="px-3 py-1.5 rounded bg-gradient-to-r from-mars-600 to-mars-700 hover:from-mars-500 hover:to-mars-600 text-white font-medium text-xs flex items-center space-x-1.5 shadow-md shadow-mars-900/40 border border-mars-400/30 transition-all cursor-pointer"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Mission Report</span>
        </button>
      </div>
    </header>
  );
};
