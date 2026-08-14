"""
Echoes of Asterra - Core Game Coordination Engine
Coordinates state machines, game loop updates, rendering, portal level transitions,
NPC interactions, and panel menus overlays.
"""
import pygame
import sys
from typing import List, Tuple, Any
from rpg.constants import (
    STATE_MENU, STATE_PLAYING, STATE_PAUSED, STATE_GAME_OVER, STATE_VICTORY, STATE_DIALOGUE, STATE_SHOP, STATE_SETTINGS,
    STATE_TUTORIAL, MAP_VILLAGE, COLOR_BLACK,
    SKILL_FIREBALL, SKILL_ICE_SPIKE, SKILL_HEALING, SKILL_DASH
)
from rpg.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TARGET_FPS, TILE_SIZE, GRID_WIDTH, GRID_HEIGHT,
    KEY_CHARACTER, KEY_QUEST, KEY_INTERACT
)
from rpg.sound import SoundManager
from rpg.input import InputHandler
from rpg.ui import UIManager
from rpg.camera import Camera
from rpg.particles import ParticleSystem
from rpg.weather import WeatherSystem
from rpg.lighting import LightingSystem
from rpg.effects import EffectsManager
from rpg.quests import QuestManager
from rpg.dialogue import DialogueManager
from rpg.world import WorldManager
from rpg.sprite import YSortedGroup
from rpg.player import Player
from rpg.minimap import Minimap
from rpg.events import EventBus
from rpg.factions import FactionManager
from rpg.npc_memory import NPCMemoryManager
from rpg.living_world import LivingWorldManager
from rpg.debug_overlay import DebugOverlay

