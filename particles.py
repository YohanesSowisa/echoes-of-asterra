"""
Echoes of Asterra - Particles System
Highly optimized particle manager for footprints, damage blood, magic spells, level-ups, weather,
and aerodynamic wind dash trail afterimages.
"""
import random
import math
import pygame
from typing import List, Tuple, Optional
from rpg.settings import MAX_PARTICLES

class Particle:
    """
    A single visual particle. Fades out over time.
    """
    __slots__ = ['pos', 'velocity', 'color', 'size', 'lifetime', 'timer', 'gravity', 'drag']
    
    def __init__(
        self,
        pos: pygame.math.Vector2,
        velocity: pygame.math.Vector2,
        color: Tuple[int, int, int],
        size: float,
        lifetime: float,
        gravity: float = 0.0,
        drag: float = 0.98
    ) -> None:
        self.pos = pygame.math.Vector2(pos)
        self.velocity = pygame.math.Vector2(velocity)
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.timer = lifetime
        self.gravity = gravity
        self.drag = drag

    def update(self, dt: float) -> bool:
        """Ticks lifetime, applies gravity/drag. Returns False when expired."""
        self.timer -= dt
        if self.timer <= 0:
            return False
            
        # Physics movement
        self.velocity.y += self.gravity * dt
        self.velocity *= (self.drag ** (dt * 60.0))  # framerate independent drag
        self.pos += self.velocity * dt
        return True

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        """Renders the particle onto the screen surface."""
        screen_pos = self.pos - camera_offset
        ratio = max(0.0, min(1.0, self.timer / self.lifetime))
        sz = int(self.size * ratio)
        if sz < 1:
            sz = 1
            
        r, g, b = int(self.color[0]), int(self.color[1]), int(self.color[2])
        base_alpha = int(self.color[3]) if len(self.color) > 3 else 255
        alpha = max(0, min(255, int(ratio * base_alpha)))

        p_surf = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
        pygame.draw.circle(p_surf, (r, g, b, alpha), (sz, sz), sz)
        surface.blit(p_surf, (int(screen_pos.x) - sz, int(screen_pos.y) - sz))



class GhostParticle:
    """Renders a fading cyan motion ghost afterimage of a sprite during dash."""
    def __init__(self, surface: pygame.Surface, pos: Tuple[float, float], lifetime: float = 0.25) -> None:
        self.image = surface.copy()
        # Cyan/white wind tint overlay
        tint = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        tint.fill((180, 235, 255, 140))
        self.image.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.pos = pygame.math.Vector2(pos)
        self.lifetime = lifetime
        self.timer = lifetime

    def update(self, dt: float) -> bool:
        self.timer -= dt
        return self.timer > 0

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        ratio = max(0.0, self.timer / self.lifetime)
        self.image.set_alpha(int(ratio * 180))
        screen_pos = self.pos - camera_offset
        surface.blit(self.image, screen_pos)


