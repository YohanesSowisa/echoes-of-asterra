"""
Echoes of Asterra - Environmental Hazard Tiles
Implements interactive hazard tiles for procedural dungeons: spike traps, lava pools,
ice patches, and poison pools. Both player AND enemies can trigger them.
"""
import pygame
import math
from typing import Tuple, List, Any, Dict
from rpg.sprite import BaseSprite
from rpg.settings import TILE_SIZE
from rpg.combat import DamageNumber


class HazardTile(BaseSprite):
    """
    Base hazard tile that deals damage or applies status effects on contact.
    Supports cooldown timers, particle effects, and entity-type awareness.
    """
    def __init__(
        self,
        pos: Tuple[float, float],
        groups: List[pygame.sprite.Group],
        hazard_type: str = "spike_trap",
        damage: int = 15,
        cooldown: float = 3.0,
        status_element: str = "",
        status_duration: float = 0.0,
    ) -> None:
        super().__init__(pos, groups, layer=0)
        self.hazard_type = hazard_type
        self.damage = damage
        self.cooldown = cooldown
        self.status_element = status_element
        self.status_duration = status_duration
        self.game: Any = None

        # Cooldown tracking per entity (so each entity gets hit independently)
        self._entity_cooldowns: Dict[int, float] = {}

        # Build visual
        self.image = self._build_image()
        self.rect = self.image.get_rect(topleft=(int(pos[0]), int(pos[1])))
        self.hitbox = self.rect.inflate(-4, -4)

    def _build_image(self) -> pygame.Surface:
        """Generates a procedural hazard tile surface based on type."""
        surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)

        if self.hazard_type == "spike_trap":
            # Gray pressure plate with spike hints
            surf.fill((60, 60, 65, 200))
            pygame.draw.rect(surf, (90, 90, 95), (4, 4, TILE_SIZE - 8, TILE_SIZE - 8), 1)
            # Spike triangles
            for ox in [8, 16, 24]:
                pygame.draw.polygon(surf, (180, 180, 190), [
                    (ox, TILE_SIZE - 6), (ox - 3, TILE_SIZE - 2), (ox + 3, TILE_SIZE - 2)
                ])

        elif self.hazard_type == "lava_pool":
            # Orange-red molten pool
            surf.fill((180, 50, 10, 180))
            pygame.draw.ellipse(surf, (255, 100, 20, 200), (2, 2, TILE_SIZE - 4, TILE_SIZE - 4))
            pygame.draw.ellipse(surf, (255, 180, 40, 140), (8, 8, TILE_SIZE - 16, TILE_SIZE - 16))

        elif self.hazard_type == "ice_patch":
            # Pale blue-white ice
            surf.fill((160, 210, 255, 150))
            pygame.draw.ellipse(surf, (200, 235, 255, 180), (2, 2, TILE_SIZE - 4, TILE_SIZE - 4))
            # Frost sparkle dots
            for ox, oy in [(6, 6), (20, 10), (12, 22), (26, 26)]:
                pygame.draw.circle(surf, (255, 255, 255, 220), (ox, oy), 2)

        elif self.hazard_type == "poison_pool":
            # Green toxic pool
            surf.fill((40, 100, 30, 160))
            pygame.draw.ellipse(surf, (80, 200, 50, 200), (2, 2, TILE_SIZE - 4, TILE_SIZE - 4))
            pygame.draw.ellipse(surf, (120, 240, 80, 140), (8, 8, TILE_SIZE - 16, TILE_SIZE - 16))

        return surf

    def _can_trigger(self, entity_id: int) -> bool:
        """Checks if cooldown has expired for a given entity."""
        return self._entity_cooldowns.get(entity_id, 0.0) <= 0.0

    def _trigger_cooldown(self, entity_id: int) -> None:
        """Starts cooldown for a specific entity."""
        self._entity_cooldowns[entity_id] = self.cooldown

    def update(self, dt: float) -> None:
        """Ticks cooldowns and checks collisions with player and enemies."""
        # Tick per-entity cooldowns
        expired = []
        for eid, remaining in self._entity_cooldowns.items():
            self._entity_cooldowns[eid] = remaining - dt
            if self._entity_cooldowns[eid] <= 0:
                expired.append(eid)
        for eid in expired:
            del self._entity_cooldowns[eid]

        if not self.game:
            return

        # Check player collision
        player = self.game.player
        if player.hp > 0 and self.hitbox.colliderect(player.hitbox):
            if self._can_trigger(id(player)):
                self._apply_to_entity(player, is_player=True)
                self._trigger_cooldown(id(player))

        # Check enemy collisions
        for enemy in self.game.enemies:
            if enemy.hp > 0 and self.hitbox.colliderect(enemy.hitbox):
                if self._can_trigger(id(enemy)):
                    self._apply_to_entity(enemy, is_player=False)
                    self._trigger_cooldown(id(enemy))

    def _apply_to_entity(self, entity: Any, is_player: bool) -> None:
        """Applies hazard effects to an entity."""
        # Apply damage
        if self.damage > 0:
            entity.take_damage(self.damage)
            color = (255, 80, 40) if self.hazard_type in ["lava_pool", "spike_trap"] else (100, 240, 80)
            label = self.hazard_type.replace("_", " ").title()
            DamageNumber(entity.rect.center, f"{label}! -{self.damage}", color, [self.game.ui_sprites], size=14)

        # Apply elemental status
        if self.status_element and self.status_duration > 0 and hasattr(entity, "apply_elemental_status"):
            entity.apply_elemental_status(self.status_element, self.status_duration)

        # Ice patch: apply movement speed boost (slide effect)
        if self.hazard_type == "ice_patch" and hasattr(entity, "apply_slow_effect"):
            entity.apply_slow_effect(1.0)  # Uses slow system for slide feel

        # Spawn particles
        if hasattr(self.game, "particles"):
            if self.hazard_type == "spike_trap":
                self.game.particles.create_hit_blood(entity.rect.center, None)
            elif self.hazard_type == "lava_pool":
                self.game.particles.create_sparkle(entity.rect.center, (255, 100, 20))
            elif self.hazard_type == "poison_pool":
                self.game.particles.create_sparkle(entity.rect.center, (80, 240, 50))


