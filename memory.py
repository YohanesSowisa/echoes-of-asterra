"""
Echoes of Asterra - Centralized Social Memory & Decay Engine
Records meaningful player actions, calculates memory decay relevance scores,
subscribes to EventBus notifications, and persists records to rpg/saves/memories.json.
"""
import os
import json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Any, Optional
from rpg.events import EventBus

class MemoryCategory(Enum):
    """Categories classifying player social memories."""
    SETTLEMENT = "settlement"
    COMBAT = "combat"
    CRIME = "crime"
    COMMERCE = "commerce"
    WORLD = "world"

# Memory Tag Constants
MEMORY_DONATED_IRON = "donated_iron_ore"
MEMORY_SAVED_FARM = "saved_village_farm"
MEMORY_CLEARED_CRYPT = "cleared_dungeon_crypt"
MEMORY_USED_GREED_ALTAR = "challenged_greed_altar"
MEMORY_KILLED_WOLF_ALPHA = "slain_wolf_alpha"
MEMORY_HELPED_DENNIS = "helped_blacksmith_dennis"
MEMORY_HELPED_SILAS = "traded_with_silas"

@dataclass
class SocialMemory:
    """Stores persistent metadata and decay metrics for a specific player action."""
    memory_id: str
    category: str
    importance: int  # 1 (Minor) to 5 (Legendary)
    created_day: int
    actor: str = "Hero"
    target: str = "World"
    location: str = "Village"
    expiration_days: int = 30
    details: Dict[str, Any] = field(default_factory=dict)

    def calculate_relevance(self, current_day: int) -> float:
        """
        Calculates memory decay relevance score based on importance and recency.
        Relevance = Importance * (1.0 / (1.0 + 0.1 * DaysPassed))
        """
        days_passed = max(0, current_day - self.created_day)
        if days_passed > self.expiration_days and self.importance < 4:
            return 0.0
        decay_factor = 1.0 / (1.0 + 0.1 * days_passed)
        return round(self.importance * decay_factor, 3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "category": self.category,
            "importance": self.importance,
            "created_day": self.created_day,
            "actor": self.actor,
            "target": self.target,
            "location": self.location,
            "expiration_days": self.expiration_days,
            "details": self.details
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SocialMemory':
        return cls(
            memory_id=data["memory_id"],
            category=data.get("category", "settlement"),
            importance=data.get("importance", 1),
            created_day=data.get("created_day", 1),
            actor=data.get("actor", "Hero"),
            target=data.get("target", "World"),
            location=data.get("location", "Village"),
            expiration_days=data.get("expiration_days", 30),
            details=data.get("details", {})
        )

MEMORIES_SAVE_PATH = os.path.join(os.path.dirname(__file__), "saves", "memories.json")

class MemoryManager:
    """
    Centralized Social Memory Engine.
    Records memories, calculates decay relevance scores, subscribes to EventBus,
    and persists records to JSON.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.memories: List[SocialMemory] = []
        self.current_day: int = 1
        if event_bus:
            self.register_event_listeners(event_bus)
        self.load_memories()

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes MemoryManager to EventBus world actions."""
        event_bus.subscribe("quest_completed", self._on_quest_completed)
        event_bus.subscribe("enemy_killed", self._on_enemy_killed)

    def add_memory(
        self,
        memory_id: str,
        category: str,
        importance: int,
        actor: str = "Hero",
        target: str = "World",
        location: str = "Village",
        expiration_days: int = 30,
        details: Optional[Dict[str, Any]] = None
    ) -> SocialMemory:
        """Records a new player memory into the persistent manager."""
        mem = SocialMemory(
            memory_id=memory_id,
            category=category,
            importance=importance,
            created_day=self.current_day,
            actor=actor,
            target=target,
            location=location,
            expiration_days=expiration_days,
            details=details or {}
        )
        self.memories.append(mem)
        self.save_memories()
        return mem

    def get_active_memories(self, category_filter: Optional[str] = None) -> List[SocialMemory]:
        """Returns all non-expired memories ordered by highest relevance score."""
        active = []
        for m in self.memories:
            rel = m.calculate_relevance(self.current_day)
            if rel > 0.0:
                if category_filter is None or m.category == category_filter:
                    active.append(m)
        return sorted(active, key=lambda m: m.calculate_relevance(self.current_day), reverse=True)

    def get_highest_relevance_memory(self, category_filter: Optional[str] = None) -> Optional[SocialMemory]:
        """Returns the single highest scoring active memory."""
        active = self.get_active_memories(category_filter)
        return active[0] if active else None

    def has_memory(self, memory_id: str) -> bool:
        """Checks if a specific memory ID exists and is active."""
        return any(m.memory_id == memory_id and m.calculate_relevance(self.current_day) > 0.0 for m in self.memories)

    def _on_quest_completed(self, quest_id: str, **kwargs: Any) -> None:
        """EventBus callback for completed quests."""
        self.add_memory(
            memory_id=f"quest_completed_{quest_id}",
            category=MemoryCategory.SETTLEMENT.value,
            importance=3,
            target=quest_id,
            details={"quest_id": quest_id}
        )

    def _on_enemy_killed(self, enemy_type: str, enemy_name: str, **kwargs: Any) -> None:
        """EventBus callback for slain elite/boss enemies."""
        if enemy_type in ["boss", "wolf_alpha"]:
            self.add_memory(
                memory_id=f"slain_{enemy_type}",
                category=MemoryCategory.COMBAT.value,
                importance=5 if enemy_type == "boss" else 3,
                target=enemy_name,
                details={"enemy_type": enemy_type}
            )

    def save_memories(self) -> None:
        """Serializes memories to JSON."""
        os.makedirs(os.path.dirname(MEMORIES_SAVE_PATH), exist_ok=True)
        payload = {
            "current_day": self.current_day,
            "memories": [m.to_dict() for m in self.memories]
        }
        try:
            with open(MEMORIES_SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"MemoryManager save warning: {e}")

    def load_memories(self) -> None:
        """Loads serialized memories from JSON."""
        if not os.path.exists(MEMORIES_SAVE_PATH):
            return
        try:
            with open(MEMORIES_SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.current_day = data.get("current_day", 1)
                raw = data.get("memories", [])
                self.memories = [SocialMemory.from_dict(m) for m in raw]
        except Exception as e:
            print(f"MemoryManager load warning: {e}")
