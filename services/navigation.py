"""
Echoes of Asterra - Navigation Service
Encapsulates grid pathfinding (A*) behind an internal abstraction layer.
Features path caching, moving target recalculation thresholds, and raycast fallback.
"""
import math
import time
from typing import Tuple, List, Dict, Optional, Any
from rpg.config import NavigationConfig, game_config
from rpg.settings import TILE_SIZE

# Optional third-party pathfinding library import
try:
    from pathfinding.core.grid import Grid
    from pathfinding.finder.a_star import AStarFinder
    PATHFINDING_AVAILABLE = True
except ImportError:
    Grid = None
    AStarFinder = None
    PATHFINDING_AVAILABLE = False


class NavigationService:
    """
    Service wrapper for A* pathfinding.
    Owns path calculation, cache invalidation, and fallback raycasting.
    """
    def __init__(self, config: Optional[NavigationConfig] = None, event_bus: Optional[Any] = None) -> None:
        self.config = config or game_config.navigation
        self.event_bus = event_bus
        self.grid_matrix: List[List[int]] = []
        self.grid_width: int = 0
        self.grid_height: int = 0
        
        # Path cache: (start_tile, goal_tile) -> (timestamp, List[pixel_waypoints])
        self._path_cache: Dict[Tuple[Tuple[int, int], Tuple[int, int]], Tuple[float, List[Tuple[float, float]]]] = {}
        
        # Performance tracking
        self.last_compute_time_ms: float = 0.0

        if self.event_bus and hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe("EVENT_WORLD_CHANGED", self.invalidate_cache)

    def set_grid(self, grid_matrix: List[List[int]]) -> None:
        """Sets or updates the tile obstacle matrix (0 = walkable, 1 = solid)."""
        self.grid_matrix = grid_matrix
        self.grid_height = len(grid_matrix)
        self.grid_width = len(grid_matrix[0]) if self.grid_height > 0 else 0
        self.invalidate_cache()

    def invalidate_cache(self, *args: Any, **kwargs: Any) -> None:
        """Flushes path cache when world state or obstacle layout changes."""
        self._path_cache.clear()

    def find_path(
        self,
        start_pos: Tuple[float, float],
        goal_pos: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """
        Public API: Calculates path from start_pos to goal_pos (in pixel coordinates).
        Returns list of pixel waypoints [(x, y), ...]. Returns [] on failure or arrival.
        """
        if not self.grid_matrix or self.grid_width == 0 or self.grid_height == 0:
            return [goal_pos]

        start_tile = (int(start_pos[0] // TILE_SIZE), int(start_pos[1] // TILE_SIZE))
        goal_tile = (int(goal_pos[0] // TILE_SIZE), int(goal_pos[1] // TILE_SIZE))

        # Clamp tiles to grid bounds
        start_tile = (max(0, min(self.grid_width - 1, start_tile[0])), max(0, min(self.grid_height - 1, start_tile[1])))
        goal_tile = (max(0, min(self.grid_width - 1, goal_tile[0])), max(0, min(self.grid_height - 1, goal_tile[1])))

        if start_tile == goal_tile:
            return [goal_pos]

        # Check cache
        cache_key = (start_tile, goal_tile)
        now = time.time()
        if cache_key in self._path_cache:
            cached_time, cached_path = self._path_cache[cache_key]
            if now - cached_time < self.config.recalc_interval_seconds:
                return list(cached_path)

        start_t0 = time.perf_counter()
        
        # Execute A* via pathfinding library if enabled and available
        path_waypoints = []
        if self.config.enable_astar and PATHFINDING_AVAILABLE:
            path_waypoints = self._compute_astar(start_tile, goal_tile, goal_pos)

        # Fallback to raycast direct path if A* disabled, unavailable, or failed
        if not path_waypoints:
            path_waypoints = self._compute_fallback_raycast(start_pos, goal_pos, start_tile, goal_tile)

        self.last_compute_time_ms = (time.perf_counter() - start_t0) * 1000.0

        # Store in cache
        self._path_cache[cache_key] = (now, path_waypoints)
        return list(path_waypoints)

    def _compute_astar(
        self,
        start_tile: Tuple[int, int],
        goal_tile: Tuple[int, int],
        goal_pos: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """Internal helper: Computes A* path using third-party pathfinding library."""
        try:
            # Map 0 = walkable, 1 = solid -> pathfinding grid: 1 = walkable, 0 = obstacle
            matrix = [[0 if cell == 1 else 1 for cell in row] for row in self.grid_matrix]
            
            # Ensure start and goal tiles are walkable for pathing
            matrix[start_tile[1]][start_tile[0]] = 1
            matrix[goal_tile[1]][goal_tile[0]] = 1
            
            grid = Grid(matrix=matrix)
            start_node = grid.node(start_tile[0], start_tile[1])
            goal_node = grid.node(goal_tile[0], goal_tile[1])
            
            finder = AStarFinder()
            path_nodes, _ = finder.find_path(start_node, goal_node, grid)
            
            if len(path_nodes) > 1:
                waypoints = []
                for node in path_nodes[1:-1]:
                    px = node.x * TILE_SIZE + TILE_SIZE // 2
                    py = node.y * TILE_SIZE + TILE_SIZE // 2
                    waypoints.append((float(px), float(py)))
                waypoints.append(goal_pos)
                return waypoints
        except Exception as e:
            # Graceful error handling - log warning and proceed to fallback
            pass
        return []

    def _compute_fallback_raycast(
        self,
        start_pos: Tuple[float, float],
        goal_pos: Tuple[float, float],
        start_tile: Tuple[int, int],
        goal_tile: Tuple[int, int]
    ) -> List[Tuple[float, float]]:
        """Internal helper fallback: Direct vector movement with simple neighbor obstacle bypass."""
        # If direct path is solid, try nearest adjacent walkable tile
        if self._is_tile_solid(goal_tile[0], goal_tile[1]):
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = goal_tile[0] + dx, goal_tile[1] + dy
                if not self._is_tile_solid(nx, ny):
                    return [(nx * TILE_SIZE + TILE_SIZE // 2, ny * TILE_SIZE + TILE_SIZE // 2)]
        return [goal_pos]

    def _is_tile_solid(self, tx: int, ty: int) -> bool:
        """Returns True if tile coordinate is solid or out of grid bounds."""
        if tx < 0 or tx >= self.grid_width or ty < 0 or ty >= self.grid_height:
            return True
        return self.grid_matrix[ty][tx] == 1