# --- HAZARD DEFINITIONS FOR DUNGEON THEMES ---

THEME_HAZARDS: Dict[str, List[Dict[str, Any]]] = {
    "crypt": [
        {"type": "spike_trap", "damage": 15, "cooldown": 3.0, "element": "", "duration": 0.0, "density": 0.08},
        {"type": "poison_pool", "damage": 8, "cooldown": 2.0, "element": "poison", "duration": 4.0, "density": 0.05},
    ],
    "cave": [
        {"type": "spike_trap", "damage": 12, "cooldown": 3.0, "element": "", "duration": 0.0, "density": 0.06},
        {"type": "poison_pool", "damage": 10, "cooldown": 2.5, "element": "poison", "duration": 3.5, "density": 0.04},
    ],
    "temple": [
        {"type": "spike_trap", "damage": 18, "cooldown": 2.5, "element": "", "duration": 0.0, "density": 0.10},
    ],
    "ice": [
        {"type": "ice_patch", "damage": 0, "cooldown": 1.0, "element": "ice", "duration": 2.0, "density": 0.12},
        {"type": "spike_trap", "damage": 12, "cooldown": 3.0, "element": "", "duration": 0.0, "density": 0.04},
    ],
    "volcano": [
        {"type": "lava_pool", "damage": 20, "cooldown": 1.5, "element": "fire", "duration": 3.0, "density": 0.10},
        {"type": "spike_trap", "damage": 15, "cooldown": 3.0, "element": "", "duration": 0.0, "density": 0.03},
    ],
}
