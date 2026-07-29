"""
Echoes of Asterra - Separate Reputation & Emergent Title Engine
Manages separated Global Reputation, NPC Personal Relationships, and Faction Reputation.
Calculates Social Recognition Tiers and generates Emergent Player Titles dynamically from memories.
Persists records to rpg/saves/social_reputation.json.
"""
import os
from typing import Dict, List, Any, Optional

from rpg.events import EventBus
from rpg.memory import MemoryManager

# Social Recognition Tiers Constants
TIER_UNKNOWN = "Unknown"
TIER_RECOGNIZED = "Recognized"
TIER_TRUSTED = "Trusted"
TIER_RESPECTED = "Respected"
TIER_FRIEND = "Friend"
TIER_HERO = "Hero"
TIER_LEGEND = "Legend"

# Emergent Title Constants
TITLE_WANDERER = "The Wanderer"
TITLE_IRON_BENEFACTOR = "Iron Benefactor"
TITLE_CRYPT_DELVER = "Crypt Delver"
TITLE_SCOURGE_OF_BANDITS = "Scourge of Bandits"
TITLE_GUARDIAN_OF_ASTERRA = "Guardian of Asterra"
TITLE_GREED_CHALLENGER = "Greed Challenger"

def get_recognition_tier(reputation_score: int) -> str:
    """Calculates social recognition tier based on reputation score (-100 to +100)."""
    if reputation_score <= -30:
        return "Hostile"
    elif reputation_score < 15:
        return TIER_UNKNOWN
    elif reputation_score < 35:
        return TIER_RECOGNIZED
    elif reputation_score < 55:
        return TIER_TRUSTED
    elif reputation_score < 75:
        return TIER_RESPECTED
    elif reputation_score < 90:
        return TIER_FRIEND
    elif reputation_score < 100:
        return TIER_HERO
    else:
        return TIER_LEGEND

class TitleEngine:
    """Evaluates accumulated memories and reputation to generate dynamic emergent player titles."""
    @staticmethod
    def evaluate_titles(memory_manager: MemoryManager, global_reputation: int) -> List[str]:
        titles = [TITLE_WANDERER]

        if memory_manager.has_memory("donated_iron_ore") or memory_manager.has_memory("quest_completed_dennis_ore"):
            titles.append(TITLE_IRON_BENEFACTOR)

        if memory_manager.has_memory("cleared_dungeon_crypt") or memory_manager.has_memory("quest_completed_crypt_clear"):
            titles.append(TITLE_CRYPT_DELVER)

        if memory_manager.has_memory("slain_bandit_captain") or memory_manager.has_memory("quest_completed_bandit_raid"):
            titles.append(TITLE_SCOURGE_OF_BANDITS)

        if memory_manager.has_memory("challenged_greed_altar"):
            titles.append(TITLE_GREED_CHALLENGER)

        if global_reputation >= 85 and len(titles) >= 3:
            titles.append(TITLE_GUARDIAN_OF_ASTERRA)

        return titles

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOCIAL_SAVE_PATH = os.path.join(BASE_DIR, "saves", "social_reputation.json")


class ReputationManager:
    """
    Centralized Social Reputation Engine.
    Tracks separated Global Reputation, NPC Personal Bonds, and Emergent Titles.
    """
    def __init__(self, event_bus: Optional[EventBus] = None, memory_manager: Optional[MemoryManager] = None) -> None:
        self.global_reputation: int = 0  # 0 to 100
        self.npc_relationships: Dict[str, int] = {
            "Eldrin": 10,
            "Dennis": 0,
            "Silas": 0,
            "Faye": 5,
            "Mira": 0,
            "Kai": 0,
            "Garth": 0
        }
        self.unlocked_titles: List[str] = [TITLE_WANDERER]
        self.active_title: str = TITLE_WANDERER
        self.memory_manager = memory_manager

        if event_bus:
            self.register_event_listeners(event_bus)

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes ReputationManager to EventBus actions."""
        event_bus.subscribe("quest_completed", self._on_quest_completed)

    def modify_global_reputation(self, amount: int) -> None:
        """Modifies global fame/heroism reputation score."""
        self.global_reputation = max(0, min(100, self.global_reputation + amount))
        self.update_titles()

    def modify_npc_relationship(self, npc_id: str, amount: int) -> None:
        """Modifies personal bond score with a specific NPC (-100 to +100)."""
        curr = self.npc_relationships.get(npc_id, 0)
        new_val = max(-100, min(100, curr + amount))
        self.npc_relationships[npc_id] = new_val
        # Sync with MemoryManager relationship score if available
        if self.memory_manager:
            mem = self.memory_manager.get_memory(npc_id)
            mem.relationship = new_val

    def get_npc_tier(self, npc_id: str) -> str:
        """Returns the Social Recognition Tier for a specific NPC."""
        score = self.npc_relationships.get(npc_id, 0)
        return get_recognition_tier(score)

    def get_global_tier(self) -> str:
        """Returns worldwide fame Social Recognition Tier."""
        return get_recognition_tier(self.global_reputation)

    def update_titles(self, game: Optional[Any] = None) -> None:
        """Re-evaluates emergent player titles from memories and reputation."""
        if self.memory_manager:
            new_titles = TitleEngine.evaluate_titles(self.memory_manager, self.global_reputation)
            for t in new_titles:
                if t not in self.unlocked_titles:
                    self.unlocked_titles.append(t)
                    self.active_title = t
                    if game and hasattr(game, "notification_manager"):
                        from rpg.notification import NotificationPriority
                        game.notification_manager.push_toast(f"👑 New Title Unlocked: {t}!", priority=NotificationPriority.HIGH)

    def _on_quest_completed(self, quest_id: str, **kwargs: Any) -> None:
        """Callback increasing global reputation on quest completion."""
        self.modify_global_reputation(10)
        self.update_titles(game=kwargs.get("game"))


    def to_dict(self) -> Dict[str, Any]:
        """Serializes reputation and titles to dictionary payload for slot saving."""
        return {
            "global_reputation": self.global_reputation,
            "npc_relationships": self.npc_relationships,
            "unlocked_titles": self.unlocked_titles,
            "active_title": self.active_title
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Loads serialized reputation and titles from dictionary payload."""
        if not data:
            return
        self.global_reputation = data.get("global_reputation", 0)
        self.npc_relationships = data.get("npc_relationships", self.npc_relationships)
        self.unlocked_titles = data.get("unlocked_titles", [TITLE_WANDERER])
        self.active_title = data.get("active_title", TITLE_WANDERER)

    def save_social_data(self) -> None:
        """Legacy helper for backward compatibility (delegates to per-slot save payload)."""
        pass

    def load_social_data(self) -> None:
        """Legacy helper for backward compatibility."""
        pass
