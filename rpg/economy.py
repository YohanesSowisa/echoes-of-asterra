"""
Echoes of Asterra - Dynamic Living Economy Engine
Simulates regional production nodes (farms, mines, forestry), settlement consumption,
item stock storage, imports/exports, and real-time price multipliers.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional

from rpg.events import EventBus

@dataclass
class ResourceStock:
    """Represents supply, demand, and price multiplier for a resource category."""
    name: str
    current_stock: float
    max_capacity: float
    daily_production: float
    daily_consumption: float
    base_price: float

    @property
    def price_multiplier(self) -> float:
        """Calculates dynamic price scalar based on stock availability (0.6x to 1.6x)."""
        if self.max_capacity <= 0:
            return 1.0
        ratio = self.current_stock / self.max_capacity
        # Low stock = higher price; high stock = lower price
        if ratio < 0.2:
            return 1.6
        elif ratio < 0.5:
            return 1.25
        elif ratio > 0.95:
            return 0.6
        elif ratio > 0.8:
            return 0.75
        return 1.0

class EconomyManager:
    """
    Simulates regional supply and demand across Asterra.
    Production nodes generate raw resources, settlements consume goods daily,
    and caravans transport stock between districts.
    """
    def __init__(self) -> None:
        self.stocks: Dict[str, ResourceStock] = {
            "food": ResourceStock("Food & Crops", current_stock=60.0, max_capacity=100.0, daily_production=10.0, daily_consumption=12.0, base_price=10.0),
            "ore": ResourceStock("Iron & Minerals", current_stock=40.0, max_capacity=100.0, daily_production=8.0, daily_consumption=6.0, base_price=25.0),
            "herbs": ResourceStock("Herbs & Potions", current_stock=30.0, max_capacity=80.0, daily_production=6.0, daily_consumption=7.0, base_price=30.0),
            "goods": ResourceStock("Trade Commodities", current_stock=50.0, max_capacity=100.0, daily_production=5.0, daily_consumption=5.0, base_price=50.0)
        }
        self.trade_disruption: float = 0.0  # 0.0 to 1.0 (higher = bandit activity blocking supply)

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes to EventBus for economic impact triggers."""
        event_bus.subscribe("day_changed", self._on_day_changed)
        event_bus.subscribe("caravan_arrived", self._on_caravan_arrived)
        event_bus.subscribe("caravan_destroyed", self._on_caravan_destroyed)
        event_bus.subscribe("npc_produced_resource", self._on_npc_produced)

    def _on_day_changed(self, **kwargs) -> None:
        """Simulates daily regional production and settlement consumption."""
        for key, res in self.stocks.items():
            # Production modified by trade disruption
            effective_prod = res.daily_production * (1.0 - self.trade_disruption * 0.5)
            res.current_stock = max(0.0, min(res.max_capacity, res.current_stock + effective_prod - res.daily_consumption))

        # Decay trade disruption slightly
        self.trade_disruption = max(0.0, self.trade_disruption - 0.1)

    def _on_caravan_arrived(self, cargo_type: str = "goods", amount: float = 25.0, **kwargs) -> None:
        """Caravan successfully delivers cargo -> boosts stock and reduces price."""
        if cargo_type in self.stocks:
            res = self.stocks[cargo_type]
            res.current_stock = min(res.max_capacity, res.current_stock + amount)

    def _on_caravan_destroyed(self, cargo_type: str = "goods", **kwargs) -> None:
        """Caravan destroyed by bandits -> increases disruption and spikes prices."""
        self.trade_disruption = min(1.0, self.trade_disruption + 0.3)
        if cargo_type in self.stocks:
            res = self.stocks[cargo_type]
            res.current_stock = max(0.0, res.current_stock - 15.0)

    def _on_npc_produced(self, resource_type: str = "food", amount: float = 2.0, **kwargs) -> None:
        """NPC worker completing job routine adds directly to regional stock."""
        if resource_type in self.stocks:
            res = self.stocks[resource_type]
            res.current_stock = min(res.max_capacity, res.current_stock + amount)

    def get_price_multiplier(self, category: str = "goods", monopoly_manager: Optional[Any] = None) -> float:
        """Returns effective price scalar for a given item category, factored by hoarding multipliers."""
        base_mult = 1.0
        res = self.stocks.get(category)
        if res:
            base_mult = res.price_multiplier * (1.0 + self.trade_disruption * 0.2)

        # Check Monopoly hoarding price surges
        if monopoly_manager and hasattr(monopoly_manager, "get_commodity_price_multiplier"):
            hoard_mult = monopoly_manager.get_commodity_price_multiplier(category)
            return base_mult * hoard_mult
        elif hasattr(self, "game_reference") and self.game_reference and hasattr(self.game_reference, "monopoly_manager"):
            hoard_mult = self.game_reference.monopoly_manager.get_commodity_price_multiplier(category)
            return base_mult * hoard_mult

        return base_mult

    def to_dict(self) -> Dict[str, Any]:
        """Serializes economic state."""
        return {
            "trade_disruption": self.trade_disruption,
            "stocks": {
                k: {
                    "current_stock": v.current_stock,
                    "max_capacity": v.max_capacity,
                    "daily_production": v.daily_production,
                    "daily_consumption": v.daily_consumption,
                    "base_price": v.base_price
                } for k, v in self.stocks.items()
            }
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes economic state."""
        if not data:
            return
        self.trade_disruption = data.get("trade_disruption", 0.0)
        stocks_data = data.get("stocks", {})
        for k, v in stocks_data.items():
            if k in self.stocks:
                self.stocks[k].current_stock = v.get("current_stock", self.stocks[k].current_stock)
                self.stocks[k].max_capacity = v.get("max_capacity", self.stocks[k].max_capacity)
                self.stocks[k].daily_production = v.get("daily_production", self.stocks[k].daily_production)
                self.stocks[k].daily_consumption = v.get("daily_consumption", self.stocks[k].daily_consumption)
