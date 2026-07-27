"""
Echoes of Asterra - Asset & Manifest Pipeline Service
Provides centralized asset loading, logical ID resolution, texture/sound caching,
and fail-fast manifest verification with graceful runtime fallbacks.
"""
import os
import json
import logging
from typing import Dict, Optional, Tuple, Any
import pygame
from rpg.config import AssetConfig, game_config

logger = logging.getLogger("AssetService")


class AssetService:
    """
    Service boundary for asset management.
    Gameplay modules request assets exclusively by logical ID (e.g. 'player_idle', 'village_tileset').
    File paths are hidden behind the manifest layer.
    """
    def __init__(self, config: Optional[AssetConfig] = None) -> None:
        self.config = config or game_config.asset
        self.manifest_path = self.config.manifest_path
        
        # Manifest data structures
        self.textures_manifest: Dict[str, str] = {}
        self.fonts_manifest: Dict[str, str] = {}
        self.sounds_manifest: Dict[str, str] = {}
        self.tilesets_manifest: Dict[str, str] = {}
        
        # Caches
        self._texture_cache: Dict[str, pygame.Surface] = {}
        self._font_cache: Dict[Tuple[str, int], pygame.font.Font] = {}
        self._sound_cache: Dict[str, pygame.mixer.Sound] = {}
        
        # Fallback surface (64x64 magenta/black checkerboard)
        self._fallback_texture: Optional[pygame.Surface] = None
        
        # Load and validate manifest (Fail-Fast condition)
        self._load_manifest()

    def _load_manifest(self) -> None:
        """
        Parses manifest JSON.
        CRITICAL Fail-fast policy: Invalid or missing manifest aborts engine boot.
        """
        if not os.path.exists(self.manifest_path):
            # Create default manifest if missing in local dev environment
            self._create_default_manifest()
            
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self.textures_manifest = data.get("textures", {})
            self.fonts_manifest = data.get("fonts", {})
            self.sounds_manifest = data.get("sounds", {})
            self.tilesets_manifest = data.get("tilesets", {})
            logger.info("Asset manifest loaded successfully from %s", self.manifest_path)
        except Exception as e:
            error_msg = f"CRITICAL: Failed to parse asset manifest at '{self.manifest_path}': {e}"
            logger.critical(error_msg)
            raise RuntimeError(error_msg) from e

    def _create_default_manifest(self) -> None:
        """Creates fallback manifest file if missing."""
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        default_data = {
            "version": "1.0.0",
            "textures": {},
            "fonts": {},
            "sounds": {},
            "tilesets": {}
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2)

    def _get_fallback_texture(self) -> pygame.Surface:
        """Generates a 64x64 magenta/black checkerboard pattern as a missing-texture fallback."""
        if self._fallback_texture is None:
            w, h = self.config.fallback_texture_size
            surf = pygame.Surface((w, h))
            surf.fill((255, 0, 255))  # Magenta base
            half_w, half_h = w // 2, h // 2
            black = (0, 0, 0)
            pygame.draw.rect(surf, black, (0, 0, half_w, half_h))
            pygame.draw.rect(surf, black, (half_w, half_h, half_w, half_h))
            self._fallback_texture = surf
        return self._fallback_texture

    def get_texture(self, texture_id: str) -> pygame.Surface:
        """
        Public API: Retrieves texture surface by logical identifier.
        Returns magenta checkerboard fallback on runtime load failure.
        """
        if texture_id in self._texture_cache:
            return self._texture_cache[texture_id]
            
        rel_path = self.textures_manifest.get(texture_id)
        if not rel_path or not os.path.exists(rel_path):
            logger.warning("Runtime texture asset missing for ID '%s' (path: %s). Using fallback surface.", texture_id, rel_path)
            return self._get_fallback_texture()
            
        try:
            surface = pygame.image.load(rel_path).convert_alpha()
            self._texture_cache[texture_id] = surface
            return surface
        except Exception as e:
            logger.warning("Failed to load texture file '%s' for ID '%s': %s. Using fallback surface.", rel_path, texture_id, e)
            return self._get_fallback_texture()

    def get_font(self, font_id: str, size: int = 16) -> pygame.font.Font:
        """
        Public API: Retrieves font instance by logical identifier and size.
        Returns system default font on runtime load failure.
        """
        cache_key = (font_id, size)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]
            
        rel_path = self.fonts_manifest.get(font_id)
        if rel_path and os.path.exists(rel_path):
            try:
                font = pygame.font.Font(rel_path, size)
                self._font_cache[cache_key] = font
                return font
            except Exception as e:
                logger.warning("Failed to load font file '%s' for ID '%s': %s. Using SysFont fallback.", rel_path, font_id, e)
                
        # System font fallback
        font = pygame.font.SysFont(None, size)
        self._font_cache[cache_key] = font
        return font

    def get_sound(self, sound_id: str) -> Optional[pygame.mixer.Sound]:
        """
        Public API: Retrieves sound instance by logical identifier.
        Returns None / silent log on missing sound or uninitialized audio mixer.
        """
        if sound_id in self._sound_cache:
            return self._sound_cache[sound_id]
            
        if not pygame.mixer.get_init():
            logger.warning("Sound requested for ID '%s' but pygame.mixer is uninitialized.", sound_id)
            return None
            
        rel_path = self.sounds_manifest.get(sound_id)
        if not rel_path or not os.path.exists(rel_path):
            logger.warning("Sound asset missing for ID '%s' (path: %s).", sound_id, rel_path)
            return None
            
        try:
            sound = pygame.mixer.Sound(rel_path)
            self._sound_cache[sound_id] = sound
            return sound
        except Exception as e:
            logger.warning("Failed to load sound file '%s' for ID '%s': %s.", rel_path, sound_id, e)
            return None

    def get_tileset_path(self, tileset_id: str) -> Optional[str]:
        """Public API: Resolves logical tileset/map ID to underlying filepath."""
        path = self.tilesets_manifest.get(tileset_id)
        if not path:
            logger.warning("Tileset ID '%s' not registered in asset manifest.", tileset_id)
        return path

    def unload_unused(self) -> None:
        """Public API: Flushes non-essential texture caches upon map or state transition."""
        self._texture_cache.clear()
        logger.info("AssetService texture cache flushed.")
