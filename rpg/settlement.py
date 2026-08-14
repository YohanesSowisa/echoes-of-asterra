"""
Echoes of Asterra - Dynamic Settlement Growth & Infrastructure System
Ties Village Prosperity directly to gameplay expansion:
unlocking new villager NPCs, street lamps, decorative banners, Master Forging, rare shop imports,
new bounty quests, and reduced town prices.
Includes Player-Driven Settlement Specializations (Military Fortress, Trade Hub, Arcane Sanctuary).
"""
from typing import Dict, Any, Optional, Tuple, List
from rpg.events import EventBus
from rpg.constants import (
    FACTION_KNIGHTS, FACTION_MAGES, FACTION_MERCHANTS
)

SPECIALIZATION_NONE = "none"
SPECIALIZATION_MILITARY = "military_fortress"
SPECIALIZATION_TRADE = "trade_hub"
SPECIALIZATION_ARCANE = "arcane_sanctuary"

SPECIALIZATION_DEFS = {
    SPECIALIZATION_MILITARY: {
        "title": "Military Fortress",
        "faction": FACTION_KNIGHTS,
        "description": "Fortified garrison with palisades, elite knight patrols, and safe zone combat training buffs.",
        "perks": "+15% ATK & +20% DEF in Village/Safe Zones, Extra Guard Patrols, +15 Global Road Safety.",
    },
    SPECIALIZATION_TRADE: {
        "title": "Trade Hub",
        "faction": FACTION_MERCHANTS,
        "description": "Bustling mercantile crossroads with colorful market canopies, exotic imports, and merchant subsidies.",
        "perks": "+15% Silas Shop Discount, Unlocks Rare Trade Goods, +30% Caravan Yields.",
    },
    SPECIALIZATION_ARCANE: {
        "title": "Arcane Sanctuary",
        "faction": FACTION_MAGES,
        "description": "Harmonious mystical sanctuary imbued with leyline mana fountains and runic scholar circles.",
        "perks": "Passive Mana Regeneration (+5.0 Mana/s) in Village, 25% Rune Crafting Discount.",
    },
}


