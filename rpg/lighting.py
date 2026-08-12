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

    def update(self, dt: float, world_state: Any = None) -> None:
        """Ticks day-night timer and recalculates ambient night color opacity synchronized with world_state."""
        if world_state and hasattr(world_state, "time_accumulator"):
            self.time_of_day = world_state.time_accumulator
        else:
            self.time_of_day = (self.time_of_day + dt) % DAY_LENGTH_SECONDS
        
        # Calculate 24-hour hour float
        hour = (self.time_of_day / max(1.0, DAY_LENGTH_SECONDS)) * 24.0
        
        # 24-Hour Lighting Cycle:
        # 00:00 - 05:00: Deep Night (Dark Blue Overlay)
        # 05:00 - 07:00: Dawn / Sunrise (Smooth transition to clear daylight)
        # 07:00 - 17:30: Full Day (Clear Transparent Overlay)
        # 17:30 - 19:30: Dusk / Sunset (Warm Orange/Purple to Night transition)
        # 19:30 - 24:00: Deep Night (Dark Blue Overlay)
        
        if hour < 5.0:
            # Deep Night
            self.ambient_color = (15, 15, 45, 195)
        elif hour < 6.5:
            # Sunrise / Dawn (05:00 - 06:30)
            ratio = (hour - 5.0) / 1.5
            r = int(15 + 105 * ratio)
            g = int(15 + 35 * ratio)
            b = int(45 - 25 * ratio)
            a = int(195 * (1.0 - ratio))
            self.ambient_color = (r, g, b, a)
        elif hour < 18.0:
            # Full Day (06:30 - 18:00)
            self.ambient_color = (255, 255, 255, 0)
        elif hour < 19.5:
            # Sunset / Dusk (17:30 - 19:30)
            ratio = (hour - 17.5) / 2.0
            r = int(120 - 105 * ratio)
            g = int(50 - 35 * ratio)
            b = int(20 + 25 * ratio)
            a = int(195 * ratio)
            self.ambient_color = (r, g, b, a)
        else:
            # Deep Night
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

        # Environmental Hazard Tile Glow (lava pools emit warm light at night)
        hazard_group = getattr(game, "hazard_tiles", None)
        if hazard_group:
            for hazard in hazard_group:
                if hasattr(hazard, "hazard_type"):
                    if hazard.hazard_type == "lava_pool":
                        light_nodes.append((hazard.rect.center, 128))
                    elif hazard.hazard_type == "spike_trap":
                        light_nodes.append((hazard.rect.center, 64))

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
