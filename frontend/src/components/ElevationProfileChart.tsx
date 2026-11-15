import React, { useState } from 'react';
import { Waypoint, RouteProfile } from '../types/api';
import { TrendingUp } from 'lucide-react';

interface ElevationProfileChartProps {
  waypoints: Waypoint[];
  onHoverWaypoint?: (wp: Waypoint | null) => void;
  profile?: RouteProfile;
}

export const ElevationProfileChart: React.FC<ElevationProfileChartProps> = ({
  waypoints,
  onHoverWaypoint,
  profile = 'balanced',
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const themeColor = profile === 'direct'
    ? '#f97316'
    : profile === 'safe'
    ? '#10b981'
    : '#06b6d4';

  if (!waypoints || waypoints.length < 2) {
    return (
      <div className="h-28 flex items-center justify-center text-xs text-slate-500 font-mono bg-space-900/60 rounded-lg border border-space-800">
        Generate a route to inspect elevation profile
      </div>
    );
  }

  const elevations = waypoints.map(w => w.elevation_m);
  const minElev = Math.min(...elevations) - 10;
  const maxElev = Math.max(...elevations) + 10;
  const elevRange = Math.max(1, maxElev - minElev);

  const totalDist = waypoints[waypoints.length - 1].cumulative_distance_m;

  // Chart dimensions
  const width = 600;
  const height = 120;
  const padding = { top: 15, right: 20, bottom: 25, left: 45 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const points = waypoints.map(w => {
    const x = padding.left + (w.cumulative_distance_m / Math.max(1, totalDist)) * plotWidth;
    const y = padding.top + plotHeight - ((w.elevation_m - minElev) / elevRange) * plotHeight;
    return { x, y, wp: w };
  });

  const pathD = points.reduce((acc, pt, idx) => {
    return `${acc} ${idx === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`;
  }, '');

  const areaD = `${pathD} L ${points[points.length - 1].x.toFixed(1)} ${height - padding.bottom} L ${points[0].x.toFixed(1)} ${height - padding.bottom} Z`;

  return (
    <div className="p-3 rounded-xl bg-space-900/90 border border-space-750 text-xs font-mono select-none">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2 text-slate-300">
          <TrendingUp className="w-4 h-4 text-telemetry-cyan" />
          <span className="font-bold uppercase tracking-wider text-[11px]">
            Terrain Elevation &amp; Slope Profile
          </span>
        </div>
        <div className="flex items-center space-x-3 text-[10px] text-slate-400">
          <span className="flex items-center"><span className="w-2 h-2 rounded-full bg-emerald-400 mr-1" /> &lt;7° Flat</span>
          <span className="flex items-center"><span className="w-2 h-2 rounded-full bg-amber-400 mr-1" /> 7°-12° Sloped</span>
          <span className="flex items-center"><span className="w-2 h-2 rounded-full bg-rose-500 mr-1" /> &gt;12° Steep</span>
        </div>
      </div>

      <div className="relative w-full overflow-hidden">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-28">
          <defs>
            <linearGradient id="elevGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={themeColor} stopOpacity="0.35" />
              <stop offset="100%" stopColor={themeColor} stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={width - padding.right}
            y2={padding.top}
            stroke="#1e293b"
            strokeDasharray="3,3"
          />
          <line
            x1={padding.left}
            y1={padding.top + plotHeight / 2}
            x2={width - padding.right}
            y2={padding.top + plotHeight / 2}
            stroke="#1e293b"
            strokeDasharray="3,3"
          />
          <line
            x1={padding.left}
            y1={height - padding.bottom}
            x2={width - padding.right}
            y2={height - padding.bottom}
            stroke="#334155"
          />

          {/* Y Axis labels */}
          <text x={padding.left - 6} y={padding.top + 4} textAnchor="end" fill="#64748b" fontSize="9">
            {maxElev}m
          </text>
          <text x={padding.left - 6} y={padding.top + plotHeight / 2 + 3} textAnchor="end" fill="#64748b" fontSize="9">
            {Math.round((minElev + maxElev) / 2)}m
          </text>
          <text x={padding.left - 6} y={height - padding.bottom} textAnchor="end" fill="#64748b" fontSize="9">
            {minElev}m
          </text>

          {/* X Axis labels */}
          <text x={padding.left} y={height - 8} textAnchor="start" fill="#64748b" fontSize="9">
            0 km
          </text>
          <text x={width - padding.right} y={height - 8} textAnchor="end" fill="#64748b" fontSize="9">
            {(totalDist / 1000).toFixed(2)} km
          </text>

          {/* Area fill */}
          <path d={areaD} fill="url(#elevGradient)" />

          {/* Stroke path */}
          <path d={pathD} fill="none" stroke={themeColor} strokeWidth="2.5" />

          {/* Waypoint circles with color-coded slopes */}
          {points.map((pt, idx) => {
            const isHovered = hoveredIndex === idx;
            const slopeColor = pt.wp.slope_deg > 12 ? '#ef4444' : pt.wp.slope_deg > 7 ? '#f59e0b' : '#10b981';

            return (
              <g key={idx}>
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={isHovered ? 6 : 3.5}
                  fill={slopeColor}
                  stroke="#0b0f17"
                  strokeWidth="1.5"
                  className="cursor-pointer transition-all"
                  onMouseEnter={() => {
                    setHoveredIndex(idx);
                    onHoverWaypoint?.(pt.wp);
                  }}
                  onMouseLeave={() => {
                    setHoveredIndex(null);
                    onHoverWaypoint?.(null);
                  }}
                />
              </g>
            );
          })}
        </svg>

        {/* Floating tooltip for hovered point */}
        {hoveredIndex !== null && points[hoveredIndex] && (
          <div
            className="absolute z-20 pointer-events-none transform -translate-x-1/2 -translate-y-full px-2 py-1 rounded bg-space-950/95 border border-telemetry-cyan text-[10px] text-slate-200 shadow-xl"
            style={{
              left: `${(points[hoveredIndex].x / width) * 100}%`,
              top: `${(points[hoveredIndex].y / height) * 100}%`,
            }}
          >
            <div className="font-bold text-telemetry-cyan">WP-{points[hoveredIndex].wp.index}</div>
            <div>Elev: {points[hoveredIndex].wp.elevation_m}m &bull; Slope: {points[hoveredIndex].wp.slope_deg}°</div>
            <div>Dist: {points[hoveredIndex].wp.cumulative_distance_m}m &bull; Sol {points[hoveredIndex].wp.estimated_sol}</div>
          </div>
        )}
      </div>
    </div>
  );
};
