"""
Echoes of Asterra - Tilemap Engine Service
Encapsulates PyTMX map parsing behind a stable internal API.
Converts Tiled (.tmx/.json) layer matrices and object groups into native Pygame surfaces and hitboxes.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional
import pygame
from rpg.config import FeatureFlagConfig, game_config
from rpg.services.asset import AssetService

logger = logging.getLogger("TilemapService")

# Optional PyTMX import check
try:
    import pytmx
    from pytmx.util_pygame import load_pygame
    PYTMX_AVAILABLE = True
except ImportError:
    pytmx = None
    load_pygame = None
    PYTMX_AVAILABLE = False


@dataclass
class TilemapData:
    """Internal decoupled representation of a loaded map region."""
    map_id: str
    width_tiles: int = 30
    height_tiles: int = 20
    tile_width: int = 64
    tile_height: int = 64
    layers: List[Tuple[str, pygame.Surface]] = field(default_factory=list)
    collision_rects: List[pygame.Rect] = field(default_factory=list)
    spawners: List[Dict[str, Any]] = field(default_factory=list)


class TilemapService:
    """
    Encapsulates map file ingestion.
    Hides third-party PyTMX objects from callers.
    """
    def __init__(self, asset_service: Optional[AssetService] = None, feature_flags: Optional[FeatureFlagConfig] = None) -> None:
        self.asset_service = asset_service
        self.feature_flags = feature_flags or game_config.feature_flags
        self._map_cache: Dict[str, TilemapData] = {}
        self.max_cached_maps = 5

    def load_map(self, map_id: str) -> Optional[TilemapData]:
        """
        Public API: Loads Tiled map by logical identifier.
        Returns cached TilemapData or parses file via PyTMX.
        Returns procedural fallback structure on load error.
        """
        if map_id in self._map_cache:
            return self._map_cache[map_id]

        if not self.feature_flags.tilemap or not PYTMX_AVAILABLE:
            logger.warning("PyTMX not enabled or unavailable. Returning fallback TilemapData for map '%s'.", map_id)
            return self._create_procedural_fallback(map_id)

        # Resolve file path via AssetService manifest
        filepath = None
        if self.asset_service:
            filepath = self.asset_service.get_tileset_path(map_id)

        if not filepath:
            filepath = f"assets/maps/{map_id}.tmx"

        try:
            tiled_map = load_pygame(filepath)
            data = self._convert_tiled_map(map_id, tiled_map)
            
            # LRU Cache eviction if exceeds limit
            if len(self._map_cache) >= self.max_cached_maps:
                oldest_key = next(iter(self._map_cache))
                del self._map_cache[oldest_key]

            self._map_cache[map_id] = data
            logger.info("Successfully loaded and cached tilemap '%s' from %s", map_id, filepath)
            return data
        except Exception as e:
            logger.warning("Failed to load TMX file '%s' for map ID '%s': %s. Returning procedural fallback.", filepath, map_id, e)
            return self._create_procedural_fallback(map_id)

    def _convert_tiled_map(self, map_id: str, tmx_data: Any) -> TilemapData:
        """Converts PyTMX internal TiledMap instance to decoupled TilemapData."""
        width_tiles = tmx_data.width
        height_tiles = tmx_data.height
        tile_w = tmx_data.tilewidth
        tile_h = tmx_data.tileheight

        layers: List[Tuple[str, pygame.Surface]] = []
        collision_rects: List[pygame.Rect] = []
        spawners: List[Dict[str, Any]] = []

        # Process Visible Tile Layers
        for layer in tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                layer_surf = pygame.Surface((width_tiles * tile_w, height_tiles * tile_h), pygame.SRCALPHA)
                for x, y, image in layer.tiles():
                    if image:
                        layer_surf.blit(image, (x * tile_w, y * tile_h))
                layers.append((layer.name, layer_surf))

        # Process Object Groups (Collisions, Spawners, Triggers)
        for obj in tmx_data.objects:
            if obj.type == "collision" or getattr(obj, "properties", {}).get("solid", False):
                collision_rects.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))
            elif obj.type == "spawner":
                spawners.append({
                    "name": obj.name,
                    "entity_type": getattr(obj, "properties", {}).get("entity_type", "slime"),
                    "pos": (obj.x, obj.y),
                    "properties": getattr(obj, "properties", {})
                })

        return TilemapData(
            map_id=map_id,
            width_tiles=width_tiles,
            height_tiles=height_tiles,
            tile_width=tile_w,
            tile_height=tile_h,
            layers=layers,
            collision_rects=collision_rects,
            spawners=spawners
        )

    def _create_procedural_fallback(self, map_id: str) -> TilemapData:
        """Fallback map generator when TMX parsing is unavailable or fails."""
        data = TilemapData(map_id=map_id)
        # Create single ground layer
        ground_surf = pygame.Surface((30 * 64, 20 * 64))
        ground_surf.fill((40, 90, 40))  # Muted green grass
        data.layers.append(("Ground", ground_surf))
        return data

    def get_layer_surfaces(self, map_id: str) -> List[Tuple[str, pygame.Surface]]:
        """Public API: Returns list of (layer_name, Surface) for drawing."""
        data = self.load_map(map_id)
        return data.layers if data else []

    def get_collision_rects(self, map_id: str) -> List[pygame.Rect]:
        """Public API: Returns collision hitboxes for a map."""
        data = self.load_map(map_id)
        return data.collision_rects if data else []

    def get_spawners(self, map_id: str) -> List[Dict[str, Any]]:
        """Public API: Returns entity spawner definitions for a map."""
        data = self.load_map(map_id)
        return data.spawners if data else []

    def clear_cache(self) -> None:
        """Public API: Clears loaded map caches upon state reset."""
        self._map_cache.clear()
        logger.info("TilemapService map cache cleared.")
