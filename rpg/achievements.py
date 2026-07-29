"""
Echoes of Asterra - Achievement System
Tracks player milestones, listens to EventBus signals, awards badges,
and persists achievement progress to saves/achievements.json.
"""
import os
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional

from rpg.events import EventBus

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACHIEVEMENTS_SAVE_PATH = os.path.join(BASE_DIR, "saves", "achievements.json")


@dataclass
class Achievement:
    id: str
    title: str
    description: str
    category: str  # "Combat", "Exploration", "Economy", "Story"
    unlocked: bool = False
    unlocked_at: Optional[str] = None
    icon_symbol: str = "🏆"


class AchievementManager:
    """
    Manages achievement definitions, tracks criteria, subscribes to EventBus,
    and triggers CelebrationManager when milestones are achieved.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.achievements: Dict[str, Achievement] = {}
        self._init_default_achievements()
        self.load_achievements()

        if self.event_bus:
            self._register_event_listeners()

    def _init_default_achievements(self) -> None:
        defaults = [
            Achievement("first_blood", "First Blood", "Defeat your first enemy in combat.", "Combat", icon_symbol="⚔️"),
            Achievement("monster_slayer", "Monster Slayer", "Defeat 10 monsters across Asterra.", "Combat", icon_symbol="🗡️"),
            Achievement("boss_vanquisher", "Overlord Slayer", "Vanquish the Shadow Overlord in the Dungeon.", "Combat", icon_symbol="👑"),
            Achievement("apprentice_hero", "Apprentice Hero", "Reach Player Level 5.", "Progression", icon_symbol="⭐"),
            Achievement("quest_master", "Village Defender", "Complete 3 quests for Asterra villagers.", "Story", icon_symbol="📜"),
            Achievement("wealthy_merchant", "Gold Hoarder", "Accumulate 100 Gold coins.", "Economy", icon_symbol="💰"),
            Achievement("safe_traveler", "Safe Passage", "Reach the Village Safe Zone.", "Exploration", icon_symbol="🏰"),
            Achievement("spellweaver", "Spellweaver", "Cast your first magical spell.", "Combat", icon_symbol="✨"),
        ]
        for ach in defaults:
            self.achievements[ach.id] = ach

    def _register_event_listeners(self) -> None:
        if not self.event_bus:
            return
        self.event_bus.subscribe("enemy_killed", self._on_enemy_killed)
        self.event_bus.subscribe("level_up", self._on_level_up)
        self.event_bus.subscribe("quest_completed", self._on_quest_completed)
        self.event_bus.subscribe("gold_gained", self._on_gold_gained)
        self.event_bus.subscribe("skill_casted", self._on_skill_casted)

    def unlock(self, ach_id: str, game: Any = None) -> bool:
        if ach_id not in self.achievements:
            return False
        ach = self.achievements[ach_id]
        if ach.unlocked:
            return False

        ach.unlocked = True
        import datetime
        ach.unlocked_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.save_achievements()

        # Trigger Celebration & Toast Notification if available
        if game:
            if hasattr(game, "notification_manager") and game.notification_manager:
                from rpg.notification import NotificationPriority
                game.notification_manager.push_toast(
                    f"🏆 Achievement Unlocked: {ach.title}!",
                    priority=NotificationPriority.HIGH
                )

            celeb = getattr(game, "celebration_manager", None) or getattr(getattr(game, "ui_manager", None), "celebration", None)
            if celeb:
                from rpg.celebration import CelebrationTier
                celeb.trigger(
                    title=f"ACHIEVEMENT UNLOCKED: {ach.title}!",
                    subtitle=ach.description,
                    tier=CelebrationTier.MEDIUM,
                    sound_name="levelup"
                )


        return True

    def _on_enemy_killed(self, enemy_type: str = "", enemy_name: str = "", **kwargs: Any) -> None:

        self.unlock("first_blood", game=kwargs.get("game"))
        player = kwargs.get("player")
        if player and getattr(player, "kill_count", 0) >= 10:
            self.unlock("monster_slayer", game=kwargs.get("game"))
        if kwargs.get("is_boss", False):
            self.unlock("boss_vanquisher", game=kwargs.get("game"))

    def _on_level_up(self, level: int = 1, **kwargs: Any) -> None:
        if level >= 5:
            self.unlock("apprentice_hero", game=kwargs.get("game"))

    def _on_quest_completed(self, **kwargs: Any) -> None:
        game = kwargs.get("game")
        if game and hasattr(game, "quest_manager"):
            completed_count = sum(1 for q in game.quest_manager.quests.values() if q.status == "completed")
            if completed_count >= 3:
                self.unlock("quest_master", game=game)

    def _on_gold_gained(self, total_gold: int = 0, **kwargs: Any) -> None:
        if total_gold >= 100:
            self.unlock("wealthy_merchant", game=kwargs.get("game"))

    def _on_skill_casted(self, **kwargs: Any) -> None:
        self.unlock("spellweaver", game=kwargs.get("game"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            aid: {"unlocked": ach.unlocked, "unlocked_at": ach.unlocked_at}
            for aid, ach in self.achievements.items()
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        for aid, ainfo in data.items():
            if aid in self.achievements:
                self.achievements[aid].unlocked = ainfo.get("unlocked", False)
                self.achievements[aid].unlocked_at = ainfo.get("unlocked_at", None)

    def reset(self) -> None:
        for ach in self.achievements.values():
            ach.unlocked = False
            ach.unlocked_at = None

    def save_achievements(self) -> None:
        try:
            os.makedirs(os.path.dirname(ACHIEVEMENTS_SAVE_PATH), exist_ok=True)
            data = self.to_dict()
            with open(ACHIEVEMENTS_SAVE_PATH, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            import logging
            logging.warning(f"Failed to save achievements: {e}")

    def load_achievements(self) -> None:
        if not os.path.exists(ACHIEVEMENTS_SAVE_PATH):
            return
        try:
            with open(ACHIEVEMENTS_SAVE_PATH, "r") as f:
                data = json.load(f)
            self.from_dict(data)
        except Exception as e:
            import logging
            logging.warning(f"Failed to load achievements: {e}")

