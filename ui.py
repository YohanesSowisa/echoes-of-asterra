"""
Echoes of Asterra - User Interface Manager
Manages all game states overlays: HUD, Menus (Main, Settings, Pause), RPG panels
(Inventory, Character Stats, Quest Log, Crafting Anvil), Shop trade UI, and Victory / Game Over.
"""
import pygame
from typing import Dict, List, Tuple, Set, Optional, Any
from rpg.constants import (
    COLOR_BLACK, COLOR_WHITE, COLOR_GRAY, COLOR_DARK_GRAY, COLOR_LIGHT_GRAY,
    COLOR_RED, COLOR_GREEN, COLOR_YELLOW,
    COLOR_UI_BG, COLOR_UI_BORDER, COLOR_UI_TEXT, COLOR_UI_HIGHLIGHT,
    COLOR_BAR_HP, COLOR_BAR_MANA, COLOR_BAR_STAMINA, COLOR_BAR_EXP,
    STATE_MENU, STATE_PLAYING, STATE_PAUSED, STATE_GAME_OVER, STATE_VICTORY, STATE_DIALOGUE, STATE_SHOP, STATE_SETTINGS,
    STATE_TUTORIAL,
    RARITY_COLORS, SKILL_FIREBALL, SKILL_ICE_SPIKE, SKILL_HEALING, SKILL_DASH
)
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from rpg.items import create_item
from rpg.crafting import CRAFTING_RECIPES, CraftingSystem

