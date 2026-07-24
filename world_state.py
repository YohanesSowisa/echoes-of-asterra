"""
Echoes of Asterra - Dynamic World State Simulation
Tracks continuous world progression: days, seasons, prosperity, danger levels, and dynamic world events.
Drives weather biases, shop price modifiers, enemy spawn scaling, and event triggers.
"""
import random
from dataclasses import dataclass, field
from typing import List, Set, Dict, Any
from rpg.constants import (
    SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER,
    EVENT_VILLAGE_FESTIVAL, EVENT_MERCHANT_CARAVAN, EVENT_BANDIT_INVASION,
    EVENT_HARVEST_SEASON
)
from rpg.settings import DAY_LENGTH_SECONDS
from rpg.events import EventBus

SEASONS_ORDER = [SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER]

@dataclass
class WorldEvent:
    """Represents a temporary or permanent active world event."""
    event_id: str
    name: str
    description: str
    duration_days: int  # -1 for permanent
    remaining_days: int
    effects: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "description": self.description,
            "duration_days": self.duration_days,
            "remaining_days": self.remaining_days,
            "effects": self.effects
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldEvent':
        return cls(
            event_id=data["event_id"],
            name=data["name"],
            description=data["description"],
            duration_days=data["duration_days"],
            remaining_days=data["remaining_days"],
            effects=data.get("effects", {})
        )

