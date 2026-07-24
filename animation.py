"""
Echoes of Asterra - Animation & Procedural Graphics Generator
Generates and caches all pixel art assets (tiles, characters, projectiles, UI elements) in the assets/ directory.
"""
import os
import pygame
import math
from typing import Dict, List, Tuple, Optional
from rpg.constants import (
    DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT,
    COLOR_TRANSPARENT, COLOR_WHITE, COLOR_BLACK, COLOR_GRAY, COLOR_DARK_GRAY, COLOR_LIGHT_GRAY,
    COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW, COLOR_ORANGE, COLOR_PURPLE, COLOR_CYAN
)
from rpg.settings import TILE_SIZE

# Calculate absolute paths for robustness
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Pixel art asset storage
tile_assets: Dict[str, pygame.Surface] = {}
entity_assets: Dict[str, Dict[str, Dict[str, List[pygame.Surface]]]] = {}  # entity_name -> state -> direction -> frames
item_assets: Dict[str, pygame.Surface] = {}
projectile_assets: Dict[str, List[pygame.Surface]] = {}

def initialize_font_asset() -> Optional[str]:
    """
    Finds a standard system font and copies it to assets/fonts/game_font.ttf.
    If offline copy fails, tries downloading a retro TTF from Google Fonts.
    """
    font_folder = os.path.join(ASSETS_DIR, "fonts")
    os.makedirs(font_folder, exist_ok=True)
    font_path = os.path.join(font_folder, "game_font.ttf")
    
    if os.path.exists(font_path):
        return font_path
        
    # Search system paths for standard fonts
    search_paths = []
    import sys
    import shutil
    
    if sys.platform == "darwin":  # Mac
        search_paths = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
            "/System/Library/Fonts/Helvetica.ttf",
            "/System/Library/Fonts/Geneva.ttf"
        ]
    elif sys.platform == "win32":  # Windows
        search_paths = [
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\cour.ttf",
            "C:\\Windows\\Fonts\\tahoma.ttf"
        ]
    else:  # Linux / Unix
        search_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]
        
    for path in search_paths:
        if os.path.exists(path):
            try:
                shutil.copy(path, font_path)
                print(f"Font: Copied system font {path} to {font_path}")
                return font_path
            except Exception:
                continue
                
    # Fallback to download a pixel font if online
    try:
        import urllib.request
        url = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/pressstart2p/PressStart2P-Regular.ttf"
        print("Font: Downloading retro font from Google Fonts CDN...")
        with urllib.request.urlopen(url, timeout=4.0) as response:
            with open(font_path, 'wb') as f:
                f.write(response.read())
        print(f"Font: Downloaded and saved to {font_path}")
        return font_path
    except Exception as e:
        print(f"Font: Could not copy system font or download. Falling back to system fonts. Details: {e}")
        
    return None

from typing import Optional

def init_assets() -> None:
    """Initializes, loads, or pre-renders all graphical assets, saving them to disk if missing."""
    os.makedirs(os.path.join(ASSETS_DIR, "tiles"), exist_ok=True)
    os.makedirs(os.path.join(ASSETS_DIR, "ui"), exist_ok=True)
    os.makedirs(os.path.join(ASSETS_DIR, "sprites"), exist_ok=True)
    os.makedirs(os.path.join(ASSETS_DIR, "fonts"), exist_ok=True)
    
    # Initialize font files
    initialize_font_asset()
    
    # 1. Load or Generate Tiles
    tile_keys = ["grass", "dirt", "water", "wall", "sand", "tree", "dungeon_floor", "chest_closed", "chest_open"]
    all_tiles_exist = all(os.path.exists(os.path.join(ASSETS_DIR, "tiles", f"{k}.png")) for k in tile_keys)
    
    if all_tiles_exist:
        for k in tile_keys:
            path = os.path.join(ASSETS_DIR, "tiles", f"{k}.png")
            has_a = k in ["water", "tree", "chest_closed", "chest_open"]
            tile_assets[k] = pygame.image.load(path).convert_alpha() if has_a else pygame.image.load(path).convert()
    else:
        _generate_tiles()
        for k in tile_keys:
            if k in tile_assets:
                path = os.path.join(ASSETS_DIR, "tiles", f"{k}.png")
                pygame.image.save(tile_assets[k], path)

    # 2. Load or Generate Items
    item_keys = ["weapon", "shield", "helmet", "chest", "legs", "boots", "potion_red", "potion_blue", "food", "quest", "material_iron", "material_wood", "accessory", "artifact"]
    all_items_exist = all(os.path.exists(os.path.join(ASSETS_DIR, "ui", f"item_{k}.png")) for k in item_keys)
    
    if all_items_exist:
        for k in item_keys:
            path = os.path.join(ASSETS_DIR, "ui", f"item_{k}.png")
            item_assets[k] = pygame.image.load(path).convert_alpha()
    else:
        _generate_items()
        for k in item_keys:
            if k in item_assets:
                path = os.path.join(ASSETS_DIR, "ui", f"item_{k}.png")
                pygame.image.save(item_assets[k], path)

    # 3. Load or Generate Projectiles
    proj_keys = ["fireball", "ice_spike", "dark_bolt"]
    all_proj_exist = True
    for k in proj_keys:
        for f in range(3):
            if not os.path.exists(os.path.join(ASSETS_DIR, "sprites", f"proj_{k}_{f}.png")):
                all_proj_exist = False
                break
                
    if all_proj_exist:
        for k in proj_keys:
            projectile_assets[k] = []
            for f in range(3):
                path = os.path.join(ASSETS_DIR, "sprites", f"proj_{k}_{f}.png")
                projectile_assets[k].append(pygame.image.load(path).convert_alpha())
    else:
        _generate_projectiles()
        for k in proj_keys:
            if k in projectile_assets:
                for f, surf in enumerate(projectile_assets[k]):
                    path = os.path.join(ASSETS_DIR, "sprites", f"proj_{k}_{f}.png")
                    pygame.image.save(surf, path)

    # 4. Load or Generate Entities
    check_file = os.path.join(ASSETS_DIR, "sprites", "player_idle_down_0.png")
    if os.path.exists(check_file):
        filenames = sorted(os.listdir(os.path.join(ASSETS_DIR, "sprites")))
        entity_assets.clear()
        for file in filenames:
            if file.endswith(".png") and not file.startswith("proj_"):
                parts = file[:-4].split("_")
                if len(parts) >= 4:
                    frame = int(parts[-1])
                    direction = parts[-2]
                    state = parts[-3]
                    entity = "_".join(parts[:-3])
                    
                    if entity not in entity_assets:
                        entity_assets[entity] = {}
                    if state not in entity_assets[entity]:
                        entity_assets[entity][state] = {}
                    if direction not in entity_assets[entity][state]:
                        entity_assets[entity][state][direction] = []
                        
                    path = os.path.join(ASSETS_DIR, "sprites", file)
                    entity_assets[entity][state][direction].append(pygame.image.load(path).convert_alpha())
    else:
        _generate_entities()
        for entity, states in entity_assets.items():
            for state, directions in states.items():
                for direction, frames in directions.items():
                    for f, surf in enumerate(frames):
                          file_name = f"{entity}_{state}_{direction}_{f}.png"
                          path = os.path.join(ASSETS_DIR, "sprites", file_name)
                          pygame.image.save(surf, path)

