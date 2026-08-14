"""
Echoes of Asterra - Rival Adventurer System (Valen the Wanderer)
Simulates an autonomous rival adventurer who travels the world, hunts monsters,
claims bounties, directly influences world danger and prosperity metrics in WorldState,
competitively explores dungeon floors, and tracks player relationships via NPCMemory.
"""
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

from rpg.events import EventBus
from rpg.constants import (
    REL_ENEMY, REL_STRANGER, REL_ACQUAINTANCE, REL_FRIEND, REL_CLOSE_FRIEND
)
from rpg.dialogue import DialogueNode, DialogueChoice

logger = logging.getLogger("RivalAdventurer")

RIVAL_NPC_ID = "rival_valen"
RIVAL_SHORT_ID = "valen"

ROAMING_ZONES = ["village", "forest", "cave", "ruins", "dungeon"]


@dataclass
class RivalAdventurerData:
    """Persistent state for the Rival Adventurer."""
    name: str = "Valen"
    title: str = "The Freelance Blade"
    level: int = 1
    xp: int = 0
    gold: int = 60
    current_zone: str = "forest"
    monsters_slain: int = 0
    quests_completed: int = 0
    dungeon_floors_cleared: int = 0
    last_action: str = "Scouting the Forest Crossroads"
    activity_log: List[str] = field(default_factory=lambda: ["Arrived in Asterra looking for glory."])
    has_contested_dungeon: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "level": self.level,
            "xp": self.xp,
            "gold": self.gold,
            "current_zone": self.current_zone,
            "monsters_slain": self.monsters_slain,
            "quests_completed": self.quests_completed,
            "dungeon_floors_cleared": self.dungeon_floors_cleared,
            "last_action": self.last_action,
            "activity_log": list(self.activity_log[-10:]),
            "has_contested_dungeon": self.has_contested_dungeon
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RivalAdventurerData':
        if not data:
            return cls()
        return cls(
            name=data.get("name", "Valen"),
            title=data.get("title", "The Freelance Blade"),
            level=data.get("level", 1),
            xp=data.get("xp", 0),
            gold=data.get("gold", 60),
            current_zone=data.get("current_zone", "forest"),
            monsters_slain=data.get("monsters_slain", 0),
            quests_completed=data.get("quests_completed", 0),
            dungeon_floors_cleared=data.get("dungeon_floors_cleared", 0),
            last_action=data.get("last_action", "Scouting the Forest Crossroads"),
            activity_log=list(data.get("activity_log", ["Arrived in Asterra."])),
            has_contested_dungeon=data.get("has_contested_dungeon", False)
        )


