"""
Echoes of Asterra - Chrono-Echoes & Spacetime Fractures System (Pillar #8).
Implements the 3-day rolling atomic timeline snapshot engine, Chrono-Weaver Hourglass
activation, non-destructive state restoration, and timeline rewind tracking.
Phase 2: Temporal Fractures and Chrono-Doppelganger Mirror Boss spawning.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import time

from rpg.events import EventBus

MAX_ROLLING_DAYS = 3


@dataclass
class TimelineSnapshot:
    """Represents an atomic point-in-time snapshot of the world and player state."""
    day: int
    time_of_day: float = 8.0
    player_hp: float = 100.0
    player_max_hp: float = 100.0
    player_stamina: float = 100.0
    player_max_stamina: float = 100.0
    player_gold: int = 0
    player_exp: int = 0
    player_level: int = 1
    player_pos: Tuple[float, float] = (100.0, 100.0)
    player_map: str = "village"
    inventory_data: List[Dict[str, Any]] = field(default_factory=list)
    equipment_data: Dict[str, Any] = field(default_factory=dict)
    quest_states: Dict[str, Any] = field(default_factory=dict)
    defeated_bosses: List[str] = field(default_factory=list)
    world_flags: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day": self.day,
            "time_of_day": self.time_of_day,
            "player_hp": self.player_hp,
            "player_max_hp": self.player_max_hp,
            "player_stamina": self.player_stamina,
            "player_max_stamina": self.player_max_stamina,
            "player_gold": self.player_gold,
            "player_exp": self.player_exp,
            "player_level": self.player_level,
            "player_pos": list(self.player_pos),
            "player_map": self.player_map,
            "inventory_data": self.inventory_data,
            "equipment_data": self.equipment_data,
            "quest_states": self.quest_states,
            "defeated_bosses": self.defeated_bosses,
            "world_flags": self.world_flags,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineSnapshot":
        return cls(
            day=data.get("day", 1),
            time_of_day=float(data.get("time_of_day", 8.0)),
            player_hp=float(data.get("player_hp", 100.0)),
            player_max_hp=float(data.get("player_max_hp", 100.0)),
            player_stamina=float(data.get("player_stamina", 100.0)),
            player_max_stamina=float(data.get("player_max_stamina", 100.0)),
            player_gold=data.get("player_gold", 0),
            player_exp=data.get("player_exp", 0),
            player_level=data.get("player_level", 1),
            player_pos=tuple(data.get("player_pos", [100.0, 100.0])),
            player_map=data.get("player_map", "village"),
            inventory_data=data.get("inventory_data", []),
            equipment_data=data.get("equipment_data", {}),
            quest_states=data.get("quest_states", {}),
            defeated_bosses=data.get("defeated_bosses", []),
            world_flags=data.get("world_flags", {}),
            timestamp=float(data.get("timestamp", 0.0))
        )


@dataclass
class TemporalFracture:
    """Represents a spacetime fissure left behind after a temporal rewind."""
    fracture_id: str
    pos: Tuple[float, float]
    map_name: str
    created_day: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fracture_id": self.fracture_id,
            "pos": list(self.pos),
            "map_name": self.map_name,
            "created_day": self.created_day
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalFracture":
        return cls(
            fracture_id=data.get("fracture_id", ""),
            pos=tuple(data.get("pos", [100.0, 100.0])),
            map_name=data.get("map_name", "village"),
            created_day=data.get("created_day", 1)
        )


@dataclass
class ChronoDoppelgangerProfile:
    """Stores mirrored profile of the player prior to a temporal rewind."""
    doppelganger_id: str
    name: str
    level: int
    hp: float
    max_hp: float
    atk: float
    equipped_weapon: str
    equipped_armor: str
    pos: Tuple[float, float]
    map_name: str
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doppelganger_id": self.doppelganger_id,
            "name": self.name,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "atk": self.atk,
            "equipped_weapon": self.equipped_weapon,
            "equipped_armor": self.equipped_armor,
            "pos": list(self.pos),
            "map_name": self.map_name,
            "is_active": self.is_active
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChronoDoppelgangerProfile":
        return cls(
            doppelganger_id=data.get("doppelganger_id", ""),
            name=data.get("name", "Chrono-Doppelganger"),
            level=data.get("level", 1),
            hp=float(data.get("hp", 150.0)),
            max_hp=float(data.get("max_hp", 150.0)),
            atk=float(data.get("atk", 20.0)),
            equipped_weapon=data.get("equipped_weapon", "Spectral Chrono-Blade"),
            equipped_armor=data.get("equipped_armor", "Temporal Plate"),
            pos=tuple(data.get("pos", [100.0, 100.0])),
            map_name=data.get("map_name", "village"),
            is_active=data.get("is_active", True)
        )


class ChronoManager:
    """
    Manages temporal snapshots, ring-buffer rolling history, atomic time rewind,
    and paradox shadow boss (Chrono-Doppelganger) spawning.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.history: List[TimelineSnapshot] = []
        self.active_fractures: List[TemporalFracture] = []
        self.active_doppelganger: Optional[ChronoDoppelgangerProfile] = None
        self.total_rewinds_performed: int = 0
        self.total_days_rewound: int = 0
        self.last_rewind_day: int = 0
        self.reset()
        if self.event_bus:
            self.event_bus.subscribe("day_changed", self._on_day_changed)

    def _on_day_changed(self, day: int = 1, game_state: Optional[Any] = None, **kwargs: Any) -> None:
        if game_state:
            self.record_snapshot(game_state)

    def reset(self) -> None:
        """Resets the Chrono Manager to clean initial state."""
        self.history = []
        self.active_fractures = []
        self.active_doppelganger = None
        self.total_rewinds_performed = 0
        self.total_days_rewound = 0
        self.last_rewind_day = 0
        self.is_sentinel_defeated = False
        self.prestige_title = None

    def record_snapshot(self, game: Any) -> TimelineSnapshot:
        """
        Creates and stores an atomic snapshot of current game state into the rolling history ring buffer.
        """
        day = getattr(game, "day", 1)
        time_of_day = getattr(game, "time_of_day", 8.0)
        player = getattr(game, "player", None)

        player_hp = getattr(player, "hp", 100.0) if player else 100.0
        player_max_hp = getattr(player, "max_hp", 100.0) if player else 100.0
        player_stamina = getattr(player, "stamina", 100.0) if player else 100.0
        player_max_stamina = getattr(player, "max_stamina", 100.0) if player else 100.0
        player_gold = getattr(player, "gold", 0) if player else 0
        player_exp = getattr(player, "exp", 0) if player else 0
        player_level = getattr(player, "level", 1) if player else 1

        if player and hasattr(player, "rect"):
            player_pos = (float(player.rect.x), float(player.rect.y))
        else:
            player_pos = (100.0, 100.0)

        player_map = getattr(game, "current_map_name", "village")

        # Capture serialized inventory
        inventory_data = []
        if player and hasattr(player, "inventory") and player.inventory:
            for slot in player.inventory.slots:
                if slot is not None:
                    if hasattr(slot, "to_dict"):
                        inventory_data.append(slot.to_dict())
                    else:
                        inventory_data.append({
                            "name": getattr(slot, "name", ""),
                            "qty": getattr(slot, "quantity", 1),
                            "quantity": getattr(slot, "quantity", 1),
                            "rarity": getattr(slot, "rarity", ""),
                            "stats": getattr(slot, "stats", {})
                        })

        # Capture serialized equipment
        equipment_data = {}
        if player and hasattr(player, "equipment") and player.equipment:
            if hasattr(player.equipment, "to_dict"):
                equipment_data = player.equipment.to_dict()

        # Capture quest states
        quest_states = {}
        if hasattr(game, "quest_manager") and game.quest_manager:
            if hasattr(game.quest_manager, "to_dict"):
                quest_states = game.quest_manager.to_dict()

        defeated_bosses = list(getattr(game, "defeated_bosses", []))
        world_flags = dict(getattr(game, "world_flags", {}))

        snapshot = TimelineSnapshot(
            day=day,
            time_of_day=time_of_day,
            player_hp=player_hp,
            player_max_hp=player_max_hp,
            player_stamina=player_stamina,
            player_max_stamina=player_max_stamina,
            player_gold=player_gold,
            player_exp=player_exp,
            player_level=player_level,
            player_pos=player_pos,
            player_map=player_map,
            inventory_data=inventory_data,
            equipment_data=equipment_data,
            quest_states=quest_states,
            defeated_bosses=defeated_bosses,
            world_flags=world_flags,
            timestamp=time.time()
        )

        # Update or append snapshot for this day
        existing_idx = next((i for i, s in enumerate(self.history) if s.day == day), -1)
        if existing_idx != -1:
            self.history[existing_idx] = snapshot
        else:
            self.history.append(snapshot)

        # Maintain max 3 days rolling history
        if len(self.history) > MAX_ROLLING_DAYS:
            self.history = self.history[-MAX_ROLLING_DAYS:]

        if self.event_bus:
            self.event_bus.emit("chrono_snapshot_recorded", day=day)

        return snapshot

    def can_rewind(self, player: Any, days_to_rewind: int = 3) -> Tuple[bool, str]:
        """
        Validates if time can be rewound using the Chrono-Weaver Hourglass.
        """
        if not self.history:
            return False, "No timeline snapshots recorded yet in the Chrono ring buffer."

        # Check for Chrono-Weaver Hourglass item
        has_hourglass = False
        if hasattr(player, "inventory") and player.inventory:
            for name in ["Chrono-Weaver Hourglass", "chrono_weaver_hourglass"]:
                if player.inventory.has_item(name, 1):
                    has_hourglass = True
                    break

        if not has_hourglass:
            return False, "Requires the 'Chrono-Weaver Hourglass' relic in your inventory to manipulate time!"

        return True, "Chrono-Weaver Hourglass radiates temporal energy. Ready for rewind!"

    def execute_temporal_rewind(
        self,
        game: Any,
        days_to_rewind: int = 3
    ) -> Tuple[bool, str, Optional[TimelineSnapshot]]:
        """
        Atomically rolls back the world and character state up to 3 in-game days.
        Leaves a Temporal Fracture at current position and spawns a Chrono-Doppelganger.
        """
        player = getattr(game, "player", None)
        can_r, reason = self.can_rewind(player, days_to_rewind)
        if not can_r:
            return False, reason, None

        curr_day = getattr(game, "day", 1)
        target_day = max(1, curr_day - days_to_rewind)

        # Find target snapshot in rolling history
        target_snapshot = None
        for s in self.history:
            if s.day <= target_day:
                target_snapshot = s

        if not target_snapshot:
            target_snapshot = self.history[0]

        actual_days_rewound = max(1, curr_day - target_snapshot.day)

        # Capture Pre-Rewind Player Profile for Chrono-Doppelganger Mirror Boss
        pre_level = getattr(player, "level", 1) if player else 1
        pre_hp = getattr(player, "max_hp", 100.0) * 1.5 if player else 150.0
        pre_atk = getattr(player, "base_atk", 20.0) if player else 20.0

        weapon_name = "Spectral Chrono-Blade"
        armor_name = "Temporal Plate"
        if player and hasattr(player, "equipment") and player.equipment and hasattr(player.equipment, "slots"):
            w_item = player.equipment.slots.get("weapon")
            if w_item:
                weapon_name = getattr(w_item, "name", "Spectral Chrono-Blade")
            a_item = player.equipment.slots.get("chest")
            if a_item:
                armor_name = getattr(a_item, "name", "Temporal Plate")

        pre_pos = (float(getattr(player.rect, "x", 100)), float(getattr(player.rect, "y", 100))) if player and hasattr(player, "rect") else (100.0, 100.0)
        pre_map = getattr(game, "current_map_name", "village")

        # Spawn Temporal Fracture
        fracture_id = f"fracture_{curr_day}_{int(pre_pos[0])}_{int(pre_pos[1])}"
        fracture = TemporalFracture(
            fracture_id=fracture_id,
            pos=pre_pos,
            map_name=pre_map,
            created_day=curr_day
        )
        self.active_fractures.append(fracture)

        # Spawn Chrono-Doppelganger Profile
        dop_id = f"doppelganger_{curr_day}"
        self.active_doppelganger = ChronoDoppelgangerProfile(
            doppelganger_id=dop_id,
            name="Chrono-Doppelganger",
            level=pre_level,
            hp=pre_hp,
            max_hp=pre_hp,
            atk=pre_atk,
            equipped_weapon=weapon_name,
            equipped_armor=armor_name,
            pos=pre_pos,
            map_name=pre_map,
            is_active=True
        )

        # Apply Atomic Rollback to Game & Player
        if hasattr(game, "day"):
            game.day = target_snapshot.day

        if hasattr(game, "time_of_day"):
            game.time_of_day = target_snapshot.time_of_day

        if player:
            player.hp = target_snapshot.player_hp
            player.max_hp = target_snapshot.player_max_hp
            player.stamina = target_snapshot.player_stamina
            player.max_stamina = target_snapshot.player_max_stamina
            player.gold = target_snapshot.player_gold
            player.exp = target_snapshot.player_exp
            player.level = target_snapshot.player_level

            if hasattr(player, "rect"):
                player.rect.x = int(target_snapshot.player_pos[0])
                player.rect.y = int(target_snapshot.player_pos[1])

            # Restore Inventory Cleanly
            if hasattr(player, "inventory") and player.inventory:
                from rpg.items import create_item
                player.inventory.slots = [None] * player.inventory.size
                for item_dict in target_snapshot.inventory_data:
                    item_name = item_dict.get("name", "")
                    qty = item_dict.get("quantity", item_dict.get("qty", 1))
                    if item_name:
                        item_obj = create_item(item_name, qty)
                        if item_obj:
                            player.inventory.add_item(item_obj)

            # Restore Equipment
            if hasattr(player, "equipment") and player.equipment and target_snapshot.equipment_data:
                if hasattr(player.equipment, "from_dict"):
                    player.equipment.from_dict(target_snapshot.equipment_data)

        # Restore Quests
        if hasattr(game, "quest_manager") and game.quest_manager and target_snapshot.quest_states:
            if hasattr(game.quest_manager, "from_dict"):
                game.quest_manager.from_dict(target_snapshot.quest_states)

        if hasattr(game, "defeated_bosses"):
            game.defeated_bosses = list(target_snapshot.defeated_bosses)

        if hasattr(game, "world_flags"):
            game.world_flags = dict(target_snapshot.world_flags)

        # Update Chrono Metrics
        self.total_rewinds_performed += 1
        self.total_days_rewound += actual_days_rewound
        self.last_rewind_day = target_snapshot.day

        # Trim snapshots that are chronologically ahead of target day
        self.history = [s for s in self.history if s.day <= target_snapshot.day]

        if self.event_bus:
            self.event_bus.emit(
                "timeline_rewound",
                target_day=target_snapshot.day,
                days_rewound=actual_days_rewound
            )
            self.event_bus.emit(
                "chrono_doppelganger_spawned",
                doppelganger_id=dop_id,
                pos=pre_pos,
                map_name=pre_map,
                weapon=weapon_name,
                armor=armor_name,
                level=pre_level
            )

        return (
            True,
            f"Temporal fracture unleashed! Rewound time {actual_days_rewound} day(s) back to Day {target_snapshot.day}. Paradox Chrono-Doppelganger has manifested!",
            target_snapshot
        )

    def defeat_doppelganger(self) -> Tuple[bool, str]:
        """Resolves the paradox anomaly when the Chrono-Doppelganger is defeated."""
        if self.active_doppelganger and self.active_doppelganger.is_active:
            self.active_doppelganger.is_active = False
            self.active_fractures.clear()
            if self.event_bus:
                self.event_bus.emit(
                    "chrono_anomaly_resolved",
                    doppelganger_id=self.active_doppelganger.doppelganger_id
                )
            return True, "Chrono-Doppelganger vanquished! The temporal fracture has collapsed and reality has stabilized."
        return False, "No active Chrono-Doppelganger to defeat."

    def is_temporal_rift_active(self) -> bool:
        """Returns True if there are unresolved temporal fractures or active doppelgangers."""
        return len(self.active_fractures) > 0 or (self.active_doppelganger is not None and self.active_doppelganger.is_active)

    def get_time_dilation_factor(self) -> float:
        """
        Returns atmospheric/combat time dilation multiplier:
        - 0.75x (25% time-slow dilation) when an active temporal fracture is present.
        - 1.0x (normal time speed) otherwise.
        """
        if self.is_temporal_rift_active():
            return 0.75
        return 1.0

    def can_summon_aeon_sentinel(self, player: Any = None) -> Tuple[bool, str]:
        """
        Validates if the player can summon or confront the Aeon Sentinel.
        Requires:
        1. Having performed temporal rewinds (total_rewinds_performed >= 1).
        2. Holding the Chrono-Weaver Hourglass relic.
        """
        if self.is_sentinel_defeated:
            return False, "The Aeon Sentinel has already been defeated and the spacetime continuum is stabilized."

        if self.total_rewinds_performed < 1:
            return False, "You have not disturbed the fabric of spacetime sufficiently to draw the Aeon Sentinel's attention."

        if player and hasattr(player, "inventory") and player.inventory:
            for name in ["Chrono-Weaver Hourglass", "chrono_weaver_hourglass"]:
                if player.inventory.has_item(name, 1):
                    return True, "The Chrono-Weaver Hourglass resonates with cosmic intensity. The Aeon Sentinel awakens!"
            return False, "Requires the 'Chrono-Weaver Hourglass' relic to channel the sentinel's manifestation."

        return True, "Conditions met to confront the Aeon Sentinel."

    def on_aeon_sentinel_defeated(self, player: Any = None) -> Tuple[bool, str]:
        """
        Handles post-defeat climax resolution when the Aeon Sentinel is slain.
        Awards prestige title 'Chrono-Weaver Supreme', gives Aeon Core, and stabilizes reality.
        """
        self.is_sentinel_defeated = True
        self.prestige_title = "Chrono-Weaver Supreme"
        self.active_fractures.clear()
        if self.active_doppelganger:
            self.active_doppelganger.is_active = False

        if player and hasattr(player, "inventory") and player.inventory:
            from rpg.items import create_item
            if not player.inventory.has_item("Aeon Core", 1):
                core_item = create_item("Aeon Core", 1)
                if core_item:
                    player.inventory.add_item(core_item)

        if self.event_bus:
            self.event_bus.emit(
                "temporal_fabric_mended",
                title=self.prestige_title,
                total_rewinds=self.total_rewinds_performed
            )

        return True, f"Spacetime Continuum Mended! You have earned the prestigious title '{self.prestige_title}'."

    def to_dict(self) -> Dict[str, Any]:
        """Serializes ChronoManager state for save games."""
        return {
            "history": [s.to_dict() for s in self.history],
            "active_fractures": [f.to_dict() for f in self.active_fractures],
            "active_doppelganger": self.active_doppelganger.to_dict() if self.active_doppelganger else None,
            "total_rewinds_performed": self.total_rewinds_performed,
            "total_days_rewound": self.total_days_rewound,
            "last_rewind_day": self.last_rewind_day,
            "is_sentinel_defeated": self.is_sentinel_defeated,
            "prestige_title": self.prestige_title
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores ChronoManager state from save games."""
        if not isinstance(data, dict):
            return

        self.total_rewinds_performed = data.get("total_rewinds_performed", 0)
        self.total_days_rewound = data.get("total_days_rewound", 0)
        self.last_rewind_day = data.get("last_rewind_day", 0)
        self.is_sentinel_defeated = data.get("is_sentinel_defeated", False)
        self.prestige_title = data.get("prestige_title")

        self.history = []
        hist = data.get("history", [])
        if isinstance(hist, list):
            for s_data in hist:
                if isinstance(s_data, dict):
                    self.history.append(TimelineSnapshot.from_dict(s_data))

        self.active_fractures = []
        fracs = data.get("active_fractures", [])
        if isinstance(fracs, list):
            for f_data in fracs:
                if isinstance(f_data, dict):
                    self.active_fractures.append(TemporalFracture.from_dict(f_data))

        dop_data = data.get("active_doppelganger")
        if dop_data and isinstance(dop_data, dict):
            self.active_doppelganger = ChronoDoppelgangerProfile.from_dict(dop_data)
        else:
            self.active_doppelganger = None
