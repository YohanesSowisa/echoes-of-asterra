"""
Echoes of Asterra - Monster Ecology System
Simulates living monster ecosystems: populations, predator-prey dynamics, territory control,
reproduction, nocturnal/diurnal activity windows, and over-hunting migration.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from rpg.events import EventBus

@dataclass
class Species:
    """Represents a monster species population in the Asterra ecosystem."""
    name: str
    base_population: int
    current_population: int
    max_population: int
    territory: List[str]             # Maps where species dwells
    diet: str                        # "herbivore", "carnivore", "scavenger", "undead"
    prey: Optional[str] = None       # Species name hunted as food
    predator: Optional[str] = None   # Species name hunting them
    active_day: bool = True
    active_night: bool = True
    preferred_weather: Optional[str] = None
    reproduction_rate: float = 0.10  # Population growth per day tick
    migration_threshold: float = 0.25 # % below which species migrates

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "current_population": self.current_population
        }

class EcologyManager:
    """
    Manages species population simulation and dynamic spawn density.
    """
    def __init__(self) -> None:
        self.species: Dict[str, Species] = {
            "slime": Species(
                name="slime", base_population=25, current_population=25, max_population=35,
                territory=["forest", "lake", "cave"], diet="herbivore", predator="wolf",
                active_day=True, active_night=True, preferred_weather="rain", reproduction_rate=0.15
            ),
            "slime_blue": Species(
                name="slime_blue", base_population=15, current_population=15, max_population=25,
                territory=["lake", "cave"], diet="herbivore", predator="wolf",
                active_day=True, active_night=False, preferred_weather="snow", reproduction_rate=0.12
            ),
            "slime_red": Species(
                name="slime_red", base_population=10, current_population=10, max_population=20,
                territory=["dungeon", "secret_area"], diet="herbivore",
                active_day=False, active_night=True, reproduction_rate=0.10
            ),
            "wolf": Species(
                name="wolf", base_population=12, current_population=12, max_population=20,
                territory=["forest", "mountain", "lake"], diet="carnivore", prey="slime",
                active_day=True, active_night=True, reproduction_rate=0.08
            ),
            "goblin": Species(
                name="goblin", base_population=15, current_population=15, max_population=25,
                territory=["ruins", "cave"], diet="scavenger", predator="knight",
                active_day=True, active_night=True, reproduction_rate=0.10
            ),
            "skeleton": Species(
                name="skeleton", base_population=18, current_population=18, max_population=30,
                territory=["ruins", "dungeon"], diet="undead",
                active_day=False, active_night=True, reproduction_rate=0.06
            ),
            "mage": Species(
                name="mage", base_population=8, current_population=8, max_population=15,
                territory=["dungeon", "ruins"], diet="undead",
                active_day=False, active_night=True, reproduction_rate=0.05
            ),
            "knight": Species(
                name="knight", base_population=8, current_population=8, max_population=15,
                territory=["mountain", "dungeon"], diet="carnivore", prey="goblin",
                active_day=True, active_night=False, reproduction_rate=0.05
            )
        }

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes to global EventBus topics."""
        event_bus.subscribe("enemy_killed", self._on_enemy_killed)
        event_bus.subscribe("day_changed", self._on_day_changed)

    def get_spawn_count(self, enemy_type: str, map_name: str, base_count: int, time_of_day_prog: float = 0.5) -> int:
        """
        Calculates dynamic enemy spawn count based on species population ratio,
        territory alignment, and day/night activity windows.
        """
        sp = self.species.get(enemy_type)
        if not sp:
            return base_count

        # Check territory
        if map_name not in sp.territory:
            return 0  # Not native to this map

        # Day/Night activity check (time_of_day_prog: 0.0 - 0.25 sunrise, 0.25-0.75 day, 0.75-1.0 night)
        is_night = (time_of_day_prog >= 0.75 or time_of_day_prog < 0.20)
        if is_night and not sp.active_night:
            return max(1, base_count // 3)  # Reduced spawns at night for diurnal
        if not is_night and not sp.active_day:
            return max(1, base_count // 3)  # Reduced spawns at day for nocturnal

        # Population density scale (0.3x to 1.5x)
        ratio = sp.current_population / max(1, sp.base_population)
        adjusted_count = max(1, int(base_count * max(0.3, min(1.5, ratio))))
        return adjusted_count

    def get_population(self, enemy_type: str) -> int:
        """Returns current population count for a species."""
        sp = self.species.get(enemy_type)
        return sp.current_population if sp else 0

    def _on_enemy_killed(self, enemy_type: str = "", **kwargs: Any) -> None:
        """Decrements current population when hero slays monsters."""
        sp = self.species.get(enemy_type)
        if sp:
            sp.current_population = max(0, sp.current_population - 1)

    def _on_day_changed(self, **kwargs: Any) -> None:
        """Runs population simulation tick on day changes."""
        for sp in self.species.values():
            # 1. Natural reproduction
            growth = int(sp.current_population * sp.reproduction_rate)
            if growth < 1 and sp.current_population > 0 and sp.current_population < sp.max_population:
                growth = 1
            sp.current_population = min(sp.max_population, sp.current_population + growth)

            # 2. Predator-Prey consumption
            if sp.prey and sp.current_population > 0:
                prey_sp = self.species.get(sp.prey)
                if prey_sp and prey_sp.current_population > 0:
                    hunted = max(1, int(sp.current_population * 0.15))
                    prey_sp.current_population = max(0, prey_sp.current_population - hunted)

            # 3. Over-hunting migration (low pop triggers territory spread)
            if sp.current_population < int(sp.max_population * sp.migration_threshold):
                # Expand territory if depleted
                adjacent_maps = ["forest", "lake", "cave", "mountain", "ruins"]
                for m in adjacent_maps:
                    if m not in sp.territory:
                        sp.territory.append(m)
                        break

    def to_dict(self) -> Dict[str, int]:
        """Serializes current species populations to dict for saving."""
        return {s_name: sp.current_population for s_name, sp in self.species.items()}

    def from_dict(self, data: Dict[str, int]) -> None:
        """Restores species populations from dict."""
        for s_name, pop in data.items():
            if s_name in self.species:
                self.species[s_name].current_population = max(0, min(self.species[s_name].max_population, pop))
