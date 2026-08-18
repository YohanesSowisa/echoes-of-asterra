"""
Echoes of Asterra - Enemy AI System
Finite State Machine controlling enemy behaviors including patrolling, chasing, attacking,
retreating, and BehaviorTag-driven tactical behaviors (pack tactics, parry, kiting, berserk).
"""
import random
import pygame
from typing import Any

# AI States
AI_STATE_IDLE = "idle"
AI_STATE_PATROL = "patrol"
AI_STATE_CHASE = "chase"
AI_STATE_ATTACK = "attack"
AI_STATE_RETREAT = "retreat"
AI_STATE_DEAD = "dead"
AI_STATE_GUARD = "guard"
AI_STATE_KITE = "kite"

class EnemyAI:
    """
    Finite State Machine (FSM) attached to enemies.
    Determines paths, tracking, attack ranges, and returns home.
    Supports BehaviorTag-driven tactical behaviors from the balance system.
    """
    def __init__(
        self,
        home_pos: pygame.math.Vector2,
        vision_radius: float = 350.0,
        attack_radius: float = 52.0,
        tether_radius: float = 700.0,
        patrol_radius: float = 140.0
    ) -> None:
        self.state = AI_STATE_PATROL
        self.home_pos = pygame.math.Vector2(home_pos)
        self.vision_radius = vision_radius
        self.attack_radius = attack_radius
        self.tether_radius = tether_radius
        self.patrol_radius = patrol_radius

        # Patrol coordinates
        self.patrol_target: pygame.math.Vector2 = pygame.math.Vector2(home_pos)
        self.patrol_timer = 0.0
        self.patrol_wait_time = 2.0  # seconds to stay idle at patrol node

        # Chase and attack parameters
        self.chase_cooldown = 0.0

        # Behavior tag tracking
        self._attack_cycle_count: int = 0  # For DEFENSIVE_PARRY: every 3rd cycle
        self._kite_strafe_dir: int = 1     # For RANGED_KITE: lateral strafe direction

    def _get_effective_vision(self, enemy: Any) -> float:
        """Returns vision radius adjusted by weather fog modifier."""
        base = self.vision_radius
        if hasattr(enemy, "game") and enemy.game and hasattr(enemy.game, "weather"):
            mods = enemy.game.weather.get_combat_modifiers()
            base *= mods.get("vision_mult", 1.0)
        return base

    def _count_nearby_pack(self, enemy: Any, radius: float = 200.0) -> int:
        """Counts nearby allies of the same type within radius (for PACK_TACTICS)."""
        count = 0
        if not hasattr(enemy, "game") or not enemy.game:
            return 0
        for other in enemy.game.enemies:
            if other is enemy or other.hp <= 0:
                continue
            if other.asset_key == enemy.asset_key:
                dist = (other.pos - enemy.pos).length()
                if dist <= radius:
                    count += 1
        return count

    def update(self, enemy: Any, player: Any, dt: float) -> None:
        """
        Updates AI state machine, sets enemy velocity/move direction,
        and triggers combat actions with BehaviorTag awareness.
        """
        from rpg.balance import BehaviorTag

        if enemy.hp <= 0:
            self.state = AI_STATE_DEAD
            enemy.move_dir = pygame.math.Vector2(0, 0)
            return

        # Calculate distances
        to_player = player.pos - enemy.pos
        dist_to_player = to_player.length()
        
        to_home = self.home_pos - enemy.pos
        dist_to_home = to_home.length()

        # Update action cooldowns
        if self.patrol_timer > 0:
            self.patrol_timer -= dt

        # Get behavior tags
        behaviors = getattr(enemy, "behaviors", [])
        effective_vision = self._get_effective_vision(enemy)

        # --- BEHAVIOR: RETREAT_LOW_HP & NEMESIS CRAVEN TRAIT ---
        is_craven = "Craven" in getattr(enemy, "traits", [])
        retreat_threshold = 0.35 if is_craven else 0.25
        if BehaviorTag.RETREAT_LOW_HP in behaviors or is_craven:
            if enemy.hp > 0 and enemy.hp / max(1, enemy.max_hp) < retreat_threshold:
                if self.state not in [AI_STATE_RETREAT, AI_STATE_DEAD]:
                    self.state = AI_STATE_RETREAT
                    enemy.is_running = True

        # --- NEMESIS: BLOODTHIRSTY TRAIT ---
        if "Bloodthirsty" in getattr(enemy, "traits", []) and not getattr(enemy, "berserk_active", False):
            if enemy.hp > 0 and enemy.hp / max(1, enemy.max_hp) < 0.50:
                enemy.berserk_active = True
                enemy.atk = int(enemy.atk * 1.35)
                enemy.speed *= 1.20
                enemy.attack_cooldown = max(0.3, enemy.attack_cooldown * 0.65)

        # --- State transitions ---
        # Enemy Recognition: Player titles trigger fear & hesitation
        if hasattr(enemy, "game") and enemy.game and hasattr(enemy.game, "reputation_manager"):
            rep_mgr = enemy.game.reputation_manager
            if (rep_mgr.active_title in ["Scourge of Bandits", "Greed Challenger"] or rep_mgr.get_global_tier() in ["Hero", "Legend"]) and dist_to_player <= effective_vision * 0.7:
                if random.random() < 0.15:
                    self.state = AI_STATE_RETREAT

        if dist_to_home > self.tether_radius:
            # Chased too far, force retreat back to home spawn
            self.state = AI_STATE_RETREAT
        elif self.state == AI_STATE_RETREAT:
            if dist_to_home < 25.0:
                # If enemy successfully escaped after being damaged, emit enemy_escaped event
                if getattr(enemy, "has_been_hit", False) and enemy.hp / max(1, enemy.max_hp) < 0.40:
                    if hasattr(enemy, "game") and enemy.game and hasattr(enemy.game, "event_bus"):
                        current_map = getattr(enemy.game.world_manager, "current_map_name", "forest") if hasattr(enemy.game, "world_manager") else "forest"
                        enemy.game.event_bus.emit(
                            "enemy_escaped",
                            enemy=enemy,
                            enemy_name=getattr(enemy, "name", "Enemy"),
                            enemy_key=getattr(enemy, "enemy_key", "bandit"),
                            map_name=current_map
                        )
                    enemy.has_been_hit = False

                self.state = AI_STATE_PATROL
                self.patrol_target = pygame.math.Vector2(self.home_pos)
        elif self.state == AI_STATE_GUARD:
            # Guard state: handled in execution below
            pass
        elif self.state == AI_STATE_KITE:
            # Kite state: handled in execution below
            pass
        elif dist_to_player <= self.attack_radius:
            # --- BEHAVIOR: RANGED_KITE overrides close-range attack ---
            if BehaviorTag.RANGED_KITE in behaviors:
                self.state = AI_STATE_KITE
            else:
                self.state = AI_STATE_ATTACK
        elif dist_to_player <= effective_vision:
            # --- BEHAVIOR: RANGED_KITE maintains distance ---
            if BehaviorTag.RANGED_KITE in behaviors and dist_to_player < 150.0:
                self.state = AI_STATE_KITE
            else:
                self.state = AI_STATE_CHASE
        else:
            if self.state in [AI_STATE_CHASE, AI_STATE_ATTACK, AI_STATE_KITE]:
                # Lost track of player, return to home/patrol
                self.state = AI_STATE_RETREAT

        # --- State execution ---
        if self.state == AI_STATE_IDLE:
            enemy.move_dir = pygame.math.Vector2(0, 0)
            if self.patrol_timer <= 0:
                self._choose_new_patrol(enemy)
                
        elif self.state == AI_STATE_PATROL:
            to_patrol = self.patrol_target - enemy.pos
            dist_to_patrol = to_patrol.length()
            
            if dist_to_patrol < 8.0:
                # Arrived at patrol destination, wait a bit
                self.state = AI_STATE_IDLE
                self.patrol_timer = random.uniform(1.0, 3.0)
                enemy.move_dir = pygame.math.Vector2(0, 0)
            else:
                enemy.move_dir = to_patrol.normalize()
                
        elif self.state == AI_STATE_CHASE:
            # Run towards player via NavigationService A* pathing if available
            nav_service = getattr(getattr(getattr(enemy, "game", None), "services", None), "navigation", None)
            if nav_service:
                waypoints = nav_service.find_path(
                    (enemy.pos.x, enemy.pos.y),
                    (player.pos.x, player.pos.y)
                )
                if waypoints:
                    next_wp = pygame.math.Vector2(waypoints[0])
                    to_wp = next_wp - enemy.pos
                    if to_wp.length_squared() > 4.0:
                        enemy.move_dir = to_wp.normalize()
                    else:
                        enemy.move_dir = to_player.normalize() if to_player.length_squared() > 0 else pygame.math.Vector2(0, 0)
                else:
                    enemy.move_dir = to_player.normalize() if to_player.length_squared() > 0 else pygame.math.Vector2(0, 0)
            else:
                enemy.move_dir = to_player.normalize() if to_player.length_squared() > 0 else pygame.math.Vector2(0, 0)
            enemy.is_running = True

            
        elif self.state == AI_STATE_ATTACK:
            # Align facing direction with player
            if abs(to_player.x) > abs(to_player.y):
                enemy.direction = "right" if to_player.x > 0 else "left"
            else:
                enemy.direction = "down" if to_player.y > 0 else "up"

            # Continuously press forward until touching contact distance (18px)
            if dist_to_player > 18.0:
                enemy.move_dir = to_player.normalize() if to_player.length_squared() > 0 else pygame.math.Vector2(0, 0)
                enemy.is_running = True
            else:
                enemy.move_dir = pygame.math.Vector2(0, 0)
                enemy.is_running = False
                
            # Perform attack if off cooldown
            if enemy.attack_timer <= 0:
                # --- BEHAVIOR: DEFENSIVE_PARRY — enter guard every 3rd attack ---
                if BehaviorTag.DEFENSIVE_PARRY in behaviors:
                    self._attack_cycle_count += 1
                    if self._attack_cycle_count >= 3:
                        self._attack_cycle_count = 0
                        self.state = AI_STATE_GUARD
                        enemy.guard_state = True
                        enemy.guard_cooldown = 1.2  # Guard stance duration
                        enemy.move_dir = pygame.math.Vector2(0, 0)
                        from rpg.combat import DamageNumber
                        DamageNumber(enemy.rect.center, "GUARD!", (200, 200, 255), [enemy.game.ui_sprites], size=14)
                        return

                # --- BEHAVIOR: PACK_TACTICS — stagger attacks with pack ---
                if BehaviorTag.PACK_TACTICS in behaviors:
                    pack_count = self._count_nearby_pack(enemy)
                    if pack_count >= 1:
                        # Stagger: only attack on alternating frames to avoid sync
                        if random.random() < 0.4:
                            enemy.attack_timer = 0.3  # Brief delay to desync
                            return

                enemy.perform_attack()

        elif self.state == AI_STATE_GUARD:
            # --- DEFENSIVE_PARRY: Guard stance execution ---
            enemy.move_dir = pygame.math.Vector2(0, 0)
            enemy.guard_state = True

            if enemy.guard_cooldown <= 0:
                enemy.guard_state = False
                self.state = AI_STATE_ATTACK
                # Counterattack after guard ends
                if dist_to_player <= self.attack_radius * 1.5:
                    enemy.attack_timer = 0.0
                    enemy.perform_attack()

        elif self.state == AI_STATE_KITE:
            # --- RANGED_KITE: Maintain 150-250px distance, strafe laterally ---
            ideal_min = 150.0
            ideal_max = 250.0

            if abs(to_player.x) > abs(to_player.y):
                enemy.direction = "right" if to_player.x > 0 else "left"
            else:
                enemy.direction = "down" if to_player.y > 0 else "up"

            if dist_to_player < ideal_min:
                # Too close — retreat away from player
                if to_player.length_squared() > 0:
                    enemy.move_dir = -to_player.normalize()
                enemy.is_running = True
            elif dist_to_player > ideal_max:
                # Too far — approach
                if to_player.length_squared() > 0:
                    enemy.move_dir = to_player.normalize()
                enemy.is_running = False
            else:
                # In kite sweet spot — strafe laterally
                if to_player.length_squared() > 0:
                    perp = pygame.math.Vector2(-to_player.y, to_player.x).normalize()
                    enemy.move_dir = perp * self._kite_strafe_dir
                    # Randomly flip strafe direction
                    if random.random() < 0.02:
                        self._kite_strafe_dir *= -1

            # Ranged attack if off cooldown
            if enemy.attack_timer <= 0:
                enemy.perform_attack()

        elif self.state == AI_STATE_RETREAT:
            # Run back to home spawn point
            enemy.move_dir = to_home.normalize() if to_home.length_squared() > 0 else pygame.math.Vector2(0, 0)
            enemy.is_running = True

    def _choose_new_patrol(self, enemy: Any) -> None:
        """Selects a random coordinate within patrol radius of home to walk to."""
        angle = random.uniform(0, 2.0 * 3.14159)
        dist = random.uniform(20.0, self.patrol_radius)
        
        self.patrol_target.x = self.home_pos.x + int(dist * math_cos(angle))
        self.patrol_target.y = self.home_pos.y + int(dist * math_sin(angle))
        self.state = AI_STATE_PATROL

# Inline math fast calculations
def math_sin(rad: float) -> float:
    return math_lookup(rad, True)

def math_cos(rad: float) -> float:
    return math_lookup(rad, False)

def math_lookup(rad: float, is_sin: bool) -> float:
    import math
    return math.sin(rad) if is_sin else math.cos(rad)
