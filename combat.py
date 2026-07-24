"""
Echoes of Asterra - Combat System
Manages hit registration, damage calculations, knockback vectors, and floating text popups.
"""
import random
import pygame
from typing import Tuple, Any, List
from rpg.sprite import BaseSprite
from rpg.constants import COLOR_WHITE, COLOR_YELLOW, COLOR_RED, COLOR_CYAN

class DamageNumber(BaseSprite):
    """
    Floating damage number text. Rises slightly and fades out.
    """
    def __init__(self, pos: Tuple[float, float], text: str, color: Tuple[int, int, int], groups: List[pygame.sprite.Group], size: int = 20) -> None:
        super().__init__(pos, groups, layer=3)  # High layer to draw above characters
        self.text = text
        self.color = color
        self.font = pygame.font.SysFont("Arial", size, bold=True)
        self.alpha = 255
        self.lifetime = 0.6  # seconds
        self.timer = self.lifetime
        self.velocity = pygame.math.Vector2(random.uniform(-30, 30), -80)  # Float up and slightly random horizontal
        self.clean_image = pygame.Surface((10, 10), pygame.SRCALPHA)
        
        self.render_image()

    def render_image(self) -> None:
        """Renders the text with transparent background."""
        text_surf = self.font.render(self.text, True, self.color)
        # Add shadow
        shadow_surf = self.font.render(self.text, True, (0, 0, 0))
        
        self.clean_image = pygame.Surface((text_surf.get_width() + 4, text_surf.get_height() + 4), pygame.SRCALPHA)
        self.clean_image.blit(shadow_surf, (2, 2))
        self.clean_image.blit(text_surf, (1, 1))
        
        self.image = self.clean_image.copy()
        self.rect = self.image.get_rect(center=self.pos)

    def update(self, dt: float) -> None:
        """Updates position, fades alpha, and kills sprite when lifetime ends."""
        self.timer -= dt
        if self.timer <= 0:
            self.kill()
            return
            
        # Float upwards
        self.pos += self.velocity * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        
        # Fade out
        self.alpha = max(0, min(255, int((self.timer / self.lifetime) * 255)))
        # Apply alpha to clean original image copy
        temp_image = self.clean_image.copy()
        temp_image.fill((255, 255, 255, self.alpha), special_flags=pygame.BLEND_RGBA_MULT)
        self.image = temp_image

