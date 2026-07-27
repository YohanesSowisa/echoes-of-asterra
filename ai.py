"""
Echoes of Asterra - Enemy AI System
Finite State Machine controlling enemy behaviors including patrolling, chasing, attacking, and retreating.
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

class EnemyAI:
    """
    Finite State Machine (FSM) attached to enemies.
    Determines paths, tracking, attack ranges, and returns home.
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

    def update(self, enemy: Any, player: Any, dt: float) -> None:
        """
        Updates AI state machine, sets enemy velocity/move direction,
        and triggers combat actions.
        """
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

        # State transitions
        # Enemy Recognition: Player titles (e.g. Scourge of Bandits) trigger fear & hesitation
        if hasattr(enemy, "game") and enemy.game and hasattr(enemy.game, "reputation_manager"):
            rep_mgr = enemy.game.reputation_manager
            if (rep_mgr.active_title in ["Scourge of Bandits", "Greed Challenger"] or rep_mgr.get_global_tier() in ["Hero", "Legend"]) and dist_to_player <= self.vision_radius * 0.7:
                if random.random() < 0.15:
                    self.state = AI_STATE_RETREAT

        if dist_to_home > self.tether_radius:
            # Chased too far, force retreat back to home spawn
            self.state = AI_STATE_RETREAT
        elif self.state == AI_STATE_RETREAT:
            if dist_to_home < 20.0:
                self.state = AI_STATE_PATROL
                self.patrol_target = pygame.math.Vector2(self.home_pos)
        elif dist_to_player <= self.attack_radius:
            self.state = AI_STATE_ATTACK
        elif dist_to_player <= self.vision_radius:
            self.state = AI_STATE_CHASE
        else:
            if self.state in [AI_STATE_CHASE, AI_STATE_ATTACK]:
                # Lost track of player, return to home/patrol
                self.state = AI_STATE_RETREAT

        # State execution
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
            # Stand and attack
            enemy.move_dir = pygame.math.Vector2(0, 0)
            enemy.is_running = False
            
            # Align face direction with player
            if abs(to_player.x) > abs(to_player.y):
                enemy.direction = "right" if to_player.x > 0 else "left"
            else:
                enemy.direction = "down" if to_player.y > 0 else "up"
                
            # Perform attack if off cooldown
            if enemy.attack_timer <= 0:
                enemy.perform_attack()
                
        elif self.state == AI_STATE_RETREAT:
            # Run back to home spawn point
            enemy.move_dir = to_home.normalize()
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