class WorldState:
    """
    Simulation engine tracking continuous time, seasons, prosperity, and world events.
    """
    def __init__(self) -> None:
        self.day: int = 1
        self.season: str = SEASON_SPRING
        # Start new game at 06:00 AM (6 hours into 24-hour cycle)
        self.time_accumulator: float = (6.0 / 24.0) * DAY_LENGTH_SECONDS
        self.prosperity: int = 50       # 0 (desolate) to 100 (thriving)
        self.danger_level: int = 20     # 0 (peaceful) to 100 (hostile overrun)
        
        self.active_events: List[WorldEvent] = []
        self.completed_event_ids: Set[str] = set()
        
        # Track daily counters for drift calculations
        self._enemies_killed_today: int = 0
        self._quests_completed_today: int = 0

    @property
    def time_of_day(self) -> float:
        """Returns in-game hour (0.0 to 24.0) calculated from time accumulator."""
        return (self.time_accumulator / max(1.0, DAY_LENGTH_SECONDS)) * 24.0

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes WorldState to relevant global events."""
        event_bus.subscribe("enemy_killed", self._on_enemy_killed)
        event_bus.subscribe("quest_completed", self._on_quest_completed)

    def _on_enemy_killed(self, **kwargs: Any) -> None:
        self._enemies_killed_today += 1

    def _on_quest_completed(self, **kwargs: Any) -> None:
        self._quests_completed_today += 1

    def update(self, dt: float, event_bus: EventBus) -> None:
        """Ticks real-time clock. When full day completes, runs day_tick()."""
        self.time_accumulator += dt
        if self.time_accumulator >= DAY_LENGTH_SECONDS:
            self.time_accumulator -= DAY_LENGTH_SECONDS
            self.day_tick(event_bus)

    tick = update

    def day_tick(self, event_bus: EventBus) -> None:
        """Advances 1 in-game day, updates season, prosperity/danger, event durations, and rolls for new events."""
        self.day += 1

        # Cycle seasons every 30 days
        season_index = ((self.day - 1) // 30) % len(SEASONS_ORDER)
        old_season = self.season
        self.season = SEASONS_ORDER[season_index]

        # Drift prosperity: +2 per quest completed today, -1 if high danger
        if self._quests_completed_today > 0:
            self.prosperity = min(100, self.prosperity + self._quests_completed_today * 2)
        if self.danger_level > 60:
            self.prosperity = max(0, self.prosperity - 1)

        # Drift danger: -1 per 4 enemies killed today, +1 if no enemies culled
        if self._enemies_killed_today >= 4:
            self.danger_level = max(0, self.danger_level - (self._enemies_killed_today // 4))
        elif self._enemies_killed_today == 0:
            self.danger_level = min(100, self.danger_level + 1)

        # Reset daily tracking
        self._enemies_killed_today = 0
        self._quests_completed_today = 0

        # Tick active events
        expired_events = []
        for evt in self.active_events:
            if evt.duration_days > 0:
                evt.remaining_days -= 1
                if evt.remaining_days <= 0:
                    expired_events.append(evt)

        for evt in expired_events:
            self.active_events.remove(evt)
            event_bus.emit("world_event_ended", event_id=evt.event_id)

        # Roll for new events
        self._roll_for_events(event_bus)

        # Emit day changed event
        event_bus.emit("day_changed", day=self.day, season=self.season)

    def _roll_for_events(self, event_bus: EventBus) -> None:
        """Evaluates conditions for new world events to trigger."""
        active_ids = {evt.event_id for evt in self.active_events}

        # 1. Village Festival: prosperity > 70 in Spring
        if self.season == SEASON_SPRING and self.prosperity >= 70 and EVENT_VILLAGE_FESTIVAL not in active_ids:
            if random.random() < 0.25:
                evt = WorldEvent(
                    event_id=EVENT_VILLAGE_FESTIVAL,
                    name="Village Festival",
                    description="The village celebrates prosperity! Shop prices are discounted.",
                    duration_days=3,
                    remaining_days=3,
                    effects={"price_mult": 0.8}
                )
                self.active_events.append(evt)
                event_bus.emit("world_event_started", event_id=evt.event_id)

        # 2. Merchant Caravan: every 7th day
        if self.day % 7 == 0 and EVENT_MERCHANT_CARAVAN not in active_ids:
            evt = WorldEvent(
                event_id=EVENT_MERCHANT_CARAVAN,
                name="Merchant Caravan",
                description="A rare trading caravan arrives in Asterra.",
                duration_days=2,
                remaining_days=2,
                effects={"price_mult": 0.9}
            )
            self.active_events.append(evt)
            event_bus.emit("world_event_started", event_id=evt.event_id)

        # 3. Bandit Invasion: high danger (> 60)
        if self.danger_level > 60 and EVENT_BANDIT_INVASION not in active_ids:
            if random.random() < 0.3:
                evt = WorldEvent(
                    event_id=EVENT_BANDIT_INVASION,
                    name="Bandit Outbreak",
                    description="Dangerous bandits roam the wilderness paths!",
                    duration_days=4,
                    remaining_days=4,
                    effects={"danger_boost": 15}
                )
                self.active_events.append(evt)
                event_bus.emit("world_event_started", event_id=evt.event_id)

        # 4. Harvest Season: Autumn + prosperity > 40
        if self.season == SEASON_AUTUMN and self.prosperity >= 40 and EVENT_HARVEST_SEASON not in active_ids:
            evt = WorldEvent(
                event_id=EVENT_HARVEST_SEASON,
                name="Harvest Season",
                description="Autumn crops yield extra food and resources.",
                duration_days=10,
                remaining_days=10,
                effects={"food_drop_mult": 2.0}
            )
            self.active_events.append(evt)
            event_bus.emit("world_event_started", event_id=evt.event_id)

    def trigger_permanent_event(self, event_id: str, name: str, description: str, event_bus: EventBus) -> None:
        """Triggers a permanent storyline world event (e.g. boss defeated)."""
        if event_id not in self.completed_event_ids:
            self.completed_event_ids.add(event_id)
            evt = WorldEvent(
                event_id=event_id,
                name=name,
                description=description,
                duration_days=-1,
                remaining_days=-1
            )
            self.active_events.append(evt)
            event_bus.emit("world_event_started", event_id=event_id)

    def get_weather_bias(self) -> Dict[str, float]:
        """Returns weather probability weights matching current season."""
        if self.season == SEASON_SPRING:
            return {"clear": 0.50, "rain": 0.30, "snow": 0.00, "fog": 0.10, "leaves": 0.10}
        elif self.season == SEASON_SUMMER:
            return {"clear": 0.85, "rain": 0.10, "snow": 0.00, "fog": 0.05, "leaves": 0.00}
        elif self.season == SEASON_AUTUMN:
            return {"clear": 0.30, "rain": 0.15, "snow": 0.05, "fog": 0.20, "leaves": 0.30}
        elif self.season == SEASON_WINTER:
            return {"clear": 0.40, "rain": 0.05, "snow": 0.40, "fog": 0.15, "leaves": 0.00}
        return {"clear": 1.0}

    def get_spawn_modifier(self) -> float:
        """Returns enemy stat/count danger scaling multiplier."""
        # Baseline 1.0 + 0.5% per danger level point
        extra_danger = 0
        for evt in self.active_events:
            extra_danger += evt.effects.get("danger_boost", 0)
        total_danger = min(100, self.danger_level + extra_danger)
        return 1.0 + (total_danger * 0.005)

    def get_price_modifier(self) -> float:
        """Returns shop price multiplier based on prosperity and active events."""
        # Base modifier from prosperity: 100 prosperity = 0.9 (10% discount), 0 prosperity = 1.2 (20% markup)
        base_mod = 1.2 - (self.prosperity / 100.0) * 0.3
        
        # Apply event multipliers
        for evt in self.active_events:
            if "price_mult" in evt.effects:
                base_mod *= evt.effects["price_mult"]
        return max(0.6, min(1.5, base_mod))

    def to_dict(self) -> Dict[str, Any]:
        """Serializes world state to dictionary for JSON saves."""
        return {
            "day": self.day,
            "season": self.season,
            "time_accumulator": self.time_accumulator,
            "prosperity": self.prosperity,
            "danger_level": self.danger_level,
            "active_events": [evt.to_dict() for evt in self.active_events],
            "completed_event_ids": list(self.completed_event_ids)
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores world state from dictionary."""
        self.day = data.get("day", 1)
        self.season = data.get("season", SEASON_SPRING)
        self.time_accumulator = data.get("time_accumulator", 0.0)
        self.prosperity = data.get("prosperity", 50)
        self.danger_level = data.get("danger_level", 20)
        self.active_events = [WorldEvent.from_dict(d) for d in data.get("active_events", [])]
        self.completed_event_ids = set(data.get("completed_event_ids", []))
