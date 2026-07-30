"""
Echoes of Asterra - Minimap System
Pre-renders map terrain layouts and draws a real-time radar showing player, enemies, and portals.
"""
import pygame
from typing import Any, Tuple
from rpg.constants import COLOR_WHITE, COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_YELLOW, COLOR_ORANGE
from rpg.settings import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE

class Minimap:
    """
    HUD radar overlay representing current map layout and entity positions.
    """
    def __init__(self) -> None:
        self.scale = 3.0  # Pixels per tile on minimap
        self.width = int(GRID_WIDTH * self.scale)
        self.height = int(GRID_HEIGHT * self.scale)
        
        # Pre-rendered static floor/wall background
        self.base_surf = pygame.Surface((self.width, self.height))
        self.current_map_name = ""

    def rebuild_base_terrain(self, map_name: str, grid: list[list[str]]) -> None:
        """
        Pre-draws walls, water, sand and grass tiles to a small cached surface.
        Speeds up frame rendering by avoiding cell looping every frame.
        """
        self.current_map_name = map_name
        if not grid or len(grid) == 0:
            return
            
        map_h = len(grid)
        map_w = len(grid[0]) if map_h > 0 else 0
        self.width = int(map_w * self.scale)
        self.height = int(map_h * self.scale)
        self.base_surf = pygame.Surface((self.width, self.height))
        self.base_surf.fill((20, 20, 25))  # Dark slate background
        
        for r in range(map_h):
            for c in range(map_w):
                tile = grid[r][c]
                px = int(c * self.scale)
                py = int(r * self.scale)
                sz = int(self.scale)
                
                # Determine minimap colors
                if tile == "wall":
                    color = (70, 75, 80)      # Gray wall
                elif tile == "tree":
                    color = (25, 65, 30)      # Dark green tree forest
                elif tile == "water":
                    color = (30, 60, 150)     # Blue water
                elif tile == "sand":
                    color = (180, 160, 110)   # Yellow sand
                elif tile == "dirt":
                    color = (90, 70, 50)      # Brown paths
                else:
                    color = (40, 90, 45)      # Light green grass/dungeon floors
                    if tile == "dungeon_floor":
                        color = (35, 35, 40)  # Dark stone slabs
                        
                pygame.draw.rect(self.base_surf, color, (px, py, sz, sz))

    def draw(self, surface: pygame.Surface, game: Any) -> None:
        """
        Blits the base terrain, outlines it, and overlays glowing dots
        for player, enemies, NPCs, chests, and portals.
        """
        # Rebuild if transition occurred
        wm = game.world_manager
        if self.current_map_name != wm.current_map_name:
            self.rebuild_base_terrain(wm.current_map_name, wm.current_map_grid)
            
        # Draw position coordinates (top-right of screen, below HUD)
        margin = 16
        bx = surface.get_width() - self.width - margin
        by = 96
        
        # 1. Draw border background
        pygame.draw.rect(surface, (10, 10, 15), (bx - 2, by - 2, self.width + 4, self.height + 4), border_radius=3)
        surface.blit(self.base_surf, (bx, by))
        
        # Compute active quest targets
        active_quest_targets = set()
        if hasattr(game, "quest_manager") and game.quest_manager:
            for q in game.quest_manager.quests.values():
                if getattr(q, "status", None) == "active":
                    for obj in q.objectives:
                        if not obj.is_complete():
                            active_quest_targets.add(obj.target.lower())

        # 2. Draw Chests
        for chest in game.chests:
            cx = bx + int((chest.rect.x / TILE_SIZE) * self.scale)
            cy = by + int((chest.rect.y / TILE_SIZE) * self.scale)
            if not chest.is_open:
                is_chest_target = any(t in "chest" or t in "ore" or t in "iron ore" for t in active_quest_targets)
                if is_chest_target:
                    pulse = 5 if int(pygame.time.get_ticks() / 300) % 2 == 0 else 4
                    pygame.draw.circle(surface, (255, 215, 0), (cx, cy), pulse)
                    pygame.draw.circle(surface, COLOR_ORANGE, (cx, cy), 2)
                else:
                    pygame.draw.circle(surface, COLOR_ORANGE, (cx, cy), 2)

        # 3. Draw Portals
        for portal in wm.current_map_data.get("portals", []):
            p_rect = portal["rect"]
            cx = bx + int((p_rect.x / TILE_SIZE) * self.scale)
            cy = by + int((p_rect.y / TILE_SIZE) * self.scale)
            pygame.draw.circle(surface, COLOR_YELLOW, (cx, cy), 3)

        # 4. Draw NPCs
        for npc in game.npcs:
            nx = bx + int((npc.pos.x / TILE_SIZE) * self.scale)
            ny = by + int((npc.pos.y / TILE_SIZE) * self.scale)
            is_quest_target = any(t in npc.name.lower() for t in active_quest_targets)

            if is_quest_target:
                pulse = 5 if int(pygame.time.get_ticks() / 300) % 2 == 0 else 4
                pygame.draw.circle(surface, (255, 215, 0), (nx, ny), pulse)
                pygame.draw.circle(surface, (255, 255, 255), (nx, ny), 2)
            else:
                pygame.draw.circle(surface, COLOR_BLUE, (nx, ny), 3)


        # 5. Draw Enemies
        for enemy in game.enemies:
            if enemy.hp > 0:
                ex = bx + int((enemy.pos.x / TILE_SIZE) * self.scale)
                ey = by + int((enemy.pos.y / TILE_SIZE) * self.scale)
                e_name = enemy.name.lower()
                e_type = getattr(enemy, "enemy_type", "").lower()
                is_quest_target = any(t in e_name or t in e_type for t in active_quest_targets)
                if is_quest_target:
                    pulse = 5 if int(pygame.time.get_ticks() / 300) % 2 == 0 else 4
                    pygame.draw.circle(surface, (255, 215, 0), (ex, ey), pulse)
                    pygame.draw.circle(surface, (255, 60, 60), (ex, ey), 2)
                else:
                    pygame.draw.circle(surface, COLOR_RED, (ex, ey), 2)


        # 6. Draw Player (Flashing Green dot)
        p = game.player
        px = bx + int((p.pos.x / TILE_SIZE) * self.scale)
        py = by + int((p.pos.y / TILE_SIZE) * self.scale)
        
        if int(pygame.time.get_ticks() / 250) % 2 == 0:
            pygame.draw.circle(surface, COLOR_GREEN, (px, py), 4)
            pygame.draw.circle(surface, COLOR_WHITE, (px, py), 2)
        else:
            pygame.draw.circle(surface, COLOR_GREEN, (px, py), 3)
            
        # 7. Draw outline frame
        pygame.draw.rect(surface, COLOR_WHITE, (bx, by, self.width, self.height), 1)

        # 8. Draw Waypoint Obelisk markers (diamond icons for activated waypoints)
        wm = game.world_manager
        for region_id in wm.activated_waypoints:
            from rpg.world import WAYPOINT_POSITIONS
            if region_id in WAYPOINT_POSITIONS and region_id == wm.current_map_name:
                wp = WAYPOINT_POSITIONS[region_id]
                wx = bx + int(wp[0] * self.scale)
                wy = by + int(wp[1] * self.scale)
                # Draw cyan diamond
                pts = [(wx, wy - 4), (wx + 3, wy), (wx, wy + 4), (wx - 3, wy)]
                pygame.draw.polygon(surface, (100, 220, 255), pts)
                pygame.draw.polygon(surface, COLOR_WHITE, pts, 1)

    def handle_click(self, mouse_pos: Tuple[int, int], game: Any) -> bool:
        """
        Handles mouse click on the minimap for fast travel to activated waypoints.
        Returns True if fast travel was triggered.
        """
        from rpg.world import WAYPOINT_POSITIONS
        margin = 16
        bx = game.screen.get_width() - self.width - margin
        by = 96

        # Check if click is within minimap bounds
        if not (bx <= mouse_pos[0] <= bx + self.width and by <= mouse_pos[1] <= by + self.height):
            return False

        wm = game.world_manager
        # Check click proximity to each activated waypoint marker
        for region_id in wm.activated_waypoints:
            if region_id == wm.current_map_name:
                continue  # Can't teleport to current map's waypoint
            if region_id not in WAYPOINT_POSITIONS:
                continue
            wp = WAYPOINT_POSITIONS[region_id]
            wx = bx + int(wp[0] * self.scale)
            wy = by + int(wp[1] * self.scale)

            dist_sq = (mouse_pos[0] - wx) ** 2 + (mouse_pos[1] - wy) ** 2
            if dist_sq <= 64:  # Within 8px click radius
                can_travel, reason = wm.can_fast_travel(region_id, game)
                if can_travel:
                    from rpg.settings import TILE_SIZE
                    spawn_x = wp[0] * TILE_SIZE + TILE_SIZE // 2
                    spawn_y = wp[1] * TILE_SIZE + TILE_SIZE // 2
                    wm.load_map(region_id, game.player, portal_spawn=True, portal_coord=(spawn_x, spawn_y))
                    from rpg.combat import DamageNumber
                    DamageNumber(game.player.rect.center, f"Traveled to {region_id.title()}",
                                 (100, 220, 255), [game.ui_sprites], size=16)
                    return True
                else:
                    from rpg.combat import DamageNumber
                    DamageNumber(game.player.rect.center, reason, (220, 60, 60), [game.ui_sprites], size=14)
                    return False
        return False
