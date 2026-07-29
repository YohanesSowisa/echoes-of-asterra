"""
Echoes of Asterra - Camera System
Handles smooth scrolling camera following the player, clamped inside the current map boundaries.
"""
import pygame
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT

class Camera:
    """
    Main camera manager. Tracks a target entity and updates screen scroll offset.
    Supports camera shake.
    """
    def __init__(self, map_width: int, map_height: int) -> None:
        self.offset = pygame.math.Vector2(0, 0)
        self.map_width = map_width
        self.map_height = map_height
        
        # Screen midpoint offset
        self.half_width = SCREEN_WIDTH // 2
        self.half_height = SCREEN_HEIGHT // 2
        
        # Camera shake parameters
        self.shake_intensity = 0.0
        self.shake_duration = 0.0
        self.shake_timer = 0.0
        self.shake_offset = pygame.math.Vector2(0, 0)

    def set_map_size(self, width: int, height: int) -> None:
        """Updates camera clamping boundaries when transitioning maps."""
        self.map_width = width
        self.map_height = height

    def trigger_shake(self, intensity: float, duration_ms: float) -> None:
        """Triggers a screen-shake visual effect."""
        self.shake_intensity = intensity
        self.shake_duration = duration_ms / 1000.0
        self.shake_timer = self.shake_duration

    def update(self, target_pos: pygame.math.Vector2, dt: float) -> None:
        """
        Updates camera center, smoothly interpolating to follow target_pos,
        clamping to map bounds, and applying screen shake.
        """
        # Smooth interpolation (lerp) towards player center
        target_x = target_pos.x - self.half_width
        target_y = target_pos.y - self.half_height
        
        # Apply smooth movement
        self.offset.x += (target_x - self.offset.x) * 10 * dt
        self.offset.y += (target_y - self.offset.y) * 10 * dt
        
        # Clamp camera to map boundaries
        self.offset.x = max(0.0, min(self.offset.x, self.map_width - SCREEN_WIDTH))
        self.offset.y = max(0.0, min(self.offset.y, self.map_height - SCREEN_HEIGHT))
        
        # Calculate screen shake
        if self.shake_timer > 0:
            self.shake_timer -= dt
            import random
            # Shake offset changes rapidly
            self.shake_offset.x = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_offset.y = random.uniform(-self.shake_intensity, self.shake_intensity)
        else:
            self.shake_offset.x = 0
            self.shake_offset.y = 0

    def get_offset(self) -> pygame.math.Vector2:
        """Returns the current camera scroll offset with shake applied."""
        return self.offset + self.shake_offset