class CombatSystem:
    """
    Coordinates combat collisions and damage resolutions.
    """
    @staticmethod
    def calculate_damage(attacker: Any, defender: Any, is_magic: bool = False, armor_pierce: float = 0.0, damage_multiplier: float = 1.0) -> Tuple[int, bool]:
        """
        Calculates damage based on attacker's ATK/Magic and defender's Defense.
        Applies armor piercing and damage multipliers.
        Returns: (damage_amount, is_critical)
        """
        is_crit = False
        
        if is_magic:
            # Magic damage ignores 60% of physical defense
            base_dmg = attacker.magic * 2
            defense_reduc = defender.defense * 0.4
        else:
            base_dmg = attacker.atk
            defense_reduc = defender.defense * max(0.0, 1.0 - armor_pierce)
            
        base_dmg = int(base_dmg * damage_multiplier)

        # Critical Hit check
        crit_chance = getattr(attacker, "crit_chance", 5)
        if random.randint(1, 100) <= crit_chance:
            is_crit = True
            base_dmg = int(base_dmg * 1.5)
            
        # Compute final damage (minimum 1)
        final_dmg = max(1, int(base_dmg - defense_reduc))
        
        # Add slight variance (+/- 15%)
        variance = random.uniform(0.85, 1.15)
        final_dmg = max(1, int(final_dmg * variance))
        
        return final_dmg, is_crit

    @staticmethod
    def execute_hit(
        attacker: Any,
        defender: Any,
        ui_group: List[pygame.sprite.Group],
        is_magic: bool = False,
        speed_modifier: float = 1.0,
        armor_pierce: float = 0.0,
        damage_multiplier: float = 1.0,
        stun_duration: float = 0.0
    ) -> bool:
        """
        Executes a hit from attacker to defender.
        Applies damage, knockback, armor piercing, stuns, triggers screen shake, flash effects, particles, and floating text.
        Returns True if hit was successfully registered, False if defender was invincible.
        """
        # If defender is in i-frames, hit fails
        if getattr(defender, "is_invincible", False):
            return False
            
        # Calculate damage
        dmg, is_crit = CombatSystem.calculate_damage(attacker, defender, is_magic, armor_pierce, damage_multiplier)
        
        # Apply Shield Skill absorption (if active)
        if hasattr(defender, "has_shield_active") and defender.has_shield_active:
            defender.has_shield_active = False  # Pop shield
            # Spawn block floating text
            DamageNumber(defender.rect.center, "SHIELD BLOCK", COLOR_CYAN, ui_group, size=16)
            defender.trigger_invincibility(300) # Short I-frames
            # Play shield hit sound
            defender.sound_manager.play_sound("click")
            return True

        # Apply blocking damage reduction (if defender is active player blocking)
        if getattr(defender, "is_blocking", False):
            # Block reduces damage by 75%
            dmg = max(1, int(dmg * 0.25))
            # Spawn block floating text
            DamageNumber(defender.rect.center, "BLOCKED", COLOR_CYAN, ui_group, size=16)
            # Add sparks particles
            defender.particles.create_block_sparks(defender.rect.center)
            # Trigger short I-frames
            defender.trigger_invincibility(200)
            # Apply light knockback
            knockback_strength = 3.0
            sound_name = "click"
        else:
            # Standard unblocked hit
            sound_name = "hit"
            knockback_strength = 6.0 * speed_modifier
            
        # Apply Stun Effect if weapon class specifies stun
        if stun_duration > 0 and hasattr(defender, "apply_slow_effect"):
            defender.apply_slow_effect(stun_duration)
            DamageNumber(defender.rect.center, "STUNNED!", COLOR_YELLOW, ui_group, size=14)
            
        # Deduct Health
        defender.take_damage(dmg)
        
        # Play combat sound
        attacker.sound_manager.play_sound(sound_name)
        
        # Spawn Damage text popup
        dmg_str = str(dmg)
        txt_color = COLOR_YELLOW if is_crit else (COLOR_RED if attacker == player_attacker(attacker) else COLOR_WHITE)
        DamageNumber(defender.rect.center, dmg_str, txt_color, ui_group, size=24 if is_crit else 20)

        # Trigger knockback vector
        if knockback_strength > 0:
            diff_vec = pygame.math.Vector2(defender.rect.center) - pygame.math.Vector2(attacker.rect.center)
            if diff_vec.length_squared() > 0:
                defender.knockback_vector = diff_vec.normalize() * knockback_strength
                defender.knockback_duration = 0.15 # seconds
                
        # Trigger hit-stop effect in camera / graphics (shakes, pauses)
        if hasattr(attacker, "game"):
            attacker.game.trigger_hit_stop(0.08)  # Stop frame updating briefly
            
        if is_crit and hasattr(attacker, "game"):
            attacker.game.camera.trigger_shake(8.0, 150) # Big screen shake
        elif hasattr(attacker, "game"):
            attacker.game.camera.trigger_shake(3.0, 100) # Minor shake

        # Spawn blood / strike particles
        defender.particles.create_hit_blood(defender.rect.center, -defender.knockback_vector if hasattr(defender, "knockback_vector") else None)

        # Trigger defender hurt state/I-frames
        defender.trigger_invincibility(500) # 0.5 seconds default
        if hasattr(defender, "state") and getattr(defender, "hp", 1) > 0:
            defender.state = "hurt"
            
        return True

def player_attacker(attacker: Any) -> Any:
    """Helper to detect if attacker is the Player class to determine text colors."""
    if hasattr(attacker, "__class__") and attacker.__class__.__name__ == "Player":
        return attacker
    return None

