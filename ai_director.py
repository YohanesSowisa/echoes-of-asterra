"""
Echoes of Asterra - Decoupled Adaptive AI Director & Pacing Observer
Observes player state, combat stress, idle time, and world metrics.
Emits high-level system signals via EventBus to modulate encounter pacing
without acting as a God Object.
"""
from typing import Dict, Any, Optional
from rpg.events import EventBus

class AIDirector:
    """
    Decoupled observer engine monitoring player engagement and pacing.
    Emits events to stimulate world reactivity.
    """
    def __init__(self) -> None:
        self.event_bus: Optional[EventBus] = None
        self.idle_time = 0.0
        self.check_timer = 0.0

    def register_event_listeners(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def update(self, dt: float, player: Any, world_state: Any) -> None:
        """
        Monitors player movement vectors, HP levels, and idle duration.
        Dispatches pacing signals periodically.
        """
        self.check_timer += dt
        
        # Track player idle status
        if hasattr(player, "velocity") and player.velocity.magnitude() == 0:
            self.idle_time += dt
        else:
            self.idle_time = 0.0

        # Evaluate pacing every 15 seconds
        if self.check_timer >= 15.0:
            self.check_timer = 0.0
            
            if not self.event_bus or not player or not world_state:
                return

            # 1. Player struggling (low HP) -> notify world to send support or merchant
            if hasattr(player, "hp") and hasattr(player, "max_hp"):
                if player.hp / player.max_hp < 0.3:
                    self.event_bus.emit("pacing_player_struggling", hp_ratio=player.hp / player.max_hp)

            # 2. Prolonged idle time (over 30s) -> stimulate ambient encounters
            if self.idle_time >= 30.0:
                self.event_bus.emit("pacing_exploration_lull", idle_seconds=self.idle_time)

            # 3. High world danger -> signal faction war / guard activity increase
            if hasattr(world_state, "danger_level") and world_state.danger_level > 60.0:
                self.event_bus.emit("pacing_danger_spiked", danger=world_state.danger_level)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes director state."""
        return {"idle_time": self.idle_time, "check_timer": self.check_timer}

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes director state."""
        if data:
            self.idle_time = data.get("idle_time", 0.0)
            self.check_timer = data.get("check_timer", 0.0)
