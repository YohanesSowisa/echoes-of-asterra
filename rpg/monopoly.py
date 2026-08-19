"""
Echoes of Asterra - Sovereign Guilds & The Continental Monopoly System (Pillar #5)
Manages resource deeds, commodity extraction, the player's Guild Warehouse stockpile,
and market supply bulk liquidations.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from rpg.events import EventBus

DEED_MINING = "mining_concession"
DEED_HERBAL = "herbal_rights"
DEED_LUMBER = "lumber_concession"

COMMODITY_MARKET_PRICES: Dict[str, int] = {
    "iron_ore": 8,
    "granite_stone": 4,
    "medicinal_herb": 6,
    "luminescent_spore": 10,
    "oak_timber": 5
}

COMMODITY_DISPLAY_NAMES: Dict[str, str] = {
    "iron_ore": "Iron Ore",
    "granite_stone": "Granite Stone",
    "medicinal_herb": "Medicinal Herbs",
    "luminescent_spore": "Luminescent Spores",
    "oak_timber": "Oak Timber"
}


@dataclass
class ResourceDeed:
    """Represents an exclusive territorial concession deed producing raw commodities daily."""
    deed_id: str
    name: str
    location_name: str
    cost: int
    daily_yield: Dict[str, int]
    is_owned: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deed_id": self.deed_id,
            "name": self.name,
            "location_name": self.location_name,
            "cost": self.cost,
            "daily_yield": dict(self.daily_yield),
            "is_owned": self.is_owned,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceDeed":
        return cls(
            deed_id=data["deed_id"],
            name=data["name"],
            location_name=data.get("location_name", "Asterra"),
            cost=data.get("cost", 100),
            daily_yield=data.get("daily_yield", {}),
            is_owned=data.get("is_owned", False),
            description=data.get("description", "")
        )


DEFAULT_RESOURCE_DEEDS: List[ResourceDeed] = [
    ResourceDeed(
        deed_id=DEED_MINING,
        name="Granite Cavern Mining Concession",
        location_name="Granite Caverns",
        cost=150,
        daily_yield={"iron_ore": 3, "granite_stone": 2},
        description="Exclusive subterranean mineral deed granting daily iron ore and quarried granite deliveries."
    ),
    ResourceDeed(
        deed_id=DEED_HERBAL,
        name="Deep Forest Herbal Rights",
        location_name="Emerald Forest Canopy",
        cost=100,
        daily_yield={"medicinal_herb": 4, "luminescent_spore": 2},
        description="Crown foraging charter guaranteeing daily harvested medicinal herbs and rare luminescent spores."
    ),
    ResourceDeed(
        deed_id=DEED_LUMBER,
        name="Verdant Woodlands Timber Concession",
        location_name="Verdant Woodlands",
        cost=120,
        daily_yield={"oak_timber": 5},
        description="Royal logging franchise delivering prime seasoned oak timber directly to the warehouse."
    )
]


class GuildWarehouse:
    """Manages the player's bulk commodity storage stockpile."""
    def __init__(self, capacity: int = 300) -> None:
        self.capacity = capacity
        self.stock: Dict[str, int] = {
            "iron_ore": 0,
            "granite_stone": 0,
            "medicinal_herb": 0,
            "luminescent_spore": 0,
            "oak_timber": 0
        }

    def get_total_items(self) -> int:
        return sum(self.stock.values())

    def get_available_capacity(self) -> int:
        return max(0, self.capacity - self.get_total_items())

    def add_item(self, item_id: str, count: int) -> int:
        """Adds commodity up to available warehouse capacity. Returns quantity successfully stored."""
        if count <= 0:
            return 0
        space = self.get_available_capacity()
        to_add = min(count, space)
        self.stock[item_id] = self.stock.get(item_id, 0) + to_add
        return to_add

    def remove_item(self, item_id: str, count: int) -> int:
        """Removes commodity up to available stock. Returns quantity removed."""
        if count <= 0:
            return 0
        available = self.stock.get(item_id, 0)
        to_remove = min(count, available)
        self.stock[item_id] = available - to_remove
        return to_remove

    def get_stock(self, item_id: str) -> int:
        return self.stock.get(item_id, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capacity": self.capacity,
            "stock": dict(self.stock)
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        self.capacity = data.get("capacity", 300)
        self.stock = {k: int(v) for k, v in data.get("stock", {}).items()}


class MonopolyManager:
    """
    Subsystem coordinating resource concessions, automated commodity supply chains,
    bulk liquidation trade, and economic influence.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.deeds: Dict[str, ResourceDeed] = {}
        self.warehouse = GuildWarehouse()
        self.active_embargoes: Dict[str, Dict[str, bool]] = {}
        self.syndicate_hq_built: bool = False
        self.vault_gold: int = 0
        self.total_commodities_sold: int = 0
        self.total_revenue_earned: int = 0
        self.reset()
        if self.event_bus:
            self.event_bus.subscribe("day_changed", self._on_day_changed)

    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        self.on_day_changed(day)

    def reset(self) -> None:
        """Resets deeds, warehouse, and embargo state to initial defaults."""
        self.deeds = {
            d.deed_id: ResourceDeed(
                deed_id=d.deed_id,
                name=d.name,
                location_name=d.location_name,
                cost=d.cost,
                daily_yield=dict(d.daily_yield),
                is_owned=False,
                description=d.description
            ) for d in DEFAULT_RESOURCE_DEEDS
        }
        self.warehouse = GuildWarehouse()
        self.active_embargoes = {}
        self.syndicate_hq_built = False
        self.vault_gold = 0
        self.total_commodities_sold = 0
        self.total_revenue_earned = 0

    def purchase_deed(self, deed_id: str, player: Any) -> Tuple[bool, str]:
        """Purchases an exclusive resource extraction deed for the player."""
        if deed_id not in self.deeds:
            return False, "Concession deed does not exist."

        deed = self.deeds[deed_id]
        if deed.is_owned:
            return False, f"You already own the {deed.name}."

        if getattr(player, "gold", 0) < deed.cost:
            return False, f"Insufficient gold ({player.gold}/{deed.cost} Gold required)."

        player.gold -= deed.cost
        deed.is_owned = True

        if self.event_bus:
            self.event_bus.emit(
                "deed_purchased",
                deed_id=deed_id,
                deed_name=deed.name,
                cost=deed.cost,
                location=deed.location_name
            )

        return True, f"Successfully acquired the {deed.name} for {deed.cost} Gold!"

    def on_day_changed(self, day: int = 1) -> Dict[str, int]:
        """
        Executes daily automated resource deliveries to the Guild Warehouse
        from all owned concession deeds.
        """
        total_delivered: Dict[str, int] = {}
        for deed in self.deeds.values():
            if deed.is_owned:
                for item_id, qty in deed.daily_yield.items():
                    stored = self.warehouse.add_item(item_id, qty)
                    total_delivered[item_id] = total_delivered.get(item_id, 0) + stored

        if total_delivered and self.event_bus:
            self.event_bus.emit(
                "warehouse_stock_delivered",
                day=day,
                delivered=total_delivered,
                total_stock=dict(self.warehouse.stock)
            )

        # Daily Gold Vault Compound Interest (+2% per day) (Pillar #5 Phase 3)
        if self.syndicate_hq_built and self.vault_gold > 0:
            interest = max(1, int(self.vault_gold * 0.02))
            self.vault_gold += interest
            if self.event_bus:
                self.event_bus.emit(
                    "bank_interest_accrued",
                    day=day,
                    interest=interest,
                    new_balance=self.vault_gold
                )

        return total_delivered

    def bulk_liquidate(self, item_id: str, count: Optional[int] = None, player: Any = None) -> Tuple[int, int]:
        """
        Liquidates stockpiled commodities directly to Silas/Market for Gold at current market value.
        Returns (items_sold, gold_earned).
        """
        available = self.warehouse.get_stock(item_id)
        if available <= 0:
            return 0, 0

        to_sell = available if count is None else min(count, available)
        if to_sell <= 0:
            return 0, 0

        unit_price = COMMODITY_MARKET_PRICES.get(item_id, 5)
        revenue = to_sell * unit_price

        self.warehouse.remove_item(item_id, to_sell)
        if player and hasattr(player, "gold"):
            player.gold += revenue

        self.total_commodities_sold += to_sell
        self.total_revenue_earned += revenue

        if self.event_bus:
            self.event_bus.emit(
                "commodity_bulk_sold",
                item_id=item_id,
                count=to_sell,
                unit_price=unit_price,
                revenue=revenue
            )

        return to_sell, revenue

    def liquidate_all(self, player: Any = None) -> Tuple[int, int]:
        """Liquidates all commodities currently in the warehouse."""
        total_sold = 0
        total_gold = 0
        for item_id in list(self.warehouse.stock.keys()):
            sold, rev = self.bulk_liquidate(item_id, player=player)
            total_sold += sold
            total_gold += rev
        return total_sold, total_gold

    def is_hoarding(self, item_id: str = "iron_ore") -> bool:
        """
        Determines if the player is actively hoarding a critical commodity,
        triggering market scarcity and economic disruption.
        Threshold: >= 30 units of Iron Ore stored in warehouse.
        """
        stock = self.warehouse.get_stock(item_id)
        if item_id == "iron_ore":
            return stock >= 30
        elif item_id == "medicinal_herb":
            return stock >= 25
        return stock >= 40

    def get_commodity_price_multiplier(self, category_or_item: str = "ore") -> float:
        """
        Calculates store and market price multipliers resulting from commodity hoarding.
        Hoarding 80%+ / 30+ units of iron ore causes iron weapon and ore prices to surge by 2.5x.
        """
        if category_or_item in ("ore", "iron_ore", "Iron Ore") and self.is_hoarding("iron_ore"):
            return 2.5
        elif category_or_item in ("herbs", "medicinal_herb", "Medicinal Herbs") and self.is_hoarding("medicinal_herb"):
            return 2.0
        return 1.0

    def set_faction_embargo(self, faction_id: str, commodity_id: str, enabled: bool = True) -> bool:
        """
        Imposes or lifts a targeted commercial embargo against a specific faction.
        """
        clean_fac = faction_id.lower()
        if clean_fac not in self.active_embargoes:
            self.active_embargoes[clean_fac] = {}
        self.active_embargoes[clean_fac][commodity_id] = enabled

        if self.event_bus:
            self.event_bus.emit(
                "faction_embargo_toggled",
                faction=clean_fac,
                commodity=commodity_id,
                enabled=enabled
            )
        return True

    def is_faction_embargoed(self, faction_id: str, commodity_id: str) -> bool:
        """
        Returns whether a faction is suffering from a trade embargo on a specific commodity.
        Also returns True for Knights if iron ore is hoarded by the player.
        """
        clean_fac = faction_id.lower()
        # Direct embargo check
        if clean_fac in self.active_embargoes and self.active_embargoes[clean_fac].get(commodity_id, False):
            return True

        # Passive hoarding embargo impact
        if "knight" in clean_fac and commodity_id == "iron_ore" and self.is_hoarding("iron_ore"):
            return True

        return False

    def build_syndicate_hq(self, player: Any) -> Tuple[bool, str]:
        """
        Constructs the Asterra Merchant Syndicate HQ in the eastern district.
        Cost: 250 Gold.
        Prerequisite: Must own at least 2 concession deeds.
        """
        if self.syndicate_hq_built:
            return False, "Asterra Merchant Syndicate HQ is already constructed."

        owned_deeds = sum(1 for d in self.deeds.values() if d.is_owned)
        if owned_deeds < 2:
            return False, f"Requires at least 2 owned concession deeds (Currently own: {owned_deeds}/2)."

        cost = 250
        if getattr(player, "gold", 0) < cost:
            return False, f"Insufficient gold ({player.gold}/{cost} Gold required)."

        player.gold -= cost
        self.syndicate_hq_built = True

        # Unlock title
        if hasattr(player, "titles") and isinstance(player.titles, set):
            player.titles.add("The Sovereign Baron")

        if self.event_bus:
            self.event_bus.emit(
                "syndicate_hq_constructed",
                cost=cost,
                title="The Sovereign Baron"
            )
            self.event_bus.emit("title_unlocked", title="The Sovereign Baron")

        return True, "Successfully constructed the Asterra Merchant Syndicate HQ! Unlocked 'The Sovereign Baron' prestige title and Gold Vault banking."

    def deposit_vault(self, amount: int, player: Any) -> Tuple[bool, str]:
        """Deposits gold from player purse into the Guild Vault."""
        if not self.syndicate_hq_built:
            return False, "Must construct the Asterra Merchant Syndicate HQ first."

        if amount <= 0:
            return False, "Deposit amount must be greater than zero."

        if getattr(player, "gold", 0) < amount:
            return False, f"Insufficient gold in purse ({player.gold}/{amount} Gold)."

        player.gold -= amount
        self.vault_gold += amount

        if self.event_bus:
            self.event_bus.emit(
                "vault_deposited",
                amount=amount,
                vault_total=self.vault_gold
            )
        return True, f"Deposited {amount} Gold into the Guild Vault. Total balance: {self.vault_gold} Gold."

    def withdraw_vault(self, amount: int, player: Any) -> Tuple[bool, str]:
        """Withdraws gold from the Guild Vault to the player purse."""
        if not self.syndicate_hq_built:
            return False, "Must construct the Asterra Merchant Syndicate HQ first."

        if amount <= 0:
            return False, "Withdrawal amount must be greater than zero."

        if self.vault_gold < amount:
            return False, f"Insufficient vault balance ({self.vault_gold}/{amount} Gold)."

        self.vault_gold -= amount
        if hasattr(player, "gold"):
            player.gold += amount

        if self.event_bus:
            self.event_bus.emit(
                "vault_withdrawn",
                amount=amount,
                vault_total=self.vault_gold
            )
        return True, f"Withdrew {amount} Gold from the Guild Vault. Remaining balance: {self.vault_gold} Gold."

    def get_merchant_discount(self) -> float:
        """Returns merchant discount percentage for 'The Sovereign Baron' (30% discount)."""
        return 0.30 if self.syndicate_hq_built else 0.0

    def can_diplomatic_bribe(self) -> bool:
        """Returns whether the player can use diplomatic bribery during faction negotiations."""
        return self.syndicate_hq_built

    def execute_diplomatic_bribe(self, faction_id: str, player: Any, bribe_amount: int = 50) -> Tuple[bool, str]:
        """
        Executes a diplomatic bribe as The Sovereign Baron to appease a hostile faction.
        Increases faction reputation or pacifies hostile sentries.
        """
        if not self.can_diplomatic_bribe():
            return False, "Requires 'The Sovereign Baron' title and Syndicate HQ."

        if getattr(player, "gold", 0) < bribe_amount:
            return False, f"Insufficient gold for diplomatic bribe ({player.gold}/{bribe_amount} Gold)."

        player.gold -= bribe_amount
        clean_fac = faction_id.lower()

        # Improve faction reputation if game reference available
        if hasattr(player, "game") and player.game and hasattr(player.game, "faction_manager"):
            player.game.faction_manager.modify_reputation(clean_fac, 25)

        if self.event_bus:
            self.event_bus.emit(
                "diplomatic_bribe_paid",
                faction=clean_fac,
                amount=bribe_amount
            )

        return True, f"Successfully paid {bribe_amount} Gold diplomatic bribe to {faction_id.capitalize()}. Hostilities calmed."

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Monopoly subsystem state for save files."""
        return {
            "deeds": {d_id: d.to_dict() for d_id, d in self.deeds.items()},
            "warehouse": self.warehouse.to_dict(),
            "active_embargoes": {k: dict(v) for k, v in self.active_embargoes.items()},
            "syndicate_hq_built": self.syndicate_hq_built,
            "vault_gold": self.vault_gold,
            "total_commodities_sold": self.total_commodities_sold,
            "total_revenue_earned": self.total_revenue_earned
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores Monopoly subsystem state from save files."""
        if not isinstance(data, dict):
            return

        if "deeds" in data and isinstance(data["deeds"], dict):
            for d_id, d_data in data["deeds"].items():
                if d_id in self.deeds:
                    self.deeds[d_id].is_owned = d_data.get("is_owned", False)

        if "warehouse" in data:
            self.warehouse.from_dict(data["warehouse"])

        if "active_embargoes" in data and isinstance(data["active_embargoes"], dict):
            self.active_embargoes = {k: dict(v) for k, v in data["active_embargoes"].items()}

        self.syndicate_hq_built = data.get("syndicate_hq_built", False)
        self.vault_gold = data.get("vault_gold", 0)
        self.total_commodities_sold = data.get("total_commodities_sold", 0)
        self.total_revenue_earned = data.get("total_revenue_earned", 0)


