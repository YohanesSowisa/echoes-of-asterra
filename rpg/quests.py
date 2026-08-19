"""
Echoes of Asterra - Quest System
Tracks active and completed quests, updates objectives, and awards items, gold, and exp.
"""
from typing import Dict, List, Any, Optional
from rpg.constants import QUEST_NOT_STARTED, QUEST_ACTIVE, QUEST_COMPLETED
from rpg.items import create_item

class QuestObjective:
    """
    Tracks progress for a specific quest criteria.
    Types: "talk" (speak to NPC), "kill" (defeat monster), "collect" (retrieve items).
    """
    def __init__(self, text: str, obj_type: str, target: str, required_count: int) -> None:
        self.text = text
        self.obj_type = obj_type
        self.target = target
        self.required_count = required_count
        self.current_count = 0

    def is_complete(self) -> bool:
        """Returns True if objective target count is met."""
        return self.current_count >= self.required_count

    def update_progress(self, amount: int) -> None:
        """Adds to current count, clamped at required limit."""
        self.current_count = min(self.required_count, self.current_count + amount)

    def set_progress(self, amount: int) -> None:
        """Directly sets count, clamped at required limit."""
        self.current_count = min(self.required_count, max(0, amount))

class Quest:
    """
    Holds quest text, status, objective progress, and payout details.
    Supports mutual exclusion between branching quest paths.
    """
    def __init__(
        self,
        quest_id: str,
        title: str,
        description: str,
        objectives: List[QuestObjective],
        rewards: Dict[str, Any],
        prerequisite: Optional[str] = None,
        exclusive_with: Optional[str] = None
    ) -> None:
        self.id = quest_id
        self.title = title
        self.description = description
        self.objectives = objectives
        self.rewards = rewards
        self.prerequisite = prerequisite
        self.exclusive_with = exclusive_with
        self.status = QUEST_NOT_STARTED

    def check_objectives_completed(self) -> bool:
        """Returns True if all objectives are complete."""
        return all(obj.is_complete() for obj in self.objectives)

