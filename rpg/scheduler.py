"""
Echoes of Asterra - Centralized World Scheduler
Single authority for simulation time and periodic tick events.
Manages in-game timing (minute, hour, day, week, season, year) and dispatches
ticks to subscribed gameplay systems.
"""
from enum import Enum
from typing import Dict, List, Callable, Any, Optional
from rpg.settings import DAY_LENGTH_SECONDS
from rpg.constants import SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER
from rpg.events import EventBus

SEASONS_ORDER = [SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER]

class TickType(str, Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    SEASON = "season"
    YEAR = "year"

class WorldScheduler:
    """
    Centralized World Scheduler.
    Ticks simulation time and dispatches periodic tick events to all registered subscribers.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        
        # Continuous time accumulator (seconds into current day)
        # Start new game at 06:00 AM (6 hours into 24-hour cycle)
        self.time_accumulator: float = (6.0 / 24.0) * DAY_LENGTH_SECONDS
        self.total_real_seconds: float = 0.0
        
        # Calendar tracking
        self.day: int = 1
        self.season_index: int = 0
        self.year: int = 1
        
        # Granular tick counters
        self.total_minutes: int = 0
        self.total_hours: int = 6  # Starts at 06:00
        
        # Subscriptions dictionary mapping TickType str to callbacks
        self._subscribers: Dict[str, List[Callable[..., None]]] = {
            TickType.MINUTE.value: [],
            TickType.HOUR.value: [],
            TickType.DAY.value: [],
            TickType.WEEK.value: [],
            TickType.SEASON.value: [],
            TickType.YEAR.value: []
        }
        
        # Statistics tracking total dispatched ticks for debug telemetry
        self.tick_counts: Dict[str, int] = {
            TickType.MINUTE.value: 0,
            TickType.HOUR.value: 0,
            TickType.DAY.value: 0,
            TickType.WEEK.value: 0,
            TickType.SEASON.value: 0,
            TickType.YEAR.value: 0
        }
        
        # Tracking last triggered discrete minute and hour to prevent duplicate ticks
        self._last_minute: int = int((self.time_accumulator / max(1.0, DAY_LENGTH_SECONDS)) * 24.0 * 60.0)
        self._last_hour: int = int((self.time_accumulator / max(1.0, DAY_LENGTH_SECONDS)) * 24.0)

    @property
    def time_of_day(self) -> float:
        """Returns current in-game hour (0.0 to 24.0)."""
        return (self.time_accumulator / max(1.0, DAY_LENGTH_SECONDS)) * 24.0

    @property
    def hour(self) -> int:
        """Returns current integer hour (0 to 23)."""
        return int(self.time_of_day) % 24

    @property
    def minute(self) -> int:
        """Returns current integer minute (0 to 59)."""
        total_mins = int((self.time_accumulator / max(1.0, DAY_LENGTH_SECONDS)) * 24.0 * 60.0)
        return total_mins % 60

    @property
    def season(self) -> str:
        """Returns current season string."""
        return SEASONS_ORDER[self.season_index % len(SEASONS_ORDER)]

    @property
    def week(self) -> int:
        """Returns current 1-based week number."""
        return ((self.day - 1) // 7) + 1

    def subscribe(self, tick_type: str, callback: Callable[..., None]) -> None:
        """Registers a callback to receive specific tick events."""
        key = str(tick_type)
        if key not in self._subscribers:
            self._subscribers[key] = []
        if callback not in self._subscribers[key]:
            self._subscribers[key].append(callback)

    def unsubscribe(self, tick_type: str, callback: Callable[..., None]) -> None:
        """Removes a registered subscriber callback."""
        key = str(tick_type)
        if key in self._subscribers and callback in self._subscribers[key]:
            self._subscribers[key].remove(callback)

    def get_subscriber_counts(self) -> Dict[str, int]:
        """Returns number of active subscribers per tick type."""
        return {k: len(v) for k, v in self._subscribers.items()}

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Attaches event bus reference."""
        self.event_bus = event_bus

    def update(self, dt: float) -> None:
        """
        Advances simulation clock by dt real seconds.
        Evaluates minute, hour, day, week, season, and year transitions.
        """
        self.total_real_seconds += dt
        self.time_accumulator += dt
        
        # Calculate continuous minutes passed
        seconds_per_min = DAY_LENGTH_SECONDS / (24.0 * 60.0)
        curr_total_mins = int(self.time_accumulator / max(0.001, seconds_per_min))
        
        # Minute ticks
        if curr_total_mins > self._last_minute:
            mins_passed = curr_total_mins - self._last_minute
            for _ in range(mins_passed):
                self._dispatch_tick(TickType.MINUTE.value, minute=self.minute, hour=self.hour, day=self.day)
            self._last_minute = curr_total_mins

        # Hour ticks
        curr_hour = int(self.time_of_day)
        if curr_hour != self._last_hour and curr_hour < 24:
            hours_passed = (curr_hour - self._last_hour) % 24
            for _ in range(hours_passed):
                self.total_hours += 1
                self._dispatch_tick(TickType.HOUR.value, hour=self.hour, day=self.day, season=self.season)
            self._last_hour = curr_hour

        # Day tick condition
        if self.time_accumulator >= DAY_LENGTH_SECONDS:
            self.time_accumulator -= DAY_LENGTH_SECONDS
            self._last_minute = int((self.time_accumulator / max(1.0, DAY_LENGTH_SECONDS)) * 24.0 * 60.0)
            self._last_hour = int(self.time_of_day)
            
            old_day = self.day
            old_week = self.week
            old_season = self.season
            old_year = self.year
            
            self.day += 1
            
            # Recalculate season index (every 30 days)
            self.season_index = ((self.day - 1) // 30) % len(SEASONS_ORDER)
            self.year = ((self.day - 1) // 120) + 1
            
            # Dispatch Day Tick
            self._dispatch_tick(TickType.DAY.value, day=self.day, season=self.season, year=self.year)
            
            # Legacy event bus emit for backward compatibility
            if self.event_bus:
                self.event_bus.emit("day_changed", day=self.day, season=self.season)

            # Week Tick (every 7 days)
            if self.week != old_week:
                self._dispatch_tick(TickType.WEEK.value, week=self.week, day=self.day)

            # Season Tick (every 30 days)
            if self.season != old_season:
                self._dispatch_tick(TickType.SEASON.value, season=self.season, year=self.year)

            # Year Tick (every 120 days)
            if self.year != old_year:
                self._dispatch_tick(TickType.YEAR.value, year=self.year)

    def _dispatch_tick(self, tick_type: str, **kwargs: Any) -> None:
        """Executes subscriber callbacks and emits event signals."""
        self.tick_counts[tick_type] = self.tick_counts.get(tick_type, 0) + 1
        
        # Call direct subscriber callbacks
        for callback in list(self._subscribers.get(tick_type, [])):
            try:
                callback(**kwargs)
            except Exception as e:
                import logging
                logging.error(f"Error executing scheduler subscriber for {tick_type}: {e}")

        # Emit EventBus signals
        if self.event_bus:
            self.event_bus.emit(f"scheduler_tick_{tick_type}", **kwargs)
            self.event_bus.emit(f"{tick_type}_tick", **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes scheduler state."""
        return {
            "time_accumulator": self.time_accumulator,
            "total_real_seconds": self.total_real_seconds,
            "day": self.day,
            "season_index": self.season_index,
            "year": self.year,
            "total_minutes": self.total_minutes,
            "total_hours": self.total_hours,
            "tick_counts": dict(self.tick_counts)
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores scheduler state."""
        if not data:
            return
        self.time_accumulator = data.get("time_accumulator", (6.0 / 24.0) * DAY_LENGTH_SECONDS)
        self.total_real_seconds = data.get("total_real_seconds", 0.0)
        self.day = data.get("day", 1)
        self.season_index = data.get("season_index", 0)
        self.year = data.get("year", 1)
        self.total_minutes = data.get("total_minutes", 0)
        self.total_hours = data.get("total_hours", 6)
        if "tick_counts" in data:
            self.tick_counts.update(data["tick_counts"])
        self._last_minute = int((self.time_accumulator / max(1.0, DAY_LENGTH_SECONDS)) * 24.0 * 60.0)
        self._last_hour = int(self.time_of_day)