def _create_outline(surface: pygame.Surface, color: Tuple[int, int, int] = COLOR_BLACK) -> pygame.Surface:
    """Draws a 1-pixel thick outline around a surface's non-transparent pixels."""
    outline_surf = pygame.Surface((surface.get_width() + 2, surface.get_height() + 2), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(surface)
    
    # Render outline by shifting mask
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        outline_surf.blit(mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0)), (dx + 1, dy + 1))
        
    outline_surf.blit(surface, (1, 1))
    return outline_surf

def _generate_tiles() -> None:
    """Generates environment tiles procedurally."""
    # 1. Grass Tile
    grass = pygame.Surface((TILE_SIZE, TILE_SIZE))
    grass.fill((70, 155, 75))
    # Add grass blades
    for x, y in [(8, 12), (24, 6), (36, 18), (14, 32), (28, 40), (4, 42), (40, 36)]:
        pygame.draw.line(grass, (90, 185, 95), (x, y), (x, y - 4), 2)
        pygame.draw.line(grass, (50, 125, 55), (x + 2, y), (x + 2, y - 2), 2)
    tile_assets["grass"] = grass

    # 2. Dirt Tile
    dirt = pygame.Surface((TILE_SIZE, TILE_SIZE))
    dirt.fill((110, 80, 55))
    # Add speckles
    for x, y in [(4, 6), (16, 20), (32, 10), (10, 38), (28, 30), (42, 42)]:
        pygame.draw.rect(dirt, (90, 60, 40), (x, y, 4, 4))
        pygame.draw.rect(dirt, (130, 100, 75), (x + 4, y + 4, 2, 2))
    tile_assets["dirt"] = dirt

    # 3. Water Tile
    water = pygame.Surface((TILE_SIZE, TILE_SIZE))
    water.fill((45, 95, 215))
    # Wave details
    for x, y in [(8, 16), (28, 12), (18, 36), (38, 28)]:
        pygame.draw.line(water, (75, 135, 235), (x, y), (x + 10, y), 2)
        pygame.draw.line(water, (30, 70, 160), (x - 2, y + 2), (x + 8, y + 2), 1)
    tile_assets["water"] = water

    # 4. Stone Wall (Solid Obstacle)
    wall = pygame.Surface((TILE_SIZE, TILE_SIZE))
    wall.fill((100, 105, 115))
    # Draw brick pattern
    pygame.draw.line(wall, (60, 62, 70), (0, 0), (TILE_SIZE, 0), 2)
    pygame.draw.line(wall, (60, 62, 70), (0, TILE_SIZE // 2), (TILE_SIZE, TILE_SIZE // 2), 2)
    pygame.draw.line(wall, (60, 62, 70), (0, TILE_SIZE - 1), (TILE_SIZE, TILE_SIZE - 1), 2)
    pygame.draw.line(wall, (60, 62, 70), (TILE_SIZE // 2, 0), (TILE_SIZE // 2, TILE_SIZE // 2), 2)
    pygame.draw.line(wall, (60, 62, 70), (TILE_SIZE // 4, TILE_SIZE // 2), (TILE_SIZE // 4, TILE_SIZE), 2)
    pygame.draw.line(wall, (60, 62, 70), (3 * TILE_SIZE // 4, TILE_SIZE // 2), (3 * TILE_SIZE // 4, TILE_SIZE), 2)
    # Highlights
    pygame.draw.line(wall, (140, 145, 155), (2, 2), (TILE_SIZE // 2 - 2, 2), 2)
    pygame.draw.line(wall, (140, 145, 155), (2, TILE_SIZE // 2 + 2), (TILE_SIZE // 4 - 2, TILE_SIZE // 2 + 2), 2)
    tile_assets["wall"] = wall

    # 5. Sand Tile
    sand = pygame.Surface((TILE_SIZE, TILE_SIZE))
    sand.fill((235, 210, 140))
    # Sand grains
    for x, y in [(12, 10), (28, 22), (4, 30), (38, 38)]:
        pygame.draw.rect(sand, (215, 185, 110), (x, y, 2, 2))
    tile_assets["sand"] = sand

    # 6. Tree Base (Decorative Solid)
    tree = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(tree, (100, 65, 35), (TILE_SIZE // 3, TILE_SIZE // 4, TILE_SIZE // 3, 3 * TILE_SIZE // 4))
    # Leaf canopy
    pygame.draw.circle(tree, (35, 115, 45), (TILE_SIZE // 2, TILE_SIZE // 3), TILE_SIZE // 3)
    pygame.draw.circle(tree, (45, 135, 55), (TILE_SIZE // 2 - 6, TILE_SIZE // 3 - 4), TILE_SIZE // 4)
    tile_assets["tree"] = _create_outline(tree)

    # 7. Dungeon Floor Tile
    dungeon = pygame.Surface((TILE_SIZE, TILE_SIZE))
    dungeon.fill((45, 45, 55))
    # Cracks/slab outlines
    pygame.draw.rect(dungeon, (25, 25, 30), (0, 0, TILE_SIZE, TILE_SIZE), 1)
    pygame.draw.line(dungeon, (30, 30, 35), (10, 10), (25, 25), 1)
    pygame.draw.line(dungeon, (30, 30, 35), (25, 25), (20, 38), 1)
    tile_assets["dungeon_floor"] = dungeon

    # 8. Chest (Interactive Container)
    chest_closed = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(chest_closed, (139, 69, 19), (6, 12, 36, 28))
    pygame.draw.rect(chest_closed, (205, 133, 63), (6, 12, 36, 10))
    pygame.draw.rect(chest_closed, (218, 165, 32), (20, 18, 8, 12))  # Lock plate
    pygame.draw.circle(chest_closed, COLOR_BLACK, (24, 26), 2)       # Keyhole
    # Gold bindings
    pygame.draw.rect(chest_closed, (218, 165, 32), (10, 12, 4, 28))
    pygame.draw.rect(chest_closed, (218, 165, 32), (34, 12, 4, 28))
    tile_assets["chest_closed"] = _create_outline(chest_closed)

    chest_open = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    # Open lid shifted back
    pygame.draw.rect(chest_open, (100, 50, 10), (6, 4, 36, 8))
    # Chest base with gold shining inside
    pygame.draw.rect(chest_open, (139, 69, 19), (6, 16, 36, 24))
    pygame.draw.rect(chest_open, COLOR_YELLOW, (10, 16, 28, 8))
    pygame.draw.rect(chest_open, (218, 165, 32), (10, 16, 4, 24))
    pygame.draw.rect(chest_open, (218, 165, 32), (34, 16, 4, 24))
    tile_assets["chest_open"] = _create_outline(chest_open)

def _generate_items() -> None:
    """Generates procedural 32x32 UI icon textures for items."""
    sz = 32
    
    # 1. Weapon (Sword)
    sword = pygame.Surface((sz, sz), pygame.SRCALPHA)
    # Blade (Diagonal)
    for i in range(18):
        pygame.draw.rect(sword, (200, 205, 215), (10 + i, 22 - i, 3, 3))
    # Guard
    pygame.draw.line(sword, (180, 130, 40), (8, 22), (14, 28), 3)
    # Hilt
    pygame.draw.line(sword, (100, 60, 20), (6, 24), (2, 28), 3)
    item_assets["weapon"] = _create_outline(sword)

    # 2. Shield
    shield = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.polygon(shield, (180, 130, 40), [(6, 4), (26, 4), (26, 18), (16, 28), (6, 18)])
    pygame.draw.polygon(shield, (140, 145, 155), [(9, 7), (23, 7), (23, 17), (16, 24), (9, 17)])
    # Emblem
    pygame.draw.line(shield, COLOR_RED, (16, 9), (16, 20), 2)
    item_assets["shield"] = _create_outline(shield)

    # 3. Helmet
    helmet = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.circle(helmet, COLOR_GRAY, (sz // 2, 16), 10)
    pygame.draw.rect(helmet, COLOR_GRAY, (6, 16, 20, 10))
    # Visor slit
    pygame.draw.rect(helmet, (30, 30, 35), (10, 13, 12, 3))
    pygame.draw.line(helmet, COLOR_YELLOW, (16, 4), (16, 10), 2) # Crest
    item_assets["helmet"] = _create_outline(helmet)

    # 4. Armor Chestplate
    chest = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.rect(chest, COLOR_GRAY, (8, 10, 16, 16), border_radius=4)
    # Shoulder pauldrons
    pygame.draw.rect(chest, (140, 145, 155), (4, 8, 6, 6), border_radius=1)
    pygame.draw.rect(chest, (140, 145, 155), (22, 8, 6, 6), border_radius=1)
    # Neck cutout
    pygame.draw.circle(chest, COLOR_TRANSPARENT, (sz // 2, 8), 3)
    item_assets["chest"] = _create_outline(chest)

    # 5. Legs (Greaves)
    legs = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.rect(legs, COLOR_GRAY, (8, 6, 16, 10))
    pygame.draw.rect(legs, (110, 115, 125), (8, 16, 6, 12))
    pygame.draw.rect(legs, (110, 115, 125), (18, 16, 6, 12))
    item_assets["legs"] = _create_outline(legs)

    # 6. Boots
    boots = pygame.Surface((sz, sz), pygame.SRCALPHA)
    # Left boot
    pygame.draw.rect(boots, (90, 60, 40), (6, 14, 8, 12), border_radius=2)
    pygame.draw.rect(boots, (90, 60, 40), (4, 22, 10, 5))
    # Right boot
    pygame.draw.rect(boots, (90, 60, 40), (18, 14, 8, 12), border_radius=2)
    pygame.draw.rect(boots, (90, 60, 40), (16, 22, 10, 5))
    item_assets["boots"] = _create_outline(boots)

    # 7. Health Potion (Red liquid inside glass)
    hp_pot = pygame.Surface((sz, sz), pygame.SRCALPHA)
    # Neck/cap
    pygame.draw.rect(hp_pot, (139, 69, 19), (14, 4, 4, 3))
    pygame.draw.rect(hp_pot, (200, 200, 240, 150), (13, 7, 6, 6)) # Glass neck
    # Round flask
    pygame.draw.circle(hp_pot, (200, 200, 240, 150), (sz // 2, 20), 8) # Glass base
    pygame.draw.circle(hp_pot, COLOR_RED, (sz // 2, 21), 6)            # Red potion
    # Glint
    pygame.draw.circle(hp_pot, COLOR_WHITE, (13, 17), 2)
    item_assets["potion_red"] = _create_outline(hp_pot)

    # 8. Mana Potion (Blue liquid)
    mp_pot = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.rect(mp_pot, (139, 69, 19), (14, 4, 4, 3))
    pygame.draw.rect(mp_pot, (200, 200, 240, 150), (13, 7, 6, 6))
    pygame.draw.circle(mp_pot, (200, 200, 240, 150), (sz // 2, 20), 8)
    pygame.draw.circle(mp_pot, COLOR_BLUE, (sz // 2, 21), 6)
    pygame.draw.circle(mp_pot, COLOR_WHITE, (13, 17), 2)
    item_assets["potion_blue"] = _create_outline(mp_pot)

    # 9. Food (Bread)
    food = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.ellipse(food, (190, 130, 70), (4, 10, 24, 12))
    # Diagonal score marks
    pygame.draw.line(food, (120, 80, 45), (10, 12), (14, 18), 2)
    pygame.draw.line(food, (120, 80, 45), (16, 12), (20, 18), 2)
    item_assets["food"] = _create_outline(food)

    # 10. Quest Item (Ancient Scroll)
    scroll = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.rect(scroll, (230, 215, 175), (8, 6, 16, 20))
    # Wood roller ends
    pygame.draw.line(scroll, (120, 70, 30), (6, 6), (26, 6), 2)
    pygame.draw.line(scroll, (120, 70, 30), (6, 25), (26, 25), 2)
    # Red ribbon seal
    pygame.draw.rect(scroll, COLOR_RED, (14, 13, 4, 4))
    item_assets["quest"] = _create_outline(scroll)

    # 11. Crafting Material (Iron Ore)
    iron = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.polygon(iron, COLOR_GRAY, [(6, 22), (16, 6), (26, 22), (16, 26)])
    # Shiny crystals/metal flecks
    pygame.draw.rect(iron, COLOR_WHITE, (12, 12, 3, 3))
    pygame.draw.rect(iron, COLOR_LIGHT_GRAY, (18, 16, 2, 2))
    item_assets["material_iron"] = _create_outline(iron)

    # 12. Crafting Material (Wood Plank)
    wood = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.rect(wood, (139, 90, 43), (4, 8, 24, 16))
    # Grain lines
    pygame.draw.line(wood, (100, 60, 20), (6, 12), (26, 12), 1)
    pygame.draw.line(wood, (100, 60, 20), (10, 18), (22, 18), 1)
    item_assets["material_wood"] = _create_outline(wood)

    # 13. Accessory (Ring)
    ring = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.circle(ring, COLOR_YELLOW, (sz // 2, sz // 2), 6, 2)
    # Gem
    pygame.draw.circle(ring, COLOR_CYAN, (sz // 2, sz // 2 - 6), 3)
    item_assets["accessory"] = _create_outline(ring)

    # 14. Rare Artifact (Ruby Heart)
    ruby = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.polygon(ruby, COLOR_RED, [(16, 8), (22, 14), (16, 24), (10, 14)])
    pygame.draw.circle(ruby, COLOR_RED, (13, 10), 3)
    pygame.draw.circle(ruby, COLOR_RED, (19, 10), 3)
    # Gem glint
    pygame.draw.circle(ruby, COLOR_WHITE, (19, 9), 1)
    item_assets["artifact"] = _create_outline(ruby)

def _generate_projectiles() -> None:
    """Generates magic/projectile animations."""
    sz = 24
    
    # 1. Fireball (3 frames)
    fireball_frames = []
    for f in range(3):
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        # Inner core
        pygame.draw.circle(surf, COLOR_WHITE, (sz // 2 - f, sz // 2), 4)
        # Outer fire
        pygame.draw.circle(surf, COLOR_ORANGE, (sz // 2, sz // 2), 6 + f)
        pygame.draw.circle(surf, COLOR_RED, (sz // 2 + 2, sz // 2 - 1), 7)
        # Flame trail
        pygame.draw.polygon(surf, COLOR_RED, [(6 - f, sz // 2 - 4), (12, sz // 2), (6 - f, sz // 2 + 4)])
        fireball_frames.append(_create_outline(surf, COLOR_DARK_GRAY))
    projectile_assets["fireball"] = fireball_frames

    # 2. Ice Spike (3 frames)
    ice_frames = []
    for f in range(3):
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        # Sharp diamond
        pygame.draw.polygon(surf, COLOR_CYAN, [(16 + f, sz // 2), (8, sz // 2 - 5), (4, sz // 2), (8, sz // 2 + 5)])
        # Ice Core
        pygame.draw.line(surf, COLOR_WHITE, (8, sz // 2), (14 + f, sz // 2), 2)
        ice_frames.append(_create_outline(surf, COLOR_BLUE))
    projectile_assets["ice_spike"] = ice_frames

    # 3. Enemy Magic Bolt (Dark purple)
    dark_frames = []
    for f in range(3):
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.circle(surf, COLOR_PURPLE, (sz // 2, sz // 2), 6)
        pygame.draw.circle(surf, COLOR_BLACK, (sz // 2, sz // 2), 3)
        # Pulsing swirls
        pygame.draw.circle(surf, COLOR_CYAN, (sz // 2 + int(math.sin(f * 2) * 4), sz // 2 + int(math.cos(f * 2) * 4)), 2)
        dark_frames.append(_create_outline(surf))
    projectile_assets["dark_bolt"] = dark_frames

def _draw_humanoid(state: str, direction: str, frame: int, max_frames: int, colors: Dict[str, Tuple[int, int, int]]) -> pygame.Surface:
    """Helper that procedurally renders a humanoid character frame by frame."""
    sz = 48
    surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
    
    # Extract colors
    c_skin = colors.get("skin", (240, 200, 160))
    c_hair = colors.get("hair", (120, 80, 45))
    c_body = colors.get("body", (45, 95, 215))
    c_legs = colors.get("legs", (80, 50, 30))
    c_boots = colors.get("boots", (50, 35, 25))
    c_weapon = colors.get("weapon", COLOR_LIGHT_GRAY)
    c_shield = colors.get("shield", COLOR_GRAY)
    
    # Calculate animation bounce/offsets
    bounce = 0
    if state == "walk":
        bounce = int(abs(math.sin(frame * (math.pi / (max_frames / 2.0)))) * 2)
        
    # Attack lunging offset
    lunge_x, lunge_y = 0, 0
    if state == "attack":
        prog = frame / max_frames
        dist = int(math.sin(prog * math.pi) * 8)
        if direction == DIR_UP: lunge_y = -dist
        elif direction == DIR_DOWN: lunge_y = dist
        elif direction == DIR_LEFT: lunge_x = -dist
        elif direction == DIR_RIGHT: lunge_x = dist
        
    # Dodge roll rotation
    roll_angle = 0
    if state == "roll":
        roll_angle = (frame / max_frames) * 360
        if direction == DIR_LEFT: roll_angle = -roll_angle
        
    # 1. Draw Feet / Boots (relative to center of screen)
    cx, cy = sz // 2 + lunge_x, sz // 2 + lunge_y
    
    # Base walking leg movement
    leg_offset = 0
    if state == "walk":
        leg_offset = 3 if (frame % 2 == 0) else -3
        
    # Draw left foot & right foot
    if direction in [DIR_UP, DIR_DOWN]:
        pygame.draw.rect(surf, c_boots, (cx - 7, cy + 12 - bounce + (leg_offset if direction == DIR_DOWN else -leg_offset), 4, 4))
        pygame.draw.rect(surf, c_boots, (cx + 3, cy + 12 - bounce + (-leg_offset if direction == DIR_DOWN else leg_offset), 4, 4))
    else: # Left or Right
        pygame.draw.rect(surf, c_boots, (cx - 5 + leg_offset, cy + 12 - bounce, 4, 4))
        pygame.draw.rect(surf, c_boots, (cx + 1 - leg_offset, cy + 12 - bounce, 4, 4))

    # 2. Draw Legs
    pygame.draw.rect(surf, c_legs, (cx - 6, cy + 6 - bounce, 12, 6))

    # 3. Draw Body/Tunic
    pygame.draw.rect(surf, c_body, (cx - 8, cy - 6 - bounce, 16, 12), border_radius=2)
    
    # 4. Draw Head
    pygame.draw.circle(surf, c_skin, (cx, cy - 12 - bounce), 6)
    
    # Hair
    if direction == DIR_UP:
        # Full back of hair
        pygame.draw.circle(surf, c_hair, (cx, cy - 13 - bounce), 7)
    elif direction == DIR_DOWN:
        # Front hair bangs
        pygame.draw.arc(surf, c_hair, (cx - 7, cy - 19 - bounce, 14, 10), 0, math.pi, 3)
    elif direction == DIR_LEFT:
        pygame.draw.circle(surf, c_hair, (cx + 2, cy - 13 - bounce), 6)
        pygame.draw.rect(surf, c_hair, (cx - 5, cy - 19 - bounce, 6, 6))
    elif direction == DIR_RIGHT:
        pygame.draw.circle(surf, c_hair, (cx - 2, cy - 13 - bounce), 6)
        pygame.draw.rect(surf, c_hair, (cx - 1, cy - 19 - bounce, 6, 6))

    # 5. Draw Eyes (except from back)
    if direction != DIR_UP:
        eye_color = COLOR_BLACK if "eye" not in colors else colors["eye"]
        if direction == DIR_DOWN:
            pygame.draw.rect(surf, eye_color, (cx - 4, cy - 13 - bounce, 2, 2))
            pygame.draw.rect(surf, eye_color, (cx + 2, cy - 13 - bounce, 2, 2))
        elif direction == DIR_LEFT:
            pygame.draw.rect(surf, eye_color, (cx - 4, cy - 13 - bounce, 2, 2))
        elif direction == DIR_RIGHT:
            pygame.draw.rect(surf, eye_color, (cx + 2, cy - 13 - bounce, 2, 2))

    # 6. Equipment (Sword, Shield)
    # Weapon position based on state and frame
    if state == "block" and c_shield:
        # Shield drawn in front
        if direction == DIR_DOWN:
            pygame.draw.rect(surf, c_shield, (cx - 8, cy - 2 - bounce, 16, 10), border_radius=2)
        elif direction == DIR_LEFT:
            pygame.draw.rect(surf, c_shield, (cx - 10, cy - 4 - bounce, 4, 12), border_radius=2)
        elif direction == DIR_RIGHT:
            pygame.draw.rect(surf, c_shield, (cx + 6, cy - 4 - bounce, 4, 12), border_radius=2)
        elif direction == DIR_UP:
            pygame.draw.rect(surf, c_shield, (cx - 8, cy - 8 - bounce, 16, 6))
            
    elif state == "attack":
        # Swing weapon arc
        prog = frame / max_frames
        angle = -45 + prog * 135  # swing range
        
        # Base weapon length
        w_len = 16
        rad = math.radians(angle)
        
        # Attack directions orientations
        if direction == DIR_DOWN:
            wx, wy = int(math.sin(rad) * w_len), int(math.cos(rad) * w_len)
            pygame.draw.line(surf, c_weapon, (cx + 6, cy), (cx + 6 + wx, cy + wy), 3)
        elif direction == DIR_UP:
            wx, wy = int(math.sin(rad) * w_len), -int(math.cos(rad) * w_len)
            pygame.draw.line(surf, c_weapon, (cx - 6, cy - 8), (cx - 6 + wx, cy - 8 + wy), 3)
        elif direction == DIR_LEFT:
            wx, wy = -int(math.cos(rad) * w_len), int(math.sin(rad) * w_len)
            pygame.draw.line(surf, c_weapon, (cx - 6, cy), (cx - 6 + wx, cy + wy), 3)
        elif direction == DIR_RIGHT:
            wx, wy = int(math.cos(rad) * w_len), int(math.sin(rad) * w_len)
            pygame.draw.line(surf, c_weapon, (cx + 6, cy), (cx + 6 + wx, cy + wy), 3)
            
    else:
        # Idle / walking weapon sheathed or held at side
        if direction == DIR_DOWN:
            # Shield left hand, Sword right hand
            pygame.draw.line(surf, c_weapon, (cx + 8, cy + 4 - bounce), (cx + 12, cy - 6 - bounce), 2)
            pygame.draw.rect(surf, c_shield, (cx - 12, cy - 2 - bounce, 4, 8))
        elif direction == DIR_LEFT:
            pygame.draw.line(surf, c_weapon, (cx + 2, cy + 4 - bounce), (cx + 6, cy - 6 - bounce), 2)
            pygame.draw.rect(surf, c_shield, (cx - 10, cy - 2 - bounce, 4, 8))
        elif direction == DIR_RIGHT:
            pygame.draw.line(surf, c_weapon, (cx - 6, cy + 4 - bounce), (cx - 10, cy - 6 - bounce), 2)
            pygame.draw.rect(surf, c_shield, (cx + 6, cy - 2 - bounce, 4, 8))
        elif direction == DIR_UP:
            # Sword on back
            pygame.draw.line(surf, c_weapon, (cx - 4, cy - 4 - bounce), (cx + 8, cy - 14 - bounce), 2)

    # Apply roll rotation if in roll state
    if state == "roll" and roll_angle != 0:
        rot_surf = pygame.transform.rotate(surf, roll_angle)
        # Re-center
        new_surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        new_surf.blit(rot_surf, (sz // 2 - rot_surf.get_width() // 2, sz // 2 - rot_surf.get_height() // 2))
        surf = new_surf

    # Apply death filter
    if state == "dead":
        dead_surf = pygame.transform.rotate(surf, 90)
        # Shift down to ground level and fade
        surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
        dead_surf.fill((100, 100, 100, 150), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(dead_surf, (0, 10))
        
    return _create_outline(surf)

def _generate_entities() -> None:
    """Pre-computes all frames for characters and monsters in all states & directions."""
    
    # 1. PLAYER RENDER
    p_colors = {
        "skin": (250, 205, 170),
        "hair": (230, 180, 50),     # Blonde hero
        "body": (40, 100, 220),     # Blue tunic
        "legs": (110, 85, 60),      # Brown pants
        "boots": (60, 45, 30),
        "weapon": COLOR_WHITE,
        "shield": (160, 165, 175)
    }
    _cache_humanoid_entity("player", p_colors)

    # 2. SKELETON (Monsters / Enemies)
    sk_colors = {
        "skin": (220, 220, 220),    # White bone
        "hair": COLOR_TRANSPARENT,
        "body": COLOR_DARK_GRAY,    # Tattered armor
        "legs": (80, 80, 80),
        "boots": COLOR_DARK_GRAY,
        "weapon": (160, 160, 165),
        "shield": COLOR_TRANSPARENT,
        "eye": COLOR_RED            # Glowing red eye-sockets
    }
    _cache_humanoid_entity("skeleton", sk_colors)

    # 3. GOBLIN
    gob_colors = {
        "skin": (80, 170, 70),       # Green skin
        "hair": (50, 40, 30),        # Dark messy hair
        "body": (140, 100, 60),      # Leather vest
        "legs": (100, 70, 45),
        "boots": (50, 35, 25),
        "weapon": (120, 120, 130),
        "shield": COLOR_TRANSPARENT,
        "eye": COLOR_YELLOW
    }
    _cache_humanoid_entity("goblin", gob_colors)

    # 4. MAGE
    mage_colors = {
        "skin": (245, 190, 150),
        "hair": (200, 200, 210),     # White beard
        "body": COLOR_PURPLE,        # Purple wizard robe
        "legs": COLOR_PURPLE,
        "boots": (30, 20, 40),
        "weapon": COLOR_YELLOW,      # Gold staff
        "shield": COLOR_TRANSPARENT,
        "eye": COLOR_CYAN
    }
    _cache_humanoid_entity("mage", mage_colors)

    # 5. KNIGHT
    knight_colors = {
        "skin": COLOR_GRAY,          # Full armor
        "hair": COLOR_TRANSPARENT,
        "body": (70, 75, 85),        # Steel armor
        "legs": (60, 65, 75),
        "boots": (50, 52, 60),
        "weapon": COLOR_WHITE,       # Shiny steel broadsword
        "shield": (120, 125, 135),
        "eye": COLOR_BLUE
    }
    _cache_humanoid_entity("knight", knight_colors)

    # 6. SLIME (Non-humanoid: Custom rendering)
    _cache_slime_entity("slime", COLOR_GREEN)
    _cache_slime_entity("slime_blue", COLOR_BLUE)  # Blue Slime variant
    _cache_slime_entity("slime_red", COLOR_RED)    # Red/Fire Slime variant

    # 7. WOLF (Quadruped: Custom rendering)
    _cache_wolf_entity("wolf", (110, 115, 125))

    # 8. BOSS: Giant Demonic Shadow Knight
    _cache_boss_entity()

def _cache_humanoid_entity(name: str, colors: Dict[str, Tuple[int, int, int]]) -> None:
    """Helper to generate all humanoid animation states and save to registry."""
    entity_assets[name] = {}
    
    states_frames = {
        "idle": 2,
        "walk": 4,
        "attack": 4,
        "roll": 4,
        "block": 1,
        "hurt": 2,
        "dead": 1
    }
    
    for state, num_frames in states_frames.items():
        entity_assets[name][state] = {}
        for direction in [DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT]:
            frames_list = []
            for f in range(num_frames):
                frames_list.append(_draw_humanoid(state, direction, f, num_frames, colors))
            entity_assets[name][state][direction] = frames_list

def _cache_slime_entity(name: str, color: Tuple[int, int, int]) -> None:
    """Generates bouncy slimes."""
    entity_assets[name] = {}
    sz = 48
    
    states_frames = {
        "idle": 2,
        "walk": 4,
        "attack": 3,
        "hurt": 2,
        "dead": 2
    }
    
    for state, num_frames in states_frames.items():
        entity_assets[name][state] = {}
        for direction in [DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT]:
            frames_list = []
            for f in range(num_frames):
                surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
                
                # Squash and stretch based on state & frame
                w_offset = 0
                h_offset = 0
                
                if state == "idle":
                    # Slow breathe
                    w_offset = int(math.sin(f * math.pi) * 3)
                    h_offset = -w_offset
                elif state in ["walk", "attack"]:
                    # Jump bounce
                    prog = f / num_frames
                    w_offset = -int(math.sin(prog * math.pi) * 4)
                    h_offset = int(math.sin(prog * math.pi) * 5)
                elif state == "hurt":
                    w_offset = 6
                    h_offset = -6
                
                cx, cy = sz // 2, sz // 2 + 6
                rx, ry = 14 + w_offset, 10 + h_offset
                
                if state == "dead":
                    # Puddle
                    rx, ry = 18, 4
                    cy = sz // 2 + 12
                    
                # Body
                pygame.draw.ellipse(surf, color, (cx - rx, cy - ry, rx * 2, ry * 2))
                # Inner highlight
                light_color = tuple(min(255, c + 60) for c in color)
                pygame.draw.ellipse(surf, light_color, (cx - rx + 4, cy - ry + 2, rx * 1.3, ry * 1.2))
                
                # Eyes (except from back)
                if direction != DIR_UP and state != "dead":
                    eye_x = cx
                    if direction == DIR_LEFT: eye_x -= 4
                    elif direction == DIR_RIGHT: eye_x += 4
                    
                    pygame.draw.circle(surf, COLOR_BLACK, (eye_x - 3, cy - 2), 2)
                    pygame.draw.circle(surf, COLOR_BLACK, (eye_x + 3, cy - 2), 2)
                    pygame.draw.circle(surf, COLOR_WHITE, (eye_x - 4, cy - 3), 1)
                    pygame.draw.circle(surf, COLOR_WHITE, (eye_x + 2, cy - 3), 1)
                    
                frames_list.append(_create_outline(surf))
            entity_assets[name][state][direction] = frames_list

def _cache_wolf_entity(name: str, color: Tuple[int, int, int]) -> None:
    """Generates animated quadruped wolf sprites."""
    entity_assets[name] = {}
    sz = 48
    
    states_frames = {
        "idle": 2,
        "walk": 4,
        "attack": 3,
        "hurt": 2,
        "dead": 1
    }
    
    for state, num_frames in states_frames.items():
        entity_assets[name][state] = {}
        for direction in [DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT]:
            frames_list = []
            for f in range(num_frames):
                surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
                
                # Center coordinates
                cx, cy = sz // 2, sz // 2 + 2
                
                # Animate body bounce
                bounce = int(abs(math.sin(f * (math.pi / 2))) * 2) if state == "walk" else 0
                
                # Tail wag
                tail_wag = int(math.sin(f * math.pi) * 3)
                
                # Render sideways vs frontways
                if direction in [DIR_LEFT, DIR_RIGHT]:
                    flip = (direction == DIR_LEFT)
                    # Body
                    pygame.draw.rect(surf, color, (cx - 14, cy - 4 - bounce, 24, 10), border_radius=2)
                    # Head
                    pygame.draw.circle(surf, color, (cx + 10 if not flip else cx - 10, cy - 6 - bounce), 6)
                    # Snout
                    pygame.draw.rect(surf, color, (cx + 14 if not flip else cx - 20, cy - 6 - bounce, 6, 4))
                    # Ears
                    pygame.draw.polygon(surf, color, [(cx + 8 if not flip else cx - 8, cy - 12 - bounce),
                                                      (cx + 11 if not flip else cx - 11, cy - 12 - bounce),
                                                      (cx + 9 if not flip else cx - 9, cy - 17 - bounce)])
                    # Tail
                    pygame.draw.line(surf, color, (cx - 14 if not flip else cx + 10, cy - 4 - bounce),
                                     (cx - 20 if not flip else cx + 16, cy - 8 - bounce + tail_wag), 3)
                    # Legs
                    leg_offset = 4 if (f % 2 == 0) else -4
                    # Front leg & back leg
                    pygame.draw.line(surf, color, (cx + 8 if not flip else cx - 8, cy + 6 - bounce), (cx + 8 + leg_offset if not flip else cx - 8 - leg_offset, cy + 12), 3)
                    pygame.draw.line(surf, color, (cx - 8 if not flip else cx + 8, cy + 6 - bounce), (cx - 8 - leg_offset if not flip else cx + 8 + leg_offset, cy + 12), 3)
                    
                    # Eyes
                    eye_x = cx + 11 if not flip else cx - 11
                    pygame.draw.rect(surf, COLOR_YELLOW, (eye_x, cy - 8 - bounce, 2, 2))
                else: # DIR_UP or DIR_DOWN
                    # Body front facing
                    pygame.draw.rect(surf, color, (cx - 8, cy - 2 - bounce, 16, 12), border_radius=2)
                    pygame.draw.circle(surf, color, (cx, cy - 6 - bounce), 6)
                    # Ears
                    pygame.draw.polygon(surf, color, [(cx - 6, cy - 10 - bounce), (cx - 3, cy - 10 - bounce), (cx - 5, cy - 15 - bounce)])
                    pygame.draw.polygon(surf, color, [(cx + 3, cy - 10 - bounce), (cx + 6, cy - 10 - bounce), (cx + 5, cy - 15 - bounce)])
                    
                    # Legs
                    leg_offset = 3 if (f % 2 == 0) else -3
                    pygame.draw.line(surf, color, (cx - 5, cy + 10 - bounce), (cx - 5, cy + 14 - bounce + leg_offset), 3)
                    pygame.draw.line(surf, color, (cx + 5, cy + 10 - bounce), (cx + 5, cy + 14 - bounce - leg_offset), 3)
                    
                    if direction == DIR_DOWN:
                        # Yellow wolf eyes
                        pygame.draw.circle(surf, COLOR_YELLOW, (cx - 2, cy - 7 - bounce), 1)
                        pygame.draw.circle(surf, COLOR_YELLOW, (cx + 2, cy - 7 - bounce), 1)

                if state == "hurt":
                    surf.fill((255, 100, 100, 100), special_flags=pygame.BLEND_RGBA_MULT)
                elif state == "dead":
                    dead_surf = pygame.transform.rotate(surf, 90)
                    surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
                    surf.blit(dead_surf, (0, 8))
                    
                frames_list.append(_create_outline(surf))
            entity_assets[name][state][direction] = frames_list

def _cache_boss_entity() -> None:
    """Generates the giant Final Boss (Dark Demon Knight). Scales to 72x72 pixels."""
    name = "boss"
    entity_assets[name] = {}
    sz = 72
    
    states_frames = {
        "idle": 4,
        "walk": 4,
        "attack": 5,
        "hurt": 2,
        "dead": 3
    }
    
    c_armor = (30, 25, 35)      # Obsidian black armor
    c_trim = COLOR_ORANGE       # Glowing lava trim
    c_horns = (180, 50, 40)     # Dark red horns
    c_sword = COLOR_ORANGE
    
    for state, num_frames in states_frames.items():
        entity_assets[name][state] = {}
        for direction in [DIR_DOWN, DIR_UP, DIR_LEFT, DIR_RIGHT]:
            frames_list = []
            for f in range(num_frames):
                surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
                
                bounce = int(math.sin(f * (math.pi / 2.0)) * 3) if state == "walk" else 0
                cx, cy = sz // 2, sz // 2 + 6
                
                # Attack lunging
                l_x, l_y = 0, 0
                if state == "attack":
                    dist = int(math.sin((f / num_frames) * math.pi) * 16)
                    if direction == DIR_DOWN: l_y = dist
                    elif direction == DIR_UP: l_y = -dist
                    elif direction == DIR_LEFT: l_x = -dist
                    elif direction == DIR_RIGHT: l_x = dist
                
                cx += l_x
                cy += l_y

                # Large Feet
                pygame.draw.rect(surf, c_armor, (cx - 12, cy + 18 - bounce, 8, 8), border_radius=2)
                pygame.draw.rect(surf, c_armor, (cx + 4, cy + 18 - bounce, 8, 8), border_radius=2)
                
                # Legs
                pygame.draw.rect(surf, c_armor, (cx - 10, cy + 8 - bounce, 20, 10))
                pygame.draw.line(surf, c_trim, (cx - 10, cy + 10 - bounce), (cx + 10, cy + 10 - bounce), 2)
                
                # Heavy Torso
                pygame.draw.rect(surf, c_armor, (cx - 16, cy - 14 - bounce, 32, 22), border_radius=4)
                pygame.draw.rect(surf, c_trim, (cx - 12, cy - 8 - bounce, 24, 6), border_radius=2) # Chest plate glow
                
                # Massive Shoulders (Pauldrons)
                pygame.draw.rect(surf, c_armor, (cx - 22, cy - 16 - bounce, 8, 10), border_radius=2)
                pygame.draw.rect(surf, c_armor, (cx + 14, cy - 16 - bounce, 8, 10), border_radius=2)
                
                # Armored Head
                pygame.draw.circle(surf, c_armor, (cx, cy - 24 - bounce), 10)
                # Glowing red visor slit
                if direction != DIR_UP:
                    pygame.draw.rect(surf, COLOR_RED, (cx - 6, cy - 26 - bounce, 12, 3))
                    
                # Curved Horns
                if direction == DIR_DOWN:
                    pygame.draw.polygon(surf, c_horns, [(cx - 9, cy - 30 - bounce), (cx - 14, cy - 38 - bounce), (cx - 5, cy - 32 - bounce)])
                    pygame.draw.polygon(surf, c_horns, [(cx + 9, cy - 30 - bounce), (cx + 14, cy - 38 - bounce), (cx + 5, cy - 32 - bounce)])
                elif direction == DIR_UP:
                    pygame.draw.polygon(surf, c_horns, [(cx - 8, cy - 30 - bounce), (cx - 12, cy - 40 - bounce), (cx - 4, cy - 32 - bounce)])
                    pygame.draw.polygon(surf, c_horns, [(cx + 8, cy - 30 - bounce), (cx + 12, cy - 40 - bounce), (cx + 4, cy - 32 - bounce)])
                elif direction == DIR_LEFT:
                    pygame.draw.polygon(surf, c_horns, [(cx - 6, cy - 32 - bounce), (cx - 16, cy - 38 - bounce), (cx, cy - 28 - bounce)])
                elif direction == DIR_RIGHT:
                    pygame.draw.polygon(surf, c_horns, [(cx + 6, cy - 32 - bounce), (cx + 16, cy - 38 - bounce), (cx, cy - 28 - bounce)])

                # Massive Fire Greatsword
                if state == "attack":
                    prog = f / num_frames
                    angle = -60 + prog * 180
                    rad = math.radians(angle)
                    s_len = 32
                    
                    if direction == DIR_DOWN:
                        wx, wy = int(math.sin(rad) * s_len), int(math.cos(rad) * s_len)
                        pygame.draw.line(surf, c_sword, (cx + 12, cy), (cx + 12 + wx, cy + wy), 5)
                    elif direction == DIR_UP:
                        wx, wy = int(math.sin(rad) * s_len), -int(math.cos(rad) * s_len)
                        pygame.draw.line(surf, c_sword, (cx - 12, cy - 16), (cx - 12 + wx, cy - 16 + wy), 5)
                    elif direction == DIR_LEFT:
                        wx, wy = -int(math.cos(rad) * s_len), int(math.sin(rad) * s_len)
                        pygame.draw.line(surf, c_sword, (cx - 16, cy), (cx - 16 + wx, cy + wy), 5)
                    elif direction == DIR_RIGHT:
                        wx, wy = int(math.cos(rad) * s_len), int(math.sin(rad) * s_len)
                        pygame.draw.line(surf, c_sword, (cx + 16, cy), (cx + 16 + wx, cy + wy), 5)
                else:
                    # Weapon held vertically
                    pygame.draw.line(surf, c_sword, (cx + 20, cy + 10 - bounce), (cx + 20, cy - 24 - bounce), 4)
                    pygame.draw.line(surf, (100, 60, 20), (cx + 20, cy + 10 - bounce), (cx + 20, cy + 16 - bounce), 3) # hilt

                if state == "hurt":
                    surf.fill((255, 100, 100, 150), special_flags=pygame.BLEND_RGBA_MULT)
                elif state == "dead":
                    dead_surf = pygame.transform.rotate(surf, 90)
                    surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
                    # Fade out dead boss
                    dead_surf.fill((100, 50, 50, int(255 * (1.0 - (f / num_frames)))), special_flags=pygame.BLEND_RGBA_MULT)
                    surf.blit(dead_surf, (0, 12))
                    
                frames_list.append(_create_outline(surf))
            entity_assets[name][state][direction] = frames_list
