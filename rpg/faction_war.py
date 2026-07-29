"""
Echoes of Asterra - Dynamic Faction Warfare & Territory Control System
Simulates active skirmishes between world factions over 4 territory control points
(Forest Crossroads, Cave Depths, Ruins Plaza, Lake Pier).
Territory control directly alters guard presence, travel safety, regional danger, and shop taxes.
"""
import random
from dataclasses import dataclass
from typing import Dict, Any, Optional

from rpg.constants import FACTION_KNIGHTS, FACTION_BANDITS, FACTION_CULTISTS, FACTION_HUNTERS
from rpg.events import EventBus

@dataclass
class ControlPoint:
    """Represents a contested strategic territory."""
    name: str
    map_name: str
    controlling_faction: str
    contested: bool = False

class FactionWarManager:
    """
    Manages global territory control, autonomous faction skirmishes, and territorial gameplay bonuses.
    """
    def __init__(self) -> None:
        self.event_bus: Optional[EventBus] = None
        self.control_points: Dict[str, ControlPoint] = {
            "forest_crossroads": ControlPoint("Forest Crossroads", "forest", FACTION_KNIGHTS),
            "cave_depths": ControlPoint("Cave Depths", "cave", FACTION_HUNTERS),
            "ruins_plaza": ControlPoint("Ruins Plaza", "ruins", FACTION_BANDITS),
            "lake_pier": ControlPoint("Lake Pier", "lake", FACTION_KNIGHTS)
        }
        self.skirmish_timer = 0.0

    def register_event_listeners(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        event_bus.subscribe("day_changed", self._on_day_changed)

    def _on_day_changed(self, **kwargs) -> None:
        """Simulates autonomous skirmishes over control points daily."""
        factions = [FACTION_KNIGHTS, FACTION_BANDITS, FACTION_CULTISTS, FACTION_HUNTERS]
        target_cp = random.choice(list(self.control_points.values()))
        new_owner = random.choice(factions)

        if target_cp.controlling_faction != new_owner:
            old_owner = target_cp.controlling_faction
            target_cp.controlling_faction = new_owner
            if self.event_bus:
                self.event_bus.emit(
                    "territory_control_changed",
                    control_point=target_cp.name,
                    map_name=target_cp.map_name,
                    old_owner=old_owner,
                    new_owner=new_owner
                )

    def get_map_tax_modifier(self, map_name: str) -> float:
        """Returns tax modifier based on controlling faction of the map."""
        for cp in self.control_points.values():
            if cp.map_name == map_name:
                if cp.controlling_faction == FACTION_KNIGHTS:
                    return -0.05  # 5% tax discount
                elif cp.controlling_faction == FACTION_BANDITS:
                    return 0.15   # 15% extortion tax
                elif cp.controlling_faction == FACTION_CULTISTS:
                    return 0.20   # 20% void tax
        return 0.0

    def get_map_danger_modifier(self, map_name: str) -> float:
        """Returns danger multiplier based on controlling faction."""
        for cp in self.control_points.values():
            if cp.map_name == map_name:
                if cp.controlling_faction == FACTION_KNIGHTS:
                    return -15.0  # Safer
                elif cp.controlling_faction == FACTION_BANDITS:
                    return 25.0   # Dangerous ambushes
                elif cp.controlling_faction == FACTION_CULTISTS:
                    return 35.0   # Severe void corruption
        return 0.0

    def update(self, dt: float) -> None:
        """Updates internal timer."""
        self.skirmish_timer += dt

    def to_dict(self) -> Dict[str, Any]:
        """Serializes territory states."""
        return {
            "control_points": {
                k: {
                    "name": v.name,
                    "map_name": v.map_name,
                    "controlling_faction": v.controlling_faction
                } for k, v in self.control_points.items()
            }
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes territory states."""
        if not data:
            return
        cps = data.get("control_points", {})
        for k, v in cps.items():
            if k in self.control_points:
                self.control_points[k].controlling_faction = v.get("controlling_faction", self.control_points[k].controlling_faction)