class Projectile(BaseSprite):
    """
    Ranged magic or physical projectiles that travel in a straight line,
    triggering damage and visual impact particles upon impact with walls or entities.
    """
    def __init__(self, pos: Tuple[float, float], direction: str, speed: float, damage: int, is_magic: bool, proj_type: str, groups: List[pygame.sprite.Group], attacker: Any) -> None:
        super().__init__(pos, groups, layer=2)
        self.direction = direction
        self.speed = speed
        self.damage = damage
        self.is_magic = is_magic
        self.proj_type = proj_type
        self.attacker = attacker
        self.game = attacker.game
        
        # Select and rotate frame assets based on direction
        from rpg.animation import projectile_assets
        self.frames = projectile_assets.get(proj_type, [])
        self.frame_index = 0.0
        
        # Calculate velocity
        self.velocity = pygame.math.Vector2(0, 0)
        if direction == "up": self.velocity.y = -1
        elif direction == "down": self.velocity.y = 1
        elif direction == "left": self.velocity.x = -1
        elif direction == "right": self.velocity.x = 1
        
        if self.velocity.length_squared() > 0:
            self.velocity = self.velocity.normalize() * speed
        else:
            self.velocity = pygame.math.Vector2(speed, 0) # Fallback right
            
        # Build initial image and rotated cache
        self.image = self.frames[0] if self.frames else pygame.Surface((16, 16))
        self._rotate_image()
        
        # Combat hitbox
        self.hitbox = self.image.get_rect(center=pos)
        self.rect = self.hitbox.copy()

    def _rotate_image(self) -> None:
        """Rotates the frame image to face the moving direction."""
        base_img = self.frames[int(self.frame_index) % len(self.frames)] if self.frames else self.image
        
        # Direction degrees offset
        deg = 0
        if self.direction == "up": deg = 90
        elif self.direction == "left": deg = 180
        elif self.direction == "down": deg = 270
        
        if deg != 0:
            self.image = pygame.transform.rotate(base_img, deg)
        else:
            self.image = base_img

    def update(self, dt: float) -> None:
        """Moves projectile, updates trail particles, and resolves collisions."""
        # 1. Update position
        self.pos += self.velocity * dt
        self.hitbox.center = (int(self.pos.x), int(self.pos.y))
        self.rect.center = self.hitbox.center
        
        # 2. Spawn trail particles
        if self.proj_type == "fireball":
            self.game.particles.create_sparkle(self.hitbox.center, (240, 80, 20))
        elif self.proj_type == "ice_spike":
            self.game.particles.create_sparkle(self.hitbox.center, (60, 210, 240))
        else:
            self.game.particles.create_sparkle(self.hitbox.center, (150, 60, 220))

        # 3. Check tile collision
        from rpg.collision import CollisionSystem
        solid_rects = CollisionSystem.get_nearby_solids(self.hitbox, self.game.world_manager.current_map_grid, 48)
        if CollisionSystem.check_tile_collision(self.hitbox, solid_rects):
            # Destroy and play collision particle puff
            self.game.particles.create_block_sparks(self.hitbox.center)
            self.kill()
            return
            
        # 4. Check entity collision
        # Detect if attacker is player
        is_player_attacker = (self.attacker == self.game.player)
        
        if is_player_attacker:
            # Check hits on enemies
            for enemy in self.game.enemies:
                if enemy.hp > 0 and self.hitbox.colliderect(enemy.hitbox):
                    # Execute hit
                    if CombatSystem.execute_hit(self.attacker, enemy, [self.game.ui_sprites], is_magic=self.is_magic):
                        # Apply slow effect if ice spike
                        if self.proj_type == "ice_spike" and hasattr(enemy, "apply_slow_effect"):
                            enemy.apply_slow_effect(2.5)  # 2.5s slow
                        self.kill()
                        return
        else:
            # Check hits on player
            player = self.game.player
            if player.hp > 0 and self.hitbox.colliderect(player.hitbox):
                if CombatSystem.execute_hit(self.attacker, player, [self.game.ui_sprites], is_magic=self.is_magic):
                    self.kill()
                    return

        # 5. Rotate animation
        if self.frames:
            self.frame_index += 10 * dt
            self._rotate_image()

