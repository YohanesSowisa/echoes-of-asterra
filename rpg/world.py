"""
Echoes of Asterra - World Manager
Manages map transitions, entities spawning, chest states, and ambient music triggers.
"""
import pygame
import math
from typing import Dict, List, Any, Tuple
from rpg.constants import MAP_VILLAGE, MAP_FOREST, MAP_LAKE, MAP_DUNGEON
from rpg.settings import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE
from rpg.map_loader import MapGenerator
from rpg.combat import DamageNumber

from rpg.sprite import BaseSprite

class ChestSprite(BaseSprite):
    """
    Interactable chest representation containing item loot stacks.
    Supports Y-sorting depth and solid physical ground collisions.
    """
    def __init__(self, pos: Tuple[int, int], loot: List[Tuple[str, int]], is_open: bool, groups: List[pygame.sprite.Group]) -> None:
        super().__init__((float(pos[0] + TILE_SIZE / 2), float(pos[1] + TILE_SIZE / 2)), groups, layer=1)
        self.grid_pos = pos
        self.loot = loot
        self.is_open = is_open


        # Load procedural frame textures
        from rpg.animation import tile_assets
        self.tile_assets = tile_assets
        self._update_image()

        self.rect = self.image.get_rect(topleft=(pos[0], pos[1]))
        # Hitbox represents physical ground base (bottom 20px of 32x32 chest)
        self.hitbox = pygame.Rect(pos[0], pos[1] + 12, TILE_SIZE, 20)


    def _update_image(self) -> None:
        """Sets texture sheet frame based on open state."""
        key = "chest_open" if self.is_open else "chest_closed"
        self.image = self.tile_assets.get(key, pygame.Surface((TILE_SIZE, TILE_SIZE)))

    def open_chest(self, player: Any) -> bool:
        """
        Unlocks the chest and adds its contents to the player's inventory.
        Returns True if successful, False if already open or inventory is full.
        """
        if self.is_open:
            return False

        # Try adding loot to player
        from rpg.items import create_item
        from rpg.combat import DamageNumber

        # Verify inventory space for all items first
        fits = True
        for item_name, qty in self.loot:
            # Simplistic verify check: can we stack or is there empty slot?
            space_exists = False
            for slot in player.inventory.slots:
                if slot is None:
                    space_exists = True
                    break
                if slot.name == item_name and slot.quantity + qty <= slot.max_stack:
                    space_exists = True
                    break
            if not space_exists:
                fits = False
                break

        if not fits:
            DamageNumber(player.rect.center, "Inventory Full!", (220, 60, 60), [player.game.ui_sprites], size=16)
            return False

        # Apply loot
        for item_name, qty in self.loot:
            item_obj = create_item(item_name, qty)
            if item_obj:
                player.inventory.add_item(item_obj)
                DamageNumber(player.rect.center, f"+ {item_name} x{qty}", (60, 200, 80), [player.game.ui_sprites], size=16)

        # Flag as open
        self.is_open = True
        self._update_image()

        # Play chest unlock sound
        player.sound_manager.play_sound("heal")
        # Trigger quest inventory counts update
        player.game.quest_manager.handle_inventory_change(player.inventory)
        return True


# --- Per-map Waypoint Obelisk spawn positions (grid coordinates) ---
WAYPOINT_POSITIONS: Dict[str, Tuple[int, int]] = {
    "village": (8, 14),
    "forest": (20, 12),
    "lake": (15, 8),
    "cave": (5, 5),
    "mountain": (10, 6),
    "ruins": (12, 10),
}


