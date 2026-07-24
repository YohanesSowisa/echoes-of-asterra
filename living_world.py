"""
Echoes of Asterra - Living World Manager (Central Simulation Orchestrator)
Unifies and coordinates all 8 simulation subsystems:
WorldState, Living Economy, NPC Job Schedules, Caravans, Faction Warfare, Settlement Growth,
Monster Ecology, and the Decoupled AI Director into a single scalable entry point.
"""
from typing import Dict, Any, List, Optional
from rpg.events import EventBus
from rpg.world_state import WorldState
from rpg.economy import EconomyManager
from rpg.npc_schedule import NPCScheduleManager
from rpg.caravan import CaravanManager
from rpg.faction_war import FactionWarManager
from rpg.settlement import SettlementManager
from rpg.ecology import EcologyManager
from rpg.ai_director import AIDirector

class LivingWorldManager:
    """
    Central simulation manager coordinating all living world sub-simulations.
    Invoked per-frame from Game.update(dt).
    """
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        
        # Instantiate sub-simulations
        self.world_state = WorldState()
        self.economy = EconomyManager()
        self.schedules = NPCScheduleManager()
        self.caravans = CaravanManager()
        self.faction_war = FactionWarManager()
        self.settlement = SettlementManager()
        self.ecology = EcologyManager()
        self.ai_director = AIDirector()
        
        # Register EventBus listeners across all subsystems
        self.world_state.register_event_listeners(self.event_bus)
        self.economy.register_event_listeners(self.event_bus)
        self.schedules.register_event_listeners(self.event_bus)
        self.caravans.register_event_listeners(self.event_bus)
        self.faction_war.register_event_listeners(self.event_bus)
        self.settlement.register_event_listeners(self.event_bus)
        self.ecology.register_event_listeners(self.event_bus)
        self.ai_director.register_event_listeners(self.event_bus)

    def update(self, dt: float, player: Any, world_manager: Any, visible_sprites: Any) -> None:
        """
        Single entry point called per-frame by Game.update(dt).
        Orchestrates sub-simulation ticks in optimal order.
        """
        # 1. Update clock, day-night time, and seasons
        self.world_state.update(dt, self.event_bus)
        
        # 2. Update AI Director pacing observer
        self.ai_director.update(dt, player, self.world_state)
        
        # 3. Update NPC Job Schedules and pathfinding
        current_map = world_manager.current_map_name if world_manager else "village"
        npcs_list = [sprite for sprite in visible_sprites if hasattr(sprite, "npc_type")] if visible_sprites else []
        self.schedules.update(dt, self.world_state.time_of_day, npcs_list, current_map)
        
        # 4. Update physical caravans along trade routes
        self.caravans.update(dt, current_map, visible_sprites)
        
        # 5. Update Faction Warfare & Skirmish timers
        self.faction_war.update(dt)

    def get_combined_price_multiplier(self, category: str = "goods", map_name: str = "village") -> float:
        """Calculates total combined item price scalar (Economy + Faction Tax + Settlement Discount)."""
        econ_scalar = self.economy.get_price_multiplier(category)
        tax_scalar = 1.0 + self.faction_war.get_map_tax_modifier(map_name)
        discount = self.settlement.get_tier_discount()
        return max(0.5, econ_scalar * tax_scalar * (1.0 - discount))

    def to_dict(self) -> Dict[str, Any]:
        """Unified serialization of all world simulations."""
        return {
            "world_state": self.world_state.to_dict(),
            "economy": self.economy.to_dict(),
            "schedules": self.schedules.to_dict(),
            "caravans": self.caravans.to_dict(),
            "faction_war": self.faction_war.to_dict(),
            "settlement": self.settlement.to_dict(),
            "ecology": self.ecology.to_dict(),
            "ai_director": self.ai_director.to_dict()
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Unified deserialization of all world simulations."""
        if not data:
            return
        if "world_state" in data:
            self.world_state.from_dict(data["world_state"])
        if "economy" in data:
            self.economy.from_dict(data["economy"])
        if "schedules" in data:
            self.schedules.from_dict(data["schedules"])
        if "caravans" in data:
            self.caravans.from_dict(data["caravans"])
        if "faction_war" in data:
            self.faction_war.from_dict(data["faction_war"])
        if "settlement" in data:
            self.settlement.from_dict(data["settlement"])
        if "ecology" in data:
            self.ecology.from_dict(data["ecology"])
        if "ai_director" in data:
            self.ai_director.from_dict(data["ai_director"])
