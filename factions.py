"""
Echoes of Asterra - Faction & Reputation System
Manages global standing with 6 distinct world factions:
Knights, Mages, Hunters, Merchants, Bandits, and Cultists.
Player actions, combat choices, and quest completions adjust faction standings,
directly modifying shop prices, dialogue reactions, and quest access.
"""
from dataclasses import dataclass
from typing import Dict, Any
from rpg.constants import (
    FACTION_KNIGHTS, FACTION_MAGES, FACTION_HUNTERS,
    FACTION_MERCHANTS, FACTION_BANDITS, FACTION_CULTISTS
)
from rpg.events import EventBus

@dataclass
class FactionData:
    faction_id: str
    name: str
    reputation: int = 0  # Range: -100 (Hostile) to +100 (Exalted)

    @property
    def standing(self) -> str:
        if self.reputation <= -30:
            return "hostile"
        elif self.reputation < 20:
            return "neutral"
        elif self.reputation < 60:
            return "friendly"
        else:
            return "exalted"

class FactionManager:
    """
    Tracks reputation scores across all factions and applies world modifiers.
    """
    def __init__(self) -> None:
        self.factions: Dict[str, FactionData] = {
            FACTION_KNIGHTS: FactionData(FACTION_KNIGHTS, "Knights of Asterra", reputation=10),
            FACTION_MAGES: FactionData(FACTION_MAGES, "Arcane Circle", reputation=5),
            FACTION_HUNTERS: FactionData(FACTION_HUNTERS, "Hunters Guild", reputation=10),
            FACTION_MERCHANTS: FactionData(FACTION_MERCHANTS, "Trade Consortium", reputation=15),
            FACTION_BANDITS: FactionData(FACTION_BANDITS, "Shadow Brotherhood", reputation=-10),
            FACTION_CULTISTS: FactionData(FACTION_CULTISTS, "Void Cult", reputation=-25)
        }

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes to global EventBus topics."""
        event_bus.subscribe("enemy_killed", self._on_enemy_killed)
        event_bus.subscribe("quest_completed", self._on_quest_completed)
        event_bus.subscribe("item_bought", self._on_item_bought)

    def modify_reputation(self, faction_id: str, amount: int) -> None:
        """Adjusts reputation score for a specific faction (clamped -100 to +100)."""
        if faction_id in self.factions:
            fac = self.factions[faction_id]
            fac.reputation = max(-100, min(100, fac.reputation + amount))

    def get_reputation(self, faction_id: str) -> int:
        """Returns reputation score for a faction."""
        if faction_id in self.factions:
            return self.factions[faction_id].reputation
        return 0

    def get_standing(self, faction_id: str) -> str:
        """Returns human-readable standing category."""
        if faction_id in self.factions:
            return self.factions[faction_id].standing
        return "neutral"

    def get_price_modifier(self) -> float:
        """Returns price multiplier based on Trade Consortium reputation."""
        merch_rep = self.get_reputation(FACTION_MERCHANTS)
        # Exalted (+100) = 20% discount (0.8), Hostile (-100) = 20% markup (1.2)
        discount = (merch_rep / 100.0) * 0.20
        return max(0.75, min(1.30, 1.0 - discount))

    def _on_enemy_killed(self, enemy_type: str = "", enemy_name: str = "", **kwargs: Any) -> None:
        """Updates faction standing when monsters or faction members are slain."""
        if "slime" in enemy_type or "wolf" in enemy_type:
            # Monster culling helps Hunters and Knights
            self.modify_reputation(FACTION_HUNTERS, 1)
            self.modify_reputation(FACTION_KNIGHTS, 1)
        elif "skeleton" in enemy_type or "mage" in enemy_type:
            # Undead cleansing helps Mages and Knights, angers Cultists
            self.modify_reputation(FACTION_MAGES, 2)
            self.modify_reputation(FACTION_KNIGHTS, 1)
            self.modify_reputation(FACTION_CULTISTS, -2)
        elif "goblin" in enemy_type:
            # Scavenger culling helps Merchants
            self.modify_reputation(FACTION_MERCHANTS, 1)
            self.modify_reputation(FACTION_BANDITS, -1)
        elif "knight" in enemy_type:
            # Killing corrupted knights helps Bandits, angers Knights
            self.modify_reputation(FACTION_KNIGHTS, -2)
            self.modify_reputation(FACTION_BANDITS, 2)
        elif enemy_type == "boss":
            # Defeating boss grants huge prestige
            self.modify_reputation(FACTION_KNIGHTS, 15)
            self.modify_reputation(FACTION_MAGES, 15)
            self.modify_reputation(FACTION_HUNTERS, 15)
            self.modify_reputation(FACTION_MERCHANTS, 10)
            self.modify_reputation(FACTION_CULTISTS, -20)

    def _on_quest_completed(self, quest_id: str = "", **kwargs: Any) -> None:
        """Completing quests boosts civil faction standing."""
        self.modify_reputation(FACTION_KNIGHTS, 3)
        self.modify_reputation(FACTION_MERCHANTS, 3)
        self.modify_reputation(FACTION_HUNTERS, 2)

    def _on_item_bought(self, **kwargs: Any) -> None:
        """Trading with Silas helps Merchants."""
        self.modify_reputation(FACTION_MERCHANTS, 1)

    def to_dict(self) -> Dict[str, int]:
        """Serializes faction reputation scores to dict for saving."""
        return {f_id: fac.reputation for f_id, fac in self.factions.items()}

    def from_dict(self, data: Dict[str, int]) -> None:
        """Restores faction reputation scores from dict."""
        for f_id, rep in data.items():
            if f_id in self.factions:
                self.factions[f_id].reputation = max(-100, min(100, rep))
