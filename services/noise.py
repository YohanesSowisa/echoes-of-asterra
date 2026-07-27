"""
Echoes of Asterra - Noise Service
Encapsulates 2D/3D procedural noise generation for terrain biomes and resource distribution.
Features seed reproducibility and deterministic pseudo-random hash fallback.
"""
import math
from typing import List, Optional
from rpg.config import NoiseConfig, game_config

# Optional third-party opensimplex import
try:
    import opensimplex
    OPENSIMPLEX_AVAILABLE = True
except ImportError:
    opensimplex = None
    OPENSIMPLEX_AVAILABLE = False


class NoiseService:
    """
    Service wrapper for procedural noise.
    Owns 2D/3D noise generation for biome maps and ecological density.
    """
    def __init__(self, config: Optional[NoiseConfig] = None) -> None:
        self.config = config or game_config.noise
        self._noise_instances = {}

    def get_noise_2d(self, x: float, y: float, scale: float = 0.05, seed: int = 1337) -> float:
        """
        Public API: Evaluates 2D noise at coordinate (x, y).
        Returns normalized float between -1.0 and 1.0.
        """
        if self.config.enable_simplex and OPENSIMPLEX_AVAILABLE:
            try:
                if seed not in self._noise_instances:
                    self._noise_instances[seed] = opensimplex.OpenSimplex(seed=seed)
                ns = self._noise_instances[seed]
                return float(ns.noise2(x * scale, y * scale))
            except Exception:
                pass
        
        # Fallback: Deterministic pseudo-random sine/cosine hashing
        return self._hash_fallback_2d(x * scale, y * scale, seed)

    def generate_heightmap(self, width: int, height: int, scale: float = 0.05, seed: int = 1337) -> List[List[float]]:
        """
        Public API: Generates 2D grid array of noise values normalized between -1.0 and 1.0.
        """
        grid = []
        for y in range(height):
            row = []
            for x in range(width):
                row.append(self.get_noise_2d(x, y, scale=scale, seed=seed))
            grid.append(row)
        return grid

    def _hash_fallback_2d(self, x: float, y: float, seed: int) -> float:
        """Internal helper fallback: Pseudo-random hash returning float in [-1.0, 1.0]."""
        val = math.sin(x * 12.9898 + y * 78.233 + seed * 0.1) * 43758.5453
        frac = val - math.floor(val)
        return (frac * 2.0) - 1.0
