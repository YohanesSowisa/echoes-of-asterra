"""
Echoes of Asterra - Constants
Defines game-wide constants, colors, states, enums, and item types.
"""
from typing import Dict, Tuple

# Screen & Rendering
GAME_TITLE = "Echoes of Asterra"

# Color Palette (RGB)
COLOR_TRANSPARENT = (0, 0, 0, 0)
COLOR_BLACK = (10, 10, 15)
COLOR_WHITE = (245, 245, 250)
COLOR_GRAY = (100, 105, 115)
COLOR_DARK_GRAY = (40, 42, 50)
COLOR_LIGHT_GRAY = (180, 185, 195)

# Primary Colors
COLOR_RED = (220, 60, 60)
COLOR_GREEN = (60, 200, 80)
COLOR_BLUE = (60, 100, 230)
COLOR_YELLOW = (240, 200, 40)
COLOR_ORANGE = (230, 120, 30)
COLOR_PURPLE = (160, 60, 220)
COLOR_CYAN = (60, 210, 230)

# UI Elements
COLOR_UI_BG = (25, 27, 35, 230)      # Translucent dark menu bg
COLOR_UI_BORDER = (80, 85, 100)
COLOR_UI_TEXT = (230, 235, 240)
COLOR_UI_HIGHLIGHT = (200, 160, 40)
COLOR_UI_SHADOW = (5, 5, 10)

# Stats Bars
COLOR_BAR_HP = (210, 50, 50)
COLOR_BAR_MANA = (50, 120, 220)
COLOR_BAR_STAMINA = (70, 180, 70)
COLOR_BAR_EXP = (200, 60, 200)

# Rarity Colors
RARITY_COMMON = "Common"
RARITY_UNCOMMON = "Uncommon"
RARITY_RARE = "Rare"
RARITY_EPIC = "Epic"
RARITY_LEGENDARY = "Legendary"

RARITY_COLORS: Dict[str, Tuple[int, int, int]] = {
    RARITY_COMMON: (200, 205, 210),
    RARITY_UNCOMMON: (30, 200, 80),
    RARITY_RARE: (30, 120, 240),
    RARITY_EPIC: (170, 50, 230),
    RARITY_LEGENDARY: (250, 150, 10)
}

# Game States
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"
STATE_VICTORY = "victory"
STATE_DIALOGUE = "dialogue"
STATE_SHOP = "shop"
STATE_SETTINGS = "settings"
STATE_TUTORIAL = "tutorial"

# Directions
DIR_DOWN = "down"
DIR_UP = "up"
DIR_LEFT = "left"
DIR_RIGHT = "right"

# Item Types
ITEM_WEAPON = "weapon"
ITEM_HELMET = "helmet"
ITEM_CHEST = "chest"
ITEM_LEGS = "legs"
ITEM_BOOTS = "boots"
ITEM_SHIELD = "shield"
ITEM_ACCESSORY = "accessory"
ITEM_POTION = "potion"
ITEM_FOOD = "food"
ITEM_QUEST = "quest_item"
ITEM_MATERIAL = "material"
ITEM_ARTIFACT = "rare_artifact"

# Quest Status
QUEST_NOT_STARTED = "not_started"
QUEST_ACTIVE = "active"
QUEST_COMPLETED = "completed"

# Skills
SKILL_SWORD_MASTERY = "Sword Mastery"
SKILL_FIREBALL = "Fireball"
SKILL_ICE_SPIKE = "Ice Spike"
SKILL_DASH = "Dash"
SKILL_HEALING = "Healing"
SKILL_SHIELD = "Magic Shield"
SKILL_LIGHTNING = "Lightning Strike"

# World Maps
MAP_VILLAGE = "village"
MAP_FOREST = "forest"
MAP_RUINS = "ruins"
MAP_CAVE = "cave"
MAP_LAKE = "lake"
MAP_MOUNTAIN = "mountain"
MAP_DUNGEON = "dungeon"
MAP_SECRET = "secret_area"
