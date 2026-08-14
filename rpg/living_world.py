"""
Echoes of Asterra - Living World Manager (Central Simulation Orchestrator)
Unifies and coordinates all simulation subsystems:
WorldScheduler, WorldState, Adaptive Game Director, Living Economy, NPC Job Schedules,
Caravans, Faction Warfare, Settlement Growth, and Monster Ecology.
"""
from typing import Dict, Any

from rpg.events import EventBus
from rpg.scheduler import WorldScheduler, TickType
from rpg.world_state import WorldState
from rpg.economy import EconomyManager
from rpg.npc_schedule import NPCScheduleManager
from rpg.caravan import CaravanManager
from rpg.faction_war import FactionWarManager
from rpg.settlement import SettlementManager
from rpg.ecology import EcologyManager
from rpg.director import GameDirector
from rpg.progression import ProgressionManager

class LivingWorldManager:
    """
    Central simulation manager coordinating all living world sub-simulations.
    Invoked per-frame from Game.update(dt).
    """
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.game_reference: Any = None
        
        # Instantiate sub-simulations
        self.scheduler = WorldScheduler(self.event_bus)
        self.world_state = WorldState()
        self.economy = EconomyManager()
        self.schedules = NPCScheduleManager()
        self.caravans = CaravanManager()
        self.faction_war = FactionWarManager()
        self.settlement = SettlementManager()
        self.ecology = EcologyManager()
        self.director = GameDirector()
        self.progression = ProgressionManager()
        from rpg.consequences import ConsequenceManager
        self.consequences = ConsequenceManager(self.event_bus)
        from rpg.rumors import RumorBoard
        self.rumors = RumorBoard(self.event_bus)
        from rpg.rival import RivalAdventurerManager
        self.rival = RivalAdventurerManager(self.event_bus)
        self.rival.game_reference = self.game_reference
        
        # Backward compatibility alias
        self.ai_director = self.director
        
        # Register EventBus listeners across all subsystems
        self.world_state.register_event_listeners(self.event_bus)
        self.economy.register_event_listeners(self.event_bus)
        self.schedules.register_event_listeners(self.event_bus)
        self.caravans.register_event_listeners(self.event_bus)
        self.faction_war.register_event_listeners(self.event_bus)
        self.settlement.register_event_listeners(self.event_bus)
        self.ecology.register_event_listeners(self.event_bus)
        self.progression.register_event_listeners(self.event_bus)
        self.consequences.register_event_listeners(self.event_bus)
        self.rumors.register_event_listeners(self.event_bus)
        self.rival.register_event_listeners(self.event_bus)
        
        from rpg.emergent_quests import EmergentQuestGenerator
        self.emergent_quests = EmergentQuestGenerator(self.event_bus)
        
        # Subscribe Director and Subsystems to Scheduler Ticks
        self.scheduler.subscribe(TickType.DAY.value, self._on_scheduler_day_tick)
        self.event_bus.subscribe("director_recommendation", self._on_director_recommendation)

    def _on_scheduler_day_tick(self, day: int, season: str, **kwargs: Any) -> None:
        """Invoked on every Day Tick from WorldScheduler."""
        # 1. Update WorldState daily drift
        self.world_state.day_tick(self.event_bus)
        
        # 2. Generate immutable WorldSnapshot and trigger GameDirector evaluation
        snapshot = self.world_state.create_snapshot(self.game_reference)
        self.director.evaluate(snapshot, self.event_bus)

        # 3. Evaluate Emergent Quest triggers
        if self.game_reference and hasattr(self.game_reference, "quest_manager"):
            self.emergent_quests.evaluate_world(self.world_state, self.game_reference.quest_manager, day)

        # 4. Simulate Rival Adventurer parallel world progression
        if hasattr(self, "rival"):
            self.rival.simulate_day(self.world_state, day)

    def _on_director_recommendation(self, action: str, effects: Dict[str, Any], **kwargs: Any) -> None:
        """Applies Director recommendations to existing simulation systems without direct private mutation."""
        if "price_mult" in effects:
            # Adjust economy price multipliers smoothly
            pass
        if "guard_density" in effects:
            self.world_state.guard_strength = min(100.0, self.world_state.guard_strength * effects["guard_density"])
        if "road_safety_bonus" in effects:
            self.world_state.road_safety = min(100.0, self.world_state.road_safety + effects["road_safety_bonus"])
        if "bandit_aggression" in effects:
            self.world_state.bandit_strength = min(100.0, self.world_state.bandit_strength * effects["bandit_aggression"])
        if "monster_spawn_mult" in effects:
            self.world_state.monster_density = min(100.0, self.world_state.monster_density * effects["monster_spawn_mult"])

    def update(self, dt: float, player: Any, world_manager: Any, visible_sprites: Any) -> None:
        """
        Single entry point called per-frame by Game.update(dt).
        Orchestrates sub-simulation ticks driven by WorldScheduler.
        """
        # 1. Update centralized WorldScheduler clock (single authority for time)
        self.scheduler.update(dt)
        
        # Sync WorldState properties with WorldScheduler
        self.world_state.time_accumulator = self.scheduler.time_accumulator
        self.world_state.day = self.scheduler.day
        self.world_state.season = self.scheduler.season
        
        # 2. Update AI Director real-time observation loop
        self.director.update(dt, player, self.world_state)
        
        # 3. Update NPC Job Schedules and pathfinding
        current_map = world_manager.current_map_name if world_manager else "village"
        npcs_list = [sprite for sprite in visible_sprites if hasattr(sprite, "npc_type")] if visible_sprites else []
        self.schedules.update(dt, self.scheduler.time_of_day, npcs_list, current_map)
        
        # 4. Update physical caravans along trade routes
        self.caravans.update(dt, current_map, visible_sprites)
        
        # 5. Update Faction Warfare & Skirmish timers
        self.faction_war.update(dt)
        if hasattr(self, "consequences"):
            self.consequences.game = self.game_reference

    def get_combined_price_multiplier(
        self,
        category: str = "goods",
        map_name: str = "village",
        merchant_reputation: float = 0.0,
        friendship_tier: float = 0.0
    ) -> float:
        """
        Single Source of Truth calculation combining all shop price multipliers:
        - Economy stock scarcity / supply scalar
        - Faction War map control tax modifier
        - Settlement tier prosperity discount
        - Merchant Faction reputation standing discount
        - NPC friendship bond discount

        Guarantees final price multiplier is strictly clamped between 0.30x and 3.00x.
        """
        econ_scalar = self.economy.get_price_multiplier(category) if hasattr(self, "economy") and self.economy else 1.0
        tax_modifier = self.faction_war.get_map_tax_modifier(map_name) if hasattr(self, "faction_war") and self.faction_war else 0.0
        tax_scalar = max(0.0, 1.0 + tax_modifier)

        settlement_discount = self.settlement.get_tier_discount() if hasattr(self, "settlement") and self.settlement else 0.0
        trade_spec_discount = self.settlement.get_trade_discount() if hasattr(self, "settlement") and self.settlement else 0.0
        total_settlement_discount = min(0.40, settlement_discount + trade_spec_discount)

        faction_discount = min(0.20, max(-0.25, merchant_reputation / 500.0))
        friend_discount = min(0.15, max(0.0, friendship_tier / 100.0))

        raw_multiplier = econ_scalar * tax_scalar * (1.0 - total_settlement_discount) * (1.0 - faction_discount) * (1.0 - friend_discount)

        # Strict safety bounds: never explode (> 3.0x) and never negative/free (< 0.30x)
        return max(0.30, min(3.00, raw_multiplier))

    def get_final_shop_price(
        self,
        base_price: int,
        category: str = "goods",
        map_name: str = "village",
        merchant_reputation: float = 0.0,
        friendship_tier: float = 0.0
    ) -> int:
        """Calculates final integer buy price, guaranteed to be at least 1 Gold and bounded."""
        mult = self.get_combined_price_multiplier(category, map_name, merchant_reputation, friendship_tier)
        return max(1, int(base_price * mult))

    def reset(self) -> None:
        """Resets all living world subsystems for a fresh game session."""
        if hasattr(self, "world_state") and hasattr(self.world_state, "reset"):
            self.world_state.reset()
        if hasattr(self, "economy") and hasattr(self.economy, "reset"):
            self.economy.reset()
        if hasattr(self, "caravans") and hasattr(self.caravans, "reset"):
            self.caravans.reset()
        if hasattr(self, "faction_war") and hasattr(self.faction_war, "reset"):
            self.faction_war.reset()
        if hasattr(self, "settlement") and hasattr(self.settlement, "reset"):
            self.settlement.reset()
        if hasattr(self, "ecology") and hasattr(self.ecology, "reset"):
            self.ecology.reset()
        if hasattr(self, "consequences") and hasattr(self.consequences, "reset"):
            self.consequences.reset()
        if hasattr(self, "rumors") and hasattr(self.rumors, "reset"):
            self.rumors.reset()
        if hasattr(self, "emergent_quests") and hasattr(self.emergent_quests, "reset"):
            self.emergent_quests.reset()
        if hasattr(self, "rival") and hasattr(self.rival, "reset"):
            self.rival.reset()

    def to_dict(self) -> Dict[str, Any]:
        """Unified serialization of all world simulations."""
        return {
            "scheduler": self.scheduler.to_dict(),
            "world_state": self.world_state.to_dict(),
            "economy": self.economy.to_dict(),
            "schedules": self.schedules.to_dict(),
            "caravans": self.caravans.to_dict(),
            "faction_war": self.faction_war.to_dict(),
            "settlement": self.settlement.to_dict(),
            "ecology": self.ecology.to_dict(),
            "director": self.director.to_dict(),
            "progression": self.progression.to_dict(),
            "consequences": self.consequences.to_dict() if hasattr(self, "consequences") else {},
            "rumors": self.rumors.to_dict() if hasattr(self, "rumors") else {},
            "rival": self.rival.to_dict() if hasattr(self, "rival") else {}
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Unified deserialization of all world simulations."""
        if not data:
            return
        if "scheduler" in data:
            self.scheduler.from_dict(data["scheduler"])
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
        if "director" in data:
            self.director.from_dict(data["director"])
        elif "ai_director" in data:
            self.director.from_dict(data["ai_director"])
        if "progression" in data:
            self.progression.from_dict(data["progression"])
        if "consequences" in data and hasattr(self, "consequences"):
            self.consequences.from_dict(data["consequences"])
        if "rumors" in data and hasattr(self, "rumors"):
            self.rumors.from_dict(data["rumors"])
        if "rival" in data and hasattr(self, "rival"):
            self.rival.from_dict(data["rival"])
