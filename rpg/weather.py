"""
Echoes of Asterra - Weather System
Cycles weather states (Rain, Snow, Fog, Falling Leaves) and renders rich atmospheric visuals:
- Rain: Sky darkening storm tint, diagonal raindrops, water splash ripples on ground, storm haze
- Snow: Cold winter sky tint, soft swirling snowflakes, frost haze
- Fog: Misty translucent volumetric fog overlay
- Leaves: Warm autumn golden tint, swaying leaf particles
"""
import random
import pygame
import math
from typing import Any, Tuple, List, Optional
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT

WEATHER_CLEAR = "clear"
WEATHER_RAIN = "rain"
WEATHER_SNOW = "snow"
WEATHER_FOG = "fog"
WEATHER_LEAVES = "leaves"


class RainStreak:
    """Slanted raindrop streak particle falling rapidly."""
    def __init__(self, pos: pygame.math.Vector2, velocity: pygame.math.Vector2, length: float, alpha: int) -> None:
        self.pos = pygame.math.Vector2(pos)
        self.velocity = pygame.math.Vector2(velocity)
        self.length = length
        self.alpha = alpha
        self.lifetime = 1.2
        self.timer = 1.2

    def update(self, dt: float) -> bool:
        self.timer -= dt
        if self.timer <= 0:
            return False
        self.pos += self.velocity * dt
        return True

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        screen_pos = self.pos - camera_offset
        sx, sy = screen_pos.x, screen_pos.y
        if -50 <= sx <= SCREEN_WIDTH + 50 and -50 <= sy <= SCREEN_HEIGHT + 50:
            end_x = sx + (self.velocity.x / 650.0) * self.length
            end_y = sy + (self.velocity.y / 650.0) * self.length

            min_x = min(sx, end_x) - 2
            min_y = min(sy, end_y) - 2
            w = max(4, int(abs(end_x - sx) + 4))
            h = max(4, int(abs(end_y - sy) + 4))

            r_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.line(
                r_surf,
                (170, 215, 255, self.alpha),
                (sx - min_x, sy - min_y),
                (end_x - min_x, end_y - min_y),
                width=2
            )
            surface.blit(r_surf, (int(min_x), int(min_y)))


