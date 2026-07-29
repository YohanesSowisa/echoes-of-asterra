"""
Echoes of Asterra - Persistent NPC Memory & Relationship System
Tracks hero interactions, crimes witnessed, gifts given, and quests completed for each NPC.
Drives dynamic dialogue greetings, rumor propagation, price discounts, and interaction refusals.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from rpg.constants import (
    REL_ENEMY, REL_STRANGER, REL_ACQUAINTANCE, REL_FRIEND, REL_CLOSE_FRIEND
)
from rpg.events import EventBus

@dataclass
class NPCMemory:
    """Stores persistent historical context and relationship score for a specific NPC."""
    npc_id: str
    relationship: int = 0  # Range: -100 to +100
    times_talked: int = 0
    times_attacked: int = 0
    gifts_given: List[str] = field(default_factory=list)
    quests_completed_for: List[str] = field(default_factory=list)
    crimes_witnessed: List[str] = field(default_factory=list)
    last_interaction_day: int = 0

    @property
    def friendship_level(self) -> str:
        if self.relationship <= -30:
            return REL_ENEMY
        elif self.relationship < 15:
            return REL_STRANGER
        elif self.relationship < 40:
            return REL_ACQUAINTANCE
        elif self.relationship < 75:
            return REL_FRIEND
        else:
            return REL_CLOSE_FRIEND

    def to_dict(self) -> Dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "relationship": self.relationship,
            "times_talked": self.times_talked,
            "times_attacked": self.times_attacked,
            "gifts_given": self.gifts_given,
            "quests_completed_for": self.quests_completed_for,
            "crimes_witnessed": self.crimes_witnessed,
            "last_interaction_day": self.last_interaction_day
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NPCMemory':
        return cls(
            npc_id=data["npc_id"],
            relationship=data.get("relationship", 0),
            times_talked=data.get("times_talked", 0),
            times_attacked=data.get("times_attacked", 0),
            gifts_given=data.get("gifts_given", []),
            quests_completed_for=data.get("quests_completed_for", []),
            crimes_witnessed=data.get("crimes_witnessed", []),
            last_interaction_day=data.get("last_interaction_day", 0)
        )

class NPCMemoryManager:
    """
    Manages memories for all non-player characters in Asterra.
    """
    def __init__(self) -> None:
        self.memories: Dict[str, NPCMemory] = {}

    def get_memory(self, npc_id: str) -> NPCMemory:
        """Retrieves or creates memory object for an NPC."""
        if npc_id not in self.memories:
            self.memories[npc_id] = NPCMemory(npc_id=npc_id)
        return self.memories[npc_id]

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes to global EventBus topics."""
        event_bus.subscribe("npc_talked", self._on_npc_talked)
        event_bus.subscribe("npc_attacked", self._on_npc_attacked)
        event_bus.subscribe("quest_completed", self._on_quest_completed)
        event_bus.subscribe("day_changed", self._on_day_changed)

    def modify_relationship(self, npc_id: str, amount: int) -> None:
        """Adjusts relationship score for an NPC."""
        mem = self.get_memory(npc_id)
        mem.relationship = max(-100, min(100, mem.relationship + amount))

    def record_gift(self, npc_id: str, item_name: str, value_bonus: int = 10) -> None:
        """Records a gift given to an NPC."""
        mem = self.get_memory(npc_id)
        mem.gifts_given.append(item_name)
        self.modify_relationship(npc_id, value_bonus)

    def get_greeting_prefix(self, npc_id: str) -> str:
        """Returns dynamic dialogue prefix based on relationship status."""
        mem = self.get_memory(npc_id)
        level = mem.friendship_level

        if level == REL_ENEMY:
            return "Get away from me, villain! I will not speak with you."
        elif level == REL_FRIEND:
            return "Ah, good to see you again my friend!"
        elif level == REL_CLOSE_FRIEND:
            return "Welcome back, my trusted ally! It is always an honor."
        elif level == REL_ACQUAINTANCE:
            return "Greetings traveler. Good to see you again."
        return ""  # Stranger = standard dialogue

    def _on_npc_talked(self, npc_id: str = "", current_day: int = 1, **kwargs: Any) -> None:
        """Increments conversation counter and boosts relationship slightly once per day."""
        mem = self.get_memory(npc_id)
        mem.times_talked += 1
        if mem.last_interaction_day < current_day:
            mem.last_interaction_day = current_day
            self.modify_relationship(npc_id, 2)  # +2 per first talk each day

    def _on_npc_attacked(self, npc_id: str = "", witnesses: Optional[List[str]] = None, **kwargs: Any) -> None:
        """Severely reduces relationship when hero attacks NPCs or witnesses attack."""
        mem = self.get_memory(npc_id)
        mem.times_attacked += 1
        self.modify_relationship(npc_id, -30)
        
        # Witnesses also dislike hero
        if witnesses:
            for wit_id in witnesses:
                if wit_id != npc_id:
                    wit_mem = self.get_memory(wit_id)
                    wit_mem.crimes_witnessed.append(f"Attacked {npc_id}")
                    self.modify_relationship(wit_id, -15)

    def _on_quest_completed(self, quest_id: str = "", **kwargs: Any) -> None:
        """Completing NPC quests significantly improves relationship."""
        # Map quests to specific NPCs
        quest_npc_map = {
            "main_quest": "Eldrin",
            "forest_patrol": "Faye",
            "scholar_quest": "Mira",
            "blacksmith_quest": "Dennis",
            "lake_quest": "Kai"
        }
        target_npc = quest_npc_map.get(quest_id)
        if target_npc:
            mem = self.get_memory(target_npc)
            if quest_id not in mem.quests_completed_for:
                mem.quests_completed_for.append(quest_id)
                self.modify_relationship(target_npc, 25)

    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        """Propagates rumors between NPCs on day ticks."""
        # Check if any NPC witnessed crimes, propagate to others
        notable_crimes = []
        for mem in self.memories.values():
            if mem.crimes_witnessed:
                notable_crimes.extend(mem.crimes_witnessed)

        if notable_crimes:
            # Spread negative rumors slowly to other NPCs
            for mem in self.memories.values():
                if mem.relationship > -50 and len(mem.crimes_witnessed) == 0:
                    self.modify_relationship(mem.npc_id, -2)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes memories to dictionary for saves."""
        return {npc_id: mem.to_dict() for npc_id, mem in self.memories.items()}

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores memories from dictionary."""
        self.memories.clear()
        for npc_id, mem_data in data.items():
            self.memories[npc_id] = NPCMemory.from_dict(mem_data)
