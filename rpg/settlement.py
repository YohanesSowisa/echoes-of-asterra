"""
Echoes of Asterra - Dynamic Settlement Growth & Infrastructure System
Ties Village Prosperity directly to gameplay expansion:
unlocking new villager NPCs, street lamps, decorative banners, Master Forging, rare shop imports,
new bounty quests, and reduced town prices.
"""
from typing import Dict, Any, Optional, Tuple
from rpg.events import EventBus

class SettlementManager:
    """
    Manages Village growth tiers, infrastructure visuals, new unlocked services, and villager spawns.
    Tracks completed town investments idempotently.
    """
    def __init__(self) -> None:
        self.event_bus: Optional[EventBus] = None
        self.growth_tier = 1  # Tier 1 (0-30), Tier 2 (31-60), Tier 3 (61-100)
        self._prosperity = 20.0
        self.master_forging_unlocked = False
        self.rare_imports_unlocked = False
        self.investments_completed: set = set()
        self.upgrades: Dict[str, bool] = {}

        # Facility Levels (Tier 1-3 upgrades for Blacksmith, Apothecary, Market)
        self.facility_levels: Dict[str, int] = {
            "blacksmith": 1,
            "apothecary": 1,
            "market": 1,
        }

    FACILITY_UPGRADE_COSTS = {
        "blacksmith": {
            2: {"gold": 150, "materials": {"Iron Ore": 5, "Timber": 5}},
            3: {"gold": 400, "materials": {"Iron Ore": 12, "Timber": 10}},
        },
        "apothecary": {
            2: {"gold": 100, "materials": {"Forest Apple": 8}},
            3: {"gold": 300, "materials": {"Forest Apple": 15, "Asterra Heart": 1}},
        },
        "market": {
            2: {"gold": 200, "materials": {"Beast Leather": 5}},
            3: {"gold": 500, "materials": {"Beast Leather": 10, "Gold Ore": 3}},
        },
    }

    def get_facility_level(self, facility_id: str) -> int:
        """Returns the current level (1-3) of a facility."""
        return self.facility_levels.get(facility_id, 1)

    def can_upgrade_facility(self, facility_id: str, player: Any) -> Tuple[bool, str]:
        """Checks if player meets gold & material costs to upgrade facility."""
        curr_lvl = self.get_facility_level(facility_id)
        next_lvl = curr_lvl + 1
        if next_lvl > 3:
            return False, "Facility is already max level (Lvl 3)!"

        cost_info = self.FACILITY_UPGRADE_COSTS.get(facility_id, {}).get(next_lvl)
        if not cost_info:
            return False, "No further upgrade available!"

        # Check gold
        if player.gold < cost_info["gold"]:
            return False, f"Need {cost_info['gold']} gold (you have {player.gold}g)"

        # Check materials in inventory
        for mat_name, req_qty in cost_info["materials"].items():
            if not player.inventory.has_item(mat_name, req_qty):
                return False, f"Need {mat_name} x{req_qty}"

        return True, f"Ready to upgrade {facility_id.title()} to Level {next_lvl}!"

    def upgrade_facility(self, facility_id: str, player: Any) -> Tuple[bool, str]:
        """Upgrades a settlement facility, deducting gold & materials from player."""
        can_up, reason = self.can_upgrade_facility(facility_id, player)
        if not can_up:
            return False, reason

        curr_lvl = self.get_facility_level(facility_id)
        next_lvl = curr_lvl + 1
        cost_info = self.FACILITY_UPGRADE_COSTS[facility_id][next_lvl]

        # Deduct costs
        player.gold -= cost_info["gold"]
        for mat_name, req_qty in cost_info["materials"].items():
            player.inventory.remove_item(mat_name, req_qty)

        self.facility_levels[facility_id] = next_lvl
        self.add_prosperity(15.0)

        if self.event_bus:
            self.event_bus.emit("facility_upgraded", facility=facility_id, new_level=next_lvl)

        return True, f"{facility_id.title()} upgraded to Level {next_lvl}!"

    @property
    def prosperity(self) -> float:
        return self._prosperity

    def register_event_listeners(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        event_bus.subscribe("prosperity_changed", self._on_prosperity_changed)

    def is_investment_completed(self, investment_id: str) -> bool:
        """Returns True if the specified town investment has already been completed."""
        return investment_id in self.investments_completed

    def fund_investment(self, investment_id: str, prosperity_bonus: float = 15.0) -> bool:
        """
        Idempotently funds a town investment.
        Returns True if newly funded, False if already completed.
        """
        if self.is_investment_completed(investment_id):
            return False
        self.investments_completed.add(investment_id)
        self.upgrades[investment_id] = True
        self.add_prosperity(prosperity_bonus)

        if self.event_bus:
            self.event_bus.emit("town_invested", investment_id=investment_id, prosperity=self._prosperity)
        return True

    def add_prosperity(self, amount: float) -> None:
        """Additive prosperity modification."""
        new_val = min(100.0, max(0.0, self._prosperity + amount))
        self._on_prosperity_changed(new_val)

    def _on_prosperity_changed(self, prosperity: float = 50.0, **kwargs: Any) -> None:
        """Evaluates prosperity and triggers milestone upgrades."""
        self._prosperity = float(prosperity)
        old_tier = self.growth_tier
        if self._prosperity >= 60.0:
            self.growth_tier = 3
            self.master_forging_unlocked = True
            self.rare_imports_unlocked = True
        elif self._prosperity >= 30.0:
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

    def get_roof_style(self) -> str:
        """Returns visual building roof asset key based on growth tier."""
        return "roof_tile_slate" if self.growth_tier >= 2 else "roof_tile_thatch"

    def get_road_style(self) -> str:
        """Returns visual street road asset key based on growth tier."""
        return "road_cobblestone" if self.growth_tier >= 2 else "road_dirt"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes settlement state."""
        return {
            "growth_tier": self.growth_tier,
            "prosperity": self._prosperity,
            "master_forging_unlocked": self.master_forging_unlocked,
            "rare_imports_unlocked": self.rare_imports_unlocked,
            "investments_completed": list(self.investments_completed),
            "upgrades": self.upgrades,
            "facility_levels": self.facility_levels,
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes settlement state."""
        if not data:
            return
        self.growth_tier = data.get("growth_tier", 1)
        self._prosperity = data.get("prosperity", 20.0)
        self.master_forging_unlocked = data.get("master_forging_unlocked", False)
        self.rare_imports_unlocked = data.get("rare_imports_unlocked", False)
        self.investments_completed = set(data.get("investments_completed", []))
        self.upgrades = data.get("upgrades", {})
        self.facility_levels = data.get("facility_levels", {"blacksmith": 1, "apothecary": 1, "market": 1})
        self._on_prosperity_changed(self._prosperity)
