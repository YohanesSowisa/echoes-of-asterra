"""
Echoes of Asterra - Particles System
Highly optimized particle manager for footprints, damage blood, magic spells, level-ups, and weather.
"""
import random
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
        # Calculate screen position
        screen_pos = self.pos - camera_offset
        
        # Calculate fade out ratio
        ratio = max(0.0, min(1.0, self.timer / self.lifetime))
        alpha = int(ratio * 255)
        
        # Draw size
        sz = int(self.size * ratio)
        if sz < 1:
            sz = 1
            
        # Draw translucent circle / rectangle
        if len(self.color) == 4:
            c = (self.color[0], self.color[1], self.color[2], int(self.color[3] * ratio))
        else:
            c = (self.color[0], self.color[1], self.color[2], alpha)
            
        # For performance, draw small particles as rects or circles
        if sz <= 2:
            pygame.draw.rect(surface, c[:3], (int(screen_pos.x), int(screen_pos.y), sz, sz))
        else:
            # Drawing transparent circles requires custom surfaces, so we stick to quick solid circles
            # which look great in pixel art!
            pygame.draw.circle(surface, c[:3], (int(screen_pos.x), int(screen_pos.y)), sz)

class ParticleSystem:
    """
    Central pool coordinates updating and drawing particles.
    """
    def __init__(self) -> None:
        self.particles: List[Particle] = []

    def clear(self) -> None:
        """Flushes all active particles."""
        self.particles.clear()

    def add_particle(self, particle: Particle) -> None:
        """Appends a particle to the update list if limit is not exceeded."""
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(particle)

    def update(self, dt: float) -> None:
        """Updates physics ticks and purges expired particles."""
        # Rebuild list retaining only active particles
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        """Draws all active particles."""
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
            # Calculate splash direction
            if hit_direction and hit_direction.length_squared() > 0:
                # Spray in direction of impact with variance
                vel = hit_direction.normalize() * random.uniform(60, 180)
                vel = vel.rotate(random.uniform(-30, 30))
            else:
                # Radial spray
                vel = pygame.math.Vector2(random.uniform(-150, 150), random.uniform(-150, 150))
                
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos),
                velocity=vel,
                color=(180, 20, 20),
                size=random.uniform(3, 5),
                lifetime=random.uniform(0.4, 0.7),
                gravity=150.0,  # pull down
                drag=0.96
            ))

    def create_block_sparks(self, pos: Tuple[float, float]) -> None:
        """Generates sparks when shield blocks an attack or hit deflects."""
        for _ in range(12):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(80, 220)
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos),
                velocity=pygame.math.Vector2(math_cos(angle) * speed, math_sin(angle) * speed),
                color=(240, 200, 40), # Golden sparkles
                size=random.uniform(2, 4),
                lifetime=random.uniform(0.2, 0.4),
                drag=0.95
            ))

    def create_heal_sparkles(self, pos: Tuple[float, float]) -> None:
        """Spawns rising green and cyan sparkles on health recovery."""
        for _ in range(16):
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos[0] + random.uniform(-16, 16), pos[1] + random.uniform(0, 16)),
                velocity=pygame.math.Vector2(random.uniform(-15, 15), random.uniform(-60, -30)),
                color=random.choice([(80, 240, 120), (60, 210, 240)]), # light green / cyan
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
                velocity=pygame.math.Vector2(math_cos(angle) * speed, math_sin(angle) * speed),
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
                velocity=pygame.math.Vector2(math_cos(angle) * speed, math_sin(angle) * speed),
                color=random.choice([(150, 20, 20), (50, 50, 50), (100, 100, 100)]), # blood red and dark smoke
                size=random.uniform(3, 5),
                lifetime=random.uniform(0.4, 0.7),
                drag=0.94
            ))

    def create_dash_trail(self, pos: Tuple[float, float], direction: str) -> None:
        """Wind smoke puff trail when sprinting/dashing."""
        # Calculate opposite direction vectors
        opposite_vec = pygame.math.Vector2(0, 0)
        if direction == "left": opposite_vec.x = 1
        elif direction == "right": opposite_vec.x = -1
        elif direction == "up": opposite_vec.y = 1
        elif direction == "down": opposite_vec.y = -1
        
        for _ in range(8):
            vel = (opposite_vec + pygame.math.Vector2(random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3))).normalize() * random.uniform(80, 160)
            self.add_particle(Particle(
                pos=pygame.math.Vector2(pos),
                velocity=vel,
                color=(240, 245, 250), # White wind
                size=random.uniform(3, 5),
                lifetime=random.uniform(0.25, 0.4),
                drag=0.9
            ))

    def create_sparkle(self, pos: Tuple[float, float], color: Tuple[int, int, int]) -> None:
        """Spawns single trail spark particle for spell fireballs/projectiles."""
        self.add_particle(Particle(
            pos=pygame.math.Vector2(pos[0] + random.uniform(-3, 3), pos[1] + random.uniform(-3, 3)),
            velocity=pygame.math.Vector2(random.uniform(-20, 20), random.uniform(-20, 20)),
            color=color,
            size=random.uniform(2, 4),
            lifetime=random.uniform(0.15, 0.3),
            drag=0.92
        ))

# Inline math fast calculations
def math_sin(rad: float) -> float:
    import math
    return math.sin(rad)

def math_cos(rad: float) -> float:
    import math
    return math.cos(rad)
