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
    STATE_TUTORIAL, MAP_VILLAGE, COLOR_BLACK
)
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT, TARGET_FPS, TILE_SIZE, GRID_WIDTH, GRID_HEIGHT
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

class Game:
    """
    Main engine orchestrator connecting graphics, audio, inputs, and states.
    """
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.dt = 0.0
        self.is_fullscreen = False
        
        # State machine
        self.game_state = STATE_MENU
        
        # Initialize Core Subsystems
        self.event_bus = EventBus()
        self.living_world = LivingWorldManager(self.event_bus)
        
        # Accessor aliases for backward compatibility
        self.world_state = self.living_world.world_state
        self.ecology = self.living_world.ecology
        
        self.factions = FactionManager()
        self.factions.register_event_listeners(self.event_bus)
        
        self.npc_memory = NPCMemoryManager()
        self.npc_memory.register_event_listeners(self.event_bus)
        
        self.sound_manager = SoundManager()
        self.input_handler = InputHandler()
        self.ui_manager = UIManager()
        self.particles = ParticleSystem()
        self.weather = WeatherSystem()
        self.lighting = LightingSystem()
        self.effects_manager = EffectsManager()
        self.quest_manager = QuestManager()
        self.dialogue_manager = DialogueManager()
        self.dialogue_manager.game = self
        self.world_manager = WorldManager()
        
        # Sprite groups
        self.visible_sprites = YSortedGroup()
        self.projectiles = pygame.sprite.Group()
        self.dropped_items = pygame.sprite.Group()
        self.chests = pygame.sprite.Group()
        self.npcs = pygame.sprite.Group()
        self.ui_sprites = YSortedGroup()  # Renders floating combat texts
        self._enemies_list = []

        # Initialize Player (Spawned at center of Village)
        self.player = Player((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), [self.visible_sprites], self.sound_manager, self.particles)
        self.player.game = self
        
        # Minimap & Camera
        self.minimap = Minimap()
        self.camera = Camera(GRID_WIDTH * TILE_SIZE, GRID_HEIGHT * TILE_SIZE)
        self.minimap_enabled = True
        
        # Mythos Inheritance Engine (Warisan Mitos & Legacy)
        from rpg.mythos import MythosManager
        self.mythos_manager = MythosManager()
        
        # Load initial village map for menu background
        self.world_manager.load_map(MAP_VILLAGE, self.player, portal_spawn=False)

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

    def start_new_game(self) -> None:
        """Resets variables and loads the starting Village map."""
        self.world_manager.boss_defeated = False
        self.world_manager.chests_opened.clear()
        
        # Reset player variables
        self.player.level = 1
        self.player.xp = 0
        self.player.xp_needed = 100
        self.player.gold = 50
        self.player.hp = self.player.base_max_hp
        self.player.mana = self.player.base_max_mana
        self.player.stamina = self.player.base_max_stamina
        
        # Equip defaults
        self.player.inventory.slots = [None] * self.player.inventory.size
        self.player.equipment.slots = {k: None for k in self.player.equipment.slots}
        self.player.add_starter_items()
        self.player.equipment.recalculate_player_stats(self.player)
        
        self.player.skill_manager = type(self.player.skill_manager)()  # Fresh skills
        self.player.skill_manager.check_unlocks(self.player.level)
        
        # Reset quests
        self.quest_manager = type(self.quest_manager)()
        
        self.particles.clear()
        self.ui_manager.close_all_panels()
        
        # Load map and switch state to PLAYING
        self.world_manager.load_map(MAP_VILLAGE, self.player, portal_spawn=False)
        self.game_state = STATE_PLAYING

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
                if self.game_state == STATE_PLAYING:
                    # Key panel quick toggles
                    if event.key == pygame.K_i:
                        self.ui_manager.toggle_panel("inventory")
                        self.sound_manager.play_sound("click")
                    elif event.key == pygame.K_c:
                        self.ui_manager.toggle_panel("character")
                        self.sound_manager.play_sound("click")
                    elif event.key == pygame.K_q:
                        self.ui_manager.toggle_panel("quests")
                        self.sound_manager.play_sound("click")
                    elif event.key == pygame.K_g:
                        self.ui_manager.toggle_panel("crafting")
                        self.sound_manager.play_sound("click")
                    elif event.key == pygame.K_m:
                        self.minimap_enabled = not self.minimap_enabled
                        self.sound_manager.play_sound("click")
                    elif event.key == pygame.K_l:
                        # Debug cheat: gain enough XP to level up instantly
                        self.player.gain_xp(self.player.xp_needed - self.player.xp)
                    elif event.key == pygame.K_e:
                        self.handle_interaction()
                    elif event.key == pygame.K_ESCAPE:
                        # Open pause
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
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        if self.ui_manager.settings_select_idx == 2:
                            self.toggle_fullscreen()
                            self.sound_manager.play_sound("click")
                        elif self.ui_manager.settings_select_idx == 3:
                            self.sound_manager.play_sound("click")
                            self.return_from_settings()
                    elif event.key == pygame.K_ESCAPE:
                        self.sound_manager.play_sound("click")
                        self.return_from_settings()
                        
                elif self.game_state == STATE_TUTORIAL:
                    if event.key in [pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE]:
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
                    if event.key in [pygame.K_SPACE, pygame.K_RETURN, pygame.K_e]:
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
                    if event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        # Load last save
                        from rpg.save import SaveSystem
                        if not SaveSystem.load_game(self.player, self.quest_manager, self.world_manager):
                            # Default back to start
                            self.start_new_game()
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

    def update(self) -> None:
        """Ticks recovery pools, triggers camera positioning, and checks portal collisions."""
        # Limit frame rate
        self.dt = self.clock.tick(TARGET_FPS) / 1000.0
        
        # Process inputs
        self.process_events()
        
        # Skip updates if in menu, paused, or victory splash
        if self.game_state in [STATE_MENU, STATE_PAUSED, STATE_GAME_OVER, STATE_VICTORY]:
            return

        # Visual Flash overlays updates
        self.effects_manager.update(self.dt)

        # Hit-Stop freeze frames (suspends movement updating)
        if self.effects_manager.hit_stop_timer > 0:
            return

        # Update NPCs range indicators
        for npc in self.npcs:
            npc.check_interaction_range(self.player.pos)

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
            from rpg.combat import DamageNumber
            DamageNumber(self.player.rect.center, f"Quest Completed: {cq.title}!", (255, 215, 0), [self.ui_sprites], size=26)
            self.event_bus.emit("quest_completed", quest_id=cq.id)
        
        # 3c. Update central Living World simulation orchestrator
        self.living_world.update(self.dt, self.player, self.world_manager, self.visible_sprites)
        
        # 4. Update weather particles
        self.weather.update(self.particles, self.camera.get_offset(), self.dt, self.world_state)
        self.particles.update(self.dt)
        
        # 5. Update ambient cycle
        self.lighting.update(self.dt, self.world_state)

        # 6. Check Portal level transitions
        player_hb = self.player.hitbox
        for portal in self.world_manager.current_map_data.get("portals", []):
            if player_hb.colliderect(portal["rect"]):
                target = portal["target_map"]
                spawn_coords = portal["target_spawn"]
                
                # Fade transition flash
                self.effects_manager.trigger_flash((255, 255, 255), 300)
                self.sound_manager.play_sound("magic")
                
                # Load Map
                self.world_manager.load_map(target, self.player, portal_spawn=True, portal_coord=spawn_coords)
                break

        # 7. Check Boss Defeat condition to sync registry
        for enemy in self.enemies:
            if enemy.name == "Shadow Overlord" and enemy.hp <= 0:
                self.world_manager.boss_defeated = True

        # 8. Focus camera tracking on player
        self.camera.update(self.player.pos, self.dt)

    def draw(self) -> None:
        """Draws background tiles, sorted sprites, dynamic lights and interfaces overlays."""
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

            # 4. Draw weather overlay
            self.weather.draw_fog_overlay(self.screen)

            # 5. Draw night light mask overlays
            self.lighting.draw_lighting(self.screen, camera_offset, self)

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