class Game:
    """
    Main engine orchestrator connecting graphics, audio, inputs, and states.
    """
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.dt = 0.0
        self.is_fullscreen = False
        self.target_fps = TARGET_FPS

        # State machine
        self.game_state = STATE_MENU

        # Initialize Core Subsystems
        self.event_bus = EventBus()
        from rpg.config import game_config
        from rpg.services import ServiceContainer
        self.services = ServiceContainer(game_config, self.event_bus)

        self.living_world = LivingWorldManager(self.event_bus)
        self.living_world.game_reference = self
        self.debug_overlay = DebugOverlay()


        # Accessor aliases for backward compatibility
        self.world_state = self.living_world.world_state
        self.ecology = self.living_world.ecology

        self.factions = FactionManager()
        self.factions.register_event_listeners(self.event_bus)
        self.living_world.faction_war.faction_manager = self.factions

        self.npc_memory = NPCMemoryManager()
        self.npc_memory.register_event_listeners(self.event_bus)

        from rpg.memory import MemoryManager
        self.memory_manager = MemoryManager(self.event_bus)

        from rpg.social import ReputationManager
        self.reputation_manager = ReputationManager(self.event_bus, self.memory_manager)

        from rpg.notification import NotificationManager
        self.notification_manager = NotificationManager()
        self.sound_manager = SoundManager()
        self.input_handler = InputHandler()
        self.ui_manager = UIManager()
        self.ui_manager.notification_manager = self.notification_manager
        self.particles = ParticleSystem()

        self.weather = WeatherSystem()
        self.weather.sound_manager = self.sound_manager
        self.lighting = LightingSystem()
        from rpg.bestiary import BestiaryManager

        self.effects_manager = EffectsManager()
        self.quest_manager = QuestManager()
        self.quest_manager.event_bus = self.event_bus
        self.dialogue_manager = DialogueManager()

        from rpg.bounty import BountyManager
        self.bounty_manager = BountyManager()

        self.dialogue_manager.game = self
        self.world_manager = WorldManager()
        self.bestiary_manager = BestiaryManager(self.event_bus)

        # Sprite groups
        self.visible_sprites = YSortedGroup()
        self.projectiles = pygame.sprite.Group()
        self.dropped_items = pygame.sprite.Group()
        self.chests = pygame.sprite.Group()
        self.npcs = pygame.sprite.Group()
        self.waypoint_obelisks = pygame.sprite.Group()
        self.ui_sprites = YSortedGroup()  # Renders floating combat texts
        self.enemies = []
        self._enemies_list = self.enemies


        # Initialize Player (Spawned at center of Village)
        self.player = Player((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), [self.visible_sprites], self.sound_manager, self.particles)
        self.player.game = self

        # Minimap & Camera
        self.minimap = Minimap()
        self.camera = Camera(GRID_WIDTH * TILE_SIZE, GRID_HEIGHT * TILE_SIZE)
        self.minimap_enabled = True

        # Mythos Inheritance Engine (Warisan Mitos & Legacy)
        from rpg.mythos import MythosManager
        from rpg.mythos_reader import MythosReader
        from rpg.telemetry import EventTelemetry
        from rpg.achievements import AchievementManager
        self.mythos_manager = MythosManager()
        self.mythos_reader = MythosReader(self)
        self.mythos_reader.apply_historical_world_buffs()
        if hasattr(self, "dialogue_manager"):
            self.mythos_reader.inject_legend_into_dialogue_manager(self.dialogue_manager)

        self.telemetry = EventTelemetry()
        self.telemetry.register_event_bus(self.event_bus)
        self.achievement_manager = AchievementManager(self.event_bus)
        self.difficulty_profile = "normal"
        self.tutorial_flags = set()

        from rpg.style_scoring import StyleScoring
        self.style_scoring = StyleScoring()

        # Subscribe onboarding tips and living world feedback to EventBus
        self.event_bus.subscribe("first_inventory_open", self._show_inventory_tip)
        self.event_bus.subscribe("first_combat", self._show_combat_tip)
        self.event_bus.subscribe("first_levelup", self._show_levelup_tip)
        self.event_bus.subscribe("first_quest_accepted", self._show_quest_tip)
        self.event_bus.subscribe("town_invested", self._on_town_invested)


        # Load initial village map for menu background and start Main Menu BGM
        self.world_manager.load_map(MAP_VILLAGE, self.player, portal_spawn=False)
        self.sound_manager.play_music("menu_music")

        from rpg.notification import NotificationPriority
        self.notification_manager.push_toast(
            f"Difficulty Mode: {self.difficulty_profile.upper()} (Adjust in Settings [ESC])",
            priority=NotificationPriority.HIGH
        )


    def _show_inventory_tip(self, **kwargs: Any) -> None:
        if "inventory" not in self.tutorial_flags:
            self.tutorial_flags.add("inventory")
            if hasattr(self, "ui_manager") and hasattr(self.ui_manager, "notification_manager"):
                from rpg.notification import NotificationPriority
                self.ui_manager.notification_manager.push_toast(
                    "Tip: Right-click items to equip/use. Press 1-4 for shortcuts!",
                    priority=NotificationPriority.HIGH
                )

    def _show_combat_tip(self, **kwargs: Any) -> None:
        if "combat" not in self.tutorial_flags:
            self.tutorial_flags.add("combat")
            if hasattr(self, "ui_manager") and hasattr(self.ui_manager, "notification_manager"):
                from rpg.notification import NotificationPriority
                self.ui_manager.notification_manager.push_toast(
                    "Tip: Left-Click to attack, Space to dodge roll!",
                    priority=NotificationPriority.HIGH
                )

    def _show_levelup_tip(self, **kwargs: Any) -> None:
        if "levelup" not in self.tutorial_flags:
            self.tutorial_flags.add("levelup")
            if hasattr(self, "ui_manager") and hasattr(self.ui_manager, "notification_manager"):
                from rpg.notification import NotificationPriority
                self.ui_manager.notification_manager.push_toast(
                    "Tip: Level Up! Press [C] to view Stats & Skills!",
                    priority=NotificationPriority.HIGH
                )

    def _show_quest_tip(self, **kwargs: Any) -> None:
        if "quest" not in self.tutorial_flags:
            self.tutorial_flags.add("quest")
            if hasattr(self, "ui_manager") and hasattr(self.ui_manager, "notification_manager"):
                from rpg.notification import NotificationPriority
                self.ui_manager.notification_manager.push_toast(
                    "Tip: Active quest targets are marked on your Minimap [M]!",
                    priority=NotificationPriority.HIGH
                )


    def _on_town_invested(self, investment_id: str = "", **kwargs: Any) -> None:

        names = {
            "silas_market": "Silas Royal Market (-20% Shop Tax)",
            "watchtower": "Village Watchtower (Raid Shield)",
            "master_forge": "Dennis Master Forge (Tier 2 Gear)"
        }
        inv_name = names.get(investment_id, investment_id.replace("_", " ").title())
        if hasattr(self, "ui_manager") and hasattr(self.ui_manager, "notification_manager"):
            from rpg.notification import NotificationPriority
            self.ui_manager.notification_manager.push_toast(
                f"🏛️ Settlement Upgraded: {inv_name}!",
                priority=NotificationPriority.HIGH
            )





    def toggle_fullscreen(self) -> None:
        """Toggles between Fullscreen and Windowed display mode cleanly with SCALED mouse mapping."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED)

    def return_from_settings(self) -> None:
        """Returns to pause menu if opened during gameplay, otherwise returns to main menu."""
        if getattr(self, "_from_pause_menu", False):
            self.game_state = STATE_PAUSED
            self._from_pause_menu = False
        else:
            self.game_state = STATE_MENU

    def is_save_allowed(self) -> Tuple[bool, str]:
        """
        Evaluates whether saving is safe and allowed based on region safety,
        enemy combat aggro, hostile proximity, and player health state.

        Returns:
            (allowed: bool, reason: str)
        """
        # 1. Player health / death status check
        if getattr(self.player, "is_dead", False) or getattr(self.player, "hp", 1) <= 0:
            return False, "Cannot save game while fallen or defeated!"

        current_map = getattr(self.world_manager, "current_map_name", "")

        # 2. Village is ALWAYS a designated safe zone
        if current_map == MAP_VILLAGE:
            return True, "Safe Zone (Village)"

        # 3. Wilderness threat checks (Forest, Cave, Crypt, etc.)
        threat_radius = 280.0  # ~9 tile radius

        enemies = getattr(self, "enemies", [])

        for enemy in enemies:
            if not getattr(enemy, "alive", True):
                continue

            # Check if enemy is actively chasing / targeting the player
            if getattr(enemy, "aggro", False):
                return False, f"Cannot save! In combat with {enemy.name}!"

            # Check proximity to hostile enemies in wilderness
            dist = self.player.pos.distance_to(enemy.pos)
            if dist < threat_radius:
                return False, f"Unsafe area! {enemy.name} is nearby."



        return True, "Safe to save"


    def start_new_game(self) -> None:
        """Resets variables and loads the starting Village map."""
        self.world_manager.boss_defeated = False
        self.world_manager.chests_opened.clear()

        # Reset player variables and state
        self.player.level = 1
        self.player.xp = 0
        self.player.xp_needed = 180
        self.player.gold = 10
        self.player.hp = self.player.base_max_hp
        self.player.mana = self.player.base_max_mana
        self.player.stamina = self.player.base_max_stamina
        self.player.state = "idle"
        self.player.action_timer = 0.0
        self.player.frame_index = 0.0
        self.player.is_invincible = False


        # Equip defaults
        self.player.inventory.slots = [None] * self.player.inventory.size
        self.player.equipment.slots = {k: None for k in self.player.equipment.slots}
        self.player.add_starter_items()
        self.player.equipment.recalculate_player_stats(self.player)

        self.player.skill_manager = type(self.player.skill_manager)()  # Fresh skills
        self.player.skill_manager.check_unlocks(self.player.level)

        # Reset quests
        self.quest_manager = type(self.quest_manager)()
        self.quest_manager.event_bus = self.event_bus

        # Reset achievements, bestiary, factions, memories, reputation, and npc_memory for new adventure
        if hasattr(self, "achievement_manager") and hasattr(self.achievement_manager, "reset"):
            self.achievement_manager.reset()
        if hasattr(self, "bestiary_manager") and hasattr(self.bestiary_manager, "reset"):
            self.bestiary_manager.reset()
        if hasattr(self, "memory_manager") and hasattr(self.memory_manager, "reset"):
            self.memory_manager.reset()
        if hasattr(self, "reputation_manager") and hasattr(self.reputation_manager, "reset"):
            self.reputation_manager.reset()
        if hasattr(self, "factions"):
            if hasattr(self.factions, "reset"):
                self.factions.reset()
            else:
                self.factions = FactionManager()
                self.factions.register_event_listeners(self.event_bus)
        if hasattr(self, "npc_memory"):
            if hasattr(self.npc_memory, "reset"):
                self.npc_memory.reset()
            else:
                self.npc_memory = NPCMemoryManager()
                self.npc_memory.register_event_listeners(self.event_bus)
        if hasattr(self, "living_world"):
            if hasattr(self.living_world, "reset"):
                self.living_world.reset()
            else:
                from rpg.living_world import LivingWorldManager
                self.living_world = LivingWorldManager(self.event_bus)
                self.living_world.game_reference = self
            self.world_state = self.living_world.world_state
            if hasattr(self, "factions"):
                self.living_world.faction_war.faction_manager = self.factions
        if hasattr(self, "mythos_reader"):
            self.mythos_reader.apply_historical_world_buffs()
            self.mythos_reader.inject_legend_into_dialogue_manager(self.dialogue_manager)




        # Reset tutorial flags and push initial onboarding notifications for New Adventure
        self.tutorial_flags.clear()
        if hasattr(self, "ui_manager") and self.ui_manager:
            self.ui_manager.show_banner(
                "WELCOME TO ASTERRA",
                f"Mode: {self.difficulty_profile.upper()} · Press [I] Backpack, [C] Character, [M] Minimap",
                color=(255, 215, 0),
                duration=6.0
            )

        if hasattr(self, "notification_manager") and self.notification_manager:
            from rpg.notification import NotificationPriority
            self.notification_manager.active_toasts.clear()
            self.notification_manager.toast_queue.clear()
            self.notification_manager.push_toast(
                f"Difficulty Mode: {self.difficulty_profile.upper()} (Adjust in Settings [ESC])",
                priority=NotificationPriority.HIGH
            )
            self.notification_manager.push_toast(
                "Welcome to Asterra! Press [I] Backpack, [C] Character, [M] Minimap",
                priority=NotificationPriority.HIGH
            )


        # Load map and switch state to PLAYING
        self.world_manager.load_map(MAP_VILLAGE, self.player, portal_spawn=False)
        self.services.reset_services()

        self.sound_manager.play_music("village_music", force=True)
        self.game_state = STATE_PLAYING

    def respawn_player(self) -> None:
        """
        Respawns the player at the Village safe zone with death penalties while maintaining full world state:
        1. Player ALWAYS respawns at MAP_VILLAGE.
        2. Un-equipped inventory items drop at the death location (death_pos in death_map)
           with a 300s (5-minute) despawn timer (Minecraft-style).
        3. XP Penalty: -25% of current level XP requirement (minimum 0).
        4. Gold Penalty: -30% of current Gold (dropped on floor at death_pos).
        5. Equipped gear, quests, map exploration, chests, boss kills, and world simulation stay intact.
        """
        import random
        player = self.player
        death_map = getattr(self.world_manager, "current_map_name", MAP_VILLAGE)
        death_pos = (player.pos.x, player.pos.y)

        if not hasattr(self.world_manager, "persistent_dropped_items"):
            self.world_manager.persistent_dropped_items = {}

        if death_map not in self.world_manager.persistent_dropped_items:
            self.world_manager.persistent_dropped_items[death_map] = []

        # 1. Store un-equipped inventory items to persistent dropped items for death_map
        for idx in range(len(player.inventory.slots)):
            item = player.inventory.slots[idx]
            if item is not None:
                scatter_offset = (
                    death_pos[0] + random.uniform(-20.0, 20.0),
                    death_pos[1] + random.uniform(-20.0, 20.0)
                )
                self.world_manager.persistent_dropped_items[death_map].append({
                    "pos": scatter_offset,
                    "item": item,
                    "despawn_timer": 300.0
                })
                player.inventory.slots[idx] = None

        # 2. Apply XP and Gold penalties
        xp_loss = int(player.xp_needed * 0.25)
        gold_loss = int(player.gold * 0.30)

        player.xp = max(0, player.xp - xp_loss)
        player.gold = max(0, player.gold - gold_loss)

        # Store gold coins stack on ground if gold was lost
        if gold_loss > 0:
            from rpg.items import create_item, Item
            gold_item = create_item("Gold Coins", gold_loss)
            if not gold_item:
                gold_item = Item("Gold Coins", "material", quantity=gold_loss)
            scatter_offset = (death_pos[0] + random.uniform(-14.0, 14.0), death_pos[1] + random.uniform(-14.0, 14.0))
            self.world_manager.persistent_dropped_items[death_map].append({
                "pos": scatter_offset,
                "item": gold_item,
                "despawn_timer": 300.0
            })

        # 3. Restore Player Vitals & State Machine
        player.state = "idle"
        player.action_timer = 0.0
        player.frame_index = 0.0
        player.is_invincible = False
        player.hp = player.max_hp
        player.mana = player.max_mana
        player.stamina = player.max_stamina

        # 4. ALWAYS respawn player at MAP_VILLAGE (Village safe town)
        self.world_manager.load_map(MAP_VILLAGE, player, portal_spawn=False)


        self.game_state = STATE_PLAYING
        self.sound_manager.play_sound("levelup")
        from rpg.combat import DamageNumber
        DamageNumber(player.rect.center, f"RESPAWNED IN VILLAGE! (-{xp_loss} XP, -{gold_loss} Gold)", (255, 215, 0), [self.ui_sprites], size=18)






    def process_events(self) -> None:
        """Captures window clicks, quick menu key toggles, and interactions."""
        events = pygame.event.get()
        self.input_handler.process_events(events)

        for event in events:
            if event.type == pygame.QUIT:
                self.sound_manager.stop_music()
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                # Developer Debug Overlay hotkey check (F9, F10, F11)
                if self.debug_overlay.handle_keydown(event.key):
                    continue

                if self.game_state == STATE_PLAYING:
                    # Keyboard WASD / Arrow / Tab / 1-3 tab navigation when Character Panel is open
                    if "character" in self.ui_manager.open_panels:
                        if event.key in [pygame.K_a, pygame.K_d, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]:
                            tabs = ["factions", "social", "town", "achievements", "bestiary"]
                            curr_t = getattr(self.ui_manager, "active_char_tab", "factions")
                            curr_i = tabs.index(curr_t) if curr_t in tabs else 0

                            if event.key in [pygame.K_a, pygame.K_LEFT]:
                                self.ui_manager.active_char_tab = tabs[(curr_i - 1) % len(tabs)]
                            elif event.key in [pygame.K_d, pygame.K_RIGHT, pygame.K_TAB]:
                                self.ui_manager.active_char_tab = tabs[(curr_i + 1) % len(tabs)]
                            elif event.key == pygame.K_1:
                                self.ui_manager.active_char_tab = "factions"
                            elif event.key == pygame.K_2:
                                self.ui_manager.active_char_tab = "social"
                            elif event.key == pygame.K_3:
                                self.ui_manager.active_char_tab = "town"
                            elif event.key == pygame.K_4:
                                self.ui_manager.active_char_tab = "achievements"
                            elif event.key == pygame.K_5:
                                self.ui_manager.active_char_tab = "bestiary"
                            self.sound_manager.play_sound("click")
                            continue



                    # Keyboard WASD / Arrow / Enter / 1-4 navigation when Inventory Panel is open
                    if "inventory" in self.ui_manager.open_panels:
                        sel_idx = self.ui_manager.selected_inventory_slot
                        cols = 6

                        total_slots = self.player.inventory.size

                        if event.key in [pygame.K_w, pygame.K_UP]:
                            self.ui_manager.selected_inventory_slot = (sel_idx - cols) % total_slots
                            self.sound_manager.play_sound("click")
                            continue
                        elif event.key in [pygame.K_s, pygame.K_DOWN]:
                            self.ui_manager.selected_inventory_slot = (sel_idx + cols) % total_slots
                            self.sound_manager.play_sound("click")
                            continue
                        elif event.key in [pygame.K_a, pygame.K_LEFT]:
                            self.ui_manager.selected_inventory_slot = (sel_idx - 1) % total_slots
                            self.sound_manager.play_sound("click")
                            continue
                        elif event.key in [pygame.K_d, pygame.K_RIGHT]:
                            self.ui_manager.selected_inventory_slot = (sel_idx + 1) % total_slots
                            self.sound_manager.play_sound("click")
                            continue
                        elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                            # Use / Equip item in currently selected slot!
                            self.player.inventory.use_item(self.ui_manager.selected_inventory_slot, self.player)
                            continue
                        elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]:
                            slot_num = event.key - pygame.K_1 + 1
                            item = self.player.inventory.slots[self.ui_manager.selected_inventory_slot]
                            if item:
                                if item.item_type in ["material", "quest"]:
                                    self.ui_manager.show_banner("CANNOT ASSIGN KEY", f"{item.name} is a material and cannot be bound to hotbar.", (240, 90, 80), duration=2.5)
                                    self.sound_manager.play_sound("hit")
                                else:
                                    self.player.inventory.assign_quick_slot(slot_num, item)
                                    self.ui_manager.show_banner(f"BOUND TO KEY [{slot_num}]", f"{item.name} assigned to Quick-Slot {slot_num}", (60, 220, 100), duration=2.5)
                                    self.sound_manager.play_sound("levelup")
                            continue


                    # Keyboard W/S / Up/Down navigation when Exploration Log (progression) Panel is open
                    if "progression" in self.ui_manager.open_panels:
                        if event.key in [pygame.K_w, pygame.K_s, pygame.K_UP, pygame.K_DOWN]:
                            num_regions = len(self.living_world.progression.regions) if hasattr(self, "living_world") and hasattr(self.living_world, "progression") else 6
                            if event.key in [pygame.K_w, pygame.K_UP]:
                                self.ui_manager.progression_select_idx = (self.ui_manager.progression_select_idx - 1) % max(1, num_regions)
                            else:
                                self.ui_manager.progression_select_idx = (self.ui_manager.progression_select_idx + 1) % max(1, num_regions)
                            self.sound_manager.play_sound("click")
                            continue

                    # Quick-Use Hotbar Item / Skill Keys (1-4, F1-F4) during gameplay when no panel is open
                    if not self.ui_manager.open_panels and event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_F1, pygame.K_F2, pygame.K_F3, pygame.K_F4]:
                        if event.key in [pygame.K_1, pygame.K_F1]: slot_num = 1
                        elif event.key in [pygame.K_2, pygame.K_F2]: slot_num = 2
                        elif event.key in [pygame.K_3, pygame.K_F3]: slot_num = 3
                        else: slot_num = 4

                        skill_names = {1: SKILL_FIREBALL, 2: SKILL_ICE_SPIKE, 3: SKILL_HEALING, 4: SKILL_DASH}
                        target_skill = skill_names.get(slot_num)
                        is_skill_unlocked = self.player.skill_manager.is_unlocked(target_skill) if target_skill else False

                        # If F-key was pressed or if numerical key was pressed and the corresponding skill IS unlocked -> Cast skill
                        if event.key in [pygame.K_F1, pygame.K_F2, pygame.K_F3, pygame.K_F4] or is_skill_unlocked:
                            if self.player.handle_skill_casts_for_slot(slot_num):
                                continue
                        else:
                            # Skill is locked or unavailable -> Use quick slot item!
                            if self.player.inventory.use_quick_slot(slot_num, self.player):
                                item_name = self.player.inventory.quick_slots.get(slot_num, "Item")
                                from rpg.combat import DamageNumber
                                DamageNumber(self.player.rect.center, f"Used {item_name} [{slot_num}]", (100, 220, 255), [self.ui_sprites], size=16)
                                continue


                    # Key panel quick toggles
                    if event.key == pygame.K_i:
                        self.ui_manager.toggle_panel("inventory", self)
                        self.sound_manager.play_sound("click")
                    elif event.key == KEY_CHARACTER:
                        self.ui_manager.toggle_panel("character", self)
                        self.sound_manager.play_sound("click")
                    elif event.key == KEY_QUEST:
                        self.ui_manager.toggle_panel("quests", self)
                        self.sound_manager.play_sound("click")
                    elif event.key == pygame.K_g:
                        self.ui_manager.toggle_panel("crafting", self)
                        self.sound_manager.play_sound("click")
                    elif event.key == pygame.K_r:
                        self.ui_manager.toggle_panel("progression", self)
                        self.sound_manager.play_sound("click")

                    elif event.key == pygame.K_m:
                        self.minimap_enabled = not self.minimap_enabled
                        self.sound_manager.play_sound("click")
                    elif event.key == pygame.K_l:
                        # Debug cheat: gain enough XP to level up instantly
                        self.player.gain_xp(self.player.xp_needed - self.player.xp)
                    elif event.key == KEY_INTERACT:
                        self.handle_interaction()
                    elif event.key == pygame.K_ESCAPE:
                        if self.ui_manager.open_panels:
                            self.ui_manager.close_all_panels()
                            self.sound_manager.play_sound("click")
                        else:
                            # Open pause
                            self.ui_manager.close_all_panels()
                            self.game_state = STATE_PAUSED
                            self.ui_manager.pause_menu_state = "main"
                            self.ui_manager.pause_select_idx = 0
                            self.ui_manager.refresh_slots_metadata()
                            self.sound_manager.play_sound("click")

                elif self.game_state == STATE_MENU:
                    if event.key in [pygame.K_w, pygame.K_UP]:
                        self.ui_manager.menu_select_idx = (self.ui_manager.menu_select_idx - 1) % len(self.ui_manager.menu_options)
                        self.sound_manager.play_sound("click")
                    elif event.key in [pygame.K_s, pygame.K_DOWN]:
                        self.ui_manager.menu_select_idx = (self.ui_manager.menu_select_idx + 1) % len(self.ui_manager.menu_options)
                        self.sound_manager.play_sound("click")
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        self.ui_manager.execute_menu_choice(self.ui_manager.menu_select_idx, self)

                elif self.game_state == STATE_SETTINGS:
                    if event.key in [pygame.K_w, pygame.K_UP]:
                        self.ui_manager.settings_select_idx = (self.ui_manager.settings_select_idx - 1) % len(self.ui_manager.settings_options)
                        self.sound_manager.play_sound("click")
                    elif event.key in [pygame.K_s, pygame.K_DOWN]:
                        self.ui_manager.settings_select_idx = (self.ui_manager.settings_select_idx + 1) % len(self.ui_manager.settings_options)
                        self.sound_manager.play_sound("click")
                    elif event.key in [pygame.K_a, pygame.K_LEFT]:
                        if self.ui_manager.settings_select_idx == 0:
                            self.sound_manager.set_music_volume(self.sound_manager.music_volume - 0.1)
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 1:
                            self.sound_manager.set_sfx_volume(self.sound_manager.sfx_volume - 0.1)
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 2:
                            self.toggle_fullscreen()
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 3:
                            fps_options = [30, 60, 120, 144, 0]
                            curr_idx = fps_options.index(self.target_fps) if self.target_fps in fps_options else 1
                            self.target_fps = fps_options[(curr_idx - 1) % len(fps_options)]
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 4:
                            diff_options = ["explorer", "normal", "veteran", "nightmare"]
                            curr_diff = str(getattr(self, "difficulty_profile", "normal")).lower()
                            curr_i = diff_options.index(curr_diff) if curr_diff in diff_options else 1
                            self.difficulty_profile = diff_options[(curr_i - 1) % len(diff_options)]
                            self.sound_manager.play_sound("click")
                    elif event.key in [pygame.K_d, pygame.K_RIGHT]:
                        if self.ui_manager.settings_select_idx == 0:
                            self.sound_manager.set_music_volume(self.sound_manager.music_volume + 0.1)
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 1:
                            self.sound_manager.set_sfx_volume(self.sound_manager.sfx_volume + 0.1)
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 2:
                            self.toggle_fullscreen()
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 3:
                            fps_options = [30, 60, 120, 144, 0]
                            curr_idx = fps_options.index(self.target_fps) if self.target_fps in fps_options else 1
                            self.target_fps = fps_options[(curr_idx + 1) % len(fps_options)]
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 4:
                            diff_options = ["explorer", "normal", "veteran", "nightmare"]
                            curr_diff = str(getattr(self, "difficulty_profile", "normal")).lower()
                            curr_i = diff_options.index(curr_diff) if curr_diff in diff_options else 1
                            self.difficulty_profile = diff_options[(curr_i + 1) % len(diff_options)]
                            self.sound_manager.play_sound("click")
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        if self.ui_manager.settings_select_idx == 2:
                            self.toggle_fullscreen()
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 3:
                            fps_options = [30, 60, 120, 144, 0]
                            curr_idx = fps_options.index(self.target_fps) if self.target_fps in fps_options else 1
                            self.target_fps = fps_options[(curr_idx + 1) % len(fps_options)]
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 4:
                            diff_options = ["explorer", "normal", "veteran", "nightmare"]
                            curr_diff = str(getattr(self, "difficulty_profile", "normal")).lower()
                            curr_i = diff_options.index(curr_diff) if curr_diff in diff_options else 1
                            self.difficulty_profile = diff_options[(curr_i + 1) % len(diff_options)]
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 5:
                            self.sound_manager.play_sound("click")
                            self.return_from_settings()
                    elif event.key == pygame.K_ESCAPE:
                        self.sound_manager.play_sound("click")
                        self.return_from_settings()

                elif self.game_state == STATE_TUTORIAL:
                    if event.key in [pygame.K_a, pygame.K_LEFT]:
                        self.ui_manager.tutorial_page_idx = (self.ui_manager.tutorial_page_idx - 1) % 4
                        self.sound_manager.play_sound("click")
                    elif event.key in [pygame.K_d, pygame.K_RIGHT, pygame.K_TAB]:
                        self.ui_manager.tutorial_page_idx = (self.ui_manager.tutorial_page_idx + 1) % 4
                        self.sound_manager.play_sound("click")
                    elif event.key in [pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE]:
                        self.sound_manager.play_sound("click")
                        self.game_state = STATE_MENU

                elif self.game_state == STATE_PAUSED:
                    # Rename Profile input typing mode
                    if self.ui_manager.pause_menu_state == "rename_input":
                        if event.key == pygame.K_ESCAPE:
                            self.ui_manager.pause_menu_state = "slot_actions"
                            self.ui_manager.pause_select_idx = 1
                            self.sound_manager.play_sound("click")
                        elif event.key == pygame.K_RETURN:
                            new_name = self.ui_manager.rename_input_text.strip()
                            if new_name:
                                from rpg.save import SaveSystem
                                SaveSystem.rename_slot(self.ui_manager.selected_slot_idx + 1, new_name)
                                self.ui_manager.refresh_slots_metadata()
                            self.ui_manager.pause_menu_state = "slot_actions"
                            self.ui_manager.pause_select_idx = 1
                            self.sound_manager.play_sound("levelup")
                        elif event.key == pygame.K_BACKSPACE:
                            self.ui_manager.rename_input_text = self.ui_manager.rename_input_text[:-1]
                            self.sound_manager.play_sound("click")
                        else:
                            # Append printable char
                            char = event.unicode
                            if char and char.isprintable() and len(self.ui_manager.rename_input_text) < 16:
                                self.ui_manager.rename_input_text += char
                                self.sound_manager.play_sound("click")
                        continue

                    # Dynamic wrap size
                    p_state = self.ui_manager.pause_menu_state
                    if p_state == "main":
                        opts_len = len(self.ui_manager.pause_options)
                    elif p_state in ["save_slots", "load_slots"]:
                        opts_len = 4
                    elif p_state == "slot_actions":
                        meta = self.ui_manager.slots_meta.get(self.ui_manager.selected_slot_idx + 1, {"exists": False})
                        if self.ui_manager.pause_action_source == "save":
                            opts_len = 2 if not meta["exists"] else 4
                        else:
                            opts_len = 1 if not meta["exists"] else 4



                    else:
                        opts_len = 1

                    if event.key in [pygame.K_w, pygame.K_UP]:
                        self.ui_manager.pause_select_idx = (self.ui_manager.pause_select_idx - 1) % opts_len
                        self.sound_manager.play_sound("click")
                    elif event.key in [pygame.K_s, pygame.K_DOWN]:
                        self.ui_manager.pause_select_idx = (self.ui_manager.pause_select_idx + 1) % opts_len
                        self.sound_manager.play_sound("click")
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        self.ui_manager.execute_pause_choice(self.ui_manager.pause_select_idx, self)
                    elif event.key == pygame.K_ESCAPE:
                        if p_state in ["save_slots", "load_slots"]:
                            if getattr(self, "_from_main_menu", False):
                                self.game_state = STATE_MENU
                            else:
                                self.ui_manager.pause_menu_state = "main"
                                self.ui_manager.pause_select_idx = 1 if p_state == "save_slots" else 2
                            self.sound_manager.play_sound("click")
                        elif p_state == "slot_actions":
                            self.ui_manager.pause_menu_state = self.ui_manager.pause_action_source + "_slots"
                            self.ui_manager.pause_select_idx = self.ui_manager.selected_slot_idx
                            self.sound_manager.play_sound("click")
                        else:
                            if getattr(self, "_from_main_menu", False):
                                self.game_state = STATE_MENU
                            else:
                                self.game_state = STATE_PLAYING
                            self.sound_manager.play_sound("click")

                elif self.game_state == STATE_DIALOGUE:
                    if event.key in [pygame.K_SPACE, pygame.K_RETURN, KEY_INTERACT]:
                        prev_st = self.game_state
                        self.dialogue_manager.advance()
                        # Only revert if dialogue closed and callback didn't transition state (e.g. to STATE_SHOP)
                        if not self.dialogue_manager.current_node and self.game_state == prev_st:
                            self.game_state = STATE_PLAYING
                    elif event.key in [pygame.K_s, pygame.K_DOWN]:
                        self.dialogue_manager.select_next_choice()
                    elif event.key in [pygame.K_w, pygame.K_UP]:
                        self.dialogue_manager.select_prev_choice()
                    elif event.key == pygame.K_ESCAPE:
                        self.dialogue_manager.close()
                        self.game_state = STATE_PLAYING

                elif self.game_state == STATE_SHOP:
                    if event.key == pygame.K_ESCAPE:
                        self.game_state = STATE_PLAYING
                        self.sound_manager.play_sound("click")

                elif self.game_state == STATE_GAME_OVER:
                    if event.key == pygame.K_r:
                        self.respawn_player()
                    elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        # Load last save or restart
                        from rpg.save import SaveSystem
                        if not SaveSystem.load_game(self.player, self.quest_manager, self.world_manager):
                            self.start_new_game()
                        else:
                            self.game_state = STATE_PLAYING

                        # Ensure player state is alive and responsive
                        self.player.state = "idle"
                        self.player.action_timer = 0.0
                        self.player.frame_index = 0.0
                        self.player.is_invincible = False
                        if self.player.hp <= 0:
                            self.player.hp = self.player.max_hp
                    elif event.key == pygame.K_ESCAPE:
                        self.game_state = STATE_MENU


                elif self.game_state == STATE_VICTORY:
                    if event.key in [pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN]:
                        self.game_state = STATE_MENU

            elif event.type == pygame.MOUSEBUTTONDOWN:
                is_right = (event.button in [2, 3] or (event.button == 1 and bool(pygame.key.get_mods() & pygame.KMOD_CTRL)))
                if is_right:
                    self.ui_manager.handle_click(event.pos, self, right_click=True)
                elif event.button == 1:
                    # Check minimap fast travel click
                    if getattr(self, "minimap_enabled", True) and self.game_state == STATE_PLAYING and not self.ui_manager.open_panels:
                        if self.minimap.handle_click(event.pos, self):
                            continue
                    self.ui_manager.handle_click(event.pos, self, right_click=False)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    # Complete drag & drop
                    self.handle_drag_release(event.pos)

    def handle_drag_release(self, pos: Tuple[int, int]) -> None:
        """Finishes drag and drop items in slots."""
        if not self.player.inventory.dragged_item:
            return

        target_idx = -1
        # Find hovered slot
        for rect, idx in self.ui_manager.slot_rects["inventory"]:
            if rect.collidepoint(pos):
                target_idx = idx
                break

        if target_idx != -1:
            self.player.inventory.stop_drag(target_idx)
        else:
            self.player.inventory.cancel_drag()

    def handle_interaction(self) -> None:
        """Looks for nearby NPCs or closed chests to trigger interactions."""
        # 1. Check chests
        for chest in self.chests:
            if not chest.is_open:
                # Within 48 pixels range
                dist = (self.player.pos - chest.rect.center).length()
                if dist <= 56.0:
                    if chest.open_chest(self.player):
                        # Register in world manager opened registry
                        map_name = self.world_manager.current_map_name
                        self.world_manager.chests_opened[map_name].append(tuple(chest.grid_pos))
                        return

        # 2. Check NPCs range
        for npc in self.npcs:
            if npc.check_interaction_range(self.player.pos):
                npc.interact()
                return

        # 3. Check Waypoint Obelisks range
        for obelisk in self.waypoint_obelisks:
            if obelisk.check_interaction_range(self.player.pos):
                obelisk.interact(self.player)
                return

    def update(self) -> None:
        """Ticks recovery pools, triggers camera positioning, and checks portal collisions."""
        self.services.profiling.start_sample("update")
        # Limit frame rate
        self.dt = self.clock.tick(self.target_fps) / 1000.0

        # Process inputs
        self.process_events()

        # Play main menu music when in menu state
        if self.game_state in [STATE_MENU, STATE_TUTORIAL]:
            self.sound_manager.play_music("menu_music")

        # Skip updates if in menu, paused, or victory splash
        if self.game_state in [STATE_MENU, STATE_PAUSED, STATE_GAME_OVER, STATE_VICTORY]:
            self.services.profiling.end_sample("update")
            return



        # Visual Flash overlays updates
        self.effects_manager.update(self.dt)

        # Hit-Stop freeze frames (suspends movement updating)
        if self.effects_manager.hit_stop_timer > 0:
            return

        # Update NPCs and Waypoints range indicators
        for npc in self.npcs:
            npc.check_interaction_range(self.player.pos)
        for obelisk in self.waypoint_obelisks:
            obelisk.check_interaction_range(self.player.pos)

        # 1. Update Game dialogue
        if self.game_state == STATE_DIALOGUE:
            self.dialogue_manager.update(self.dt)
            # Freeze player movements during conversation
            self.player.velocity.x = 0
            self.player.velocity.y = 0
            self.player.animate(self.dt)
            return

        # 2. Update player casting
        self.player.handle_skill_casts(self.input_handler)

        # 3. Update all level sprites
        self.visible_sprites.update(self.dt)
        self.projectiles.update(self.dt)
        self.ui_sprites.update(self.dt)

        # 3b. Check quest completions and grant rewards
        completed_quests = self.quest_manager.check_completable_quests(self.player)
        for cq in completed_quests:
            from rpg.celebration import CelebrationTier
            self.ui_manager.celebration.trigger_celebration(
                CelebrationTier.MEDIUM,
                f"QUEST COMPLETED: {cq.title.upper()}!",
                "Earned Gold, XP, and NPC Trust!",
                event_bus=self.event_bus
            )
            self.event_bus.emit("quest_completed", quest_id=cq.id)

        # 3c. Update central Living World simulation orchestrator
        self.living_world.update(self.dt, self.player, self.world_manager, self.visible_sprites)

        # 4. Update weather particles
        self.weather.update(self.particles, self.camera.get_offset(), self.dt, self.world_state)
        self.particles.update(self.dt)

        # 5. Update ambient cycle
        self.lighting.update(self.dt, self.world_state)

        # 6. Check Portal level transitions with Centralized ProgressionManager
        player_hb = self.player.hitbox
        for portal in self.world_manager.current_map_data.get("portals", []):
            if player_hb.colliderect(portal["rect"]):
                target = portal["target_map"]
                spawn_coords = portal["target_spawn"]

                # Evaluate regional access via ProgressionManager (Rule 1)
                prog_mgr = self.living_world.progression
                can_access, clue, reg_state = prog_mgr.can_access_region(target, self)

                if not can_access:
                    # Push back player slightly to prevent stuck collision loop
                    push_dir = pygame.math.Vector2(self.player.pos - portal["rect"].center)
                    if push_dir.length_squared() > 0:
                        push_dir = push_dir.normalize()
                        self.player.pos += push_dir * 22.0
                        self.player.hitbox.center = (int(self.player.pos.x), int(self.player.pos.y))
                        self.player.rect.center = self.player.hitbox.center

                    target_prof = prog_mgr.regions.get(target)
                    reg_name = target_prof.name if target_prof else target.upper()

                    # Trigger Screen-Centered Banner Notification (100% visible on any screen location)
                    self.ui_manager.show_banner(
                        title=f"REGION LOCKED: {reg_name.upper()}",
                        subtitle=clue,
                        color=(240, 140, 30),
                        duration=4.5
                    )
                    self.sound_manager.play_sound("click")
                    break

                # If state was AVAILABLE, unlock region & trigger living celebration!
                if reg_state.value == "available":
                    prog_mgr.unlock_region(target, self, self.event_bus)
                    target_prof = prog_mgr.regions.get(target)
                    reg_name = target_prof.name if target_prof else target.upper()

                    from rpg.celebration import CelebrationTier
                    self.ui_manager.celebration.trigger_celebration(
                        CelebrationTier.LARGE,
                        f"REGION UNLOCKED: {reg_name.upper()}!",
                        f"The path to {reg_name} is now open and accessible.",
                        event_bus=self.event_bus
                    )

                # Fade transition flash
                self.effects_manager.trigger_flash((255, 255, 255), 300)
                self.sound_manager.play_sound("magic")

                # Load Map
                self.world_manager.load_map(target, self.player, portal_spawn=True, portal_coord=spawn_coords)
                self.services.reset_services()
                break


        # 7. Check Boss Defeat condition to sync registry
        for enemy in self.enemies:
            if enemy.name == "Shadow Overlord" and enemy.hp <= 0:
                self.world_manager.boss_defeated = True

        # 8. Focus camera tracking on player
        self.camera.update(self.player.pos, self.dt)
        self.services.profiling.end_sample("update")

    def draw(self) -> None:
        """Draws background tiles, sorted sprites, dynamic lights and interfaces overlays."""
        self.services.profiling.start_sample("draw")
        # 1. Clear display
        self.screen.fill(COLOR_BLACK)


        # Draw game world when playing, paused, dialogue, shop, menu or tutorial
        if self.game_state in [STATE_PLAYING, STATE_PAUSED, STATE_DIALOGUE, STATE_SHOP, STATE_MENU, STATE_TUTORIAL]:
            from rpg.animation import tile_assets
            grid = self.world_manager.current_map_grid

            if grid and len(grid) > 0:
                map_h = len(grid)
                map_w = len(grid[0]) if map_h > 0 else 0

                if self.game_state in [STATE_MENU, STATE_TUTORIAL]:
                    # Slowly pan camera horizontally for cinematic menu background
                    menu_time = pygame.time.get_ticks() / 80.0
                    pan_max = max(1, map_w * TILE_SIZE - SCREEN_WIDTH)
                    camera_offset = pygame.math.Vector2(menu_time % pan_max, 160)
                else:
                    camera_offset = self.camera.get_offset()

                # Draw only tiles visible in view boundary (Camera Culling Optimization)
                start_col = max(0, int(camera_offset.x // TILE_SIZE))
                end_col = min(map_w - 1, int((camera_offset.x + SCREEN_WIDTH) // TILE_SIZE))
                start_row = max(0, int(camera_offset.y // TILE_SIZE))
                end_row = min(map_h - 1, int((camera_offset.y + SCREEN_HEIGHT) // TILE_SIZE))

                for r in range(start_row, min(end_row + 1, map_h)):
                    for c in range(start_col, min(end_col + 1, map_w)):
                        tile_type = grid[r][c]
                        # Map tree trunks to grass underneath, since tree is a separate layered sprite
                        if tile_type in ["tree", "chest_closed", "chest_open"]:
                            tile_surf = tile_assets.get("grass")
                        else:
                            tile_surf = tile_assets.get(tile_type, tile_assets["grass"])

                        sx = int(c * TILE_SIZE - camera_offset.x)
                        sy = int(r * TILE_SIZE - camera_offset.y)
                        self.screen.blit(tile_surf, (sx, sy))

            # 2. Draw YSorted Sprites (Player, enemies, chests, NPCs, projectiles)
            self.visible_sprites.draw_sorted(self.screen, camera_offset)

            # Render NPCs indicators above heads
            for sprite in self.visible_sprites.sprites():
                if hasattr(sprite, "draw_indicator"):
                    sprite.draw_indicator(self.screen, camera_offset)

            # 3. Draw particles
            self.particles.draw(self.screen, camera_offset)

            # 4. Draw night light mask overlays
            self.lighting.draw_lighting(self.screen, camera_offset, self)

            # 5. Draw weather overlay (sky tints, raindrops, ripples, snowflakes, leaves, fog)
            self.weather.draw_weather_overlay(self.screen, camera_offset)

            # 6. Draw floating combat damage indicators
            self.ui_sprites.draw_sorted(self.screen, camera_offset)

            # Draw cinematic dark menu overlay for main menu & tutorial screens
            if self.game_state in [STATE_MENU, STATE_TUTORIAL]:
                menu_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                menu_overlay.fill((12, 14, 24, 185))  # Smooth deep dark translucent tint
                self.screen.blit(menu_overlay, (0, 0))

        # 7. UI Overlay Panel layer
        self.ui_manager.draw(self.screen, self)

        # 8. Render damage flashes on top of UI
        self.effects_manager.draw_flash(self.screen)

        # 9. Render Developer Debug Overlay (F9, F10, F11)
        self.debug_overlay.draw(self.screen, self)

        self.services.profiling.end_sample("draw")
        # Flip display buffer
        pygame.display.flip()


    @property
    def enemies(self) -> List[Any]:
        """Provides references to active list of map enemies."""
        return self._enemies_list

    @enemies.setter
    def enemies(self, val: List[Any]) -> None:
        self._enemies_list = val

    def trigger_hit_stop(self, duration: float) -> None:
        """Trigger update freezes (e.g. from hit stops)."""
        self.effects_manager.trigger_hit_stop(duration * 1000.0)