class ParticleManager:
    """
    Manages active particle effects pool and ghost motion afterimages.
    """
    def __init__(self) -> None:

        self.particles: List[Particle] = []
        self.ghost_particles: List[GhostParticle] = []

    def clear(self) -> None:
        """Flushes all active particles."""
        self.particles.clear()
        self.ghost_particles.clear()

    def add_particle(self, particle: Particle) -> None:
        """Appends a particle to the update list if limit is not exceeded."""
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(particle)

    def create_ghost_afterimage(self, pos: Tuple[float, float], sprite_surface: pygame.Surface) -> None:
        """Spawns a fading cyan motion ghost afterimage at the dash position."""
        if len(self.ghost_particles) < 20:
            self.ghost_particles.append(GhostParticle(sprite_surface, pos, lifetime=0.25))

    def update(self, dt: float) -> None:
        """Updates physics ticks and purges expired particles and ghosts."""
        self.particles = [p for p in self.particles if p.update(dt)]
        self.ghost_particles = [g for g in self.ghost_particles if g.update(dt)]

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        """Draws all active motion ghosts and particles."""
        for g in self.ghost_particles:
            g.draw(surface, camera_offset)
        for p in self.particles:
            p.draw(surface, camera_offset)

    # --- PARTICLE FACTORY METHODS ---

    def create_dust_puff(self, pos: Tuple[float, float]) -> None:
        """Spawn small gray dust particles rising upwards (footsteps)."""
        for _ in range(3):
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos[0], pos[1] - 2),
                velocity=pygame.math.Vector2(random.uniform(-10, 10), random.uniform(-20, -5)),
                color=(170, 175, 180),
                size=random.uniform(2, 4),
                lifetime=random.uniform(0.3, 0.5),
                drag=0.9
            ))

    def create_hit_blood(self, pos: Tuple[float, float], hit_direction: Optional[pygame.math.Vector2]) -> None:
        """Spurs dark red droplet particles splashing out from target."""
        for _ in range(8):
            if hit_direction and hit_direction.length_squared() > 0:
                vel = hit_direction.normalize() * random.uniform(60, 180)
                vel = vel.rotate(random.uniform(-30, 30))
            else:
                vel = pygame.math.Vector2(random.uniform(-150, 150), random.uniform(-150, 150))
                
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos),
                velocity=vel,
                color=(180, 20, 20),
                size=random.uniform(3, 5),
                lifetime=random.uniform(0.4, 0.7),
                gravity=150.0,
                drag=0.96
            ))

    def create_block_sparks(self, pos: Tuple[float, float]) -> None:
        """Generates sparks when shield blocks an attack or hit deflects."""
        for _ in range(12):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(100, 220)
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos),
                velocity=pygame.math.Vector2(math.cos(angle) * speed, math.sin(angle) * speed),
                color=random.choice([(255, 230, 80), (255, 180, 40), (255, 255, 200)]),
                size=random.uniform(2, 4),
                lifetime=random.uniform(0.2, 0.4),
                drag=0.92
            ))

    def create_heal_sparkles(self, pos: Tuple[float, float]) -> None:
        """Spawns rising green and cyan sparkles on health recovery."""
        for _ in range(16):
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos[0] + random.uniform(-16, 16), pos[1] + random.uniform(0, 16)),
                velocity=pygame.math.Vector2(random.uniform(-15, 15), random.uniform(-60, -30)),
                color=random.choice([(80, 240, 120), (60, 210, 240)]),
                size=random.uniform(2, 5),
                lifetime=random.uniform(0.6, 0.9),
                drag=0.97
            ))

    def create_levelup_splash(self, pos: Tuple[float, float]) -> None:
        """Triumphant radial ring of stars/fireworks when level rises."""
        for i in range(40):
            angle = (i / 40.0) * 6.28
            speed = random.uniform(150, 300)
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos),
                velocity=pygame.math.Vector2(math.cos(angle) * speed, math.sin(angle) * speed),
                color=random.choice([(220, 60, 220), (250, 200, 30), (60, 230, 240)]),
                size=random.uniform(3, 6),
                lifetime=random.uniform(0.8, 1.3),
                drag=0.96
            ))

    def create_kill_splash(self, pos: Tuple[float, float]) -> None:
        """Explosive radial splash of dark/red and smoke particles on enemy death."""
        for i in range(25):
            angle = (i / 25.0) * 6.28 + random.uniform(-0.2, 0.2)
            speed = random.uniform(80, 160)
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos),
                velocity=pygame.math.Vector2(math.cos(angle) * speed, math.sin(angle) * speed),
                color=random.choice([(150, 20, 20), (50, 50, 50), (100, 100, 100)]),
                size=random.uniform(3, 5),
                lifetime=random.uniform(0.4, 0.7),
                drag=0.94
            ))

    def create_dash_trail(self, pos: Tuple[float, float], direction: str, sprite_surface: Optional[pygame.Surface] = None) -> None:
        """Spawns aerodynamic wind shockwaves, breeze streaks, and motion ghost afterimages upon dashing."""
        opposite_vec = pygame.math.Vector2(0, 0)
        if direction == "left": opposite_vec.x = 1
        elif direction == "right": opposite_vec.x = -1
        elif direction == "up": opposite_vec.y = 1
        elif direction == "down": opposite_vec.y = -1

        # 1. Aerodynamic Wind Streak Particles
        for _ in range(14):
            vel = (opposite_vec + pygame.math.Vector2(random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4))).normalize() * random.uniform(140, 280)
            color = random.choice([(230, 245, 255), (180, 230, 255), (140, 210, 255)])
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos[0] + random.uniform(-6, 6), pos[1] + random.uniform(-6, 6)),
                velocity=vel,
                color=color,
                size=random.uniform(3, 6),
                lifetime=random.uniform(0.25, 0.45),
                drag=0.92
            ))

        # 2. Motion Ghost Afterimage
        if sprite_surface is not None:
            self.create_ghost_afterimage(pos, sprite_surface)

    def create_wind_stream(self, pos: Tuple[float, float], direction: str) -> None:
        """Spawns continuous aerodynamic wind stream particles during dash movement."""
        opposite_vec = pygame.math.Vector2(0, 0)
        if direction == "left": opposite_vec.x = 1
        elif direction == "right": opposite_vec.x = -1
        elif direction == "up": opposite_vec.y = 1
        elif direction == "down": opposite_vec.y = -1

        for _ in range(4):
            vel = (opposite_vec + pygame.math.Vector2(random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2))).normalize() * random.uniform(100, 220)
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos[0] + random.uniform(-4, 4), pos[1] + random.uniform(-4, 4)),
                velocity=vel,
                color=random.choice([(240, 250, 255), (190, 235, 255)]),
                size=random.uniform(2, 4),
                lifetime=random.uniform(0.15, 0.3),
                drag=0.9
            ))

    def create_blood_spurt(self, pos: Tuple[float, float]) -> None:
        """Spawns dripping visceral blood droplets and flesh embers for wounded/mutilated enemies."""
        for _ in range(4):
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos[0] + random.uniform(-8, 8), pos[1] + random.uniform(-4, 4)),
                velocity=pygame.math.Vector2(random.uniform(-25, 25), random.uniform(-10, 40)),
                color=random.choice([(140, 10, 10), (180, 20, 20), (90, 5, 5)]),
                size=random.uniform(2, 4),
                lifetime=random.uniform(0.3, 0.6),
                gravity=120.0,
                drag=0.95
            ))


# Class Alias for backward compatibility
ParticleSystem = ParticleManager
