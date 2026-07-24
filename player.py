"""
Echoes of Asterra - Player Entity
Manages player movement, combat inputs, animations, stat scaling, inventory/gear, and skills.
"""
import pygame
from typing import List, Any, Tuple
from rpg.sprite import BaseSprite
from rpg.constants import (
    DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT,
    STATE_PLAYING, STATE_PAUSED, STATE_GAME_OVER,
    ITEM_WEAPON, ITEM_HELMET, ITEM_CHEST, ITEM_BOOTS, ITEM_SHIELD, ITEM_ACCESSORY, ITEM_LEGS,
    SKILL_DASH, SKILL_HEALING, SKILL_FIREBALL, SKILL_SHIELD, SKILL_ICE_SPIKE, SKILL_LIGHTNING, SKILL_SWORD_MASTERY
)
from rpg.settings import (
    TILE_SIZE, PLAYER_SPEED, PLAYER_RUN_MULTIPLIER, PLAYER_ROLL_SPEED,
    PLAYER_ROLL_DURATION, PLAYER_ROLL_COOLDOWN, PLAYER_I_FRAMES_DURATION
)
from rpg.inventory import Inventory
from rpg.equipment import Equipment
from rpg.skills import SkillManager
from rpg.animation import entity_assets
from rpg.combat import DamageNumber