class QuestManager:
    """
    Coordinates quest status updates, parses entity/loot kills, and distributes awards.
    """
    def __init__(self) -> None:
        self.quests: Dict[str, Quest] = {}
        self.tracked_quest_id: Optional[str] = None
        self._initialize_quests()

    def _initialize_quests(self) -> None:
        """Creates the initial game quests."""
        # 1. Main Quest: Echoes of Asterra
        self.quests["main_quest"] = Quest(
            quest_id="main_quest",
            title="The Core of Asterra",
            description="Find Elder Eldrin to understand the dark shadows spreading across the lands.",
            objectives=[
                QuestObjective("Speak to Elder Eldrin in the village", "talk", "Eldrin", 1),
                QuestObjective("Defeat 3 Wolves in the Forest", "kill", "wolf", 3),
                QuestObjective("Gather 3 Iron Ores (from Caverns, Mobs, or Silas)", "collect", "Iron Ore", 3),
                QuestObjective("Slay the Shadow Knight in the Dungeon", "kill", "boss", 1)
            ],
            rewards={
                "exp": 500,
                "gold": 250,
                "items": [("Steel Blade", 1), ("Asterra Heart", 1)]
            }
        )

        # 2. Side Quest: Slime Infestation (Independent)
        self.quests["slime_quest"] = Quest(
            quest_id="slime_quest",
            title="Slime Cleaning",
            description="Clear the forest road of bouncing green slimes.",
            objectives=[
                QuestObjective("Defeat 5 Green Slimes", "kill", "slime", 5)
            ],
            rewards={
                "exp": 100,
                "gold": 50,
                "items": [("Red Potion", 2)]
            }
        )

        # 3. Sequential Quest 1: Forest Patrol (Ranger Faye) - Prereq: main_quest
        self.quests["forest_patrol"] = Quest(
            quest_id="forest_patrol",
            title="Forest Patrol",
            description="Ranger Faye needs the forest trails cleared of monsters.",
            objectives=[
                QuestObjective("Defeat 5 Slimes", "kill", "slime", 5),
                QuestObjective("Defeat 2 Wolves", "kill", "wolf", 2)
            ],
            rewards={
                "exp": 100,
                "gold": 80,
                "items": [("Forest Apple", 3)]
            },
            prerequisite="main_quest"
        )

        # 4. Sequential Quest 2: Echoes of the Past (Scholar Mira) - Prereq: forest_patrol
        self.quests["scholar_quest"] = Quest(
            quest_id="scholar_quest",
            title="Echoes of the Past",
            description="Scholar Mira needs an Ancient Scroll from the Ruins.",
            objectives=[
                QuestObjective("Find the Ancient Scroll", "collect", "Ancient Scroll", 1)
            ],
            rewards={
                "exp": 150,
                "gold": 60,
                "items": [("Blue Potion", 2)]
            },
            prerequisite="forest_patrol"
        )

        # 5. Sequential Quest 3: Blacksmith's Apprentice (Blacksmith Dennis) - Prereq: scholar_quest
        self.quests["blacksmith_quest"] = Quest(
            quest_id="blacksmith_quest",
            title="Iron Forging",
            description="Acquire materials so the Blacksmith can forge weapons for defense. Iron Ore can be found in Caverns, dropped by Skeletons/Goblins, or bought from Merchant Silas.",
            objectives=[
                QuestObjective("Deliver 5 Iron Ores to Blacksmith (Caverns/Mobs/Silas)", "collect", "Iron Ore", 5)
            ],
            rewards={
                "exp": 150,
                "gold": 80,
                "items": [("Wooden Shield", 1), ("Blue Potion", 2)]
            },
            prerequisite="scholar_quest"
        )

        # 6. Sequential Quest 4: Lake Vigil (Guardian Kai) - Prereq: blacksmith_quest
        self.quests["lake_quest"] = Quest(
            quest_id="lake_quest",
            title="Lake Vigil",
            description="Guardian Kai patrols the lake but frost slimes have overrun the shores.",
            objectives=[
                QuestObjective("Defeat 4 Frost Slimes", "kill", "slime_blue", 4)
            ],
            rewards={
                "exp": 200,
                "gold": 100,
                "items": [("Glow Amulet", 1)]
            },
            prerequisite="blacksmith_quest"
        )

        # 7. Side Quest: Bridge Repair (Town Board / Elder Eldrin)
        self.quests["bridge_repair_quest"] = Quest(
            quest_id="bridge_repair_quest",
            title="Northern Bridge Reconstruction",
            description="The northern stone bridge to Asterra Lake collapsed. Gather materials (Oak Wood from Forest Wolves/Silas, Iron Ore from Caverns/Silas) and fund the repair.",
            objectives=[
                QuestObjective("Deliver 5 Oak Wood (from Forest Wolves / Silas)", "collect", "Oak Wood", 5),
                QuestObjective("Deliver 3 Iron Ores (from Caverns / Silas)", "collect", "Iron Ore", 3)
            ],
            rewards={
                "exp": 120,
                "gold": 60,
                "items": [("Red Potion", 2)]
            }
        )

        # 8. Side Quest: Watchtower Construction (Town Board / Elder Eldrin)
        self.quests["watchtower_quest"] = Quest(
            quest_id="watchtower_quest",
            title="Watchtower Construction",
            description="Build the village watchtower to secure the road to the Crystal Caverns. Oak Wood drops from Forest Wolves; Iron Ore can be scavenged from Caverns or Merchant Silas.",
            objectives=[
                QuestObjective("Deliver 3 Oak Wood (from Forest Wolves / Silas)", "collect", "Oak Wood", 3),
                QuestObjective("Deliver 2 Iron Ores (from Caverns / Silas)", "collect", "Iron Ore", 2)
            ],
            rewards={
                "exp": 100,
                "gold": 50,
                "items": [("Forest Apple", 3)]
            }
        )

        # 9. Side Quest: Ruins Reconnaissance Expedition (Scholar Mira)
        self.quests["ruins_expedition"] = Quest(
            quest_id="ruins_expedition",
            title="Ruins Reconnaissance Expedition",
            description="Scholar Mira needs you to explore the Sunken Ruins and recover a Relic Fragment from the ancient vaults.",
            objectives=[
                QuestObjective("Recover 1 Relic Fragment from Ruins chests", "collect", "Relic Fragment", 1),
                QuestObjective("Defeat the Bandit Warlord guarding the vault", "kill", "bandit_leader", 1)
            ],
            rewards={
                "exp": 250,
                "gold": 120,
                "items": [("Ancient Relic", 1)]
            },
            prerequisite="scholar_quest"
        )

        # 10. Mutually Exclusive Fork 1: The Knight's Path (Alliance)
        self.quests["knight_path_quest"] = Quest(
            quest_id="knight_path_quest",
            title="The Knight's Vow (Alliance)",
            description="Pledge your allegiance to the Knights of Asterra. Clear the roads and fortify village defenses.",
            objectives=[
                QuestObjective("Defeat 4 Goblins", "kill", "goblin", 4),
                QuestObjective("Deliver 3 Iron Ores", "collect", "Iron Ore", 3)
            ],
            rewards={"exp": 300, "gold": 150, "items": [("Iron Aegis", 1)]},
            prerequisite="main_quest",
            exclusive_with="shadow_path_quest"
        )

        # 11. Mutually Exclusive Fork 2: The Shadow's Path (Alliance)
        self.quests["shadow_path_quest"] = Quest(
            quest_id="shadow_path_quest",
            title="The Void Covenant (Alliance)",
            description="Embrace the shadows for power. Cleave corrupt knights and harness ancient relics.",
            objectives=[
                QuestObjective("Defeat 2 Knights", "kill", "knight", 2),
                QuestObjective("Find 1 Ancient Scroll", "collect", "Ancient Scroll", 1)
            ],
            rewards={"exp": 350, "gold": 200, "items": [("Blue Potion", 3)]},
            prerequisite="main_quest",
            exclusive_with="knight_path_quest"
        )

        # 12. Conspiracy Quest: Protect the Mage Guild Envoy (Pillar 2 Phase 3)
        self.quests["quest_conspiracy_envoy"] = Quest(
            quest_id="quest_conspiracy_envoy",
            title="Protect the Mage Guild Envoy",
            description="The Shadow Syndicate deployed Shadow Assassins to ambush Envoy Vaelin in the Sunfire Ruins. Intercept and eliminate the assassins!",
            objectives=[
                QuestObjective("Defeat 3 Shadow Assassins in Ruins", "kill", "Shadow Assassin", 3)
            ],
            rewards={
                "exp": 250,
                "gold": 150,
                "items": [("Syndicate Cipher Fragment #2", 1)]
            }
        )

    def is_quest_available(self, quest_id: str) -> bool:
        """Checks if a quest is eligible to be accepted based on prerequisites and mutual exclusions."""
        quest = self.quests.get(quest_id)
        if not quest or quest.status != QUEST_NOT_STARTED:
            return False

        if quest.exclusive_with:
            excl = self.quests.get(quest.exclusive_with)
            if excl and excl.status in [QUEST_ACTIVE, QUEST_COMPLETED]:
                return False

        if quest.prerequisite:
            prereq = self.quests.get(quest.prerequisite)
            if not prereq:
                return False
            if quest_id == "forest_patrol" or quest_id in ["knight_path_quest", "shadow_path_quest"]:
                return prereq.status in [QUEST_ACTIVE, QUEST_COMPLETED] and prereq.objectives[0].is_complete()
            return prereq.status == QUEST_COMPLETED
        return True

    def accept_quest(self, quest_id: str) -> None:
        """Sets an available quest status to active."""
        quest = self.quests.get(quest_id)
        if quest and quest.status == QUEST_NOT_STARTED:
            if not self.is_quest_available(quest_id):
                return
            quest.status = QUEST_ACTIVE
            if hasattr(self, "event_bus") and self.event_bus:
                self.event_bus.emit("first_quest_accepted", quest_id=quest_id)
                if quest_id in ["knight_path_quest", "shadow_path_quest"]:
                    alliance = "knights" if quest_id == "knight_path_quest" else "cult"
                    self.event_bus.emit("alliance_chosen", alliance=alliance)


    def handle_kill(self, enemy_type: str) -> None:
        """Increments matching kill objectives on all active quests."""
        for quest in self.quests.values():
            if quest.status == QUEST_ACTIVE:
                for obj in quest.objectives:
                    if obj.obj_type == "kill":
                        if obj.target == enemy_type or (obj.target == "slime" and "slime" in enemy_type):
                            obj.update_progress(1)

    def handle_talk(self, npc_name: str) -> None:
        """Increments conversation-based talk objectives on all active quests."""
        for quest in self.quests.values():
            if quest.status == QUEST_ACTIVE:
                for obj in quest.objectives:
                    if obj.obj_type == "talk" and obj.target == npc_name:
                        obj.update_progress(1)

    def handle_inventory_change(self, inventory: Any) -> None:
        """Syncs all collection quest counters with current item quantities."""
        for quest in self.quests.values():
            if quest.status == QUEST_ACTIVE:
                for obj in quest.objectives:
                    if obj.obj_type == "collect":
                        count = inventory.get_item_count(obj.target)
                        obj.set_progress(count)

    def check_completable_quests(self, player: Any) -> List[Quest]:
        """
        Scans active quests to see if objectives are met.
        If met, awards rewards (gold, exp, items) and sets status to COMPLETED.
        Returns a list of completed quest objects for UI notification.
        """
        completed = []
        for quest in self.quests.values():
            if quest.status == QUEST_ACTIVE:
                # Synchronize item collection count first
                for obj in quest.objectives:
                    if obj.obj_type == "collect":
                        count = player.inventory.get_item_count(obj.target)
                        obj.set_progress(count)
                        
                if quest.check_objectives_completed():
                    # Deduct any collected quest materials from player inventory
                    for obj in quest.objectives:
                        if obj.obj_type == "collect":
                            player.inventory.remove_item(obj.target, obj.required_count)
                            
                    # Set state to completed
                    quest.status = QUEST_COMPLETED
                    completed.append(quest)
                    
                    # Grant Exp, Gold
                    player.gain_xp(quest.rewards.get("exp", 0))
                    player.gold += quest.rewards.get("gold", 0)
                    
                    # Grant Items
                    for item_name, qty in quest.rewards.get("items", []):
                        item = create_item(item_name, qty)
                        if item:
                            player.inventory.add_item(item)
                            
                    # Play quest complete jingle
                    player.sound_manager.play_sound("levelup")

                    # Emit construction completion flags for infrastructure quests
                    game = getattr(player, "game", None)
                    if game and hasattr(game, "world_state"):
                        if quest.id == "bridge_repair_quest":
                            game.world_state.completed_event_ids.add("bridge_rebuilt")
                        elif quest.id == "watchtower_quest":
                            game.world_state.completed_event_ids.add("watchtower_built")
                            # Also record in settlement upgrades for visual tier changes
                            if hasattr(game, "living_world") and hasattr(game.living_world, "settlement"):
                                game.living_world.settlement.upgrades["watchtower_built"] = True
                    
        return completed

    def get_active_quests(self) -> List[Quest]:
        """Returns list of quests that are currently active."""
        return [q for q in self.quests.values() if q.status == QUEST_ACTIVE]

    def get_completed_quests(self) -> List[Quest]:
        """Returns list of quests that are completed."""
        return [q for q in self.quests.values() if q.status == QUEST_COMPLETED]

    def set_tracked_quest(self, quest_id: str) -> None:
        """Pins a specific active quest to the HUD tracker."""
        if quest_id in self.quests and self.quests[quest_id].status == QUEST_ACTIVE:
            self.tracked_quest_id = quest_id

    def get_tracked_quest(self) -> Optional[Quest]:
        """Returns the manually pinned active quest, or defaults to the first active quest."""
        if self.tracked_quest_id and self.tracked_quest_id in self.quests:
            q = self.quests[self.tracked_quest_id]
            if q.status == QUEST_ACTIVE:
                return q
            else:
                self.tracked_quest_id = None
                
        active = self.get_active_quests()
        if active:
            main_q = next((q for q in active if q.id == "main_quest"), None)
            return main_q if main_q else active[0]
        return None
