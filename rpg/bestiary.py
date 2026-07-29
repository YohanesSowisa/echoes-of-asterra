"""
Echoes of Asterra - Bestiary & Enemy Compendium System
Tracks discovered and defeated enemy types, kill statistics, elemental weaknesses,
lore descriptions, and persists data to saves/bestiary.json.
"""
import os
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional

from rpg.events import EventBus

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BESTIARY_SAVE_PATH = os.path.join(BASE_DIR, "saves", "bestiary.json")


@dataclass
class BestiaryEntry:
    enemy_id: str
    name: str
    category: str
    element: str
    weakness: str
    lore: str
    kills: int = 0
    unlocked: bool = False


DEFAULT_BESTIARY: Dict[str, Dict[str, Any]] = {
    "slime": {
        "name": "Green Slime",
        "category": "Beast",
        "element": "Nature",
        "weakness": "Fire",
        "lore": "Common gelatinous organism inhabiting lush pastures and riverbanks."
    },
    "slime_blue": {
        "name": "Frost Slime",
        "category": "Beast",
        "element": "Ice",
        "weakness": "Fire",
        "lore": "Chilled jelly emitting sub-zero frost aura that slows unwary adventurers."
    },
    "slime_red": {
        "name": "Magma Slime",
        "category": "Beast",
        "element": "Fire",
        "weakness": "Ice",
        "lore": "Volcanic organism radiating intense thermal heat born from deep caverns."
    },
    "goblin": {
        "name": "Goblin Raider",
        "category": "Humanoid",
        "element": "Physical",
        "weakness": "Bludgeoning",
        "lore": "Cunning forest scavenger known for ambush tactics and stolen loot."
    },
    "skeleton": {
        "name": "Crypt Skeleton",
        "category": "Undead",
        "element": "Shadow",
        "weakness": "Holy / Fire",
        "lore": "Reanimated bone warrior bound by ancient dark spells guarding sunken crypts."
    },
    "mage": {
        "name": "Dark Cultist Mage",
        "category": "Humanoid",
        "element": "Arcane",
        "weakness": "Melee Rush",
        "lore": "Wielder of forbidden shadowy sorcery who strikes from long range."
    },
    "knight": {
        "name": "Rival Rogue Knight",
        "category": "Humanoid",
        "element": "Heavy Armor",
        "weakness": "Magic / Stun",
        "lore": "Dishonored mercenary seeking ancient Asterra relics and combat glory."
    },
    "wolf": {
        "name": "Crossroads Timberwolf",
        "category": "Beast",
        "element": "Nature",
        "weakness": "Fire / Slashing",
        "lore": "Fierce pack predator roaming the crossroads and dense forest paths."
    },
    "boss": {
        "name": "Shadow Knight Lord",
        "category": "Boss",
        "element": "Shadow / Boss",
        "weakness": "Combo Finishers",
        "lore": "Fallen commander of Asterra's lost legion, wielding devastating shockwaves."
    }
}


class BestiaryManager:
    """
    Manages enemy compendium records and listens to EventBus 'enemy_killed' signals.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.entries: Dict[str, BestiaryEntry] = {}
        self._init_defaults()
        self.load_bestiary()

        if self.event_bus and hasattr(self.event_bus, "subscribe"):
            self.event_bus.subscribe("enemy_killed", self._on_enemy_killed)

    def _init_defaults(self) -> None:
        for eid, meta in DEFAULT_BESTIARY.items():
            self.entries[eid] = BestiaryEntry(
                enemy_id=eid,
                name=meta["name"],
                category=meta["category"],
                element=meta["element"],
                weakness=meta["weakness"],
                lore=meta["lore"]
            )

    def record_kill(self, enemy_type: str, enemy_name: str = "", game: Any = None) -> bool:
        """Increments kill count for matching enemy and unlocks compendium entry."""
        target_key = enemy_type.lower()
        if target_key not in self.entries:
            # Fallback matching
            for key in self.entries:
                if key in target_key or target_key in key:
                    target_key = key
                    break

        if target_key in self.entries:
            entry = self.entries[target_key]
            first_unlock = not entry.unlocked
            entry.kills += 1
            entry.unlocked = True
            self.save_bestiary()

            if first_unlock and game and hasattr(game, "notification_manager") and game.notification_manager:
                from rpg.notification import NotificationPriority
                game.notification_manager.push_toast(
                    f"📖 Bestiary Unlocked: {entry.name}!",
                    priority=NotificationPriority.HIGH
                )
            return True
        return False

    def _on_enemy_killed(self, enemy_type: str = "", enemy_name: str = "", game: Any = None, **kwargs: Any) -> None:
        self.record_kill(enemy_type, enemy_name, game=game)

    def to_dict(self) -> Dict[str, Any]:
        return {
            eid: {"kills": entry.kills, "unlocked": entry.unlocked}
            for eid, entry in self.entries.items()
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        for eid, binfo in data.items():
            if eid in self.entries:
                self.entries[eid].kills = binfo.get("kills", 0)
                self.entries[eid].unlocked = binfo.get("unlocked", False)

    def reset(self) -> None:
        for entry in self.entries.values():
            entry.kills = 0
            entry.unlocked = False

    def save_bestiary(self) -> None:
        try:
            os.makedirs(os.path.dirname(BESTIARY_SAVE_PATH), exist_ok=True)
            payload = self.to_dict()
            with open(BESTIARY_SAVE_PATH, "w") as f:
                json.dump(payload, f, indent=4)
        except Exception as e:
            print(f"Warning: Failed saving bestiary state: {e}")

    def load_bestiary(self) -> None:
        if not os.path.exists(BESTIARY_SAVE_PATH):
            return
        try:
            with open(BESTIARY_SAVE_PATH, "r") as f:
                payload = json.load(f)
            self.from_dict(payload)
        except Exception as e:
            print(f"Warning: Failed loading bestiary state: {e}")

