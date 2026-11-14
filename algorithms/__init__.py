"""MARSWALK Algorithms Package.

Intelligent Mars Exploration & Mission Planning System.
Target Region: Jezero Crater, Mars.

This package provides:
- A* Pathfinding (8-connected grid with corner-cutting prevention)
- Terrain cost calculation (slope gradient and surface roughness)
- Hazard proximity buffer and risk scoring
- Alternative route generation (Direct, Safe, Balanced)
- Mars geographic coordinate transformations (Jezero Crater lon/lat to local grid)
- Documented synthetic benchmark grids for testing and integration
"""

__version__ = "0.1.0"
__author__ = "MARSWALK Engineering Team - Developer C (Algorithms)"
