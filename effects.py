"""
Echoes of Asterra - Visual Effects Manager
Coordinates screen damage flashes, hit-stops, and outline overlays.
"""
import pygame
from typing import Tuple

class EffectsManager:
    """
    Tracks visual combat feedback.
    """
    def __init__(self) -> None:
        # Hit stop (frame freezes)
        self.hit_stop_timer = 0.0
        
        # Screen flash overlays
        self.flash_color = (255, 255, 255)
        self.flash_duration = 0.0
        self.flash_timer = 0.0
        
        # Flash overlay screen buffer
        self.flash_surf = pygame.Surface((1, 1))

    def trigger_flash(self, color: Tuple[int, int, int], duration_ms: float) -> None:
        """Starts a full-screen translucent color flash."""
        self.flash_color = color
        self.flash_duration = duration_ms / 1000.0
        self.flash_timer = self.flash_duration

    def trigger_hit_stop(self, duration_ms: float) -> None:
        """Freezes frame updates briefly to convey hit weight and impact."""
        self.hit_stop_timer = duration_ms / 1000.0

    def update(self, dt: float) -> None:
        """Ticks down flash and hit stop timers."""
        if self.hit_stop_timer > 0:
            self.hit_stop_timer = max(0.0, self.hit_stop_timer - dt)
            
        if self.flash_timer > 0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

    def draw_flash(self, surface: pygame.Surface) -> None:
        """Draws the screen flash overlay on top of rendering."""
        if self.flash_timer <= 0:
            return
            
        # Calculate alpha decay
        ratio = self.flash_timer / self.flash_duration
        alpha = int(120 * ratio)  # cap at 120 opacity for visibility
        
        # Resize flash surface to match main viewport if necessary
        if self.flash_surf.get_size() != surface.get_size():
            self.flash_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            
        # Fill overlay with faded flash color
        self.flash_surf.fill((self.flash_color[0], self.flash_color[1], self.flash_color[2], alpha))
        surface.blit(self.flash_surf, (0, 0))

    def draw_low_hp_vignette(self, surface: pygame.Surface, hp_ratio: float) -> None:
        """Draws pulsing red screen edge vignette when player HP drops below 25%."""
        if hp_ratio >= 0.25 or hp_ratio <= 0.0:
            return
            
        import math
        ticks = pygame.time.get_ticks() / 300.0
        pulse = (math.sin(ticks) + 1.0) * 0.5  # 0.0 to 1.0
        alpha = int(60 + pulse * 90) # 60 to 150 opacity
        
        sw, sh = surface.get_size()
        vignette = pygame.Surface((sw, sh), pygame.SRCALPHA)
        
        # Red border vignette rings
        border_thick = int(40 + pulse * 20)
        pygame.draw.rect(vignette, (230, 20, 20, alpha), (0, 0, sw, sh), width=border_thick)
        pygame.draw.rect(vignette, (255, 60, 60, int(alpha * 0.5)), (border_thick, border_thick, sw - border_thick * 2, sh - border_thick * 2), width=15)
        
        surface.blit(vignette, (0, 0))

    @staticmethod
    def draw_glowing_outline(surface: pygame.Surface, target_surf: pygame.Surface, pos: Tuple[int, int], color: Tuple[int, int, int]) -> None:
        """
        Draws a glowing 1px outline of 'color' around target_surf at screen coordinate 'pos'.
        Used to highlight interactive nodes.
        """
        mask = pygame.mask.from_surface(target_surf)
        outline_surf = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
        
        # Blit shifted copies around pos to build outline
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            surface.blit(outline_surf, (pos[0] + dx, pos[1] + dy))
            
        # Draw actual sprite image on top
        surface.blit(target_surf, pos)
