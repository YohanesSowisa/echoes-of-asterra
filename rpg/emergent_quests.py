"""
Echoes of Asterra - Emergent Dynamic Quest Generator
Evaluates simulation state (danger, ecology, trade, guard status) on day ticks
and dynamically injects context-aware emergent quests into QuestManager.
"""
from typing import Dict, Any, Optional, Set
from rpg.events import EventBus
from rpg.quests import Quest, QuestObjective, QuestManager
from rpg.constants import QUEST_ACTIVE

class EmergentQuestGenerator:
    """
    Evaluates Living World simulation metrics and generates dynamic context-driven quests.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.active_emergent_ids: Set[str] = set()

    def evaluate_world(self, world_state: Any, quest_manager: QuestManager, day: int) -> Optional[Quest]:
        """
        Evaluates world conditions on Day Ticks and creates dynamic quests if criteria are met.
        """
        if not world_state or not quest_manager:
            return None

        danger_level = getattr(world_state, "danger_level", 0.0)
        guard_strength = getattr(world_state, "guard_strength", 50.0)
        road_safety = getattr(world_state, "road_safety", 50.0)

        # 1. High Danger & Low Guard Strength -> Emergency Militia Patrol
        quest_id = f"emergent_militia_day_{day}"
        if danger_level >= 50.0 and guard_strength < 60.0 and quest_id not in self.active_emergent_ids:
            new_quest = Quest(
                quest_id=quest_id,
                title=f"[Emergent] Village Guard Crisis (Day {day})",
                description=f"Rising danger ({int(danger_level)}%) has strained guard patrols. Help Guard Dennis neutralize 4 Skeletons to stabilize Asterra.",
                objectives=[
                    QuestObjective("Defeat 4 Skeletons", "kill", "skeleton", 4)
                ],
                rewards={
                    "exp": 180,
                    "gold": 120,
                    "items": [("Iron Ore", 2), ("Red Potion", 2)]
                }
            )
            new_quest.status = QUEST_ACTIVE
            quest_manager.quests[quest_id] = new_quest
            self.active_emergent_ids.add(quest_id)
            if self.event_bus:
                self.event_bus.emit("emergent_quest_generated", quest=new_quest)
            return new_quest

        # 2. Low Road Safety -> Caravan Highway Clearance
        quest_id_caravan = f"emergent_caravan_day_{day}"
        if road_safety < 50.0 and quest_id_caravan not in self.active_emergent_ids:
            new_quest = Quest(
                quest_id=quest_id_caravan,
                title=f"[Emergent] Highway Clearance (Day {day})",
                description=f"Road safety has fallen to {int(road_safety)}%. Clear 3 Goblins blocking the trade highway for Merchant Silas.",
                objectives=[
                    QuestObjective("Defeat 3 Goblins", "kill", "goblin", 3)
                ],
                rewards={
                    "exp": 160,
                    "gold": 140,
                    "items": [("Baked Bread", 3), ("Blue Potion", 2)]
                }
            )
            new_quest.status = QUEST_ACTIVE
            quest_manager.quests[quest_id_caravan] = new_quest
            self.active_emergent_ids.add(quest_id_caravan)
            if self.event_bus:
                self.event_bus.emit("emergent_quest_generated", quest=new_quest)
            return new_quest

        # 3. High Leyline Spore Rot (rot_level >= 60%) -> Emergency Leyline Purification
        quest_id_rot = f"emergent_spore_rot_day_{day}"
        mm = getattr(world_state, "mire_manager", None)
        rot_level = getattr(mm, "rot_level", 0.0) if mm else getattr(world_state, "mire_rot_level", 0.0)
        if rot_level >= 60.0 and quest_id_rot not in self.active_emergent_ids:
            new_quest = Quest(
                quest_id=quest_id_rot,
                title=f"[Emergent] Leyline Spore Blight Crisis (Day {day})",
                description=f"Leyline Rot has reached critical levels ({int(rot_level)}%). Defeat 3 Spore-Host Wolves in the Forest to curb the toxic epidemic!",
                objectives=[
                    QuestObjective("Defeat 3 Spore-Host Wolves", "kill", "spore_host_wolf", 3)
                ],
                rewards={
                    "exp": 220,
                    "gold": 160,
                    "items": [("Mire Cleansing Draught", 2), ("Starlight Crystal", 1)]
                }
            )
            new_quest.status = QUEST_ACTIVE
            quest_manager.quests[quest_id_rot] = new_quest
            self.active_emergent_ids.add(quest_id_rot)
            if self.event_bus:
                self.event_bus.emit("emergent_quest_generated", quest=new_quest)
            return new_quest

        return None

    def reset(self) -> None:
        """Resets tracked emergent quest IDs."""
        self.active_emergent_ids.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes emergent quest generator state."""
        return {"active_emergent_ids": list(self.active_emergent_ids)}

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes emergent quest generator state."""
        if data and "active_emergent_ids" in data:
            self.active_emergent_ids = set(data["active_emergent_ids"])
