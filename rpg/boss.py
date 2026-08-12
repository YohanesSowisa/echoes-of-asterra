"""
Echoes of Asterra - Final Boss
Implements the multi-phase Shadow Overlord boss with custom attack patterns, phase shifts, and a death cutscene.
"""
import random
import pygame
import math
from typing import Tuple, List
from rpg.constants import (
    DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT,
    COLOR_WHITE, COLOR_RED, COLOR_YELLOW, COLOR_BLACK, COLOR_ORANGE
)
from rpg.settings import TILE_SIZE
from rpg.enemy import Enemy
from rpg.ai import EnemyAI
from rpg.combat import CombatSystem, Projectile, DamageNumber
from typing import Any

class Boss(Enemy):
    """
    Final dungeon boss. Has 2 distinct phases:
    - Phase 1: Heavy melee swings and rapid dash slams.
    - Phase 2 (<50% HP): Speed up, shorter attack cooldown, and radial dark bolt rings.
    - Death Cutscene: Controls lock, camera shakes, and fades into victory state.
    """
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group], sound_manager: Any, particles: Any) -> None:
        super().__init__(pos, groups, "Shadow Overlord", "boss")
        self.sound_manager = sound_manager
        self.particles = particles

        # --- BOSS STATS ---
        self.hp = 600
        self.max_hp = 600
        self.atk = 24
        self.defense = 7
        self.speed = 1.8
        self.xp_reward = 2000
        self.gold_reward = 1000
        self.attack_cooldown = 2.0

        # Large scale hitbox
        self.hitbox = pygame.Rect(0, 0, 52, 44)
        self.hitbox.center = self.rect.center

        # FSM parameters
        self.ai = EnemyAI(
            self.pos,
            vision_radius=400.0,
            attack_radius=96.0,
            tether_radius=1000.0,
            patrol_radius=0.0  # Stays stationary until aggroed
        )

        # Phase parameters
        self.phase = 1
        self.is_cutscene_active = False
        self.cutscene_timer = 0.0

        self.loot_table = {
            "Asterra Sword": 1.00,
            "Dragon Horn Helmet": 1.00,
            "Asterra Heart": 1.00
        }

    def take_damage(self, amount: int) -> None:
        """Applies damage and checks for Phase 2 shift and Death Cutscene triggers."""
        if self.is_cutscene_active:
            return

        self.hp = max(0, self.hp - amount)
        self.hit_flash_timer = 0.15

        # Check Phase 2 Shift
        if self.phase == 1 and self.hp <= self.max_hp // 2:
            self.phase = 2
            self.speed = 2.6
            self.attack_cooldown = 1.2
            self.sound_manager.play_sound("levelup")
            self.particles.create_levelup_splash(self.rect.center)
            DamageNumber(self.rect.center, "PHASE 2 - RAGE MODE!", COLOR_YELLOW, [self.game.ui_sprites], size=22)
            # Shake screen
            self.game.camera.trigger_shake(10.0, 300)

        # Check Death
        if self.hp <= 0:
            self.is_cutscene_active = True
            self.cutscene_timer = 3.0  # 3-second death scene
            self.state = "dead"
            self.frame_index = 0.0
            # Mute bg music
            self.sound_manager.stop_music()
            self.sound_manager.play_sound("gameover")

    def perform_attack(self) -> None:
        """Chooses randomly between Boss special moves based on current phase."""
        self.attack_timer = self.attack_cooldown
        self.state = "attack"
        self.frame_index = 0.0
        
        # Project 1.0s Floor Danger Telegraph Circle centered on target
        self.telegraph_timer = 1.0
        self.telegraph_pos = pygame.math.Vector2(self.game.player.pos)
        self.telegraph_radius = 96.0 if self.phase == 2 else 72.0

        attack_choice = random.choice([1, 2])
        if self.phase == 2:
            # Unlock bullet ring in Phase 2
            attack_choice = random.choice([1, 2, 3])

        if attack_choice == 1:
            self.attack_greatsword_swing()
        elif attack_choice == 2:
            self.attack_dash_slam()
        elif attack_choice == 3:
            self.attack_bullet_ring()

    def attack_greatsword_swing(self) -> None:
        """A massive sweeping melee strike in front of the boss."""
        self.sound_manager.play_sound("sword")

        # Build giant sweep rect
        sweep_rect = pygame.Rect(0, 0, TILE_SIZE * 2, TILE_SIZE * 2)
        if self.direction == DIR_DOWN: sweep_rect.midtop = self.hitbox.midbottom
        elif self.direction == DIR_UP: sweep_rect.midbottom = self.hitbox.midtop
        elif self.direction == DIR_LEFT: sweep_rect.midright = self.hitbox.midleft
        elif self.direction == DIR_RIGHT: sweep_rect.midleft = self.hitbox.midright

        # Test collision against player
        player = self.game.player
        if player.hp > 0 and sweep_rect.colliderect(player.hitbox):
            CombatSystem.execute_hit(self, player, [self.game.ui_sprites], speed_modifier=1.5)

    def attack_dash_slam(self) -> None:
        """Charges rapidly forward. Deals impact damage and shakes screen."""
        self.sound_manager.play_sound("magic")

        # Calculate dash velocity towards player
        player = self.game.player
        diff = player.pos - self.pos
        if diff.length_squared() > 0:
            dash_dir = diff.normalize()
            self.knockback_vector = dash_dir * 5.0  # High dash speed
            self.knockback_duration = 0.3
            self.velocity = self.knockback_vector

        # Spawn shockwave dust
        self.particles.create_dash_trail(self.rect.center, self.direction)

        # Test overlap hits during slide
        if self.hitbox.colliderect(player.hitbox):
            CombatSystem.execute_hit(self, player, [self.game.ui_sprites], speed_modifier=2.0)

    def attack_bullet_ring(self) -> None:
        """Fires 8 magical dark bolts radially in all directions (Phase 2 Only)."""
        self.sound_manager.play_sound("magic")

        angles = [0, 45, 90, 135, 180, 225, 270, 315]
        dirs = [DIR_RIGHT, DIR_RIGHT, DIR_DOWN, DIR_LEFT, DIR_LEFT, DIR_LEFT, DIR_UP, DIR_RIGHT]

        for angle, direction in zip(angles, dirs):
            rad = math.radians(angle)
            vx, vy = math.cos(rad), math.sin(rad)

            # Spawn dark bolt projectile
            proj = Projectile(
                pos=self.rect.center,
                direction=direction,
                speed=180.0,
                damage=12 + self.magic,
                is_magic=True,
                proj_type="dark_bolt",
                groups=[self.game.visible_sprites, self.game.projectiles],
                attacker=self
            )
            # Override projectile velocity to precise radial vector
            proj.velocity = pygame.math.Vector2(vx, vy) * 180.0

    def update(self, dt: float) -> None:
        """Updates FSM AI actions. Handles custom cutscene progression on death."""
        # 1. Death Cutscene ticker
        if self.is_cutscene_active:
            self.velocity = pygame.math.Vector2(0, 0)
            self.cutscene_timer -= dt

            # Violent shake
            self.game.camera.trigger_shake(8.0, 50)
            # Spawn dark explosions
            if random.random() < 0.15:
                self.particles.create_kill_splash(self.rect.center + pygame.math.Vector2(random.uniform(-40, 40), random.uniform(-40, 40)))
                self.sound_manager.play_sound("hit")

            if self.cutscene_timer <= 0:
                self.die()
                self.game.world_manager.boss_defeated = True
                if hasattr(self.game, "world_state"):
                    self.game.world_state.completed_event_ids.add("boss_shadow_overlord")
                if hasattr(self.game, "event_bus"):
                    self.game.event_bus.emit("boss_defeated", boss_id="shadow_overlord", boss_name=self.name)
                if hasattr(self.game, "mythos_manager") and self.game.mythos_manager:
                    self.game.mythos_manager.record_run(self.game, end_cause="Vanquished the Shadow Overlord")
                
                # Trigger LEGENDARY celebration banner instead of forcing main menu kick
                if hasattr(self.game, "ui_manager") and hasattr(self.game.ui_manager, "celebration"):
                    from rpg.celebration import CelebrationTier
                    self.game.ui_manager.celebration.trigger_celebration(
                        CelebrationTier.LEGENDARY,
                        "SHADOW OVERLORD VANQUISHED!",
                        "The corruption lifts from Asterra! Return to Elder Eldrin to claim your victory.",
                        event_bus=getattr(self.game, "event_bus", None)
                    )
            return

        # 2. Standard enemy updates (AI, collisions, moves)
        super().update(dt)

        if self.telegraph_timer > 0.0:
            self.telegraph_timer = max(0.0, self.telegraph_timer - dt)

        # 3. Particle glow in Phase 2
        if self.phase == 2 and random.random() < 0.2:
            self.particles.create_sparkle(self.rect.center + pygame.math.Vector2(random.uniform(-20, 20), random.uniform(-20, 20)), COLOR_ORANGE)

    def draw_danger_telegraph(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        """Renders glowing translucent red floor danger circle 1.0s before heavy attacks."""
        if self.telegraph_timer <= 0.0:
            return
            
        screen_pos = self.telegraph_pos - camera_offset
        r = int(self.telegraph_radius)
        
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        alpha = int(140 * (self.telegraph_timer / 1.0))
        pygame.draw.circle(surf, (240, 40, 40, alpha), (r, r), r)
        pygame.draw.circle(surf, (255, 200, 50, alpha), (r, r), r, width=3)
        surface.blit(surf, (screen_pos.x - r, screen_pos.y - r))

    def draw_health_bar(self, surface: pygame.Surface) -> None:
        """Renders the custom Boss HP overlay on top of screen."""
        if self.hp <= 0 or self.ai.state == "patrol":
            return

        bar_w = 400
        bar_h = 16
        bx = (surface.get_width() - bar_w) // 2
        by = 24

        # Border
        pygame.draw.rect(surface, COLOR_BLACK, (bx - 2, by - 2, bar_w + 4, bar_h + 4), border_radius=4)

        # Background
        pygame.draw.rect(surface, (60, 20, 20), (bx, by, bar_w, bar_h), border_radius=2)

        # Fill
        ratio = self.hp / self.max_hp
        pygame.draw.rect(surface, COLOR_RED, (bx, by, int(bar_w * ratio), bar_h), border_radius=2)

        # Shiny highlight
        if ratio > 0:
            pygame.draw.rect(surface, (255, 120, 120), (bx, by, int(bar_w * ratio), 3), border_radius=1)

        # Text Overlay
        try:
            font = pygame.font.Font("assets/fonts/game_font.ttf", 14)
        except Exception as e:
            print(f"Warning: Failed loading custom font for Boss HUD: {e}")
            font = pygame.font.SysFont("Arial", 12, bold=True)

        name_txt = font.render(f"{self.name} (PHASE {self.phase})", True, COLOR_WHITE)
        hp_txt = font.render(f"{self.hp} / {self.max_hp}", True, COLOR_WHITE)

        surface.blit(name_txt, (bx, by - 16))
        surface.blit(hp_txt, (bx + bar_w - hp_txt.get_width(), by - 16))
