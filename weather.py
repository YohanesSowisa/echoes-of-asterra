"""
Echoes of Asterra - Weather System
Cycles weather states (Rain, Snow, Fog, Falling Leaves) and spawns environment particle overlays.
"""
import random
import pygame
import math
from typing import Any, Tuple
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT

WEATHER_CLEAR = "clear"
WEATHER_RAIN = "rain"
WEATHER_SNOW = "snow"
WEATHER_FOG = "fog"
WEATHER_LEAVES = "leaves"

class WeatherSystem:
    """
    Manages atmospheric overlays. Generates weather particles in camera screen-space.
    """
    def __init__(self) -> None:
        self.state = WEATHER_CLEAR
        self.states_cycle = [WEATHER_CLEAR, WEATHER_RAIN, WEATHER_CLEAR, WEATHER_SNOW, WEATHER_CLEAR, WEATHER_LEAVES, WEATHER_FOG]
        self.cycle_index = 0
        
        self.timer = 45.0  # seconds per weather type
        self.intensity = 0.0  # transitions: fade-in/fade-out
        
        # Pre-allocate fog overlay
        self.fog_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._build_fog_texture()

    def _build_fog_texture(self) -> None:
        """Draws soft misty circles on fog overlay to create an atmospheric fog veil."""
        self.fog_surf.fill((0, 0, 0, 0))
        # Draw soft translucent gray blobs
        for _ in range(30):
            cx = random.randint(0, SCREEN_WIDTH)
            cy = random.randint(0, SCREEN_HEIGHT)
            rad = random.randint(120, 240)
            
            # Simple soft falloff by drawing concentric circles
            for r in range(rad, 10, -30):
                alpha = int(4 * (1.0 - (r / rad)))
                pygame.draw.circle(self.fog_surf, (150, 160, 185, alpha), (cx, cy), r)

    def change_weather(self, next_state: str) -> None:
        """Sets weather state and resets intensity transition."""
        self.state = next_state
        self.intensity = 0.0

    def update(self, particles: Any, camera_offset: pygame.math.Vector2, dt: float, world_state: Any = None) -> None:
        """
        Ticks the weather cycle timer, increments transition intensity,
        and spawns weather particles above the screen viewport.
        """
        # Cycle weather states
        self.timer -= dt
        if self.timer <= 0:
            self.timer = 45.0
            if world_state and hasattr(world_state, "get_weather_bias"):
                bias = world_state.get_weather_bias()
                states = list(bias.keys())
                weights = list(bias.values())
                next_st = random.choices(states, weights=weights, k=1)[0]
                self.change_weather(next_st)
            else:
                self.cycle_index = (self.cycle_index + 1) % len(self.states_cycle)
                self.change_weather(self.states_cycle[self.cycle_index])

        # Fade in intensity
        if self.intensity < 1.0:
            self.intensity = min(1.0, self.intensity + dt * 0.2)  # 5s fade in

        if self.state == WEATHER_CLEAR:
            return

        # Spawning bounds based on active camera offset
        left = int(camera_offset.x)
        right = int(camera_offset.x + SCREEN_WIDTH)
        top = int(camera_offset.y)

        # Spawning rates scaled by intensity and frame ticks
        if self.state == WEATHER_RAIN:
            # Spawn rain droplets (thin diagonals)
            spawn_count = int(120 * dt * self.intensity)
            for _ in range(max(1, spawn_count)):
                rx = random.uniform(left - 100, right)
                ry = top - 10
                
                # Setup rain particle
                from rpg.particles import Particle
                particles.add_particle(Particle(
                    pos=pygame.math.Vector2(rx, ry),
                    velocity=pygame.math.Vector2(random.uniform(-180, -120), random.uniform(500, 600)),
                    color=(80, 120, 180, 140), # translucent blue-gray
                    size=random.uniform(1.5, 2.5),
                    lifetime=1.5,
                    gravity=0.0,
                    drag=1.0
                ))
                
        elif self.state == WEATHER_SNOW:
            # Spawn floating snowflakes
            spawn_count = int(35 * dt * self.intensity)
            for _ in range(max(1, spawn_count)):
                rx = random.uniform(left, right)
                ry = top - 10
                
                from rpg.particles import Particle
                particles.add_particle(Particle(
                    pos=pygame.math.Vector2(rx, ry),
                    velocity=pygame.math.Vector2(random.uniform(-40, -10), random.uniform(60, 100)),
                    color=(245, 245, 255, 180), # soft white
                    size=random.uniform(2.0, 4.0),
                    lifetime=6.0,
                    gravity=0.0,
                    drag=0.99
                ))

        elif self.state == WEATHER_LEAVES:
            # Spawn falling forest leaves
            spawn_count = int(12 * dt * self.intensity)
            for _ in range(max(1, spawn_count)):
                rx = random.uniform(left - 50, right)
                ry = top - 10
                
                from rpg.particles import Particle
                # Green/Orange/Yellow leaves
                leaf_color = random.choice([
                    (70, 140, 50, 180),   # green
                    (210, 110, 30, 180),  # orange
                    (220, 180, 40, 180)   # yellow
                ])
                
                # High wind sway path
                sway_speed = random.uniform(2.0, 4.0)
                particles.add_particle(SwayingLeaf(
                    pos=pygame.math.Vector2(rx, ry),
                    velocity=pygame.math.Vector2(random.uniform(-60, -30), random.uniform(80, 130)),
                    color=leaf_color,
                    size=random.uniform(3.0, 5.0),
                    lifetime=5.0,
                    sway_speed=sway_speed
                ))

    def draw_fog_overlay(self, surface: pygame.Surface) -> None:
        """Blits the pre-rendered translucent fog surface over the viewport."""
        if self.state == WEATHER_FOG and self.intensity > 0:
            # Create a copies with scaled opacity
            temp_overlay = self.fog_surf.copy()
            temp_overlay.fill((255, 255, 255, int(180 * self.intensity)), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(temp_overlay, (0, 0))

class SwayingLeaf:
    """
    Sways left and right using a sine wave modifier.
    We mock basic properties to plug into ParticleSystem.
    """
    def __init__(self, pos: pygame.math.Vector2, velocity: pygame.math.Vector2, color: Tuple[int, int, int, int], size: float, lifetime: float, sway_speed: float) -> None:
        self.pos = pygame.math.Vector2(pos)
        self.base_vx = velocity.x
        self.velocity = pygame.math.Vector2(velocity)
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.timer = lifetime
        self.sway_speed = sway_speed
        self.sway_timer = random.uniform(0.0, 6.28)

    def update(self, dt: float) -> bool:
        self.timer -= dt
        if self.timer <= 0:
            return False
            
        # Apply horizontal sine sway
        self.sway_timer += self.sway_speed * dt
        self.velocity.x = self.base_vx + math.sin(self.sway_timer) * 40.0
        self.pos += self.velocity * dt
        return True

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        screen_pos = self.pos - camera_offset
        ratio = max(0.0, min(1.0, self.timer / self.lifetime))
        sz = int(self.size * ratio)
        if sz < 1: sz = 1
        
        # Draw tiny leaf shape (a diamond)
        cx, cy = int(screen_pos.x), int(screen_pos.y)
        pygame.draw.polygon(surface, self.color[:3], [
            (cx, cy - sz),
            (cx + sz, cy),
            (cx, cy + sz),
            (cx - sz, cy)
        ])
