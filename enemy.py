"""
Echoes of Asterra - Enemy Classes
Defines the base enemy class, specific enemy archetypes, and dropped loot items.
"""
import random
import pygame
from typing import Tuple, List, Dict, Any, Optional
from rpg.sprite import BaseSprite
from rpg.constants import (
    DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT,
    COLOR_WHITE, COLOR_RED, COLOR_YELLOW
)
from rpg.settings import TILE_SIZE
from rpg.ai import EnemyAI
from rpg.items import create_item, Item
from rpg.combat import CombatSystem, DamageNumber

class DroppedItem(BaseSprite):
    """
    An item floating on the ground. Magnetizes towards the player
    when they get close and adds itself to the inventory on contact.
    """
    def __init__(self, pos: Tuple[float, float], item: Item, groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, layer=0)
        self.item = item
        self.game = None  # Bound on spawning
        
        # Procedural icon representation
        self.image = pygame.transform.scale(item.icon, (24, 24))
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.copy()
        
        self.bounce_timer = random.uniform(0.0, 6.28)
        self.pickup_radius = 90.0
        self.magnet_speed = 220.0

    def update(self, dt: float) -> None:
        """Applies hover bounce and pulls towards player if nearby."""
        if not self.game:
            return
            
        # Float bounce
        self.bounce_timer += 4 * dt
        y_offset = math_sin(self.bounce_timer) * 3
        
        # Magnetize to player check
        player = self.game.player
        to_player = player.pos - self.pos
        dist = to_player.length()
        
        if dist < self.pickup_radius:
            # Pull towards player
            dir_vec = to_player.normalize()
            self.pos += dir_vec * self.magnet_speed * dt
            self.rect.center = (int(self.pos.x), int(self.pos.y) + int(y_offset))
            self.hitbox.center = self.rect.center
            
            # Collide to pick up
            if self.hitbox.colliderect(player.hitbox):
                if player.inventory.add_item(self.item):
                    # Play sound
                    player.sound_manager.play_sound("heal")
                    # Float notify
                    DamageNumber(player.rect.center, f"+ {self.item.name} x{self.item.quantity}", (60, 200, 80), [self.game.ui_sprites], size=16)
                    # Trigger inventory quest check
                    self.game.quest_manager.handle_inventory_change(player.inventory)
                    self.kill()
                else:
                    # Inventory full
                    DamageNumber(player.rect.center, "Inventory Full!", COLOR_RED, [self.game.ui_sprites], size=16)
                    # Push back a bit
                    self.pos -= dir_vec * 20
        else:
            # Keep resting position
            self.rect.center = (int(self.pos.x), int(self.pos.y) + int(y_offset))

