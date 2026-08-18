"""
Echoes of Asterra - User Interface Manager
Manages all game states overlays: HUD, Menus (Main, Settings, Pause), RPG panels
(Inventory, Character Stats, Quest Log, Crafting Anvil), Shop trade UI, and Victory / Game Over.
"""
import os
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
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
                    "tiny": load_custom_font(9, bold=True),
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
        self.shop_goods = ["Red Potion", "Blue Potion", "Baked Bread", "Oak Wood", "Iron Ore", "Steel Blade", "Wooden Shield"]
        self.shop_prices = {
            "Red Potion": (15, 5),      # (Buy, Sell)
            "Blue Potion": (20, 7),
            "Baked Bread": (10, 3),
            "Oak Wood": (12, 5),
            "Iron Ore": (25, 10),
            "Steel Blade": (100, 30),
            "Wooden Shield": (40, 12),
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
        self.settings_options = ["Music Volume", "SFX Volume", "Display Mode", "Target FPS", "Difficulty Preset", "Back to Menu"]

        # Tutorial multi-page selection index
        self.tutorial_page_idx = 0


        # Progression / Exploration log selection index
        self.progression_select_idx = 0

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

        # Banner notification system
        self.banner_title: str = ""
        self.banner_subtitle: str = ""
        self.banner_color: Tuple[int, int, int] = (240, 140, 30)
        self.banner_timer: float = 0.0
        self.banner_duration: float = 4.0

        # Centralized Managers
        from rpg.celebration import CelebrationManager
        from rpg.notification import NotificationManager
        self.celebration = CelebrationManager()
        self.notifications = NotificationManager()
        self.notification_manager = self.notifications


        # Progressive Information Disclosure Timers
        self.playtime_seconds: float = 0.0
        self.onboarding_stage: int = 0 # 0: Talk only, 1: Combat prompts, 2: Inventory tutorial, 3: Toasts active, 4: Forecasts active

        # Double click tracker & WASD inventory selection cursor
        self.last_click_time = 0
        self.last_click_slot = -1
        self.selected_inventory_slot: int = 0


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
            "tiny": pygame.font.SysFont("Arial", 10, bold=True),
            "small": pygame.font.SysFont("Arial", 14),
            "medium": pygame.font.SysFont("Arial", 18, bold=True),
            "large": pygame.font.SysFont("Arial", 28, bold=True),
            "title": pygame.font.SysFont("Arial", 48, bold=True)
        }


    def _render_wrapped_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        x: int,
        y: int,
        max_width: int,
        line_spacing: int = 18
    ) -> int:
        """Renders multi-line wrapped text with clean newline support without ballooning blank line height."""
        paragraphs = text.split("\n")
        curr_y = y

        for para in paragraphs:
            para_str = para.strip()
            if not para_str:
                curr_y += 6
                continue

            words = para_str.split(" ")
            current_line = []
            for word in words:
                test_line = " ".join(current_line + [word])
                if font.size(test_line)[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        line_txt = " ".join(current_line)
                        surf = font.render(line_txt, True, color)
                        surface.blit(surf, (x, curr_y))
                        curr_y += line_spacing
                    current_line = [word]
            if current_line:
                line_txt = " ".join(current_line)
                surf = font.render(line_txt, True, color)
                surface.blit(surf, (x, curr_y))
                curr_y += line_spacing

        return curr_y

    def toggle_panel(self, panel_name: str, game: Any = None) -> None:
        """Toggles visibility of an RPG panel (inventory, character, quests, crafting, progression). Enforces exclusive single active panel."""
        if panel_name in self.open_panels:
            self.open_panels.remove(panel_name)
        else:
            # Exclusive single panel mode: Close all other active panels
            self.open_panels.clear()
            self.open_panels.add(panel_name)
            if panel_name == "inventory" and game and hasattr(game, "event_bus"):
                game.event_bus.emit("first_inventory_open")


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
            self.draw_pause_menu(surface, game)

        elif state == STATE_GAME_OVER:
            self.draw_game_over(surface)
        elif state == STATE_VICTORY:
            self.draw_victory(surface)
        elif state == STATE_PLAYING or state == STATE_DIALOGUE or state == STATE_SHOP:
            self.draw_gameplay_layers(surface, game)

    def draw_gameplay_layers(self, surface: pygame.Surface, game: Any) -> None:
        """Renders standard HUD, minimap, dialogue boxes, shops, and active panels."""
        dt = getattr(game, "dt", 0.016)
        self.playtime_seconds += dt

        # Progressive Information Disclosure Stages:
        # 0: <30s (Talk prompt only), 1: 30-120s (Combat prompts), 2: 120-300s (Inventory tutorial), 3: 300-420s (Toasts active), 4: >420s (Forecasts active)
        if self.playtime_seconds > 420.0: self.onboarding_stage = 4
        elif self.playtime_seconds > 300.0: self.onboarding_stage = 3
        elif self.playtime_seconds > 120.0: self.onboarding_stage = 2
        elif self.playtime_seconds > 30.0: self.onboarding_stage = 1
        else: self.onboarding_stage = 0

        # Update managers
        self.celebration.update(dt)
        self.notifications.update(dt)

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
        if "progression" in self.open_panels:
            self.draw_exploration_log_panel(surface, game)

        # 4. Dialogue Box
        if game.game_state == STATE_DIALOGUE:
            self.draw_dialogue_box(surface, game.dialogue_manager)

        # 5. Shop Interface
        elif game.game_state == STATE_SHOP:
            self.draw_shop_interface(surface, game.player)

        # 6. Render Low-HP Red Screen Vignette (<25% HP)
        if hasattr(game, "effects_manager") and hasattr(game, "player"):
            hp_r = game.player.hp / max(1.0, float(game.player.max_hp))
            game.effects_manager.draw_low_hp_vignette(surface, hp_r)

        # 7. Render Floor Interaction Prompts
        self.draw_floor_interaction_prompts(surface, game)

        # 7b. Render Seasonal Festival Minigame Overlay (if active)
        self.draw_festival_minigame_overlay(surface, game)

        # 8. Render Stacked Notification Feed
        self.notifications.draw(surface, self.fonts, SCREEN_WIDTH)


        # 9. Render Screen-Centered Top Banner & Celebration Overlay
        self.celebration.draw(surface, self.fonts, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.draw_banner_notification(surface, dt)

        # 10. Render dragged item outline on top of everything
        if game.player.inventory.dragged_item:
            m_pos = pygame.mouse.get_pos()
            icon = pygame.transform.scale(game.player.inventory.dragged_item.icon, (36, 36))
            surface.blit(icon, (m_pos[0] - 18, m_pos[1] - 18))

        # 11. Render Tooltip popup on hover with Side-by-Side comparison
        if self.hovered_item:
            tooltip_pos = pygame.mouse.get_pos()
            if "inventory" in self.open_panels:
                ix, iy, iw = 40, 120, 340
                sel_slot = getattr(self, "selected_inventory_slot", 0)
                row = sel_slot // 6
                grid_start_y = iy + 52
                slot_row_y = grid_start_y + row * 52
                tooltip_pos = (ix + iw + 16, slot_row_y - 8)

            self.draw_tooltip(surface, self.hovered_item, tooltip_pos, player=game.player)


    def show_banner(self, title: str, subtitle: str = "", color: Tuple[int, int, int] = (240, 140, 30), duration: float = 4.0) -> None:
        """Displays a screen-centered top banner message overlay."""
        self.banner_title = title
        self.banner_subtitle = subtitle
        self.banner_color = color
        self.banner_timer = duration
        self.banner_duration = duration

    def draw_banner_notification(self, surface: pygame.Surface, dt: float) -> None:
        """Renders active top banner notification just below HUD at Y=90."""
        if self.banner_timer <= 0:
            return

        self.banner_timer = max(0.0, self.banner_timer - dt)

        # Calculate alpha fade
        alpha = 240
        if self.banner_timer > self.banner_duration - 0.3:
            alpha = int(240 * ((self.banner_duration - self.banner_timer) / 0.3))
        elif self.banner_timer < 0.5:
            alpha = int(240 * (self.banner_timer / 0.5))

        alpha = max(0, min(240, alpha))
        if alpha <= 0:
            return

        t_surf = self.fonts["large"].render(self.banner_title, True, self.banner_color)
        sub_surf = self.fonts["small"].render(self.banner_subtitle, True, (230, 240, 250)) if self.banner_subtitle else None

        req_w = max(t_surf.get_width(), sub_surf.get_width() if sub_surf else 0) + 40
        w = max(420, min(SCREEN_WIDTH - 60, req_w))
        h = 58 if sub_surf else 42
        x = (SCREEN_WIDTH - w) // 2
        y = 90

        banner_bg = pygame.Surface((w, h), pygame.SRCALPHA)
        banner_bg.fill((16, 22, 34, alpha))
        surface.blit(banner_bg, (x, y))

        pygame.draw.rect(surface, (*self.banner_color, alpha), (x, y, w, h), width=2, border_radius=4)

        surface.blit(t_surf, (x + (w - t_surf.get_width()) // 2, y + 6))
        if sub_surf:
            surface.blit(sub_surf, (x + (w - sub_surf.get_width()) // 2, y + 32))

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

        # 5e. Quick Skill Hotkeys (Far Right: Q, E, C, X)
        box_sz = 34
        box_gap = 38
        hx = SCREEN_WIDTH - 162
        hy = 14

        skills_layout = [
            ("Q", "Fireb", player.skill_manager.skills[SKILL_FIREBALL]),
            ("E", "IceSp", player.skill_manager.skills[SKILL_ICE_SPIKE]),
            ("C", "Heal", player.skill_manager.skills[SKILL_HEALING]),
            ("X", "Dash", player.skill_manager.skills[SKILL_DASH])
        ]

        for idx, (key, label, skill) in enumerate(skills_layout):
            sx = hx + idx * box_gap
            sy = hy
            box = pygame.Rect(sx, sy, box_sz, box_sz)
            pygame.draw.rect(surface, COLOR_UI_BG[:3], box, border_radius=4)

            border_c = COLOR_UI_HIGHLIGHT if skill.unlocked else COLOR_GRAY
            pygame.draw.rect(surface, border_c, box, 1 if skill.timer <= 0 else 2, border_radius=4)

            if skill.unlocked and skill.timer > 0:
                cooldown_ratio = skill.timer / skill.cooldown
                shader_h = int(box_sz * cooldown_ratio)
                pygame.draw.rect(surface, (100, 10, 10, 180), (sx, sy + box_sz - shader_h, box_sz, shader_h), border_radius=4)
                cd_lbl = self.fonts["tiny"].render(f"{skill.timer:.1f}s", True, COLOR_RED)
                surface.blit(cd_lbl, (sx + box_sz // 2 - cd_lbl.get_width() // 2, sy + 10))
            else:
                lbl = self.fonts["tiny"].render(label[:4], True, COLOR_UI_TEXT if skill.unlocked else COLOR_GRAY)
                surface.blit(lbl, (sx + box_sz // 2 - lbl.get_width() // 2, sy + 14))

            num_lbl = self.fonts["tiny"].render(key, True, COLOR_WHITE)
            surface.blit(num_lbl, (sx + 2, sy + 1))

        # 5f. Quick Item Consumable Hotbar (Keys 1-4, positioned directly to the left of Skills)
        item_hx = hx - 160
        item_hy = hy
        if hasattr(player.inventory, "quick_slots"):
            for s_num in range(1, 5):
                sx = item_hx + (s_num - 1) * box_gap
                sy = item_hy
                box = pygame.Rect(sx, sy, box_sz, box_sz)
                pygame.draw.rect(surface, (25, 28, 38), box, border_radius=4)

                bound_name = player.inventory.quick_slots.get(s_num)
                found_item = None
                if bound_name:
                    for it in player.inventory.slots:
                        if it and it.name == bound_name:
                            found_item = it
                            break

                if found_item:
                    icon_img = pygame.transform.scale(found_item.icon, (20, 20))
                    surface.blit(icon_img, (sx + 7, sy + 7))
                    pygame.draw.rect(surface, (255, 215, 0), box, 1, border_radius=4)
                    if found_item.quantity > 1:
                        q_lbl = self.fonts["tiny"].render(str(found_item.quantity), True, COLOR_WHITE)
                        surface.blit(q_lbl, (sx + box_sz - q_lbl.get_width() - 2, sy + box_sz - q_lbl.get_height() - 1))
                else:
                    pygame.draw.rect(surface, (60, 65, 75), box, 1, border_radius=4)
                    if bound_name:
                        name_sub = self.fonts["tiny"].render(bound_name[:3], True, (130, 130, 130))
                        surface.blit(name_sub, (sx + 3, sy + 14))

                key_lbl = self.fonts["tiny"].render(f"[{s_num}]", True, (255, 215, 0) if found_item else (150, 150, 150))
                surface.blit(key_lbl, (sx + 2, sy + 1))

        # 6. Dynamic Boss HP & Posture Stagger Bar (when boss enemy is present)
        if game and hasattr(game, "enemies"):
            boss = next((e for e in game.enemies if getattr(e, "enemy_key", "") in ["boss", "demon_lord", "dragon"] or getattr(e, "name", "").startswith("Shadow") or getattr(e, "is_boss", False)), None)
            if boss and getattr(boss, "hp", 0) > 0:
                bw, bh = 420, 16
                bx = SCREEN_WIDTH // 2 - bw // 2
                by = SCREEN_HEIGHT - 65
                self._draw_hud_bar(surface, bx, by, bw, bh, boss.hp, boss.max_hp, COLOR_RED, f"BOSS: {boss.name.upper()}")
                stagger_pct = max(0.0, min(1.0, boss.poise / max(1.0, boss.max_poise)))
                stagger_bar_box = pygame.Rect(bx, by + 18, bw, 8)
                pygame.draw.rect(surface, (40, 40, 20), stagger_bar_box, border_radius=2)
                fill_w = int(bw * (1.0 - stagger_pct))
                if getattr(boss, "is_staggered", False):
                    pygame.draw.rect(surface, COLOR_YELLOW, (bx, by + 18, bw, 8), border_radius=2)
                    stg_lbl = self.fonts["tiny"].render("STAGGERED! (TAKING 2x DAMAGE)", True, COLOR_YELLOW)
                    surface.blit(stg_lbl, (bx + bw // 2 - stg_lbl.get_width() // 2, by + 28))
                else:
                    pygame.draw.rect(surface, (255, 180, 40), (bx, by + 18, fill_w, 8), border_radius=2)
                pygame.draw.rect(surface, COLOR_UI_BORDER, stagger_bar_box, 1, border_radius=2)

        # 7. Style Scoring Combat HUD (only during active combat)
        if game and hasattr(game, "style_scoring"):
            self._draw_style_scoring_hud(surface, player, game)

        # 8. Companion Party HUD Widget
        self._draw_companion_hud(surface, game)

    def _draw_companion_hud(self, surface: pygame.Surface, game: Any) -> None:
        """Renders active party companion status card under the left HUD."""
        if not game or not hasattr(game, "companion_manager") or not game.companion_manager:
            return
        active_comp = game.companion_manager.get_active_companion()
        if not active_comp or not active_comp.is_in_party:
            return

        comp_w, comp_h = 160, 42
        comp_rect = pygame.Rect(20, 88, comp_w, comp_h)
        pygame.draw.rect(surface, (25, 28, 35), comp_rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_UI_BORDER, comp_rect, 1, border_radius=4)

        mode_colors = {
            "attack": (255, 120, 100),
            "tank": (100, 180, 255),
            "heal": (100, 255, 140)
        }
        c_name_lbl = self.fonts["tiny"].render(f"🤝 {active_comp.name} (Lv.{active_comp.level})", True, COLOR_WHITE)
        m_color = mode_colors.get(active_comp.mode, COLOR_WHITE)
        mode_lbl = self.fonts["tiny"].render(f"[{active_comp.mode.upper()[:3]}]", True, m_color)
        surface.blit(c_name_lbl, (26, 92))
        surface.blit(mode_lbl, (comp_rect.right - mode_lbl.get_width() - 6, 92))

        # Mini HP Bar
        bar_w, bar_h = 148, 6
        bx, by = 26, 114
        pygame.draw.rect(surface, (15, 17, 22), (bx, by, bar_w, bar_h), border_radius=2)
        hp_ratio = max(0.0, min(1.0, active_comp.hp / float(active_comp.max_hp)))
        pygame.draw.rect(surface, (60, 200, 80), (bx, by, int(bar_w * hp_ratio), bar_h), border_radius=2)

    def draw_festival_minigame_overlay(self, surface: pygame.Surface, game: Any) -> None:
        """Renders the active seasonal festival minigame modal overlay."""
        minigame_id = getattr(self, "active_festival_minigame", None)
        if not minigame_id or not hasattr(game, "festival_manager") or not game.festival_manager:
            return

        fm = game.festival_manager
        pw, ph = 420, 260
        px = (SCREEN_WIDTH - pw) // 2
        py = (SCREEN_HEIGHT - ph) // 2
        box = pygame.Rect(px, py, pw, ph)

        pygame.draw.rect(surface, (20, 22, 30), box, border_radius=8)
        pygame.draw.rect(surface, COLOR_GOLD, box, 2, border_radius=8)

        cls_hint = self.fonts["tiny"].render("[ESC] Exit", True, COLOR_GRAY)
        surface.blit(cls_hint, (px + pw - cls_hint.get_width() - 12, py + 12))

        if minigame_id == "archery":
            hdr = self.fonts["medium"].render("🎯 Village Festival Archery Contest", True, COLOR_GOLD)
            surface.blit(hdr, (px + 16, py + 16))

            desc = self.fonts["small"].render(f"Arrows Remaining: {fm.archery_shots_left} / 5  •  Score: {fm.archery_accumulated_score}", True, COLOR_WHITE)
            surface.blit(desc, (px + 16, py + 50))

            dt = getattr(game, "dt", 0.016)
            gauge_speed = getattr(self, "archery_gauge_speed", 1.8)
            gauge_dir = getattr(self, "archery_gauge_dir", 1)
            gauge_pos = getattr(self, "archery_gauge_pos", 0.5) + gauge_dir * gauge_speed * dt
            if gauge_pos >= 1.0:
                gauge_pos = 1.0
                gauge_dir = -1
            elif gauge_pos <= 0.0:
                gauge_pos = 0.0
                gauge_dir = 1
            self.archery_gauge_pos = gauge_pos
            self.archery_gauge_dir = gauge_dir

            gx, gy = px + 30, py + 90
            gw, gh = 360, 28
            pygame.draw.rect(surface, (35, 38, 48), (gx, gy, gw, gh), border_radius=4)
            pygame.draw.rect(surface, (80, 85, 95), (gx, gy, gw, gh), 1, border_radius=4)

            bx_start = gx + int(gw * 0.45)
            bx_w = int(gw * 0.10)
            pygame.draw.rect(surface, (255, 215, 0), (bx_start, gy, bx_w, gh), border_radius=2)

            ix_start = gx + int(gw * 0.35)
            ix_w = int(gw * 0.30)
            pygame.draw.rect(surface, (100, 200, 255), (ix_start, gy, ix_w, gh), 2, border_radius=2)

            mx = gx + int(gw * gauge_pos)
            pygame.draw.line(surface, (255, 60, 60), (mx, gy - 6), (mx, gy + gh + 6), 4)

            prompt = self.fonts["medium"].render("Press [SPACE] or [J] to Shoot!", True, COLOR_YELLOW)
            surface.blit(prompt, (px + pw // 2 - prompt.get_width() // 2, py + 160))

        elif minigame_id == "harvest":
            hdr = self.fonts["medium"].render("🌾 Village Harvest Sprint", True, COLOR_GREEN)
            surface.blit(hdr, (px + 16, py + 16))

            dt = getattr(game, "dt", 0.016)
            self.harvest_sprint_timer = max(0.0, getattr(self, "harvest_sprint_timer", 15.0) - dt)
            time_left = self.harvest_sprint_timer
            crops = getattr(self, "harvest_sprint_crops", 0)

            t_lbl = self.fonts["medium"].render(f"Time Left: {time_left:.1f}s", True, COLOR_RED if time_left < 5.0 else COLOR_WHITE)
            c_lbl = self.fonts["medium"].render(f"Crops Gathered: {crops} / 8", True, COLOR_YELLOW)
            surface.blit(t_lbl, (px + 16, py + 52))
            surface.blit(c_lbl, (px + 16, py + 86))

            bar_w, bar_h = 360, 20
            bx, by = px + 30, py + 130
            pygame.draw.rect(surface, (35, 38, 48), (bx, by, bar_w, bar_h), border_radius=4)
            pygame.draw.rect(surface, (60, 200, 80), (bx, by, int(bar_w * (crops / 8.0)), bar_h), border_radius=4)

            if time_left <= 0.0:
                res = fm.finalize_minigame_score("harvest", fm.evaluate_harvest_sprint(crops, 0.0), season=game.world_state.season, player=game.player)
                self.active_festival_minigame = None
                self.show_banner("HARVEST SPRINT COMPLETE", f"Score: {res['score']} ({res['tier']} Tier)! +{res['gold']}g", color=(100, 255, 100))
            else:
                prompt = self.fonts["medium"].render("Mash [F] / [SPACE] to Harvest Crops!", True, COLOR_WHITE)
                surface.blit(prompt, (px + pw // 2 - prompt.get_width() // 2, py + 180))

        elif minigame_id == "feast":
            hdr = self.fonts["medium"].render("🍖 Dennis's Feast & Brew Challenge", True, (255, 160, 80))
            surface.blit(hdr, (px + 16, py + 16))

            score_txt = self.fonts["small"].render(f"Your Score: {fm.feast_player_score}  •  Dennis Target: {fm.feast_dennis_score}", True, COLOR_WHITE)
            surface.blit(score_txt, (px + 16, py + 50))

            f_lbl = self.fonts["small"].render(f"Fullness: {fm.feast_player_fullness} / 100", True, COLOR_RED if fm.feast_player_fullness > 80 else COLOR_YELLOW)
            surface.blit(f_lbl, (px + 16, py + 76))

            bar_w, bar_h = 360, 16
            bx, by = px + 30, py + 98
            pygame.draw.rect(surface, (35, 38, 48), (bx, by, bar_w, bar_h), border_radius=3)
            f_color = COLOR_RED if fm.feast_player_fullness > 80 else (255, 180, 40)
            pygame.draw.rect(surface, f_color, (bx, by, int(bar_w * min(1.0, fm.feast_player_fullness / 100.0)), bar_h), border_radius=3)
            pygame.draw.rect(surface, (80, 85, 95), (bx, by, bar_w, bar_h), 1, border_radius=3)

            opts = [
                ("[1] Roast Boar (+25 pts, +22 Fullness)", (255, 200, 120)),
                ("[2] Honey Mead (+15 pts, +14 Fullness)", (255, 220, 140)),
                ("[3] Pace Yourself (+5 pts, -12 Fullness)", (140, 220, 180)),
                ("[4/Space] Pass / Lock In Score", COLOR_WHITE)
            ]
            for idx, (opt_txt, opt_col) in enumerate(opts):
                o_lbl = self.fonts["tiny"].render(opt_txt, True, opt_col)
                surface.blit(o_lbl, (px + 30, py + 130 + idx * 24))

    def _draw_style_scoring_hud(self, surface: pygame.Surface, player: Any, game: Any) -> None:
        """
        Renders a compact combat style meter in the top-right area (below skill hotbar).
        Shows current grade letter, combo count, and style meter fill.
        Only visible when player is in active combat.
        """
        if not hasattr(game, "style_scoring"):
            return

        # Only show during active combat
        if getattr(player, "out_of_combat_timer", 5.0) > 2.0:
            return

        ss = game.style_scoring
        grade = ss.evaluate()
        grade_color = ss.get_grade_color()

        # Position: below skill hotbar on the right
        panel_w, panel_h = 110, 50
        px = SCREEN_WIDTH - panel_w - 12
        py = 68

        # Semi-transparent panel background
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((15, 18, 25, 180))
        pygame.draw.rect(panel_surf, grade_color + (160,), (0, 0, panel_w, panel_h), 1, border_radius=5)
        surface.blit(panel_surf, (px, py))

        # Grade letter (large, left side)
        grade_lbl = self.fonts["large"].render(grade, True, grade_color)
        surface.blit(grade_lbl, (px + 8, py + 6))

        # "RANK" tiny label above grade
        rank_lbl = self.fonts["tiny"].render("RANK", True, (140, 150, 170))
        surface.blit(rank_lbl, (px + 8, py + 2))

        # Combo counter (right side)
        combo = getattr(player, "combo_count", 0)
        if combo > 0:
            combo_lbl = self.fonts["medium"].render(f"x{combo}", True, COLOR_YELLOW)
            surface.blit(combo_lbl, (px + 48, py + 8))

        # Style meter bar (bottom strip)
        bar_x = px + 4
        bar_y = py + panel_h - 10
        bar_w = panel_w - 8
        bar_h = 5

        # Calculate score as 0-100 for the bar fill
        score = 0.0
        score += min(25.0, ss.max_combo * 5.0)
        score += min(20.0, ss.perfect_dodges * 10.0)
        score += min(20.0, ss.parries * 10.0)
        score += min(15.0, ss.elemental_reactions * 7.5)
        score += min(10.0, ss.finishers_landed * 5.0)
        score -= ss.hits_taken * 5.0
        score = max(0.0, min(100.0, score))

        ratio = score / 100.0
        pygame.draw.rect(surface, (30, 30, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            pygame.draw.rect(surface, grade_color, (bar_x, bar_y, fill_w, bar_h), border_radius=2)

        # Kills counter
        if ss.kills > 0:
            kill_lbl = self.fonts["tiny"].render(f"Kills:{ss.kills}", True, (180, 200, 220))
            surface.blit(kill_lbl, (px + 48, py + 30))

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

        # Position unified Clock & Weather box at top center (Compact 188x44)
        box_w, box_h = 188, 44
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

        # 1. Season & Day Line (e.g., "SPRING 12")
        season_str = f"{season[:3]} {day_of_season} · Yr {year}"
        s_lbl = self.fonts["tiny"].render(season_str, True, s_color)
        surface.blit(s_lbl, (bx + 8, by + 5))

        # 2. Digital Clock Line (e.g., "08:30 AM")
        t_lbl = self.fonts["small"].render(clock_str, True, COLOR_WHITE)
        surface.blit(t_lbl, (bx + 8, by + 22))

        # 3. Sun / Moon Icon
        icon_cx = bx + 96
        icon_cy = by + 28
        is_day = 6 <= hours < 18

        if is_day:
            pygame.draw.circle(surface, (255, 220, 50), (icon_cx, icon_cy), 5)
            pygame.draw.circle(surface, (255, 240, 150), (icon_cx, icon_cy), 3)
        else:
            pygame.draw.circle(surface, (200, 230, 255), (icon_cx, icon_cy), 5)
            pygame.draw.circle(surface, (25, 22, 30), (icon_cx - 2, icon_cy - 1), 4)

        # Subtle Vertical Divider
        pygame.draw.line(surface, (65, 70, 85), (bx + 110, by + 6), (bx + 110, by + 38), 1)

        # 4. Integrated Weather Pill (Right side of card)
        w_info = game.weather.get_weather_info() if hasattr(game, "weather") else {
            "name": "Clear Weather", "label": "CLEAR", "icon": "☀️",
            "color": (255, 220, 100), "effects": ["☀️ Sunlit baseline environment"]
        }
        w_rect = pygame.Rect(bx + 114, by + 5, 68, 34)
        pygame.draw.rect(surface, (18, 20, 28), w_rect, border_radius=4)
        pygame.draw.rect(surface, w_info["color"], w_rect, 1, border_radius=4)

        w_txt = f"{w_info['icon']} {w_info['label'][:5]}"
        w_lbl = self.fonts["tiny"].render(w_txt, True, w_info["color"])
        surface.blit(w_lbl, (w_rect.x + (w_rect.w - w_lbl.get_width()) // 2, w_rect.y + 4))

        sub_lbl = self.fonts["tiny"].render("WEATHER", True, (140, 150, 170))
        surface.blit(sub_lbl, (w_rect.x + (w_rect.w - sub_lbl.get_width()) // 2, w_rect.y + 18))

        # 5. Active Greed Curse HUD Badge (if player challenged Greed Altar)
        if hasattr(game, "player") and getattr(game.player, "greed_curse_active", False):
            gb_rect = pygame.Rect(bx + box_w + 10, by + 10, 160, 32)
            pygame.draw.rect(surface, (45, 12, 18), gb_rect, border_radius=4)
            pygame.draw.rect(surface, (255, 60, 60), gb_rect, 1, border_radius=4)
            g_txt = self.fonts["small"].render("GREED CURSE ACTIVATED", True, (255, 180, 60))
            sub_txt = self.fonts["small"].render("ATK +50% | Loot x2", True, (255, 220, 220))
            surface.blit(g_txt, (gb_rect.x + 8, gb_rect.y + 2))
            surface.blit(sub_txt, (gb_rect.x + 8, gb_rect.y + 16))

        # 6. Weather Hover Tooltip Window Check (Triggers when hovering over Weather Pill or Clock Card)
        mx, my = pygame.mouse.get_pos()
        if w_rect.collidepoint(mx, my) or frame_rect.collidepoint(mx, my):
            effects = w_info["effects"]
            tw = 230
            th = 34 + len(effects) * 20 + 8
            tx = max(10, min(SCREEN_WIDTH - tw - 10, bx + box_w // 2 - tw // 2))
            ty = by + box_h + 6

            tip_surf = pygame.Surface((tw, th), pygame.SRCALPHA)
            tip_surf.fill((15, 18, 26, 240))
            surface.blit(tip_surf, (tx, ty))

            pygame.draw.rect(surface, w_info["color"], (tx, ty, tw, th), 2, border_radius=6)

            # Tooltip Header
            hdr_lbl = self.fonts["small"].render(w_info["name"].upper(), True, w_info["color"])
            surface.blit(hdr_lbl, (tx + 10, ty + 8))

            pygame.draw.line(surface, (70, 80, 100), (tx + 8, ty + 28), (tx + tw - 8, ty + 28), 1)

            # Tooltip Bullet Points
            ey = ty + 34
            for eff in effects:
                e_lbl = self.fonts["tiny"].render(eff, True, COLOR_WHITE)
                surface.blit(e_lbl, (tx + 12, ey))
                ey += 20

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
        """Renders the settings screen to adjust volumes and game options."""
        surface.fill(COLOR_BLACK)

        # Title text
        title = self.fonts["title"].render("Settings", True, COLOR_UI_HIGHLIGHT)
        subtitle = self.fonts["medium"].render("Adjust game settings using keyboard or mouse clicks", True, COLOR_GRAY)

        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 75))
        surface.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 130))

        start_y = 175
        box_h = 44
        gap = 12

        # Draw options buttons
        for idx, opt in enumerate(self.settings_options):
            x = SCREEN_WIDTH // 2 - 160
            y = start_y + idx * (box_h + gap)

            box = pygame.Rect(x, y, 320, box_h)
            is_hover = (idx == self.settings_select_idx)
            bg_c = COLOR_UI_BG[:3] if not is_hover else COLOR_UI_HIGHLIGHT
            border_c = COLOR_WHITE if is_hover else COLOR_UI_BORDER
            text_c = COLOR_BLACK if is_hover else COLOR_WHITE

            pygame.draw.rect(surface, bg_c, box, border_radius=6)
            pygame.draw.rect(surface, border_c, box, 1, border_radius=6)

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
            elif idx == 3:
                fps_val = getattr(game, "target_fps", 0)
                fps_str = "MAX (UNCAPPED)" if fps_val == 0 else f"{fps_val} FPS"
                text = f"Target FPS:  <  {fps_str}  >"
            elif idx == 4:
                diff_val = str(getattr(game, "difficulty_profile", "normal")).upper()
                text = f"Difficulty:  <  {diff_val}  >"
            else:
                text = opt

            lbl = self.fonts["medium"].render(text, True, text_c)
            surface.blit(lbl, (x + 160 - lbl.get_width() // 2, y + box_h // 2 - lbl.get_height() // 2))

        # Render active Difficulty Preset guide card below all settings options
        diff_key = getattr(game, "difficulty_profile", "normal").lower()
        diff_guides = {
            "explorer": "Explorer: 75% Enemy HP/Atk · +20% XP · 2.0x HP Regen (Easy Story)",
            "normal": "Normal: 100% Enemy HP/Atk · 1.0x XP · 1.0x HP Regen (Standard RPG)",
            "veteran": "Veteran: 130% Enemy HP · 135% Atk · 0.5x HP Regen (Hard Combat)",
            "nightmare": "Nightmare: 170% Enemy HP · 175% Atk · 0.2x HP Regen (Brutal Challenge)"
        }
        guide_str = diff_guides.get(diff_key, "")
        if guide_str:
            guide_txt = self.fonts["small"].render(guide_str, True, (255, 215, 0))
            card_y = start_y + len(self.settings_options) * (box_h + gap) + 16
            g_rect = guide_txt.get_rect(center=(SCREEN_WIDTH // 2, card_y))

            bg_card = pygame.Rect(g_rect.x - 14, g_rect.y - 6, g_rect.width + 28, g_rect.height + 12)
            pygame.draw.rect(surface, (14, 20, 32), bg_card, border_radius=6)
            pygame.draw.rect(surface, (255, 215, 0), bg_card, width=1, border_radius=6)
            surface.blit(guide_txt, g_rect)



    # --- TUTORIAL SCREEN ---

    # --- TUTORIAL SCREEN ---

    def draw_tutorial(self, surface: pygame.Surface) -> None:
        """Draws a multi-page interactive tutorial overlay detailing keybindings and gameplay mechanics."""
        # Panel Coordinates (Center screen)
        tw, th = 800, 520
        tx = (SCREEN_WIDTH - tw) // 2
        ty = (SCREEN_HEIGHT - th) // 2

        box = pygame.Rect(tx, ty, tw, th)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=8)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=8)

        # Header title
        hdr = self.fonts["large"].render("Echoes of Asterra - Game Guide & Systems", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (tx + tw // 2 - hdr.get_width() // 2, ty + 16))

        # --- Tab Navigation Bar ---
        tabs = [
            "1. Controls",
            "2. Combat & Parry",
            "3. Fast Travel & Bounties",
            "4. Upgrades & Loot"
        ]
        curr_page = self.tutorial_page_idx % len(tabs)

        tab_y = ty + 50
        tab_w = 180
        tab_h = 32
        start_tab_x = tx + (tw - (len(tabs) * (tab_w + 8) - 8)) // 2

        mouse_pos = pygame.mouse.get_pos()

        for idx, tab_name in enumerate(tabs):
            tab_x = start_tab_x + idx * (tab_w + 8)
            tab_rect = pygame.Rect(tab_x, tab_y, tab_w, tab_h)
            is_active = (idx == curr_page)
            is_hover = tab_rect.collidepoint(mouse_pos)

            if is_active:
                bg_col = (0, 140, 180)
                border_col = (0, 220, 255)
                txt_col = COLOR_WHITE
            elif is_hover:
                bg_col = (40, 55, 75)
                border_col = (100, 180, 220)
                txt_col = (200, 230, 255)
            else:
                bg_col = (25, 32, 45)
                border_col = (50, 65, 85)
                txt_col = COLOR_GRAY

            pygame.draw.rect(surface, bg_col, tab_rect, border_radius=4)
            pygame.draw.rect(surface, border_col, tab_rect, 1, border_radius=4)

            t_surf = self.fonts["small"].render(tab_name, True, txt_col)
            surface.blit(t_surf, (tab_x + (tab_w - t_surf.get_width()) // 2, tab_y + (tab_h - t_surf.get_height()) // 2))

        # Divider under tab bar
        content_top_y = tab_y + tab_h + 12
        pygame.draw.line(surface, (60, 70, 90), (tx + 24, content_top_y), (tx + tw - 24, content_top_y), 1)

        content_y = content_top_y + 12

        # --- PAGE CONTENTS ---
        if curr_page == 0:
            # PAGE 0: Controls & Keybindings
            left_controls = [
                ("Move / Walk", "W, A, S, D"),
                ("Sprint Movement", "Hold Left Shift"),
                ("Dodge Roll (I-Frames)", "Spacebar"),
                ("Melee Attack", "Left Click or J"),
                ("Shield Block / Parry", "Right Click or K"),
                ("Valorant Spells / Skills", "Q, E, C, X"),
                ("Quick Item Consumables", "Hotbar Keys 1, 2, 3, 4"),
                ("Interaction", "Press [F] (NPCs, Chests, Portals)")
            ]
            right_controls = [
                ("Backpack Inventory", "Toggle [I]"),
                ("Character Attributes", "Toggle [V]"),
                ("Quest Journal", "Toggle [N]"),
                ("Crafting Forge", "Toggle [G]"),
                ("Exploration Log / World Map", "Toggle [R]"),
                ("Radar Minimap", "Toggle [M]"),
                ("Level Up Cheat", "Press [L]"),
                ("Pause / Settings / Save", "Press [ESC]")
            ]

            col_w = 350
            left_x = tx + 28
            right_x = tx + tw // 2 + 16

            c1_hdr = self.fonts["medium"].render("Combat & Movement Controls", True, (200, 220, 255))
            c2_hdr = self.fonts["medium"].render("Menus & System Shortcuts", True, (200, 220, 255))
            surface.blit(c1_hdr, (left_x, content_y))
            surface.blit(c2_hdr, (right_x, content_y))

            pygame.draw.line(surface, (50, 60, 80), (tx + tw // 2, content_y), (tx + tw // 2, ty + th - 55), 1)

            start_y = content_y + 28
            for idx, (action, bind) in enumerate(left_controls):
                curr_y = start_y + idx * 42
                act_lbl = self.fonts["small"].render(action, True, COLOR_WHITE)
                bind_lbl = self.fonts["small"].render(bind, True, COLOR_UI_HIGHLIGHT)
                surface.blit(act_lbl, (left_x, curr_y))
                surface.blit(bind_lbl, (left_x, curr_y + 16))
                if idx < len(left_controls) - 1:
                    pygame.draw.line(surface, (40, 45, 55), (left_x, curr_y + 36), (left_x + col_w, curr_y + 36), 1)

            for idx, (action, bind) in enumerate(right_controls):
                curr_y = start_y + idx * 36
                act_lbl = self.fonts["small"].render(action, True, COLOR_WHITE)
                bind_lbl = self.fonts["small"].render(bind, True, COLOR_UI_HIGHLIGHT)
                surface.blit(act_lbl, (right_x, curr_y))
                surface.blit(bind_lbl, (right_x + col_w - bind_lbl.get_width(), curr_y))
                if idx < len(right_controls) - 1:
                    pygame.draw.line(surface, (40, 45, 55), (right_x, curr_y + 28), (right_x + col_w, curr_y + 28), 1)

        elif curr_page == 1:
            # PAGE 1: Combat & Parry Mechanics
            sections = [
                ("1. Poise & Break Stagger System", [
                    "• Enemies have a yellow Poise bar under their HP. Poise regenerates over time.",
                    "• Heavy weapons (Hammers/Axes) deal high poise damage; daggers deal fast light poise damage.",
                    "• Breaking poise triggers [STAGGERED!] — freezing enemy movement (1.5s mob / 2.0s elite / 3.0s boss).",
                    "• All attacks against staggered enemies deal 1.75x bonus damage!"
                ]),
                ("2. Timed Shield Parry & Animation Canceling", [
                    "• Raising your shield (Right-Click) within 0.2s of an incoming strike triggers a PERFECT PARRY.",
                    "• Perfect Parry negates 100% damage, triggers [PARRY!], and instantly breaks the attacker's poise.",
                    "• Press Spacebar during attack recovery to cancel animation into an invincible Dodge Roll (I-Frames)."
                ]),
                ("3. Elemental Reactions", [
                    "• Combine elements for extra damage: Fire + Oil = Ignite DOT | Ice + Wet = Freeze Stun | Lightning + Wet = Overload AOE."
                ])
            ]
            cy_pos = content_y
            for sec_title, lines in sections:
                hdr_s = self.fonts["medium"].render(sec_title, True, (255, 215, 0))
                surface.blit(hdr_s, (tx + 28, cy_pos))
                cy_pos += 22
                for line in lines:
                    line_s = self.fonts["small"].render(line, True, (220, 230, 245))
                    surface.blit(line_s, (tx + 36, cy_pos))
                    cy_pos += 18
                cy_pos += 8

        elif curr_page == 2:
            # PAGE 2: Fast Travel & Bounty System
            sections = [
                ("1. Ancient Waypoint Crystals & Fast Travel", [
                    "• Ornate Waypoint Obelisks are located in major regions (Village, Forest, Lake, Cave, Mountain, Ruins).",
                    "• Approach an obelisk and press [F] to permanently activate its waypoint.",
                    "• Fast Travel via Minimap: Click any activated Cyan Diamond on the Minimap radar (M key).",
                    "• Fast Travel via World Map: Open Exploration Log (R key), select an activated region, and click [★ Fast Travel].",
                    "• (Fast travel is disabled during active combat and inside subterranean Crypt depths)."
                ]),
                ("2. Village Notice Board Bounties", [
                    "• Visit the Town Notice Board in Asterra Haven Village to accept kill & gather contracts.",
                    "• Bounties reward Gold and XP scaled to your character level.",
                    "• Track up to 3 bounties simultaneously. Upon completion, return to the Town Board and click [TURN IN]."
                ])
            ]
            cy_pos = content_y
            for sec_title, lines in sections:
                hdr_s = self.fonts["medium"].render(sec_title, True, (0, 220, 255))
                surface.blit(hdr_s, (tx + 28, cy_pos))
                cy_pos += 22
                for line in lines:
                    line_s = self.fonts["small"].render(line, True, (220, 230, 245))
                    surface.blit(line_s, (tx + 36, cy_pos))
                    cy_pos += 20
                cy_pos += 12

        elif curr_page == 3:
            # PAGE 3: Upgrades, Loot & Runes
            sections = [
                ("1. Interactive Settlement Construction", [
                    "• Speak with Blacksmith Dennis or visit the Town Board to upgrade village facilities (Level 1 to 3).",
                    "• Upgrading Blacksmith, Apothecary, and Market unlocks advanced crafting recipes and shop discounts.",
                    "• High-tier items (Iron Aegis, Asterra Sword, Blue Potion) require specific facility levels to forge."
                ]),
                ("2. ARPG Loot Affixes & Socketable Runes", [
                    "• Equipment drops with Rarity tiers (Common, Uncommon, Rare, Epic, Legendary) and stat Affixes.",
                    "• Prefixes (Vicious, Heavy, Titan's) and Suffixes (of Strength, of Precision) boost HP, ATK, Def, and Crit.",
                    "• Gear with open sockets can be socketed with Runes (Rune of Fire, Rune of Vitality, Rune of Shielding).",
                    "• Stats from gear, affixes, and socketed runes automatically aggregate into your character attributes."
                ])
            ]
            cy_pos = content_y
            for sec_title, lines in sections:
                hdr_s = self.fonts["medium"].render(sec_title, True, (255, 180, 60))
                surface.blit(hdr_s, (tx + 28, cy_pos))
                cy_pos += 22
                for line in lines:
                    line_s = self.fonts["small"].render(line, True, (220, 230, 245))
                    surface.blit(line_s, (tx + 36, cy_pos))
                    cy_pos += 20
                cy_pos += 12

        # --- Footer Navigation Bar ---
        pygame.draw.line(surface, (60, 70, 90), (tx + 24, ty + th - 44), (tx + tw - 24, ty + th - 44), 1)

        # Prev / Next buttons
        btn_w, btn_h = 100, 26
        prev_rect = pygame.Rect(tx + 28, ty + th - 38, btn_w, btn_h)
        next_rect = pygame.Rect(tx + tw - 28 - btn_w, ty + th - 38, btn_w, btn_h)

        is_prev_hover = prev_rect.collidepoint(mouse_pos)
        is_next_hover = next_rect.collidepoint(mouse_pos)

        pygame.draw.rect(surface, (50, 70, 95) if is_prev_hover else (30, 40, 55), prev_rect, border_radius=4)
        pygame.draw.rect(surface, (0, 180, 216), prev_rect, 1, border_radius=4)
        p_txt = self.fonts["small"].render("< Prev", True, COLOR_WHITE)
        surface.blit(p_txt, (prev_rect.centerx - p_txt.get_width() // 2, prev_rect.centery - p_txt.get_height() // 2))

        pygame.draw.rect(surface, (50, 70, 95) if is_next_hover else (30, 40, 55), next_rect, border_radius=4)
        pygame.draw.rect(surface, (0, 180, 216), next_rect, 1, border_radius=4)
        n_txt = self.fonts["small"].render("Next >", True, COLOR_WHITE)
        surface.blit(n_txt, (next_rect.centerx - n_txt.get_width() // 2, next_rect.centery - n_txt.get_height() // 2))

        hint_str = f"Page {curr_page + 1} of {len(tabs)}  |  Press [A/D or Arrows] to switch  |  [ESC/Enter] to Exit"
        footer = self.fonts["small"].render(hint_str, True, COLOR_GRAY)
        surface.blit(footer, (tx + tw // 2 - footer.get_width() // 2, ty + th - 32))

    # --- PAUSE OVERLAY ---

    def draw_pause_menu(self, surface: pygame.Surface, game: Any = None) -> None:
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

            can_save = True
            if game and hasattr(game, "is_save_allowed"):
                can_save, _ = game.is_save_allowed()


            for idx, opt in enumerate(self.pause_options):
                bx = px + 30
                by = py + 68 + idx * 58

                option_box = pygame.Rect(bx, by, 260, 40)
                is_hover = (idx == self.pause_select_idx)

                is_disabled_save = (opt == "Save Game" and not can_save)

                if is_disabled_save:
                    bg_c = (35, 38, 48) if not is_hover else (45, 48, 58)
                    text_c = COLOR_DARK_GRAY
                    opt_display = "Save Game [UNSAFE]"
                else:
                    bg_c = COLOR_UI_HIGHLIGHT if is_hover else COLOR_DARK_GRAY
                    text_c = COLOR_BLACK if is_hover else COLOR_WHITE
                    opt_display = opt

                pygame.draw.rect(surface, bg_c, option_box, border_radius=4)
                pygame.draw.rect(surface, COLOR_UI_BORDER if not is_disabled_save else (45, 50, 60), option_box, 1, border_radius=4)

                lbl = self.fonts["medium"].render(opt_display, True, text_c)
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
            py = SCREEN_HEIGHT // 2 - 200
            pw, ph = 400, 400

            box = pygame.Rect(px, py, pw, ph)
            pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=8)
            pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=8)

            p_txt = self.fonts["large"].render(f"SLOT {self.selected_slot_idx + 1} ACTIONS", True, COLOR_UI_HIGHLIGHT)
            surface.blit(p_txt, (px + 200 - p_txt.get_width() // 2, py + 20))

            # Draw small slot status info box
            sbx = px + 30
            sby = py + 60
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
                opts = ["Create Save" if not meta["exists"] else "Overwrite Save", "Rename Profile", "Delete Save", "Back"] if meta["exists"] else ["Create Save", "Back"]
            else:
                opts = ["Load Profile", "Rename Profile", "Delete Save", "Back"] if meta["exists"] else ["Back"]


            # Draw action buttons
            for idx, opt in enumerate(opts):
                bx = px + 30
                by = py + 130 + idx * 42

                option_box = pygame.Rect(bx, by, 340, 34)
                is_hover = (idx == self.pause_select_idx)

                # Check for disabled options
                is_disabled = (not meta["exists"] and opt in ["Export Backup", "Rename Profile", "Delete Save", "Load Profile"])

                if is_disabled:
                    bg_c = (25, 25, 25)
                    text_c = COLOR_DARK_GRAY
                else:
                    bg_c = COLOR_UI_HIGHLIGHT if is_hover else COLOR_DARK_GRAY
                    text_c = COLOR_BLACK if is_hover else COLOR_WHITE

                pygame.draw.rect(surface, bg_c, option_box, border_radius=4)
                pygame.draw.rect(surface, COLOR_UI_BORDER if not is_disabled else (35, 35, 35), option_box, 1, border_radius=4)

                lbl = self.fonts["medium"].render(opt, True, text_c)
                surface.blit(lbl, (bx + 170 - lbl.get_width() // 2, by + 17 - lbl.get_height() // 2))



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

        # Draw hint text next to sort button (2 crisp, readable lines)
        h1 = self.fonts["small"].render("[WASD] Select  •  [Enter] Use", True, (140, 220, 255))
        h2 = self.fonts["small"].render("[1-4] Bind Quick-Slot Key", True, COLOR_UI_HIGHLIGHT)
        surface.blit(h1, (ix + 124, iy + ih - 44))
        surface.blit(h2, (ix + 124, iy + ih - 26))

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

                # Mouse hover syncs WASD selection cursor
                is_hover = slot_rect.collidepoint(m_pos)
                if is_hover:
                    self.selected_inventory_slot = idx

                is_selected = (idx == self.selected_inventory_slot)
                bg_color = (65, 75, 95) if is_selected else ((50, 52, 62) if is_hover else (35, 37, 45))

                pygame.draw.rect(surface, bg_color, slot_rect, border_radius=4)

                # Draw item if slot populated
                item = player.inventory.slots[idx]
                if item and idx != player.inventory.dragged_slot_idx:
                    # Item procedural icon
                    icon_img = pygame.transform.scale(item.icon, (32, 32))
                    surface.blit(icon_img, (sx + 6, sy + 6))

                    # Highlight slot border by item rarity color
                    rarity_c = RARITY_COLORS.get(item.rarity, COLOR_UI_BORDER)
                    pygame.draw.rect(surface, rarity_c, slot_rect, 2 if not is_selected else 1, border_radius=4)

                    # Draw stack quantity if > 1
                    if item.quantity > 1:
                        qty_txt = self.fonts["small"].render(str(item.quantity), True, COLOR_WHITE)
                        surface.blit(qty_txt, (sx + slot_sz - qty_txt.get_width() - 4, sy + slot_sz - qty_txt.get_height() - 2))

                    # Render quick-slot key badge (e.g. "[1]") if bound to this item
                    if hasattr(player.inventory, "quick_slots"):
                        for s_num, s_name in player.inventory.quick_slots.items():
                            if s_name == item.name:
                                badge = self.fonts["tiny"].render(f"[{s_num}]", True, (255, 215, 0))
                                surface.blit(badge, (sx + 3, sy + 2))
                                break

                    # Cache hovered/selected item for tooltip popup
                    if is_hover or is_selected:
                        self.hovered_item = item
                else:
                    pygame.draw.rect(surface, COLOR_UI_BORDER, slot_rect, 1, border_radius=4)

                # Render active cyan selection cursor box if selected via WASD/Mouse
                if is_selected:
                    pygame.draw.rect(surface, (0, 220, 255), slot_rect, 3, border_radius=4)

                # Store bounds for click registration
                self.slot_rects["inventory"].append((slot_rect, idx))


    # --- CHARACTER PANEL ---

    def draw_character_panel(self, surface: pygame.Surface, player: Any) -> None:
        """Renders equipment gear sockets, stats listings, and tabbed faction/NPC standings/town dashboard."""
        # Panel Coordinates (Centered)
        cw, ch = 680, 460
        cx = (SCREEN_WIDTH - cw) // 2
        cy = (SCREEN_HEIGHT - ch) // 2

        box = pygame.Rect(cx, cy, cw, ch)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=6)

        # Header Title
        game_ref = getattr(player, "game", None)
        active_title = getattr(getattr(game_ref, "reputation_manager", None), "active_title", "The Wanderer") if game_ref else "The Wanderer"
        hdr = self.fonts["medium"].render(f"Hero Attributes  •  Title: {active_title}", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (cx + 16, cy + 16))

        # Close label & Nav hint
        cls = self.fonts["small"].render("[1-6/Tab] Tabs | [V] Close", True, COLOR_GRAY)
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
        stat_x = cx + 140
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

        # Tab Switcher Header (Right Section)
        active_tab = getattr(self, "active_char_tab", "factions")

        # 6 Tab Buttons (Factions, Social, Town, Achievements, Bestiary, Nemesis)
        tab_x = cx + 290
        tab_y = cy + 52

        tab1_rect = pygame.Rect(tab_x, tab_y, 58, 24)
        tab2_rect = pygame.Rect(tab_x + 62, tab_y, 48, 24)
        tab3_rect = pygame.Rect(tab_x + 114, tab_y, 44, 24)
        tab4_rect = pygame.Rect(tab_x + 162, tab_y, 56, 24)
        tab5_rect = pygame.Rect(tab_x + 222, tab_y, 56, 24)
        tab6_rect = pygame.Rect(tab_x + 282, tab_y, 62, 24)

        for t_idx, (t_rect, t_id, t_lbl_str) in enumerate([
            (tab1_rect, "factions", "Factions"),
            (tab2_rect, "social", "Social"),
            (tab3_rect, "town", "Town"),
            (tab4_rect, "achievements", "Achiev"),
            (tab5_rect, "bestiary", "Bestiary"),
            (tab6_rect, "nemesis", "Nemesis")
        ]):
            t_bg = COLOR_UI_HIGHLIGHT if active_tab == t_id else (40, 42, 50)
            t_fg = COLOR_BLACK if active_tab == t_id else COLOR_WHITE
            pygame.draw.rect(surface, t_bg, t_rect, border_radius=4)
            pygame.draw.rect(surface, COLOR_UI_BORDER, t_rect, 1, border_radius=4)
            lbl = self.fonts["small"].render(t_lbl_str, True, t_fg)
            surface.blit(lbl, (t_rect.centerx - lbl.get_width() // 2, t_rect.centery - lbl.get_height() // 2))

        content_y = tab_y + 34

        # TAB 1: FACTIONS & PERKS
        if active_tab == "factions":
            if hasattr(player, "game") and hasattr(player.game, "factions"):
                fm = player.game.factions
                perk_descriptions = {
                    "knights": "Perk: Road Safety + Patrol Escorts",
                    "mages": "Perk: Mana Regeneration + Arcane Items",
                    "hunters": "Perk: Beast Drops x2 + Alpine Pass",
                    "merchants": "Perk: Trade Discount (up to -20%)",
                    "bandits": "Perk: Black Market Gear",
                    "cultists": "Perk: Dark Alchemy Ingredients"
                }
                for idx, (f_id, fac_data) in enumerate(fm.factions.items()):
                    y_pos = content_y + idx * 58
                    fn_lbl = self.fonts["small"].render(fac_data.name, True, COLOR_WHITE)
                    surface.blit(fn_lbl, (tab_x, y_pos))

                    bar_w, bar_h = 260, 8
                    bx, by = tab_x, y_pos + 16
                    pygame.draw.rect(surface, (30, 32, 40), (bx, by, bar_w, bar_h), border_radius=2)
                    pygame.draw.rect(surface, COLOR_UI_BORDER, (bx, by, bar_w, bar_h), 1, border_radius=2)

                    norm_ratio = (fac_data.reputation + 100) / 200.0
                    bar_color = (60, 200, 80) if fac_data.reputation >= 0 else (220, 60, 60)
                    pygame.draw.rect(surface, bar_color, (bx, by, int(bar_w * norm_ratio), bar_h), border_radius=2)

                    perk_txt = perk_descriptions.get(f_id, "")
                    st_lbl = self.fonts["small"].render(f"{fac_data.standing.title()} ({fac_data.reputation:+d}) - {perk_txt}", True, COLOR_GRAY)
                    surface.blit(st_lbl, (tab_x, by + 10))

        # TAB 2: NPC SOCIAL DIRECTORY
        elif active_tab == "social":
            if hasattr(player, "game") and hasattr(player.game, "npc_memory"):
                nm = player.game.npc_memory
                npc_list = ["Eldrin", "Dennis", "Silas", "Faye", "Mira", "Kai", "Garth"]
                for idx, npc_id in enumerate(npc_list):
                    ny_pos = content_y + idx * 48
                    mem = nm.get_memory(npc_id)
                    rel_val = mem.relationship
                    level_str = mem.friendship_level.replace("_", " ").title()

                    n_lbl = self.fonts["small"].render(f"{npc_id}: {level_str} ({rel_val:+d})", True, COLOR_WHITE)
                    surface.blit(n_lbl, (tab_x, ny_pos))

                    bar_w, bar_h = 260, 8
                    bx, by = tab_x, ny_pos + 18
                    pygame.draw.rect(surface, (30, 32, 40), (bx, by, bar_w, bar_h), border_radius=2)
                    pygame.draw.rect(surface, COLOR_UI_BORDER, (bx, by, bar_w, bar_h), 1, border_radius=2)

                    norm_ratio = max(0.0, min(1.0, (rel_val + 100) / 200.0))
                    bar_color = (100, 200, 255) if rel_val >= 0 else (250, 100, 100)
                    pygame.draw.rect(surface, bar_color, (bx, by, int(bar_w * norm_ratio), bar_h), border_radius=2)
                    pygame.draw.rect(surface, COLOR_UI_BORDER, (bx, by, bar_w, bar_h), 1, border_radius=2)

        # TAB 3: TOWN INFRASTRUCTURE DASHBOARD
        elif active_tab == "town":
            if hasattr(player, "game") and hasattr(player.game, "living_world"):
                st = player.game.living_world.settlement

                # Prosperity Header Card
                prosp_lbl = self.fonts["medium"].render(f"Village Prosperity: {st.prosperity:.1f} / 100", True, COLOR_UI_HIGHLIGHT)
                tier_lbl = self.fonts["small"].render(f"Settlement Growth: Tier {st.growth_tier}", True, COLOR_WHITE)
                surface.blit(prosp_lbl, (tab_x, content_y))
                surface.blit(tier_lbl, (tab_x, content_y + 20))

                # Prosperity Bar
                bar_w, bar_h = 260, 10
                bx, by = tab_x, content_y + 38
                pygame.draw.rect(surface, (30, 32, 40), (bx, by, bar_w, bar_h), border_radius=2)
                pygame.draw.rect(surface, COLOR_UI_BORDER, (bx, by, bar_w, bar_h), 1, border_radius=2)
                p_ratio = min(1.0, max(0.0, st.prosperity / 100.0))
                pygame.draw.rect(surface, (240, 200, 40), (bx, by, int(bar_w * p_ratio), bar_h), border_radius=2)

                # Funded Investments List
                inv_hdr = self.fonts["small"].render("Infrastructure & Investments:", True, COLOR_LIGHT_GRAY)
                surface.blit(inv_hdr, (tab_x, content_y + 56))

                all_investments = [
                    ("silas_market", "Silas Royal Market (-20% Shop Tax)"),
                    ("watchtower", "Village Watchtower (Raid Shield)"),
                    ("master_forge", "Dennis Master Forge (Tier 2 Gear)"),
                    ("bridge_rebuilt", "Northern Stone Bridge (Lake Access)"),
                    ("watchtower_built", "Road Watchtower (Cavern Access)")
                ]

                for idx, (inv_id, inv_name) in enumerate(all_investments):
                    iy = content_y + 76 + idx * 24
                    is_done = st.is_investment_completed(inv_id) or st.upgrades.get(inv_id, False)
                    status_str = "[ACTIVE]" if is_done else "[NOT BUILT]"
                    status_c = (60, 200, 80) if is_done else COLOR_GRAY

                    lbl = self.fonts["small"].render(f"{status_str} {inv_name}", True, status_c)
                    surface.blit(lbl, (tab_x, iy))

        # TAB 4: ACHIEVEMENTS & MILESTONES
        elif active_tab == "achievements":
            if hasattr(player, "game") and hasattr(player.game, "achievement_manager"):
                am = player.game.achievement_manager
                ach_list = list(am.achievements.values())
                unlocked_cnt = sum(1 for a in ach_list if a.unlocked)
                
                header_str = f"Achievements: {unlocked_cnt}/{len(ach_list)} Unlocked"
                h_lbl = self.fonts["small"].render(header_str, True, COLOR_UI_HIGHLIGHT)
                surface.blit(h_lbl, (tab_x, content_y))

                for idx, ach in enumerate(ach_list):
                    ay = content_y + 24 + idx * 42
                    status_c = (255, 215, 0) if ach.unlocked else COLOR_GRAY
                    status_tag = f"[{ach.category}]"
                    title_str = f"{ach.icon_symbol} {ach.title} {status_tag}"
                    
                    t_lbl = self.fonts["small"].render(title_str, True, status_c)
                    d_lbl = self.fonts["tiny"].render(ach.description, True, (170, 175, 185) if ach.unlocked else (100, 105, 115))
                    
                    surface.blit(t_lbl, (tab_x, ay))
                    surface.blit(d_lbl, (tab_x + 16, ay + 18))

        # TAB 5: BESTIARY ENEMY COMPENDIUM
        elif active_tab == "bestiary":
            if hasattr(player, "game") and hasattr(player.game, "bestiary_manager"):
                bm = player.game.bestiary_manager
                b_list = list(bm.entries.values())
                unlocked_cnt = sum(1 for e in b_list if e.unlocked)
                
                header_str = f"Bestiary: {unlocked_cnt}/{len(b_list)} Discovered"
                h_lbl = self.fonts["small"].render(header_str, True, COLOR_UI_HIGHLIGHT)
                surface.blit(h_lbl, (tab_x, content_y))

                for idx, entry in enumerate(b_list):
                    ey = content_y + 22 + idx * 38
                    status_c = COLOR_WHITE if entry.unlocked else COLOR_GRAY
                    name_str = f"📖 {entry.name}" if entry.unlocked else "❓ Unknown Creature"
                    meta_str = f"Kills: {entry.kills} • Element: {entry.element} • Weakness: {entry.weakness}" if entry.unlocked else "Defeat this enemy to unlock lore & weaknesses"
                    
                    e_lbl = self.fonts["small"].render(name_str, True, status_c)
                    d_lbl = self.fonts["tiny"].render(meta_str, True, COLOR_LIGHT_GRAY if entry.unlocked else (100, 105, 115))
                    
                    surface.blit(e_lbl, (tab_x, ey))
                    surface.blit(d_lbl, (tab_x + 12, ey + 16))

        # TAB 6: NEMESIS CAPTAINS ROSTER
        elif active_tab == "nemesis":
            game_inst = getattr(player, "game", None)
            nemesis_mgr = getattr(game_inst, "nemesis_manager", None) if game_inst else None

            if nemesis_mgr:
                all_caps = list(nemesis_mgr.captains.values())
                active_caps = [c for c in all_caps if c.active and not c.is_defeated]

                header_str = f"Nemesis Captains: {len(active_caps)} Active Menace{'s' if len(active_caps) != 1 else ''}"
                h_lbl = self.fonts["small"].render(header_str, True, COLOR_UI_HIGHLIGHT)
                surface.blit(h_lbl, (tab_x, content_y))

                if not all_caps:
                    empty_lbl = self.fonts["small"].render("No Nemesis captains have emerged yet.", True, COLOR_GRAY)
                    desc_lbl = self.fonts["tiny"].render("Enemies that defeat you or escape combat become Nemesis Captains.", True, (150, 155, 165))
                    surface.blit(empty_lbl, (tab_x, content_y + 30))
                    surface.blit(desc_lbl, (tab_x, content_y + 50))
                else:
                    for idx, cap in enumerate(all_caps[:5]):
                        cy_item = content_y + 24 + idx * 64

                        # Status tag & color
                        if cap.active and not cap.is_defeated:
                            stat_color = (255, 215, 0)
                            status_tag = f"[LV.{cap.level} ACTIVE]"
                        else:
                            stat_color = (120, 125, 135)
                            status_tag = "[SLAIN]"

                        title_sub = f' "{cap.victory_titles[-1]}"' if cap.victory_titles else ""
                        name_str = f"⚔️ {cap.name}{title_sub}"

                        n_lbl = self.fonts["small"].render(name_str, True, stat_color)
                        st_lbl = self.fonts["tiny"].render(status_tag, True, (255, 100, 100) if cap.active else (100, 200, 100))

                        surface.blit(n_lbl, (tab_x, cy_item))
                        surface.blit(st_lbl, (tab_x + 280, cy_item))

                        # Details line 1: Stats & Kills
                        terr_name = cap.claimed_territory.title()
                        det_str = f"Territory: {terr_name}  •  Kills on Hero: {cap.kills_on_player}  •  ATK: {cap.atk}  DEF: {cap.defense}"
                        d_lbl = self.fonts["tiny"].render(det_str, True, (180, 185, 195))
                        surface.blit(d_lbl, (tab_x + 12, cy_item + 18))

                        # Details line 2: Traits
                        traits_str = f"Traits: {', '.join(cap.traits) if cap.traits else 'None'}"
                        t_lbl = self.fonts["tiny"].render(traits_str, True, (210, 160, 255))
                        surface.blit(t_lbl, (tab_x + 12, cy_item + 34))



    # --- QUEST LOG PANEL ---

    def draw_quests_panel(self, surface: pygame.Surface, quest_manager: Any) -> None:
        """Renders active side/main quests tasks checklist."""
        qx, qy = 40, 100
        qw, qh = 480, 440

        box = pygame.Rect(qx, qy, qw, qh)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=6)

        hdr = self.fonts["medium"].render("Quest Journal", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (qx + 16, qy + 16))

        cls = self.fonts["small"].render("[N] Close", True, COLOR_GRAY)
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
            title_str = f"{title_prefix}{quest.title}"
            avail_t_w = qw - 100
            if self.fonts["medium"].size(title_str)[0] > avail_t_w:
                while title_str and self.fonts["medium"].size(title_str + "...")[0] > avail_t_w:
                    title_str = title_str[:-1]
                title_str += "..."

            title_lbl = self.fonts["medium"].render(title_str, True, title_color)
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

                avail_obj_w = qw - 44
                if self.fonts["small"].size(obj_text)[0] > avail_obj_w:
                    while obj_text and self.fonts["small"].size(obj_text + "...")[0] > avail_obj_w:
                        obj_text = obj_text[:-1]
                    obj_text += "..."

                color = COLOR_GREEN if obj.is_complete() else COLOR_LIGHT_GRAY
                obj_lbl = self.fonts["small"].render(obj_text, True, color)
                surface.blit(obj_lbl, (qx + 28, curr_y))
                curr_y += 20

            curr_y += 10  # spacer between quests

    # --- CRAFTING PANEL ---

    def draw_crafting_panel(self, surface: pygame.Surface, player: Any) -> None:
        """Lists recipes and consumes materials to craft items."""
        cx, cy = 40, 100
        cw, ch = 460, 440

        box = pygame.Rect(cx, cy, cw, ch)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=6)

        hdr = self.fonts["medium"].render("Forge Anvil Crafting", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (cx + 16, cy + 16))

        cls = self.fonts["small"].render("[G] Close", True, COLOR_GRAY)
        surface.blit(cls, (cx + cw - cls.get_width() - 16, cy + 18))

        recipes = CraftingSystem.get_recipes_list()

        grid_start_y = cy + 50
        m_pos = pygame.mouse.get_pos()

        # Vertical lists of craftable items
        for idx, recipe_name in enumerate(recipes):
            y_pos = grid_start_y + idx * 36
            recipe_rect = pygame.Rect(cx + 16, y_pos, cw - 32, 32)

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
            surface.blit(name_lbl, (cx + 24, y_pos + 7))

            # Draw required items inline (e.g. Iron: 5/3)
            recipe_data = CRAFTING_RECIPES[recipe_name]
            ingredients = recipe_data[0]
            min_facility_lvl = recipe_data[2] if len(recipe_data) > 2 else 1

            ing_strs = []
            can_craft = True

            settlement = getattr(player.game.living_world, "settlement", None) if hasattr(player, "game") and hasattr(player.game, "living_world") else None
            facility_lvl = settlement.get_facility_level("blacksmith") if settlement else 1
            if facility_lvl < min_facility_lvl:
                can_craft = False
                ing_strs.append(f"Forge Lvl {min_facility_lvl}")

            for ing_name, req_qty in ingredients.items():
                curr_qty = player.inventory.get_item_count(ing_name)
                if curr_qty < req_qty:
                    can_craft = False
                ing_strs.append(f"{ing_name[:4]}:{curr_qty}/{req_qty}")

            ing_lbl_txt = ", ".join(ing_strs)
            ing_color = COLOR_GREEN if can_craft else (COLOR_RED if not is_hover else (180, 50, 50))

            ing_lbl = self.fonts["small"].render(ing_lbl_txt, True, ing_color)
            surface.blit(ing_lbl, (cx + cw - ing_lbl.get_width() - 24, y_pos + 7))

    # --- SILAS MERCHANT SHOP UI ---

    def _get_item_econ_category(self, item_name: str) -> str:
        """Maps shop item names to Living Economy resource stock categories."""
        if "Potion" in item_name or "Herb" in item_name:
            return "herbs"
        elif "Bread" in item_name or "Apple" in item_name or "Food" in item_name:
            return "food"
        elif "Ore" in item_name or "Stone" in item_name or "Ingot" in item_name:
            return "ore"
        return "goods"

    def draw_shop_interface(self, surface: pygame.Surface, player: Any) -> None:
        """Buy and Sell panels interface with Merchant Silas."""
        # Large centered dual window (740x500)
        sw, sh = 740, 500
        sx = (SCREEN_WIDTH - sw) // 2
        sy = (SCREEN_HEIGHT - sh) // 2

        box = pygame.Rect(sx, sy, sw, sh)
        pygame.draw.rect(surface, COLOR_UI_BG, box, border_radius=8)
        pygame.draw.rect(surface, COLOR_UI_BORDER, box, 2, border_radius=8)

        # Header Title
        hdr = self.fonts["large"].render(f"Merchant Silas' Shop (Gold: {player.gold}g)", True, COLOR_UI_HIGHLIGHT)
        surface.blit(hdr, (sx + 24, sy + 18))

        # Close label
        cls = self.fonts["small"].render("[ESC] Exit Shop", True, COLOR_GRAY)
        surface.blit(cls, (sx + sw - cls.get_width() - 24, sy + 24))

        # LEFT PANEL: SILAS SELLS
        left_box = pygame.Rect(sx + 20, sy + 60, 340, 420)
        pygame.draw.rect(surface, COLOR_DARK_GRAY, left_box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, left_box, 1, border_radius=6)

        lbl_s = self.fonts["medium"].render("Silas' Wares (Buy)", True, COLOR_WHITE)
        surface.blit(lbl_s, (sx + 32, sy + 72))

        # Render Active Market Tax/Discount Modifier Badge from Living World Decisions
        if hasattr(player, "game") and hasattr(player.game, "living_world"):
            c_map = getattr(player.game.world_manager, "current_map_name", "village")
            p_scalar = player.game.living_world.get_combined_price_multiplier("goods", c_map)
            perc = int((p_scalar - 1.0) * 100)
            if perc != 0:
                badge_str = f"Tax: +{perc}%" if perc > 0 else f"Discount: {perc}%"
                badge_c = (255, 100, 100) if perc > 0 else (100, 240, 140)
                badge_lbl = self.fonts["small"].render(f"[{badge_str}]", True, badge_c)
                surface.blit(badge_lbl, (sx + 200, sy + 74))

        m_pos = pygame.mouse.get_pos()
        self.slot_rects["shop"].clear()

        # Calculate row height dynamically to fit all shop items cleanly
        n_items = max(1, len(self.shop_goods))
        avail_h = 360
        row_step = min(44, avail_h // n_items)
        row_h = min(36, row_step - 4)

        for idx, item_name in enumerate(self.shop_goods):
            by = sy + 104 + idx * row_step
            row_rect = pygame.Rect(sx + 32, by, 316, row_h)

            # Check Living Economy stock levels for scarcity
            econ_cat = self._get_item_econ_category(item_name)
            stock_ratio = 1.0
            price_scalar = 1.0

            if hasattr(player, "game") and hasattr(player.game, "living_world"):
                current_map = getattr(player.game.world_manager, "current_map_name", "village")
                price_scalar = player.game.living_world.get_combined_price_multiplier(econ_cat, current_map)
                stocks = getattr(player.game.living_world.economy, "stocks", {})
                if econ_cat in stocks:
                    res = stocks[econ_cat]
                    stock_ratio = res.current_stock / max(1.0, res.max_capacity)

            is_out_of_stock = (stock_ratio < 0.30)

            # Hover & background rendering
            is_hover = row_rect.collidepoint(m_pos) and not is_out_of_stock
            if is_out_of_stock:
                bg_c = (35, 37, 42)
            else:
                bg_c = (80, 85, 95) if is_hover else (45, 48, 55)

            pygame.draw.rect(surface, bg_c, row_rect, border_radius=4)
            pygame.draw.rect(surface, (60, 62, 70) if is_out_of_stock else COLOR_UI_BORDER, row_rect, 1, border_radius=4)

            # Icon
            mock_item = create_item(item_name)
            if mock_item:
                icon_img = pygame.transform.scale(mock_item.icon, (24, 24))
                if is_out_of_stock:
                    icon_img.set_alpha(100)
                surface.blit(icon_img, (sx + 38, by + (row_h - 24) // 2))
                if is_hover:
                    self.hovered_item = mock_item

            # Name label
            name_color = (130, 135, 145) if is_out_of_stock else COLOR_WHITE
            name_lbl = self.fonts["small"].render(item_name, True, name_color)
            surface.blit(name_lbl, (sx + 70, by + (row_h - name_lbl.get_height()) // 2))

            # Price / Out of Stock badge
            base_buy, _ = self.shop_prices[item_name]
            buy_price = max(1, int(base_buy * price_scalar))

            if is_out_of_stock:
                stock_lbl = self.fonts["small"].render("OUT OF STOCK", True, (220, 80, 80))
                surface.blit(stock_lbl, (sx + 336 - stock_lbl.get_width() - 12, by + (row_h - stock_lbl.get_height()) // 2))
            else:
                # Color code price based on market conditions & player gold
                if player.gold < buy_price:
                    prc_color = COLOR_RED
                elif price_scalar < 0.90:
                    prc_color = (100, 240, 140)  # Green = discounted
                elif price_scalar > 1.15:
                    prc_color = (255, 140, 60)   # Orange = high demand/tax
                else:
                    prc_color = COLOR_YELLOW

                prc_lbl = self.fonts["medium"].render(f"{buy_price}g", True, prc_color)
                surface.blit(prc_lbl, (sx + 336 - prc_lbl.get_width() - 12, by + (row_h - prc_lbl.get_height()) // 2))

            # Store bounds for click buy actions (only if in stock)
            if not is_out_of_stock:
                self.slot_rects["shop"].append((row_rect, idx))

        # RIGHT PANEL: PLAYER INVENTORY BACKPACK
        right_box = pygame.Rect(sx + 380, sy + 60, 340, 420)
        pygame.draw.rect(surface, COLOR_DARK_GRAY, right_box, border_radius=6)
        pygame.draw.rect(surface, COLOR_UI_BORDER, right_box, 1, border_radius=6)

        lbl_p = self.fonts["medium"].render("Sell Items", True, COLOR_WHITE)
        surface.blit(lbl_p, (sx + 392, sy + 72))

        # Sell All Materials Button
        sell_all_rect = pygame.Rect(sx + 546, sy + 68, 160, 26)
        m_pos = pygame.mouse.get_pos()
        is_sa_hover = sell_all_rect.collidepoint(m_pos)
        pygame.draw.rect(surface, (80, 50, 20) if is_sa_hover else (50, 30, 15), sell_all_rect, border_radius=3)
        pygame.draw.rect(surface, (240, 180, 40), sell_all_rect, width=1, border_radius=3)
        sa_lbl = self.fonts["small"].render("Sell All Junk/Ores", True, COLOR_YELLOW)
        surface.blit(sa_lbl, (sell_all_rect.centerx - sa_lbl.get_width() // 2, sell_all_rect.centery - sa_lbl.get_height() // 2))
        self.slot_rects["sell_all"] = [(sell_all_rect, 0)]

        # Render mini inventory backpack (6 cols, 4 rows)
        grid_start_x = sx + 392
        grid_start_y = sy + 110
        slot_sz = 42
        spacing = 10

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
                    icon_img = pygame.transform.scale(item.icon, (28, 28))
                    surface.blit(icon_img, (x + 7, y + 7))

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

    def draw_floor_interaction_prompts(self, surface: pygame.Surface, game: Any) -> None:
        """Renders subtle floor key hints ([E] Talk, [E] Open Chest) over nearby interactable entities."""
        if getattr(game, "game_state", None) != STATE_PLAYING:
            return
        if self.open_panels:
            return
        if hasattr(game, "dialogue_manager") and getattr(game.dialogue_manager, "current_node", None) is not None:
            return
        if not hasattr(game, "player") or not hasattr(game, "camera"):
            return

        p_pos = game.player.pos
        cam_offset = game.camera.get_offset()
        font = self.fonts.get("small", pygame.font.SysFont("Arial", 14))

        # Check nearby NPCs
        if hasattr(game, "npcs"):
            for npc in game.npcs:
                if hasattr(npc, "pos"):
                    dist = (npc.pos - p_pos).length()
                    if dist <= 54.0:
                        screen_p = npc.pos - cam_offset
                        name_str = getattr(npc, "name", "NPC")
                        prompt_txt = f"[F] Talk to {name_str}"

                        lbl = font.render(prompt_txt, True, (255, 215, 0))
                        bg_w = lbl.get_width() + 16
                        bg_h = 24
                        bx = screen_p.x - bg_w // 2
                        by = screen_p.y - 48

                        bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
                        bg.fill((16, 22, 34, 210))
                        surface.blit(bg, (bx, by))
                        pygame.draw.rect(surface, (0, 180, 216), (bx, by, bg_w, bg_h), width=1, border_radius=4)
                        surface.blit(lbl, (bx + 8, by + 3))

        # Check nearby Chests
        if hasattr(game, "chests"):
            for chest in game.chests:
                if hasattr(chest, "rect"):
                    chest_center = pygame.math.Vector2(chest.rect.center)
                    dist = (chest_center - p_pos).length()
                    if dist <= 58.0:
                        screen_p = chest_center - cam_offset
                        if chest.is_open:
                            prompt_txt = "[Opened Chest]"
                            txt_col = (160, 160, 160)
                            border_col = (80, 80, 80)
                        else:
                            prompt_txt = "[F] Open Chest"
                            txt_col = (255, 215, 0)
                            border_col = (255, 180, 0)

                        lbl = font.render(prompt_txt, True, txt_col)
                        bg_w = lbl.get_width() + 16
                        bg_h = 24
                        bx = screen_p.x - bg_w // 2
                        by = screen_p.y - 42

                        bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
                        bg.fill((16, 22, 34, 220))
                        surface.blit(bg, (bx, by))
                        pygame.draw.rect(surface, border_col, (bx, by, bg_w, bg_h), width=1, border_radius=4)
                        surface.blit(lbl, (bx + 8, by + 3))


    def draw_tooltip(self, surface: pygame.Surface, item: Any, mouse_pos: Tuple[int, int], player: Any = None) -> None:
        """Floating tooltip showing description, stats, rarity colors, and side-by-side equipped gear comparison."""
        tw, th = 240, 136
        is_anchored = "inventory" in self.open_panels
        tx = mouse_pos[0] if is_anchored else mouse_pos[0] + 16
        ty = mouse_pos[1] if is_anchored else mouse_pos[1] + 16

        # Keep tooltip bounded on screen right/bottom boundaries
        if tx + tw > SCREEN_WIDTH: tx = SCREEN_WIDTH - tw - 10
        if ty + th > SCREEN_HEIGHT: ty = SCREEN_HEIGHT - th - 10
        if ty < 10: ty = 10


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

        # 3. Item stats & Side-by-Side Equipment Comparison
        stat_y = ty + 46
        if item.stats:
            eq_item = player.equipment.slots.get(item.item_type) if (player and hasattr(item, "item_type")) else None

            for k, val in item.stats.items():
                eq_val = eq_item.stats.get(k, 0) if (eq_item and hasattr(eq_item, "stats")) else 0
                diff = val - eq_val

                diff_str = ""
                diff_c = COLOR_GREEN
                if eq_item and eq_item != item:
                    if diff > 0:
                        diff_str = f" (+{diff} net gain)"
                        diff_c = (100, 240, 140)
                    elif diff < 0:
                        diff_str = f" ({diff} net drop)"
                        diff_c = (240, 100, 100)
                    else:
                        diff_str = " (= same)"
                        diff_c = COLOR_GRAY

                stat_txt = f"+{val} {k.upper()}{diff_str}"
                stat_lbl = self.fonts["small"].render(stat_txt, True, diff_c)
                surface.blit(stat_lbl, (tx + 10, stat_y))
                stat_y += 18

        # 4. Item Description text (wraps slightly)
        desc_lbl = self.fonts["small"].render(item.description[:38], True, COLOR_WHITE)
        surface.blit(desc_lbl, (tx + 10, stat_y))

    # --- DIALOGUE WINDOW ---

    def draw_dialogue_box(self, surface: pygame.Surface, dialogue_manager: Any) -> None:
        """Typing dialogue node panel at screen bottom with dynamic height, sprite portrait, and collision-free choices list."""
        node = dialogue_manager.current_node
        if not node:
            return

        dw = SCREEN_WIDTH - 80
        max_txt_w = dw - 180

        # Word wrap visible dialogue text with clean paragraph newline handling
        raw_paragraphs = dialogue_manager.visible_text.split("\n")
        lines = []
        for para in raw_paragraphs:
            p_str = para.strip()
            if not p_str:
                continue
            words = p_str.split(" ")
            curr_line = []
            for w in words:
                test_line = " ".join(curr_line + [w])
                if self.fonts["small"].size(test_line)[0] <= max_txt_w:
                    curr_line.append(w)
                else:
                    if curr_line:
                        lines.append(" ".join(curr_line))
                    curr_line = [w]
            if curr_line:
                lines.append(" ".join(curr_line))

        n_choices = len(node.choices) if (dialogue_manager.typing_finished and node.choices) else 0
        text_h = len(lines) * 20
        choices_h = n_choices * 34 + (10 if n_choices > 0 else 0)

        # Dynamic panel height calculation to guarantee zero text/choice overlap
        dh = max(160, 52 + text_h + 16 + choices_h + 16)
        dx = 40
        dy = SCREEN_HEIGHT - dh - 20

        # Warm RPG Dialogue Box (Harvest Moon Parchment Style)
        box = pygame.Rect(dx, dy, dw, dh)
        pygame.draw.rect(surface, (252, 246, 222), box, border_radius=8)
        pygame.draw.rect(surface, (255, 252, 240), box.inflate(-4, -4), border_radius=6)
        pygame.draw.rect(surface, (130, 95, 45), box, 3, border_radius=8)
        pygame.draw.rect(surface, (190, 155, 95), box, 1, border_radius=8)

        # ESC Leave hint badge at top-right of dialogue box
        esc_lbl = self.fonts["small"].render("[ESC] Leave", True, (130, 100, 70))
        surface.blit(esc_lbl, (dx + dw - esc_lbl.get_width() - 18, dy + 14))

        # Speaker portrait socket
        px, py = dx + 18, dy + 18
        pw, ph = 120, 120
        pygame.draw.rect(surface, (235, 225, 195), (px, py, pw, ph), border_radius=6)
        pygame.draw.rect(surface, (130, 95, 45), (px, py, pw, ph), 2, border_radius=6)

        # Draw actual NPC sprite portrait if available
        name_str = node.speaker_name
        short_id = name_str.split()[-1].lower()
        asset_map = {
            "eldrin": "npc_eldrin", "silas": "npc_silas", "dennis": "npc_dennis",
            "faye": "npc_faye", "mira": "npc_mira", "garth": "npc_garth",
            "kai": "npc_kai", "finn": "npc_finn", "spirit": "npc_spirit"
        }
        key = asset_map.get(short_id)
        npc_img = None
        if key:
            from rpg.animation import entity_assets
            from rpg.constants import DIR_DOWN
            frames = entity_assets.get(key, {}).get("idle", {}).get(DIR_DOWN)
            if frames:
                npc_img = frames[0]

        if npc_img:
            scaled = pygame.transform.smoothscale(npc_img, (96, 96))
            surface.blit(scaled, (px + 12, py + 12))
        else:
            # Stylized avatar fallback
            pygame.draw.circle(surface, (230, 180, 140), (px + 60, py + 60), 30)
            pygame.draw.circle(surface, (120, 80, 40), (px + 60, py + 52), 34, 4)
            pygame.draw.circle(surface, COLOR_BLACK, (px + 50, py + 56), 3)
            pygame.draw.circle(surface, COLOR_BLACK, (px + 70, py + 56), 3)
            pygame.draw.circle(surface, COLOR_RED, (px + 60, py + 72), 6, 2)

        # Floating Speaker Name Badge (Harvest Moon Style Nameplate)
        rel_suffix = ""
        if hasattr(dialogue_manager, "game") and hasattr(dialogue_manager.game, "npc_memory"):
            mem = dialogue_manager.game.npc_memory.get_memory(short_id.title())
            rel_level = mem.friendship_level.replace("_", " ").title()
            rel_suffix = f" [{rel_level}]"

        full_name_text = name_str + rel_suffix
        name_lbl = self.fonts["medium"].render(full_name_text, True, COLOR_WHITE)
        badge_w = name_lbl.get_width() + 24
        badge_h = 30
        badge_rect = pygame.Rect(dx + 160, dy - 14, badge_w, badge_h)

        # Nameplate shadow & blue gradient body
        pygame.draw.rect(surface, (20, 30, 50), badge_rect.move(2, 2), border_radius=4)
        pygame.draw.rect(surface, (25, 75, 170), badge_rect, border_radius=4)
        pygame.draw.rect(surface, (255, 215, 0), badge_rect, 2, border_radius=4)
        surface.blit(name_lbl, (badge_rect.x + 12, badge_rect.y + 15 - name_lbl.get_height() // 2))

        # Render dialogue text lines in dark brown pixel text on parchment
        txt_y = dy + 32
        for idx, line in enumerate(lines):
            lbl = self.fonts["small"].render(line, True, (50, 35, 25))
            surface.blit(lbl, (dx + 160, txt_y + idx * 22))

        # Choices list starts cleanly BELOW the last line of text
        if dialogue_manager.typing_finished and node.choices:
            choice_x = dx + 160
            choice_w = dw - 180
            choice_start_y = txt_y + text_h + 12
            m_pos = pygame.mouse.get_pos()

            for idx, choice in enumerate(node.choices):
                cy = choice_start_y + idx * 34
                choice_rect = pygame.Rect(choice_x, cy, choice_w, 30)

                if choice_rect.collidepoint(m_pos):
                    dialogue_manager.selected_choice_idx = idx

                is_selected = (idx == dialogue_manager.selected_choice_idx)
                bg_c = (255, 220, 100) if is_selected else (235, 225, 195)
                border_c = (180, 130, 40) if is_selected else (160, 130, 90)
                text_c = (40, 20, 10) if is_selected else (70, 50, 30)

                pygame.draw.rect(surface, bg_c, choice_rect, border_radius=4)
                pygame.draw.rect(surface, border_c, choice_rect, 2, border_radius=4)

                # Fit choice text cleanly inside choice_rect without overflowing
                avail_choice_w = choice_w - 24
                choice_str = choice.text
                if self.fonts["small"].size(choice_str)[0] > avail_choice_w:
                    while choice_str and self.fonts["small"].size(choice_str + "...")[0] > avail_choice_w:
                        choice_str = choice_str[:-1]
                    choice_str += "..."

                lbl = self.fonts["small"].render(choice_str, True, text_c)
                surface.blit(lbl, (choice_x + 12, cy + 15 - lbl.get_height() // 2))
        elif dialogue_manager.typing_finished:
            hint = self.fonts["small"].render("[Space/Enter] Continue", True, (130, 100, 70))
            surface.blit(hint, (dx + dw - hint.get_width() - 20, dy + dh - 24))


    # --- GAME OVER SCREEN ---

    def draw_game_over(self, surface: pygame.Surface) -> None:
        """Dark red atmospheric game over screen with Respawn vs Reload options."""
        surface.fill((24, 4, 6))

        lbl = self.fonts["title"].render("YOU PERISHED", True, COLOR_RED)

        opt_respawn = self.fonts["medium"].render("[R] Respawn (-25% XP, -30% Gold, Drop Inventory)", True, (255, 215, 0))
        opt_reload = self.fonts["medium"].render("[SPACE] Reload Last Save", True, (220, 220, 220))
        opt_menu = self.fonts["small"].render("[ESC] Return to Main Menu", True, (150, 150, 150))

        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2

        surface.blit(lbl, (cx - lbl.get_width() // 2, cy - 80))
        surface.blit(opt_respawn, (cx - opt_respawn.get_width() // 2, cy - 10))
        surface.blit(opt_reload, (cx - opt_reload.get_width() // 2, cy + 30))
        surface.blit(opt_menu, (cx - opt_menu.get_width() // 2, cy + 70))
        
        mythos_txt = self.fonts["small"].render("✨ Mythos Inheritance: Unlocked traits will be passed to your next hero!", True, (255, 215, 0))
        surface.blit(mythos_txt, (cx - mythos_txt.get_width() // 2, cy + 110))


    # --- VICTORY SCREEN ---

    def draw_victory(self, surface: pygame.Surface) -> None:
        """Triumphant victory splash screen."""
        surface.fill((5, 30, 15))

        lbl = self.fonts["title"].render("VICTORY ACHIEVED!", True, COLOR_GREEN)
        desc = self.fonts["large"].render("Asterra's Core is Purified", True, COLOR_UI_HIGHLIGHT)
        sub = self.fonts["medium"].render("Press [ESC] to return to Main Menu", True, COLOR_WHITE)
        mythos_txt = self.fonts["medium"].render("✨ Mythos Inheritance: Legacy Unlocked (+15% Stats on New Game+)", True, (255, 215, 0))

        surface.blit(lbl, (SCREEN_WIDTH // 2 - lbl.get_width() // 2, SCREEN_HEIGHT // 2 - 80))
        surface.blit(desc, (SCREEN_WIDTH // 2 - desc.get_width() // 2, SCREEN_HEIGHT // 2 - 20))
        surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, SCREEN_HEIGHT // 2 + 50))
        surface.blit(mythos_txt, (SCREEN_WIDTH // 2 - mythos_txt.get_width() // 2, SCREEN_HEIGHT // 2 + 95))


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
                by = 175 + idx * 56
                rect = pygame.Rect(bx, by, 320, 44)

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
                        fps_options = [30, 60, 120, 144, 0]
                        curr_fps = getattr(game, "target_fps", 60)
                        curr_i = fps_options.index(curr_fps) if curr_fps in fps_options else 1
                        dir_step = -1 if mouse_pos[0] < bx + 160 else 1
                        game.target_fps = fps_options[(curr_i + dir_step) % len(fps_options)]
                        game.sound_manager.play_sound("click")
                    elif idx == 4:
                        diff_options = ["explorer", "normal", "veteran", "nightmare"]
                        curr_diff = str(getattr(game, "difficulty_profile", "normal")).lower()
                        curr_i = diff_options.index(curr_diff) if curr_diff in diff_options else 1
                        dir_step = -1 if mouse_pos[0] < bx + 160 else 1
                        game.difficulty_profile = diff_options[(curr_i + dir_step) % len(diff_options)]
                        game.sound_manager.play_sound("click")
                    elif idx == 5:
                        game.sound_manager.play_sound("click")
                        game.return_from_settings()
                    return


        # 2. Pause Menu click checks
        elif state == STATE_PAUSED:
            p_state = self.pause_menu_state
            if p_state == "main":
                for idx in range(len(self.pause_options)):
                    bx = SCREEN_WIDTH // 2 - 160
                    by = SCREEN_HEIGHT // 2 - 200 + 68 + idx * 58
                    rect = pygame.Rect(bx, by, 260, 40)
                    if rect.collidepoint(mouse_pos):
                        self.execute_pause_choice(idx, game)
                        return
            elif p_state in ["save_slots", "load_slots"]:
                px = SCREEN_WIDTH // 2 - 250
                py = SCREEN_HEIGHT // 2 - 205
                for idx in range(3):
                    bx = px + 30
                    by = py + 68 + idx * 82
                    rect = pygame.Rect(bx, by, 440, 72)
                    if rect.collidepoint(mouse_pos):
                        self.execute_pause_choice(idx, game)
                        return
                # Cancel button
                cancel_rect = pygame.Rect(px + 30, py + 326, 440, 40)
                if cancel_rect.collidepoint(mouse_pos):
                    self.execute_pause_choice(3, game)
                    return
            elif p_state == "slot_actions":
                px = SCREEN_WIDTH // 2 - 200
                py = SCREEN_HEIGHT // 2 - 180
                meta = self.slots_meta.get(self.selected_slot_idx + 1, {"exists": False})
                if self.pause_action_source == "save":
                    opts = ["Create Save" if not meta["exists"] else "Overwrite Save", "Export Backup", "Rename Profile", "Delete Save", "Back"] if meta["exists"] else ["Create Save", "Back"]
                else:
                    opts = ["Load Profile", "Export Backup", "Rename Profile", "Delete Save", "Back"] if meta["exists"] else ["Back"]

                for idx, opt in enumerate(opts):
                    bx = px + 30
                    by = py + 135 + idx * 42
                    rect = pygame.Rect(bx, by, 340, 34)
                    if rect.collidepoint(mouse_pos):
                        self.execute_pause_choice(idx, game)
                        return

        # Tutorial Screen tab and page navigation clicks
        elif state == STATE_TUTORIAL:
            tw, th = 800, 520
            tx = (SCREEN_WIDTH - tw) // 2
            ty = (SCREEN_HEIGHT - th) // 2

            tabs = ["Controls", "Combat", "Fast Travel", "Upgrades"]
            tab_y = ty + 50
            tab_w = 180
            tab_h = 32
            start_tab_x = tx + (tw - (len(tabs) * (tab_w + 8) - 8)) // 2

            # Check tab clicks
            for idx in range(len(tabs)):
                tab_x = start_tab_x + idx * (tab_w + 8)
                tab_rect = pygame.Rect(tab_x, tab_y, tab_w, tab_h)
                if tab_rect.collidepoint(mouse_pos):
                    self.tutorial_page_idx = idx
                    game.sound_manager.play_sound("click")
                    return

            # Check Prev / Next button clicks
            btn_w, btn_h = 100, 26
            prev_rect = pygame.Rect(tx + 28, ty + th - 38, btn_w, btn_h)
            next_rect = pygame.Rect(tx + tw - 28 - btn_w, ty + th - 38, btn_w, btn_h)

            if prev_rect.collidepoint(mouse_pos):
                self.tutorial_page_idx = (self.tutorial_page_idx - 1) % len(tabs)
                game.sound_manager.play_sound("click")
                return
            elif next_rect.collidepoint(mouse_pos):
                self.tutorial_page_idx = (self.tutorial_page_idx + 1) % len(tabs)
                game.sound_manager.play_sound("click")
                return
            return

        # Dialogue box clicks
        elif state == STATE_DIALOGUE:
            node = game.dialogue_manager.current_node
            if node:
                n_choices = len(node.choices) if (game.dialogue_manager.typing_finished and node.choices) else 0
                dw = SCREEN_WIDTH - 80
                dh = 160 + max(0, n_choices * 36)
                dx = 40
                dy = SCREEN_HEIGHT - dh - 20
                box = pygame.Rect(dx, dy, dw, dh)

                if box.collidepoint(mouse_pos):
                    if game.dialogue_manager.typing_finished and node.choices:
                        choice_x = dx + 160
                        choice_w = dw - 180
                        choice_start_y = dy + 92
                        for idx, choice in enumerate(node.choices[:4]):
                            cy = choice_start_y + idx * 36
                            choice_rect = pygame.Rect(choice_x, cy, choice_w, 32)
                            if choice_rect.collidepoint(mouse_pos):
                                game.dialogue_manager.selected_choice_idx = idx
                                break
                    prev_st = game.game_state
                    game.dialogue_manager.advance()
                    if not game.dialogue_manager.current_node and game.game_state == prev_st:
                        game.game_state = STATE_PLAYING
            return

        # Character Panel tab clicks
        if "character" in self.open_panels:
            cw, ch = 680, 460
            cx = (SCREEN_WIDTH - cw) // 2
            cy = (SCREEN_HEIGHT - ch) // 2
            tab_x, tab_y = cx + 290, cy + 52
            tab1_rect = pygame.Rect(tab_x, tab_y, 58, 24)
            tab2_rect = pygame.Rect(tab_x + 62, tab_y, 48, 24)
            tab3_rect = pygame.Rect(tab_x + 114, tab_y, 44, 24)
            tab4_rect = pygame.Rect(tab_x + 162, tab_y, 56, 24)
            tab5_rect = pygame.Rect(tab_x + 222, tab_y, 56, 24)
            tab6_rect = pygame.Rect(tab_x + 282, tab_y, 62, 24)

            if tab1_rect.collidepoint(mouse_pos):
                self.active_char_tab = "factions"
                return
            elif tab2_rect.collidepoint(mouse_pos):
                self.active_char_tab = "social"
                return
            elif tab3_rect.collidepoint(mouse_pos):
                self.active_char_tab = "town"
                return
            elif tab4_rect.collidepoint(mouse_pos):
                self.active_char_tab = "achievements"
                return
            elif tab5_rect.collidepoint(mouse_pos):
                self.active_char_tab = "bestiary"
                return
            elif tab6_rect.collidepoint(mouse_pos):
                self.active_char_tab = "nemesis"
                return



        # 3. Shop Window clicks
        elif state == STATE_SHOP:
            # Silas Sells: Click item row to buy
            for rect, idx in self.slot_rects["shop"]:
                if rect.collidepoint(mouse_pos) and not right_click:
                    goods_name = self.shop_goods[idx]
                    buy_price_base, _ = self.shop_prices[goods_name]
                    econ_cat = self._get_item_econ_category(goods_name)

                    price_mod = 1.0
                    stock_ratio = 1.0
                    current_map = getattr(game.world_manager, "current_map_name", "village") if hasattr(game, "world_manager") else "village"

                    if hasattr(game, "living_world"):
                        price_mod = game.living_world.get_combined_price_multiplier(econ_cat, current_map)
                        stocks = getattr(game.living_world.economy, "stocks", {})
                        if econ_cat in stocks:
                            res = stocks[econ_cat]
                            stock_ratio = res.current_stock / max(1.0, res.max_capacity)

                    if stock_ratio < 0.30:
                        if hasattr(self, "notification_manager"):
                            from rpg.notification import NotificationPriority
                            self.notification_manager.push_toast(f"'{goods_name}' is currently Out of Stock!", priority=NotificationPriority.HIGH)
                        return

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
                    else:
                        if hasattr(self, "notification_manager"):
                            from rpg.notification import NotificationPriority
                            self.notification_manager.push_toast("Not enough gold!", priority=NotificationPriority.HIGH)
                    return

            # Sell All Materials Button click
            for sa_rect, _ in self.slot_rects.get("sell_all", []):
                if sa_rect.collidepoint(mouse_pos):
                    total_sold_gold = 0
                    items_sold_count = 0
                    for s_idx, slot in enumerate(player.inventory.slots):
                        if slot and getattr(slot, "item_type", "") == "material":
                            s_price = self.get_item_sell_price(slot)
                            if s_price > 0:
                                gained = s_price * slot.quantity
                                total_sold_gold += gained
                                items_sold_count += slot.quantity
                                player.inventory.slots[s_idx] = None
                    if items_sold_count > 0:
                        player.gold += total_sold_gold
                        player.sound_manager.play_sound("heal")
                        from rpg.notification import NotificationPriority
                        self.notifications.push_toast(f"Sold {items_sold_count} materials for +{total_sold_gold}g!", NotificationPriority.HIGH, color=(255, 215, 0))
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
                player.inventory.auto_sort()
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
                    y_pos = 100 + 50 + idx * 36
                    recipe_rect = pygame.Rect(40 + 16, y_pos, 460 - 32, 32)
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
                # Save options safety check
                can_save, reason = game.is_save_allowed()
                if not can_save:
                    game.sound_manager.play_sound("error")
                    self.show_banner(reason, color=(255, 75, 75), duration=3.5)
                    return

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
                opts = ["Create Save" if not meta["exists"] else "Overwrite Save", "Rename Profile", "Delete Save", "Back"] if meta["exists"] else ["Create Save", "Back"]
            else:
                opts = ["Load Profile", "Rename Profile", "Delete Save", "Back"] if meta["exists"] else ["Back"]

            # Out of bounds safety check
            if idx >= len(opts):
                return

            action = opts[idx]

            if action in ["Create Save", "Overwrite Save"]:
                can_save, reason = game.is_save_allowed()
                if not can_save:
                    game.sound_manager.play_sound("error")
                    self.show_banner(reason, color=(255, 75, 75), duration=3.5)
                    return

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



    def draw_exploration_log_panel(self, surface: pygame.Surface, game: Any) -> None:
        """Renders Region Exploration Log & Progression Panel [R]."""
        if "progression" not in self.open_panels or not game:
            return

        prog_mgr = getattr(getattr(game, "living_world", None), "progression", None) if hasattr(game, "living_world") else None
        if not prog_mgr:
            return

        w, h = 740, 490
        x = (SCREEN_WIDTH - w) // 2
        y = (SCREEN_HEIGHT - h) // 2

        # 1. Overlay & Panel Frame
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((16, 20, 30, 245))
        surface.blit(overlay, (x, y))

        # Outer Border
        pygame.draw.rect(surface, (0, 180, 216), (x, y, w, h), width=2, border_radius=6)

        # Title Banner
        pygame.draw.rect(surface, (25, 38, 56), (x, y, w, 38), border_top_left_radius=6, border_top_right_radius=6)
        pygame.draw.line(surface, (0, 180, 216), (x, y + 38), (x + w, y + 38), width=1)

        title_surf = self.fonts["medium"].render("[R] REGION EXPLORATION LOG & WORLD PROGRESSION", True, (255, 215, 0))
        surface.blit(title_surf, (x + 14, y + 9))

        close_txt = self.fonts["small"].render("[R] / [ESC] Close", True, (160, 200, 220))
        surface.blit(close_txt, (x + w - close_txt.get_width() - 14, y + 12))

        # 2. Left Column: Region List Selection
        regions_list = list(prog_mgr.regions.values())
        if self.progression_select_idx >= len(regions_list):
            self.progression_select_idx = 0

        list_x = x + 14
        list_y = y + 48
        list_w = 210

        state_badge_colors = {
            "unknown": (120, 120, 130),
            "rumor_heard": (60, 210, 230),
            "discovered": (240, 200, 40),
            "locked": (230, 120, 30),
            "available": (60, 200, 80),
            "unlocked": (30, 200, 80),
            "mastered": (255, 215, 0)
        }

        for idx, reg in enumerate(regions_list):
            card_rect = pygame.Rect(list_x, list_y + idx * 68, list_w, 62)
            is_selected = (idx == self.progression_select_idx)

            # Hover / click selection
            m_pos = pygame.mouse.get_pos()
            if card_rect.collidepoint(m_pos):
                if pygame.mouse.get_pressed()[0]:
                    self.progression_select_idx = idx

            bg_col = (35, 50, 75) if is_selected else (22, 28, 42)
            border_col = (0, 210, 255) if is_selected else (50, 60, 80)

            pygame.draw.rect(surface, bg_col, card_rect, border_radius=4)
            pygame.draw.rect(surface, border_col, card_rect, width=2 if is_selected else 1, border_radius=4)

            # Name
            disp_name = "???" if reg.state.value == "unknown" else reg.name
            name_surf = self.fonts["medium"].render(disp_name, True, (255, 255, 255) if is_selected else (200, 210, 220))
            surface.blit(name_surf, (list_x + 10, list_y + idx * 68 + 8))

            # State Badge
            st_val = reg.state.value.upper().replace("_", " ")
            st_col = state_badge_colors.get(reg.state.value, (180, 180, 180))
            badge_surf = self.fonts["small"].render(f"[{st_val}]", True, st_col)
            surface.blit(badge_surf, (list_x + 10, list_y + idx * 68 + 34))

        # 3. Right Column: Detailed Exploration Log Card
        detail_x = x + 234
        detail_y = y + 48
        detail_w = 492
        detail_h = 432

        sel_reg = regions_list[self.progression_select_idx]

        card_bg = pygame.Surface((detail_w, detail_h), pygame.SRCALPHA)
        card_bg.fill((20, 26, 38, 220))
        surface.blit(card_bg, (detail_x, detail_y))
        pygame.draw.rect(surface, (0, 180, 216), (detail_x, detail_y, detail_w, detail_h), width=1, border_radius=4)

        curr_y = detail_y + 12

        if sel_reg.state.value == "unknown":
            # Secret / Unrevealed region
            unkn_surf = self.fonts["large"].render("??? UNKNOWN REGION ???", True, (160, 160, 170))
            surface.blit(unkn_surf, (detail_x + 16, curr_y))
            curr_y += 36
            hint_surf = self.fonts["medium"].render("Speak with villagers or explore noticeboards to uncover rumors.", True, (140, 150, 170))
            surface.blit(hint_surf, (detail_x + 16, curr_y))
            return

        # Header Title
        t_surf = self.fonts["large"].render(sel_reg.name, True, (255, 255, 255))
        surface.blit(t_surf, (detail_x + 16, curr_y))

        st_val = sel_reg.state.value.upper().replace("_", " ")
        st_col = state_badge_colors.get(sel_reg.state.value, (180, 180, 180))
        st_surf = self.fonts["medium"].render(f"[{st_val}]", True, st_col)
        surface.blit(st_surf, (detail_x + detail_w - st_surf.get_width() - 16, curr_y + 4))
        curr_y += 32

        pygame.draw.line(surface, (50, 70, 95), (detail_x + 16, curr_y), (detail_x + detail_w - 16, curr_y), 1)
        curr_y += 8

        # Lore / Description (Wrapped)
        curr_y = self._render_wrapped_text(surface, f"Lore: {sel_reg.narrative_lore}", self.fonts["small"], (200, 220, 240), detail_x + 16, curr_y, detail_w - 32, 16)
        curr_y += 4

        # Known Rumor (Wrapped)
        curr_y = self._render_wrapped_text(surface, f"Rumor: \"{sel_reg.rumor}\"", self.fonts["small"], (240, 200, 40), detail_x + 16, curr_y, detail_w - 32, 16)
        curr_y += 8

        # Region Identity Metadata Box
        ident_hdr = self.fonts["medium"].render("Region Identity & Atmosphere:", True, (0, 180, 216))
        surface.blit(ident_hdr, (detail_x + 16, curr_y))
        curr_y += 18

        ident = sel_reg.identity
        ident_lines = [
            f" • Ambient Theme: {ident.ambient_music}  |  Mechanic: {ident.regional_mechanic}",
            f" • Gathering Resources: {', '.join(ident.resources[:3])}",
            f" • Dominant Fauna/Enemies: {', '.join(ident.enemies[:3])}"
        ]
        for il in ident_lines:
            curr_y = self._render_wrapped_text(surface, il, self.fonts["small"], (170, 190, 210), detail_x + 20, curr_y, detail_w - 40, 16)

        curr_y += 8

        # Narrative Progress & Unlock Vectors Box
        req_hdr = self.fonts["medium"].render("Narrative Unlock Requirements & Progress:", True, (0, 180, 216))
        surface.blit(req_hdr, (detail_x + 16, curr_y))
        curr_y += 18

        from rpg.progression import RegionState
        if sel_reg.state in [RegionState.UNLOCKED, RegionState.MASTERED] or getattr(sel_reg.state, "value", sel_reg.state) in ["unlocked", "mastered"]:
            unl_lbl = self.fonts["medium"].render("[OK] Region path is fully open and accessible!", True, (60, 200, 80))
            surface.blit(unl_lbl, (detail_x + 20, curr_y))
            curr_y += 22
        else:
            for grp in sel_reg.requirement_groups:
                grp_desc = f"Path Vector ({grp.description}):"
                g_surf = self.fonts["small"].render(grp_desc, True, (255, 215, 0))
                surface.blit(g_surf, (detail_x + 20, curr_y))
                curr_y += 16
                for req in grp.requirements:
                    req_met = prog_mgr.evaluate_requirement(req, game)
                    icon_str = "[OK]" if req_met else "[X]"
                    col = (60, 200, 80) if req_met else (230, 120, 30)
                    r_text = f"  {icon_str} {req.narrative_clue}"
                    curr_y = self._render_wrapped_text(surface, r_text, self.fonts["small"], col, detail_x + 24, curr_y, detail_w - 48, 16)
            curr_y += 6

        # Region Mastery Progress Box
        m_hdr = self.fonts["medium"].render("Region Exploration Mastery:", True, (255, 215, 0))
        surface.blit(m_hdr, (detail_x + 16, curr_y))
        curr_y += 18

        mastery = sel_reg.mastery

        # Text details above progress bar
        m_details = f"Landmarks: {mastery.landmarks_found}/{mastery.max_landmarks}  |  Elites: {mastery.elites_culled}/{mastery.max_elites}  |  Secrets: {mastery.secrets_found}/{mastery.max_secrets}"
        md_surf = self.fonts["small"].render(m_details, True, (180, 200, 220))
        surface.blit(md_surf, (detail_x + 20, curr_y))
        curr_y += 16

        # Draw Progress Bar below text
        bar_w = 440
        bar_h = 10
        bar_x = detail_x + 20
        pygame.draw.rect(surface, (30, 40, 55), (bar_x, curr_y, bar_w, bar_h), border_radius=3)
        fill_w = int(bar_w * (mastery.exploration_percent / 100.0))
        if fill_w > 0:
            pygame.draw.rect(surface, (255, 215, 0), (bar_x, curr_y, fill_w, bar_h), border_radius=3)
        pygame.draw.rect(surface, (0, 180, 216), (bar_x, curr_y, bar_w, bar_h), width=1, border_radius=3)
        curr_y += 16

        # Fast Travel Button if Waypoint Activated
        reg_id = getattr(sel_reg, "region_id", getattr(sel_reg, "id", ""))
        if hasattr(game, "world_manager") and reg_id in game.world_manager.activated_waypoints:
            ft_rect = pygame.Rect(detail_x + detail_w - 160, detail_y + detail_h - 34, 144, 26)
            is_ft_hover = ft_rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surface, (0, 140, 180) if is_ft_hover else (0, 80, 110), ft_rect, border_radius=4)
            pygame.draw.rect(surface, (0, 220, 255), ft_rect, width=1, border_radius=4)
            ft_lbl = self.fonts["small"].render("[CLICK] Fast Travel", True, (255, 255, 255))
            surface.blit(ft_lbl, (ft_rect.centerx - ft_lbl.get_width() // 2, ft_rect.centery - ft_lbl.get_height() // 2))

            if pygame.mouse.get_pressed()[0] and is_ft_hover:
                can_ft, reason = game.world_manager.can_fast_travel(reg_id, game)
                if can_ft:
                    self.close_all_panels()
                    game.sound_manager.play_sound("magic")
                    game.effects_manager.trigger_flash((255, 255, 255), 300)
                    game.world_manager.load_map(reg_id, game.player, portal_spawn=False)
                else:
                    from rpg.notification import NotificationPriority
                    self.notifications.push_toast(reason, NotificationPriority.MEDIUM, color=(240, 120, 30))

def cy_crafting(cy: int) -> int:
    return cy
