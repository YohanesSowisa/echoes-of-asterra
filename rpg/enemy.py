"""
Echoes of Asterra - Enemy Classes
Defines the base enemy class, specific enemy archetypes, and dropped loot items.
"""
import random
import pygame
from typing import Tuple, List, Dict
from rpg.sprite import BaseSprite
from rpg.constants import (
    DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT,
    COLOR_RED
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
    def __init__(self, pos: Tuple[float, float], item: Item, groups: List[pygame.sprite.Group], despawn_time: float = 300.0) -> None:
        super().__init__(pos, groups, layer=0)
        self.item = item
        self.game = None  # Bound on spawning
        self.despawn_timer = despawn_time

        # Procedural icon representation
        self.base_image = pygame.transform.scale(item.icon, (24, 24))
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.copy()

        self.bounce_timer = random.uniform(0.0, 6.28)
        self.pickup_radius = 90.0
        self.magnet_speed = 220.0

    def update(self, dt: float) -> None:
        """Applies hover bounce, despawn timer, and pulls towards player if nearby."""
        if self.despawn_timer > 0:
            self.despawn_timer -= dt
            if self.despawn_timer <= 0:
                self.kill()
                return

        if not self.game:
            return

        # Float bounce
        self.bounce_timer += 4 * dt
        y_offset = math_sin(self.bounce_timer) * 3

        # Despawn warning blink when < 30 seconds remain
        if self.despawn_timer < 30.0:
            if int(self.despawn_timer * 8) % 2 == 0:
                self.image.set_alpha(80)
            else:
                self.image.set_alpha(255)
        else:
            self.image.set_alpha(255)

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


_ENEMY_UI_FONT_SMALL = None

_ENEMY_UI_FONT_TINY = None

def get_enemy_ui_fonts() -> Tuple[pygame.font.Font, pygame.font.Font]:
    global _ENEMY_UI_FONT_SMALL, _ENEMY_UI_FONT_TINY
    if _ENEMY_UI_FONT_SMALL is None:
        try:
            _ENEMY_UI_FONT_SMALL = pygame.font.Font("assets/fonts/game_font.ttf", 11)
            _ENEMY_UI_FONT_TINY = pygame.font.Font("assets/fonts/game_font.ttf", 9)
        except Exception as e:
            print(f"Warning: Failed loading font for Enemy UI: {e}")
            _ENEMY_UI_FONT_SMALL = pygame.font.SysFont("Arial", 11, bold=True)
            _ENEMY_UI_FONT_TINY = pygame.font.SysFont("Arial", 9, bold=True)

    return _ENEMY_UI_FONT_SMALL, _ENEMY_UI_FONT_TINY


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

        # --- AI CONTROLLER & UNLOCKED ABILITIES ---
        self.ai = EnemyAI(self.pos)
        self.level = 1
        self.enemy_key = "slime"
        self.unlocked_abilities: List[str] = []

        # --- ANIMATIONS & INJURY TRACKING ---
        self.frame_index = 0.0
        self.prev_state = "idle"
        self.prev_direction = DIR_DOWN
        self.has_been_hit = False
        self.hp_bar_timer = 0.0


    def setup_balance(self, enemy_key: str, map_name: str = "village", player_level: int = 1, floor_depth: int = 1) -> None:
        """Applies data-driven balance curves, level scaling, and archetype AI unlocks."""
        from rpg.balance import compute_enemy_level, ENEMY_BALANCES, GrowthCurve, compute_reward_multiplier

        self.enemy_key = enemy_key
        self.level = compute_enemy_level(enemy_key, map_name, player_level, floor_depth)

        bal = ENEMY_BALANCES.get(enemy_key, ENEMY_BALANCES.get("slime"))
        if bal:
            self.max_hp = GrowthCurve.calculate_hp(bal.hp_base, self.level)
            self.hp = self.max_hp
            self.atk = GrowthCurve.calculate_atk(bal.atk_base, self.level)
            self.defense = bal.def_base

            # Level delta reward scaling
            reward_mult = compute_reward_multiplier(self.level, player_level)
            base_xp = GrowthCurve.calculate_xp(bal.xp_base, self.level)
            base_gold = GrowthCurve.calculate_gold(bal.gold_base, self.level)
            self.xp_reward = max(1, int(base_xp * reward_mult))
            self.gold_reward = max(1, int(base_gold * reward_mult))

            # Archetype AI Abilities unlock
            self.unlocked_abilities = [ability for lvl, ability in bal.abilities_by_level.items() if self.level >= lvl]

    def trigger_invincibility(self, duration_ms: float) -> None:
        """Triggers temporary invincibility on getting hit."""
        self.i_frames_timer = duration_ms / 1000.0
        self.is_invincible = True

    def apply_slow_effect(self, duration: float) -> None:
        """Applies speed slow debuff (e.g. from Ice Spikes)."""
        self.slow_timer = duration

    def take_damage(self, amount: int) -> None:
        """Deducts health, activates conditional floating HP bar, and checks for death."""
        self.hp = max(0, self.hp - amount)
        self.hit_flash_timer = 0.15
        self.has_been_hit = True
        self.hp_bar_timer = 5.0
        if self.hp <= 0:
            self.state = "dead"
            self.action_timer = 0.8  # Wait for death animation
            self.sound_manager.play_sound("hit")


    def perform_attack(self) -> None:
        """Melee strike towards the player."""
        self.state = "attack"
        self.frame_index = 0.0
        self.attack_timer = self.attack_cooldown

        # Check hit on player with expanded melee reach box
        player = self.game.player
        if player and hasattr(player, "pos"):
            attack_box = self.hitbox.inflate(36, 36)
            if player.hp > 0 and attack_box.colliderect(player.hitbox):
                if getattr(player, "greed_curse_active", False):
                    self.atk = int(self.atk * 1.5)
                CombatSystem.execute_hit(self, player, [self.game.ui_sprites])


    def die(self) -> None:
        """Gives rewards, registers quest kills, and spawns loot items."""
        player = self.game.player

        # Check Greed Curse & Faction Drop Multipliers
        greed_mult = 2.0 if getattr(player, "greed_curse_active", False) else 1.0

        # Faction Hunters vs Knights Loot Multiplier
        hunter_mult = 1.0
        if hasattr(self.game, "factions"):
            h_rep = self.game.factions.get_reputation("hunters")
            if h_rep > 10 and self.asset_key in ["wolf", "slime", "slime_blue", "slime_red"]:
                hunter_mult = 2.0
            elif h_rep < 0 and self.asset_key in ["wolf", "slime", "slime_blue", "slime_red"]:
                hunter_mult = 0.5

        player.gain_xp(int(self.xp_reward * greed_mult))
        player.gold += int(self.gold_reward * greed_mult)

        # Trigger quest kill progression
        kill_type = getattr(self, "kill_type", self.asset_key)
        self.game.quest_manager.handle_kill(kill_type)

        # Emit event bus notification
        if hasattr(self.game, "event_bus"):
            self.game.event_bus.emit("enemy_killed", enemy_type=kill_type, enemy_name=self.name, pos=self.rect.center)

        # Process drops
        for item_name, base_chance in self.loot_table.items():
            final_chance = min(1.0, base_chance * hunter_mult * greed_mult)
            if random.random() <= final_chance:
                loot = create_item(item_name)
                if loot:
                    dropped = DroppedItem(self.rect.center, loot, [self.game.visible_sprites, self.game.dropped_items])
                    dropped.game = self.game
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

        # Apply visceral procedural injury / mutilation surface variant
        from rpg.sprite import get_injured_surface
        ratio = max(0.0, self.hp / max(1, self.max_hp))
        is_boss = self.asset_key in ["boss", "demon_lord", "dragon"] or "boss" in self.name.lower()
        self.image = get_injured_surface(self.image, ratio, is_boss=is_boss)

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

    def draw_hp_bar(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:

        """
        Renders floating mini HP bar, Level badge, Name, and XP reward above enemy head ONLY if enemy has been struck.
        Features smooth HP fill, dark border, color gradient, and XP reward scaling display.
        """
        if not self.has_been_hit or self.hp <= 0:
            return

        font_small, font_tiny = get_enemy_ui_fonts()
        bar_w, bar_h = 44, 5
        offset_pos = self.rect.topleft - camera_offset
        center_x = int(offset_pos.x + self.rect.width / 2)
        bar_y = int(offset_pos.y - 10)

        # 1. Level & Name Header (e.g. "Lv.3 Goblin")
        player_level = self.game.player.level if self.game and hasattr(self.game, "player") else 1
        level_color = (240, 240, 240)
        if self.level > player_level + 2:
            level_color = (255, 80, 80)  # Red warning for high level
        elif "boss" in self.name.lower() or self.asset_key == "boss":
            level_color = (255, 215, 0)  # Gold for Bosses

        name_text = f"Lv.{self.level} {self.name}"
        name_surf = font_small.render(name_text, True, level_color)
        name_rect = name_surf.get_rect(center=(center_x, bar_y - 8))

        # Text dark drop shadow for high contrast readability
        shadow_surf = font_small.render(name_text, True, (10, 10, 10))
        surface.blit(shadow_surf, (name_rect.x + 1, name_rect.y + 1))
        surface.blit(name_surf, name_rect)

        # 2. HP Bar Container & Fill
        bar_x = int(center_x - bar_w / 2)
        bg_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        pygame.draw.rect(surface, (20, 20, 20), bg_rect)
        pygame.draw.rect(surface, (0, 0, 0), bg_rect, 1)

        ratio = max(0.0, min(1.0, self.hp / max(1, self.max_hp)))
        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            if ratio > 0.66:
                col = (60, 220, 80)
            elif ratio > 0.33:
                col = (230, 200, 40)
            else:
                col = (230, 40, 40)
            fill_rect = pygame.Rect(bar_x, bar_y, fill_w, bar_h)
            pygame.draw.rect(surface, col, fill_rect)

        # 3. XP Reward Footer Badge (e.g. "+25 XP")
        xp_text = f"+{self.xp_reward} XP"
        xp_surf = font_tiny.render(xp_text, True, (120, 220, 255))
        xp_rect = xp_surf.get_rect(center=(center_x, bar_y + bar_h + 7))

        xp_shadow = font_tiny.render(xp_text, True, (10, 10, 10))
        surface.blit(xp_shadow, (xp_rect.x + 1, xp_rect.y + 1))
        surface.blit(xp_surf, xp_rect)


# --- ENEMY SUBCLASSES ---


class Slime(Enemy):
    """Bouncing soft forest slimes. Sluggish speed, common drops."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Slime", "slime")
        self.hp = 30
        self.max_hp = 30
        self.atk = 9
        self.defense = 1
        self.speed = 1.8
        self.xp_reward = 8
        self.gold_reward = 3
        self.attack_cooldown = 0.9

        # Loot drop chances
        self.loot_table = {
            "Forest Apple": 0.35,
            "Red Potion": 0.12
        }

        # Custom smaller hitbox
        self.hitbox = pygame.Rect(0, 0, 28, 16)
        self.hitbox.center = self.rect.center
        self.ai = EnemyAI(self.pos, vision_radius=300.0, attack_radius=48.0)

class Wolf(Enemy):
    """Agile forest canine. Fast speed, pounces, medium stats."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Wolf", "wolf")
        self.hp = 55
        self.max_hp = 55
        self.atk = 12
        self.defense = 2
        self.speed = 3.2
        self.xp_reward = 16
        self.gold_reward = 6
        self.attack_cooldown = 1.2

        self.loot_table = {
            "Oak Wood": 0.35,
            "Baked Bread": 0.15
        }
        self.ai = EnemyAI(self.pos, vision_radius=380.0, attack_radius=54.0)


class Skeleton(Enemy):
    """Armored undead warrior. Medium health and damage."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Skeleton", "skeleton")
        self.hp = 95
        self.max_hp = 95
        self.atk = 26
        self.defense = 5
        self.speed = 2.4
        self.xp_reward = 35
        self.gold_reward = 12
        self.attack_cooldown = 1.0

        self.loot_table = {
            "Iron Ore": 0.40,
            "Steel Blade": 0.05
        }
        self.ai = EnemyAI(self.pos, vision_radius=340.0, attack_radius=56.0)

class Mage(Enemy):
    """Ranged spellcaster. Spawns dark bolt magic projectiles."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Shadow Mage", "mage")
        self.hp = 60
        self.max_hp = 60
        self.atk = 10
        self.defense = 2
        self.magic = 24
        self.speed = 2.2
        self.xp_reward = 40
        self.gold_reward = 15
        self.attack_cooldown = 1.2

        self.loot_table = {
            "Blue Potion": 0.35,
            "Glow Amulet": 0.06
        }
        self.ai = EnemyAI(self.pos, vision_radius=420.0, attack_radius=220.0)

    def perform_attack(self) -> None:
        """Casts a dark bolt spell projectile towards the player."""
        self.state = "attack"
        self.frame_index = 0.0
        self.attack_timer = self.attack_cooldown

        self.sound_manager.play_sound("magic")

        to_player = self.game.player.pos - self.pos
        if to_player.length_squared() > 0:
            to_player = to_player.normalize()

        if abs(to_player.x) > abs(to_player.y):
            self.direction = "right" if to_player.x > 0 else "left"
        else:
            self.direction = "down" if to_player.y > 0 else "up"

        from rpg.combat import Projectile
        Projectile(
            pos=self.rect.center,
            direction=self.direction,
            speed=320.0,
            damage=14 + self.magic,
            is_magic=True,
            proj_type="dark_bolt",
            groups=[self.game.visible_sprites, self.game.projectiles],
            attacker=self
        )

