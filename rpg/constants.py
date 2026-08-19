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
COLOR_GOLD = (255, 215, 0)
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
ITEM_ARMOR = "chest"
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
MAP_CRYPT = "crypt"  # Endless procedural dungeon entrance
MAP_SUNKEN_MIRE = "sunken_mire"  # Submerged wetland biome with dynamic tide cycles
MAP_SUBMERGED_TEMPLE = "submerged_temple"  # Ancient aquatic sanctum & boss chamber

# Tide Cycle Constants
TIDE_LOW = "low"
TIDE_RISING = "rising"
TIDE_HIGH = "high"
TIDE_FALLING = "falling"

# Mire Enemy & Boss Types
ENEMY_MIRE_LURKER = "mire_lurker"
ENEMY_BOG_LEECH = "bog_leech"
ENEMY_TEMPLE_GUARDIAN = "temple_guardian"
BOSS_MIRE_LEVIATHAN = "mire_leviathan"

# Seasons
SEASON_SPRING = "spring"
SEASON_SUMMER = "summer"
SEASON_AUTUMN = "autumn"
SEASON_WINTER = "winter"

# Factions
FACTION_KNIGHTS = "knights"
FACTION_MAGES = "mages"
FACTION_HUNTERS = "hunters"
FACTION_MERCHANTS = "merchants"
FACTION_BANDITS = "bandits"
FACTION_CULTISTS = "cultists"

# Weapon Classes
WEAPON_SWORD = "sword"
WEAPON_AXE = "axe"
WEAPON_HAMMER = "hammer"
WEAPON_SPEAR = "spear"
WEAPON_DAGGER = "dagger"

# Elements
ELEMENT_NONE = "none"
ELEMENT_FIRE = "fire"
ELEMENT_ICE = "ice"
ELEMENT_LIGHTNING = "lightning"
ELEMENT_WIND = "wind"
ELEMENT_POISON = "poison"

# World Event IDs
EVENT_VILLAGE_FESTIVAL = "village_festival"
EVENT_MERCHANT_CARAVAN = "merchant_caravan"
EVENT_BANDIT_INVASION = "bandit_invasion"
EVENT_BRIDGE_REBUILT = "bridge_rebuilt"
EVENT_FOREST_CORRUPTION = "forest_corruption"
EVENT_HARVEST_SEASON = "harvest_season"
EVENT_BLOOD_MOON = "blood_moon"
EVENT_BLESSING_ASTERRA = "blessing_of_asterra"
EVENT_GUARD_DRILL = "guard_drill"
EVENT_MANA_SURGE = "mana_surge"

# NPC Relationship Levels
REL_ENEMY = "enemy"
REL_STRANGER = "stranger"
REL_ACQUAINTANCE = "acquaintance"
REL_FRIEND = "friend"
REL_CLOSE_FRIEND = "close_friend"

# Dungeon Themes
DUNGEON_CAVE = "cave"
DUNGEON_TEMPLE = "temple"
DUNGEON_CRYPT = "crypt"
DUNGEON_ICE = "ice"
DUNGEON_VOLCANO = "volcano"

# Monster Keys
ENEMY_SPORE_HOST_WOLF = "spore_host_wolf"

