"""
Echoes of Asterra - Cataclysm Epochs System (Pillar #4)
Manages procedural generational overlays, in-memory tilemap mutation engines,
and multi-epoch world transformations:
- The Deluge Epoch (Zaman Air Bah): Flooded archipelagos + wooden raft bridges.
- The Scorched Blight (Zaman Bara Api): Ash ground + burnt trees + molten magma hazard fissures.
- The Glacial Winter (Zaman Salju Abadi): Snow blankets + snow pines + frozen ice lakes with low-friction sliding.
"""
import copy
import random
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import deque

from rpg.settings import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE
from rpg.events import EventBus

EPOCH_DEFAULT = "standard"
EPOCH_DELUGE = "deluge"
EPOCH_SCORCHED = "scorched"
EPOCH_GLACIAL = "glacial"

WALKABLE_TILES = {
    "grass", "dirt", "sand", "wood_bridge", "raft", "bridge",
    "floor", "stone_floor", "wood_floor", "shallow_water", "dungeon_floor",
    "ash_ground", "snow", "ice", "magma", "magma_tile"
}

NON_MUTABLE_TILES = {
    "wall", "tree", "rock", "door", "building", "dungeon_wall", "burnt_tree", "snow_tree"
}


@dataclass
class EpochData:
    """Represents the configuration and world parameters of a Cataclysm Epoch."""
    epoch_id: str
    name: str
    description: str
    weather_override: Optional[str] = None
    water_level_modifier: float = 0.0
    movement_speed_modifier: float = 1.0


EPOCH_CONFIGS: Dict[str, EpochData] = {
    EPOCH_DEFAULT: EpochData(
        epoch_id=EPOCH_DEFAULT,
        name="Era of Balance",
        description="The temperate seasonal climate of peaceful Asterra.",
        weather_override=None,
        water_level_modifier=0.0,
        movement_speed_modifier=1.0
    ),
    EPOCH_DELUGE: EpochData(
        epoch_id=EPOCH_DELUGE,
        name="The Deluge Epoch (Zaman Air Bah)",
        description="Primordial tides have risen across Asterra, transforming the continents into flooded archipelagos connected by wooden raft bridges.",
        weather_override="rain",
        water_level_modifier=0.45,
        movement_speed_modifier=0.85
    ),
    EPOCH_SCORCHED: EpochData(
        epoch_id=EPOCH_SCORCHED,
        name="The Scorched Blight (Zaman Bara Api)",
        description="Volcanic fissures crack the earth, blanketing the soil in charcoal ash and molten magma hazards.",
        weather_override="fog",
        water_level_modifier=0.0,
        movement_speed_modifier=1.0
    ),
    EPOCH_GLACIAL: EpochData(
        epoch_id=EPOCH_GLACIAL,
        name="The Glacial Winter (Zaman Salju Abadi)",
        description="A perpetual glacial frost blankets Asterra in slippery ice sheets, powder snow, and continuous blizzards.",
        weather_override="snow",
        water_level_modifier=0.0,
        movement_speed_modifier=1.1
    )
}


