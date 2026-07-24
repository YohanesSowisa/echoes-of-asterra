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
        player = self.game.player
        
        def fund_silas():
            if player.gold >= 100:
                player.gold -= 100
                if hasattr(self.game, "living_world"):
                    self.game.living_world.settlement._on_prosperity_changed(prosperity=90.0)
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "Royal Market Unlocked! -20% Shop Discount!", (255, 215, 0), [self.game.ui_sprites], size=18)
                self.game.dialogue_manager.start_dialogue("eldrin_silas")

        def fund_watchtower():
            if player.gold >= 50:
                player.gold -= 50
                if hasattr(self.game, "living_world"):
                    self.game.living_world.event_bus.emit("road_safety_increased", amount=50.0)
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "Watchtower Erected! Raid Shield Active!", (100, 255, 100), [self.game.ui_sprites], size=18)
                self.game.dialogue_manager.start_dialogue("eldrin_watchtower")

        def fund_dennis():
            if player.gold >= 50:
                player.gold -= 50
                if hasattr(self.game, "living_world"):
                    self.game.living_world.settlement._on_prosperity_changed(prosperity=75.0)
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "Master Forge Unlocked! Tier 2 Weapons!", (255, 180, 60), [self.game.ui_sprites], size=18)
                self.game.dialogue_manager.start_dialogue("eldrin_dennis")

        node_s = DialogueNode("eldrin_silas", self.name, "Wonderful investment! Silas has expanded the Royal Market. All shop prices in Asterra receive a 20% discount!", [DialogueChoice("Great news.", None)])
        node_w = DialogueNode("eldrin_watchtower", self.name, "The Village Watchtower is built! Watchmen now scout for monster raids and highway safety is fortified.", [DialogueChoice("Asterra is safe.", None)])
        node_d = DialogueNode("eldrin_dennis", self.name, "Dennis has upgraded his forge to a Master Anvil! You can now forge Tier 2 weapons and armor.", [DialogueChoice("To the forge!", None)])
        
        self.game.dialogue_manager.add_node(node_s)
        self.game.dialogue_manager.add_node(node_w)
        self.game.dialogue_manager.add_node(node_d)

        investment_choices = []
        if player.gold >= 100:
            investment_choices.append(DialogueChoice("[INVEST: SILAS] Fund Royal Market (100g -> -20% Shop Prices)", None, fund_silas))
        if player.gold >= 50:
            investment_choices.append(DialogueChoice("[INVEST: ELDRIN] Fund Watchtower (50g -> Raid Shield & Road Safety)", None, fund_watchtower))
            investment_choices.append(DialogueChoice("[INVEST: DENNIS] Fund Master Forge (50g -> Tier 2 Gear)", None, fund_dennis))

        if quest.status == QUEST_NOT_STARTED:
            # 1. Available Main Quest Node
            def accept_callback():
                self.game.quest_manager.accept_quest("main_quest")
                self.game.quest_manager.handle_talk("Eldrin")
                
            n1 = DialogueNode(
                "eldrin_start",
                self.name,
                "Greetings, traveler! Review the Town Board or assist us in clearing the shadow corrupting Asterra.",
                investment_choices + [
                    DialogueChoice("Yes, I will help!", "eldrin_accept", accept_callback),
                    DialogueChoice("Maybe later.", None)
                ]
            )
            n2 = DialogueNode(
                "eldrin_accept",
                self.name,
                "Wonderful! Go to the Forest to clean out the wolves, mine Cavern Iron Ores, and defeat the Shadow Overlord."
            )
            self.game.dialogue_manager.add_node(n1)
            self.game.dialogue_manager.add_node(n2)
            self.game.dialogue_manager.start_dialogue("eldrin_start")
            
        elif quest.status == QUEST_ACTIVE:
            self.game.quest_manager.handle_talk("Eldrin")
            txt = "How goes the quest? Cleanse the wolves, gather 3 Iron Ores, and defeat the Shadow Overlord."
            node = DialogueNode("eldrin_active", self.name, txt, investment_choices + [DialogueChoice("Continue quest.", None)])
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("eldrin_active")
            
        elif quest.status == QUEST_COMPLETED:
            txt = "You have saved Asterra! The light returns. You are a legendary champion."
            node = DialogueNode("eldrin_complete", self.name, txt, investment_choices + [DialogueChoice("Thank you.", None)])
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
        player = self.game.player
        
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
        player = self.game.player
        qm = self.game.quest_manager
        side_quest = qm.quests["blacksmith_quest"]
        
        def open_crafting():
            from rpg.constants import STATE_PLAYING
            self.game.game_state = STATE_PLAYING
            self.game.ui_manager.toggle_panel("crafting")
            
        def accept_side():
            qm.accept_quest("blacksmith_quest")

        def donate_ore_for_guards():
            if player.inventory.remove_item("Iron Ore", 5):
                if hasattr(self.game, "living_world"):
                    self.game.living_world.event_bus.emit("road_safety_increased", amount=35.0)
                    self.game.living_world.event_bus.emit("caravan_arrived", caravan_type="military", cargo_type="supplies", target_map="village")
                    self.game.living_world.settlement._on_prosperity_changed(prosperity=70.0)
                if hasattr(self.game, "factions"):
                    self.game.factions.modify_reputation("knights", 15)
                
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "+35 Guard Defense! Market Tax -15%!", (255, 215, 0), [self.game.ui_sprites], size=20)
                self.game.dialogue_manager.start_dialogue("dennis_donated")

        def sell_ore_for_gold():
            if player.inventory.remove_item("Iron Ore", 5):
                player.gold += 50
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "+50 Gold Gained!", (255, 255, 0), [self.game.ui_sprites], size=20)
                self.game.dialogue_manager.start_dialogue("dennis_sold_gold")

        # Response nodes
        node_donated = DialogueNode(
            "dennis_donated",
            self.name,
            "Outstanding decision, Hero! I've forged 5 Iron Shields for the Village Guards. Highway patrols are reinforced, road danger has dropped, and Silas's shop prices are down by 15%!",
            [DialogueChoice("Glad to protect Asterra.", None)]
        )
        node_sold = DialogueNode(
            "dennis_sold_gold",
            self.name,
            "50 Gold added to your pouch! Personal gold lets you buy spells right now. Remember: if guards remain under-equipped, highway danger will rise!",
            [DialogueChoice("I need personal power first.", None)]
        )
        self.game.dialogue_manager.add_node(node_donated)
        self.game.dialogue_manager.add_node(node_sold)

        # Build choices list based on player's Iron Ore inventory
        choices = []
        if player.inventory.has_item("Iron Ore", 5):
            choices.append(DialogueChoice("[TOWN SECURITY] Donate 5 Ore -> Forge Guard Shields (-15% Market Tax)", None, donate_ore_for_guards))
            choices.append(DialogueChoice("[PERSONAL POWER] Sell 5 Ore for 50 Gold (Buy Spells)", None, sell_ore_for_gold))
        
        choices.append(DialogueChoice("Open Forge Crafting", None, open_crafting))
        choices.append(DialogueChoice("Goodbye.", None))

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
                node = DialogueNode("dennis_locked", self.name, "Complete Scholar Mira's quest in Ruins first!", choices)
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("dennis_locked")
        else:
            hint = " Next: Visit Guardian Kai at Lake." if side_quest.status == QUEST_COMPLETED else ""
            node = DialogueNode("dennis_regular", self.name, f"Ready to work the anvil?{hint}", choices)
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

        def empower_knights():
            if hasattr(self.game, "factions"):
                self.game.factions.modify_reputation("knights", 20)
                self.game.factions.modify_reputation("hunters", -10)
            if hasattr(self.game, "living_world"):
                self.game.living_world.event_bus.emit("territory_control_changed", control_point="Forest Crossroads", map_name="forest", old_owner="hunters", new_owner="knights")
                self.game.living_world.event_bus.emit("road_safety_increased", amount=20.0)
            from rpg.combat import DamageNumber
            DamageNumber(self.rect.center, "+20 Knights Rep! Highway Safe (-10% Shop Tax)", (100, 200, 255), [self.game.ui_sprites], size=18)
            self.game.dialogue_manager.start_dialogue("faye_knights")

        def empower_hunters():
            if hasattr(self.game, "factions"):
                self.game.factions.modify_reputation("hunters", 20)
                self.game.factions.modify_reputation("knights", -10)
            if hasattr(self.game, "living_world"):
                self.game.living_world.event_bus.emit("territory_control_changed", control_point="Forest Crossroads", map_name="forest", old_owner="knights", new_owner="hunters")
            from rpg.combat import DamageNumber
            DamageNumber(self.rect.center, "+20 Hunters Rep! Beast Drops x2!", (255, 180, 60), [self.game.ui_sprites], size=18)
            self.game.dialogue_manager.start_dialogue("faye_hunters")

        node_k = DialogueNode("faye_knights", self.name, "Understood! I'll report to Knight Captains. Highway patrols are reinforced, shop taxes dropped 10%, though wild beasts are driven deeper into hiding.", [DialogueChoice("Understood.", None)])
        node_h = DialogueNode("faye_hunters", self.name, "Excellent choice! The Hunters Guild will preserve the forest habitats. Beast Leather and Meat drops are doubled, though highway danger will rise!", [DialogueChoice("Let nature thrive.", None)])
        self.game.dialogue_manager.add_node(node_k)
        self.game.dialogue_manager.add_node(node_h)

        faction_choices = [
            DialogueChoice("[FACTION: KNIGHTS] Empower Knight Patrols (-10% Shop Tax, Safe Trade)", None, empower_knights),
            DialogueChoice("[FACTION: HUNTERS] Empower Hunters Preserve (Beast Drops x2, Wild Habitat)", None, empower_hunters),
        ]

        if quest.status == QUEST_NOT_STARTED:
            if qm.is_quest_available("forest_patrol"):
                node = DialogueNode(
                    "faye_start",
                    self.name,
                    "Traveler! The forest trails are contested between Knight Patrols and Hunter Preserves. How shall we manage the region?",
                    faction_choices + [DialogueChoice("I'll clear the forest! (5 Slimes, 2 Wolves)", "faye_acc", accept)]
                )
                node_acc = DialogueNode("faye_acc", self.name, "Thank you! Slay 5 Slimes and 2 Wolves. Be careful out there.")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.add_node(node_acc)
                self.game.dialogue_manager.start_dialogue("faye_start")
            else:
                node = DialogueNode("faye_locked", self.name, "Speak to Elder Eldrin in the Village first!", faction_choices)
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("faye_locked")
        elif quest.status == QUEST_ACTIVE:
            node = DialogueNode("faye_active", self.name, "Keep clearing the paths! Slay 5 Slimes and 2 Wolves.", faction_choices)
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("faye_active")
        else:
            node = DialogueNode("faye_done", self.name, "Great job in the forest! Seek Scholar Mira in the Ruins to the east.", faction_choices)
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