class SettlementManager:
    """
    Manages Village growth tiers, infrastructure visuals, specialization choices,
    new unlocked services, and villager spawns.
    Tracks completed town investments idempotently.
    """
    def __init__(self) -> None:
        self.event_bus: Optional[EventBus] = None
        self.growth_tier = 1  # Tier 1 (0-30), Tier 2 (31-60), Tier 3 (61-100)
        self._prosperity = 20.0
        self.specialization = SPECIALIZATION_NONE
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

    def set_specialization(self, spec_id: str, player: Any, faction_manager: Optional[Any] = None) -> Tuple[bool, str]:
        """
        Player-driven or faction-driven specialization selection:
        Allowed if player pays 75g investment OR has Friendly standing (reputation >= 20) with aligned faction.
        """
        if spec_id not in SPECIALIZATION_DEFS:
            return False, f"Unknown specialization: '{spec_id}'"

        spec_def = SPECIALIZATION_DEFS[spec_id]
        title = spec_def["title"]

        if self.specialization == spec_id:
            return True, f"Asterra is already designated as a {title}."

        # Check faction standing discount or gold cost
        aligned_faction = spec_def["faction"]
        faction_rep = faction_manager.get_reputation(aligned_faction) if faction_manager else 0
        has_faction_endorsement = faction_rep >= 20

        cost_gold = 0 if has_faction_endorsement else 75
        if not has_faction_endorsement:
            if getattr(player, "gold", 0) < cost_gold:
                return False, f"Requires 75 Gold or Friendly Standing (20+ Rep) with {aligned_faction.title()} (Current: {faction_rep} Rep, {player.gold}g)."
            player.gold -= cost_gold

        self.specialization = spec_id
        self.add_prosperity(12.0)

        if self.event_bus:
            self.event_bus.emit(
                "settlement_specialized",
                specialization=spec_id,
                title=title,
                endorsed_by=aligned_faction if has_faction_endorsement else "Independent Gold Investment"
            )

        return True, f"Asterra successfully transformed into a {title}!"

    def get_specialization_title(self, spec_id: Optional[str] = None) -> str:
        """Returns human-readable title of current or specified specialization."""
        active_id = spec_id or self.specialization
        return SPECIALIZATION_DEFS.get(active_id, {}).get("title", "Standard Settlement")

    def get_specialization_perks_summary(self, spec_id: Optional[str] = None) -> str:
        """Returns perk summary string of active specialization."""
        active_id = spec_id or self.specialization
        return SPECIALIZATION_DEFS.get(active_id, {}).get("perks", "No active specialization bonuses.")

    def get_safe_zone_stat_buffs(self, map_name: str) -> Dict[str, float]:
        """Returns player combat multipliers when within safe zone (Village)."""
        if map_name == "village" and self.specialization == SPECIALIZATION_MILITARY:
            return {"atk_mult": 1.15, "def_mult": 1.20, "speed_mult": 1.05}
        return {"atk_mult": 1.0, "def_mult": 1.0, "speed_mult": 1.0}

    def get_safe_zone_mana_regen(self, map_name: str) -> float:
        """Returns mana regeneration per second in Village."""
        if map_name == "village" and self.specialization == SPECIALIZATION_ARCANE:
            return 5.0
        return 0.0

    def get_trade_discount(self) -> float:
        """Returns additional shop discount from Trade Hub specialization."""
        if self.specialization == SPECIALIZATION_TRADE:
            return 0.15
        return 0.0

    def get_rune_crafting_discount(self) -> float:
        """Returns rune/spell crafting discount from Arcane Sanctuary specialization."""
        if self.specialization == SPECIALIZATION_ARCANE:
            return 0.25
        return 0.0

    def get_specialization_decorations(self, map_name: str) -> List[Dict[str, Any]]:
        """Returns decorative props to spawn in Village based on specialization."""
        if map_name != "village":
            return []

        if self.specialization == SPECIALIZATION_MILITARY:
            return [
                {"type": "banner_knights", "pos": (12 * 32, 8 * 32), "name": "Fortress Palisade Banner"},
                {"type": "weapon_rack", "pos": (14 * 32, 13 * 32), "name": "Garrison Weapon Rack"},
                {"type": "guard_post", "pos": (19 * 32, 10 * 32), "name": "Fortress Guard Post"},
            ]
        elif self.specialization == SPECIALIZATION_TRADE:
            return [
                {"type": "trade_stand", "pos": (12 * 32, 13 * 32), "name": "Grand Market Stand"},
                {"type": "cargo_crates", "pos": (14 * 32, 14 * 32), "name": "Merchant Spice Crates"},
                {"type": "silk_canopy", "pos": (18 * 32, 11 * 32), "name": "Consortium Silk Canopy"},
            ]
        elif self.specialization == SPECIALIZATION_ARCANE:
            return [
                {"type": "mana_fountain", "pos": (13 * 32, 12 * 32), "name": "Glowing Leyline Fountain"},
                {"type": "mystic_flora", "pos": (15 * 32, 14 * 32), "name": "Bioluminescent Shrub"},
                {"type": "arcane_obelisk", "pos": (18 * 32, 9 * 32), "name": "Sanctuary Rune Pillar"},
            ]
        return []

    def get_facility_level(self, facility_id: str) -> int:
        """Returns the current level (1-3) of a facility."""
        return self.facility_levels.get(facility_id, 1)

    def get_facility_upgrade_cost_summary(self, facility_id: str, player: Any) -> str:
        """Returns a complete, simultaneous summary string of all upgrade costs and player's current amounts."""
        curr_lvl = self.get_facility_level(facility_id)
        next_lvl = curr_lvl + 1
        if next_lvl > 3:
            return "Max Level (Lvl 3)"
        
        cost_info = self.FACILITY_UPGRADE_COSTS.get(facility_id, {}).get(next_lvl)
        if not cost_info:
            return "No Upgrade Available"

        parts = [f"{cost_info['gold']}g ({player.gold}g)"]
        for mat_name, req_qty in cost_info["materials"].items():
            has_qty = player.inventory.get_item_count(mat_name)
            parts.append(f"{mat_name} {has_qty}/{req_qty}")

        return f"Req: {', '.join(parts)}"

    def can_upgrade_facility(self, facility_id: str, player: Any) -> Tuple[bool, str]:
        """Checks if player meets ALL gold & material costs simultaneously."""
        curr_lvl = self.get_facility_level(facility_id)
        next_lvl = curr_lvl + 1
        if next_lvl > 3:
            return False, "Facility is already max level (Lvl 3)!"

        cost_info = self.FACILITY_UPGRADE_COSTS.get(facility_id, {}).get(next_lvl)
        if not cost_info:
            return False, "No further upgrade available!"

        missing = []
        if player.gold < cost_info["gold"]:
            missing.append(f"{cost_info['gold'] - player.gold}g gold")

        for mat_name, req_qty in cost_info["materials"].items():
            has_qty = player.inventory.get_item_count(mat_name)
            if has_qty < req_qty:
                missing.append(f"{mat_name} x{req_qty - has_qty}")

        if missing:
            return False, f"Missing: {', '.join(missing)}"

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
            "specialization": self.specialization,
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
        self.specialization = data.get("specialization", SPECIALIZATION_NONE)
        self.master_forging_unlocked = data.get("master_forging_unlocked", False)
        self.rare_imports_unlocked = data.get("rare_imports_unlocked", False)
        self.investments_completed = set(data.get("investments_completed", []))
        self.upgrades = data.get("upgrades", {})
        self.facility_levels = data.get("facility_levels", {"blacksmith": 1, "apothecary": 1, "market": 1})
        self._on_prosperity_changed(self._prosperity)

    def reset(self) -> None:
        """Resets settlement manager to starting state."""
        self.growth_tier = 1
        self._prosperity = 20.0
        self.specialization = SPECIALIZATION_NONE
        self.master_forging_unlocked = False
        self.rare_imports_unlocked = False
        self.investments_completed = set()
        self.upgrades = {}
        self.facility_levels = {"blacksmith": 1, "apothecary": 1, "market": 1}