class RainRipple:
    """Expanding water splash ripple ring when raindrop hits ground."""
    def __init__(self, pos: pygame.math.Vector2) -> None:
        self.pos = pygame.math.Vector2(pos)
        self.lifetime = 0.35
        self.timer = 0.35
        self.max_radius = random.uniform(4.0, 9.0)

    def update(self, dt: float) -> bool:
        self.timer -= dt
        return self.timer > 0

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        screen_pos = self.pos - camera_offset
        sx, sy = screen_pos.x, screen_pos.y
        if 0 <= sx <= SCREEN_WIDTH and 0 <= sy <= SCREEN_HEIGHT:
            ratio = max(0.0, min(1.0, 1.0 - (self.timer / self.lifetime)))
            radius = max(1, int(self.max_radius * ratio))
            alpha = max(0, min(255, int(160 * (1.0 - ratio))))

            r_surf = pygame.Surface((radius * 2 + 4, radius + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(r_surf, (180, 225, 255, alpha), (2, 2, radius * 2, max(2, radius)), width=1)
            surface.blit(r_surf, (int(sx - radius - 2), int(sy - radius // 2 - 2)))


class SnowFlakeParticle:
    """Soft glowing snowflake particle with horizontal sine sway."""
    def __init__(self, pos: pygame.math.Vector2, velocity: pygame.math.Vector2, size: float) -> None:
        self.pos = pygame.math.Vector2(pos)
        self.base_vx = velocity.x
        self.velocity = pygame.math.Vector2(velocity)
        self.size = size
        self.lifetime = random.uniform(4.0, 7.0)
        self.timer = self.lifetime
        self.sway_speed = random.uniform(1.5, 3.5)
        self.sway_timer = random.uniform(0.0, 6.28)

    def update(self, dt: float) -> bool:
        self.timer -= dt
        if self.timer <= 0:
            return False
        self.sway_timer += self.sway_speed * dt
        self.velocity.x = self.base_vx + math.sin(self.sway_timer) * 30.0
        self.pos += self.velocity * dt
        return True

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        screen_pos = self.pos - camera_offset
        sx, sy = screen_pos.x, screen_pos.y
        if -20 <= sx <= SCREEN_WIDTH + 20 and -20 <= sy <= SCREEN_HEIGHT + 20:
            ratio = min(1.0, self.timer / self.lifetime)
            alpha = int(220 * ratio)
            sz = int(self.size)
            if sz < 1: sz = 1

            s_surf = pygame.Surface((sz * 2 + 6, sz * 2 + 6), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (245, 250, 255, alpha), (sz + 3, sz + 3), sz)
            pygame.draw.circle(s_surf, (180, 220, 255, int(alpha * 0.4)), (sz + 3, sz + 3), sz + 1)
            surface.blit(s_surf, (int(sx - sz - 3), int(sy - sz - 3)))


class SwayingLeaf:
    """Sways left and right using a sine wave modifier (Green, Orange, Yellow)."""
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
        self.sway_timer += self.sway_speed * dt
        self.velocity.x = self.base_vx + math.sin(self.sway_timer) * 40.0
        self.pos += self.velocity * dt
        return True

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        screen_pos = self.pos - camera_offset
        sx, sy = screen_pos.x, screen_pos.y
        if -20 <= sx <= SCREEN_WIDTH + 20 and -20 <= sy <= SCREEN_HEIGHT + 20:
            ratio = max(0.0, min(1.0, self.timer / self.lifetime))
            sz = int(self.size * ratio)
            if sz < 1: sz = 1

            cx, cy = int(sx), int(sy)
            pygame.draw.polygon(surface, self.color[:3], [
                (cx, cy - sz),
                (cx + sz, cy),
                (cx, cy + sz),
                (cx - sz, cy)
            ])


class WeatherSystem:
    """
    Manages atmospheric overlays, weather cycles, sky darkening tints,
    and particle rendering for Rain, Snow, Fog, and Leaves.
    """
    def __init__(self) -> None:
        self.state = WEATHER_CLEAR
        self.states_cycle = [WEATHER_CLEAR, WEATHER_RAIN, WEATHER_CLEAR, WEATHER_SNOW, WEATHER_CLEAR, WEATHER_LEAVES, WEATHER_FOG]
        self.cycle_index = 0

        self.timer = 45.0  # seconds per weather type
        self.intensity = 0.0  # transitions: fade-in/fade-out

        # Weather-specific active particles
        self.weather_particles: List[Any] = []
        self.sound_manager: Optional[Any] = None

        # Lightning flash state during heavy rainstorms
        self.lightning_flash_timer = 0.0
        self.fog_drift_x = 0.0

        # Pre-allocate fog overlay
        self.fog_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._build_fog_texture()

    def _build_fog_texture(self) -> None:
        """Draws soft misty circles on fog overlay to create an atmospheric fog veil."""
        self.fog_surf.fill((0, 0, 0, 0))
        for _ in range(35):
            cx = random.randint(0, SCREEN_WIDTH)
            cy = random.randint(0, SCREEN_HEIGHT)
            rad = random.randint(140, 260)
            for r in range(rad, 10, -30):
                alpha = int(5 * (1.0 - (r / rad)))
                pygame.draw.circle(self.fog_surf, (150, 165, 190, alpha), (cx, cy), r)

    def change_weather(self, next_state: str) -> None:
        """Sets weather state, clears old particles, and resets intensity transition."""
        self.state = next_state
        self.intensity = 0.0
        self.weather_particles.clear()
        self.lightning_flash_timer = 0.0

    def update(self, particles: Any, camera_offset: pygame.math.Vector2, dt: float, world_state: Any = None) -> None:
        """
        Ticks the weather cycle timer, increments transition intensity,
        spawns weather particles, and updates active weather particle physics.
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

        # Fade in intensity (5s fade in)
        if self.intensity < 1.0:
            self.intensity = min(1.0, self.intensity + dt * 0.2)

        # Update lightning flash timer
        if self.lightning_flash_timer > 0.0:
            self.lightning_flash_timer = max(0.0, self.lightning_flash_timer - dt)

        # Drift fog overlay horizontally
        if self.state == WEATHER_FOG:
            self.fog_drift_x = (self.fog_drift_x + dt * 18.0) % SCREEN_WIDTH

        # Update active weather particles
        self.weather_particles = [p for p in self.weather_particles if p.update(dt)]

        if self.state == WEATHER_CLEAR:
            return

        # Spawning bounds based on active camera offset
        left = int(camera_offset.x)
        right = int(camera_offset.x + SCREEN_WIDTH)
        top = int(camera_offset.y)
        bottom = int(camera_offset.y + SCREEN_HEIGHT)

        # 1. WEATHER_RAIN: Spawn fast angled rain streaks & splash ripples + lightning flashes & thunder audio
        if self.state == WEATHER_RAIN:
            if self.intensity > 0.4 and random.random() < 0.008:
                self.lightning_flash_timer = random.uniform(0.08, 0.16)
                if self.sound_manager and hasattr(self.sound_manager, "play_sound"):
                    self.sound_manager.play_sound("thunder")

        elif self.state in [WEATHER_SNOW, WEATHER_LEAVES]:
            if self.intensity > 0.5 and random.random() < 0.003:
                if self.sound_manager and hasattr(self.sound_manager, "play_sound"):
                    self.sound_manager.play_sound("wind_gust")

        elif self.state == WEATHER_FOG:
            if self.intensity > 0.5 and random.random() < 0.003:
                if self.sound_manager and hasattr(self.sound_manager, "play_sound"):
                    self.sound_manager.play_sound("crickets")
            spawn_count = int(140 * dt * self.intensity)
            for _ in range(max(2, spawn_count)):
                rx = random.uniform(left - 120, right + 40)
                ry = top - random.uniform(10, 80)
                speed_y = random.uniform(580, 720)
                speed_x = random.uniform(-160, -110)
                length = random.uniform(16.0, 24.0)
                alpha = random.randint(140, 210)

                self.weather_particles.append(RainStreak(
                    pos=pygame.math.Vector2(rx, ry),
                    velocity=pygame.math.Vector2(speed_x, speed_y),
                    length=length,
                    alpha=alpha
                ))

                # Occasional splash ripples near the ground plane
                if random.random() < 0.25:
                    splash_x = random.uniform(left, right)
                    splash_y = random.uniform(top + 100, bottom)
                    self.weather_particles.append(RainRipple(pygame.math.Vector2(splash_x, splash_y)))

        # 2. WEATHER_SNOW: Spawn soft floating snowflakes
        elif self.state == WEATHER_SNOW:
            spawn_count = int(35 * dt * self.intensity)
            for _ in range(max(1, spawn_count)):
                rx = random.uniform(left - 40, right + 40)
                ry = top - 10
                size = random.uniform(2.0, 4.5)
                speed_y = random.uniform(60, 110)
                speed_x = random.uniform(-30, -10)

                self.weather_particles.append(SnowFlakeParticle(
                    pos=pygame.math.Vector2(rx, ry),
                    velocity=pygame.math.Vector2(speed_x, speed_y),
                    size=size
                ))

        # 3. WEATHER_LEAVES: Spawn swaying autumn leaves
        elif self.state == WEATHER_LEAVES:
            spawn_count = int(14 * dt * self.intensity)
            for _ in range(max(1, spawn_count)):
                rx = random.uniform(left - 50, right + 50)
                ry = top - 10
                leaf_color = random.choice([
                    (70, 140, 50, 180),   # green
                    (210, 110, 30, 180),  # orange
                    (220, 180, 40, 180)   # yellow
                ])
                sway_speed = random.uniform(2.0, 4.0)
                self.weather_particles.append(SwayingLeaf(
                    pos=pygame.math.Vector2(rx, ry),
                    velocity=pygame.math.Vector2(random.uniform(-60, -30), random.uniform(80, 130)),
                    color=leaf_color,
                    size=random.uniform(3.5, 5.5),
                    lifetime=5.0,
                    sway_speed=sway_speed
                ))

    def draw_weather_overlay(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2 = None) -> None:
        """
        Renders atmospheric sky tinting overlays, rain streaks, splash ripples,
        snowflakes, leaves, and fog mist overlays across the viewport.
        """
        if self.intensity <= 0:
            return

        sw, sh = surface.get_size()
        cam = camera_offset if camera_offset is not None else pygame.math.Vector2(0, 0)

        # 1. Atmospheric Sky Tint Overlay (Darkens world during rain, tints snow/autumn)
        if self.state == WEATHER_RAIN:
            # Slate-blue storm sky darkening (Darkens sky/world so raindrops pop)
            dark_tint = pygame.Surface((sw, sh), pygame.SRCALPHA)
            alpha = int(95 * self.intensity)
            dark_tint.fill((15, 22, 40, alpha))
            surface.blit(dark_tint, (0, 0))

            # Lightning Flash Overlay
            if self.lightning_flash_timer > 0.0:
                flash_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                f_alpha = int(180 * self.intensity)
                flash_surf.fill((230, 245, 255, f_alpha))
                surface.blit(flash_surf, (0, 0))

        elif self.state == WEATHER_SNOW:
            # Cold cyan-white winter tint
            snow_tint = pygame.Surface((sw, sh), pygame.SRCALPHA)
            alpha = int(45 * self.intensity)
            snow_tint.fill((170, 210, 245, alpha))
            surface.blit(snow_tint, (0, 0))
        elif self.state == WEATHER_LEAVES:
            # Warm golden autumn tint
            leaf_tint = pygame.Surface((sw, sh), pygame.SRCALPHA)
            alpha = int(25 * self.intensity)
            leaf_tint.fill((230, 140, 40, alpha))
            surface.blit(leaf_tint, (0, 0))

        # 2. Render weather particles (Rain Streaks, Ripples, Snowflakes, Leaves)
        for p in self.weather_particles:
            p.draw(surface, cam)

        # 3. Render Drifting Volumetric Fog Overlay
        if self.state == WEATHER_FOG and self.intensity > 0:
            temp_overlay = self.fog_surf.copy()
            temp_overlay.fill((255, 255, 255, int(185 * self.intensity)), special_flags=pygame.BLEND_RGBA_MULT)
            dx = int(self.fog_drift_x)
            surface.blit(temp_overlay, (dx - sw, 0))
            surface.blit(temp_overlay, (dx, 0))

    def draw_fog_overlay(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2 = None) -> None:
        """Alias for draw_weather_overlay for backwards compatibility."""
        self.draw_weather_overlay(surface, camera_offset)

    def get_combat_modifiers(self) -> dict:
        """Returns combat modifiers based on current weather state."""
        if self.state == WEATHER_RAIN:
            return {
                "fire_mult": 0.75,         # Rain weakens fire -25%
                "ice_mult": 1.0,
                "lightning_mult": 1.30,     # Rain conducts lightning +30%
                "speed_mult": 1.0,
                "vision_mult": 1.0,
                "ice_duration_bonus": 1.0,  # +1s ice duration in rain
            }
        elif self.state == WEATHER_SNOW:
            return {
                "fire_mult": 0.65,         # Snow suppresses fire -35%
                "ice_mult": 1.20,          # Snow enhances ice +20%
                "lightning_mult": 1.0,
                "speed_mult": 0.85,        # Snow slows all movement -15%
                "vision_mult": 1.0,
                "ice_duration_bonus": 0.5,
            }
        elif self.state == WEATHER_FOG:
            return {
                "fire_mult": 1.0,
                "ice_mult": 1.0,
                "lightning_mult": 1.0,
                "speed_mult": 1.0,
                "vision_mult": 0.60,       # Fog reduces enemy vision -40%
                "ice_duration_bonus": 0.0,
            }
        else:
            return {
                "fire_mult": 1.0,
                "ice_mult": 1.0,
                "lightning_mult": 1.0,
                "speed_mult": 1.0,
                "vision_mult": 1.0,
                "ice_duration_bonus": 0.0,
            }

    def get_weather_info(self) -> dict:
        """Returns display metadata, accent colors, and detailed effect bullet points for UI hover tooltips."""
        if self.state == WEATHER_RAIN:
            return {
                "name": "Heavy Downpour",
                "label": "RAIN",
                "icon": "🌧",
                "color": (80, 160, 240),
                "effects": [
                    "⚡ Lightning Damage: +30%",
                    "🔥 Fire Damage: -25%",
                    "🧊 Ice Freeze Duration: +1.0s",
                    "🌧 Wetness active on all targets"
                ]
            }
        elif self.state == WEATHER_SNOW:
            return {
                "name": "Blizzard / Snowfall",
                "label": "SNOW",
                "icon": "❄",
                "color": (160, 220, 255),
                "effects": [
                    "🧊 Ice Damage: +20%",
                    "🔥 Fire Damage: -35%",
                    "👟 Movement Speed: -15%",
                    "❄ Frostbite buildup active"
                ]
            }
        elif self.state == WEATHER_FOG:
            return {
                "name": "Dense Fog",
                "label": "FOG",
                "icon": "🌫",
                "color": (200, 210, 220),
                "effects": [
                    "🌫 Enemy Vision Radius: -40%",
                    "🗡 Stealth & Ambush bonus active",
                    "👁 Reduced map visibility"
                ]
            }
        elif self.state == WEATHER_LEAVES:
            return {
                "name": "Autumn Breeze",
                "label": "LEAVES",
                "icon": "🍂",
                "color": (230, 140, 50),
                "effects": [
                    "🍂 Gentle wind sway",
                    "🍃 Baseline combat balance"
                ]
            }
        else:
            return {
                "name": "Clear Weather",
                "label": "CLEAR",
                "icon": "☀️",
                "color": (255, 220, 100),
                "effects": [
                    "☀️ Sunlit baseline environment",
                    "⚡ Normal elemental efficiency"
                ]
            }