class RivalAdventurerManager:
    """
    Coordinates rival adventurer simulation, parallel world progression,
    dungeon chest contention, and EventBus messaging.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.data = RivalAdventurerData()
        self.game_reference: Any = None
        if self.event_bus:
            self.register_event_listeners(self.event_bus)

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes to world events."""
        self.event_bus = event_bus
        event_bus.subscribe("npc_talked", self._on_npc_talked)
        event_bus.subscribe("enemy_killed", self._on_enemy_killed)
        event_bus.subscribe("quest_completed", self._on_quest_completed)

    def _on_npc_talked(self, npc_id: str, **kwargs: Any) -> None:
        if npc_id in [RIVAL_NPC_ID, RIVAL_SHORT_ID, "Valen"]:
            logger.info("Player interacted with Rival Adventurer %s", self.data.name)

    def _on_enemy_killed(self, enemy_type: str = "", **kwargs: Any) -> None:
        # Rival gains subtle competitive drive when player slays enemies
        if random.random() < 0.15:
            self.data.xp += 10
            self._check_level_up()

    def _on_quest_completed(self, quest_id: str = "", **kwargs: Any) -> None:
        # Rival gets inspired to take on bigger bounties
        self.data.gold += 15
        self.data.xp += 20
        self._check_level_up()

    def _check_level_up(self) -> None:
        xp_needed = self.data.level * 100
        if self.data.xp >= xp_needed and self.data.level < 20:
            self.data.level += 1
            self.data.xp -= xp_needed
            self._log_activity(f"{self.data.name} reached Level {self.data.level}!")
            if self.event_bus:
                self.event_bus.emit("rival_level_up", rival_name=self.data.name, level=self.data.level)

    def _log_activity(self, text: str) -> None:
        self.data.last_action = text
        self.data.activity_log.append(text)
        if len(self.data.activity_log) > 15:
            self.data.activity_log.pop(0)

    def simulate_day(self, world_state: Any, day: int) -> Dict[str, Any]:
        """
        Executes autonomous daily adventure simulation for Valen:
        - Roams to a new target zone
        - Slays monsters / clears bounties / explores dungeons
        - Directly updates WorldState danger_level, prosperity, road_safety
        - Emits EventBus signals
        """
        # 1. Roam to a zone
        previous_zone = self.data.current_zone
        possible_zones = [z for z in ROAMING_ZONES if z != previous_zone]
        self.data.current_zone = random.choice(possible_zones) if possible_zones else "forest"

        zone = self.data.current_zone
        result = {
            "day": day,
            "zone": zone,
            "action": "",
            "monsters_slain": 0,
            "prosperity_change": 0.0,
            "danger_change": 0.0
        }

        # 2. Perform parallel adventure based on current zone
        if zone in ["forest", "cave"]:
            # Beast hunt
            slain = random.randint(2, 4)
            self.data.monsters_slain += slain
            self.data.xp += slain * 25
            self.data.gold += slain * 8
            
            # Impact world metrics: decreases danger, improves road safety
            danger_reduction = 2.5
            safety_increase = 4.0
            if hasattr(world_state, "danger_level"):
                world_state.danger_level = max(5.0, world_state.danger_level - danger_reduction)
            if hasattr(world_state, "road_safety"):
                world_state.road_safety = min(100.0, world_state.road_safety + safety_increase)
            if hasattr(world_state, "monster_density"):
                world_state.monster_density = max(10.0, world_state.monster_density - 2.0)

            action_desc = f"Hunted {slain} beasts in the {zone}, securing traveler routes."
            self._log_activity(f"Day {day}: {action_desc}")
            result["action"] = action_desc
            result["monsters_slain"] = slain
            result["danger_change"] = -danger_reduction

        elif zone == "village":
            # Bounty / Guard assistance
            self.data.quests_completed += 1
            self.data.gold += 35
            self.data.xp += 40
            
            # Impact world metrics: boosts settlement prosperity
            prosperity_boost = 2.0
            if hasattr(world_state, "prosperity"):
                world_state.prosperity = min(100.0, world_state.prosperity + prosperity_boost)
            if hasattr(world_state, "guard_strength"):
                world_state.guard_strength = min(100.0, world_state.guard_strength + 3.0)

            action_desc = "Assisted Elder Eldrin with village logistics and defenses."
            self._log_activity(f"Day {day}: {action_desc}")
            result["action"] = action_desc
            result["prosperity_change"] = prosperity_boost

        elif zone in ["ruins", "dungeon"]:
            # Dungeon expedition
            self.data.dungeon_floors_cleared += 1
            self.data.monsters_slain += 3
            self.data.gold += 50
            self.data.xp += 80
            self.data.has_contested_dungeon = True

            danger_reduction = 3.5
            if hasattr(world_state, "danger_level"):
                world_state.danger_level = max(5.0, world_state.danger_level - danger_reduction)

            action_desc = f"Explored deep {zone} chambers and vanquished ancient guardians."
            self._log_activity(f"Day {day}: {action_desc}")
            result["action"] = action_desc
            result["danger_change"] = -danger_reduction

        self._check_level_up()

        # Emit simulation event
        if self.event_bus:
            self.event_bus.emit(
                "rival_daily_action",
                rival_name=self.data.name,
                zone=self.data.current_zone,
                action=result["action"],
                day=day
            )

        return result

    def contest_dungeon_loot(self, loot_list: List[Tuple[str, int]], depth: int) -> Tuple[List[Tuple[str, int]], bool]:
        """
        Dungeon Chest Contention:
        When Valen is ahead in the dungeon, he claims the primary rare item from one chest,
        leaving a generous replacement consumable and a signature rival calling card.
        """
        if not loot_list:
            return loot_list, False

        # Chance to contest if rival cleared dungeon floor or high depth
        should_contest = self.data.has_contested_dungeon and depth >= 2
        if not should_contest:
            return loot_list, False

        # Valen takes the primary rare item and leaves healing potion and note
        modified_loot = [("Red Potion", 2), ("Iron Ore", 1)]
        self.data.has_contested_dungeon = False  # Consumed for this dungeon run
        self._log_activity(f"Claimed ancestral treasure from Dungeon Floor {depth} before the Hero.")
        
        if self.event_bus:
            self.event_bus.emit("rival_contested_chest", depth=depth, rival_name=self.data.name)

        return modified_loot, True

    def build_dialogue_nodes(self, game: Any, npc_instance: Any) -> DialogueNode:
        """
        Generates contextual branching dialogue connecting with NPCMemory:
        - Greetings reflecting Friendship Level (Enemy, Stranger, Acquaintance, Friend, Close Friend)
        - Action choices: Inquire activity, Assist / Gift Potion, Spar / Duel, Barter
        """
        npc_memory = getattr(game, "npc_memory", None)
        player = getattr(game, "player", None)
        dm = game.dialogue_manager

        mem = npc_memory.get_memory(RIVAL_SHORT_ID) if npc_memory else None
        friendship = mem.friendship_level if mem else REL_STRANGER

        # Base greeting based on friendship
        if friendship == REL_ENEMY:
            greeting = f"Draw your steel if you must, {player.name if player else 'stranger'}. Asterra isn't big enough for the both of us."
        elif friendship == REL_CLOSE_FRIEND:
            greeting = "Ah, my favorite rival! Together there's no beast in Asterra we cannot fell. How goes your journey?"
        elif friendship == REL_FRIEND:
            greeting = "Well met, partner! Always good to see a competent blade in the wild."
        elif friendship == REL_ACQUAINTANCE:
            greeting = "Greetings! You're making quite a name for yourself around Asterra. I have to stay sharp to keep up."
        else:
            greeting = "I am Valen, freelance blade of the Asterra Wilds. If you're hunting bounties, make sure you don't slow me down."

        root_node_id = "rival_valen_root"
        choices: List[DialogueChoice] = []

        # Choice 1: Ask about recent adventures
        def ask_activity():
            report_text = f"My recent report: {self.data.last_action} (Total Slain: {self.data.monsters_slain}, Quests: {self.data.quests_completed}, Level: {self.data.level})."
            node_act = DialogueNode(
                "rival_valen_activity",
                self.data.name,
                report_text,
                [DialogueChoice("Keep up the good fight.", None)]
            )
            dm.add_node(node_act)
            dm.start_dialogue("rival_valen_activity")

        choices.append(DialogueChoice("💬 'What are you currently hunting?'", None, ask_activity))

        # Choice 2: Gift healing supplies (Assist)
        def give_potion():
            if player and player.inventory.has_item("Red Potion"):
                player.inventory.remove_item("Red Potion", 1)
                if npc_memory:
                    npc_memory.record_gift(RIVAL_SHORT_ID, "Red Potion", 15)
                # Rival gives advice or iron in return
                reward_item = "Iron Ore"
                from rpg.items import create_item
                itm = create_item(reward_item, 2)
                if itm and player.inventory.add_item(itm):
                    pass
                player.gain_xp(35)
                
                resp_text = "Much appreciated! Here, take some refined iron ore I salvaged from my last expedition."
                node_gift = DialogueNode(
                    "rival_valen_gift",
                    self.data.name,
                    resp_text,
                    [DialogueChoice("Glad to help.", None)]
                )
                dm.add_node(node_gift)
                dm.start_dialogue("rival_valen_gift")
                if self.event_bus:
                    self.event_bus.emit("rival_assisted", player_name=player.name, rival_name=self.data.name)

        if player and player.inventory.has_item("Red Potion"):
            choices.append(DialogueChoice("🎁 'Here, take a Red Potion for the road.' (+Relationship, Get Iron)", None, give_potion))

        # Choice 3: Friendly Sparring / Challenge
        def spar_challenge():
            if npc_memory:
                if friendship == REL_ENEMY:
                    npc_memory.modify_relationship(RIVAL_SHORT_ID, -10)
                    resp = "You dare provoke me again?! Next time, steel will clash for real!"
                else:
                    npc_memory.modify_relationship(RIVAL_SHORT_ID, 5)
                    resp = "A splendid clash! Your footwork has grown formidable. Let us test our blades again soon."
            else:
                resp = "A fine bout!"
            if player:
                player.gain_xp(40)
            node_spar = DialogueNode(
                "rival_valen_spar",
                self.data.name,
                resp,
                [DialogueChoice("Until next time.", None)]
            )
            dm.add_node(node_spar)
            dm.start_dialogue("rival_valen_spar")

        choices.append(DialogueChoice("⚔️ 'Care to spar with blades?' (+XP & Combat Camaraderie)", None, spar_challenge))

        # Choice 4: Trade / Barter
        def barter_supplies():
            if player and player.gold >= 30:
                player.gold -= 30
                from rpg.items import create_item
                bought = create_item("Blue Potion", 2)
                if bought:
                    player.inventory.add_item(bought)
                if npc_memory:
                    npc_memory.modify_relationship(RIVAL_SHORT_ID, 5)
                node_barter = DialogueNode(
                    "rival_valen_barter",
                    self.data.name,
                    "Pleasure doing business. These arcane draughts served me well in the Crypt.",
                    [DialogueChoice("Thank you.", None)]
                )
                dm.add_node(node_barter)
                dm.start_dialogue("rival_valen_barter")

        if player and player.gold >= 30:
            choices.append(DialogueChoice("⚖️ 'Buy 2 Blue Potions from Valen' (30 Gold)", None, barter_supplies))

        choices.append(DialogueChoice("Farewell for now.", None))

        root_node = DialogueNode(root_node_id, f"{self.data.name} {self.data.title}", greeting, choices)
        dm.add_node(root_node)
        return root_node

    def to_dict(self) -> Dict[str, Any]:
        """Serializes rival adventurer manager state."""
        return {"data": self.data.to_dict()}

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes rival adventurer manager state."""
        if not data:
            return
        if "data" in data:
            self.data = RivalAdventurerData.from_dict(data["data"])

    def reset(self) -> None:
        """Resets rival adventurer to starting state for new game / save slots."""
        self.data = RivalAdventurerData()
