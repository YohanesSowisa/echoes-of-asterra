"""
Echoes of Asterra - Procedural Map Generator
Generates layouts, tiles, enemy spawns, NPC placements, chests, and portals for all 8 zones.
"""
import random
import pygame
from typing import Dict, List, Tuple, Any
from rpg.constants import (
    MAP_VILLAGE, MAP_FOREST, MAP_RUINS, MAP_CAVE,
    MAP_LAKE, MAP_MOUNTAIN, MAP_DUNGEON, MAP_SECRET, MAP_CRYPT
)
from rpg.settings import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE

class MapGenerator:
    """
    Algorithmic generator creating top-down levels.
    """
    @staticmethod
    def generate(map_name: str) -> Dict[str, Any]:
        """
        Builds a map container containing the tile grid, spawn positions,
        enemies list, chest contents, and portal transition rectangles.
        Loads layout from assets/maps/ if present, otherwise generates procedurally.
        """
        import os
        import json

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        MAPS_DIR = os.path.join(BASE_DIR, "assets", "maps")
        os.makedirs(MAPS_DIR, exist_ok=True)
        file_path = os.path.join(MAPS_DIR, f"{map_name}.json")

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    map_data = json.load(f)
                # Reconstruct pygame.Rect objects from lists
                for portal in map_data["portals"]:
                    portal["rect"] = pygame.Rect(*portal["rect"])
                return map_data
            except Exception as e:
                print(f"Warning: Failed to load map layout {file_path} from disk. Re-generating. Details: {e}")

        if map_name == MAP_CRYPT:
            from rpg.dungeon_gen import DungeonGenerator
            from rpg.constants import DUNGEON_CRYPT
            return DungeonGenerator.generate_floor(1, 42, DUNGEON_CRYPT)

        w, h = GRID_WIDTH, GRID_HEIGHT

        # 1. Initialize default grid
        grid = [["grass" for _ in range(w)] for _ in range(h)]

        player_spawn = (w // 2 * TILE_SIZE, h // 2 * TILE_SIZE)
        portals = []
        enemies = []
        npcs = []
        chests = []

        # 2. Algorithmic modifications based on level
        if map_name == MAP_VILLAGE:
            # Peace town. Add dirt roads
            for x in range(w):
                grid[h // 2][x] = "dirt"
                grid[h // 2 + 1][x] = "dirt"
            for y in range(h):
                grid[y][w // 2] = "dirt"
                grid[y][w // 2 + 1] = "dirt"

            # Surround map boundaries with solid trees
            for x in range(w):
                grid[0][x] = "tree"
                grid[h - 1][x] = "tree"
            for y in range(h):
                grid[y][0] = "tree"
                grid[y][w - 1] = "tree"

            # Place houses (hollow walls with doorways)
            # House 1 (Elder Eldrin)
            for r in range(4, 9):
                for c in range(4, 10):
                    if r == 4 or r == 8 or c == 4 or c == 9:
                        grid[r][c] = "wall"
                    else:
                        grid[r][c] = "dirt"
            grid[8][6] = "dirt"
            grid[8][7] = "dirt"

            # House 2 (Blacksmith Dennis)
            for r in range(4, 9):
                for c in range(w - 10, w - 4):
                    if r == 4 or r == 8 or c == w - 10 or c == w - 5:
                        grid[r][c] = "wall"
                    else:
                        grid[r][c] = "dirt"
            grid[8][w - 7] = "dirt"

            # House 3 (Merchant Silas Shop)
            for r in range(h - 9, h - 4):
                for c in range(4, 10):
                    if r == h - 9 or r == h - 5 or c == 4 or c == 9:
                        grid[r][c] = "wall"
                    else:
                        grid[r][c] = "dirt"
            grid[h - 9][6] = "dirt"
            grid[h - 9][7] = "dirt"

            # NPCs Placements (open accessible dirt ground)
            npcs.append({"type": "eldrin", "pos": (6.5 * TILE_SIZE, 10 * TILE_SIZE)})
            npcs.append({"type": "dennis", "pos": ((w - 7) * TILE_SIZE, 10 * TILE_SIZE)})
            npcs.append({"type": "silas", "pos": (6.5 * TILE_SIZE, (h - 11) * TILE_SIZE)})

            # Chest
            chests.append({"pos": (12 * TILE_SIZE, 5 * TILE_SIZE), "loot": [("Baked Bread", 2), ("Red Potion", 1)]})

            # Portals to Forest (Right side)
            grid[h // 2][w - 1] = "dirt"
            grid[h // 2 + 1][w - 1] = "dirt"
            portals.append({
                "rect": pygame.Rect((w - 1) * TILE_SIZE, (h // 2) * TILE_SIZE, TILE_SIZE, TILE_SIZE * 2),
                "target_map": MAP_FOREST,
                "target_spawn": (2 * TILE_SIZE, h // 2 * TILE_SIZE)
            })

            # Portal to Cavern (Bottom side)
            grid[h - 1][w // 2] = "dirt"
            grid[h - 1][w // 2 + 1] = "dirt"
            portals.append({
                "rect": pygame.Rect((w // 2) * TILE_SIZE, (h - 1) * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_CAVE,
                "target_spawn": (w // 2 * TILE_SIZE, 2 * TILE_SIZE)
            })

            # Portal to Endless Crypt (Top side)
            grid[0][w // 2] = "dirt"
            grid[0][w // 2 + 1] = "dirt"
            portals.append({
                "rect": pygame.Rect((w // 2) * TILE_SIZE, 0, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_CRYPT,
                "target_spawn": (w // 2 * TILE_SIZE, (h - 4) * TILE_SIZE)
            })

        elif map_name == MAP_FOREST:
            # Forest wilderness: scatter trees and grass blades
            for r in range(h):
                for c in range(w):
                    # Outer boundary
                    if r == 0 or r == h - 1 or c == 0 or c == w - 1:
                        grid[r][c] = "tree"
                    elif random.random() < 0.25:
                        grid[r][c] = "tree"

            # Keep pathways clear (horizontal + vertical cross)
            for x in range(w):
                grid[h // 2][x] = "grass"
                grid[h // 2 + 1][x] = "grass"
            for y in range(h):
                grid[y][w // 2] = "grass"
                grid[y][w // 2 + 1] = "grass"

            # Clear portal boundary tiles so player can walk through
            # Left portal (Village)
            grid[h // 2][0] = "grass"
            grid[h // 2 + 1][0] = "grass"
            # Right portal (Ruins)
            grid[h // 2][w - 1] = "grass"
            grid[h // 2 + 1][w - 1] = "grass"
            # Top portal (Lake)
            grid[0][w // 2] = "grass"
            grid[0][w // 2 + 1] = "grass"

            # Landmark: Campfire clearing (dirt circle)
            for r in range(5, 10):
                for c in range(5, 10):
                    grid[r][c] = "dirt"

            # NPCs (Ranger Faye at campfire)
            npcs.append({"type": "faye", "pos": (7 * TILE_SIZE, 7 * TILE_SIZE)})

            # Enemies (pass grid to avoid spawning inside trees)
            for _ in range(5):
                enemies.append({"type": "slime", "pos": _rand_pixel_pos(w, h, "grass", grid)})
            for _ in range(3):
                enemies.append({"type": "wolf", "pos": _rand_pixel_pos(w, h, "grass", grid)})

            # Apples chest (rebalanced quantity)
            chests.append({"pos": (5 * TILE_SIZE, 6 * TILE_SIZE), "loot": [("Forest Apple", 3)]})

            # Portals
            # Left -> Village
            portals.append({
                "rect": pygame.Rect(0, (h // 2) * TILE_SIZE, TILE_SIZE, TILE_SIZE * 2),
                "target_map": MAP_VILLAGE,
                "target_spawn": ((w - 3) * TILE_SIZE, h // 2 * TILE_SIZE)
            })
            # Right -> Ruins
            portals.append({
                "rect": pygame.Rect((w - 1) * TILE_SIZE, (h // 2) * TILE_SIZE, TILE_SIZE, TILE_SIZE * 2),
                "target_map": MAP_RUINS,
                "target_spawn": (3 * TILE_SIZE, h // 2 * TILE_SIZE)
            })
            # Top -> Lake
            portals.append({
                "rect": pygame.Rect((w // 2) * TILE_SIZE, 0, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_LAKE,
                "target_spawn": (w // 2 * TILE_SIZE, (h - 4) * TILE_SIZE)
            })

        elif map_name == MAP_RUINS:
            # Shattered brick columns
            grid = [["dirt" for _ in range(w)] for _ in range(h)]
            # Draw ruined stone walls
            for r in range(h):
                for c in range(w):
                    if r == 0 or r == h - 1 or c == 0 or c == w - 1:
                        grid[r][c] = "wall"
                    elif (r % 6 == 0 and c % 6 == 0):
                        grid[r][c] = "wall"  # Ruin pillars

            # Clear corridor (2 tiles wide for easier navigation)
            for x in range(w):
                grid[h // 2][x] = "dirt"
                grid[h // 2 + 1][x] = "dirt"

            # Clear portal boundary tiles (both rows of each 2-tile-high portal)
            # Left portal (Forest)
            grid[h // 2][0] = "dirt"
            grid[h // 2 + 1][0] = "dirt"
            # Right portal (Dungeon)
            grid[h // 2][w - 1] = "dirt"
            grid[h // 2 + 1][w - 1] = "dirt"

            # Landmark: Ancient Library room (top right)
            for r in range(4, 9):
                for c in range(w - 12, w - 4):
                    grid[r][c] = "dirt"

            # NPCs (Scholar Mira in Library)
            npcs.append({"type": "mira", "pos": ((w - 8) * TILE_SIZE, 6 * TILE_SIZE)})

            # Enemies (Skeletons & Goblins)
            for _ in range(4):
                enemies.append({"type": "skeleton", "pos": _rand_pixel_pos(w, h, "dirt", grid)})
            for _ in range(3):
                enemies.append({"type": "goblin", "pos": _rand_pixel_pos(w, h, "dirt", grid)})

            # Chest with scroll/shield
            chests.append({"pos": (w // 3 * TILE_SIZE, h // 4 * TILE_SIZE), "loot": [("Ancient Scroll", 1), ("Iron Ore", 3)]})

            # Portals
            # Left -> Forest
            portals.append({
                "rect": pygame.Rect(0, (h // 2) * TILE_SIZE, TILE_SIZE, TILE_SIZE * 2),
                "target_map": MAP_FOREST,
                "target_spawn": ((w - 3) * TILE_SIZE, h // 2 * TILE_SIZE)
            })
            # Right -> Dungeon (Deep Boss Lair)
            portals.append({
                "rect": pygame.Rect((w - 1) * TILE_SIZE, (h // 2) * TILE_SIZE, TILE_SIZE, TILE_SIZE * 2),
                "target_map": MAP_DUNGEON,
                "target_spawn": (5 * TILE_SIZE, 15 * TILE_SIZE)
            })

        elif map_name == MAP_CAVE:
            # Excavated sand caverns - large interconnected cave system
            grid = [["wall" for _ in range(w)] for _ in range(h)]

            # Carve out large cavern rooms (6 rooms spread across the map)
            room_centers = []
            room_defs = [
                # (cx, cy, half_w, half_h) - predefined room positions for good layout
                (w // 4, h // 4, 6, 5),           # Top-left cavern
                (3 * w // 4, h // 4, 5, 4),       # Top-right cavern
                (w // 4, 3 * h // 4, 5, 5),       # Bottom-left cavern
                (3 * w // 4, 3 * h // 4, 6, 4),   # Bottom-right cavern
                (w // 2, h // 2, 7, 5),            # Central grand cavern
                (w // 2, h // 4, 4, 3),            # Top-center small grotto
            ]

            for cx, cy, hw, hh in room_defs:
                room_centers.append((cx, cy))
                for r in range(max(1, cy - hh), min(h - 1, cy + hh + 1)):
                    for c in range(max(1, cx - hw), min(w - 1, cx + hw + 1)):
                        grid[r][c] = "sand"

            # Wide central vertical corridor (4 tiles wide)
            for y in range(h):
                for dx in range(-1, 3):
                    col = w // 2 + dx
                    if 0 < col < w - 1:
                        grid[y][col] = "sand"

            # Wide horizontal corridor connecting left and right cavern rooms
            for x in range(1, w - 1):
                for dy in range(-1, 2):
                    row = h // 2 + dy
                    if 0 < row < h - 1:
                        grid[row][x] = "sand"

            # Seal outer left and right boundaries with solid cave walls
            for r in range(h):
                grid[r][0] = "wall"
                grid[r][w - 1] = "wall"

            # Connect each room to nearest corridor with wide tunnels
            for cx, cy in room_centers:
                # Horizontal tunnel to vertical corridor
                start_c = min(cx, w // 2)
                end_c = max(cx, w // 2 + 2)
                for c in range(start_c, end_c + 1):
                    for dy in range(-1, 2):
                        row = min(h - 2, max(1, cy + dy))
                        grid[row][c] = "sand"
                # Vertical tunnel to horizontal corridor
                start_r = min(cy, h // 2)
                end_r = max(cy, h // 2 + 1)
                for r in range(start_r, end_r + 1):
                    for dx in range(-1, 2):
                        col = min(w - 2, max(1, cx + dx))
                        grid[r][col] = "sand"

            # Add some random rocky outcrops inside rooms for visual variety
            for _ in range(15):
                rc = random.randint(3, w - 4)
                rr = random.randint(3, h - 4)
                if grid[rr][rc] == "sand":
                    # Only place if surrounded by sand (interior)
                    neighbors = sum(1 for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]
                                  if grid[rr+dr][rc+dc] == "sand")
                    if neighbors == 4:
                        grid[rr][rc] = "wall"  # Rocky pillar

            # Clear portal exit tiles
            grid[0][w // 2] = "sand"
            grid[0][w // 2 + 1] = "sand"
            grid[1][w // 2] = "sand"
            grid[1][w // 2 + 1] = "sand"
            grid[h - 1][w // 2] = "sand"
            grid[h - 1][w // 2 + 1] = "sand"
            grid[h - 2][w // 2] = "sand"
            grid[h - 2][w // 2 + 1] = "sand"

            # NPCs (Miner Garth in central cavern)
            npcs.append({"type": "garth", "pos": (w // 2 * TILE_SIZE, (h // 2 + 2) * TILE_SIZE)})

            # Enemies (Cave Goblins & Cave Slimes)
            for _ in range(3):
                enemies.append({"type": "slime_blue", "pos": _rand_pixel_pos(w, h, "sand", grid)})
            for _ in range(4):
                enemies.append({"type": "goblin", "pos": _rand_pixel_pos(w, h, "sand", grid)})

            # Iron Ore resource chests (rebalanced quantities)
            chests.append({"pos": (w // 4 * TILE_SIZE, h // 4 * TILE_SIZE), "loot": [("Iron Ore", 2), ("Red Potion", 1)]})
            chests.append({"pos": (3 * w // 4 * TILE_SIZE, 3 * h // 4 * TILE_SIZE), "loot": [("Iron Ore", 3)]})

            # Portals
            # Top -> Village
            portals.append({
                "rect": pygame.Rect((w // 2) * TILE_SIZE, 0, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_VILLAGE,
                "target_spawn": (w // 2 * TILE_SIZE, (h - 3) * TILE_SIZE)
            })
            # Bottom -> Mountain
            portals.append({
                "rect": pygame.Rect((w // 2) * TILE_SIZE, (h - 1) * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_MOUNTAIN,
                "target_spawn": (w // 2 * TILE_SIZE, 3 * TILE_SIZE)
            })

        elif map_name == MAP_LAKE:
            # Large circular water reservoir
            grid = [["grass" for _ in range(w)] for _ in range(h)]

            # Place water circle in center
            center_x, center_y = w // 2, h // 2
            for r in range(h):
                for c in range(w):
                    # Check distance to center
                    dist = ((c - center_x) ** 2 + (r - center_y) ** 2) ** 0.5
                    if dist < 8.0:
                        grid[r][c] = "water"
                    elif dist < 9.5:
                        grid[r][c] = "sand"  # Beach shores

            # Keep boundaries lined with trees
            for x in range(w):
                grid[0][x] = "tree"
                grid[h - 1][x] = "tree"
            for y in range(h):
                grid[y][0] = "tree"
                grid[y][w - 1] = "tree"

            # Clear portal boundary tiles
            # Bottom portal (Forest)
            grid[h - 1][w // 2] = "grass"
            grid[h - 1][w // 2 + 1] = "grass"
            grid[h - 2][w // 2] = "grass"
            grid[h - 2][w // 2 + 1] = "grass"
            # Top portal (Secret)
            grid[0][w // 2] = "grass"
            grid[0][w // 2 + 1] = "grass"

            # Landmark: Fishing dock (dirt pier extending toward water)
            for r in range(h // 2 - 2, h // 2 + 3):
                for c in range(5, 11):
                    grid[r][c] = "dirt"

            # NPCs (Guardian Kai at fishing dock)
            npcs.append({"type": "kai", "pos": (9 * TILE_SIZE, (h // 2) * TILE_SIZE)})

            # Enemies
            for _ in range(4):
                enemies.append({"type": "slime_blue", "pos": _rand_pixel_pos(w, h, "grass", grid)})
            for _ in range(2):
                enemies.append({"type": "wolf", "pos": _rand_pixel_pos(w, h, "grass", grid)})

            # Portals
            # Bottom -> Forest
            portals.append({
                "rect": pygame.Rect((w // 2) * TILE_SIZE, (h - 1) * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_FOREST,
                "target_spawn": (w // 2 * TILE_SIZE, 3 * TILE_SIZE)
            })
            # Top -> Secret Area
            portals.append({
                "rect": pygame.Rect((w // 2) * TILE_SIZE, 0, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_SECRET,
                "target_spawn": (w // 2 * TILE_SIZE, (h - 5) * TILE_SIZE)
            })

            # Default spawn on grass (not center water)
            player_spawn = (w // 2 * TILE_SIZE, (h - 4) * TILE_SIZE)

        elif map_name == MAP_MOUNTAIN:
            # Snow-pass framed by cliffs. Represented as dirt with sand border walls.
            grid = [["sand" for _ in range(w)] for _ in range(h)]
            # Draw cliff borders
            for r in range(h):
                for c in range(w):
                    if c < 8 or c > w - 9:
                        grid[r][c] = "wall"

            # Keep vertical lane open
            for y in range(h):
                grid[y][w // 2] = "sand"
                grid[y][w // 2 + 1] = "sand"

            # Enemies (Wolves and Corrupted Knights)
            for _ in range(3):
                enemies.append({"type": "wolf", "pos": _rand_pixel_pos(w, h, "sand", grid)})
            for _ in range(3):
                enemies.append({"type": "knight", "pos": _rand_pixel_pos(w, h, "sand", grid)})

            # Potions chest (placed on guaranteed sand corridor)
            chests.append({"pos": (w // 2 * TILE_SIZE, h // 3 * TILE_SIZE), "loot": [("Blue Potion", 3), ("Glow Amulet", 1)]})

            # Portals
            # Top -> Cave (return path)
            portals.append({
                "rect": pygame.Rect((w // 2) * TILE_SIZE, 0, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_CAVE,
                "target_spawn": (w // 2 * TILE_SIZE, (h - 4) * TILE_SIZE)
            })
            # Bottom -> Dungeon (alternate boss path)
            portals.append({
                "rect": pygame.Rect((w // 2) * TILE_SIZE, (h - 1) * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_DUNGEON,
                "target_spawn": (33 * TILE_SIZE, 22 * TILE_SIZE)
            })

        elif map_name == MAP_DUNGEON:
            # Multi-room stone slabs dungeon
            grid = [["wall" for _ in range(w)] for _ in range(h)]

            # Dig out 3 large rectangular rooms: Left Room, Center Hall, Boss Arena Right
            # 1. Left Entry Room
            for r in range(10, 20):
                for c in range(4, 12):
                    grid[r][c] = "dungeon_floor"
            # 2. Center Hall
            for r in range(8, 22):
                for c in range(16, 24):
                    grid[r][c] = "dungeon_floor"
            # 3. Right Boss Chamber
            for r in range(6, 24):
                for c in range(28, 38):
                    grid[r][c] = "dungeon_floor"

            # Connect corridors (2 tiles wide for easier navigation)
            # Corridor Left-Center
            for c in range(12, 16):
                grid[14][c] = "dungeon_floor"
                grid[15][c] = "dungeon_floor"
            # Corridor Center-Right
            for c in range(24, 28):
                grid[14][c] = "dungeon_floor"
                grid[15][c] = "dungeon_floor"

            # Clear exit passage from Left Room to portal (column 3)
            grid[14][3] = "dungeon_floor"
            grid[15][3] = "dungeon_floor"

            # Clear Mountain entry passage in Boss Chamber (bottom row)
            grid[22][28] = "dungeon_floor"
            grid[22][29] = "dungeon_floor"
            grid[23][28] = "dungeon_floor"
            grid[23][29] = "dungeon_floor"

            # Enemies (Shadow Mages, Knights, Red Slimes)
            # Left room
            enemies.append({"type": "slime_red", "pos": (8 * TILE_SIZE, 15 * TILE_SIZE)})
            enemies.append({"type": "skeleton", "pos": (6 * TILE_SIZE, 12 * TILE_SIZE)})
            # Center hall
            enemies.append({"type": "mage", "pos": (20 * TILE_SIZE, 10 * TILE_SIZE)})
            enemies.append({"type": "knight", "pos": (20 * TILE_SIZE, 18 * TILE_SIZE)})

            # BOSS SPAWN in the center of Right Chamber
            enemies.append({"type": "boss", "pos": (33 * TILE_SIZE, 15 * TILE_SIZE)})

            # Chests (dungeon rewards — inside Center Hall)
            chests.append({"pos": (20 * TILE_SIZE, 9 * TILE_SIZE), "loot": [("Blue Potion", 2), ("Asterra Heart", 1)]})

            # Set spawn point in Left Room (guaranteed dungeon_floor tile)
            player_spawn = (6 * TILE_SIZE, 15 * TILE_SIZE)

            # Portals
            # Left exit -> Ruins (placed at room edge, not wall column 0)
            portals.append({
                "rect": pygame.Rect(3 * TILE_SIZE, 14 * TILE_SIZE, TILE_SIZE, TILE_SIZE * 2),
                "target_map": MAP_RUINS,
                "target_spawn": ((w - 3) * TILE_SIZE, h // 2 * TILE_SIZE)
            })
            # Bottom-right exit -> Mountain (Boss Chamber bottom edge)
            portals.append({
                "rect": pygame.Rect(28 * TILE_SIZE, 23 * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_MOUNTAIN,
                "target_spawn": (w // 2 * TILE_SIZE, 3 * TILE_SIZE)
            })

        elif map_name == MAP_SECRET:
            # Small hidden glade
            for r in range(h):
                for c in range(w):
                    if r == 0 or r == h - 1 or c == 0 or c == w - 1:
                        grid[r][c] = "tree"
                    elif (r < 6 or r > h - 7 or c < 6 or c > w - 7) and random.random() < 0.3:
                        grid[r][c] = "tree"

            # Place water puddle
            for r in range(12, 18):
                for c in range(16, 24):
                    grid[r][c] = "water"

            # Landmark: Ancient Altar (dirt clearing at center north)
            for r in range(5, 10):
                for c in range(w // 2 - 3, w // 2 + 4):
                    grid[r][c] = "dirt"

            # NPCs (Spirit of Asterra at altar)
            npcs.append({"type": "spirit", "pos": (w // 2 * TILE_SIZE, 7 * TILE_SIZE)})

            # Clear spawn zone (bottom portal entry area) from random trees
            for dr in range(h - 6, h - 1):
                for dc in range(w // 2 - 1, w // 2 + 3):
                    if grid[dr][dc] == "tree" and dr != h - 1:
                        grid[dr][dc] = "grass"
            # Clear bottom portal exit tiles
            grid[h - 1][w // 2] = "grass"
            grid[h - 1][w // 2 + 1] = "grass"

            # Rare artifacts chest
            chests.append({"pos": (w // 2 * TILE_SIZE, 8 * TILE_SIZE), "loot": [("Asterra Heart", 1), ("Asterra Sword", 1)]})

            # Enemies (protecting the chest)
            enemies.append({"type": "slime_red", "pos": (12 * TILE_SIZE, 8 * TILE_SIZE)})
            enemies.append({"type": "slime_red", "pos": (28 * TILE_SIZE, 8 * TILE_SIZE)})

            # Portal
            # Bottom -> Lake
            portals.append({
                "rect": pygame.Rect((w // 2) * TILE_SIZE, (h - 1) * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE),
                "target_map": MAP_LAKE,
                "target_spawn": (w // 2 * TILE_SIZE, 3 * TILE_SIZE)
            })

            # Default spawn on grass (not center water puddle)
            player_spawn = (w // 2 * TILE_SIZE, (h - 5) * TILE_SIZE)

        # Assemble map database
        assembled_data = {
            "grid": grid,
            "player_spawn": player_spawn,
            "portals": portals,
            "enemies": enemies,
            "npcs": npcs,
            "chests": chests
        }

        # Save map layout as JSON to disk for customization/modding
        try:
            serializable_data = assembled_data.copy()
            serializable_data["portals"] = []
            for portal in portals:
                rect = portal["rect"]
                serializable_data["portals"].append({
                    "rect": [rect.x, rect.y, rect.width, rect.height],
                    "target_map": portal["target_map"],
                    "target_spawn": portal["target_spawn"]
                })

            with open(file_path, 'w') as f:
                json.dump(serializable_data, f, indent=4)
        except Exception as e:
            print(f"Warning: Failed to save map layout {file_path} to disk. Details: {e}")

        return assembled_data

def _rand_pixel_pos(w: int, h: int, allowed_tile: str = "grass", grid: List[List[str]] = None) -> Tuple[float, float]:
    """Helper that picks a random valid coordinate not inside a solid tile/tree."""
    for _ in range(100):
        c = random.randint(2, w - 3)
        r = random.randint(2, h - 3)

        # Check matching tile restriction if provided
        if grid:
            if grid[r][c] != allowed_tile:
                continue

        return (c * TILE_SIZE + TILE_SIZE // 2, r * TILE_SIZE + TILE_SIZE // 2)

    return (w // 2 * TILE_SIZE, h // 2 * TILE_SIZE)

# Inline math fast calculations
def math_sin(rad: float) -> float:
    import math
    return math.sin(rad)
