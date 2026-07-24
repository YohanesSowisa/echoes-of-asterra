"""
Echoes of Asterra - Diverse Caravan Simulation & Road Pathfinding System
Simulates 5 distinct types of physical traveling caravans (Merchant, Military Patrol, Refugee,
Religious Pilgrims, Tax Caravan) moving along dirt trade routes between maps.
Caravan arrivals and destructions trigger cascading economic and safety events.
"""
import random
import pygame
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional
from rpg.sprite import BaseSprite
from rpg.settings import TILE_SIZE, GRID_WIDTH, GRID_HEIGHT
from rpg.events import EventBus

CARAVAN_MERCHANT = "merchant"
CARAVAN_MILITARY = "military"
CARAVAN_REFUGEE = "refugee"
CARAVAN_PILGRIM = "pilgrim"
CARAVAN_TAX = "tax"

@dataclass
class CaravanRoute:
    """Path connecting maps."""
    origin_map: str
    target_map: str
    waypoints: List[Tuple[float, float]]

class CaravanEntity(BaseSprite):
    """Physical sprite representing a traveling caravan on active map."""
    def __init__(self, c_type: str, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        self._layer = 1
        super().__init__(pos, groups, layer=1)
        self.caravan_type = c_type
        self.hp = 100 if c_type == CARAVAN_MILITARY else 40
        self.max_hp = self.hp
        self.speed = 50.0 if c_type == CARAVAN_MILITARY else 35.0
        
        # Procedural sprite image rendering
        self.image = pygame.Surface((28, 28), pygame.SRCALPHA)
        self._draw_caravan_texture()
        self.rect = self.image.get_rect(center=(int(pos[0]), int(pos[1])))
        self.hitbox = self.rect.copy()

    def _draw_caravan_texture(self) -> None:
        """Draws distinct visual badge per caravan type."""
        color_map = {
            CARAVAN_MERCHANT: (220, 180, 50),   # Gold/Yellow
            CARAVAN_MILITARY: (70, 130, 220),   # Knight Blue
            CARAVAN_REFUGEE: (160, 120, 90),    # Earth Brown
            CARAVAN_PILGRIM: (200, 230, 240),   # White/Cyan
            CARAVAN_TAX: (220, 80, 80)          # Crimson Red
        }
        c = color_map.get(self.caravan_type, (200, 200, 200))
        # Draw wooden cart / pack mule frame
        pygame.draw.rect(self.image, c, (2, 4, 24, 20), border_radius=4)
        pygame.draw.rect(self.image, (40, 30, 20), (2, 4, 24, 20), 2, border_radius=4)
        # Wheels
        pygame.draw.circle(self.image, (30, 30, 30), (6, 22), 4)
        pygame.draw.circle(self.image, (30, 30, 30), (22, 22), 4)

class CaravanManager:
    """
    Spawns, simulates, and updates physical traveling caravans across Asterra.
    """
    def __init__(self) -> None:
        self.event_bus: Optional[EventBus] = None
        self.active_caravans: List[Dict[str, Any]] = []
        self.spawn_timer = 0.0

    def register_event_listeners(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        event_bus.subscribe("day_changed", self._on_day_changed)

    def _on_day_changed(self, **kwargs) -> None:
        """Spawns 1-2 new caravans daily based on world state."""
        types = [CARAVAN_MERCHANT, CARAVAN_MILITARY, CARAVAN_REFUGEE, CARAVAN_PILGRIM, CARAVAN_TAX]
        selected_type = random.choice(types)
        self.spawn_caravan(selected_type)

    def spawn_caravan(self, c_type: str = CARAVAN_MERCHANT) -> None:
        """Instantiates a new caravan route."""
        routes = [
            ("village", "forest"),
            ("forest", "ruins"),
            ("village", "cave"),
            ("forest", "lake")
        ]
        origin, target = random.choice(routes)
        caravan_data = {
            "id": random.randint(1000, 9999),
            "type": c_type,
            "origin": origin,
            "target": target,
            "current_map": origin,
            "progress": 0.0,
            "cargo": "goods" if c_type == CARAVAN_MERCHANT else ("gold" if c_type == CARAVAN_TAX else "supplies"),
            "pos": (GRID_WIDTH // 2 * TILE_SIZE, GRID_HEIGHT // 2 * TILE_SIZE)
        }
        self.active_caravans.append(caravan_data)
        if self.event_bus:
            self.event_bus.emit("caravan_spawned", caravan_type=c_type, origin=origin, target=target)

    def update(self, dt: float, current_map: str, visible_sprites: pygame.sprite.Group) -> None:
        """Updates caravan positions and handles map travel or arrivals."""
        self.spawn_timer += dt
        if self.spawn_timer >= 60.0:  # Spawn ambient caravan every 60 seconds
            self.spawn_timer = 0.0
            self.spawn_caravan(random.choice([CARAVAN_MERCHANT, CARAVAN_MILITARY]))

        for caravan in list(self.active_caravans):
            caravan["progress"] += dt * 0.05  # Travel speed
            
            if caravan["progress"] >= 1.0:
                # Caravan completed route!
                c_type = caravan["type"]
                target_map = caravan["target"]
                self.active_caravans.remove(caravan)
                
                if self.event_bus:
                    self.event_bus.emit("caravan_arrived", caravan_type=c_type, cargo_type=caravan["cargo"], target_map=target_map)
                    if c_type == CARAVAN_MILITARY:
                        self.event_bus.emit("road_safety_increased", amount=15.0)
                    elif c_type == CARAVAN_PILGRIM:
                        self.event_bus.emit("prosperity_changed", amount=3.0)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes caravan state."""
        return {"caravans": self.active_caravans, "spawn_timer": self.spawn_timer}

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes caravan state."""
        if data:
            self.active_caravans = data.get("caravans", [])
            self.spawn_timer = data.get("spawn_timer", 0.0)
