"""
Echoes of Asterra - Sprite Classes & Procedural Injury Engine
Defines base sprite classes, Y-sorted rendering group, and visceral procedural injury surface generators.
"""
import pygame
from typing import List, Tuple, Union, Dict

_INJURY_SURFACE_CACHE: Dict[Tuple[int, int], pygame.Surface] = {}

def get_injured_surface(base_surface: pygame.Surface, hp_ratio: float, is_boss: bool = False) -> pygame.Surface:
    """
    Generates or retrieves cached visceral procedural injury surface variants based on HP ratio:
    - HP > 0.66: Stage 0 - Pristine / Undamaged.
    - 0.33 < HP <= 0.66: Stage 1 - Lacerated / Deep Blood Gashes.
    - HP <= 0.33: Stage 2 - Mutilated / Severed Limb & Exposed Bone/Viscera.
    - HP <= 0.20 (Boss): Stage 3 - Visceral Enrage / Crimson Aura & Bleeding Core.
    """
    if hp_ratio > 0.66:
        return base_surface

    stage = 1
    if is_boss and hp_ratio <= 0.20:
        stage = 3
    elif hp_ratio <= 0.33:
        stage = 2

    # Create unique cache key using object ID of base surface and stage index
    cache_key = (id(base_surface), stage)
    if cache_key in _INJURY_SURFACE_CACHE:
        return _INJURY_SURFACE_CACHE[cache_key]

    # Create copy of original sprite surface
    injured_surf = base_surface.copy()
    w, h = injured_surf.get_size()
    mask = pygame.mask.from_surface(base_surface)

    if stage == 1:
        # STAGE 1: Visceral Lacerations & Deep Blood Gashes (66% HP threshold)
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        cut_color_dark = (120, 10, 10, 230)
        cut_color_bright = (200, 20, 20, 240)
        
        # Diagonal cuts across torso
        pygame.draw.line(overlay, cut_color_dark, (int(w * 0.25), int(h * 0.25)), (int(w * 0.75), int(h * 0.65)), 2)
        pygame.draw.line(overlay, cut_color_bright, (int(w * 0.25), int(h * 0.25)), (int(w * 0.65), int(h * 0.55)), 1)
        pygame.draw.line(overlay, cut_color_dark, (int(w * 0.2), int(h * 0.6)), (int(w * 0.6), int(h * 0.8)), 2)

        # Blood pooling spots
        pygame.draw.circle(overlay, (140, 15, 15, 210), (int(w * 0.45), int(h * 0.5)), max(2, int(w * 0.12)))

        # Blend overlay onto sprite confined strictly to non-transparent mask pixels
        for x in range(w):
            for y in range(h):
                if mask.get_at((x, y)):
                    ov_color = overlay.get_at((x, y))
                    if ov_color.a > 0:
                        src_color = injured_surf.get_at((x, y))
                        blended_r = int(src_color.r * 0.4 + ov_color.r * 0.6)
                        blended_g = int(src_color.g * 0.2 + ov_color.g * 0.8)
                        blended_b = int(src_color.b * 0.2 + ov_color.b * 0.8)
                        injured_surf.set_at((x, y), (blended_r, blended_g, blended_b, src_color.a))

    elif stage == 2:
        # STAGE 2: Extreme Mutilation & Severed Limb (33% HP threshold)
        amp_x_start = int(w * 0.55)
        amp_y_start = int(h * 0.25)
        
        # Erase upper right limb quadrant with jagged flesh edge
        for x in range(amp_x_start, w):
            for y in range(amp_y_start, int(h * 0.75)):
                if x - amp_x_start > (y % 4):
                    injured_surf.set_at((x, y), (0, 0, 0, 0))

        # Exposed bone & severed flesh highlights along amputation stump
        for y in range(amp_y_start, int(h * 0.75)):
            stump_x = amp_x_start + (y % 4)
            if 0 <= stump_x < w and mask.get_at((stump_x, y)):
                if y % 3 == 0:
                    injured_surf.set_at((stump_x, y), (240, 235, 220, 255))  # Bone white
                else:
                    injured_surf.set_at((stump_x, y), (160, 10, 10, 255))   # Visceral crimson

        # Heavy blood splatter & dark gashes across remaining body
        for x in range(w):
            for y in range(h):
                if mask.get_at((x, y)) and injured_surf.get_at((x, y)).a > 0:
                    if (x + y * 3) % 5 == 0:
                        c = injured_surf.get_at((x, y))
                        injured_surf.set_at((x, y), (max(0, c.r - 80), max(0, c.g - 90), max(0, c.b - 90), c.a))

    elif stage == 3:
        # STAGE 3: Visceral Enrage / Crimson Aura & Bleeding Core (Boss < 20% HP)
        for x in range(w):
            for y in range(h):
                if mask.get_at((x, y)):
                    c = injured_surf.get_at((x, y))
                    r_boost = min(255, c.r + 130)
                    g_dark = max(0, c.g - 70)
                    injured_surf.set_at((x, y), (r_boost, g_dark, max(0, c.b - 40), c.a))

    _INJURY_SURFACE_CACHE[cache_key] = injured_surf
    return injured_surf


class BaseSprite(pygame.sprite.Sprite):
    """
    Base sprite class with floating point position tracking and layered sorting support.
    """
    def __init__(self, pos: Tuple[float, float], groups: Union[pygame.sprite.Group, List[pygame.sprite.Group]], layer: int = 1) -> None:
        self._layer = layer
        super().__init__(groups)
        self.pos = pygame.math.Vector2(pos)
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.copy()

    def update(self, dt: float) -> None:
        """Standard update logic."""
        pass


class YSortedGroup(pygame.sprite.Group):
    """
    A custom sprite group that sorts sprites by their vertical (Y) coordinate
    to create a pseudo-3D perspective depth effect.
    """
    def __init__(self) -> None:
        super().__init__()

    def draw_sorted(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        """
        Draws sprites sorted by their bottom Y coordinate, applying the camera scroll offset.
        Also renders conditional floating HP bars for enemies that have been struck.
        """
        sorted_sprites = sorted(
            self.sprites(),
            key=lambda spr: (getattr(spr, "layer", 1), spr.hitbox.bottom if hasattr(spr, "hitbox") else spr.rect.bottom)
        )
        
        for sprite in sorted_sprites:
            offset_pos = sprite.rect.topleft - camera_offset
            surface.blit(sprite.image, offset_pos)

            # Render Conditional Floating HP Bar for Enemies
            if hasattr(sprite, "draw_hp_bar"):
                sprite.draw_hp_bar(surface, camera_offset)
