"""
Echoes of Asterra - NPC System
Implements interactive non-player characters with dialog nodes, trading shop, and quest prompts.
"""
import pygame
from typing import Tuple, List
from rpg.sprite import BaseSprite
from rpg.constants import (
    DIR_DOWN,
    COLOR_WHITE, COLOR_YELLOW, COLOR_DARK_GRAY,
    QUEST_NOT_STARTED, QUEST_ACTIVE, QUEST_COMPLETED,
    STATE_DIALOGUE, STATE_SHOP
)
from rpg.dialogue import DialogueNode, DialogueChoice

class NPC(BaseSprite):
    """
    Base NPC class with interaction detection and dialogue initialization.
    """
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group], name: str, asset_key: str) -> None:
        super().__init__(pos, groups, layer=1)
        self.name = name
        self.asset_key = asset_key
        self.game = None  # bound during map spawn
        
        self.direction = DIR_DOWN
        self.state = "idle"
        self.hitbox = pygame.Rect(0, 0, 24, 20)
        self.hitbox.center = self.rect.center
        
        # Interact indicator
        self.interact_radius = 60.0
        self.show_indicator = False
        
        self.frame_index = 0.0

    def check_interaction_range(self, player_pos: pygame.math.Vector2) -> bool:
        """Determines if the player is within conversational speaking range."""
        dist = (player_pos - self.pos).length()
        self.show_indicator = (dist <= self.interact_radius)
        return self.show_indicator

    def interact(self) -> None:
        """Triggered when the player presses interact key while nearby. Overridden by child classes."""
        pass

    def on_interact_start(self, npc_short_id: str) -> bool:
        """Emits npc_talked event, checks friendship level. Returns False if NPC refuses interaction."""
        if not self.game:
            return True
            
        current_day = getattr(self.game.world_state, "day", 1) if hasattr(self.game, "world_state") else 1
        if hasattr(self.game, "event_bus"):
            self.game.event_bus.emit("npc_talked", npc_id=npc_short_id, current_day=current_day)
            
        if hasattr(self.game, "npc_memory"):
            mem = self.game.npc_memory.get_memory(npc_short_id)
            from rpg.constants import REL_ENEMY
            if mem.friendship_level == REL_ENEMY:
                node = DialogueNode(
                    f"{npc_short_id}_hostile",
                    self.name,
                    "Get away from me, villain! I will not speak with a criminal."
                )
                self.game.dialogue_manager.close()
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue(f"{npc_short_id}_hostile")
                self.game.game_state = STATE_DIALOGUE
                return False
        return True

    def update(self, dt: float) -> None:
        """Updates standing idle animation loops."""
        self.frame_index += 4.0 * dt
        from rpg.animation import entity_assets
        frames = entity_assets.get(self.asset_key, {}).get("idle", {}).get(self.direction)
        if frames:
            self.image = frames[int(self.frame_index) % len(frames)]

    def draw_indicator(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        """Renders a floating 'E' interaction button above the NPC's head."""
        if not self.show_indicator:
            return
            
        # Position indicator above sprite
        x = self.rect.centerx - camera_offset.x
        y = self.rect.top - 20 - camera_offset.y
        
        # Indicator box
        font = pygame.font.SysFont("Arial", 12, bold=True)
        lbl = font.render("[E]", True, COLOR_YELLOW)
        
        bg_rect = pygame.Rect(x - 10, y, 20, 16)
        pygame.draw.rect(surface, COLOR_DARK_GRAY, bg_rect, border_radius=3)
        pygame.draw.rect(surface, COLOR_WHITE, bg_rect, 1, border_radius=3)
        surface.blit(lbl, (x - lbl.get_width() // 2, y + 1))

# --- SPECIALIZED NPCs ---

class ElderEldrin(NPC):
    """Elder of Asterra. Guides the player along the Main Quest path."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Elder Eldrin", "mage")  # Reuse mage visual sheet

    def interact(self) -> None:
        """Checks Main Quest state to trigger corresponding dialogues."""
        if not self.on_interact_start("Eldrin"):
            return
        quest = self.game.quest_manager.quests["main_quest"]
        
        # Setup Elder conversation trees
        self.game.dialogue_manager.close()
        
        if quest.status == QUEST_NOT_STARTED:
            # 1. Available Main Quest Node
            def accept_callback():
                self.game.quest_manager.accept_quest("main_quest")
                # Advance quest step 1 immediately (spoke to Elder)
                self.game.quest_manager.handle_talk("Eldrin")
                
            n1 = DialogueNode(
                "eldrin_start",
                self.name,
                "Greetings, young traveler! A dark shadow is corrupting Asterra's core. Will you help save our land?",
                [
                    DialogueChoice("Yes, I will help!", "eldrin_accept", accept_callback),
                    DialogueChoice("Maybe later.", None)
                ]
            )
            n2 = DialogueNode(
                "eldrin_accept",
                self.name,
                "Wonderful! Go to the Forest to clean out the wolves. You must also mine Cavern Iron Ores, and defeat the Shadow Overlord in the deepest Dungeon."
            )
            self.game.dialogue_manager.add_node(n1)
            self.game.dialogue_manager.add_node(n2)
            self.game.dialogue_manager.start_dialogue("eldrin_start")
            
        elif quest.status == QUEST_ACTIVE:
            # Check objective 1 (talk to Elder) is updated
            self.game.quest_manager.handle_talk("Eldrin")
            
            # 2. Main Quest active, check status
            txt = "How goes the quest? Cleanse the wolves, gather 3 Iron Ores, and defeat the Shadow Overlord in the Dungeon."
            node = DialogueNode("eldrin_active", self.name, txt)
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("eldrin_active")
            
        elif quest.status == QUEST_COMPLETED:
            # 3. Quest completed
            txt = "You have saved Asterra! The light returns. You are a legendary champion."
            node = DialogueNode("eldrin_complete", self.name, txt)
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("eldrin_complete")
            
        self.game.game_state = STATE_DIALOGUE

class MerchantSilas(NPC):
    """Silas the merchant. Trades items (buying/selling consumables & weapons)."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Merchant Silas", "goblin")  # Reuse goblin model

    def interact(self) -> None:
        """Opens Shop UI trading inventory."""
        if not self.on_interact_start("Silas"):
            return
        self.game.dialogue_manager.close()
        
        def open_shop_callback():
            self.game.game_state = STATE_SHOP
            
        # Dialogue prompting to trade
        node = DialogueNode(
            "silas_start",
            self.name,
            "Welcome! Looking to trade? I carry fine supplies and will buy raw ores/apples.",
            [
                DialogueChoice("Let's trade.", None, open_shop_callback),
                DialogueChoice("Just looking around.", None)
            ]
        )
        self.game.dialogue_manager.add_node(node)
        self.game.dialogue_manager.start_dialogue("silas_start")
        self.game.game_state = STATE_DIALOGUE

class BlacksmithDennis(NPC):
    """Blacksmith Dennis. Crafts gear and issues side quest."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Blacksmith Dennis", "knight")

    def interact(self) -> None:
        """Prompt to open crafting menu or accept side quest."""
        self.game.dialogue_manager.close()
        qm = self.game.quest_manager
        side_quest = qm.quests["blacksmith_quest"]
        
        def open_crafting():
            from rpg.constants import STATE_PLAYING
            self.game.game_state = STATE_PLAYING
            self.game.ui_manager.toggle_panel("crafting")
            
        def accept_side():
            qm.accept_quest("blacksmith_quest")

        if side_quest.status == QUEST_NOT_STARTED:
            if qm.is_quest_available("blacksmith_quest"):
                node = DialogueNode(
                    "dennis_start",
                    self.name,
                    "Scholar Mira sent you? I can forge a sturdy shield for you, but I need 5 Iron Ores from the Caverns.",
                    [
                        DialogueChoice("Sure, I'll bring 5 Iron Ores.", "dennis_accepted", accept_side),
                        DialogueChoice("Just open the forge.", None, open_crafting)
                    ]
                )
                node_acc = DialogueNode("dennis_accepted", self.name, "Excellent! Bring 5 Iron Ores from the Caverns and I'll reward you.")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.add_node(node_acc)
                self.game.dialogue_manager.start_dialogue("dennis_start")
            else:
                node = DialogueNode(
                    "dennis_locked",
                    self.name,
                    "Complete Scholar Mira's quest 'Echoes of the Past' in the Ruins first so I can forge a shield for you!",
                    [
                        DialogueChoice("Open Crafting", None, open_crafting),
                        DialogueChoice("Goodbye.", None)
                    ]
                )
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("dennis_locked")
        else:
            hint = " Next: Visit Guardian Kai at the Lake." if side_quest.status == QUEST_COMPLETED else ""
            node = DialogueNode(
                "dennis_regular",
                self.name,
                f"Ready to work the anvil?{hint}",
                [
                    DialogueChoice("Open Crafting", None, open_crafting),
                    DialogueChoice("Not right now.", None)
                ]
            )
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("dennis_regular")
            
        self.game.game_state = STATE_DIALOGUE

class RangerFaye(NPC):
    """Ranger Faye in the Forest. Gives Forest Patrol quest."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Ranger Faye", "wolf")

    def interact(self) -> None:
        self.game.dialogue_manager.close()
        qm = self.game.quest_manager
        quest = qm.quests["forest_patrol"]

        def accept():
            qm.accept_quest("forest_patrol")

        if quest.status == QUEST_NOT_STARTED:
            if qm.is_quest_available("forest_patrol"):
                node = DialogueNode(
                    "faye_start",
                    self.name,
                    "Traveler! The forest trails are overrun by slimes and aggressive wolves. Will you help clear them?",
                    [
                        DialogueChoice("I'll clear the forest! (5 Slimes, 2 Wolves)", "faye_acc", accept),
                        DialogueChoice("Not right now.", None)
                    ]
                )
                node_acc = DialogueNode("faye_acc", self.name, "Thank you! Slay 5 Slimes and 2 Wolves. Be careful out there.")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.add_node(node_acc)
                self.game.dialogue_manager.start_dialogue("faye_start")
            else:
                node = DialogueNode("faye_locked", self.name, "Speak to Elder Eldrin in the Village first to begin 'The Core of Asterra' before taking on forest duties!")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("faye_locked")
        elif quest.status == QUEST_ACTIVE:
            node = DialogueNode("faye_active", self.name, "Keep clearing the paths! Slay 5 Slimes and 2 Wolves in the Forest.")
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("faye_active")
        else:
            node = DialogueNode("faye_done", self.name, "Great job clearing the forest! The Ruins to the east hold ancient secrets. Seek Scholar Mira in the Ruins.")
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("faye_done")

        self.game.game_state = STATE_DIALOGUE

class ScholarMira(NPC):
    """Scholar Mira in the Ruins. Gives Echoes of the Past quest."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Scholar Mira", "mage")

    def interact(self) -> None:
        if not self.on_interact_start("Mira"):
            return
        self.game.dialogue_manager.close()
        qm = self.game.quest_manager
        quest = qm.quests["scholar_quest"]

        def accept():
            qm.accept_quest("scholar_quest")

        if quest.status == QUEST_NOT_STARTED:
            if qm.is_quest_available("scholar_quest"):
                node = DialogueNode(
                    "mira_start",
                    self.name,
                    "Welcome, brave traveler. Deep in these ruined halls lies a chest with an Ancient Scroll detailing the Shadow Overlord's origin. Will you retrieve it?",
                    [
                        DialogueChoice("I will find the scroll.", "mira_acc", accept),
                        DialogueChoice("Maybe later.", None)
                    ]
                )
                node_acc = DialogueNode("mira_acc", self.name, "Search the chests in the Ruins for the Ancient Scroll!")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.add_node(node_acc)
                self.game.dialogue_manager.start_dialogue("mira_start")
            else:
                node = DialogueNode("mira_locked", self.name, "Complete Ranger Faye's quest 'Forest Patrol' in the Forest first before exploring these Ruins!")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("mira_locked")
        elif quest.status == QUEST_ACTIVE:
            node = DialogueNode("mira_active", self.name, "Look for the chest inside these ruined halls to retrieve the Ancient Scroll.")
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("mira_active")
        else:
            node = DialogueNode("mira_done", self.name, "The scroll reveals the Shadow Overlord is in the Dungeon! You'll need sturdy iron gear. Speak to Blacksmith Dennis in the Village.")
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("mira_done")

        self.game.game_state = STATE_DIALOGUE

class MinerGarth(NPC):
    """Miner Garth in the Caverns. Provides mining guidance."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Miner Garth", "skeleton")

    def interact(self) -> None:
        if not self.on_interact_start("Garth"):
            return
        self.game.dialogue_manager.close()
        node = DialogueNode("garth_talk", self.name, "Greetings! These caverns are rich with Iron Ores inside resource chests. Bring 5 Iron Ores to Blacksmith Dennis in the Village to forge armor!")
        self.game.dialogue_manager.add_node(node)
        self.game.dialogue_manager.start_dialogue("garth_talk")
        self.game.game_state = STATE_DIALOGUE