class Enemy(BaseSprite):
    """
    Base enemy class containing core stats, combat loops, FSM tickers,
    and loot dropping methods.
    """
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group], name: str, asset_key: str) -> None:
        super().__init__(pos, groups, layer=1)
        self.name = name
        self.asset_key = asset_key
        self.game = None  # bound during map spawn
        
        # --- BASE STATS (subclasses override these) ---
        self.hp = 20
        self.max_hp = 20
        self.atk = 5
        self.defense = 1
        self.magic = 0
        self.speed = 2.0
        self.xp_reward = 15
        self.gold_reward = 10
        self.loot_table: Dict[str, float] = {}  # item_name -> drop_chance (0.0 to 1.0)
        
        # --- PHYSICALS & MOVEMENT ---
        self.velocity = pygame.math.Vector2(0, 0)
        self.hitbox = pygame.Rect(0, 0, 24, 20)
        self.hitbox.center = self.rect.center
        self.direction = DIR_DOWN
        self.state = "idle"
        self.is_running = False
        
        self.knockback_vector = pygame.math.Vector2(0, 0)
        self.knockback_duration = 0.0
        
        # --- COMBAT COOLDOWNS ---
        self.attack_timer = 0.0
        self.attack_cooldown = 1.5  # seconds
        self.i_frames_timer = 0.0
        self.is_invincible = False
        
        # Slow debuff tracker
        self.slow_timer = 0.0
        self.slow_multiplier = 0.5
        self.hit_flash_timer = 0.0
        
        # --- AI CONTROLLER ---
        self.ai = EnemyAI(self.pos)
        
        # --- ANIMATIONS ---
        self.frame_index = 0.0
        self.prev_state = "idle"
        self.prev_direction = DIR_DOWN

    def trigger_invincibility(self, duration_ms: float) -> None:
        """Triggers temporary invincibility on getting hit."""
        self.i_frames_timer = duration_ms / 1000.0
        self.is_invincible = True

    def apply_slow_effect(self, duration: float) -> None:
        """Applies speed slow debuff (e.g. from Ice Spikes)."""
        self.slow_timer = duration

    def take_damage(self, amount: int) -> None:
        """Deducts health, checks for death."""
        self.hp = max(0, self.hp - amount)
        self.hit_flash_timer = 0.15
        if self.hp <= 0:
            self.state = "dead"
            self.action_timer = 0.8  # Wait for death animation
            self.sound_manager.play_sound("hit")

    def perform_attack(self) -> None:
        """Melee strike towards the player."""
        self.state = "attack"
        self.frame_index = 0.0
        self.attack_timer = self.attack_cooldown
        
        # Check hit on player
        player = self.game.player
        if player.hp > 0 and self.hitbox.colliderect(player.hitbox):
            CombatSystem.execute_hit(self, player, [self.game.ui_sprites])

    def die(self) -> None:
        """Gives rewards, registers quest kills, and spawns loot items."""
        player = self.game.player
        player.gain_xp(self.xp_reward)
        player.gold += self.gold_reward
        
        # Trigger quest kill progression
        self.game.quest_manager.handle_kill(getattr(self, "kill_type", self.asset_key))
        
        # Process drops
        for item_name, chance in self.loot_table.items():
            if random.random() <= chance:
                loot = create_item(item_name)
                if loot:
                    dropped = DroppedItem(self.rect.center, loot, [self.game.visible_sprites, self.game.dropped_items])
                    dropped.game = self.game
                    # Toss randomly slightly away
                    dropped.pos.x += random.uniform(-15, 15)
                    dropped.pos.y += random.uniform(-15, 15)
                    
        # Visual particles splash
        self.game.particles.create_kill_splash(self.rect.center)
        self.kill()

    def update(self, dt: float) -> None:
        """Ticks cooldowns, updates FSM AI direction, and handles collisions."""
        # 1. Update timers
        if self.attack_timer > 0:
            self.attack_timer -= dt
            
        if self.i_frames_timer > 0:
            self.i_frames_timer -= dt
            if self.i_frames_timer <= 0:
                self.is_invincible = False
                if self.state == "hurt":
                    self.state = "idle"
                    
        if self.slow_timer > 0:
            self.slow_timer -= dt
            
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt

        # 2. Check Death
        if self.hp <= 0:
            self.velocity = pygame.math.Vector2(0, 0)
            if self.knockback_duration > 0:
                self.knockback_duration -= dt
                self.pos += self.knockback_vector * dt
                self.hitbox.center = (int(self.pos.x), int(self.pos.y))
                self.rect.center = self.hitbox.center
            
            self.frame_index += 4 * dt
            # If death anim finishes, trigger cleanup
            from rpg.animation import entity_assets
            frames = entity_assets[self.asset_key]["dead"][self.direction]
            if int(self.frame_index) >= len(frames):
                self.die()
            else:
                self.image = frames[int(self.frame_index)]
            return

        # 3. Process AI Brain
        self.ai.update(self, self.game.player, dt)

        # 4. Resolve Movement
        if self.knockback_duration > 0:
            self.knockback_duration -= dt
            self.velocity = self.knockback_vector
            if self.knockback_duration <= 0:
                self.knockback_vector = pygame.math.Vector2(0, 0)
        else:
            # Set speed (applying slows)
            curr_speed = self.speed
            if self.slow_timer > 0:
                curr_speed *= self.slow_multiplier
                
            self.velocity = self.move_dir * curr_speed
            
        if self.velocity.length_squared() > 0 or self.knockback_duration > 0:
            # Align facing direction based on movement
            if self.knockback_duration <= 0:
                self.state = "walk"
                if abs(self.velocity.x) > abs(self.velocity.y):
                    self.direction = DIR_RIGHT if self.velocity.x > 0 else DIR_LEFT
                else:
                    self.direction = DIR_DOWN if self.velocity.y > 0 else DIR_UP
            else:
                self.state = "hurt"
                
            from rpg.collision import CollisionSystem
            solid_rects = CollisionSystem.get_nearby_solids(self.hitbox, self.game.world_manager.current_map_grid, TILE_SIZE)
            
            # Resolve X
            self.pos.x += self.velocity.x * 60.0 * dt
            self.hitbox.centerx = int(self.pos.x)
            CollisionSystem.resolve_movement(self, solid_rects, 'x')
            
            # Resolve Y
            self.pos.y += self.velocity.y * 60.0 * dt
            self.hitbox.centery = int(self.pos.y)
            CollisionSystem.resolve_movement(self, solid_rects, 'y')
            
            self.rect.center = self.hitbox.center
        else:
            if self.state not in ["attack", "hurt"]:
                self.state = "idle"

        # 5. Handle Sprite animations
        self.animate(dt)

    def animate(self, dt: float) -> None:
        """Ticks animation frames and updates Surface."""
        current_key = self.state
        if self.prev_state != current_key or self.prev_direction != self.direction:
            self.frame_index = 0.0
            self.prev_state = current_key
            self.prev_direction = self.direction
            
        from rpg.animation import entity_assets
        frames = entity_assets[self.asset_key][current_key][self.direction]
        
        anim_speed = 6.0
        if self.state == "walk":
            anim_speed = 10.0 if self.is_running else 6.0
        elif self.state == "attack":
            anim_speed = 12.0
            
        self.frame_index += anim_speed * dt
        self.image = frames[int(self.frame_index) % len(frames)]
        
        # Red flashing if hurt and invincible
        if self.is_invincible:
            if int(pygame.time.get_ticks() / 50) % 2 == 0:
                temp = self.image.copy()
                temp.fill((255, 100, 100, 130), special_flags=pygame.BLEND_RGBA_MULT)
                self.image = temp
                
        # Solid white hit flash
        if self.hit_flash_timer > 0:
            mask = pygame.mask.from_surface(self.image)
            self.image = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))