class WaypointObelisk(BaseSprite):
    """
    Ancient crystal obelisk that serves as a fast travel anchor point.
    Activates on player interaction ('E' key) and glows with a pulsing aura.
    """
    def __init__(self, pos: Tuple[int, int], region_id: str, activated: bool,
                 groups: List[pygame.sprite.Group]) -> None:
        center = (float(pos[0] + TILE_SIZE / 2), float(pos[1] + TILE_SIZE / 2))
        super().__init__(center, groups, layer=1)
        self.region_id = region_id
        self.activated = activated
        self.grid_pos = pos
        self.game = None
        self.show_indicator = False
        self.interact_radius = 60.0

        # Build visual surface (32x48 standing sprite)
        self.image = pygame.Surface((32, 48), pygame.SRCALPHA)
        self.rect = self.image.get_rect(midbottom=(pos[0] + 16, pos[1] + 32))
        self.hitbox = pygame.Rect(pos[0] + 4, pos[1] + 16, 24, 16)
        self._build_surface()

    def check_interaction_range(self, player_pos: pygame.math.Vector2) -> bool:
        """Updates indicator visibility based on player proximity."""
        dist = (self.pos - player_pos).length()
        self.show_indicator = (dist <= self.interact_radius)
        return self.show_indicator

    def update(self, dt: float) -> None:
        """Animates floating crystal bobbing motion."""
        self._build_surface()

    def _build_surface(self) -> None:
        """Renders a high-quality ornate crystal obelisk sprite procedurally."""
        self.image.fill((0, 0, 0, 0))
        ticks = pygame.time.get_ticks()

        # 1. Ground Arcane Rune Platform (at base)
        pulse = math.sin(ticks * 0.005) * 0.25 + 0.75
        if self.activated:
            aura_col = (60, 200, 255, int(120 * pulse))
            ring_col = (140, 230, 255, int(200 * pulse))
        else:
            aura_col = (100, 110, 130, int(50 * pulse))
            ring_col = (130, 140, 160, int(90 * pulse))

        aura_surf = pygame.Surface((32, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(aura_surf, aura_col, (2, 2, 28, 10))
        pygame.draw.ellipse(aura_surf, ring_col, (4, 3, 24, 8), 1)
        self.image.blit(aura_surf, (0, 34))

        # 2. Multi-tiered Carved Stone Pedestal
        # Dark granite base
        pygame.draw.rect(self.image, (45, 48, 56), (4, 34, 24, 10), border_radius=2)
        pygame.draw.rect(self.image, (75, 80, 92), (4, 34, 24, 10), 1, border_radius=2)
        # Metallic mid-section
        pygame.draw.rect(self.image, (60, 65, 76), (8, 28, 16, 8), border_radius=1)
        pygame.draw.rect(self.image, (120, 130, 150), (8, 28, 16, 8), 1, border_radius=1)

        # 3. Floating Octagonal Crystal Spire
        bob_y = math.sin(ticks * 0.004) * 3.0
        cy = 14 + bob_y

        if self.activated:
            top_col = (180, 245, 255)
            left_col = (100, 210, 255)
            right_col = (40, 150, 220)
            core_col = (240, 255, 255)
        else:
            top_col = (160, 170, 185)
            left_col = (110, 120, 135)
            right_col = (70, 80, 95)
            core_col = (200, 210, 225)

        # Main crystal facets
        pts_left = [(16, cy - 12), (10, cy), (16, cy + 10)]
        pts_right = [(16, cy - 12), (22, cy), (16, cy + 10)]
        pygame.draw.polygon(self.image, left_col, pts_left)
        pygame.draw.polygon(self.image, right_col, pts_right)
        pygame.draw.line(self.image, top_col, (16, cy - 12), (16, cy + 10), 1)

        # Glowing Crystal Core
        core_pts = [(16, cy - 5), (19, cy), (16, cy + 5), (13, cy)]
        pygame.draw.polygon(self.image, core_col, core_pts)

        # Orbiting Energy Sparks (when active)
        if self.activated:
            angle = ticks * 0.006
            sx1 = 16 + math.cos(angle) * 12
            sy1 = cy + math.sin(angle) * 5
            sx2 = 16 + math.cos(angle + math.pi) * 12
            sy2 = cy + math.sin(angle + math.pi) * 5
            pygame.draw.circle(self.image, (200, 245, 255), (int(sx1), int(sy1)), 2)
            pygame.draw.circle(self.image, (120, 220, 255), (int(sx2), int(sy2)), 1)

    def interact(self, player: Any) -> None:
        """Player presses E near obelisk — activates the waypoint."""
        if not self.activated:
            self.activated = True
            self._build_surface()
            if self.game:
                self.game.world_manager.activate_waypoint(self.region_id, self.game)
        else:
            DamageNumber(player.rect.center, f"{self.region_id.title()} Waypoint Active!",
                         (120, 220, 255), [self.game.ui_sprites], size=16)

    def draw_indicator(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        """Renders floating interactive badge above obelisk when player is nearby."""
        if not self.show_indicator:
            return

        offset_pos = self.pos - camera_offset
        cx, cy = int(offset_pos.x), int(offset_pos.y) - 28

        font = pygame.font.Font(None, 16)
        txt = "[E] Activate Waypoint" if not self.activated else "[E] Fast Travel"
        text_surf = font.render(txt, True, (240, 255, 255))
        w, h = text_surf.get_width() + 12, text_surf.get_height() + 6

        badge_rect = pygame.Rect(0, 0, w, h)
        badge_rect.center = (cx, cy)

        badge_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        bg_col = (15, 25, 35, 220) if self.activated else (25, 25, 30, 220)
        border_col = (100, 220, 255, 255) if self.activated else (255, 215, 0, 255)

        pygame.draw.rect(badge_surf, bg_col, (0, 0, w, h), border_radius=4)
        pygame.draw.rect(badge_surf, border_col, (0, 0, w, h), 1, border_radius=4)

        surface.blit(badge_surf, badge_rect.topleft)
        text_rect = text_surf.get_rect(center=badge_rect.center)
        surface.blit(text_surf, text_rect)


class SettlementDecorationProp(BaseSprite):
    """Visual decorative prop rendered in Village according to active Settlement Specialization."""
    def __init__(self, pos: Tuple[int, int], prop_type: str, name: str, groups: List[pygame.sprite.Group]) -> None:
        center = (float(pos[0] + TILE_SIZE / 2), float(pos[1] + TILE_SIZE / 2))
        super().__init__(center, groups, layer=1)
        self.prop_type = prop_type
        self.name = name
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = pygame.Rect(pos[0] + 4, pos[1] + 8, 24, 20)
        self._render_prop()

    def _render_prop(self) -> None:
        self.image.fill((0, 0, 0, 0))
        if "banner" in self.prop_type:
            # Regal knight fortress banner
            pygame.draw.rect(self.image, (120, 100, 80), (14, 2, 4, 28))
            pygame.draw.polygon(self.image, (180, 30, 30), [(6, 4), (26, 4), (26, 20), (16, 26), (6, 20)])
            pygame.draw.circle(self.image, (240, 200, 50), (16, 12), 4)
        elif "weapon_rack" in self.prop_type or "guard" in self.prop_type:
            # Wooden rack with steel spears/swords
            pygame.draw.rect(self.image, (90, 60, 35), (4, 16, 24, 12))
            pygame.draw.line(self.image, (200, 200, 215), (8, 4), (8, 24), 2)
            pygame.draw.line(self.image, (200, 200, 215), (16, 2), (16, 24), 2)
            pygame.draw.line(self.image, (200, 200, 215), (24, 4), (24, 24), 2)
        elif "trade_stand" in self.prop_type or "canopy" in self.prop_type:
            # Silk trade tent / stand
            pygame.draw.rect(self.image, (100, 70, 40), (4, 14, 24, 14))
            pygame.draw.rect(self.image, (210, 160, 40), (2, 2, 28, 12), border_radius=3)
            pygame.draw.rect(self.image, (180, 40, 40), (6, 2, 6, 12))
            pygame.draw.rect(self.image, (180, 40, 40), (20, 2, 6, 12))
        elif "crates" in self.prop_type:
            # Stacked wooden merchant crates
            pygame.draw.rect(self.image, (130, 95, 55), (4, 12, 14, 14))
            pygame.draw.rect(self.image, (110, 80, 45), (14, 8, 14, 18))
        elif "fountain" in self.prop_type or "mana" in self.prop_type:
            # Glowing arcane mana fountain
            pygame.draw.circle(self.image, (70, 75, 90), (16, 18), 12)
            pygame.draw.circle(self.image, (60, 180, 255), (16, 18), 8)
            pygame.draw.circle(self.image, (190, 240, 255), (16, 17), 4)
        elif "flora" in self.prop_type or "obelisk" in self.prop_type:
            # Glowing bioluminescent flora / crystal
            pygame.draw.circle(self.image, (20, 80, 40), (16, 20), 10)
            pygame.draw.circle(self.image, (140, 70, 230), (16, 14), 6)
            pygame.draw.circle(self.image, (220, 180, 255), (16, 13), 2)
        else:
            pygame.draw.circle(self.image, (180, 180, 180), (16, 16), 8)

class WorldManager:
    """
    Coordinator of map layouts, world scenes, chest state persistence, and level loading.
    """
    def __init__(self) -> None:
        self.current_map_name = ""
        self.current_map_data: Dict[str, Any] = {}
        self.current_map_grid: List[List[str]] = []
        self.chests_opened: Dict[str, List[Tuple[int, int]]] = {}
        self.boss_defeated = False
        self.dungeon_depth = 1
        self.activated_waypoints = set(["village"])
        self.persistent_dropped_items: Dict[str, List[Dict[str, Any]]] = {}


    def activate_waypoint(self, region_id: str, game: Any) -> bool:
        """Activates an Ancient Waypoint Stone, enabling fast travel."""
        if region_id not in self.activated_waypoints:
            self.activated_waypoints.add(region_id)
            if hasattr(game, "ui_manager") and hasattr(game.ui_manager, "celebration"):
                from rpg.celebration import CelebrationTier
                game.ui_manager.celebration.trigger_celebration(
                    CelebrationTier.MEDIUM,
                    f"WAYPOINT ACTIVATED: {region_id.upper()}!",
                    "Fast travel point is now bound and active!",
                    event_bus=getattr(game, "event_bus", None)
                )
            return True
        return False

    def can_fast_travel(self, target_region: str, game: Any) -> Tuple[bool, str]:
        """
        Validates fast travel rules:
        - Waypoint must be activated
        - Target region unlocked
        - Player not in combat
        - Player not inside dungeon
        """
        from rpg.constants import MAP_CRYPT
        if self.current_map_name == MAP_CRYPT:
            return False, "Cannot fast travel from subterranean crypts!"

        if getattr(game, "enemies_in_combat", False):
            return False, "Cannot fast travel during active combat!"

        if target_region not in self.activated_waypoints:
            return False, f"Ancient Waypoint Stone in {target_region.upper()} is not activated!"

        lw = getattr(game, "living_world", None)
        prog_mgr = getattr(lw, "progression", None) if lw else None
        if prog_mgr:
            can_acc, clue, _ = prog_mgr.can_access_region(target_region, game)
            if not can_acc:
                return False, f"Target region is locked: {clue}"

        return True, "Fast travel ready"

    def load_map(self, map_name: str, player: Any, portal_spawn: bool = True, portal_coord: Tuple[int, int] = None) -> None:
        """
        Terminates previous scene entities, pulls map layout arrays,
        re-spawns characters, links camera boundary limits, and starts correct music.
        """
        game = player.game

        from rpg.constants import MAP_CRYPT
        if map_name == MAP_CRYPT:
            if self.current_map_name == MAP_CRYPT:
                self.dungeon_depth += 1
            else:
                self.dungeon_depth = 1
        else:
            self.dungeon_depth = 1

        self.current_map_name = map_name

        # 1. Clear previous level sprites lists
        game.visible_sprites.empty()
        game.projectiles.empty()
        game.dropped_items.empty()
        game.chests.empty()
        game.npcs.empty()
        if hasattr(game, "waypoint_obelisks"):
            game.waypoint_obelisks.empty()

        # Retain player in visible group
        game.visible_sprites.add(player)

        # Reset enemies listing
        game.enemies.clear()

        # 2. Get procedural map template
        if map_name == MAP_CRYPT:
            from rpg.dungeon_gen import DungeonGenerator, THEMES_LIST
            theme = THEMES_LIST[(self.dungeon_depth - 1) // 5 % len(THEMES_LIST)]
            seed = 42 + self.dungeon_depth * 17
            self.current_map_data = DungeonGenerator.generate_floor(self.dungeon_depth, seed, theme)
        else:
            self.current_map_data = MapGenerator.generate(map_name)

        self.current_map_grid = self.current_map_data["grid"]
        if hasattr(game, "services") and hasattr(game.services, "navigation"):
            game.services.navigation.set_grid(self.current_map_grid)

        # 3. Position the player
        if portal_spawn and portal_coord:
            player.pos.x = portal_coord[0]
            player.pos.y = portal_coord[1]
        else:
            # Fall back to default map spawn point
            spawn = self.current_map_data["player_spawn"]
            player.pos.x = spawn[0]
            player.pos.y = spawn[1]

        player.hitbox.center = (int(player.pos.x), int(player.pos.y))
        player.rect.center = player.hitbox.center
        player.velocity.x = 0
        player.velocity.y = 0

        # 4. Spawns Portals transition rects
        # (Stored in map_data, processed in core loop update)

        # 5. Spawns NPCs
        from rpg.npc import ElderEldrin, BlacksmithDennis, MerchantSilas, RangerFaye, ScholarMira, MinerGarth, GuardianKai, SpiritOfAsterra
        for npc_info in self.current_map_data.get("npcs", []):
            npc_type = npc_info["type"]
            pos = npc_info["pos"]

            npc = None
            if npc_type == "eldrin":
                npc = ElderEldrin(pos, [game.visible_sprites, game.npcs])
            elif npc_type == "dennis":
                npc = BlacksmithDennis(pos, [game.visible_sprites, game.npcs])
            elif npc_type == "silas":
                npc = MerchantSilas(pos, [game.visible_sprites, game.npcs])
            elif npc_type == "faye":
                npc = RangerFaye(pos, [game.visible_sprites, game.npcs])
            elif npc_type == "mira":
                npc = ScholarMira(pos, [game.visible_sprites, game.npcs])
            elif npc_type == "garth":
                npc = MinerGarth(pos, [game.visible_sprites, game.npcs])
            elif npc_type == "kai":
                npc = GuardianKai(pos, [game.visible_sprites, game.npcs])
            elif npc_type == "spirit":
                npc = SpiritOfAsterra(pos, [game.visible_sprites, game.npcs])
            elif npc_type in ["villager_male", "villager_female", "guard_village", "hunter_forest"]:
                from rpg.npc import NPC
                disp_name = "Village Guard" if npc_type == "guard_village" else ("Forest Hunter" if npc_type == "hunter_forest" else "Villager")
                npc = NPC(pos, [game.visible_sprites, game.npcs], name=disp_name, asset_key=npc_type)

            if npc:
                npc.game = game

        # Spawn Town Noticeboard, Past Hero Statue & Bard Finn in Village Square
        if map_name == MAP_VILLAGE:
            from rpg.npc import TownNoticeboard, PastHeroStatue, BardFinn
            tb = TownNoticeboard((11 * TILE_SIZE, 11 * TILE_SIZE), [game.visible_sprites, game.npcs])
            tb.game = game

            bf = BardFinn((15 * TILE_SIZE, 11 * TILE_SIZE), [game.visible_sprites, game.npcs])
            bf.game = game

            # Spawn Past Hero Statue in Village Plaza if past run history exists
            if hasattr(game, "mythos_manager"):
                past_record = game.mythos_manager.get_latest_record()
                if past_record:
                    st_pos = (13 * TILE_SIZE, 11 * TILE_SIZE)
                    st = PastHeroStatue(st_pos, past_record, [game.visible_sprites, game.npcs])
                    st.game = game

        # Spawn Greed Altar & Past Hero Statue in Dungeon Crypt
        if map_name == MAP_CRYPT:
            from rpg.npc import GreedAltar, PastHeroStatue
            ga_pos = ((GRID_WIDTH // 2) * TILE_SIZE, (GRID_HEIGHT - 6) * TILE_SIZE)
            ga = GreedAltar(ga_pos, [game.visible_sprites, game.npcs])
            ga.game = game

            # Spawn Past Hero Statue from Mythos Inheritance System if past history exists
            if hasattr(game, "mythos_manager"):
                past_record = game.mythos_manager.get_latest_record()
                if past_record:
                    st_pos = ((GRID_WIDTH // 2 - 3) * TILE_SIZE, 3 * TILE_SIZE)
                    st = PastHeroStatue(st_pos, past_record, [game.visible_sprites, game.npcs])
                    st.game = game

        # 5b. Spawn Waypoint Obelisks (fast travel anchor crystals)
        if map_name in WAYPOINT_POSITIONS:
            wp_grid = WAYPOINT_POSITIONS[map_name]
            wp_pos = (wp_grid[0] * TILE_SIZE, wp_grid[1] * TILE_SIZE)
            is_active = map_name in self.activated_waypoints
            if not hasattr(game, 'waypoint_obelisks'):
                game.waypoint_obelisks = pygame.sprite.Group()
            obelisk = WaypointObelisk(wp_pos, map_name, is_active, [game.visible_sprites, game.waypoint_obelisks])
            obelisk.game = game

        # 5c. Spawn Rival Adventurer (Valen) if currently roaming in this map
        if hasattr(game, "living_world") and hasattr(game.living_world, "rival"):
            rival_data = game.living_world.rival.data
            if rival_data.current_zone == map_name:
                from rpg.npc import RivalAdventurerNPC
                rival_spawn_positions = {
                    "village": (17 * TILE_SIZE, 12 * TILE_SIZE),
                    "forest": (18 * TILE_SIZE, 14 * TILE_SIZE),
                    "cave": (7 * TILE_SIZE, 6 * TILE_SIZE),
                    "ruins": (14 * TILE_SIZE, 12 * TILE_SIZE),
                    "dungeon": (8 * TILE_SIZE, 8 * TILE_SIZE),
                    "lake": (16 * TILE_SIZE, 9 * TILE_SIZE),
                }
                r_pos = rival_spawn_positions.get(map_name, (10 * TILE_SIZE, 10 * TILE_SIZE))
                rival_npc = RivalAdventurerNPC(r_pos, [game.visible_sprites, game.npcs])
                rival_npc.game = game

        # 5d. Spawn Settlement Specialization Visual Props & Guards (if Village)
        if map_name == MAP_VILLAGE and hasattr(game, "living_world") and hasattr(game.living_world, "settlement"):
            settlement = game.living_world.settlement
            decorations = settlement.get_specialization_decorations("village")
            for d in decorations:
                prop = SettlementDecorationProp(d["pos"], d["type"], d["name"], [game.visible_sprites])
                prop.game = game

            # If Military Fortress, spawn an extra elite fortress guard in the village square
            from rpg.settlement import SPECIALIZATION_MILITARY
            if settlement.specialization == SPECIALIZATION_MILITARY:
                from rpg.npc import NPC
                guard_pos = (15 * TILE_SIZE, 13 * TILE_SIZE)
                extra_guard = NPC(guard_pos, [game.visible_sprites, game.npcs], name="Fortress Guard", asset_key="guard_village")
                extra_guard.game = game

        # 6. Spawns Chests
        if map_name not in self.chests_opened:
            self.chests_opened[map_name] = []

        opened_tuples = [tuple(p) for p in self.chests_opened[map_name]]
        for chest_info in self.current_map_data["chests"]:
            c_pos = tuple(chest_info["pos"])
            is_open = c_pos in opened_tuples

            chest = ChestSprite(c_pos, chest_info["loot"], is_open, [game.visible_sprites, game.chests])
            # Save actual map data key referencing
            chest.grid_pos = c_pos

        # 7. Spawns Enemies
        from rpg.enemy import Slime, Wolf, Skeleton, Mage, Goblin, Knight
        from rpg.boss import Boss

        for enemy_info in self.current_map_data["enemies"]:
            e_type = enemy_info["type"]
            e_pos = enemy_info["pos"]

            # If loading boss, check if already dead
            if e_type == "boss" and self.boss_defeated:
                continue

            if e_type == "slime":
                enemy = Slime(e_pos, [game.visible_sprites])
            elif e_type == "slime_blue":
                from rpg.enemy import Slime
                enemy = Slime(e_pos, [game.visible_sprites])
                enemy.name = "Frost Slime"
                enemy.asset_key = "slime_blue"
                enemy.kill_type = "slime_blue"
                enemy.loot_table["Blue Potion"] = 0.25
            elif e_type == "slime_red":
                from rpg.enemy import Slime
                enemy = Slime(e_pos, [game.visible_sprites])
                enemy.name = "Fire Slime"
                enemy.asset_key = "slime_red"
                enemy.kill_type = "slime_red"
                enemy.loot_table["Red Potion"] = 0.30
                enemy.loot_table["Asterra Heart"] = 0.05
            elif e_type == "wolf":
                enemy = Wolf(e_pos, [game.visible_sprites])
            elif e_type == "skeleton":
                enemy = Skeleton(e_pos, [game.visible_sprites])
            elif e_type == "mage":
                enemy = Mage(e_pos, [game.visible_sprites])
            elif e_type == "goblin":
                enemy = Goblin(e_pos, [game.visible_sprites])
            elif e_type == "knight":
                enemy = Knight(e_pos, [game.visible_sprites])
            elif e_type == "forest_guardian":
                from rpg.enemy import ForestGuardian
                enemy = ForestGuardian(e_pos, [game.visible_sprites])
            elif e_type == "bandit_leader":
                from rpg.enemy import BanditLeader
                enemy = BanditLeader(e_pos, [game.visible_sprites])
            elif e_type == "boss":
                enemy = Boss(e_pos, [game.visible_sprites], game.sound_manager, game.particles)

            enemy.game = game
            p_level = getattr(game.player, "level", 1) if hasattr(game, "player") else 1
            floor_d = getattr(self, "current_floor", 1) if map_name == MAP_CRYPT else 1
            e_key = getattr(enemy, "asset_key", "slime")
            enemy.setup_balance(e_key, map_name, p_level, floor_d)
            enemy.sound_manager = game.sound_manager
            enemy.particles = game.particles

            # Apply WorldState danger level stat scaling
            if hasattr(game, "world_state"):
                spawn_mod = game.world_state.get_spawn_modifier()
                enemy.max_hp = int(enemy.max_hp * spawn_mod)
                enemy.hp = enemy.max_hp
                enemy.atk = int(enemy.atk * spawn_mod)

            game.enemies.append(enemy)

        # 8. Align Camera Bounds
        map_w = GRID_WIDTH * TILE_SIZE
        map_h = GRID_HEIGHT * TILE_SIZE
        game.camera.set_map_size(map_w, map_h)

        # 9. Spawn static obstacles (Trees) as depth-sorted BaseSprites
        from rpg.sprite import BaseSprite
        from rpg.animation import tile_assets
        for r in range(len(self.current_map_grid)):
            for c in range(len(self.current_map_grid[0])):
                if self.current_map_grid[r][c] == "tree":
                    tree_pos = (c * TILE_SIZE + TILE_SIZE // 2, r * TILE_SIZE + TILE_SIZE // 2)
                    tree_sprite = BaseSprite(tree_pos, [game.visible_sprites], layer=1)
                    tree_sprite.image = tile_assets["tree"]
                    tree_sprite.rect = tree_sprite.image.get_rect(center=tree_pos)
                    # Align hitbox with the solid tile grid cell
                    tree_sprite.hitbox = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)

        # 10. Spawn portal exit markers (glowing indicator sprites & directional text)
        for portal in self.current_map_data.get("portals", []):
            prect = portal["rect"]
            target_map_raw = portal.get("target_map", "")

            # Format display label for destination map
            target_title = target_map_raw.replace("_", " ").title()
            if target_map_raw == "crypt":
                target_title = f"Crypt F{self.dungeon_depth + 1}" if self.current_map_name == "crypt" else "Endless Crypt"
            elif target_map_raw == "secret_area":
                target_title = "Secret Grove"

            marker_w, marker_h = max(TILE_SIZE * 2, prect.width), max(TILE_SIZE, prect.height)
            marker_surf = pygame.Surface((marker_w, marker_h), pygame.SRCALPHA)

            # Pulsing cyan-gold glow rectangle
            is_return = target_map_raw in ["village", "forest", "cave", "lake"]
            bg_color = (240, 200, 60, 110) if is_return else (80, 200, 255, 110)
            border_color = (250, 220, 100, 220) if is_return else (120, 220, 255, 220)

            pygame.draw.rect(marker_surf, bg_color, (0, 0, marker_w, marker_h), border_radius=4)
            pygame.draw.rect(marker_surf, border_color, (2, 2, marker_w - 4, marker_h - 4), 2, border_radius=3)

            # Arrow indicator direction calculation
            cx, cy = marker_w // 2, marker_h // 2
            arrow_color = (255, 255, 200, 240) if is_return else (200, 240, 255, 240)

            if prect.y <= TILE_SIZE * 2:  # Top edge or near top -> arrow points UP
                pygame.draw.polygon(marker_surf, arrow_color, [(cx, 4), (cx - 8, 16), (cx + 8, 16)])
            elif prect.y >= (GRID_HEIGHT - 3) * TILE_SIZE:  # Bottom edge -> arrow points DOWN
                pygame.draw.polygon(marker_surf, arrow_color, [(cx, marker_h - 4), (cx - 8, marker_h - 16), (cx + 8, marker_h - 16)])
            elif prect.x <= TILE_SIZE * 2:  # Left edge -> arrow points LEFT
                pygame.draw.polygon(marker_surf, arrow_color, [(4, cy), (16, cy - 8), (16, cy + 8)])
            elif prect.x >= (GRID_WIDTH - 3) * TILE_SIZE:  # Right edge -> arrow points RIGHT
                pygame.draw.polygon(marker_surf, arrow_color, [(marker_w - 4, cy), (marker_w - 16, cy - 8), (marker_w - 16, cy + 8)])
            else:  # Interior portals (stairs, return portals inside rooms)
                pygame.draw.polygon(marker_surf, arrow_color, [(cx, marker_h - 4), (cx - 8, marker_h - 16), (cx + 8, marker_h - 16)])

            # Render text label (e.g. "To Village" or "To Forest")
            try:
                lbl_font = pygame.font.Font("assets/fonts/game_font.ttf", 11)
            except Exception as e:
                print(f"Warning: Failed loading portal marker font, using fallback: {e}")
                lbl_font = pygame.font.SysFont("Arial", 11, bold=True)
            lbl_str = f"To {target_title}"
            lbl_surf = lbl_font.render(lbl_str, True, (255, 255, 240))

            lx = (marker_w - lbl_surf.get_width()) // 2
            ly = (marker_h - lbl_surf.get_height()) // 2

            # Text background badge
            bg_rect = pygame.Rect(lx - 4, ly - 1, lbl_surf.get_width() + 8, lbl_surf.get_height() + 2)
            pygame.draw.rect(marker_surf, (15, 18, 25, 220), bg_rect, border_radius=3)
            pygame.draw.rect(marker_surf, border_color[:3], bg_rect, 1, border_radius=3)
            marker_surf.blit(lbl_surf, (lx, ly))

            # Adjust portal guide badge center so edge markers are never clipped or covered by top HUD
            portal_pos_x = prect.centerx
            portal_pos_y = prect.centery
            if prect.y <= TILE_SIZE:
                portal_pos_y = prect.centery + int(TILE_SIZE * 1.5)  # Shift down below top HUD
            elif prect.y >= (GRID_HEIGHT - 2) * TILE_SIZE:
                portal_pos_y = prect.centery - int(TILE_SIZE * 0.6)  # Shift up inside map
            elif prect.x <= TILE_SIZE:
                portal_pos_x = prect.centerx + int(TILE_SIZE * 0.6)  # Shift right inside map
            elif prect.x >= (GRID_WIDTH - 2) * TILE_SIZE:
                portal_pos_x = prect.centerx - int(TILE_SIZE * 0.6)  # Shift left inside map

            portal_sprite = BaseSprite((portal_pos_x, portal_pos_y), [game.visible_sprites], layer=10)
            portal_sprite.image = marker_surf
            portal_sprite.rect = marker_surf.get_rect(center=(portal_pos_x, portal_pos_y))
            portal_sprite.hitbox = pygame.Rect(0, 0, 0, 0)  # Visual guide only

        # 10b. Spawn Town Investment Architectural Objects in Village
        if map_name == MAP_VILLAGE and hasattr(game, "living_world"):
            prosperity = game.living_world.settlement.prosperity
            if prosperity >= 50.0:
                wt_pos = (TILE_SIZE * 4, TILE_SIZE * 4)
                wt_surf = pygame.Surface((TILE_SIZE * 2, TILE_SIZE * 3), pygame.SRCALPHA)
                pygame.draw.rect(wt_surf, (80, 85, 95), (4, 16, TILE_SIZE * 2 - 8, TILE_SIZE * 3 - 16), border_radius=4)
                pygame.draw.rect(wt_surf, (180, 50, 50), (12, 0, TILE_SIZE * 2 - 24, 20), border_radius=3)
                try:
                    wt_font = pygame.font.Font("assets/fonts/game_font.ttf", 10)
                except Exception as e:
                    print(f"Warning: Failed loading watchtower font, using fallback: {e}")
                    wt_font = pygame.font.SysFont("Arial", 10, bold=True)
                wt_lbl = wt_font.render("WATCHTOWER", True, (255, 240, 200))
                wt_surf.blit(wt_lbl, (8, TILE_SIZE * 2))
                wt_sprite = BaseSprite(wt_pos, [game.visible_sprites], layer=1)
                wt_sprite.image = wt_surf
                wt_sprite.rect = wt_surf.get_rect(center=wt_pos)

            if prosperity >= 80.0:
                mkt_pos = (TILE_SIZE * 18, TILE_SIZE * 6)
                mkt_surf = pygame.Surface((TILE_SIZE * 4, TILE_SIZE * 2), pygame.SRCALPHA)
                pygame.draw.rect(mkt_surf, (210, 170, 50), (0, 0, TILE_SIZE * 4, 24), border_radius=4)
                try:
                    mkt_font = pygame.font.Font("assets/fonts/game_font.ttf", 11)
                except Exception as e:
                    import logging
                    logging.warning(f"Could not load custom font for Market Exchange: {e}")
                    mkt_font = pygame.font.SysFont("Arial", 11, bold=True)
                mkt_lbl = mkt_font.render("ROYAL MARKET EXCHANGE", True, (25, 20, 10))
                mkt_surf.blit(mkt_lbl, ((TILE_SIZE * 4 - mkt_lbl.get_width()) // 2, 4))
                mkt_sprite = BaseSprite(mkt_pos, [game.visible_sprites], layer=1)

                mkt_sprite.image = mkt_surf
                mkt_sprite.rect = mkt_surf.get_rect(center=mkt_pos)

        # 10c. Re-spawn persistent dropped items for target map (Minecraft-style death loot)
        if hasattr(self, "persistent_dropped_items") and map_name in self.persistent_dropped_items:
            active_drops = []
            for d_info in self.persistent_dropped_items[map_name]:
                if d_info.get("despawn_timer", 0) > 0:
                    from rpg.enemy import DroppedItem
                    drop = DroppedItem(d_info["pos"], d_info["item"], [game.visible_sprites, game.dropped_items], despawn_time=d_info["despawn_timer"])
                    drop.game = game
                    active_drops.append(d_info)
            self.persistent_dropped_items[map_name] = active_drops

        # 11. Trigger background theme

        if map_name == MAP_VILLAGE:
            game.sound_manager.play_music("village_music", force=True)
        elif map_name == MAP_FOREST:
            game.sound_manager.play_music("forest_music", force=True)
        elif map_name == MAP_LAKE:
            game.sound_manager.play_music("lake_music", force=True)
        elif map_name == MAP_DUNGEON and not self.boss_defeated:
            game.sound_manager.play_music("boss_music", force=True)
        else:
            game.sound_manager.play_music("dungeon_music", force=True)

        # Spawn map-level entry text float (only during active gameplay, not menu boot)
        from rpg.constants import STATE_PLAYING
        if game.game_state == STATE_PLAYING:
            title_str = map_name.replace("_", " ").title()
            DamageNumber(player.rect.center, f"Entering {title_str}", (235, 210, 140), [game.ui_sprites], size=24)
