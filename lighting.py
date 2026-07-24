"""
Echoes of Asterra - Day-Night Cycle & Lighting System
Simulates time progression and renders a light mask to carve out radial glows around light sources at night.
"""
import pygame
from typing import List, Tuple, Any
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT, DAY_LENGTH_SECONDS

class LightingSystem:
    """
    Tracks time of day and builds a full-screen overlay mask
    representing ambient shadow and glow sources.
    """
    def __init__(self) -> None:
        self.time_of_day = 0.0
        self.ambient_color = (255, 255, 255, 0)
        
        # Pre-render light radial cutout gradients
        self.glows: dict[int, pygame.Surface] = {}
        self._precompute_radial_glows()
        
        # Screen light mask buffer
        self.mask_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    def _precompute_radial_glows(self) -> None:
        """Pre-renders circular light cutouts of varying radius sizes."""
        sizes = [64, 128, 256, 384]
        for sz in sizes:
            surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
            surf.fill((255, 255, 255, 255)) # Default fully bright edges (so BLEND_RGBA_MIN retains ambient color)
            
            # Draw concentric soft transparent circles
            cx, cy = sz // 2, sz // 2
            for r in range(cx, 0, -2):
                ratio = r / cx
                # Inner circle is fully transparent (carves out light), outer is solid white
                alpha = int(255 * (ratio ** 1.8))
                pygame.draw.circle(surf, (255, 255, 255, alpha), (cx, cy), r)
                
            self.glows[sz] = surf

    def update(self, dt: float) -> None:
        """Ticks day-night timer and recalculates ambient night color opacity."""
        self.time_of_day = (self.time_of_day + dt) % DAY_LENGTH_SECONDS
        
        # Calculate ambient color cycles
        # Progress ranges 0.0 to 1.0
        prog = self.time_of_day / DAY_LENGTH_SECONDS
        
        # Cycle states:
        # 0.00 - 0.25 (Morning sunrise: dark blue to bright)
        # 0.25 - 0.60 (Midday: clear sunlight)
        # 0.60 - 0.75 (Sunset: bright to orange to dark purple)
        # 0.75 - 1.00 (Night: deep dark blue)
        
        if prog < 0.20:
            # Sunrise: fade out dark overlay
            ratio = 1.0 - (prog / 0.20)
            self.ambient_color = (15, 15, 45, int(195 * ratio))
        elif prog < 0.60:
            # Day: transparent, full light
            self.ambient_color = (255, 255, 255, 0)
        elif prog < 0.75:
            # Sunset: fade in orange overlay
            ratio = (prog - 0.60) / 0.15
            # Shift from transparent to orange/purple sunset
            self.ambient_color = (120, 50, 20, int(130 * ratio))
        elif prog < 0.85:
            # Sunset transition to night
            ratio = (prog - 0.75) / 0.10
            # Blend sunset orange into night dark blue
            r = int(120 - 105 * ratio)
            g = int(50 - 35 * ratio)
            b = int(20 + 25 * ratio)
            a = int(130 + 65 * ratio)
            self.ambient_color = (r, g, b, a)
        else:
            # Night: deep dark blue
            self.ambient_color = (15, 15, 45, 195)

    def draw_lighting(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2, game: Any) -> None:
        """
        Builds the light mask, inserts circular glows at player / projectiles,
        and overlays it onto the game screen.
        """
        # If fully daytime, skip rendering light mask overlay to save performance
        if self.ambient_color[3] == 0:
            return
            
        # 1. Fill mask with ambient darkness color
        self.mask_surf.fill(self.ambient_color)
        
        # 2. Compile light source nodes to carve out
        light_nodes: List[Tuple[Tuple[float, float], int]] = []
        
        # Player light (medium size 256)
        p_screen = game.player.rect.center
        light_nodes.append((p_screen, 256))
        
        # Spells projectiles lights (small size 128)
        for proj in game.projectiles:
            if proj.proj_type == "fireball":
                light_nodes.append((proj.rect.center, 128))
            elif proj.proj_type == "ice_spike":
                light_nodes.append((proj.rect.center, 64))
                
        # Final Boss fiery eyes glow (large size 384)
        for enemy in game.enemies:
            if enemy.name == "Shadow Overlord" and enemy.hp > 0 and enemy.ai.state != "patrol":
                light_nodes.append((enemy.rect.center, 384))

        # 3. Carve light circles out of mask using blending multiplier
        for pos, radius in light_nodes:
            # Retrieve cached glow circle texture
            glow = self.glows.get(radius)
            if glow:
                # Center glow on target position (relative to screen space!)
                sx = int(pos[0] - camera_offset.x - radius // 2)
                sy = int(pos[1] - camera_offset.y - radius // 2)
                
                # BLEND_RGBA_MIN keeps the lowest alpha, carving out circles
                self.mask_surf.blit(glow, (sx, sy), special_flags=pygame.BLEND_RGBA_MIN)

        # 4. Blit mask over screen
        surface.blit(self.mask_surf, (0, 0))
