"""
Echoes of Asterra - NPC System
Implements interactive non-player characters with dialog nodes, trading shop, and quest prompts.
"""
import pygame
import math
import random
from typing import Tuple, List, Dict, Any, Optional
from rpg.sprite import BaseSprite
from rpg.settings import TILE_SIZE
from rpg.constants import (
    DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT,
    COLOR_WHITE, COLOR_YELLOW, COLOR_DARK_GRAY,
    QUEST_NOT_STARTED, QUEST_ACTIVE, QUEST_COMPLETED,
    STATE_DIALOGUE, STATE_SHOP, STATE_PAUSED
)
from rpg.dialogue import DialogueNode, DialogueChoice

class NPC(BaseSprite):
    """
    Base NPC class with interaction detection, dialogue initialization, and autonomous wandering AI.
    """
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group], name: str, asset_key: str, can_wander: bool = True) -> None:
        super().__init__(pos, groups, layer=1)
        self.name = name
        self.asset_key = asset_key
        self.game = None  # bound during map spawn
        self.can_wander = can_wander
        
        self.direction = DIR_DOWN
        self.state = "idle"
        self.hitbox = pygame.Rect(0, 0, 24, 20)
        self.hitbox.center = self.rect.center
        
        # Wandering AI parameters
        self.spawn_pos = pygame.math.Vector2(pos)
        self.wander_radius = 80.0
        self.move_speed = 45.0
        self.target_pos: Optional[pygame.math.Vector2] = None
        self.wander_timer = random.uniform(1.0, 3.5)
        
        # Interact indicator
        self.interact_radius = 60.0
        self.show_indicator = False
        
        self.frame_index = 0.0

    def check_interaction_range(self, player_pos: pygame.math.Vector2) -> bool:
        """Determines if the player is within conversational speaking range and turns NPC to face player."""
        dist = (player_pos - self.pos).length()
        self.show_indicator = (dist <= self.interact_radius)
        if self.show_indicator:
            # Turn to face player when nearby
            diff = player_pos - self.pos
            if abs(diff.x) > abs(diff.y):
                self.direction = DIR_RIGHT if diff.x > 0 else DIR_LEFT
            else:
                self.direction = DIR_DOWN if diff.y > 0 else DIR_UP
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

    def inject_rumor_choice(self, node: DialogueNode, npc_short_id: str) -> None:
        """Injects 'Heard any rumors?' choice into a dialogue node."""
        if not self.game or not hasattr(self.game, "living_world") or not hasattr(self.game.living_world, "rumors"):
            return

        if any("rumor" in c.text.lower() for c in node.choices):
            return

        def rumor_callback():
            rumor_info = self.game.living_world.rumors.get_npc_rumor(npc_short_id.lower())
            dm = self.game.dialogue_manager
            if rumor_info:
                topic, content, distortion = rumor_info
                prefix = "⚡ [DISTORTED RUMOR] " if distortion >= 0.4 else "🗣️ [TOWN RUMOR] "
                r_node = DialogueNode(
                    f"{npc_short_id}_rumor_response",
                    self.name,
                    f"{prefix}Regarding {topic}: \"{content}\"",
                    [DialogueChoice("Interesting...", None)]
                )
                dm.add_node(r_node)
                dm.set_node(f"{npc_short_id}_rumor_response")
            else:
                r_node = DialogueNode(
                    f"{npc_short_id}_rumor_response",
                    self.name,
                    "Quiet days in Asterra... I haven't heard any new rumors today.",
                    [DialogueChoice("Fair enough.", None)]
                )
                dm.add_node(r_node)
                dm.set_node(f"{npc_short_id}_rumor_response")

        rumor_choice = DialogueChoice("🗣️ Heard any rumors?", None, rumor_callback)
        if node.choices:
            node.choices.insert(max(0, len(node.choices) - 1), rumor_choice)
        else:
            node.choices.append(rumor_choice)

    def update(self, dt: float) -> None:
        """Updates standing idle/walking animation loops and autonomous wandering movement."""
        # Pause wandering during active dialogue or when player is in interaction range
        is_dialogue = (self.game and getattr(self.game, "game_state", None) == STATE_DIALOGUE)
        if is_dialogue or self.show_indicator:
            self.state = "idle"
            self.target_pos = None

        if self.can_wander and not is_dialogue and not self.show_indicator:
            self._update_wander(dt)

        self.frame_index += (6.0 if self.state == "walk" else 3.0) * dt
        from rpg.animation import entity_assets
        frames = entity_assets.get(self.asset_key, {}).get(self.state, {}).get(self.direction)
        if not frames:
            frames = entity_assets.get(self.asset_key, {}).get("idle", {}).get(self.direction)
        if frames:
            self.image = frames[int(self.frame_index) % len(frames)]

    def _update_wander(self, dt: float) -> None:
        """Handles autonomous random wandering around spawn position."""
        self.wander_timer -= dt
        if self.wander_timer <= 0:
            self.wander_timer = random.uniform(2.0, 5.0)
            if self.state == "idle" and random.random() < 0.65:
                # Pick a random target within wander_radius
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(24.0, self.wander_radius)
                target = self.spawn_pos + pygame.math.Vector2(math.cos(angle) * dist, math.sin(angle) * dist)
                
                if self._is_position_walkable(target):
                    self.target_pos = target
                    self.state = "walk"
            else:
                self.state = "idle"
                self.target_pos = None

        if self.state == "walk" and self.target_pos:
            move_vec = self.target_pos - self.pos
            dist = move_vec.length()
            if dist < 4.0:
                self.pos = pygame.math.Vector2(self.target_pos)
                self.rect.center = (int(self.pos.x), int(self.pos.y))
                self.hitbox.center = self.rect.center
                self.state = "idle"
                self.target_pos = None
            else:
                move_dir = move_vec.normalize()
                if abs(move_dir.x) > abs(move_dir.y):
                    self.direction = DIR_RIGHT if move_dir.x > 0 else DIR_LEFT
                else:
                    self.direction = DIR_DOWN if move_dir.y > 0 else DIR_UP

                new_pos = self.pos + move_dir * self.move_speed * dt
                if self._is_position_walkable(new_pos):
                    self.pos = new_pos
                    self.rect.center = (int(self.pos.x), int(self.pos.y))
                    self.hitbox.center = self.rect.center
                else:
                    self.state = "idle"
                    self.target_pos = None

    def _is_position_walkable(self, pos: pygame.math.Vector2) -> bool:
        """Checks if a target position is within map bounds and not colliding with obstacles."""
        if not self.game or not hasattr(self.game, "world_manager"):
            return True
        wm = self.game.world_manager
        current_map = wm.current_map_data
        if not current_map:
            return True

        w = current_map.get("width", 40)
        h = current_map.get("height", 30)
        grid_x = int(pos.x // TILE_SIZE)
        grid_y = int(pos.y // TILE_SIZE)

        if grid_x < 1 or grid_x >= w - 1 or grid_y < 1 or grid_y >= h - 1:
            return False

        grid = current_map.get("grid")
        if grid and grid[grid_y][grid_x] in ["wall", "water", "tree"]:
            return False

        return True

    def draw_indicator(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        """Renders floating quest marker [!] or interaction prompt [E] above NPC head."""
        # Suppress indicator prompts while UI overlays or open panels (crafting/inv/etc) are active
        if self.game:
            if getattr(self.game, "game_state", None) in [STATE_SHOP, STATE_DIALOGUE, STATE_PAUSED]:
                return
            if hasattr(self.game, "ui_manager") and self.game.ui_manager.open_panels:
                return
            if hasattr(self.game, "dialogue_manager") and getattr(self.game.dialogue_manager, "current_node", None) is not None:
                return

        x = self.rect.centerx - camera_offset.x
        y = self.rect.top - 20 - camera_offset.y

        # Floating quest available marker for Elder or primary quest givers
        is_elder = (getattr(self, "npc_id", "") == "elder" or "eldrin" in getattr(self, "name", "").lower())
        if is_elder and not self.show_indicator:
            # Pulsing gold ! badge above head
            bob_offset = int(math.sin(pygame.time.get_ticks() / 180.0) * 3)
            bg_rect = pygame.Rect(x - 10, y + bob_offset, 20, 20)
            pygame.draw.rect(surface, (255, 200, 0), bg_rect, border_radius=10)
            pygame.draw.rect(surface, (40, 30, 0), bg_rect, 1, border_radius=10)
            try:
                font = pygame.font.Font("assets/fonts/game_font.ttf", 14)
            except Exception as e:
                import logging
                logging.getLogger("NPC").warning("TTF font load failed, using SysFont fallback: %s", e)
                font = pygame.font.SysFont("Arial", 14, bold=True)
            lbl = font.render("!", True, (20, 20, 20))
            surface.blit(lbl, (x - lbl.get_width() // 2, y + bob_offset + 1))
            return

        if not self.show_indicator:
            return
            
        # Interaction prompt [F]
        try:
            font = pygame.font.Font("assets/fonts/game_font.ttf", 12)
        except Exception as e:
            import logging
            logging.getLogger("NPC").warning("TTF font load failed, using SysFont fallback: %s", e)
            font = pygame.font.SysFont("Arial", 12, bold=True)
        lbl = font.render("[F]", True, COLOR_YELLOW)
        
        bg_rect = pygame.Rect(x - 10, y, 20, 16)
        pygame.draw.rect(surface, COLOR_DARK_GRAY, bg_rect, border_radius=3)
        pygame.draw.rect(surface, COLOR_WHITE, bg_rect, 1, border_radius=3)
        surface.blit(lbl, (x - lbl.get_width() // 2, y + 1))

    def get_companion_dialogue_choices(self, companion_id: str) -> List[DialogueChoice]:
        """Returns companion recruitment, party management, tactics, and expedition dialogue choices."""
        choices: List[DialogueChoice] = []
        if not hasattr(self.game, "companion_manager") or not self.game.companion_manager:
            return choices

        cm = self.game.companion_manager
        comp = cm.companions.get(companion_id)
        if not comp:
            return choices

        # 1. Recruitment Choice (if not yet recruited)
        if not comp.is_recruited:
            def do_recruit():
                cm.recruit_companion(companion_id)
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, f"🤝 {comp.name} Recruited!", (100, 255, 140), [self.game.ui_sprites], size=18)
                self.game.dialogue_manager.close()
                self.interact()

            choices.append(DialogueChoice(f"🤝 [RECRUIT] \"Join my roster, {comp.name}!\"", None, do_recruit))
            return choices

        # 2. Party Management
        if comp.is_in_party:
            def do_dismiss():
                cm.set_active_party_companion(None)
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, f"🏠 {comp.name} resting at camp", (200, 200, 200), [self.game.ui_sprites], size=16)
                self.game.dialogue_manager.close()
                self.interact()

            def set_mode_atk():
                comp.assign_mode("attack")
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "⚔️ Tactics: Focus Attack!", (255, 120, 100), [self.game.ui_sprites], size=16)

            def set_mode_tank():
                comp.assign_mode("tank")
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "🛡️ Tactics: Protect & Tank!", (100, 180, 255), [self.game.ui_sprites], size=16)

            def set_mode_heal():
                comp.assign_mode("heal")
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "✨ Tactics: Support & Heal!", (100, 255, 140), [self.game.ui_sprites], size=16)

            choices.append(DialogueChoice(f"🏠 [PARTY] \"Rest at the village for now, {comp.name}.\"", None, do_dismiss))
            choices.append(DialogueChoice(f"⚔️ [TACTICS] Set Mode: Attack (Current: {comp.mode.upper()})", None, set_mode_atk))
            choices.append(DialogueChoice(f"🛡️ [TACTICS] Set Mode: Tank (Current: {comp.mode.upper()})", None, set_mode_tank))
            choices.append(DialogueChoice(f"✨ [TACTICS] Set Mode: Heal (Current: {comp.mode.upper()})", None, set_mode_heal))
        else:
            if not comp.expedition or comp.expedition.is_completed:
                def do_join():
                    cm.set_active_party_companion(companion_id)
                    from rpg.combat import DamageNumber
                    DamageNumber(self.rect.center, f"⚔️ {comp.name} joined party!", (100, 255, 140), [self.game.ui_sprites], size=18)
                    self.game.dialogue_manager.close()
                    self.interact()

                def do_exp_forest():
                    cm.dispatch_expedition(companion_id, "forest", 1)
                    from rpg.combat import DamageNumber
                    DamageNumber(self.rect.center, f"🗺️ {comp.name} dispatched to Forest!", (255, 215, 0), [self.game.ui_sprites], size=16)
                    self.game.dialogue_manager.close()

                def do_exp_cave():
                    cm.dispatch_expedition(companion_id, "cave", 2)
                    from rpg.combat import DamageNumber
                    DamageNumber(self.rect.center, f"🗺️ {comp.name} dispatched to Cave (2 days)!", (255, 215, 0), [self.game.ui_sprites], size=16)
                    self.game.dialogue_manager.close()

                choices.append(DialogueChoice(f"⚔️ [PARTY] \"Join my party for adventure, {comp.name}!\"", None, do_join))
                choices.append(DialogueChoice(f"🗺️ [EXPEDITION] Send on Forest Scout Expedition (1 Day)", None, do_exp_forest))
                choices.append(DialogueChoice(f"🗺️ [EXPEDITION] Send on Cave Mining Expedition (2 Days)", None, do_exp_cave))
            else:
                choices.append(DialogueChoice(f"🗺️ [EXPEDITION] Away on {comp.expedition.zone.title()} expedition ({comp.expedition.days_remaining}d left)", None))

            if comp.expedition and comp.expedition.is_completed:
                def do_claim():
                    res = cm.claim_expedition_rewards(companion_id, self.game.player)
                    if res:
                        gold, items = res
                        from rpg.combat import DamageNumber
                        DamageNumber(self.rect.center, f"🎁 Claimed {gold}g & {len(items)} items!", (255, 215, 0), [self.game.ui_sprites], size=18)
                    self.game.dialogue_manager.close()
                    self.interact()

                choices.append(DialogueChoice(f"🎁 [EXPEDITION] Claim Expedition Spoils ({comp.expedition.rewards_gold}g + items)!", None, do_claim))

        return choices


# --- SPECIALIZED NPCs ---

def create_settlement_specialization_dialogue(game: Any, return_node_id: str = "eldrin_start") -> DialogueNode:
    """Builds interactive specialization selection dialogue tree."""
    dm = game.dialogue_manager
    player = game.player
    settlement = getattr(game.living_world, "settlement", None) if hasattr(game, "living_world") else None
    factions = getattr(game, "factions", None)

    from rpg.settlement import SPECIALIZATION_MILITARY, SPECIALIZATION_TRADE, SPECIALIZATION_ARCANE

    def choose_spec(spec_id: str):
        if settlement:
            success, msg = settlement.set_specialization(spec_id, player, factions)
            from rpg.combat import DamageNumber
            col = (100, 255, 100) if success else (255, 100, 100)
            DamageNumber(player.rect.center, msg, col, [game.ui_sprites], size=18)
            # Re-spawn map decorations if in Village
            if game.world_manager and game.world_manager.current_map_name == "village":
                game.world_manager.load_map("village", player, portal_spawn=False)
            res_node = DialogueNode(
                "settlement_spec_result",
                "Town Specialization Proclaimed",
                msg,
                [DialogueChoice("Understood.", return_node_id)]
            )
            dm.add_node(res_node)
            dm.start_dialogue("settlement_spec_result")

    curr_title = settlement.get_specialization_title() if settlement else "Standard"
    spec_choices = [
        DialogueChoice("🛡️ Military Fortress (Knights: +15% ATK/+20% DEF Safe Zone, Patrols)", None, lambda: choose_spec(SPECIALIZATION_MILITARY)),
        DialogueChoice("⚖️ Trade Hub (Merchants: +15% Shop Discount, Rare Goods, Caravans)", None, lambda: choose_spec(SPECIALIZATION_TRADE)),
        DialogueChoice("🔮 Arcane Sanctuary (Mages: +5 Mana/s Village Regen, 25% Rune Discount)", None, lambda: choose_spec(SPECIALIZATION_ARCANE)),
        DialogueChoice("Back to previous menu.", return_node_id)
    ]

    node = DialogueNode(
        "settlement_specialization_menu",
        "Town Specialization Proclamation",
        f"Current Designation: [{curr_title}].\nSelect a strategic specialization for Asterra (75g or Friendly 20+ Faction Standing):",
        spec_choices
    )
    dm.add_node(node)
    return node


class ElderEldrin(NPC):
    """Elder of Asterra. Guides the player along the Main Quest path."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Elder Eldrin", "npc_eldrin")

    def interact(self) -> None:
        """Checks Main Quest state to trigger corresponding dialogues."""
        if not self.on_interact_start("Eldrin"):
            return
        quest = self.game.quest_manager.quests["main_quest"]
        
        # Setup Elder conversation trees
        self.game.dialogue_manager.close()
        player = self.game.player
        settlement = getattr(self.game.living_world, "settlement", None) if hasattr(self.game, "living_world") else None

        def fund_silas():
            if player.gold >= 100:
                if settlement and settlement.fund_investment("silas_market", 30.0):
                    player.gold -= 100
                    from rpg.combat import DamageNumber
                    DamageNumber(self.rect.center, "Royal Market Unlocked! -20% Shop Discount!", (255, 215, 0), [self.game.ui_sprites], size=18)
                    self.game.dialogue_manager.start_dialogue("eldrin_silas")

        def fund_watchtower():
            if player.gold >= 50:
                if settlement and settlement.fund_investment("watchtower", 20.0):
                    player.gold -= 50
                    if hasattr(self.game, "living_world"):
                        self.game.living_world.event_bus.emit("road_safety_increased", amount=50.0)
                    from rpg.combat import DamageNumber
                    DamageNumber(self.rect.center, "Watchtower Erected! Raid Shield Active!", (100, 255, 100), [self.game.ui_sprites], size=18)
                    self.game.dialogue_manager.start_dialogue("eldrin_watchtower")

        def fund_dennis():
            if player.gold >= 50:
                if settlement and settlement.fund_investment("master_forge", 20.0):
                    player.gold -= 50
                    from rpg.combat import DamageNumber
                    DamageNumber(self.rect.center, "Master Forge Unlocked! Tier 2 Weapons!", (255, 180, 60), [self.game.ui_sprites], size=18)
                    self.game.dialogue_manager.start_dialogue("eldrin_dennis")

        def open_specialization_menu():
            create_settlement_specialization_dialogue(self.game, "eldrin_start")
            self.game.dialogue_manager.start_dialogue("settlement_specialization_menu")

        node_s = DialogueNode("eldrin_silas", self.name, "Wonderful investment! Silas has expanded the Royal Market. All shop prices in Asterra receive a 20% discount!", [DialogueChoice("Great news.", None)])
        node_w = DialogueNode("eldrin_watchtower", self.name, "The Village Watchtower is built! Watchmen now scout for monster raids and highway safety is fortified.", [DialogueChoice("Asterra is safe.", None)])
        node_d = DialogueNode("eldrin_dennis", self.name, "Dennis has upgraded his forge to a Master Anvil! You can now forge Tier 2 weapons and armor.", [DialogueChoice("To the forge!", None)])
        
        self.game.dialogue_manager.add_node(node_s)
        self.game.dialogue_manager.add_node(node_w)
        self.game.dialogue_manager.add_node(node_d)

        investment_choices = []
        if settlement:
            investment_choices.append(DialogueChoice("🏛️ [SPECIALIZE] Proclaim Town Strategic Specialization", None, open_specialization_menu))
            if not settlement.is_investment_completed("silas_market") and player.gold >= 100:
                investment_choices.append(DialogueChoice("[INVEST: SILAS] Fund Royal Market (100g -> -20% Shop Prices)", None, fund_silas))
            if not settlement.is_investment_completed("watchtower") and player.gold >= 50:
                investment_choices.append(DialogueChoice("[INVEST: ELDRIN] Fund Watchtower (50g -> Raid Shield & Road Safety)", None, fund_watchtower))
            if not settlement.is_investment_completed("master_forge") and player.gold >= 50:
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
            completed_qs = self.game.quest_manager.check_completable_quests(player)
            if quest in completed_qs or quest.status == QUEST_COMPLETED:
                # Main Quest Handed In!
                if hasattr(self.game, "reputation_manager"):
                    if "Savior of Asterra" not in self.game.reputation_manager.unlocked_titles:
                        self.game.reputation_manager.unlocked_titles.append("Savior of Asterra")
                    self.game.reputation_manager.active_title = "Savior of Asterra"
                txt = "You have defeated the Shadow Overlord and saved Asterra! The land is restored and your legacy is eternal. You are honored as the Savior of Asterra!"
                node = DialogueNode("eldrin_complete", self.name, txt, investment_choices + [DialogueChoice("I am honored.", None), DialogueChoice("Goodbye.", None)])
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("eldrin_complete")
            else:
                txt = "How goes the quest? Cleanse the wolves, gather 3 Iron Ores, and defeat the Shadow Overlord."
                node = DialogueNode("eldrin_active", self.name, txt, investment_choices + [DialogueChoice("Continue quest.", None), DialogueChoice("Goodbye.", None)])
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("eldrin_active")
            
        elif quest.status == QUEST_COMPLETED:
            txt = "You have saved Asterra! The light returns. You are a legendary champion."
            node = DialogueNode("eldrin_complete", self.name, txt, investment_choices + [DialogueChoice("Thank you.", None), DialogueChoice("Goodbye.", None)])
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("eldrin_complete")
            
        self.game.game_state = STATE_DIALOGUE

class MerchantSilas(NPC):
    """Silas the merchant. Trades items (buying/selling consumables & weapons)."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Merchant Silas", "npc_silas")

    def interact(self) -> None:
        """Opens Shop UI trading inventory."""
        if not self.on_interact_start("Silas"):
            return
        self.game.dialogue_manager.close()

        
        def open_shop_callback():
            self.game.game_state = STATE_SHOP
            
        # Check Silas relationship tier for hidden inventory unlock
        silas_tier = "Unknown"
        greeting_txt = "Welcome! Looking to trade? I carry fine supplies and will buy raw ores/apples."
        if hasattr(self.game, "reputation_manager"):
            silas_tier = self.game.reputation_manager.get_npc_tier("Silas")
            if silas_tier in ["Trusted", "Friend", "Hero", "Legend"]:
                greeting_txt = "Welcome back, my trusted friend! I kept these rare imported goods set aside just for you."

        # Dialogue prompting to trade
        node = DialogueNode(
            "silas_start",
            self.name,
            greeting_txt,
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
        super().__init__(pos, groups, "Blacksmith Dennis", "npc_dennis")

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
                if hasattr(self.game, "memory_manager"):
                    self.game.memory_manager.add_memory("donated_iron_ore", "settlement", 4, target="Dennis")
                if hasattr(self.game, "reputation_manager"):
                    self.game.reputation_manager.modify_npc_relationship("Dennis", 45)
                    self.game.reputation_manager.modify_global_reputation(15)
                
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

        def upgrade_forge():
            settlement = getattr(self.game.living_world, "settlement", None) if hasattr(self.game, "living_world") else None
            if settlement:
                success, msg = settlement.upgrade_facility("blacksmith", player)
                from rpg.combat import DamageNumber
                color = (255, 215, 0) if success else (220, 60, 60)
                DamageNumber(self.rect.center, msg, color, [self.game.ui_sprites], size=16)

        # Build choices list based on player's Iron Ore inventory
        choices = []
        if player.inventory.has_item("Iron Ore", 5):
            choices.append(DialogueChoice("[TOWN SECURITY] Donate 5 Ore -> Forge Guard Shields (-15% Market Tax)", None, donate_ore_for_guards))
            choices.append(DialogueChoice("[PERSONAL POWER] Sell 5 Ore for 50 Gold (Buy Spells)", None, sell_ore_for_gold))

        settlement = getattr(self.game.living_world, "settlement", None) if hasattr(self.game, "living_world") else None
        if settlement:
            lvl = settlement.get_facility_level("blacksmith")
            if lvl < 3:
                summary = settlement.get_facility_upgrade_cost_summary("blacksmith", player)
                choices.append(DialogueChoice(f"[UPGRADE FORGE] Level {lvl + 1} ({summary})", None, upgrade_forge))
            else:
                choices.append(DialogueChoice("[FORGE] Blacksmith is Max Level (Lvl 3)", None))

        choices.append(DialogueChoice("Open Forge Crafting", None, open_crafting))
        choices.append(DialogueChoice("Goodbye.", None))

        if side_quest.status == QUEST_NOT_STARTED:
            if qm.is_quest_available("blacksmith_quest"):
                node = DialogueNode(
                    "dennis_start",
                    self.name,
                    "Scholar Mira sent you? I can forge a sturdy shield for you, but I need 5 Iron Ores. You can find them in Cavern crates, scavenge them from skeletons/goblins, or buy them from Silas!",
                    [
                        DialogueChoice("Sure, I'll bring 5 Iron Ores.", "dennis_accepted", accept_side),
                        DialogueChoice("Just open the forge.", None, open_crafting)
                    ]
                )
                node_acc = DialogueNode("dennis_accepted", self.name, "Excellent! Bring 5 Iron Ores (from Cavern crates, monster drops, or Merchant Silas) and I'll reward you with a Wooden Shield.")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.add_node(node_acc)
                self.game.dialogue_manager.start_dialogue("dennis_start")
            else:
                node = DialogueNode("dennis_locked", self.name, "Complete Scholar Mira's quest in Ruins first!", choices)
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("dennis_locked")
            dennis_greeting = "Ready to work the anvil?"
            if hasattr(self.game, "memory_manager") and self.game.memory_manager.has_memory("donated_iron_ore"):
                dennis_greeting = "I've been forging ever since you brought me that iron ore. The village guards still carry your shields! What can I craft for you today?"
            hint = " Next: Visit Guardian Kai at Lake." if side_quest.status == QUEST_COMPLETED else ""
            node = DialogueNode("dennis_regular", self.name, f"{dennis_greeting}{hint}", choices)
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("dennis_regular")
            
        self.game.game_state = STATE_DIALOGUE

class RangerFaye(NPC):
    """Ranger Faye in the Forest. Gives Forest Patrol quest."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Ranger Faye", "npc_faye")

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

        # Slime quest acceptance callback
        slime_q = qm.quests.get("slime_quest")
        def accept_slime():
            qm.accept_quest("slime_quest")

        slime_choice = None
        if slime_q and slime_q.status == QUEST_NOT_STARTED:
            slime_choice = DialogueChoice("[SIDE QUEST] Clear Slime Infestation (5 Slimes)", "faye_slime_acc", accept_slime)
            node_slime_acc = DialogueNode("faye_slime_acc", self.name, "Good! Slay 5 Green Slimes along the forest trails. They've been scaring travelers.")
            self.game.dialogue_manager.add_node(node_slime_acc)

        comp_choices = self.get_companion_dialogue_choices("faye")

        if quest.status == QUEST_NOT_STARTED:
            if qm.is_quest_available("forest_patrol"):
                extra = [slime_choice] if slime_choice else []
                node = DialogueNode(
                    "faye_start",
                    self.name,
                    "Traveler! The forest trails are contested between Knight Patrols and Hunter Preserves. How shall we manage the region?",
                    faction_choices + extra + comp_choices + [DialogueChoice("I'll clear the forest! (5 Slimes, 2 Wolves)", "faye_acc", accept)]
                )
                node_acc = DialogueNode("faye_acc", self.name, "Thank you! Slay 5 Slimes and 2 Wolves. Be careful out there.")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.add_node(node_acc)
                self.game.dialogue_manager.start_dialogue("faye_start")
            else:
                extra = [slime_choice] if slime_choice else []
                node = DialogueNode("faye_locked", self.name, "Speak to Elder Eldrin in the Village first! But if you want a quick task, I have something...", faction_choices + extra + comp_choices)
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("faye_locked")
        elif quest.status == QUEST_ACTIVE:
            node = DialogueNode("faye_active", self.name, "Keep clearing the paths! Slay 5 Slimes and 2 Wolves.", faction_choices + comp_choices)
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("faye_active")
        else:
            node = DialogueNode("faye_done", self.name, "Great job in the forest! Seek Scholar Mira in the Ruins to the east.", faction_choices + comp_choices)
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("faye_done")

        self.game.game_state = STATE_DIALOGUE

class ScholarMira(NPC):
    """Scholar Mira in the Ruins. Gives Echoes of the Past quest."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Scholar Mira", "npc_mira")

    def interact(self) -> None:
        if not self.on_interact_start("Mira"):
            return
        self.game.dialogue_manager.close()
        qm = self.game.quest_manager
        quest = qm.quests["scholar_quest"]

        def accept():
            qm.accept_quest("scholar_quest")

        comp_choices = self.get_companion_dialogue_choices("mira")

        if quest.status == QUEST_NOT_STARTED:
            if qm.is_quest_available("scholar_quest"):
                node = DialogueNode(
                    "mira_start",
                    self.name,
                    "Welcome, brave traveler. Deep in these ruined halls lies a chest with an Ancient Scroll detailing the Shadow Overlord's origin. Will you retrieve it?",
                    [
                        DialogueChoice("I will find the scroll.", "mira_acc", accept),
                    ] + comp_choices + [
                        DialogueChoice("Maybe later.", None)
                    ]
                )
                node_acc = DialogueNode("mira_acc", self.name, "Search the chests in the Ruins for the Ancient Scroll!")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.add_node(node_acc)
                self.game.dialogue_manager.start_dialogue("mira_start")
            else:
                node = DialogueNode("mira_locked", self.name, "Complete Ranger Faye's quest 'Forest Patrol' in the Forest first before exploring these Ruins!", comp_choices)
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("mira_locked")
        elif quest.status == QUEST_ACTIVE:
            node = DialogueNode("mira_active", self.name, "Look for the chest inside these ruined halls to retrieve the Ancient Scroll.", comp_choices)
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("mira_active")
        else:
            expedition_q = qm.quests.get("ruins_expedition")
            def accept_expedition():
                qm.accept_quest("ruins_expedition")

            if expedition_q and expedition_q.status == QUEST_NOT_STARTED:
                node = DialogueNode(
                    "mira_expedition_start",
                    self.name,
                    "The scroll reveals the Shadow Overlord's void seal in the Catacombs! We need to recover a Relic Fragment from the Bandit Warlord in these Ruins.",
                    [
                        DialogueChoice("[EXPEDITION] Accept Ruins Reconnaissance Expedition", "mira_expedition_acc", accept_expedition),
                    ] + comp_choices + [
                        DialogueChoice("I'll prepare first.", None)
                    ]
                )
                node_acc = DialogueNode("mira_expedition_acc", self.name, "Defeat the Bandit Warlord holding the vault and recover the Relic Fragment!")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.add_node(node_acc)
                self.game.dialogue_manager.start_dialogue("mira_expedition_start")
            else:
                node = DialogueNode("mira_done", self.name, "The scroll reveals the Shadow Overlord is in the Dungeon! You'll need sturdy iron gear. Speak to Blacksmith Dennis in the Village.", comp_choices)
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("mira_done")

        self.game.game_state = STATE_DIALOGUE

class MinerGarth(NPC):
    """Miner Garth in the Caverns. Provides mining guidance."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Miner Garth", "npc_garth")

    def interact(self) -> None:
        if not self.on_interact_start("Garth"):
            return
        self.game.dialogue_manager.close()

        # Check if Garth's mind is compromised
        cm = getattr(self.game, "conspiracy_manager", None)
        if cm and cm.is_npc_compromised("garth"):
            c_data = cm.compromised_npcs.get("garth")
            cold_text = c_data.cold_dialogue if c_data else "The deep rocks speak of darkness... do not stand in our way."

            def initiate_exorcism():
                player = self.game.player
                if getattr(player, "mana", 0) >= 15:
                    player.mana -= 15
                    from rpg.enemy import ShadowParasite
                    from rpg.constants import STATE_PLAYING
                    spawn_pos = (self.pos.x + 32, self.pos.y)
                    parasite = ShadowParasite(spawn_pos, [self.game.visible_sprites], target_npc_id="garth")
                    parasite.game = self.game
                    parasite.sound_manager = self.game.sound_manager
                    parasite.particles = self.game.particles
                    self.game.enemies.append(parasite)
                    from rpg.combat import DamageNumber
                    DamageNumber(self.rect.center, "⚔️ EXORCISM INITIATED!", (200, 140, 255), [self.game.ui_sprites], size=18)
                    self.game.dialogue_manager.close()
                    self.game.game_state = STATE_PLAYING

            choices = [
                DialogueChoice("✨ Perform Exorcism Ritual (15 Mana)", None, initiate_exorcism),
                DialogueChoice("Leave", None, lambda: self.game.dialogue_manager.close())
            ]
            node = DialogueNode("garth_compromised", f"{self.name} [COMPROMISED]", cold_text, choices)
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("garth_compromised")
            self.game.game_state = STATE_DIALOGUE
            return

        node = DialogueNode("garth_talk", self.name, "Greetings! These caverns are rich with Iron Ores inside resource chests. Bring 5 Iron Ores to Blacksmith Dennis in the Village to forge armor!")
        self.game.dialogue_manager.add_node(node)
        self.game.dialogue_manager.start_dialogue("garth_talk")
        self.game.game_state = STATE_DIALOGUE

class GuardianKai(NPC):
    """Guardian Kai at the Lake. Gives Lake Vigil quest."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Guardian Kai", "npc_kai")

    def interact(self) -> None:
        if not self.on_interact_start("Kai"):
            return
        self.game.dialogue_manager.close()
        qm = self.game.quest_manager
        quest = qm.quests["lake_quest"]

        def accept():
            qm.accept_quest("lake_quest")

        comp_choices = self.get_companion_dialogue_choices("kai")

        if quest.status == QUEST_NOT_STARTED:
            if qm.is_quest_available("lake_quest"):
                node = DialogueNode(
                    "kai_start",
                    self.name,
                    "Frost Slimes are corrupting our lake shores! Help me drive back 4 Frost Slimes.",
                    [
                        DialogueChoice("I'll defeat 4 Frost Slimes.", "kai_acc", accept),
                    ] + comp_choices + [
                        DialogueChoice("Not now.", None)
                    ]
                )
                node_acc = DialogueNode("kai_acc", self.name, "Thank you! Hunt down 4 Frost Slimes around the lake.")
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.add_node(node_acc)
                self.game.dialogue_manager.start_dialogue("kai_start")
            else:
                node = DialogueNode("kai_locked", self.name, "Complete Blacksmith Dennis's quest 'Iron Forging' in the Village first so you are equipped with a sturdy shield!", comp_choices)
                self.game.dialogue_manager.add_node(node)
                self.game.dialogue_manager.start_dialogue("kai_locked")
        elif quest.status == QUEST_ACTIVE:
            node = DialogueNode("kai_active", self.name, "Drive back 4 Frost Slimes along the shores of this lake.", comp_choices)
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("kai_active")
        else:
            node = DialogueNode("kai_done", self.name, "Thank you warrior! North of here lies a hidden grove (Secret Area). Visit the sacred altar there, then head to the Dungeon to face the Shadow Overlord!", comp_choices)
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("kai_done")

        self.game.game_state = STATE_DIALOGUE