class GuardianKai(NPC):
    """Guardian Kai at the Lake. Gives Lake Vigil quest."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Guardian Kai", "knight")

    def interact(self) -> None:
        if not self.on_interact_start("Kai"):
            return
        self.game.dialogue_manager.close()
        qm = self.game.quest_manager
        quest = qm.quests["lake_quest"]

        def accept():
            qm.accept_quest("lake_quest")

        if quest.status == QUEST_NOT_STARTED:
            if qm.is_quest_available("lake_quest"):
                node = DialogueNode(
                    "kai_start",
                    self.name,
                    "Frost Slimes are corrupting our lake shores! Help me drive back 4 Frost Slimes.",
                    [
                        DialogueChoice("I'll defeat 4 Frost Slimes.", "kai_acc", accept),
                        DialogueChoice("Not now.", None)
                    ]
                )
                node_acc = DialogueNode("kai_acc", self.name, "Thank you! Hunt down 4 Frost Slimes around the lake.")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.add_node(node_acc)
                self.game.dialogue_manager.start_dialogue("kai_start")
            else:
                node = DialogueNode("kai_locked", self.name, "Complete Blacksmith Dennis's quest 'Iron Forging' in the Village first so you are equipped with a sturdy shield!")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("kai_locked")
        elif quest.status == QUEST_ACTIVE:
            node = DialogueNode("kai_active", self.name, "Drive back 4 Frost Slimes along the shores of this lake.")
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("kai_active")
        else:
            node = DialogueNode("kai_done", self.name, "Thank you warrior! North of here lies a hidden grove (Secret Area). Visit the sacred altar there, then head to the Dungeon to face the Shadow Overlord!")
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("kai_done")

        self.game.game_state = STATE_DIALOGUE

class SpiritOfAsterra(NPC):
    """Spirit of Asterra in the Secret Area. Gives final lore."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Spirit of Asterra", "boss")

    def interact(self) -> None:
        if not self.on_interact_start("Spirit"):
            return
        self.game.dialogue_manager.close()
        node = DialogueNode("spirit_talk", self.name, "Brave champion, you stand in the sacred grove. Claim the legendary Asterra Sword from the chest nearby, then venture into the Dungeon to defeat the Shadow Overlord!")
        self.game.dialogue_manager.add_node(node)
        self.game.dialogue_manager.start_dialogue("spirit_talk")
        self.game.game_state = STATE_DIALOGUE