class GreedAltar(NPC):
    """Ancient Greed Altar in Dungeon exit rooms. Offers Extraction vs Greed Curse."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Greed Altar", "greed_altar")
        self.image = pygame.Surface((36, 48), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (120, 20, 40), (4, 8, 28, 36), border_radius=4)
        pygame.draw.rect(self.image, (255, 60, 60), (6, 10, 24, 32), 2, border_radius=3)
        pygame.draw.circle(self.image, (255, 200, 60), (18, 20), 6)

    def interact(self) -> None:
        self.game.dialogue_manager.close()
        player = self.game.player
        
        def extract_to_village():
            from rpg.constants import MAP_VILLAGE
            self.game.world_manager.load_map(MAP_VILLAGE, player)
            
        def challenge_greed():
            player.greed_curse_active = True
            from rpg.combat import DamageNumber
            DamageNumber(self.rect.center, "GREED CURSE ACTIVATED! ATK +50%, Loot x2!", (255, 60, 60), [self.game.ui_sprites], size=20)
            self.game.dialogue_manager.start_dialogue("greed_curse_started")

        node_c = DialogueNode("greed_curse_started", self.name, "The Ancient Altar flares with blood-red energy! Monsters in this crypt now deal +50% Damage, but all Chest Loot & Boss Rewards are DOUBLED!", [DialogueChoice("I accept the challenge!", None)])
        self.game.dialogue_manager.add_node(node_c)

        node = DialogueNode(
            "greed_altar_start",
            self.name,
            "An Ancient Extraction Altar hums with dark magic. Extract safely back to town, or challenge the Greed Curse?",
            [
                DialogueChoice("[EXTRACTION PORTAL] Return Safely to Village (Lock in Loot)", None, extract_to_village),
                DialogueChoice("[GREED ALTAR] Challenge Greed Curse (Enemies ATK +50%, Loot x2)", None, challenge_greed),
                DialogueChoice("Leave Altar.", None)
            ]
        )
        self.game.dialogue_manager.add_node(node)
        self.game.dialogue_manager.start_dialogue("greed_altar_start")
        self.game.game_state = STATE_DIALOGUE

class TownNoticeboard(NPC):
    """Town Investment Board in Village Plaza."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Town Investment Board", "noticeboard")
        self.image = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (100, 70, 40), (0, 0, 44, 44), border_radius=4)
        pygame.draw.rect(self.image, (210, 170, 60), (2, 2, 40, 40), 2, border_radius=3)
        lbl = pygame.font.SysFont("Arial", 10, bold=True).render("NOTICE", True, (255, 240, 200))
        self.image.blit(lbl, (4, 14))

    def interact(self) -> None:
        self.game.dialogue_manager.close()
        player = self.game.player
        
        def fund_silas():
            if player.gold >= 100:
                player.gold -= 100
                if hasattr(self.game, "living_world"):
                    self.game.living_world.settlement._on_prosperity_changed(prosperity=90.0)
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "Royal Market Unlocked! -20% Shop Discount!", (255, 215, 0), [self.game.ui_sprites], size=18)

        def fund_watchtower():
            if player.gold >= 50:
                player.gold -= 50
                if hasattr(self.game, "living_world"):
                    self.game.living_world.event_bus.emit("road_safety_increased", amount=50.0)
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "Watchtower Erected! Raid Shield Active!", (100, 255, 100), [self.game.ui_sprites], size=18)

        def fund_dennis():
            if player.gold >= 50:
                player.gold -= 50
                if hasattr(self.game, "living_world"):
                    self.game.living_world.settlement._on_prosperity_changed(prosperity=75.0)
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "Master Forge Unlocked! Tier 2 Weapons!", (255, 180, 60), [self.game.ui_sprites], size=18)

        choices = []
        if player.gold >= 100:
            choices.append(DialogueChoice("[INVEST: SILAS] Fund Royal Market (100g -> -20% Shop Prices)", None, fund_silas))
        if player.gold >= 50:
            choices.append(DialogueChoice("[INVEST: ELDRIN] Fund Watchtower (50g -> Raid Shield & Road Safety)", None, fund_watchtower))
            choices.append(DialogueChoice("[INVEST: DENNIS] Fund Master Forge (50g -> Tier 2 Gear)", None, fund_dennis))
        choices.append(DialogueChoice("Close Town Board.", None))

        node = DialogueNode("town_board", self.name, "Asterra Town Board: Allocate your gold and resources to fund competing NPC ambitions and town infrastructure!", choices)
        self.game.dialogue_manager.add_node(node)
        self.game.dialogue_manager.start_dialogue("town_board")
        self.game.game_state = STATE_DIALOGUE