class Player(BaseSprite):
    """
    Main playable hero. Receives inputs, coordinates inventory/gear,
    moves, collides, attacks, blocks, and levels up.
    """
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group], sound_manager: Any, particles: Any) -> None:
        super().__init__(pos, groups, layer=1)
        self.sound_manager = sound_manager
        self.particles = particles
        self.game = None  # Bound during game engine startup
        
        # --- BASE STATS (Level 1) ---
        self.level = 1
        self.xp = 0
        self.xp_needed = 100
        self.gold = 50
        
        self.base_max_hp = 100
        self.base_max_mana = 50
        self.base_max_stamina = 100
        
        self.base_atk = 10
        self.base_def = 2
        self.base_magic = 8
        self.base_speed = 3.2
        self.base_crit = 5  # percent

        # --- DYNAMIC/DERIVED STATS ---
        # Recalculated by inventory equipment updates
        self.max_hp = self.base_max_hp
        self.max_mana = self.base_max_mana
        self.max_stamina = self.base_max_stamina
        
        self.hp = self.max_hp
        self.mana = self.max_mana
        self.stamina = self.max_stamina
        
        self.atk = self.base_atk
        self.defense = self.base_def
        self.magic = self.base_magic
        self.speed = self.base_speed
        self.crit_chance = self.base_crit

        # --- MOVEMENT & PHYSICS ---
        self.velocity = pygame.math.Vector2(0, 0)
        # Custom tight combat hitbox (bottom half of character)
        self.hitbox = pygame.Rect(0, 0, 24, 20)
        self.hitbox.center = self.rect.center
        
        self.direction = DIR_DOWN
        self.state = "idle"
        self.is_running = False
        self.is_blocking = False
        
        # Knockback physical impulse
        self.knockback_vector = pygame.math.Vector2(0, 0)
        self.knockback_duration = 0.0

        # --- RECOVERY & REGEN TICKERS ---
        self.mana_regen_rate = 3.0  # mana per sec
        self.stamina_regen_rate = 15.0  # stamina per sec

        # --- TIMER COOLDOWNS ---
        self.action_timer = 0.0
        self.roll_cooldown_timer = 0.0
        self.i_frames_timer = 0.0
        self.is_invincible = False
        self.attack_cooldown_timer = 0.0

        # --- INVENTORY, GEAR, & SKILLS ---
        self.inventory = Inventory(24)
        self.equipment = Equipment()
        self.skill_manager = SkillManager()
        self.skill_manager.check_unlocks(self.level)
        
        # Skill buffs/shields
        self.has_shield_active = False

        # --- GRAPHICS FRAME ---
        self.frame_index = 0.0
        self.prev_state = "idle"
        self.prev_direction = DIR_DOWN
        
        # Add basic starting items
        self.add_starter_items()

    def add_starter_items(self) -> None:
        """Grants the player basic starting gear and resources."""
        from rpg.items import create_item
        sword = create_item("Rusty Sword")
        shield = create_item("Wooden Shield")
        pot = create_item("Red Potion", 3)
        mp_pot = create_item("Blue Potion", 2)
        bread = create_item("Baked Bread", 2)
        iron = create_item("Iron Ore", 2)
        wood = create_item("Oak Wood", 2)
        
        if sword: self.inventory.add_item(sword)
        if shield: self.inventory.add_item(shield)
        if pot: self.inventory.add_item(pot)
        if mp_pot: self.inventory.add_item(mp_pot)
        if bread: self.inventory.add_item(bread)
        if iron: self.inventory.add_item(iron)
        if wood: self.inventory.add_item(wood)

    def trigger_invincibility(self, duration_ms: float) -> None:
        """Gives the player temporary damage invincibility frames."""
        self.i_frames_timer = duration_ms / 1000.0
        self.is_invincible = True

    def gain_xp(self, amount: int) -> None:
        """Gains experience points and handles level ups."""
        self.xp += amount
        if self.xp >= self.xp_needed:
            self.xp -= self.xp_needed
            self.level_up()

    def level_up(self) -> None:
        """Triggers player stat growth and skill unlocks on level up."""
        self.level += 1
        self.xp_needed = int(self.xp_needed * 1.5)
        
        # Grow base stats
        self.base_max_hp += 12
        self.base_max_mana += 6
        self.base_max_stamina += 5
        self.base_atk += 2
        self.base_def += 1
        self.base_magic += 2
        
        # Recalculate stats with equipment modifiers
        self.equipment.recalculate_player_stats(self)
        
        # Heal completely on level up
        self.hp = self.max_hp
        self.mana = self.max_mana
        self.stamina = self.max_stamina
        
        # Play Levelup sound and spark particles
        self.sound_manager.play_sound("levelup")
        self.particles.create_levelup_splash(self.hitbox.center)
        
        # Float text
        DamageNumber(self.rect.center, f"LEVEL UP! ({self.level})", (200, 60, 200), [self.game.ui_sprites], size=22)
        
        # Check skill unlocks
        newly_unlocked = self.skill_manager.check_unlocks(self.level)
        for skill_name in newly_unlocked:
            DamageNumber((self.rect.centerx, self.rect.centery - 24), f"Unlocked {skill_name}!", (250, 150, 10), [self.game.ui_sprites], size=16)

    def take_damage(self, amount: int) -> None:
        """Applies damage to health, triggers death sequence if HP is empty."""
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.state = "dead"
            self.action_timer = 2.0  # dead animation duration before game over
            self.sound_manager.play_sound("gameover")

    def perform_attack(self) -> None:
        """Triggers a sword slash sweep in front of the player."""
        if self.state in ["attack", "roll", "dead"]:
            return
            
        self.state = "attack"
        self.frame_index = 0.0
        # Melee swing duration (fast)
        self.action_timer = 0.25
        self.attack_cooldown_timer = 0.35
        
        # Play slash sound
        self.sound_manager.play_sound("sword")

        # Determine hit check zone in front of player
        sweep_dist = 36
        sweep_rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        
        if self.direction == DIR_DOWN:
            sweep_rect.midtop = self.hitbox.midbottom
            sweep_rect.y += 4
        elif self.direction == DIR_UP:
            sweep_rect.midbottom = self.hitbox.midtop
            sweep_rect.y -= 4
        elif self.direction == DIR_LEFT:
            sweep_rect.midright = self.hitbox.midleft
            sweep_rect.x -= 4
        elif self.direction == DIR_RIGHT:
            sweep_rect.midleft = self.hitbox.midright
            sweep_rect.x += 4

        # Query hits against enemies
        from rpg.combat import CombatSystem
        # Apply Sword Mastery passive bonus if unlocked
        atk_boost = 0
        if self.skill_manager.skills[SKILL_SWORD_MASTERY].unlocked:
            atk_boost = 4
            
        # Temporarily increase ATK for this strike
        self.atk += atk_boost
        
        for enemy in self.game.enemies:
            if enemy.hp > 0 and sweep_rect.colliderect(enemy.hitbox):
                CombatSystem.execute_hit(self, enemy, [self.game.ui_sprites], is_magic=False)
                
        # Revert ATK boost
        self.atk -= atk_boost

    def perform_roll(self) -> None:
        """Initiates a dodge roll maneuver."""
        if self.state in ["roll", "attack", "dead"]:
            return
        if self.stamina < 15:
            return
            
        self.stamina -= 15
        self.state = "roll"
        self.frame_index = 0.0
        self.action_timer = PLAYER_ROLL_DURATION / 1000.0
        self.roll_cooldown_timer = PLAYER_ROLL_COOLDOWN / 1000.0
        
        # Grant invincibility frames during roll
        self.trigger_invincibility(PLAYER_ROLL_DURATION)
        
        # Play footstep/swoosh sound
        self.sound_manager.play_sound("footstep")

    def handle_skill_casts(self, input_handler: Any) -> None:
        """Maps quick skill casting keys (1-4) to skill effects."""
        if self.state in ["roll", "dead"]:
            return

        # Map active key triggers
        casted = False
        skill_name = None
        
        if input_handler.consume_action("skill_4"):  # K_4: Dash
            skill_name = SKILL_DASH
        elif input_handler.consume_action("skill_3"): # K_3: Healing
            skill_name = SKILL_HEALING
        elif input_handler.consume_action("skill_1"): # K_1: Fireball
            skill_name = SKILL_FIREBALL
        elif input_handler.consume_action("skill_2"): # K_2: Ice Spike
            skill_name = SKILL_ICE_SPIKE

        if not skill_name:
            return

        # Attempt to cast via manager
        if self.skill_manager.cast(skill_name, self):
            self.execute_skill_effect(skill_name)

    def execute_skill_effect(self, name: str) -> None:
        """Spawns spell projectiles or triggers visual/recovery buffs."""
        if name == SKILL_DASH:
            # Force a dodge roll in moving direction
            self.state = "roll"
            self.frame_index = 0.0
            self.action_timer = 0.3
            self.trigger_invincibility(350)
            
            # Spawn wind trail
            self.particles.create_dash_trail(self.hitbox.center, self.direction)
            self.sound_manager.play_sound("magic")
            
        elif name == SKILL_HEALING:
            # Healing recovery
            heal_amt = 35 + int(self.magic * 0.5)
            self.hp = min(self.max_hp, self.hp + heal_amt)
            self.sound_manager.play_sound("heal")
            self.particles.create_heal_sparkles(self.hitbox.center)
            DamageNumber(self.rect.center, f"+{heal_amt}", (100, 240, 100), [self.game.ui_sprites], size=18)
            
        elif name == SKILL_FIREBALL:
            # Spawn projectile
            self.state = "attack"
            self.action_timer = 0.2
            self.sound_manager.play_sound("magic")
            # Launch fireball
            from rpg.combat import Projectile
            Projectile(
                pos=self.rect.center,
                direction=self.direction,
                speed=300.0,
                damage=15 + self.magic,
                is_magic=True,
                proj_type="fireball",
                groups=[self.game.visible_sprites, self.game.projectiles],
                attacker=self
            )
            
        elif name == SKILL_ICE_SPIKE:
            # Spawn ice projectile
            self.state = "attack"
            self.action_timer = 0.2
            self.sound_manager.play_sound("magic")
            # Launch spike
            from rpg.combat import Projectile
            Projectile(
                pos=self.rect.center,
                direction=self.direction,
                speed=340.0,
                damage=10 + int(self.magic * 0.8),
                is_magic=True,
                proj_type="ice_spike",
                groups=[self.game.visible_sprites, self.game.projectiles],
                attacker=self
            )

    def handle_movement_input(self, input_handler: Any) -> None:
        """Translates keyboard inputs into movement direction, running and blocking."""
        if self.state in ["attack", "roll", "dead"]:
            return
            
        # Continuous movement and key state checks (must run every frame!)
        input_handler.update_keyboard_states()

        # Check shield blocking
        if input_handler.is_blocking and self.equipment.slots.get(ITEM_SHIELD):
            self.is_blocking = True
            self.state = "block"
            self.velocity.x = 0
            self.velocity.y = 0
            return
        else:
            self.is_blocking = False

        move_vec = input_handler.move_dir
        self.is_running = input_handler.is_running
        
        if move_vec.length_squared() > 0:
            self.state = "walk"
            # Update facing direction
            if abs(move_vec.x) > abs(move_vec.y):
                self.direction = DIR_RIGHT if move_vec.x > 0 else DIR_LEFT
            else:
                self.direction = DIR_DOWN if move_vec.y > 0 else DIR_UP
                
            # Speed parameters
            curr_speed = self.speed
            if self.is_running and self.stamina > 5:
                curr_speed *= PLAYER_RUN_MULTIPLIER
                # Consume stamina slowly when running
                self.stamina = max(0.0, self.stamina - 15.0 * self.game.dt)
                
            self.velocity = move_vec * curr_speed
        else:
            self.state = "idle"
            self.velocity.x = 0
            self.velocity.y = 0

    def update(self, dt: float) -> None:
        """Ticks recovery pools, updates animation frames, and resolves collisions."""
        # Read keyboard controls and inputs
        if self.state != "dead":
            self.handle_movement_input(self.game.input_handler)
            self.handle_skill_casts(self.game.input_handler)
            
            # Melee Attack check
            if self.game.input_handler.consume_action("attack"):
                self.perform_attack()
            # Roll check
            elif self.game.input_handler.consume_action("roll"):
                self.perform_roll()

        # 1. Update timers
        if self.action_timer > 0:
            self.action_timer -= dt
            if self.action_timer <= 0:
                if self.state == "dead":
                    # Trigger Game Over state in core loop
                    self.game.game_state = STATE_GAME_OVER
                else:
                    self.state = "idle"
                    self.velocity.x = 0
                    self.velocity.y = 0
                    
        if self.roll_cooldown_timer > 0:
            self.roll_cooldown_timer -= dt
            
        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer -= dt
            
        if self.i_frames_timer > 0:
            self.i_frames_timer -= dt
            if self.i_frames_timer <= 0:
                self.is_invincible = False

        # Update skill timers
        self.skill_manager.update(dt)

        # 2. Continuous Pool recovery (when not rolling/running)
        if self.state != "roll" and not (self.is_running and self.velocity.length_squared() > 0):
            # Regenerate stamina
            self.stamina = min(self.max_stamina, self.stamina + self.stamina_regen_rate * dt)
            
        # Always regenerate mana slowly
        self.mana = min(self.max_mana, self.mana + self.mana_regen_rate * dt)

        # 3. Apply Knockback impulse if present
        if self.knockback_duration > 0:
            self.knockback_duration -= dt
            self.velocity = self.knockback_vector
            if self.knockback_duration <= 0:
                self.knockback_vector = pygame.math.Vector2(0, 0)

        # 4. Process movement and collisions
        if self.velocity.length_squared() > 0 or self.knockback_duration > 0:
            from rpg.collision import CollisionSystem
            solid_rects = CollisionSystem.get_nearby_solids(self.hitbox, self.game.world_manager.current_map_grid, TILE_SIZE)
            
            # Move & resolve horizontal
            if self.state == "roll" and self.knockback_duration <= 0:
                # Rolling speed boost
                roll_vec = pygame.math.Vector2(0, 0)
                if self.direction == DIR_LEFT: roll_vec.x = -1
                elif self.direction == DIR_RIGHT: roll_vec.x = 1
                elif self.direction == DIR_UP: roll_vec.y = -1
                elif self.direction == DIR_DOWN: roll_vec.y = 1
                self.velocity = roll_vec * PLAYER_ROLL_SPEED
                
            self.pos.x += self.velocity.x * 60.0 * dt
            self.hitbox.centerx = int(self.pos.x)
            CollisionSystem.resolve_movement(self, solid_rects, 'x')
            
            # Move & resolve vertical
            self.pos.y += self.velocity.y * 60.0 * dt
            self.hitbox.centery = int(self.pos.y)
            CollisionSystem.resolve_movement(self, solid_rects, 'y')
            
            # Re-sync standard drawing rect with hitbox center
            self.rect.center = self.hitbox.center
            
            # Spawn footstep particle puffs
            if self.state == "walk" and int(self.frame_index) % 2 == 0:
                self.particles.create_dust_puff(self.rect.midbottom)

        # 5. Tick frames and render procedural graphics
        self.animate(dt)

    def animate(self, dt: float) -> None:
        """Increments frame indexes and selects corresponding procedural Surfaces."""
        # Detect state shifts to reset animation frames
        current_anim_key = self.state
        if self.prev_state != current_anim_key or self.prev_direction != self.direction:
            self.frame_index = 0.0
            self.prev_state = current_anim_key
            self.prev_direction = self.direction
            
        frames = entity_assets["player"][current_anim_key][self.direction]
        
        # Dynamic animation play speed
        anim_speed = 8.0
        if self.state == "walk":
            anim_speed = 12.0 if self.is_running else 8.0
        elif self.state == "attack":
            anim_speed = 16.0
        elif self.state == "roll":
            anim_speed = 12.0
            
        self.frame_index += anim_speed * dt
        self.image = frames[int(self.frame_index) % len(frames)]
        
        # Flash player red briefly if hurt and invincible
        if self.is_invincible and self.state != "roll":
            # Toggle alpha flicker
            if int(pygame.time.get_ticks() / 50) % 2 == 0:
                temp_image = self.image.copy()
                # Apply translucent red overlay
                temp_image.fill((255, 100, 100, 120), special_flags=pygame.BLEND_RGBA_MULT)
                self.image = temp_image