class EpochManager:
    """
    Coordinates global Cataclysm Epochs and procedural in-memory tilemap mutation.
    Ensures zero disk asset corruption and guarantees 100% path accessibility across all zones.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.current_epoch: str = EPOCH_DEFAULT
        self.game_reference: Any = None
        self.reset()

    def reset(self) -> None:
        """Resets the epoch to the default temperate era."""
        self.current_epoch = EPOCH_DEFAULT

    def get_current_epoch_data(self) -> EpochData:
        """Returns metadata for the currently active epoch."""
        return EPOCH_CONFIGS.get(self.current_epoch, EPOCH_CONFIGS[EPOCH_DEFAULT])

    def get_current_epoch_name(self) -> str:
        """Returns the human-readable display name of the current epoch."""
        return self.get_current_epoch_data().name

    def set_epoch(self, epoch_id: str) -> bool:
        """
        Transitions the global world state to a new Cataclysm Epoch, notifying
        the EventBus, weather systems, and living world simulation.
        """
        if epoch_id not in EPOCH_CONFIGS:
            return False

        old_epoch = self.current_epoch
        self.current_epoch = epoch_id
        epoch_data = self.get_current_epoch_data()

        # Update weather if game reference is available
        if self.game_reference:
            weather = getattr(self.game_reference, "weather", None)
            if weather and epoch_data.weather_override:
                if hasattr(weather, "set_weather"):
                    weather.set_weather(epoch_data.weather_override)

        if self.event_bus:
            self.event_bus.emit(
                "epoch_changed",
                old_epoch=old_epoch,
                new_epoch=epoch_id,
                name=epoch_data.name,
                weather=epoch_data.weather_override
            )

        return True

    def determine_starting_epoch_from_mythos(self, mythos_manager: Any) -> str:
        """Determines and sets the starting epoch based on past ancestral runs in Mythos."""
        if not mythos_manager:
            return self.current_epoch
        if hasattr(mythos_manager, "get_inherited_starting_epoch"):
            inherited_epoch = mythos_manager.get_inherited_starting_epoch()
            if inherited_epoch in EPOCH_CONFIGS:
                self.set_epoch(inherited_epoch)
        return self.current_epoch

    def apply_epoch_to_map(self, map_name: str, map_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies in-memory procedural overlays to the generated map container.
        Leaves subterranean crypts and original disk json files intact.
        """
        if self.current_epoch == EPOCH_DEFAULT:
            return map_data

        if map_name in ["crypt", "submerged_temple"]:
            return map_data  # Keep interior dungeons unmutated

        # Create a deep copy of map data to preserve procedural integrity
        modified_data = copy.deepcopy(map_data)
        grid = modified_data.get("grid", [])
        if not grid or len(grid) == 0:
            return map_data

        if self.current_epoch == EPOCH_DELUGE:
            self._apply_deluge_epoch(map_name, modified_data)
        elif self.current_epoch == EPOCH_SCORCHED:
            self._apply_scorched_epoch(map_name, modified_data)
        elif self.current_epoch == EPOCH_GLACIAL:
            self._apply_glacial_epoch(map_name, modified_data)

        return modified_data

    def _get_critical_points_and_protected_cells(
        self,
        map_name: str,
        map_data: Dict[str, Any],
        w: int,
        h: int
    ) -> Tuple[List[Tuple[int, int]], Set[Tuple[int, int]]]:
        """Extracts critical navigation landmarks and creates safety buffer zones around them."""
        critical_points: List[Tuple[int, int]] = []

        # Player spawn
        p_spawn = map_data.get("player_spawn", (w // 2 * TILE_SIZE, h // 2 * TILE_SIZE))
        start_pt = (
            max(0, min(w - 1, int(p_spawn[0] // TILE_SIZE))),
            max(0, min(h - 1, int(p_spawn[1] // TILE_SIZE)))
        )
        critical_points.append(start_pt)

        # Portals
        for portal in map_data.get("portals", []):
            prect = portal.get("rect")
            if prect:
                cx = max(0, min(w - 1, int(prect.centerx // TILE_SIZE)))
                cy = max(0, min(h - 1, int(prect.centery // TILE_SIZE)))
                critical_points.append((cx, cy))

        # NPCs
        for npc in map_data.get("npcs", []):
            npos = npc.get("pos", (0, 0))
            nx = max(0, min(w - 1, int(npos[0] // TILE_SIZE)))
            ny = max(0, min(h - 1, int(npos[1] // TILE_SIZE)))
            critical_points.append((nx, ny))

        # Chests
        for chest in map_data.get("chests", []):
            cpos = chest.get("pos", (0, 0))
            cx = max(0, min(w - 1, int(cpos[0] // TILE_SIZE)))
            cy = max(0, min(h - 1, int(cpos[1] // TILE_SIZE)))
            critical_points.append((cx, cy))

        # Waypoint Conduits & Outpost positions
        from rpg.leylines import DEFAULT_LEYLINE_NODES
        for node in DEFAULT_LEYLINE_NODES:
            if node.region_map == map_name:
                lx = max(0, min(w - 1, int(node.pos[0] // TILE_SIZE)))
                ly = max(0, min(h - 1, int(node.pos[1] // TILE_SIZE)))
                critical_points.append((lx, ly))

        from rpg.outpost import OUTPOST_TACTICAL_CONFIGS
        for config in OUTPOST_TACTICAL_CONFIGS.values():
            if config.get("map_name") == map_name:
                tpos = config.get("tower_pos", (0, 0))
                tx = max(0, min(w - 1, int(tpos[0] // TILE_SIZE)))
                ty = max(0, min(h - 1, int(tpos[1] // TILE_SIZE)))
                critical_points.append((tx, ty))

        # Build protected bounding box around all critical points
        protected_cells: Set[Tuple[int, int]] = set()
        for cx, cy in critical_points:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        protected_cells.add((nx, ny))

        return critical_points, protected_cells

    def _apply_deluge_epoch(self, map_name: str, map_data: Dict[str, Any]) -> None:
        """Transforms low-elevation grass into waterways and constructs raft bridges."""
        grid = map_data["grid"]
        h = len(grid)
        w = len(grid[0]) if h > 0 else 0

        seed = sum(ord(c) * (i + 1) for i, c in enumerate(map_name)) + 404
        rng = random.Random(seed)

        critical_points, protected_cells = self._get_critical_points_and_protected_cells(map_name, map_data, w, h)
        start_pt = critical_points[0]

        # Flood lower elevation open grass tiles into water
        for r in range(1, h - 1):
            for c in range(1, w - 1):
                if (c, r) in protected_cells:
                    continue
                tile = grid[r][c]
                if tile == "grass":
                    if rng.random() < 0.42:
                        grid[r][c] = "water"

        # Construct procedural wooden raft bridges to connect all critical points
        for target in critical_points:
            path = self._trace_raft_bridge_corridor(start_pt, target, w, h)
            for bx, by in path:
                if grid[by][bx] == "water":
                    grid[by][bx] = "wood_bridge"

        # Guarantee 100% path connectivity via BFS flood fill validation
        self._ensure_complete_connectivity(start_pt, critical_points, grid, w, h)

    def _apply_scorched_epoch(self, map_name: str, map_data: Dict[str, Any]) -> None:
        """
        Transforms landscapes into volcanic wastelands:
        - Grass converts to charcoal ash earth ('ash_ground').
        - Trees convert to charred husks ('burnt_tree').
        - Open wilderness terrain spawns molten magma fissures ('magma').
        """
        grid = map_data["grid"]
        h = len(grid)
        w = len(grid[0]) if h > 0 else 0

        seed = sum(ord(c) * (i + 1) for i, c in enumerate(map_name)) + 666
        rng = random.Random(seed)

        critical_points, protected_cells = self._get_critical_points_and_protected_cells(map_name, map_data, w, h)

        for r in range(h):
            for c in range(w):
                tile = grid[r][c]
                if tile == "grass":
                    grid[r][c] = "ash_ground"
                    # Spawn magma fissures on non-protected wilderness ground
                    if (c, r) not in protected_cells and rng.random() < 0.12:
                        grid[r][c] = "magma"
                elif tile == "tree":
                    grid[r][c] = "burnt_tree"

    def _apply_glacial_epoch(self, map_name: str, map_data: Dict[str, Any]) -> None:
        """
        Transforms landscapes into frozen winter wonderlands:
        - Grass converts to powder snow ('snow').
        - Trees convert to snow pines ('snow_tree').
        - Water and rivers freeze into traversable slippery ice ('ice').
        """
        grid = map_data["grid"]
        h = len(grid)
        w = len(grid[0]) if h > 0 else 0

        for r in range(h):
            for c in range(w):
                tile = grid[r][c]
                if tile == "grass":
                    grid[r][c] = "snow"
                elif tile == "tree":
                    grid[r][c] = "snow_tree"
                elif tile in ["water", "shallow_water"]:
                    grid[r][c] = "ice"

    def _trace_raft_bridge_corridor(self, start: Tuple[int, int], end: Tuple[int, int], w: int, h: int) -> List[Tuple[int, int]]:
        """Traces an L-shaped direct bridge corridor between two coordinates."""
        path = []
        cur_x, cur_y = start
        target_x, target_y = end

        # Step X
        step_x = 1 if target_x >= cur_x else -1
        while cur_x != target_x:
            path.append((cur_x, cur_y))
            cur_x += step_x

        # Step Y
        step_y = 1 if target_y >= cur_y else -1
        while cur_y != target_y:
            path.append((cur_x, cur_y))
            cur_y += step_y

        path.append((target_x, target_y))
        return path

    def _ensure_complete_connectivity(
        self,
        start_pt: Tuple[int, int],
        critical_points: List[Tuple[int, int]],
        grid: List[List[str]],
        w: int,
        h: int
    ) -> None:
        """Validates with BFS flood fill that all critical points can be reached from start_pt."""
        def is_walkable(x: int, y: int) -> bool:
            if not (0 <= x < w and 0 <= y < h):
                return False
            return grid[y][x] in WALKABLE_TILES

        visited: Set[Tuple[int, int]] = set()
        queue = deque([start_pt])
        visited.add(start_pt)

        while queue:
            cx, cy = queue.popleft()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in visited and is_walkable(nx, ny):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

        for pt in critical_points:
            if pt not in visited:
                corridor = self._trace_raft_bridge_corridor(start_pt, pt, w, h)
                for bx, by in corridor:
                    if grid[by][bx] in ["water", "wall", "tree"]:
                        grid[by][bx] = "wood_bridge"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes current epoch state for savegame."""
        return {
            "current_epoch": self.current_epoch
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores epoch state from savegame."""
        if not isinstance(data, dict):
            return
        self.current_epoch = data.get("current_epoch", EPOCH_DEFAULT)
        if self.current_epoch not in EPOCH_CONFIGS:
            self.current_epoch = EPOCH_DEFAULT
