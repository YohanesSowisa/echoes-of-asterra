"""
Echoes of Asterra - World Manager
Manages map transitions, entities spawning, chest states, and ambient music triggers.
"""
import pygame
from typing import Dict, List, Any, Tuple
from rpg.constants import MAP_VILLAGE, MAP_DUNGEON
from rpg.settings import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE
from rpg.map_loader import MapGenerator
from rpg.combat import DamageNumber

class ChestSprite(pygame.sprite.Sprite):
    """
    Interactable chest representation containing item loot stacks.
    """
    def __init__(self, pos: Tuple[int, int], loot: List[Tuple[str, int]], is_open: bool, groups: List[pygame.sprite.Group]) -> None:
        self._layer = 1
        super().__init__(groups)
        self.grid_pos = pos
        self.loot = loot
        self.is_open = is_open
        
        # Load procedural frame textures
        from rpg.animation import tile_assets
        self.tile_assets = tile_assets
        self._update_image()
        
        self.rect = self.image.get_rect(topleft=(pos[0], pos[1]))
        self.hitbox = self.rect.copy()

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
                
            if npc:
                npc.game = game

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
            elif e_type == "boss":
                enemy = Boss(e_pos, [game.visible_sprites], game.sound_manager, game.particles)
                
            enemy.game = game
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
            
            portal_pos = (prect.centerx, prect.centery)
            portal_sprite = BaseSprite(portal_pos, [game.visible_sprites], layer=0)
            portal_sprite.image = marker_surf
            portal_sprite.rect = marker_surf.get_rect(center=portal_pos)
            portal_sprite.hitbox = pygame.Rect(0, 0, 0, 0)  # No collision

        # 11. Trigger background theme
        if map_name == MAP_VILLAGE:
            game.sound_manager.play_music("village_music")
        elif map_name == MAP_DUNGEON and not self.boss_defeated:
            game.sound_manager.play_music("boss_music")
        else:
            game.sound_manager.play_music("dungeon_music")
            
        # Spawn map-level entry text float (only during active gameplay, not menu boot)
        from rpg.constants import STATE_PLAYING
        if game.game_state == STATE_PLAYING:
            title_str = map_name.replace("_", " ").title()
            DamageNumber(player.rect.center, f"Entering {title_str}", (235, 210, 140), [game.ui_sprites], size=24)