class SpiritOfAsterra(NPC):
    """Spirit of Asterra in the Secret Area. Gives final lore."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Spirit of Asterra", "npc_spirit")

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
        super().__init__(pos, groups, "Greed Altar", "greed_altar", can_wander=False)
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
        super().__init__(pos, groups, "Town Investment Board", "noticeboard", can_wander=False)
        self.image = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (100, 70, 40), (0, 0, 44, 44), border_radius=4)
        pygame.draw.rect(self.image, (210, 170, 60), (2, 2, 40, 40), 2, border_radius=3)
        try:
            font = pygame.font.Font("assets/fonts/game_font.ttf", 10)
        except Exception as e:
            print(f"Debug: Using fallback font for Noticeboard: {e}")
            font = pygame.font.SysFont("Arial", 10, bold=True)
        lbl = font.render("NOTICE", True, (255, 240, 200))
        self.image.blit(lbl, (4, 14))

    def interact(self) -> None:
        self.game.dialogue_manager.close()
        player = self.game.player
        settlement = getattr(self.game.living_world, "settlement", None) if hasattr(self.game, "living_world") else None

        # --- Bounty Board Integration ---
        bounty_mgr = getattr(self.game, "bounty_manager", None)
        if bounty_mgr:
            # Auto-refresh if board is empty
            if not bounty_mgr.available_bounties and not bounty_mgr.active_bounties:
                bounty_mgr.refresh_board(player.level)

        def fund_silas():
            if player.gold >= 100:
                if settlement and settlement.fund_investment("silas_market", 30.0):
                    player.gold -= 100
                    from rpg.combat import DamageNumber
                    DamageNumber(self.rect.center, "Royal Market Unlocked! -20% Shop Discount!", (255, 215, 0), [self.game.ui_sprites], size=18)

        def fund_watchtower():
            if player.gold >= 50:
                if settlement and settlement.fund_investment("watchtower", 20.0):
                    player.gold -= 50
                    if hasattr(self.game, "living_world"):
                        self.game.living_world.event_bus.emit("road_safety_increased", amount=50.0)
                    from rpg.combat import DamageNumber
                    DamageNumber(self.rect.center, "Watchtower Erected! Raid Shield Active!", (100, 255, 100), [self.game.ui_sprites], size=18)

        def fund_dennis():
            if player.gold >= 50:
                if settlement and settlement.fund_investment("master_forge", 20.0):
                    player.gold -= 50
                    from rpg.combat import DamageNumber
                    DamageNumber(self.rect.center, "Master Forge Unlocked! Tier 2 Weapons!", (255, 180, 60), [self.game.ui_sprites], size=18)

        choices = []

        # --- Bounty Contracts Section ---
        if bounty_mgr:
            # Show turn-in options for completed bounties first
            for b in list(bounty_mgr.active_bounties):
                if b.is_completed and not b.is_turned_in:
                    def _turn_in(bounty=b):
                        success, msg = bounty_mgr.turn_in_bounty(bounty, player)
                        if success:
                            from rpg.combat import DamageNumber
                            DamageNumber(self.rect.center, f"BOUNTY COMPLETE! {msg}", (255, 215, 0), [self.game.ui_sprites], size=18)
                    choices.append(DialogueChoice(f"[TURN IN] {b.title} ({b.gold_reward}g + {b.xp_reward}XP)", None, _turn_in))

            # Show progress on active bounties
            for b in bounty_mgr.active_bounties:
                if not b.is_completed:
                    choices.append(DialogueChoice(f"[ACTIVE] {b.title} ({b.current_count}/{b.required_count})", None))

            # Show available bounties to accept
            for b in bounty_mgr.available_bounties:
                if not b.is_accepted:
                    def _accept(bounty=b):
                        success, msg = bounty_mgr.accept_bounty(bounty)
                        from rpg.combat import DamageNumber
                        color = (100, 255, 100) if success else (220, 60, 60)
                        DamageNumber(self.rect.center, msg, color, [self.game.ui_sprites], size=16)
                    label = f"[BOUNTY] {b.title} → {b.gold_reward}g + {b.xp_reward}XP"
                    choices.append(DialogueChoice(label, None, _accept))

            # Refresh board option
            def _refresh():
                bounty_mgr.refresh_board(player.level)
                from rpg.combat import DamageNumber
                DamageNumber(self.rect.center, "Board refreshed!", (120, 200, 255), [self.game.ui_sprites], size=14)
            choices.append(DialogueChoice("[REFRESH] New bounty contracts", None, _refresh))

        # --- Quest Infrastructure Options ---
        qm = self.game.quest_manager
        b_quest = qm.quests.get("bridge_repair_quest")
        w_quest = qm.quests.get("watchtower_quest")

        def accept_bridge_q():
            qm.accept_quest("bridge_repair_quest")

        def accept_watchtower_q():
            qm.accept_quest("watchtower_quest")

        if b_quest and b_quest.status == QUEST_NOT_STARTED:
            choices.append(DialogueChoice("[QUEST] Northern Bridge Repair (5 Oak Wood from Wolves, 3 Iron Ore)", None, accept_bridge_q))
        elif b_quest and b_quest.status == QUEST_ACTIVE:
            choices.append(DialogueChoice("[STATUS] Bridge Repair Active (5 Oak Wood from Wolves, 3 Iron Ore needed)", None))
        elif b_quest and b_quest.status == QUEST_COMPLETED:
            choices.append(DialogueChoice("[STATUS] Northern Bridge Rebuilt!", None))

        if w_quest and w_quest.status == QUEST_NOT_STARTED:
            choices.append(DialogueChoice("[QUEST] Watchtower Construction (3 Oak Wood from Wolves, 2 Iron Ore)", None, accept_watchtower_q))
        elif w_quest and w_quest.status == QUEST_ACTIVE:
            choices.append(DialogueChoice("[STATUS] Watchtower Construction Active (3 Oak Wood from Wolves, 2 Iron Ore needed)", None))
        elif w_quest and w_quest.status == QUEST_COMPLETED:
            choices.append(DialogueChoice("[STATUS] Watchtower Erected!", None))

        def open_specialization_menu():
            create_settlement_specialization_dialogue(self.game, "town_board")
            self.game.dialogue_manager.start_dialogue("settlement_specialization_menu")

        # --- Investment & Specialization Options ---
        if settlement:
            choices.append(DialogueChoice("🏛️ [SPECIALIZE] Proclaim Town Strategic Specialization", None, open_specialization_menu))
            if not settlement.is_investment_completed("silas_market") and player.gold >= 100:
                choices.append(DialogueChoice("[INVEST: SILAS] Fund Royal Market (100g -> -20% Shop Prices)", None, fund_silas))
            if not settlement.is_investment_completed("watchtower") and player.gold >= 50:
                choices.append(DialogueChoice("[INVEST: ELDRIN] Fund Watchtower (50g -> Raid Shield & Road Safety)", None, fund_watchtower))
            if not settlement.is_investment_completed("master_forge") and player.gold >= 50:
                choices.append(DialogueChoice("[INVEST: DENNIS] Fund Master Forge (50g -> Tier 2 Gear)", None, fund_dennis))
        choices.append(DialogueChoice("Close Town Board.", None))

        board_desc = "Asterra Town Board: Accept bounties, fund investments, and build infrastructure!"
        if bounty_mgr:
            board_desc += f" (Bounties completed: {bounty_mgr.completed_count})"
        node = DialogueNode("town_board", self.name, board_desc, choices)
        self.game.dialogue_manager.add_node(node)
        self.game.dialogue_manager.start_dialogue("town_board")
        self.game.game_state = STATE_DIALOGUE

class PastHeroStatue(NPC):
    """Weathered Stone Statue of a Past Hero from Mythos History."""
    def __init__(self, pos: Tuple[float, float], record: Dict[str, Any], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, f"Statue of {record.get('hero_name', 'Ancient Champion')}", "past_statue", can_wander=False)
        self.record = record
        self.image = pygame.Surface((40, 56), pygame.SRCALPHA)
        # Stone pedestal
        pygame.draw.rect(self.image, (90, 95, 105), (4, 36, 32, 20), border_radius=4)
        # Weathered stone hero figure
        pygame.draw.circle(self.image, (160, 165, 175), (20, 18), 12)
        pygame.draw.rect(self.image, (140, 145, 155), (10, 26, 20, 14), border_radius=3)
        # Inscribed rune
        pygame.draw.circle(self.image, (210, 170, 60), (20, 20), 4)

    def interact(self) -> None:
        self.game.dialogue_manager.close()
        h_name = self.record.get("hero_name", "Ancient Champion")
        days = self.record.get("days_lived", 1)
        wpn = self.record.get("favored_weapon", "Steel Blade")
        faction = self.record.get("favored_faction", "knights").title()
        end_reason = self.record.get("end_cause", "Fell in battle")

        txt = (
            f"An ancient weathered stone monument inscribed with runes:\n\n"
            f"'Here rests {h_name}, who favored the {faction} and wielded the {wpn}. "
            f"Survived {days} days before {end_reason}.'"
        )
        node = DialogueNode("past_statue_read", self.name, txt, [DialogueChoice("Honor the Old Hero.", None)])
        self.game.dialogue_manager.add_node(node)
        self.game.dialogue_manager.start_dialogue("past_statue_read")
        self.game.game_state = STATE_DIALOGUE

class BardFinn(NPC):
    """Bard Finn. Sings procedural ballad songs generated from player memories."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Bard Finn", "npc_finn")

    def interact(self) -> None:
        """Triggers procedural song composition and dialogue."""
        if not self.on_interact_start("Finn"):
            return
        self.game.dialogue_manager.close()

        from rpg.bard import BardSongEngine
        song_txt = BardSongEngine.compose_song(
            getattr(self.game, "memory_manager", None),
            getattr(self.game, "reputation_manager", None)
        )

        node = DialogueNode(
            "bard_song",
            self.name,
            song_txt,
            [DialogueChoice("Bravo! What a song.", None)]
        )
        self.game.dialogue_manager.add_node(node)
        self.game.dialogue_manager.start_dialogue("bard_song")
        self.game.game_state = STATE_DIALOGUE


class RivalAdventurerNPC(NPC):
    """
    Rival Adventurer NPC (Valen the Wanderer).
    Autonomous rival who roams the zones, provides contextual dialogue,
    spars with the player, exchanges supplies, and shares hunting accomplishments.
    """
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group]) -> None:
        super().__init__(pos, groups, "Valen", "npc_rival")
        self.npc_id = "rival_valen"

    def interact(self) -> None:
        """Triggers dynamic rival dialogue connecting with NPCMemory and RivalManager."""
        if not self.on_interact_start("valen"):
            return
        self.game.dialogue_manager.close()

        if hasattr(self.game, "living_world") and hasattr(self.game.living_world, "rival"):
            self.game.living_world.rival.build_dialogue_nodes(self.game, self)
            self.game.dialogue_manager.start_dialogue("rival_valen_root")
            self.game.game_state = STATE_DIALOGUE
        else:
            node = DialogueNode(
                "valen_fallback",
                self.name,
                "Greetings, adventurer. Keep your blade sharp in these wilds.",
                [DialogueChoice("Will do.", None)]
            )
            self.game.dialogue_manager.add_node(node)
            self.game.dialogue_manager.start_dialogue("valen_fallback")
            self.game.game_state = STATE_DIALOGUE


