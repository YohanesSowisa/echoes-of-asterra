"""
Echoes of Asterra - The Sunken Mire & Tide Engine
Manages dynamic wetland water levels, tide cycles (Low/Rising/High/Falling),
submerged passability calculations, and marsh environmental hazards.
"""
import math
from typing import Dict, Any, Tuple, Optional
from rpg.constants import (
    MAP_SUNKEN_MIRE,
    TIDE_LOW,
    TIDE_RISING,
    TIDE_HIGH,
    TIDE_FALLING
)
from rpg.events import EventBus


class MireManager:
    """
    Subsystem managing the Sunken Mire biome mechanics and dynamic tide cycles.
    Synchronizes water levels with in-game time of day.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.tide_phase: str = TIDE_LOW
        self.water_level: float = 0.0  # 0.0 (fully receded) to 1.0 (fully flooded)
        self.tide_timer: float = 0.0
        self.game_reference: Any = None
        self.unlocked_sunken_chests: list = []
        self.rot_level: float = 15.0  # 0.0 to 100.0% Leyline Rot
        self.spore_nests: Dict[str, bool] = {
            "nest_west": True,
            "nest_center": True,
            "nest_east": True
        }
        if self.event_bus:
            self.event_bus.subscribe("day_changed", lambda day=1, **kw: self.on_day_changed(day))

    def reset(self) -> None:
        """Resets all mire state to defaults."""
        self.tide_phase = TIDE_LOW
        self.water_level = 0.0
        self.tide_timer = 0.0
        self.unlocked_sunken_chests.clear()
        self.rot_level = 15.0
        self.spore_nests = {
            "nest_west": True,
            "nest_center": True,
            "nest_east": True
        }

    def on_day_changed(self, day: int = 1) -> None:
        """
        Calculates daily Leyline Rot accumulation.
        - Active Spore Nests add +5% Rot each per day.
        - If Sunken Mire Leyline is Overcharged, rot decays by -10% per day instead.
        """
        is_overcharged = False
        if self.game_reference and hasattr(self.game_reference, "leyline_manager"):
            lm = self.game_reference.leyline_manager
            if lm and lm.is_region_overcharged(MAP_SUNKEN_MIRE):
                is_overcharged = True

        if is_overcharged:
            self.rot_level = max(0.0, self.rot_level - 10.0)
        else:
            active_cnt = sum(1 for active in self.spore_nests.values() if active)
            self.rot_level = min(100.0, self.rot_level + active_cnt * 5.0)

        if self.event_bus and self.rot_level >= 60.0:
            self.event_bus.emit("spore_blight_escalated", rot_level=self.rot_level, day=day)

    def cleanse_spore_nest(self, nest_id: str) -> bool:
        """
        Cleanses an active parasitic Spore Nest, dropping Rot level by 25%.
        """
        if nest_id in self.spore_nests and self.spore_nests[nest_id]:
            self.spore_nests[nest_id] = False
            self.rot_level = max(0.0, self.rot_level - 25.0)
            if self.event_bus:
                self.event_bus.emit(
                    "spore_nest_cleansed",
                    nest_id=nest_id,
                    remaining_rot=self.rot_level
                )
            return True
        return False

    def update(self, dt: float, time_of_day: float) -> None:
        """
        Updates tide cycles based on the in-game clock (0.0 to 24.0 hours).
        - 00:00 - 06:00: High Tide (Flooded)
        - 06:00 - 09:00: Falling Tide (Waters recede)
        - 09:00 - 15:00: Low Tide (Passages dry & accessible)
        - 15:00 - 18:00: Rising Tide (Waters swell)
        - 18:00 - 24:00: High Tide (Flooded)
        """
        prev_phase = self.tide_phase

        # Check if Sunken Mire Leyline is overcharged -> locks Low Tide permanently
        if self.game_reference and hasattr(self.game_reference, "leyline_manager"):
            lm = self.game_reference.leyline_manager
            if lm and lm.is_region_overcharged(MAP_SUNKEN_MIRE):
                self.tide_phase = TIDE_LOW
                self.water_level = 0.0
                return

        hour = time_of_day % 24.0

        if 0.0 <= hour < 6.0:
            self.tide_phase = TIDE_HIGH
            self.water_level = 1.0
        elif 6.0 <= hour < 9.0:
            self.tide_phase = TIDE_FALLING
            # Transition 1.0 -> 0.0 over 3 hours
            prog = (hour - 6.0) / 3.0
            self.water_level = max(0.0, 1.0 - prog)
        elif 9.0 <= hour < 15.0:
            self.tide_phase = TIDE_LOW
            self.water_level = 0.0
        elif 15.0 <= hour < 18.0:
            self.tide_phase = TIDE_RISING
            # Transition 0.0 -> 1.0 over 3 hours
            prog = (hour - 15.0) / 3.0
            self.water_level = min(1.0, prog)
        else:  # 18.0 <= hour < 24.0
            self.tide_phase = TIDE_HIGH
            self.water_level = 1.0

        if self.event_bus and prev_phase != self.tide_phase:
            self.event_bus.emit(
                "tide_phase_changed",
                previous_phase=prev_phase,
                current_phase=self.tide_phase,
                water_level=self.water_level
            )

    def get_speed_multiplier(self, current_map: str, is_in_water: bool = True) -> float:
        """
        Calculates movement speed penalty in the Sunken Mire.
        High Tide in water applies up to a 25% speed penalty (0.75x speed).
        """
        if current_map != MAP_SUNKEN_MIRE:
            return 1.0
        if not is_in_water:
            return 1.0

        # Check if local area is stabilized by Leyline Node
        if self.game_reference and hasattr(self.game_reference, "leyline_manager"):
            lm = self.game_reference.leyline_manager
            player = getattr(self.game_reference, "player", None)
            if lm and player and lm.is_position_purified(player.pos.x, player.pos.y, current_map):
                return 1.0

        # Scale speed between 1.0 (Low tide) and 0.75 (Peak High tide)
        return max(0.75, 1.0 - (0.25 * self.water_level))

    def is_toxic_water(self, x: float, y: float, current_map: str) -> bool:
        """
        Returns True if the location is toxic mire water during High Tide (water_level >= 0.7).
        Stabilized Leyline areas are immune to toxicity.
        """
        if current_map != MAP_SUNKEN_MIRE:
            return False
        if self.water_level < 0.7:
            return False

        if self.game_reference and hasattr(self.game_reference, "leyline_manager"):
            lm = self.game_reference.leyline_manager
            if lm and lm.is_position_purified(x, y, current_map):
                return False

        return True

    def is_passage_walkable(self, tile_type: str) -> bool:
        """
        During Low Tide (water_level < 0.5), marsh and mud passages are walkable.
        During High Tide (water_level >= 0.5), deep submerged marsh requires wading.
        """
        if tile_type in ["dirt", "bog_mud", "grass", "bog_grass"]:
            return True
        if tile_type == "mire_shallow":
            return True
        if tile_type == "mire_deep":
            return False
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes mire state for savegame."""
        return {
            "tide_phase": self.tide_phase,
            "water_level": round(self.water_level, 3),
            "unlocked_sunken_chests": list(self.unlocked_sunken_chests),
            "rot_level": round(self.rot_level, 2),
            "spore_nests": dict(self.spore_nests)
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores mire state from savegame."""
        if not isinstance(data, dict):
            return
        self.tide_phase = data.get("tide_phase", TIDE_LOW)
        self.water_level = float(data.get("water_level", 0.0))
        self.unlocked_sunken_chests = list(data.get("unlocked_sunken_chests", []))
        self.rot_level = float(data.get("rot_level", 15.0))
        self.spore_nests = dict(data.get("spore_nests", {
            "nest_west": True,
            "nest_center": True,
            "nest_east": True
        }))
