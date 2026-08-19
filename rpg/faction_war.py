"""
Echoes of Asterra - Dynamic Faction Warfare & Territory Control System
Simulates active skirmishes between world factions over 4 territory control points
(Forest Crossroads, Cave Depths, Ruins Plaza, Lake Pier).
Territory control is influenced by player faction reputation and zone activity,
directly altering guard presence, travel safety, regional danger, and shop taxes.
"""
import random
from dataclasses import dataclass
from typing import Dict, Any, Optional

from rpg.constants import FACTION_KNIGHTS, FACTION_BANDITS, FACTION_CULTISTS, FACTION_HUNTERS
from rpg.events import EventBus

# Maps each control point to factions that can contest it
CONTESTABLE_FACTIONS: Dict[str, list] = {
    "forest_crossroads": [FACTION_KNIGHTS, FACTION_BANDITS, FACTION_HUNTERS],
    "cave_depths": [FACTION_HUNTERS, FACTION_CULTISTS, FACTION_BANDITS],
    "ruins_plaza": [FACTION_BANDITS, FACTION_CULTISTS, FACTION_KNIGHTS],
    "lake_pier": [FACTION_KNIGHTS, FACTION_HUNTERS, FACTION_CULTISTS]
}

@dataclass
class ControlPoint:
    """Represents a contested strategic territory."""
    name: str
    map_name: str
    controlling_faction: str
    contested: bool = False
    stability: float = 50.0  # 0-100; below 30 triggers contest, above 70 is secure

