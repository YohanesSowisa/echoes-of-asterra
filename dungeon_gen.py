"""
Echoes of Asterra - Procedural Dungeon Generator
BSP (Binary Space Partitioning) algorithm generating infinite replayable dungeon levels.
Produces dynamic room layouts, corridors, traps, enemy spawns, chests, and boss chambers
across 5 environmental themes (Cave, Temple, Crypt, Ice, Volcano) with scaling depth difficulty.
"""
import random
import pygame
from typing import Dict, List, Any, Optional
from rpg.constants import (
    DUNGEON_CAVE, DUNGEON_TEMPLE, DUNGEON_CRYPT, DUNGEON_ICE, DUNGEON_VOLCANO,
    MAP_CRYPT
)
from rpg.settings import GRID_WIDTH, GRID_HEIGHT, TILE_SIZE

THEMES_LIST = [DUNGEON_CRYPT, DUNGEON_CAVE, DUNGEON_TEMPLE, DUNGEON_ICE, DUNGEON_VOLCANO]

class BSPNode:
    """Node representing a partition rectangle in space."""
    def __init__(self, x: int, y: int, w: int, h: int) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.left: Optional['BSPNode'] = None
        self.right: Optional['BSPNode'] = None
        self.room: Optional[pygame.Rect] = None

    def split(self, min_size: int = 8) -> bool:
        """Splits node into two sub-nodes horizontally or vertically."""
        if self.left or self.right:
            return False

        # Decide split direction
        split_h = random.choice([True, False])
        if self.w / self.h >= 1.4:
            split_h = False  # Split vertically (x-axis)
        elif self.h / self.w >= 1.4:
            split_h = True   # Split horizontally (y-axis)

        max_val = (self.h if split_h else self.w) - min_size
        if max_val <= min_size:
            return False

        split_pos = random.randint(min_size, max_val)

        if split_h:
            self.left = BSPNode(self.x, self.y, self.w, split_pos)
            self.right = BSPNode(self.x, self.y + split_pos, self.w, self.h - split_pos)
        else:
            self.left = BSPNode(self.x, self.y, split_pos, self.h)
            self.right = BSPNode(self.x + split_pos, self.y, self.w - split_pos, self.h)

        return True

    def create_rooms(self) -> List[pygame.Rect]:
        """Recursively builds room rects inside leaf nodes."""
        if self.left or self.right:
            rooms = []
            if self.left: rooms.extend(self.left.create_rooms())
            if self.right: rooms.extend(self.right.create_rooms())
            return rooms
        else:
            # Leaf node: carve out room with random margins
            rw = random.randint(max(5, self.w - 3), max(6, self.w - 1))
            rh = random.randint(max(5, self.h - 3), max(6, self.h - 1))
            rx = self.x + random.randint(1, max(1, self.w - rw - 1))
            ry = self.y + random.randint(1, max(1, self.h - rh - 1))
            self.room = pygame.Rect(rx, ry, rw, rh)
            return [self.room]

