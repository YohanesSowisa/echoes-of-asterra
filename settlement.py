"""
Echoes of Asterra - Dynamic Settlement Growth & Infrastructure System
Ties Village Prosperity directly to gameplay expansion:
unlocking new villager NPCs, street lamps, decorative banners, Master Forging, rare shop imports,
new bounty quests, and reduced town prices.
"""
from typing import Dict, Any, Optional
from rpg.events import EventBus

class SettlementManager:
    """
    Manages Village growth tiers, infrastructure visuals, new unlocked services, and villager spawns.
    """
    def __init__(self) -> None:
        self.event_bus: Optional[EventBus] = None
        self.growth_tier = 1  # Tier 1 (0-30), Tier 2 (31-60), Tier 3 (61-100)
        self._prosperity = 20.0
        self.master_forging_unlocked = False
        self.rare_imports_unlocked = False

    @property
    def prosperity(self) -> float:
        return self._prosperity

    def register_event_listeners(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        event_bus.subscribe("prosperity_changed", self._on_prosperity_changed)

    def _on_prosperity_changed(self, prosperity: float = 50.0, **kwargs) -> None:
        """Evaluates prosperity and triggers milestone upgrades."""
        self._prosperity = float(prosperity)
        old_tier = self.growth_tier
        if prosperity >= 60.0:
            self.growth_tier = 3
            self.master_forging_unlocked = True
            self.rare_imports_unlocked = True
        elif prosperity >= 30.0:
            self.growth_tier = 2
            self.master_forging_unlocked = True
            self.rare_imports_unlocked = False
        else:
            self.growth_tier = 1
            self.master_forging_unlocked = False
            self.rare_imports_unlocked = False

        if self.growth_tier > old_tier and self.event_bus:
            self.event_bus.emit(
                "settlement_upgraded",
                new_tier=self.growth_tier,
                master_forging=self.master_forging_unlocked,
                rare_imports=self.rare_imports_unlocked
            )

    def get_tier_discount(self) -> float:
        """Returns price discount scalar based on settlement growth tier."""
        if self.growth_tier == 3:
            return 0.20  # 20% discount
        elif self.growth_tier == 2:
            return 0.10  # 10% discount
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes settlement state."""
        return {
            "growth_tier": self.growth_tier,
            "master_forging_unlocked": self.master_forging_unlocked,
            "rare_imports_unlocked": self.rare_imports_unlocked
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes settlement state."""
        if not data:
            return
        self.growth_tier = data.get("growth_tier", 1)
        self.master_forging_unlocked = data.get("master_forging_unlocked", False)
        self.rare_imports_unlocked = data.get("rare_imports_unlocked", False)
