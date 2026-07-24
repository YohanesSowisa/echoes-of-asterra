"""
Echoes of Asterra - Job-Simulated NPC Schedules & Routines System
Simulates 24-hour daily schedules for all NPCs.
NPCs autonomously perform economic jobs (smithing gear, mining ore, gathering herbs, trading)
and walk between work, social, and rest waypoints based on in-game time of day.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
from rpg.settings import TILE_SIZE, GRID_WIDTH, GRID_HEIGHT
from rpg.events import EventBus

@dataclass
class ScheduleTask:
    """Represents a specific routine task for an NPC at a time window."""
    start_hour: float
    end_hour: float
    map_name: str
    target_pos: Tuple[float, float]
    activity: str        # "work", "socialize", "rest", "patrol"
    resource_produced: Optional[str] = None
    production_rate: float = 0.0

class NPCScheduleManager:
    """
    Manages 24-hour job routines and waypoint pathing for all key NPCs in Asterra.
    """
    def __init__(self) -> None:
        self.event_bus: Optional[EventBus] = None
        
        # Define 24-hour schedules per NPC key
        self.schedules: Dict[str, List[ScheduleTask]] = {
            "dennis": [
                # Dennis (Blacksmith): Smiths iron ore at Forge in morning -> Plaza in afternoon -> Home rest
                ScheduleTask(6.0, 13.0, "village", ((GRID_WIDTH - 7) * TILE_SIZE, 10 * TILE_SIZE), "work", resource_produced="ore", production_rate=1.5),
                ScheduleTask(13.0, 19.0, "village", (GRID_WIDTH // 2 * TILE_SIZE, 12 * TILE_SIZE), "socialize"),
                ScheduleTask(19.0, 6.0, "village", ((GRID_WIDTH - 7) * TILE_SIZE, 6 * TILE_SIZE), "rest")
            ],
            "silas": [
                # Silas (Merchant): Manages Shop -> Market Plaza -> Rest
                ScheduleTask(7.0, 18.0, "village", (6.5 * TILE_SIZE, (GRID_HEIGHT - 11) * TILE_SIZE), "work", resource_produced="goods", production_rate=1.0),
                ScheduleTask(18.0, 22.0, "village", (GRID_WIDTH // 2 * TILE_SIZE, (GRID_HEIGHT - 8) * TILE_SIZE), "socialize"),
                ScheduleTask(22.0, 7.0, "village", (6.5 * TILE_SIZE, (GRID_HEIGHT - 6) * TILE_SIZE), "rest")
            ],
            "garth": [
                # Garth (Miner): Mines in Cave -> Transports ore to Village -> Rest
                ScheduleTask(6.0, 16.0, "cave", (GRID_WIDTH // 2 * TILE_SIZE, (GRID_HEIGHT // 2 + 2) * TILE_SIZE), "work", resource_produced="ore", production_rate=2.0),
                ScheduleTask(16.0, 20.0, "village", ((GRID_WIDTH - 7) * TILE_SIZE, 12 * TILE_SIZE), "socialize"),
                ScheduleTask(20.0, 6.0, "cave", (GRID_WIDTH // 4 * TILE_SIZE, GRID_HEIGHT // 4 * TILE_SIZE), "rest")
            ],
            "faye": [
                # Faye (Ranger): Patrols Forest & gathers herbs -> Campfire
                ScheduleTask(6.0, 18.0, "forest", (7 * TILE_SIZE, 7 * TILE_SIZE), "work", resource_produced="herbs", production_rate=1.5),
                ScheduleTask(18.0, 6.0, "forest", (8 * TILE_SIZE, 8 * TILE_SIZE), "rest")
            ],
            "eldrin": [
                # Elder Eldrin: Town Hall -> Plaza -> Rest
                ScheduleTask(8.0, 14.0, "village", (6.5 * TILE_SIZE, 10 * TILE_SIZE), "work"),
                ScheduleTask(14.0, 20.0, "village", (GRID_WIDTH // 2 * TILE_SIZE, 10 * TILE_SIZE), "socialize"),
                ScheduleTask(20.0, 8.0, "village", (6.5 * TILE_SIZE, 6 * TILE_SIZE), "rest")
            ],
            "kai": [
                # Kai (Guardian): Patrols Fishing Dock -> Rest
                ScheduleTask(6.0, 19.0, "lake", (9 * TILE_SIZE, (GRID_HEIGHT // 2) * TILE_SIZE), "work", resource_produced="food", production_rate=1.2),
                ScheduleTask(19.0, 6.0, "lake", (6 * TILE_SIZE, (GRID_HEIGHT // 2) * TILE_SIZE), "rest")
            ]
        }
        self.work_timer = 0.0

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Stores event bus reference for production triggers."""
        self.event_bus = event_bus

    def get_current_task(self, npc_type: str, time_of_day: float) -> Optional[ScheduleTask]:
        """Returns active task for an NPC at the given hour (0-24)."""
        tasks = self.schedules.get(npc_type, [])
        for task in tasks:
            if task.start_hour < task.end_hour:
                if task.start_hour <= time_of_day < task.end_hour:
                    return task
            else:  # Overnight task (e.g. 19:00 to 06:00)
                if time_of_day >= task.start_hour or time_of_day < task.end_hour:
                    return task
        return tasks[0] if tasks else None

    def update(self, dt: float, time_of_day: float, active_npcs: List[Any], current_map: str) -> None:
        """
        Updates NPC positions, waypoint walking towards active job locations,
        and emits resource production events when NPCs are working.
        """
        self.work_timer += dt
        should_produce = False
        if self.work_timer >= 10.0:  # Every 10 seconds of gameplay, working NPCs produce stock
            self.work_timer = 0.0
            should_produce = True

        for npc in active_npcs:
            npc_type = getattr(npc, "npc_type", None)
            if not npc_type:
                continue

            task = self.get_current_task(npc_type, time_of_day)
            if not task:
                continue

            # Update NPC status tag
            npc.current_activity = task.activity

            # If task target map matches current map, interpolate NPC position toward waypoint
            if task.map_name == current_map:
                target_x, target_y = task.target_pos
                dx = target_x - npc.pos.x
                dy = target_y - npc.pos.y
                dist = (dx * dx + dy * dy) ** 0.5

                if dist > 4.0:  # Smoothly walk toward target waypoint
                    move_speed = 60.0 * dt
                    npc.pos.x += (dx / dist) * min(dist, move_speed)
                    npc.pos.y += (dy / dist) * min(dist, move_speed)
                    npc.rect.center = (int(npc.pos.x), int(npc.pos.y))
                    npc.hitbox.center = npc.rect.center

            # Trigger production if working
            if should_produce and task.activity == "work" and task.resource_produced and self.event_bus:
                self.event_bus.emit("npc_produced_resource", resource_type=task.resource_produced, amount=task.production_rate)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes schedule states."""
        return {"work_timer": self.work_timer}

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes schedule states."""
        if data:
            self.work_timer = data.get("work_timer", 0.0)