# --- ENEMY SUBCLASSES ---

class Slime(Enemy):
    """Bouncing soft forest slimes. Sluggish speed, common drops."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Slime", "slime")
        self.hp = 25
        self.max_hp = 25
        self.atk = 5
        self.defense = 1
        self.speed = 1.4
        self.xp_reward = 12
        self.gold_reward = 6
        self.attack_cooldown = 1.8
        
        # Loot drop chances
        self.loot_table = {
            "Forest Apple": 0.40,
            "Red Potion": 0.15
        }
        
        # Custom smaller hitbox
        self.hitbox = pygame.Rect(0, 0, 28, 16)
        self.hitbox.center = self.rect.center
        self.ai = EnemyAI(self.pos, vision_radius=280.0, attack_radius=38.0)

class Wolf(Enemy):
    """Agile forest canine. Fast speed, pounces, medium stats."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Wolf", "wolf")
        self.hp = 40
        self.max_hp = 40
        self.atk = 9
        self.defense = 2
        self.speed = 2.6
        self.xp_reward = 25
        self.gold_reward = 12
        self.attack_cooldown = 1.3
        
        self.loot_table = {
            "Oak Wood": 0.35,
            "Baked Bread": 0.20
        }
        self.ai = EnemyAI(self.pos, vision_radius=350.0, attack_radius=44.0)

class Skeleton(Enemy):
    """Armored undead warrior. Medium health and damage."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Skeleton", "skeleton")
        self.hp = 60
        self.max_hp = 60
        self.atk = 12
        self.defense = 3
        self.speed = 1.8
        self.xp_reward = 35
        self.gold_reward = 18
        self.attack_cooldown = 1.6
        
        self.loot_table = {
            "Iron Ore": 0.45,
            "Steel Blade": 0.05
        }
        self.ai = EnemyAI(self.pos, vision_radius=320.0, attack_radius=48.0)

class Mage(Enemy):
    """Ranged spellcaster. Spawns dark bolt magic projectiles."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Shadow Mage", "mage")
        self.hp = 45
        self.max_hp = 45
        self.atk = 6
        self.defense = 1
        self.magic = 12
        self.speed = 1.6
        self.xp_reward = 45
        self.gold_reward = 25
        self.attack_cooldown = 2.2
        
        self.loot_table = {
            "Blue Potion": 0.40,
            "Glow Amulet": 0.06
        }
        # Mage keeps range away from player, vision is wide, attacks from distance
        self.ai = EnemyAI(self.pos, vision_radius=400.0, attack_radius=200.0)

    def perform_attack(self) -> None:
        """Casts a dark bolt spell projectile towards the player."""
        self.state = "attack"
        self.frame_index = 0.0
        self.attack_timer = self.attack_cooldown
        
        # Play magic sound
        self.sound_manager.play_sound("magic")
        
        # Calculate direction towards player
        to_player = self.game.player.pos - self.pos
        if to_player.length_squared() > 0:
            to_player = to_player.normalize()
            
        # Determine facing
        if abs(to_player.x) > abs(to_player.y):
            self.direction = "right" if to_player.x > 0 else "left"
        else:
            self.direction = "down" if to_player.y > 0 else "up"

        # Spawn Projectile
        from rpg.combat import Projectile
        Projectile(
            pos=self.rect.center,
            direction=self.direction,
            speed=200.0,
            damage=12 + self.magic,
            is_magic=True,
            proj_type="dark_bolt",
            groups=[self.game.visible_sprites, self.game.projectiles],
            attacker=self
        )

class Goblin(Enemy):
    """Small fast scavenger. Steals items and flees quickly."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Goblin", "goblin")
        self.hp = 35
        self.max_hp = 35
        self.atk = 8
        self.defense = 0
        self.speed = 2.3
        self.xp_reward = 20
        self.gold_reward = 15
        self.attack_cooldown = 1.1
        
        self.loot_table = {
            "Iron Ore": 0.25,
            "Forest Apple": 0.30,
            "Red Potion": 0.15
        }
        self.ai = EnemyAI(self.pos, vision_radius=320.0, attack_radius=40.0)

class Knight(Enemy):
    """Heavy armored knight. High health, defense, and high damage."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Corrupted Knight", "knight")
        self.hp = 90
        self.max_hp = 90
        self.atk = 18
        self.defense = 6  # Blocks high amount of damage
        self.speed = 1.5
        self.xp_reward = 60
        self.gold_reward = 35
        self.attack_cooldown = 1.8
        
        self.loot_table = {
            "Iron Ore": 0.50,
            "Iron Aegis": 0.08,
            "Iron Helmet": 0.12
        }
        self.ai = EnemyAI(self.pos, vision_radius=300.0, attack_radius=52.0)

# Fast math helpers
def math_sin(rad: float) -> float:
    import math
    return math.sin(rad)
