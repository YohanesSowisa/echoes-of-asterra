"""
Echoes of Asterra - Consequence Chain Engine (The Whispering World)
Manages multi-day delayed consequence chains linking Ecology, Economy, Quests, and NPC Dialogue.
Player actions trigger causal ripples that arrive 2-5 in-game days later.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Callable, Optional, Set
from rpg.events import EventBus


@dataclass
class ConsequenceChain:
    """Represents a multi-stage delayed causal chain in Asterra."""
    chain_id: str
    trigger_topic: str
    delay_days: int
    due_day: int = -1
    is_pending: bool = False
    is_executed: bool = False
    description: str = ""


class ConsequenceManager:
    """
    Coordinates multi-day delayed consequences across Asterra.
    When a trigger event occurs (e.g. overhunting wolves), a consequence is queued
    to execute N days later via WorldScheduler day ticks.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.active_chains: Dict[str, ConsequenceChain] = {}
        self.completed_chains: Set[str] = set()
        self.game: Any = None

        if self.event_bus:
            self.register_event_listeners(self.event_bus)

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes to EventBus for trigger monitoring and day ticks."""
        self.event_bus = event_bus
        event_bus.subscribe("day_changed", self._on_day_changed)
        event_bus.subscribe("enemy_killed", self._on_enemy_killed)

    def _on_enemy_killed(self, enemy_type: str = "", **kwargs: Any) -> None:
        """Evaluates immediate environmental triggers when monsters are slain."""
        if not self.game:
            return

        current_day = getattr(self.game.world_state, "day", 1) if hasattr(self.game, "world_state") else 1

        # Chain 1 Trigger: Wolf Overhunting / Population collapse
        if "wolf" in enemy_type and "wolf_extinction_chain" not in self.active_chains and "wolf_extinction_chain" not in self.completed_chains:
            if hasattr(self.game, "living_world") and hasattr(self.game.living_world, "ecology"):
                wolves = self.game.living_world.ecology.get_population("wolf")
                if wolves <= 2:  # Population depleted below 25%
                    self.queue_consequence(
                        chain_id="wolf_extinction_chain",
                        delay_days=2,
                        current_day=current_day,
                        description="Wolf extinction leading to deer overpopulation and crop devastation."
                    )

    def queue_consequence(self, chain_id: str, delay_days: int, current_day: int, description: str = "") -> None:
        """Queues a delayed consequence chain to execute on (current_day + delay_days)."""
        due_day = current_day + delay_days
        chain = ConsequenceChain(
            chain_id=chain_id,
            trigger_topic="wolf_depleted",
            delay_days=delay_days,
            due_day=due_day,
            is_pending=True,
            is_executed=False,
            description=description
        )
        self.active_chains[chain_id] = chain
        if self.event_bus:
            self.event_bus.emit("consequence_queued", chain_id=chain_id, due_day=due_day)

    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        """Evaluates pending consequence chains on daily clock ticks."""
        for chain_id, chain in list(self.active_chains.items()):
            if chain.is_pending and not chain.is_executed:
                if day >= chain.due_day:
                    self._execute_chain(chain)

    def _execute_chain(self, chain: ConsequenceChain) -> None:
        """Executes the consequence action and fires world events."""
        chain.is_pending = False
        chain.is_executed = True
        self.completed_chains.add(chain.chain_id)

        if chain.chain_id == "wolf_extinction_chain":
            self._execute_wolf_extinction_chain()

        if self.event_bus:
            self.event_bus.emit("consequence_executed", chain_id=chain.chain_id)

    def _execute_wolf_extinction_chain(self) -> None:
        """Action for Chain 1: Devastates food stocks, alters Silas & Faye dialogue, spawns culling quest."""
        if not self.game:
            return

        # 1. Reduce food stock by 40% in EconomyManager
        if hasattr(self.game, "living_world") and hasattr(self.game.living_world, "economy"):
            food_stock = self.game.living_world.economy.stocks.get("food")
            if food_stock:
                food_stock.current_stock = max(5.0, food_stock.current_stock * 0.6)

        # 2. Set WorldState consequence flag
        if hasattr(self.game, "world_state"):
            self.game.world_state.completed_event_ids.add("consequence_deer_overpopulation")

        # 3. Inject reactive dialogue nodes into DialogueManager
        if hasattr(self.game, "dialogue_manager"):
            from rpg.dialogue import DialogueNode, DialogueChoice
            self.game.dialogue_manager.add_node(DialogueNode(
                "silas_deer_crisis",
                "Merchant Silas",
                "The crop fields were invaded by herds of deer! Food supplies are ruined, and prices have skyrocketed.",
                [DialogueChoice("That's awful news.", None)]
            ))
            self.game.dialogue_manager.add_node(DialogueNode(
                "faye_deer_crisis",
                "Ranger Faye",
                "The wolves used to hunt the deer and keep them in check. Without predators, the forest ecosystem collapsed.",
                [DialogueChoice("I see the balance now...", None)]
            ))

        # 4. Generate Emergent Quest "Deer Culling"
        if hasattr(self.game, "quest_manager"):
            from rpg.quests import Quest, QuestObjective
            deer_quest = Quest(
                quest_id="deer_culling_emergent",
                title="Ecological Crisis: Deer Culling",
                description="Without wolves, deer have overrun the forest. Slay slimes and forest creatures to clear the farmland.",
                objectives=[QuestObjective("Defeat 4 Forest Slimes", "kill", "slime", 4)],
                rewards={"exp": 200, "gold": 120, "items": [("Baked Bread", 3)]}
            )
            self.game.quest_manager.quests["deer_culling_emergent"] = deer_quest
            self.game.quest_manager.accept_quest("deer_culling_emergent")

        # 5. Push toast notification
        if hasattr(self.game, "notification_manager"):
            from rpg.notification import NotificationPriority
            self.game.notification_manager.push_toast(
                "🌊 World Consequence: Ecosystem Shift! Deer crop destruction has disrupted Food stocks.",
                priority=NotificationPriority.HIGH
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes consequence manager state."""
        return {
            "active_chains": {
                k: {
                    "chain_id": v.chain_id,
                    "trigger_topic": v.trigger_topic,
                    "delay_days": v.delay_days,
                    "due_day": v.due_day,
                    "is_pending": v.is_pending,
                    "is_executed": v.is_executed,
                    "description": v.description
                } for k, v in self.active_chains.items()
            },
            "completed_chains": list(self.completed_chains)
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes consequence manager state."""
        if not data:
            return
        self.completed_chains = set(data.get("completed_chains", []))
        chains_data = data.get("active_chains", {})
        for k, v in chains_data.items():
            self.active_chains[k] = ConsequenceChain(
                chain_id=v.get("chain_id", k),
                trigger_topic=v.get("trigger_topic", ""),
                delay_days=v.get("delay_days", 2),
                due_day=v.get("due_day", 1),
                is_pending=v.get("is_pending", False),
                is_executed=v.get("is_executed", False),
                description=v.get("description", "")
            )
