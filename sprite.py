"""
Echoes of Asterra - Sprite Classes
Defines the base sprite classes and a Y-sorted camera rendering group.
"""
import pygame
from typing import List, Tuple, Union

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
        """
        # Sort active sprites: first by layer, then by bottom Y position of their hitbox/rect
        sorted_sprites = sorted(
            self.sprites(),
            key=lambda spr: (getattr(spr, "layer", 1), spr.hitbox.bottom if hasattr(spr, "hitbox") else spr.rect.bottom)
        )
        
        for sprite in sorted_sprites:
            offset_pos = sprite.rect.topleft - camera_offset
            surface.blit(sprite.image, offset_pos)