class DungeonGenerator:
    """
    Algorithmic procedural dungeon layout engine.
    """
    @staticmethod
    def generate_floor(depth: int, seed: int, theme: str = DUNGEON_CRYPT) -> Dict[str, Any]:
        """
        Builds a full procedural map container for the specified floor depth and theme.
        """
        random.seed(seed + depth * 997)
        w, h = GRID_WIDTH, GRID_HEIGHT

        # Select floor tile string based on theme
        floor_tile = "dungeon_floor" if theme in [DUNGEON_CRYPT, DUNGEON_TEMPLE] else ("sand" if theme == DUNGEON_CAVE else "dirt")
        wall_tile = "wall"

        # Initialize solid wall grid
        grid = [[wall_tile for _ in range(w)] for _ in range(h)]

        # 1. BSP Room Partitioning
        root = BSPNode(1, 1, w - 2, h - 2)
        nodes = [root]
        for _ in range(4):  # 4 iterations -> up to 16 leaves
            for n in list(nodes):
                if n.split():
                    nodes.extend([n.left, n.right])

        rooms = root.create_rooms()

        # 2. Carve out room floor tiles
        for room in rooms:
            for r in range(room.top, room.bottom):
                for c in range(room.left, room.right):
                    if 0 <= r < h and 0 <= c < w:
                        grid[r][c] = floor_tile

        # 3. Connect rooms via corridors (L-shaped wide tunnels)
        for i in range(len(rooms) - 1):
            r1 = rooms[i]
            r2 = rooms[i + 1]
            cx1, cy1 = r1.centerx, r1.centery
            cx2, cy2 = r2.centerx, r2.centery

            # Horizontal corridor
            start_x, end_x = min(cx1, cx2), max(cx1, cx2)
            for x in range(start_x, end_x + 1):
                for dy in range(2):
                    if 0 <= cy1 + dy < h and 0 <= x < w:
                        grid[cy1 + dy][x] = floor_tile

            # Vertical corridor
            start_y, end_y = min(cy1, cy2), max(cy1, cy2)
            for y in range(start_y, end_y + 1):
                for dx in range(2):
                    if 0 <= y < h and 0 <= cx2 + dx < w:
                        grid[y][cx2 + dx] = floor_tile

        # 4. Determine Spawn (Entrance) and Exit Portal (Stairs Down)
        entrance_room = rooms[0]
        exit_room = rooms[-1]

        player_spawn = (entrance_room.centerx * TILE_SIZE, entrance_room.centery * TILE_SIZE)

        portals = []

        # Exit portal (Stairs Down to next floor depth)
        portals.append({
            "rect": pygame.Rect(exit_room.centerx * TILE_SIZE, exit_room.centery * TILE_SIZE, TILE_SIZE * 2, TILE_SIZE * 2),
            "target_map": MAP_CRYPT,
            "target_spawn": (entrance_room.centerx * TILE_SIZE, entrance_room.centery * TILE_SIZE)
        })

        # Return portal to Village (in entrance room)
        portals.append({
            "rect": pygame.Rect((entrance_room.left + 1) * TILE_SIZE, (entrance_room.top + 1) * TILE_SIZE, TILE_SIZE, TILE_SIZE),
            "target_map": "village",
            "target_spawn": (GRID_WIDTH // 2 * TILE_SIZE, 3 * TILE_SIZE)
        })

        # 5. Populate Enemies
        enemies = []
        is_boss_floor = (depth % 5 == 0)

        theme_enemy_pool = {
            DUNGEON_CRYPT: ["skeleton", "mage", "slime_red"],
            DUNGEON_CAVE: ["slime", "slime_blue", "goblin"],
            DUNGEON_TEMPLE: ["skeleton", "mage", "knight"],
            DUNGEON_ICE: ["slime_blue", "wolf"],
            DUNGEON_VOLCANO: ["slime_red", "mage", "knight"]
        }
        pool = theme_enemy_pool.get(theme, ["skeleton", "slime"])

        for idx, room in enumerate(rooms[1:]):  # Skip entrance room
            if is_boss_floor and idx == len(rooms) - 2:
                # Boss chamber
                enemies.append({"type": "boss", "pos": (room.centerx * TILE_SIZE, room.centery * TILE_SIZE)})
            else:
                num_e = random.randint(1, min(4, 1 + depth // 2))
                for _ in range(num_e):
                    ex = random.randint(room.left + 1, room.right - 2) * TILE_SIZE
                    ey = random.randint(room.top + 1, room.bottom - 2) * TILE_SIZE
                    e_type = random.choice(pool)
                    enemies.append({"type": e_type, "pos": (ex, ey)})

        # 6. Populate Loot Chests
        chests = []
        num_chests = random.randint(1, 3)
        for _ in range(num_chests):
            c_room = random.choice(rooms[1:])
            cx = (c_room.left + 1) * TILE_SIZE
            cy = (c_room.top + 1) * TILE_SIZE

            # Scale loot quality with depth
            loot_list = [("Red Potion", 1)]
            if depth >= 3:
                loot_list.append(("Iron Ore", random.randint(1, 3)))
            if depth >= 5:
                loot_list.append(("Steel Blade", 1))
            if depth >= 10:
                loot_list.append(("Asterra Heart", 1))

            chests.append({"pos": (cx, cy), "loot": loot_list})

        random.seed()  # Reset RNG seed

        return {
            "grid": grid,
            "player_spawn": player_spawn,
            "portals": portals,
            "enemies": enemies,
            "npcs": [],
            "chests": chests,
            "depth": depth,
            "theme": theme
        }