class FactionWarManager:
    """
    Manages global territory control based on player faction reputation and zone activity.
    Territory shifts toward factions the player supports through combat and quest actions,
    replacing the previous random dice roll system.
    """
    def __init__(self) -> None:
        self.event_bus: Optional[EventBus] = None
        self.faction_manager: Any = None  # Bound to game.faction_manager during init
        self.game_reference: Any = None
        self.control_points: Dict[str, ControlPoint] = {
            "forest_crossroads": ControlPoint("Forest Crossroads", "forest", FACTION_KNIGHTS),
            "cave_depths": ControlPoint("Cave Depths", "cave", FACTION_HUNTERS),
            "ruins_plaza": ControlPoint("Ruins Plaza", "ruins", FACTION_BANDITS),
            "lake_pier": ControlPoint("Lake Pier", "lake", FACTION_KNIGHTS)
        }
        self.skirmish_timer = 0.0
        # Zone kill counters: tracks player kills per map region for influence
        self.zone_kills: Dict[str, int] = {
            "forest": 0, "cave": 0, "ruins": 0, "lake": 0
        }

    def register_event_listeners(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        event_bus.subscribe("day_changed", self._on_day_changed)
        event_bus.subscribe("enemy_killed", self._on_enemy_killed)

    def _on_enemy_killed(self, map_name: str = "", **kwargs) -> None:
        """Tracks player combat activity per zone for territory influence."""
        if map_name in self.zone_kills:
            self.zone_kills[map_name] += 1

    def _on_day_changed(self, **kwargs) -> None:
        """Simulates faction skirmishes influenced by player reputation and zone activity."""
        all_factions = [FACTION_KNIGHTS, FACTION_BANDITS, FACTION_CULTISTS, FACTION_HUNTERS]

        for cp_key, cp in self.control_points.items():
            # Check if an outpost is constructed at this control point
            has_outpost = False
            if self.game_reference and hasattr(self.game_reference, "outpost_manager"):
                has_outpost = self.game_reference.outpost_manager.has_outpost(cp_key)

            if has_outpost:
                # Fortified outpost locks control and prevents degradation
                cp.stability = max(cp.stability, 85.0)
                cp.contested = False
                continue

            # Get contestable factions for this control point
            contestable = CONTESTABLE_FACTIONS.get(cp_key, all_factions)

            # Calculate influence scores per faction
            scores: Dict[str, float] = {}
            for faction_id in contestable:
                # Base: current controller has a 30-point stability advantage
                base_score = 30.0 if faction_id == cp.controlling_faction else 0.0

                # Player reputation influence (strongest factor)
                rep_bonus = 0.0
                if self.faction_manager:
                    rep = self.faction_manager.get_reputation(faction_id)
                    rep_bonus = rep * 0.5  # Scale: -50 to +50

                # Zone kill influence: player activity in this zone favors allied factions
                zone_bonus = 0.0
                zone_count = self.zone_kills.get(cp.map_name, 0)
                if zone_count > 0 and self.faction_manager:
                    rep = self.faction_manager.get_reputation(faction_id)
                    if rep > 0:
                        zone_bonus = min(20.0, zone_count * 2.0)  # Cap at 20
                    elif rep < -10:
                        zone_bonus = -min(10.0, zone_count * 1.0)  # Hostile activity hurts

                # Small random variance (±10) to prevent total determinism
                variance = random.uniform(-10.0, 10.0)

                # Commodity Embargo Penalties (Pillar #5 Phase 2)
                embargo_penalty = 0.0
                if self.game_reference and hasattr(self.game_reference, "monopoly_manager"):
                    mm = self.game_reference.monopoly_manager
                    if mm:
                        if faction_id == FACTION_KNIGHTS and mm.is_faction_embargoed(FACTION_KNIGHTS, "iron_ore"):
                            embargo_penalty -= 15.0
                        elif faction_id == FACTION_BANDITS and mm.is_faction_embargoed(FACTION_BANDITS, "medicinal_herb"):
                            embargo_penalty -= 15.0

                scores[faction_id] = base_score + rep_bonus + zone_bonus + embargo_penalty + variance

            # Determine winner
            best_faction = max(scores, key=scores.get)

            if best_faction != cp.controlling_faction:
                # Territory changes hands
                old_owner = cp.controlling_faction
                cp.controlling_faction = best_faction
                cp.stability = 40.0  # Newly contested territory is unstable
                cp.contested = True

                if self.event_bus:
                    self.event_bus.emit(
                        "territory_control_changed",
                        control_point=cp.name,
                        map_name=cp.map_name,
                        old_owner=old_owner,
                        new_owner=best_faction
                    )
            else:
                # Territory held — stability increases
                cp.stability = min(100.0, cp.stability + 5.0)
                if cp.stability >= 70.0:
                    cp.contested = False

        # Decay zone kill counters gradually (so stale activity fades)
        for zone in self.zone_kills:
            self.zone_kills[zone] = max(0, self.zone_kills[zone] - 2)

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

    def get_faction_defense_multiplier(self, faction_id: str) -> float:
        """
        Returns military defense multiplier for a faction based on commodity supply lines.
        Knights of Asterra suffer a -20% DEF debuff (0.8x) during iron ore shortages/embargoes.
        """
        clean_fac = faction_id.lower()
        if clean_fac in (FACTION_KNIGHTS, "knights"):
            if self.game_reference and hasattr(self.game_reference, "monopoly_manager"):
                mm = self.game_reference.monopoly_manager
                if mm and mm.is_faction_embargoed(FACTION_KNIGHTS, "iron_ore"):
                    return 0.8
        return 1.0

    def covert_shift_ownership(self, point_id: str, new_faction: str) -> bool:
        """
        Seamlessly shifts control point ownership during a covert syndicate sabotage
        without open battlefield skirmishes.
        """
        if point_id not in self.control_points:
            return False
        cp = self.control_points[point_id]
        old_owner = cp.controlling_faction
        cp.controlling_faction = new_faction
        cp.stability = 30.0
        cp.contested = True
        if self.event_bus:
            self.event_bus.emit(
                "territory_control_changed",
                control_point=cp.name,
                map_name=cp.map_name,
                old_owner=old_owner,
                new_owner=new_faction
            )
        return True

    def update(self, dt: float) -> None:
        """Updates internal timer."""
        self.skirmish_timer += dt

    def to_dict(self) -> Dict[str, Any]:
        """Serializes territory states including stability and zone activity."""
        return {
            "control_points": {
                k: {
                    "name": v.name,
                    "map_name": v.map_name,
                    "controlling_faction": v.controlling_faction,
                    "stability": v.stability,
                    "contested": v.contested
                } for k, v in self.control_points.items()
            },
            "zone_kills": dict(self.zone_kills)
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes territory states."""
        if not data:
            return
        cps = data.get("control_points", {})
        for k, v in cps.items():
            if k in self.control_points:
                self.control_points[k].controlling_faction = v.get("controlling_faction", self.control_points[k].controlling_faction)
                self.control_points[k].stability = v.get("stability", 50.0)
                self.control_points[k].contested = v.get("contested", False)
        zk = data.get("zone_kills", {})
        for zone, count in zk.items():
            if zone in self.zone_kills:
                self.zone_kills[zone] = count

    def reset(self) -> None:
        """Resets control points and zone kill counters to default starting states."""
        for zone in self.zone_kills:
            self.zone_kills[zone] = 0
        defaults = {
            "forest_crossroads": FACTION_KNIGHTS,
            "cave_depths": FACTION_HUNTERS,
            "ruins_plaza": FACTION_BANDITS,
            "lake_pier": FACTION_KNIGHTS
        }
        for k, cp in self.control_points.items():
            cp.controlling_faction = defaults.get(k, FACTION_KNIGHTS)
            cp.stability = 50.0
            cp.contested = False

    def apply_mythos_inheritance(self, mythos_manager: Any) -> Optional[str]:
        """
        Inherits territory dominance from previous run's winning faction in Mythos history.
        The victorious faction starts the new run with fortified territory control and higher stability.
        """
        if not mythos_manager:
            return None
        dominant_faction = getattr(mythos_manager, "get_dominant_war_faction", lambda: None)()
        if not dominant_faction:
            return None

        # Give dominant faction starting territory advantage
        if dominant_faction == FACTION_KNIGHTS:
            self.control_points["forest_crossroads"].controlling_faction = FACTION_KNIGHTS
            self.control_points["forest_crossroads"].stability = 80.0
            self.control_points["lake_pier"].controlling_faction = FACTION_KNIGHTS
            self.control_points["lake_pier"].stability = 80.0
            self.control_points["ruins_plaza"].controlling_faction = FACTION_KNIGHTS
            self.control_points["ruins_plaza"].stability = 65.0
        elif dominant_faction == FACTION_HUNTERS:
            self.control_points["cave_depths"].controlling_faction = FACTION_HUNTERS
            self.control_points["cave_depths"].stability = 80.0
            self.control_points["forest_crossroads"].controlling_faction = FACTION_HUNTERS
            self.control_points["forest_crossroads"].stability = 75.0
        elif dominant_faction in [FACTION_BANDITS, FACTION_CULTISTS]:
            self.control_points["ruins_plaza"].controlling_faction = dominant_faction
            self.control_points["ruins_plaza"].stability = 85.0
            self.control_points["cave_depths"].controlling_faction = dominant_faction
            self.control_points["cave_depths"].stability = 75.0

        if self.event_bus:
            self.event_bus.emit(
                "faction_war_mythos_inherited",
                dominant_faction=dominant_faction
            )
        return dominant_faction
