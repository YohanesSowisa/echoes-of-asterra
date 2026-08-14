"""
Echoes of Asterra - Dynamic World State Simulation & Snapshot API
Tracks continuous world progression: days, seasons, prosperity, danger levels, and dynamic world events.
Drives weather biases, shop price modifiers, enemy spawn scaling, and provides immutable WorldSnapshots.
"""
import random
from dataclasses import dataclass, field
from typing import List, Set, Dict, Any, Optional, Tuple
from rpg.constants import (
    SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER,
    EVENT_VILLAGE_FESTIVAL, EVENT_MERCHANT_CARAVAN, EVENT_BANDIT_INVASION,
    EVENT_HARVEST_SEASON
)
from rpg.settings import DAY_LENGTH_SECONDS
from rpg.events import EventBus

SEASONS_ORDER = [SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER]

@dataclass(frozen=True)
class WorldSnapshot:
    """
    Lightweight immutable snapshot representing current simulation state.
    Consumed strictly by GameDirector without allowing direct state mutation.
    """
    day: int
    season: str
    time_of_day: float
    prosperity: int              # 0 (desolate) to 100 (thriving)
    guard_strength: float        # 0.0 to 100.0
    bandit_strength: float       # 0.0 to 100.0
    road_safety: float           # 0.0 to 100.0
    danger_level: float          # 0.0 (peaceful) to 100.0 (crisis)
    trade_activity: float        # 0.0 to 100.0
    weather: str
    active_crisis: Optional[str]
    population: int
    player_wealth: int
    player_level: int
    player_hp_ratio: float
    reputation: float
    memory_stats: Dict[str, Any]
    recent_deaths: int
    combat_win_rate: float
    monster_density: float
    faction_stability: float
    active_events: Tuple[str, ...]

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
    Provides immutable WorldSnapshot objects for system observers.
    """
    def __init__(self) -> None:
        self.day: int = 1
        self.season: str = SEASON_SPRING
        # Start new game at 06:00 AM (6 hours into 24-hour cycle)
        self.time_accumulator: float = (6.0 / 24.0) * DAY_LENGTH_SECONDS
        self.prosperity: int = 50       # 0 to 100
        self.danger_level: int = 20     # 0 to 100
        
        # Extended world metrics
        self.guard_strength: float = 60.0
        self.bandit_strength: float = 40.0
        self.road_safety: float = 50.0
        self.trade_activity: float = 50.0
        self.population: int = 120
        self.monster_density: float = 30.0
        self.faction_stability: float = 65.0
        
        self.active_events: List[WorldEvent] = []
        self.completed_event_ids: Set[str] = set()
        
        # Track daily counters for drift calculations
        self._enemies_killed_today: int = 0
        self._quests_completed_today: int = 0
        self.recent_deaths: int = 0
        self._combat_wins: int = 0
        self._combat_losses: int = 0

    @property
    def time_of_day(self) -> float:
        """Returns in-game hour (0.0 to 24.0) calculated from time accumulator."""
        return (self.time_accumulator / max(1.0, DAY_LENGTH_SECONDS)) * 24.0

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes WorldState to relevant global events."""
        event_bus.subscribe("enemy_killed", self._on_enemy_killed)
        event_bus.subscribe("quest_completed", self._on_quest_completed)
        event_bus.subscribe("player_died", self._on_player_died)

    def _on_enemy_killed(self, **kwargs: Any) -> None:
        self._enemies_killed_today += 1
        self._combat_wins += 1

    def _on_quest_completed(self, **kwargs: Any) -> None:
        self._quests_completed_today += 1

    def _on_player_died(self, **kwargs: Any) -> None:
        self.recent_deaths += 1
        self._combat_losses += 1

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

        # Dynamic drift of secondary metrics
        self.road_safety = max(0.0, min(100.0, 50.0 + (self.guard_strength - self.bandit_strength) * 0.5))
        self.trade_activity = max(0.0, min(100.0, (self.prosperity * 0.6) + (self.road_safety * 0.4)))

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
        extra_danger = 0
        for evt in self.active_events:
            extra_danger += evt.effects.get("danger_boost", 0)
        total_danger = min(100, self.danger_level + extra_danger)
        return 1.0 + (total_danger * 0.005)

    def get_price_modifier(self) -> float:
        """Returns shop price multiplier based on prosperity and active events."""
        base_mod = 1.2 - (self.prosperity / 100.0) * 0.3
        for evt in self.active_events:
            if "price_mult" in evt.effects:
                base_mod *= evt.effects["price_mult"]
        return max(0.6, min(1.5, base_mod))

    def create_snapshot(self, game_context: Any = None) -> WorldSnapshot:
        """
        Generates a lightweight immutable WorldSnapshot representing the current world state.
        Safely extracts player, reputation, and memory stats from optional game_context.
        """
        player_wealth = 0
        player_level = 1
        player_hp_ratio = 1.0
        reputation = 0.0
        memory_stats: Dict[str, Any] = {"active_memories": 0}
        active_crisis: Optional[str] = None
        weather = "clear"

        if game_context:
            # Extract player properties
            player = getattr(game_context, "player", None)
            if player:
                player_wealth = getattr(player, "gold", 0)
                player_level = getattr(player, "level", 1)
                max_hp = max(1, getattr(player, "max_hp", 100))
                player_hp_ratio = getattr(player, "hp", max_hp) / max_hp

            # Extract reputation
            rep_mgr = getattr(game_context, "reputation_manager", None)
            if rep_mgr and hasattr(rep_mgr, "global_reputation"):
                reputation = float(rep_mgr.global_reputation)

            # Extract memory stats
            mem_mgr = getattr(game_context, "memory_manager", None)
            if mem_mgr and hasattr(mem_mgr, "memories"):
                memory_stats = {"active_memories": len(mem_mgr.memories)}

            # Extract weather
            weather_sys = getattr(game_context, "weather", None)
            if weather_sys and hasattr(weather_sys, "current_weather"):
                weather = str(weather_sys.current_weather)

        # Detect active crisis from active events
        for evt in self.active_events:
            if "invasion" in evt.event_id or "outbreak" in evt.event_id or "crisis" in evt.event_id:
                active_crisis = evt.name
                break

        # Calculate combat win rate
        total_battles = self._combat_wins + self._combat_losses
        win_rate = (self._combat_wins / float(total_battles)) if total_battles > 0 else 0.5

        return WorldSnapshot(
            day=int(self.day),
            season=str(self.season),
            time_of_day=float(self.time_of_day),
            prosperity=int(self.prosperity),
            guard_strength=float(self.guard_strength),
            bandit_strength=float(self.bandit_strength),
            road_safety=float(self.road_safety),
            danger_level=float(self.danger_level),
            trade_activity=float(self.trade_activity),
            weather=weather,
            active_crisis=active_crisis,
            population=int(self.population),
            player_wealth=int(player_wealth),
            player_level=int(player_level),
            player_hp_ratio=float(player_hp_ratio),
            reputation=float(reputation),
            memory_stats=dict(memory_stats),
            recent_deaths=int(self.recent_deaths),
            combat_win_rate=float(win_rate),
            monster_density=float(self.monster_density),
            faction_stability=float(self.faction_stability),
            active_events=tuple(evt.name for evt in self.active_events)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes world state to dictionary for JSON saves."""
        return {
            "day": self.day,
            "season": self.season,
            "time_accumulator": self.time_accumulator,
            "prosperity": self.prosperity,
            "danger_level": self.danger_level,
            "guard_strength": self.guard_strength,
            "bandit_strength": self.bandit_strength,
            "road_safety": self.road_safety,
            "trade_activity": self.trade_activity,
            "population": self.population,
            "monster_density": self.monster_density,
            "faction_stability": self.faction_stability,
            "recent_deaths": self.recent_deaths,
            "combat_wins": self._combat_wins,
            "combat_losses": self._combat_losses,
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
        self.guard_strength = data.get("guard_strength", 60.0)
        self.bandit_strength = data.get("bandit_strength", 40.0)
        self.road_safety = data.get("road_safety", 50.0)
        self.trade_activity = data.get("trade_activity", 50.0)
        self.population = data.get("population", 120)
        self.monster_density = data.get("monster_density", 30.0)
        self.faction_stability = data.get("faction_stability", 65.0)
        self.recent_deaths = data.get("recent_deaths", 0)
        self._combat_wins = data.get("combat_wins", 0)
        self._combat_losses = data.get("combat_losses", 0)
        self.active_events = [WorldEvent.from_dict(d) for d in data.get("active_events", [])]
        self.completed_event_ids = set(data.get("completed_event_ids", []))

    def reset(self) -> None:
        """Resets world state simulation metrics to starting defaults."""
        self.day = 1
        self.season = SEASON_SPRING
        self.time_accumulator = 0.0
        self.prosperity = 50.0
        self.danger_level = 20.0
        self.guard_strength = 60.0
        self.bandit_strength = 40.0
        self.road_safety = 50.0
        self.trade_activity = 50.0
        self.population = 120
        self.monster_density = 30.0
        self.faction_stability = 65.0
        self.recent_deaths = 0
        self._combat_wins = 0
        self._combat_losses = 0
        self._enemies_killed_today = 0
        self._quests_completed_today = 0
        self.active_events.clear()
        self.completed_event_ids.clear()