class Goblin(Enemy):
    """Small fast scavenger. Steals items and flees quickly."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Goblin", "goblin")
        self.hp = 45
        self.max_hp = 45
        self.atk = 14
        self.defense = 1
        self.speed = 3.0
        self.xp_reward = 18
        self.gold_reward = 7
        self.attack_cooldown = 0.7


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

class ForestGuardian(Enemy):
    """Corrupted Forest Guardian mini-boss. Defeating it emits 'boss_forest_guardian' event
    into world_state.completed_event_ids, which is required to unlock MAP_CAVE."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Forest Guardian", "wolf")
        self.hp = 200
        self.max_hp = 200
        self.atk = 16
        self.defense = 5
        self.speed = 2.2
        self.xp_reward = 150
        self.gold_reward = 80
        self.attack_cooldown = 1.4
        self.kill_type = "forest_guardian"
        self.enemy_key = "forest_guardian"

        self.loot_table = {
            "Oak Wood": 0.80,
            "Forest Apple": 1.00,
            "Glow Amulet": 0.25,
            "Red Potion": 0.50
        }
        self.ai = EnemyAI(self.pos, vision_radius=400.0, attack_radius=56.0)

    def die(self) -> None:
        """Emits boss_forest_guardian completion flag into world_state on death."""
        if self.game and hasattr(self.game, "world_state"):
            self.game.world_state.completed_event_ids.add("boss_forest_guardian")
        if self.game and hasattr(self.game, "event_bus"):
            self.game.event_bus.emit("boss_defeated", boss_id="forest_guardian", boss_name=self.name)
        super().die()