class UIManager:
    """
    Main user interface coordinator. Draws overlays and catches click events
    to trigger inventory shifts, crafts, trades, and menu toggles.
    """
    def __init__(self) -> None:
        import os
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(BASE_DIR, "assets", "fonts", "game_font.ttf")
        
        pygame.font.init()
        
        if os.path.exists(font_path):
            try:
                def load_custom_font(size: int, bold: bool = False) -> pygame.font.Font:
                    f = pygame.font.Font(font_path, size)
                    if bold:
                        f.set_bold(True)
                    return f
                self.fonts = {
                    "small": load_custom_font(12),
                    "medium": load_custom_font(15, bold=True),
                    "large": load_custom_font(24, bold=True),
                    "title": load_custom_font(36, bold=True)
                }
            except Exception as e:
                print(f"Font: Failed to load TTF from {font_path}. Falling back. Details: {e}")
                self._load_fallback_fonts()
        else:
            self._load_fallback_fonts()
            
        # Panel visibility set
        self.open_panels: Set[str] = set()
        
        # Shop configurations
        self.shop_goods = ["Red Potion", "Blue Potion", "Baked Bread", "Steel Blade", "Wooden Shield"]
        self.shop_prices = {
            "Red Potion": (15, 5),      # (Buy, Sell)
            "Blue Potion": (20, 7),
            "Baked Bread": (10, 3),
            "Steel Blade": (100, 30),
            "Wooden Shield": (40, 12),
            "Iron Ore": (0, 10),        # Silas only buys these
            "Oak Wood": (0, 6),
            "Forest Apple": (0, 3),
            "Asterra Heart": (0, 150)
        }
        self.shop_mode = "buy" # "buy" or "sell"
        self.shop_select_idx = 0

        # Menu selections
        self.menu_select_idx = 0
        self.menu_options = ["New Adventure", "Load Adventure", "Tutorial", "Settings", "Quit Game"]
        
        self.pause_select_idx = 0
        self.pause_options = ["Resume", "Save Game", "Load Game", "Settings", "Main Menu"]
        self.pause_menu_state = "main"
        self.pause_action_source = "save"
        self.selected_slot_idx = 0
        self.rename_input_text = ""
        self.slots_meta = {}

        self.settings_select_idx = 0
        self.settings_options = ["Music Volume", "SFX Volume", "Display Mode", "Back to Menu"]

        # Tooltip item hovering cache
        self.hovered_item: Optional[Any] = None
        self.hovered_rect: Optional[pygame.Rect] = None

        # Drag slot positions cache
        self.slot_rects: Dict[str, List[Any]] = {
            "inventory": [],
            "equipment": [],
            "shop": [],
            "quest_panel": []
        }

        # Double click tracker
        self.last_click_time = 0
        self.last_click_slot = -1

    def get_item_sell_price(self, item: Any) -> int:
        """Returns the sell gold value for an item, with fallback calculation for any item in the game."""
        if not item:
            return 0
            
        # Check explicit shop prices table first
        if hasattr(item, "name") and item.name in self.shop_prices:
            _, sell_price = self.shop_prices[item.name]
            if sell_price > 0:
                return sell_price

        # Fallback calculation based on rarity and stats
        from rpg.constants import RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY
        base_val = 5
        rarity_multipliers = {
            RARITY_COMMON: 1,
            RARITY_UNCOMMON: 2,
            RARITY_RARE: 4,
            RARITY_EPIC: 8,
            RARITY_LEGENDARY: 15
        }
        mult = rarity_multipliers.get(getattr(item, "rarity", RARITY_COMMON), 1)
        
        # Add value for stats
        stats_dict = getattr(item, "stats", {})
        stat_val = sum(stats_dict.values()) * 3 if stats_dict else 0
        
        return max(2, (base_val + stat_val) * mult)

    def refresh_slots_metadata(self) -> None:
        """Reads metadata for all slots from disk and caches it in memory."""
        from rpg.save import SaveSystem
        self.slots_meta = {
            1: SaveSystem.get_slot_meta(1),
            2: SaveSystem.get_slot_meta(2),
            3: SaveSystem.get_slot_meta(3)
        }

    def _load_fallback_fonts(self) -> None:
        """Loads Arial system fonts as a fallback."""
        self.fonts = {
            "small": pygame.font.SysFont("Arial", 14),
            "medium": pygame.font.SysFont("Arial", 18, bold=True),
            "large": pygame.font.SysFont("Arial", 28, bold=True),
            "title": pygame.font.SysFont("Arial", 48, bold=True)
        }

    def toggle_panel(self, panel_name: str) -> None:
        """Toggles visibility of an RPG panel (inventory, character, quests, crafting)."""
        if panel_name in self.open_panels:
            self.open_panels.remove(panel_name)
        else:
            self.open_panels.add(panel_name)

    def close_all_panels(self) -> None:
        """Closes all active RPG panels."""
        self.open_panels.clear()

    def draw(self, surface: pygame.Surface, game: Any) -> None:
        """
        Coordinates screen drawings based on the active game state.
        """
        state = game.game_state
        
        if state == STATE_MENU:
            self.draw_main_menu(surface)
        elif state == STATE_SETTINGS:
            self.draw_settings_menu(surface, game)
        elif state == STATE_TUTORIAL:
            self.draw_tutorial(surface)
        elif state == STATE_PAUSED:
            # Draw game behind and draw pause panel on top
            self.draw_gameplay_layers(surface, game)
            self.draw_pause_menu(surface)
        elif state == STATE_GAME_OVER:
            self.draw_game_over(surface)
        elif state == STATE_VICTORY:
            self.draw_victory(surface)
        elif state == STATE_PLAYING or state == STATE_DIALOGUE or state == STATE_SHOP:
            self.draw_gameplay_layers(surface, game)

    def draw_gameplay_layers(self, surface: pygame.Surface, game: Any) -> None:
        """Renders standard HUD, minimap, dialogue boxes, shops, and active panels."""
        # 1. Base HUD
        self.draw_hud(surface, game.player, game)
        
        # 2. Minimap (if toggled)
        if game.minimap_enabled:
            game.minimap.draw(surface, game)
            
        # 2b. Active Quest Tracker Widget
        self.draw_quest_tracker_widget(surface, game)
            
        # 3. Active UI Panels
        self.slot_rects["inventory"].clear()
        self.slot_rects["equipment"].clear()
        self.hovered_item = None
        
        if "inventory" in self.open_panels:
            self.draw_inventory_panel(surface, game.player)
        if "character" in self.open_panels:
            self.draw_character_panel(surface, game.player)
        if "quests" in self.open_panels:
            self.draw_quests_panel(surface, game.quest_manager)
        if "crafting" in self.open_panels:
            self.draw_crafting_panel(surface, game.player)

        # 4. Dialogue Box
        if game.game_state == STATE_DIALOGUE:
            self.draw_dialogue_box(surface, game.dialogue_manager)
            
        # 5. Shop Interface
        elif game.game_state == STATE_SHOP:
            self.draw_shop_interface(surface, game.player)

        # 6. Render dragged item outline on top of everything
        if game.player.inventory.dragged_item:
            m_pos = pygame.mouse.get_pos()
            icon = pygame.transform.scale(game.player.inventory.dragged_item.icon, (36, 36))
            surface.blit(icon, (m_pos[0] - 18, m_pos[1] - 18))

        # 7. Render Tooltip popup on hover
        if self.hovered_item:
            self.draw_tooltip(surface, self.hovered_item, pygame.mouse.get_pos())

    # --- BASE HUD RENDER ---

    def draw_hud(self, surface: pygame.Surface, player: Any, game: Any = None) -> None:
        """Renders standard top-left health/mana bars and bottom hotkeys."""
        # HUD Panel background
        bg_bar = pygame.Surface((SCREEN_WIDTH, 80))
        bg_bar.fill((20, 22, 28))
        pygame.draw.line(bg_bar, COLOR_UI_BORDER, (0, 79), (SCREEN_WIDTH, 79), 2)
        surface.blit(bg_bar, (0, 0))

        # 1. HP Bar
        self._draw_hud_bar(surface, 20, 16, 200, 16, player.hp, player.max_hp, COLOR_BAR_HP, "HP")
        # 2. Mana Bar
        self._draw_hud_bar(surface, 20, 38, 200, 12, player.mana, player.max_mana, COLOR_BAR_MANA, "MP")
        # 3. Stamina Bar
        self._draw_hud_bar(surface, 20, 56, 200, 12, player.stamina, player.max_stamina, COLOR_BAR_STAMINA, "STAM")

        # 4. XP Bar (faded thin strip along very top of screen)
        xp_ratio = player.xp / max(1, player.xp_needed)
        pygame.draw.rect(surface, (40, 20, 40), (0, 0, SCREEN_WIDTH, 4))
        pygame.draw.rect(surface, COLOR_BAR_EXP, (0, 0, int(SCREEN_WIDTH * xp_ratio), 4))

        # 5. Level & Gold Text
        lvl_txt = self.fonts["medium"].render(f"Level {player.level}", True, COLOR_WHITE)
        gold_txt = self.fonts["medium"].render(f"Gold: {player.gold}g", True, COLOR_YELLOW)
        surface.blit(lvl_txt, (240, 14))
        surface.blit(gold_txt, (240, 36))

        # 5b. Current Map Location Name
        if game and hasattr(game, 'world_manager'):
            map_name = game.world_manager.current_map_name.replace("_", " ").title()
            depth_str = f" (Floor {game.world_manager.dungeon_depth})" if game.world_manager.current_map_name == "crypt" else ""
            loc_txt = self.fonts["small"].render(f">> {map_name}{depth_str}", True, (180, 200, 220))
            surface.blit(loc_txt, (240, 56))

        # 5c. Harvest Moon / Stardew Valley Time & Season HUD Clock Card
        self._draw_harvest_moon_clock(surface, game)

        # 5d. Combo Counter overlay
        if getattr(player, "combo_count", 0) > 1 and getattr(player, "combo_timer", 0) > 0:
            cb_str = f"COMBO x{player.combo_count}!"
            cb_lbl = self.fonts["large"].render(cb_str, True, COLOR_YELLOW)
            surface.blit(cb_lbl, (SCREEN_WIDTH // 2 - cb_lbl.get_width() // 2, 88))

        # 6. Quick Skill Hotkeys (Bottom Right)
        hx = SCREEN_WIDTH - 280
        hy = 16
        
        # Skill hotkeys (1-4)
        skills_layout = [
            ("1", "Fireball", player.skill_manager.skills[SKILL_FIREBALL]),
            ("2", "Ice Spike", player.skill_manager.skills[SKILL_ICE_SPIKE]),
            ("3", "Heal", player.skill_manager.skills[SKILL_HEALING]),
            ("4", "Dash", player.skill_manager.skills[SKILL_DASH])
        ]
        
        for idx, (key, label, skill) in enumerate(skills_layout):
            sx = hx + idx * 60
            sy = hy
            
            # Hotkey box
            box = pygame.Rect(sx, sy, 44, 44)
            pygame.draw.rect(surface, COLOR_UI_BG[:3], box, border_radius=4)
            
            # Highlight border if unlocked, gray if locked
            border_c = COLOR_UI_HIGHLIGHT if skill.unlocked else COLOR_GRAY
            pygame.draw.rect(surface, border_c, box, 1 if skill.timer <= 0 else 2, border_radius=4)
            
            # Render cooldown shader overlay
            if skill.unlocked and skill.timer > 0:
                cooldown_ratio = skill.timer / skill.cooldown
                shader_h = int(44 * cooldown_ratio)
                pygame.draw.rect(surface, (100, 10, 10, 180), (sx, sy + 44 - shader_h, 44, shader_h), border_radius=4)
                
                # Cooldown numbers
                cd_lbl = self.fonts["small"].render(f"{skill.timer:.1f}s", True, COLOR_RED)
                surface.blit(cd_lbl, (sx + 22 - cd_lbl.get_width() // 2, sy + 14))
            else:
                # Skill label name
                lbl = self.fonts["small"].render(label, True, COLOR_UI_TEXT if skill.unlocked else COLOR_GRAY)
                surface.blit(lbl, (sx + 22 - lbl.get_width() // 2, sy + 14))
                
            # Key trigger number indicator
            num_lbl = self.fonts["small"].render(key, True, COLOR_WHITE)
            surface.blit(num_lbl, (sx + 4, sy + 2))

    def _draw_harvest_moon_clock(self, surface: pygame.Surface, game: Any) -> None:
        """
        Renders a Harvest Moon / Stardew Valley style time & season HUD clock.
        Displays season badge, day/year counter, 12h digital clock, and Sun/Moon icon.
        """
        if not game or not hasattr(game, "world_state"):
            return

        ws = game.world_state
        tod = getattr(ws, "time_of_day", 12.0)
        day = getattr(ws, "day", 1)
        season = str(getattr(ws, "season", "spring")).upper()

        # Calculate time components (12-hour format)
        hours = int(tod) % 24
        mins = int((tod % 1.0) * 60)
        period = "AM" if hours < 12 else "PM"
        display_h = 12 if hours in [0, 12] else hours % 12
        clock_str = f"{display_h:02d}:{mins:02d} {period}"

        # Calculate season & year
        day_of_season = (day - 1) % 30 + 1
        year = (day - 1) // 120 + 1

        # Position box at top center
        box_w, box_h = 190, 52
        bx = SCREEN_WIDTH // 2 - box_w // 2
        by = 10

        # Draw retro brass/wooden frame
        frame_rect = pygame.Rect(bx, by, box_w, box_h)
        pygame.draw.rect(surface, (25, 22, 30), frame_rect, border_radius=6)
        pygame.draw.rect(surface, (210, 170, 60), frame_rect, 2, border_radius=6)

        # Season colors and badge text
        season_colors = {
            "SPRING": (120, 220, 140),  # Fresh Green
            "SUMMER": (255, 210, 60),   # Sun Yellow
            "AUTUMN": (230, 130, 50),   # Crimson Orange
            "WINTER": (120, 200, 255)   # Ice Blue
        }
        s_color = season_colors.get(season, (200, 200, 200))

        # 1. Season & Day Line (e.g., "SPRING · Day 12 (Yr 1)")
        season_str = f"{season} · Day {day_of_season} (Yr {year})"
        s_lbl = self.fonts["small"].render(season_str, True, s_color)
        surface.blit(s_lbl, (bx + 12, by + 8))

        # 2. Digital Clock Line (e.g., "08:30 AM")
        t_lbl = self.fonts["medium"].render(clock_str, True, COLOR_WHITE)
        surface.blit(t_lbl, (bx + 12, by + 26))

        # 3. Sun / Moon Icon Badge (Right side of clock card)
        icon_cx = bx + box_w - 24
        icon_cy = by + box_h // 2
        is_day = 6 <= hours < 18

        if is_day:
            # Draw Sun (Golden circle with rays)
            pygame.draw.circle(surface, (255, 220, 50), (icon_cx, icon_cy), 9)
            pygame.draw.circle(surface, (255, 240, 150), (icon_cx, icon_cy), 5)
        else:
            # Draw Moon (Cyan/White Crescent)
            pygame.draw.circle(surface, (200, 230, 255), (icon_cx, icon_cy), 9)
            pygame.draw.circle(surface, (25, 22, 30), (icon_cx - 4, icon_cy - 2), 7)

        # 4. Render Active Greed Curse HUD Badge if player challenged Greed Altar
        if hasattr(game, "player") and getattr(game.player, "greed_curse_active", False):
            gb_rect = pygame.Rect(bx + box_w + 10, by + 10, 160, 32)
            pygame.draw.rect(surface, (45, 12, 18), gb_rect, border_radius=4)
            pygame.draw.rect(surface, (255, 60, 60), gb_rect, 1, border_radius=4)
            g_txt = self.fonts["small"].render("GREED CURSE ACTIVATED", True, (255, 180, 60))
            sub_txt = self.fonts["small"].render("ATK +50% | Loot x2", True, (255, 220, 220))
            surface.blit(g_txt, (gb_rect.x + 8, gb_rect.y + 2))
            surface.blit(sub_txt, (gb_rect.x + 8, gb_rect.y + 16))

    def draw_quest_tracker_widget(self, surface: pygame.Surface, game: Any) -> None:
        """Renders small active quest overlay widget on the right side of the screen."""
        if not hasattr(game, "quest_manager"):
            return
            
        quest = game.quest_manager.get_tracked_quest()
        if not quest:
            return

        w = 210
        padding = 8
        line_h = 18
        
        # Calculate dynamic box height
        h = 28 + len(quest.objectives) * line_h + 8

        # Position right side below minimap
        x = SCREEN_WIDTH - w - 10
        y = 290 if getattr(game, "minimap_enabled", True) else 90

        # Background translucent box
        bg_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        bg_surf.fill((16, 20, 28, 200))
        surface.blit(bg_surf, (x, y))
        pygame.draw.rect(surface, (70, 90, 120), (x, y, w, h), 1, border_radius=4)

        # Header title
        title_txt = f"★ {quest.title}" if game.quest_manager.tracked_quest_id == quest.id else f"Quest: {quest.title}"
        if len(title_txt) > 23:
            title_txt = title_txt[:21] + ".."
        title_lbl = self.fonts["small"].render(title_txt, True, (240, 210, 100))
        surface.blit(title_lbl, (x + padding, y + 6))

        # Divider
        pygame.draw.line(surface, (60, 80, 100), (x + 6, y + 24), (x + w - 6, y + 24), 1)

        # Draw objective lines
        cur_y = y + 28
        for obj in quest.objectives:
            chk = "[v]" if obj.is_complete() else "[ ]"
            color = (100, 220, 120) if obj.is_complete() else (200, 200, 200)
            txt = f"{chk} {obj.text} ({obj.current_count}/{obj.required_count})"
            if len(txt) > 25:
                txt = txt[:23] + ".."
            obj_lbl = self.fonts["small"].render(txt, True, color)
            surface.blit(obj_lbl, (x + padding, cur_y))
            cur_y += line_h

    def _draw_hud_bar(self, surface: pygame.Surface, x: int, y: int, w: int, h: int, val: float, val_max: float, color: Tuple[int, int, int], tag: str) -> None:
        """Helper to render stats bar gradients with overlays."""
        # Base shadow box
        pygame.draw.rect(surface, COLOR_BLACK, (x, y, w, h), border_radius=3)
        
        # Colored fill
        ratio = max(0.0, min(1.0, val / max(1.0, val_max)))
        if ratio > 0:
            pygame.draw.rect(surface, color, (x, y, int(w * ratio), h), border_radius=3)
            # Highlights shine
            pygame.draw.rect(surface, tuple(min(255, c + 40) for c in color), (x, y, int(w * ratio), h // 3), border_radius=1)
            
        # Draw border frame
        pygame.draw.rect(surface, COLOR_UI_BORDER, (x, y, w, h), 1, border_radius=3)
        
        # Tag text overlay
        lbl = self.fonts["small"].render(f"{tag}: {int(val)}/{int(val_max)}", True, COLOR_WHITE)
        surface.blit(lbl, (x + 6, y + h // 2 - lbl.get_height() // 2 - 1))

    # --- MAIN MENU SCREEN ---

    def draw_main_menu(self, surface: pygame.Surface) -> None:
        """Renders the game entry title splash screen."""
        # Note: Clear display is handled by game.py with village background + translucent overlay
        
        # Title text
        title = self.fonts["title"].render("Echoes of Asterra", True, COLOR_UI_HIGHLIGHT)
        subtitle = self.fonts["medium"].render("A Procedural Pixel-Art RPG Adventure", True, COLOR_GRAY)
        
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 120))
        surface.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 170))

        # Draw options buttons
        for idx, opt in enumerate(self.menu_options):
            x = SCREEN_WIDTH // 2 - 140
            y = 230 + idx * 52
            
            box = pygame.Rect(x, y, 280, 44)
            # Hover highlight
            is_hover = (idx == self.menu_select_idx)
            bg_c = COLOR_UI_BG[:3] if not is_hover else COLOR_UI_HIGHLIGHT
            border_c = COLOR_WHITE if is_hover else COLOR_UI_BORDER
            text_c = COLOR_BLACK if is_hover else COLOR_WHITE
            
            pygame.draw.rect(surface, bg_c, box, border_radius=5)
            pygame.draw.rect(surface, border_c, box, 1, border_radius=5)
            
            lbl = self.fonts["medium"].render(opt, True, text_c)
            surface.blit(lbl, (x + 140 - lbl.get_width() // 2, y + 22 - lbl.get_height() // 2))

    # --- SETTINGS MENU SCREEN ---

    def draw_settings_menu(self, surface: pygame.Surface, game: Any) -> None:
        """Renders the settings screen to adjust volumes."""
        surface.fill(COLOR_BLACK)
        
        # Title text
        title = self.fonts["title"].render("Settings", True, COLOR_UI_HIGHLIGHT)
        subtitle = self.fonts["medium"].render("Adjust game volumes using keyboard or clicks", True, COLOR_GRAY)
        
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 160))
        surface.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 220))

        # Draw options buttons
        for idx, opt in enumerate(self.settings_options):
            x = SCREEN_WIDTH // 2 - 160
            y = 260 + idx * 64
            
            box = pygame.Rect(x, y, 320, 48)
            is_hover = (idx == self.settings_select_idx)
            bg_c = COLOR_UI_BG[:3] if not is_hover else COLOR_UI_HIGHLIGHT
            border_c = COLOR_WHITE if is_hover else COLOR_UI_BORDER
            text_c = COLOR_BLACK if is_hover else COLOR_WHITE
            
            pygame.draw.rect(surface, bg_c, box, border_radius=5)
            pygame.draw.rect(surface, border_c, box, 1, border_radius=5)
            
            # Format text based on type
            if idx == 0:
                pct = int(game.sound_manager.music_volume * 100)
                text = f"Music Volume:  <  {pct}%  >"
            elif idx == 1:
                pct = int(game.sound_manager.sfx_volume * 100)
                text = f"SFX Volume:  <  {pct}%  >"
            elif idx == 2:
                mode_str = "FULLSCREEN" if getattr(game, "is_fullscreen", True) else "WINDOWED"
                text = f"Display:  <  {mode_str}  >"
            else:
                text = opt
                
            lbl = self.fonts["medium"].render(text, True, text_c)
            surface.blit(lbl, (x + 160 - lbl.get_width() // 2, y + 24 - lbl.get_height() // 2))

    # --- TUTORIAL SCREEN ---

    def draw_tutorial(self, surface: pygame.Surface) -> None:
        """Draws a complete custom tutorial overlay detailing all key bindings and game systems."""
        # Panel Coordinates (Center screen)
        tw, th = 760, 480
        tx = (SCREEN_WIDTH - tw) // 2
        ty = (SCREEN_HEIGHT - th) // 2
        
        box = pygame.Rect(tx, ty, tw, th)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=8)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=8)
        
        # Header title
        hdr = self.fonts["large"].render("Tutorial & Keybindings Reference", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (tx + tw // 2 - hdr.get_width() // 2, ty + 18))
        
        # Divider under header
        pygame.draw.line(surface, (60, 70, 90), (tx + 24, ty + 54), (tx + tw - 24, ty + 54), 1)

        # Left Column: Combat & Movement
        left_controls = [
            ("Move / Walk", "W, A, S, D"),
            ("Sprint Movement", "Hold Left Shift"),
            ("Dodge Roll", "Spacebar (I-Frames)"),
            ("Melee Attack", "J or Left Click"),
            ("Shield Block", "K or Hold Right Click"),
            ("Quick Spells", "1 (Fireball), 2 (Ice), 3 (Heal), 4 (Dash)"),
            ("Interaction", "Press [E] (NPCs, Chests, Portals)")
        ]

        # Right Column: UI Menus & Systems
        right_controls = [
            ("Backpack Inventory", "Toggle [I]"),
            ("Character Attributes", "Toggle [C]"),
            ("Quest Journal", "Toggle [Q] or [L]"),
            ("Crafting Forge", "Toggle [G]"),
            ("Radar Minimap", "Toggle [M]"),
            ("Equip / Use Item", "Right-Click item"),
            ("Unequip Gear", "Right-Click equipment slot"),
            ("Sell Items to Silas", "Click item in Shop Sell Panel"),
            ("Pause / Save / Load", "Press [ESC]")
        ]

        col_w = 340
        left_x = tx + 24
        right_x = tx + tw // 2 + 16

        # Column Section Headers
        c1_hdr = self.fonts["medium"].render("Combat & Movement", True, (200, 220, 255))
        c2_hdr = self.fonts["medium"].render("Menus & System Controls", True, (200, 220, 255))
        surface.blit(c1_hdr, (left_x, ty + 64))
        surface.blit(c2_hdr, (right_x, ty + 64))

        # Vertical Divider between columns
        pygame.draw.line(surface, (50, 60, 80), (tx + tw // 2, ty + 64), (tx + tw // 2, ty + th - 50), 1)

        # Draw Left Column
        start_y = ty + 96
        line_h = 44
        for idx, (action, bind) in enumerate(left_controls):
            curr_y = start_y + idx * line_h
            act_lbl = self.fonts["small"].render(action, True, COLOR_WHITE)
            bind_lbl = self.fonts["small"].render(bind, True, COLOR_UI_HIGHLIGHT)
            surface.blit(act_lbl, (left_x, curr_y))
            surface.blit(bind_lbl, (left_x, curr_y + 16))
            if idx < len(left_controls) - 1:
                pygame.draw.line(surface, (40, 45, 55), (left_x, curr_y + 36), (left_x + col_w, curr_y + 36), 1)

        # Draw Right Column
        for idx, (action, bind) in enumerate(right_controls):
            curr_y = start_y + idx * 36
            act_lbl = self.fonts["small"].render(action, True, COLOR_WHITE)
            bind_lbl = self.fonts["small"].render(bind, True, COLOR_UI_HIGHLIGHT)
            surface.blit(act_lbl, (right_x, curr_y))
            surface.blit(bind_lbl, (right_x + col_w - bind_lbl.get_width(), curr_y))
            if idx < len(right_controls) - 1:
                pygame.draw.line(surface, (40, 45, 55), (right_x, curr_y + 28), (right_x + col_w, curr_y + 28), 1)

        # Footer
        pygame.draw.line(surface, (60, 70, 90), (tx + 24, ty + th - 44), (tx + tw - 24, ty + th - 44), 1)
        footer = self.fonts["small"].render("Press [ESC, Space, or Enter] to return to menu", True, COLOR_GRAY)
        surface.blit(footer, (tx + tw // 2 - footer.get_width() // 2, ty + th - 32))

    # --- PAUSE OVERLAY ---

    def draw_pause_menu(self, surface: pygame.Surface) -> None:
        """Translucent pause dialogue panel supporting slot selector, management, and renaming."""
        # Tint back layer
        dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((5, 5, 10, 150))
        surface.blit(dim, (0, 0))

        state = self.pause_menu_state

        # 1. Main Pause Menu State
        if state == "main":
            px = SCREEN_WIDTH // 2 - 160
            py = SCREEN_HEIGHT // 2 - 200
            pw, ph = 320, 390
            
            box = pygame.Rect(px, py, pw, ph)
            pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=8)
            pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=8)

            p_txt = self.fonts["large"].render("GAME PAUSED", True, COLOR_UI_HIGHLIGHT)
            surface.blit(p_txt, (px + 160 - p_txt.get_width() // 2, py + 20))

            for idx, opt in enumerate(self.pause_options):
                bx = px + 30
                by = py + 68 + idx * 58
                
                option_box = pygame.Rect(bx, by, 260, 40)
                is_hover = (idx == self.pause_select_idx)
                
                bg_c = COLOR_UI_HIGHLIGHT if is_hover else COLOR_DARK_GRAY
                text_c = COLOR_BLACK if is_hover else COLOR_WHITE
                
                pygame.draw.rect(surface, bg_c, option_box, border_radius=4)
                pygame.draw.rect(surface, COLOR_UI_BORDER, option_box, 1, border_radius=4)
                
                lbl = self.fonts["medium"].render(opt, True, text_c)
                surface.blit(lbl, (bx + 130 - lbl.get_width() // 2, by + 20 - lbl.get_height() // 2))

        # 2. Save / Load Slots Selector State
        elif state in ["save_slots", "load_slots"]:
            px = SCREEN_WIDTH // 2 - 250
            py = SCREEN_HEIGHT // 2 - 220
            pw, ph = 500, 410
            
            box = pygame.Rect(px, py, pw, ph)
            pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=8)
            pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=8)

            title_text = "SAVE PROFILE SLOT" if state == "save_slots" else "LOAD PROFILE SLOT"
            p_txt = self.fonts["large"].render(title_text, True, COLOR_UI_HIGHLIGHT)
            surface.blit(p_txt, (px + 250 - p_txt.get_width() // 2, py + 20))

            # Slots (1-3)
            for idx in range(3):
                bx = px + 30
                by = py + 68 + idx * 82
                
                option_box = pygame.Rect(bx, by, 440, 72)
                is_hover = (idx == self.pause_select_idx)
                
                bg_c = COLOR_UI_BG[:3] if not is_hover else (30, 35, 45)
                border_c = COLOR_UI_HIGHLIGHT if is_hover else COLOR_UI_BORDER
                
                pygame.draw.rect(surface, bg_c, option_box, border_radius=6)
                pygame.draw.rect(surface, border_c, option_box, 1 if not is_hover else 2, border_radius=6)
                
                meta = self.slots_meta.get(idx + 1, {"exists": False})
                if meta["exists"]:
                    # Slot name
                    name_lbl = self.fonts["large"].render(meta["slot_name"], True, COLOR_UI_HIGHLIGHT if is_hover else COLOR_WHITE)
                    surface.blit(name_lbl, (bx + 16, by + 10))
                    
                    # Stats info
                    stats_lbl = self.fonts["small"].render(f"Lvl {meta['level']}  •  {meta['gold']}g", True, COLOR_LIGHT_GRAY)
                    surface.blit(stats_lbl, (bx + 16, by + 46))
                    
                    # Map location
                    map_lbl = self.fonts["medium"].render(meta["map"], True, COLOR_WHITE)
                    surface.blit(map_lbl, (bx + 424 - map_lbl.get_width(), by + 12))
                    
                    # Timestamp
                    date_lbl = self.fonts["small"].render(meta["date"], True, COLOR_GRAY)
                    surface.blit(date_lbl, (bx + 424 - date_lbl.get_width(), by + 46))
                else:
                    empty_lbl = self.fonts["medium"].render(f"Slot {idx + 1} - [EMPTY PROFILE]", True, COLOR_GRAY)
                    surface.blit(empty_lbl, (bx + 220 - empty_lbl.get_width() // 2, by + 36 - empty_lbl.get_height() // 2))

            # Back button (idx == 3)
            bx = px + 30
            by = py + 326
            back_box = pygame.Rect(bx, by, 440, 40)
            is_hover = (self.pause_select_idx == 3)
            bg_c = COLOR_UI_HIGHLIGHT if is_hover else COLOR_DARK_GRAY
            text_c = COLOR_BLACK if is_hover else COLOR_WHITE
            
            pygame.draw.rect(surface, bg_c, back_box, border_radius=4)
            pygame.draw.rect(surface, COLOR_UI_BORDER, back_box, 1, border_radius=4)
            
            lbl = self.fonts["medium"].render("Cancel", True, text_c)
            surface.blit(lbl, (bx + 220 - lbl.get_width() // 2, by + 20 - lbl.get_height() // 2))

        # 3. Actions Panel for selected slot
        elif state == "slot_actions":
            px = SCREEN_WIDTH // 2 - 200
            py = SCREEN_HEIGHT // 2 - 180
            pw, ph = 400, 360
            
            box = pygame.Rect(px, py, pw, ph)
            pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=8)
            pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=8)

            p_txt = self.fonts["large"].render(f"SLOT {self.selected_slot_idx + 1} ACTIONS", True, COLOR_UI_HIGHLIGHT)
            surface.blit(p_txt, (px + 200 - p_txt.get_width() // 2, py + 24))

            # Draw small slot status info box
            sbx = px + 30
            sby = py + 68
            sbox = pygame.Rect(sbx, sby, 340, 56)
            pygame.draw.rect(surface, (20, 20, 25), sbox, border_radius=4)
            pygame.draw.rect(surface, COLOR_UI_BORDER, sbox, 1, border_radius=4)
            
            meta = self.slots_meta.get(self.selected_slot_idx + 1, {"exists": False})
            if meta["exists"]:
                lbl1 = self.fonts["medium"].render(meta["slot_name"], True, COLOR_WHITE)
                lbl2 = self.fonts["small"].render(f"Lvl {meta['level']}  •  {meta['gold']}g  •  {meta['map']}", True, COLOR_LIGHT_GRAY)
                surface.blit(lbl1, (sbx + 12, sby + 8))
                surface.blit(lbl2, (sbx + 12, sby + 32))
            else:
                lbl1 = self.fonts["medium"].render("[Empty Profile Slot]", True, COLOR_GRAY)
                surface.blit(lbl1, (sbx + 12, sby + 18))

            # Determine dynamic actions
            if self.pause_action_source == "save":
                opts = ["Create Save" if not meta["exists"] else "Overwrite Save", "Rename Profile", "Delete Save", "Back"]
            else:
                opts = ["Load Profile", "Rename Profile", "Delete Save", "Back"]
                if not meta["exists"]:
                    opts = ["Back"] # Nothing to do on empty slot when loading

            # Draw action buttons
            for idx, opt in enumerate(opts):
                bx = px + 30
                by = py + 144 + idx * 48
                
                option_box = pygame.Rect(bx, by, 340, 36)
                is_hover = (idx == self.pause_select_idx)
                
                # Check for disabled options (Delete/Rename on empty slots)
                is_disabled = (not meta["exists"] and opt in ["Rename Profile", "Delete Save", "Load Profile"])
                
                if is_disabled:
                    bg_c = (25, 25, 25)
                    text_c = COLOR_DARK_GRAY
                else:
                    bg_c = COLOR_UI_HIGHLIGHT if is_hover else COLOR_DARK_GRAY
                    text_c = COLOR_BLACK if is_hover else COLOR_WHITE
                
                pygame.draw.rect(surface, bg_c, option_box, border_radius=4)
                pygame.draw.rect(surface, COLOR_UI_BORDER if not is_disabled else (35, 35, 35), option_box, 1, border_radius=4)
                
                lbl = self.fonts["medium"].render(opt, True, text_c)
                surface.blit(lbl, (bx + 170 - lbl.get_width() // 2, by + 18 - lbl.get_height() // 2))

        # 4. Text Input field for Renaming
        elif state == "rename_input":
            px = SCREEN_WIDTH // 2 - 200
            py = SCREEN_HEIGHT // 2 - 110
            pw, ph = 400, 220
            
            box = pygame.Rect(px, py, pw, ph)
            pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=8)
            pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=8)

            p_txt = self.fonts["large"].render("RENAME PROFILE", True, COLOR_UI_HIGHLIGHT)
            surface.blit(p_txt, (px + 200 - p_txt.get_width() // 2, py + 24))

            # Prompt label
            lbl_prompt = self.fonts["medium"].render("Enter profile name:", True, COLOR_WHITE)
            surface.blit(lbl_prompt, (px + 30, py + 68))

            # Text input field box
            ibx = px + 30
            iby = py + 98
            ibox = pygame.Rect(ibx, iby, 340, 44)
            pygame.draw.rect(surface, (10, 10, 15), ibox, border_radius=4)
            pygame.draw.rect(surface, COLOR_UI_HIGHLIGHT, ibox, 1, border_radius=4)

            # Draw text with flashing cursor
            cursor = "|" if int(pygame.time.get_ticks() / 400) % 2 == 0 else ""
            display_txt = self.rename_input_text + cursor
            lbl_txt = self.fonts["large"].render(display_txt, True, COLOR_WHITE)
            surface.blit(lbl_txt, (ibx + 12, iby + 22 - lbl_txt.get_height() // 2))

            # Help instruction hint
            lbl_hint = self.fonts["small"].render("Press [ENTER] to Save  •  [ESC] to Cancel", True, COLOR_GRAY)
            surface.blit(lbl_hint, (px + 200 - lbl_hint.get_width() // 2, py + 168))

    # --- INVENTORY PANEL ---

    def draw_inventory_panel(self, surface: pygame.Surface, player: Any) -> None:
        """Renders grid backpack item slots."""
        # Panel Coordinates (Left side screen)
        ix, iy = 40, 120
        iw, ih = 340, 380
        
        box = pygame.Rect(ix, iy, iw, ih)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=6)

        # Header title
        hdr = self.fonts["medium"].render("Backpack Inventory", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (ix + 16, iy + 16))

        # Close button instructions
        cls = self.fonts["small"].render("[I] Close", True, COLOR_GRAY)
        surface.blit(cls, (ix + iw - cls.get_width() - 16, iy + 18))

        # Draw Sort Button
        sort_rect = pygame.Rect(ix + 16, iy + ih - 44, 100, 26)
        pygame.draw.rect(surface, COLOR_DARK_GRAY, sort_rect, border_radius=3)
        pygame.draw.rect(surface, COLOR_UI_BORDER, sort_rect, 1, border_radius=3)
        sort_lbl = self.fonts["small"].render("Sort Slots", True, COLOR_WHITE)
        surface.blit(sort_lbl, (sort_rect.centerx - sort_lbl.get_width() // 2, sort_rect.centery - sort_lbl.get_height() // 2))

        # Draw hint text next to sort button
        hint_lbl = self.fonts["small"].render("[R-Click/Double-Click] Use", True, COLOR_GRAY)
        surface.blit(hint_lbl, (ix + 124, iy + ih - 36))

        # Grid specifications
        cols, rows = 6, 4
        slot_sz = 44
        spacing = 8
        grid_start_x = ix + 16
        grid_start_y = iy + 52

        # Draw grid cells
        m_pos = pygame.mouse.get_pos()
        
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                if idx >= player.inventory.size:
                    break
                    
                sx = grid_start_x + c * (slot_sz + spacing)
                sy = grid_start_y + r * (slot_sz + spacing)
                
                slot_rect = pygame.Rect(sx, sy, slot_sz, slot_sz)
                
                # Check hover highlight
                is_hover = slot_rect.collidepoint(m_pos)
                bg_color = (60, 62, 72) if is_hover else (35, 37, 45)
                
                pygame.draw.rect(surface, bg_color, slot_rect, border_radius=4)
                
                # Draw item if slot populated
                item = player.inventory.slots[idx]
                if item and idx != player.inventory.dragged_slot_idx:
                    # Item procedural icon
                    icon_img = pygame.transform.scale(item.icon, (32, 32))
                    surface.blit(icon_img, (sx + 6, sy + 6))
                    
                    # Highlight slot border by item rarity color
                    rarity_c = RARITY_COLORS.get(item.rarity, COLOR_UI_BORDER)
                    pygame.draw.rect(surface, rarity_c, slot_rect, 2, border_radius=4)
                    
                    # Draw stack quantity if > 1
                    if item.quantity > 1:
                        qty_txt = self.fonts["small"].render(str(item.quantity), True, COLOR_WHITE)
                        surface.blit(qty_txt, (sx + slot_sz - qty_txt.get_width() - 4, sy + slot_sz - qty_txt.get_height() - 2))

                    # Cache hovered item for tooltip popup
                    if is_hover:
                        self.hovered_item = item
                else:
                    pygame.draw.rect(surface, COLOR_UI_BORDER, slot_rect, 1, border_radius=4)

                # Store bounds for click registration
                self.slot_rects["inventory"].append((slot_rect, idx))

    # --- CHARACTER PANEL ---

    def draw_character_panel(self, surface: pygame.Surface, player: Any) -> None:
        """Renders equipment gear sockets, stats listings, and faction standings."""
        # Panel Coordinates (Centered)
        cx, cy = 240, 100
        cw, ch = 560, 420
        
        box = pygame.Rect(cx, cy, cw, ch)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=6)

        # Header Title
        hdr = self.fonts["medium"].render("Hero Attributes & Factions", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (cx + 16, cy + 16))

        # Close label
        cls = self.fonts["small"].render("[C] Close", True, COLOR_GRAY)
        surface.blit(cls, (cx + cw - cls.get_width() - 16, cy + 18))

        # Draw Equipment Slots
        eq_slots = list(player.equipment.slots.keys())
        slot_sz = 40
        grid_x = cx + 16
        grid_y = cy + 52
        
        m_pos = pygame.mouse.get_pos()

        for idx, slot_type in enumerate(eq_slots):
            sy = grid_y + idx * 44
            slot_rect = pygame.Rect(grid_x, sy, slot_sz, slot_sz)
            
            # Hover check
            is_hover = slot_rect.collidepoint(m_pos)
            bg_color = (60, 62, 72) if is_hover else (35, 37, 45)
            pygame.draw.rect(surface, bg_color, slot_rect, border_radius=4)
            pygame.draw.rect(surface, COLOR_UI_BORDER, slot_rect, 1, border_radius=4)
            
            # Label
            abbr = slot_type[:3].upper()
            lbl = self.fonts["small"].render(abbr, True, COLOR_GRAY)
            surface.blit(lbl, (grid_x + slot_sz + 6, sy + 12))

            # Spun equipped item if active
            equipped_item = player.equipment.slots[slot_type]
            if equipped_item:
                icon_img = pygame.transform.scale(equipped_item.icon, (28, 28))
                surface.blit(icon_img, (grid_x + 6, sy + 6))
                
                # Color borders by rarity
                rarity_c = RARITY_COLORS.get(equipped_item.rarity, COLOR_UI_BORDER)
                pygame.draw.rect(surface, rarity_c, slot_rect, 2, border_radius=4)

                # Tooltip query hover
                if is_hover:
                    self.hovered_item = equipped_item
                    
            # Cache coordinate rect for click unequip checks
            self.slot_rects["equipment"].append((slot_rect, slot_type))

        # Draw character attributes listings (Middle section of panel)
        stat_x = cx + 130
        stat_y = cy + 52
        
        stats = [
            ("Base Melee ATK", player.atk),
            ("Physical DEF", player.defense),
            ("Spell Power", player.magic),
            ("Speed Rating", f"{player.speed:.1f}"),
            ("Critical Strike", f"{player.crit_chance}%"),
            ("Maximum HP", player.max_hp),
            ("Maximum Mana", player.max_mana)
        ]
        
        for idx, (label, val) in enumerate(stats):
            y_pos = stat_y + idx * 36
            lbl = self.fonts["small"].render(label, True, COLOR_GRAY)
            val_lbl = self.fonts["medium"].render(str(val), True, COLOR_WHITE)
            surface.blit(lbl, (stat_x, y_pos))
            surface.blit(val_lbl, (stat_x, y_pos + 12))

        # Draw Faction Reputation Listings (Right section of panel)
        fac_x = cx + 330
        fac_y = cy + 52
        
        fac_title = self.fonts["medium"].render("Faction Standing", True, COLOR_UI_HIGHLIGHT)
        surface.blit(fac_title, (fac_x, cy + 24))
        
        if hasattr(player, "game") and hasattr(player.game, "factions"):
            fm = player.game.factions
            for idx, (f_id, fac_data) in enumerate(fm.factions.items()):
                y_pos = fac_y + idx * 46
                # Faction Name
                fn_lbl = self.fonts["small"].render(fac_data.name, True, COLOR_WHITE)
                surface.blit(fn_lbl, (fac_x, y_pos))
                
                # Rep Bar
                bar_w, bar_h = 180, 10
                bx, by = fac_x, y_pos + 16
                pygame.draw.rect(surface, (30, 32, 40), (bx, by, bar_w, bar_h), border_radius=2)
                pygame.draw.rect(surface, COLOR_UI_BORDER, (bx, by, bar_w, bar_h), 1, border_radius=2)
                
                # Fill ratio (-100 to +100 -> 0.0 to 1.0)
                norm_ratio = (fac_data.reputation + 100) / 200.0
                bar_color = (60, 200, 80) if fac_data.reputation >= 0 else (220, 60, 60)
                pygame.draw.rect(surface, bar_color, (bx, by, int(bar_w * norm_ratio), bar_h), border_radius=2)
                
                # Standing Text
                st_lbl = self.fonts["small"].render(f"{fac_data.standing.title()} ({fac_data.reputation})", True, COLOR_GRAY)
                surface.blit(st_lbl, (fac_x, by + 12))

    # --- QUEST LOG PANEL ---

    def draw_quests_panel(self, surface: pygame.Surface, quest_manager: Any) -> None:
        """Renders active side/main quests tasks checklist."""
        qx, qy = 40, 120
        qw, qh = 340, 380
        
        box = pygame.Rect(qx, qy, qw, qh)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=6)

        hdr = self.fonts["medium"].render("Quest Journal", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (qx + 16, qy + 16))

        cls = self.fonts["small"].render("[Q] Close", True, COLOR_GRAY)
        surface.blit(cls, (qx + qw - cls.get_width() - 16, qy + 18))

        active_quests = quest_manager.get_active_quests()
        if not active_quests:
            empty_lbl = self.fonts["small"].render("No active quests.", True, COLOR_GRAY)
            surface.blit(empty_lbl, (qx + 24, qy + 60))
            return

        self.slot_rects["quest_panel"].clear()
        m_pos = pygame.mouse.get_pos()
        curr_y = qy + 52

        for quest in active_quests:
            is_tracked = (quest_manager.tracked_quest_id == quest.id)
            title_prefix = "★ " if is_tracked else ""
            title_color = (255, 220, 100) if is_tracked else COLOR_WHITE

            row_rect = pygame.Rect(qx + 12, curr_y - 2, qw - 24, 22)
            if row_rect.collidepoint(m_pos):
                pygame.draw.rect(surface, (50, 65, 85), row_rect, border_radius=3)
            
            # Quest Title
            title_lbl = self.fonts["medium"].render(f"{title_prefix}{quest.title}", True, title_color)
            surface.blit(title_lbl, (qx + 16, curr_y))
            
            if is_tracked:
                pin_lbl = self.fonts["small"].render("[PINNED]", True, COLOR_GREEN)
                surface.blit(pin_lbl, (qx + qw - pin_lbl.get_width() - 20, curr_y + 2))
                
            self.slot_rects["quest_panel"].append((row_rect, quest.id))
            curr_y += 24
            
            # Objectives checkboxes
            for obj in quest.objectives:
                chk = "[v]" if obj.is_complete() else "[ ]"
                obj_text = f"{chk} {obj.text} ({obj.current_count}/{obj.required_count})"
                
                color = COLOR_GREEN if obj.is_complete() else COLOR_LIGHT_GRAY
                obj_lbl = self.fonts["small"].render(obj_text, True, color)
                surface.blit(obj_lbl, (qx + 28, curr_y))
                curr_y += 18
                
            curr_y += 12  # spacer between quests

    # --- CRAFTING PANEL ---

    def draw_crafting_panel(self, surface: pygame.Surface, player: Any) -> None:
        """Lists recipes and consumes materials to craft items."""
        cx, cy = 40, 120
        cw, ch = 340, 380
        
        box = pygame.Rect(cx, cy, cw, ch)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=6)

        hdr = self.fonts["medium"].render("Forge Anvil Crafting", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (cx + 16, cy + 16))

        cls = self.fonts["small"].render("[G] Close", True, COLOR_GRAY)
        surface.blit(cls, (cx + cw - cls.get_width() - 16, cy + 18))

        recipes = CraftingSystem.get_recipes_list()
        
        grid_start_y = cy + 52
        m_pos = pygame.mouse.get_pos()

        # Vertical lists of craftable items
        for idx, recipe_name in enumerate(recipes):
            y_pos = grid_start_y + idx * 30
            recipe_rect = pygame.Rect(cx + 16, y_pos, cw - 32, 26)
            
            # Hover check
            is_hover = recipe_rect.collidepoint(m_pos)
            bg_c = COLOR_DARK_GRAY if not is_hover else COLOR_UI_HIGHLIGHT
            text_c = COLOR_BLACK if is_hover else COLOR_WHITE
            
            pygame.draw.rect(surface, bg_c, recipe_rect, border_radius=3)
            pygame.draw.rect(surface, COLOR_UI_BORDER, recipe_rect, 1, border_radius=3)
            
            # Create a mock item to display tooltip hover card details
            mock_item = create_item(recipe_name, 1)
            if is_hover and mock_item:
                self.hovered_item = mock_item

            # Draw name
            name_lbl = self.fonts["small"].render(recipe_name, True, text_c)
            surface.blit(name_lbl, (cx + 24, y_pos + 5))
            
            # Draw required items inline (e.g. Iron: 5/3)
            ingredients, qty = CRAFTING_RECIPES[recipe_name]
            ing_strs = []
            can_craft = True
            
            for ing_name, req_qty in ingredients.items():
                curr_qty = player.inventory.get_item_count(ing_name)
                if curr_qty < req_qty:
                    can_craft = False
                ing_strs.append(f"{ing_name[:4]}:{curr_qty}/{req_qty}")
                
            ing_lbl_txt = ", ".join(ing_strs)
            ing_color = COLOR_GREEN if can_craft else (COLOR_RED if not is_hover else COLOR_DARK_GRAY)
            
            ing_lbl = self.fonts["small"].render(ing_lbl_txt, True, ing_color)
            surface.blit(ing_lbl, (cx + cw - ing_lbl.get_width() - 24, y_pos + 5))

    # --- SILAS MERCHANT SHOP UI ---

    def draw_shop_interface(self, surface: pygame.Surface, player: Any) -> None:
        """Buy and Sell panels interface with Merchant Silas."""
        # Large centered dual window
        sx, sy = SCREEN_WIDTH // 2 - 340, SCREEN_HEIGHT // 2 - 200
        sw, sh = 680, 400
        
        box = pygame.Rect(sx, sy, sw, sh)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=8)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=8)

        # Header Title
        hdr = self.fonts["large"].render(f"Merchant Silas' Shop (Gold: {player.gold}g)", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (sx + 24, sy + 20))

        # Close label
        cls = self.fonts["small"].render("[ESC] Exit Shop", True, COLOR_GRAY)
        surface.blit(cls, (sx + sw - cls.get_width() - 24, sy + 28))

        # LEFT PANEL: SILAS SELLS
        left_box = pygame.Rect(sx + 24, sy + 68, 300, 300)
        pygame.draw.rect(surface, COLOR_DARK_GRAY, left_box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, left_box, 1, border_radius=6)
        
        lbl_s = self.fonts["medium"].render("Silas' Wares (Buy)", True, COLOR_WHITE)
        surface.blit(lbl_s, (sx + 36, sy + 80))

        # Render Active Market Tax/Discount Modifier Badge from Living World Decisions
        if hasattr(player, "game") and hasattr(player.game, "living_world"):
            c_map = getattr(player.game.world_manager, "current_map_name", "village")
            p_scalar = player.game.living_world.get_combined_price_multiplier("goods", c_map)
            perc = int((p_scalar - 1.0) * 100)
            if perc != 0:
                badge_str = f"Tax: +{perc}%" if perc > 0 else f"Discount: {perc}%"
                badge_c = (255, 100, 100) if perc > 0 else (100, 240, 140)
                badge_lbl = self.fonts["small"].render(f"[{badge_str}]", True, badge_c)
                surface.blit(badge_lbl, (sx + 185, sy + 82))

        m_pos = pygame.mouse.get_pos()
        self.slot_rects["shop"].clear()

        for idx, item_name in enumerate(self.shop_goods):
            by = sy + 116 + idx * 46
            row_rect = pygame.Rect(sx + 36, by, 276, 40)
            
            # Hover check
            is_hover = row_rect.collidepoint(m_pos)
            bg_c = (80, 85, 95) if is_hover else (45, 48, 55)
            pygame.draw.rect(surface, bg_c, row_rect, border_radius=4)
            pygame.draw.rect(surface, COLOR_UI_BORDER, row_rect, 1, border_radius=4)
            
            # Icon
            mock_item = create_item(item_name)
            if mock_item:
                icon_img = pygame.transform.scale(mock_item.icon, (24, 24))
                surface.blit(icon_img, (sx + 42, by + 8))
                if is_hover:
                    self.hovered_item = mock_item

            # Name
            name_lbl = self.fonts["small"].render(item_name, True, COLOR_WHITE)
            surface.blit(name_lbl, (sx + 74, by + 12))
            
            # Price (modified dynamically by Living Economy + Factions + Settlement)
            base_buy, _ = self.shop_prices[item_name]
            price_scalar = 1.0
            if hasattr(player, "game") and hasattr(player.game, "living_world"):
                current_map = getattr(player.game.world_manager, "current_map_name", "village")
                price_scalar = player.game.living_world.get_combined_price_multiplier("goods", current_map)
            buy_price = max(1, int(base_buy * price_scalar))
            prc_color = COLOR_YELLOW if player.gold >= buy_price else COLOR_RED
            prc_lbl = self.fonts["medium"].render(f"{buy_price}g", True, prc_color)
            surface.blit(prc_lbl, (sx + 300 - prc_lbl.get_width() - 46, by + 10))

            # Store bounds for click buy actions
            self.slot_rects["shop"].append((row_rect, idx))

        # RIGHT PANEL: PLAYER INVENTORY BACKPACK
        right_box = pygame.Rect(sx + 356, sy + 68, 300, 300)
        pygame.draw.rect(surface, COLOR_DARK_GRAY, right_box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, right_box, 1, border_radius=6)

        lbl_p = self.fonts["medium"].render("Sell Items (Right-Click)", True, COLOR_WHITE)
        surface.blit(lbl_p, (sx + 368, sy + 80))

        # Render mini inventory backpack (6 cols, 4 rows)
        grid_start_x = sx + 368
        grid_start_y = sy + 116
        slot_sz = 36
        spacing = 6
        
        for r in range(4):
            for c in range(6):
                idx = r * 6 + c
                if idx >= player.inventory.size:
                    break
                    
                x = grid_start_x + c * (slot_sz + spacing)
                y = grid_start_y + r * (slot_sz + spacing)
                
                slot_rect = pygame.Rect(x, y, slot_sz, slot_sz)
                is_hover = slot_rect.collidepoint(m_pos)
                bg_color = (80, 85, 95) if is_hover else (35, 37, 45)
                
                pygame.draw.rect(surface, bg_color, slot_rect, border_radius=3)
                
                item = player.inventory.slots[idx]
                if item:
                    icon_img = pygame.transform.scale(item.icon, (24, 24))
                    surface.blit(icon_img, (x + 6, y + 6))
                    
                    rarity_c = RARITY_COLORS.get(item.rarity, COLOR_UI_BORDER)
                    pygame.draw.rect(surface, rarity_c, slot_rect, 2, border_radius=3)
                    
                    if item.quantity > 1:
                        qty_txt = self.fonts["small"].render(str(item.quantity), True, COLOR_WHITE)
                        surface.blit(qty_txt, (x + slot_sz - qty_txt.get_width() - 4, y + slot_sz - qty_txt.get_height() - 2))
                        
                    if is_hover:
                        self.hovered_item = item
                else:
                    pygame.draw.rect(surface, COLOR_UI_BORDER, slot_rect, 1, border_radius=3)

                # Store coordinates for sell clicks
                self.slot_rects["inventory"].append((slot_rect, idx))

    # --- ITEM DESCRIPTION TOOLTIP ---

    def draw_tooltip(self, surface: pygame.Surface, item: Any, mouse_pos: Tuple[int, int]) -> None:
        """Floating tooltip showing description, stats, and rarity colors."""
        tw, th = 220, 120
        tx = mouse_pos[0] + 16
        ty = mouse_pos[1] + 16
        
        # Keep tooltip bounded on screen right/bottom boundaries
        if tx + tw > SCREEN_WIDTH: tx = mouse_pos[0] - tw - 16
        if ty + th > SCREEN_HEIGHT: ty = mouse_pos[1] - th - 16

        box = pygame.Rect(tx, ty, tw, th)
        pygame.draw.rect(surface, (15, 17, 24, 240), box, border_radius=4)
        
        # Color outline by rarity
        rarity_c = RARITY_COLORS.get(item.rarity, COLOR_UI_BORDER)
        pygame.draw.rect(surface, rarity_c, box, 1, border_radius=4)

        # 1. Item Name
        name_lbl = self.fonts["medium"].render(item.name, True, rarity_c)
        surface.blit(name_lbl, (tx + 10, ty + 10))
        
        # 2. Item Rarity / Category label
        cat_lbl = self.fonts["small"].render(f"{item.rarity} {item.item_type.title()}", True, COLOR_GRAY)
        surface.blit(cat_lbl, (tx + 10, ty + 28))

        # 2b. Sell price tag
        sell_val = self.get_item_sell_price(item)
        if sell_val > 0:
            val_lbl = self.fonts["small"].render(f"Sell: {sell_val}g", True, COLOR_YELLOW)
            surface.blit(val_lbl, (tx + tw - val_lbl.get_width() - 10, ty + 28))

        # 3. Item stats
        stat_y = ty + 46
        if item.stats:
            stat_strs = [f"+{val} {k.upper()}" for k, val in item.stats.items()]
            stat_lbl_txt = ", ".join(stat_strs)
            stat_lbl = self.fonts["small"].render(stat_lbl_txt, True, COLOR_GREEN)
            surface.blit(stat_lbl, (tx + 10, stat_y))
            stat_y += 18
            
        # 4. Item Description text (wraps slightly)
        desc_lbl = self.fonts["small"].render(item.description[:36], True, COLOR_WHITE)
        desc_lbl_2 = self.fonts["small"].render(item.description[36:72], True, COLOR_WHITE)
        surface.blit(desc_lbl, (tx + 10, stat_y))
        surface.blit(desc_lbl_2, (tx + 10, stat_y + 14))

    # --- DIALOGUE WINDOW ---

    def draw_dialogue_box(self, surface: pygame.Surface, dialogue_manager: Any) -> None:
        """Typing dialogue node panel at screen bottom."""
        node = dialogue_manager.current_node
        if not node:
            return
            
        dw, dh = SCREEN_WIDTH - 80, 160
        dx, dy = 40, SCREEN_HEIGHT - 200
        
        box = pygame.Rect(dx, dy, dw, dh)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=6)

        # Draw speaker portrait socket (Procedural avatar shape)
        px, py = dx + 20, dy + 20
        pw, ph = 120, 120
        pygame.draw.rect(surface, COLOR_DARK_GRAY, (px, py, pw, ph), border_radius=4)
        pygame.draw.rect(surface, COLOR_UI_BORDER, (px, py, pw, ph), 1, border_radius=4)
        
        # Simple face avatar
        pygame.draw.circle(surface, (230, 180, 140), (px + 60, py + 60), 30)
        pygame.draw.circle(surface, (120, 80, 40), (px + 60, py + 52), 34, 4) # Hair
        pygame.draw.circle(surface, COLOR_BLACK, (px + 50, py + 56), 3) # Eyes
        pygame.draw.circle(surface, COLOR_BLACK, (px + 70, py + 56), 3)
        pygame.draw.circle(surface, COLOR_RED, (px + 60, py + 72), 6, 2) # Smile

        # Speaker Name & Relationship Standing Badge
        name_str = node.speaker_name
        rel_suffix = ""
        if hasattr(dialogue_manager, "game") and hasattr(dialogue_manager.game, "npc_memory"):
            short_id = name_str.split()[-1]
            mem = dialogue_manager.game.npc_memory.get_memory(short_id)
            rel_level = mem.friendship_level.replace("_", " ").title()
            rel_suffix = f" [{rel_level}]"
            
        name_lbl = self.fonts["medium"].render(name_str + rel_suffix, True, COLOR_UI_HIGHLIGHT)
        surface.blit(name_lbl, (dx + 160, dy + 18))

        # Dialogue text spelling
        txt_y = dy + 46
        words = dialogue_manager.visible_text.split(" ")
        lines = []
        curr_line = ""
        
        for w in words:
            test_line = curr_line + w + " "
            # Clip lines by pixel width
            if self.fonts["small"].size(test_line)[0] < dw - 200:
                curr_line = test_line
            else:
                lines.append(curr_line)
                curr_line = w + " "
        lines.append(curr_line)
        
        for idx, line in enumerate(lines[:3]):
            lbl = self.fonts["small"].render(line, True, COLOR_WHITE)
            surface.blit(lbl, (dx + 160, txt_y + idx * 20))

        # Dialogue choices list
        if dialogue_manager.typing_finished and node.choices:
            choice_start_x = dx + 160
            choice_start_y = dy + 104
            m_pos = pygame.mouse.get_pos()
            
            for idx, choice in enumerate(node.choices[:2]):
                cx = choice_start_x + idx * 240
                choice_rect = pygame.Rect(cx, choice_start_y, 220, 32)
                
                if choice_rect.collidepoint(m_pos):
                    dialogue_manager.selected_choice_idx = idx
                
                is_selected = (idx == dialogue_manager.selected_choice_idx)
                bg_c = COLOR_UI_HIGHLIGHT if is_selected else COLOR_DARK_GRAY
                text_c = COLOR_BLACK if is_selected else COLOR_WHITE
                
                pygame.draw.rect(surface, bg_c, choice_rect, border_radius=4)
                pygame.draw.rect(surface, COLOR_UI_BORDER, choice_rect, 1, border_radius=4)
                
                lbl = self.fonts["small"].render(choice.text, True, text_c)
                surface.blit(lbl, (cx + 110 - lbl.get_width() // 2, choice_start_y + 16 - lbl.get_height() // 2))
        elif dialogue_manager.typing_finished:
            # Advance hint
            hint = self.fonts["small"].render("[Space/Enter] Continue", True, COLOR_GRAY)
            surface.blit(hint, (dx + dw - hint.get_width() - 20, dy + dh - 24))

    # --- GAME OVER SCREEN ---

    def draw_game_over(self, surface: pygame.Surface) -> None:
        """Red dark game over screen."""
        surface.fill((30, 5, 5))
        
        lbl = self.fonts["title"].render("YOU PERISHED", True, COLOR_RED)
        sub = self.fonts["medium"].render("Press [Space] to reload last save, or [ESC] for Main Menu", True, COLOR_WHITE)
        
        surface.blit(lbl, (SCREEN_WIDTH // 2 - lbl.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, SCREEN_HEIGHT // 2 + 10))

    # --- VICTORY SCREEN ---

    def draw_victory(self, surface: pygame.Surface) -> None:
        """Triumphant victory splash screen."""
        surface.fill((5, 30, 15))
        
        lbl = self.fonts["title"].render("VICTORY ACHIEVED!", True, COLOR_GREEN)
        desc = self.fonts["large"].render("Asterra's Core is Purified", True, COLOR_UI_HIGHLIGHT)
        sub = self.fonts["medium"].render("Press [ESC] to return to Main Menu", True, COLOR_WHITE)
        
        surface.blit(lbl, (SCREEN_WIDTH // 2 - lbl.get_width() // 2, SCREEN_HEIGHT // 2 - 80))
        surface.blit(desc, (SCREEN_WIDTH // 2 - desc.get_width() // 2, SCREEN_HEIGHT // 2 - 20))
        surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, SCREEN_HEIGHT // 2 + 60))

    # --- INPUT CLICKS RESOLUTIONS ---

    def handle_click(self, mouse_pos: Tuple[int, int], game: Any, right_click: bool = False) -> None:
        """Catches button coordinates clicked to trigger panels interactions."""
        player = game.player
        state = game.game_state
        
        # 1. Main Menu click checks
        if state == STATE_MENU:
            for idx in range(len(self.menu_options)):
                bx = SCREEN_WIDTH // 2 - 140
                by = 230 + idx * 52
                rect = pygame.Rect(bx, by, 280, 44)
                if rect.collidepoint(mouse_pos):
                    self.execute_menu_choice(idx, game)
                    return
                    
        # Settings Menu click checks
        elif state == STATE_SETTINGS:
            for idx in range(len(self.settings_options)):
                bx = SCREEN_WIDTH // 2 - 160
                by = 260 + idx * 64
                rect = pygame.Rect(bx, by, 320, 48)
                if rect.collidepoint(mouse_pos):
                    self.settings_select_idx = idx
                    if idx == 0:
                        if mouse_pos[0] < bx + 160:
                            game.sound_manager.set_music_volume(game.sound_manager.music_volume - 0.1)
                        else:
                            game.sound_manager.set_music_volume(game.sound_manager.music_volume + 0.1)
                        game.sound_manager.play_sound("click")
                    elif idx == 1:
                        if mouse_pos[0] < bx + 160:
                            game.sound_manager.set_sfx_volume(game.sound_manager.sfx_volume - 0.1)
                        else:
                            game.sound_manager.set_sfx_volume(game.sound_manager.sfx_volume + 0.1)
                        game.sound_manager.play_sound("click")
                    elif idx == 2:
                        game.toggle_fullscreen()
                        game.sound_manager.play_sound("click")
                    elif idx == 3:
                        game.sound_manager.play_sound("click")
                        game.return_from_settings()
                    return

        # 2. Pause Menu click checks
        elif state == STATE_PAUSED:
            for idx in range(len(self.pause_options)):
                bx = SCREEN_WIDTH // 2 - 160
                by = SCREEN_HEIGHT // 2 - 200 + 68 + idx * 58
                rect = pygame.Rect(bx, by, 260, 40)
                if rect.collidepoint(mouse_pos):
                    self.execute_pause_choice(idx, game)
                    return

        # Dialogue box clicks
        elif state == STATE_DIALOGUE:
            node = game.dialogue_manager.current_node
            if node:
                dw, dh = SCREEN_WIDTH - 80, 160
                dx, dy = 40, SCREEN_HEIGHT - 200
                box = pygame.Rect(dx, dy, dw, dh)
                
                if box.collidepoint(mouse_pos):
                    if game.dialogue_manager.typing_finished and node.choices:
                        choice_start_x = dx + 160
                        choice_start_y = dy + 104
                        for idx, choice in enumerate(node.choices[:2]):
                            cx = choice_start_x + idx * 240
                            choice_rect = pygame.Rect(cx, choice_start_y, 220, 32)
                            if choice_rect.collidepoint(mouse_pos):
                                game.dialogue_manager.selected_choice_idx = idx
                                break
                    prev_st = game.game_state
                    game.dialogue_manager.advance()
                    if not game.dialogue_manager.current_node and game.game_state == prev_st:
                        game.game_state = STATE_PLAYING
            return

        # 3. Shop Window clicks
        elif state == STATE_SHOP:
            # Silas Sells: Click item row to buy
            for rect, idx in self.slot_rects["shop"]:
                if rect.collidepoint(mouse_pos) and not right_click:
                    goods_name = self.shop_goods[idx]
                    buy_price_base, _ = self.shop_prices[goods_name]
                    price_mod = 1.0
                    if hasattr(game, "factions"):
                        price_mod *= game.factions.get_price_modifier()
                    if hasattr(game, "world_state"):
                        price_mod *= game.world_state.get_price_modifier()
                    buy_price = max(1, int(buy_price_base * price_mod))
                    
                    if player.gold >= buy_price:
                        # Try adding to inventory
                        bought_item = create_item(goods_name, 1)
                        if bought_item and player.inventory.add_item(bought_item):
                            player.gold -= buy_price
                            player.sound_manager.play_sound("heal")
                            if hasattr(game, "event_bus"):
                                game.event_bus.emit("item_bought", item_name=goods_name, price=buy_price)
                            # Sync quest logs count
                            game.quest_manager.handle_inventory_change(player.inventory)
                    return
            
            # Player Sell: Click (Left-click OR Right-click) item in Sell Panel to sell to Silas
            for rect, idx in self.slot_rects["inventory"]:
                if rect.collidepoint(mouse_pos):
                    item = player.inventory.slots[idx]
                    if item:
                        sell_price = self.get_item_sell_price(item)
                        if sell_price > 0:
                            # Sell 1 from stack
                            player.gold += sell_price
                            player.sound_manager.play_sound("click")
                            item.quantity -= 1
                            if item.quantity <= 0:
                                player.inventory.slots[idx] = None
                            # Sync quest counters
                            game.quest_manager.handle_inventory_change(player.inventory)
                    return
            return

        # 4. Inventory Backpack & Equipment slots & Quest Journal interactions
        elif state == STATE_PLAYING:
            # Quest Journal panel clicks (pin/track active quest)
            if "quests" in self.open_panels:
                for rect, q_id in self.slot_rects.get("quest_panel", []):
                    if rect.collidepoint(mouse_pos) and not right_click:
                        game.quest_manager.set_tracked_quest(q_id)
                        player.sound_manager.play_sound("click")
                        return

            # Sort button click
            ix, iy = 40, 120
            ih = 380
            sort_rect = pygame.Rect(ix + 16, iy + ih - 44, 100, 26)
            if sort_rect.collidepoint(mouse_pos) and not right_click:
                player.inventory.sort_inventory()
                player.sound_manager.play_sound("click")
                return

            # Check gear slots right click (unequip)
            for rect, slot_type in self.slot_rects["equipment"]:
                if rect.collidepoint(mouse_pos) and right_click:
                    player.equipment.unequip(slot_type, player)
                    return

            # Check inventory grid clicks
            for rect, idx in self.slot_rects["inventory"]:
                if rect.collidepoint(mouse_pos):
                    if right_click:
                        # Consume / equip item
                        player.inventory.use_item(idx, player)
                    else:
                        # Check for double-click (within 250ms on same slot)
                        now = pygame.time.get_ticks()
                        if now - self.last_click_time < 250 and self.last_click_slot == idx:
                            # Cancel drag if started
                            player.inventory.dragged_item = None
                            player.inventory.drag_source_idx = -1
                            # Consume / equip item
                            player.inventory.use_item(idx, player)
                        else:
                            # Start dragging item
                            player.inventory.start_drag(idx)
                            self.last_click_time = now
                            self.last_click_slot = idx
                    return

            # Crafting anvil clicking
            if "crafting" in self.open_panels:
                recipes = CraftingSystem.get_recipes_list()
                for idx, recipe_name in enumerate(recipes):
                    y_pos = cy_crafting(cy=120) + 52 + idx * 30
                    recipe_rect = pygame.Rect(40 + 16, y_pos, 340 - 32, 26)
                    if recipe_rect.collidepoint(mouse_pos) and not right_click:
                        if CraftingSystem.craft(recipe_name, player.inventory):
                            player.sound_manager.play_sound("levelup")
                        return

    def execute_menu_choice(self, idx: int, game: Any) -> None:
        """Executes choice highlighted on Main Menu."""
        game.sound_manager.play_sound("click")
        if idx == 0:  # New Adventure
            game.start_new_game()
            game.game_state = STATE_PLAYING
            game._from_main_menu = False
        elif idx == 1:  # Load Adventure
            self.pause_menu_state = "load_slots"
            self.pause_action_source = "load"
            self.pause_select_idx = 0
            self.refresh_slots_metadata()
            game._from_main_menu = True
            game.game_state = STATE_PAUSED
        elif idx == 2:  # Tutorial
            game.game_state = STATE_TUTORIAL
        elif idx == 3:  # Settings
            game.game_state = STATE_SETTINGS
            self.settings_select_idx = 0
        elif idx == 4:  # Quit
            pygame.quit()
            import sys
            sys.exit()

    def execute_pause_choice(self, idx: int, game: Any) -> None:
        """Executes choice highlighted on Pause Menu supporting slots and management."""
        game.sound_manager.play_sound("click")
        
        # 1. Main Pause options
        if self.pause_menu_state == "main":
            if idx == 0:
                # Resume
                game.game_state = STATE_PLAYING
            elif idx == 1:
                # Save options
                self.pause_action_source = "save"
                self.pause_menu_state = "save_slots"
                self.pause_select_idx = 0
                self.refresh_slots_metadata()
            elif idx == 2:
                # Load options
                self.pause_action_source = "load"
                self.pause_menu_state = "load_slots"
                self.pause_select_idx = 0
                self.refresh_slots_metadata()
            elif idx == 3:
                # Settings
                game._from_pause_menu = True
                self.settings_select_idx = 0
                game.game_state = STATE_SETTINGS
            elif idx == 4:
                # Main Menu
                game.sound_manager.stop_music()
                game.game_state = STATE_MENU
                
        # 2. Save slot list options
        elif self.pause_menu_state == "save_slots":
            if idx in [0, 1, 2]:
                self.selected_slot_idx = idx
                self.pause_menu_state = "slot_actions"
                self.pause_select_idx = 0
            elif idx == 3:
                # Cancel / Back
                self.pause_menu_state = "main"
                self.pause_select_idx = 1
                
        # 3. Load slot list options
        elif self.pause_menu_state == "load_slots":
            if idx in [0, 1, 2]:
                self.selected_slot_idx = idx
                self.pause_menu_state = "slot_actions"
                self.pause_select_idx = 0
            elif idx == 3:
                # Cancel / Back
                if getattr(game, "_from_main_menu", False):
                    game.game_state = STATE_MENU
                else:
                    self.pause_menu_state = "main"
                    self.pause_select_idx = 2

        # 4. Slot Action options
        elif self.pause_menu_state == "slot_actions":
            meta = self.slots_meta.get(self.selected_slot_idx + 1, {"exists": False})
            
            # Determine options list
            if self.pause_action_source == "save":
                opts = ["Create Save" if not meta["exists"] else "Overwrite Save", "Rename Profile", "Delete Save", "Back"]
            else:
                opts = ["Load Profile", "Rename Profile", "Delete Save", "Back"]
                if not meta["exists"]:
                    opts = ["Back"]
            
            # Out of bounds safety check
            if idx >= len(opts):
                return
                
            action = opts[idx]
            
            if action in ["Create Save", "Overwrite Save"]:
                from rpg.save import SaveSystem
                # Save the game
                SaveSystem.save_game(game.player, game.quest_manager, game.world_manager, slot=self.selected_slot_idx + 1)
                self.refresh_slots_metadata()
                self.pause_menu_state = "main"
                self.pause_select_idx = 1
                game.game_state = STATE_PLAYING
            elif action == "Load Profile":
                from rpg.save import SaveSystem
                # Load the game
                if SaveSystem.load_game(game.player, game.quest_manager, game.world_manager, slot=self.selected_slot_idx + 1):
                    game.game_state = STATE_PLAYING
                self.pause_menu_state = "main"
                self.pause_select_idx = 2
            elif action == "Rename Profile":
                if meta["exists"]:
                    self.pause_menu_state = "rename_input"
                    self.rename_input_text = meta["slot_name"]
            elif action == "Delete Save":
                if meta["exists"]:
                    from rpg.save import SaveSystem
                    SaveSystem.delete_slot(self.selected_slot_idx + 1)
                    self.refresh_slots_metadata()
                    # Go back to slots list
                    self.pause_menu_state = self.pause_action_source + "_slots"
                    self.pause_select_idx = self.selected_slot_idx
            elif action == "Back":
                self.pause_menu_state = self.pause_action_source + "_slots"
                self.pause_select_idx = self.selected_slot_idx

def cy_crafting(cy: int) -> int:
    return cy