class BanditLeader(Enemy):
    """Bandit Warlord mini-boss in the Ruins. Defeating it emits 'boss_bandit_leader' event
    into world_state.completed_event_ids, which is required to unlock MAP_RUINS access paths."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Bandit Warlord", "knight")
        self.hp = 280
        self.max_hp = 280
        self.atk = 20
        self.defense = 6
        self.speed = 2.0
        self.xp_reward = 200
        self.gold_reward = 120
        self.attack_cooldown = 1.5
        self.kill_type = "bandit_leader"
        self.enemy_key = "bandit_leader"

        self.loot_table = {
            "Iron Ore": 0.60,
            "Steel Blade": 0.20,
            "Ancient Relic": 0.30,
            "Red Potion": 0.50
        }
        self.ai = EnemyAI(self.pos, vision_radius=380.0, attack_radius=54.0)

    def die(self) -> None:
        """Emits boss_bandit_leader completion flag into world_state on death."""
        if self.game and hasattr(self.game, "world_state"):
            self.game.world_state.completed_event_ids.add("boss_bandit_leader")
        if self.game and hasattr(self.game, "event_bus"):
            self.game.event_bus.emit("boss_defeated", boss_id="bandit_leader", boss_name=self.name)
        super().die()

# Fast math helpers
def math_sin(rad: float) -> float:
    import math
    return math.sin(rad)
