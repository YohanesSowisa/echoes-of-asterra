"""
Echoes of Asterra - Items System
Defines item class structures, rarities, stat modifiers, and an item database factory.
"""
import pygame
from typing import Dict, Any, Union
from rpg.constants import (
    ITEM_WEAPON, ITEM_HELMET, ITEM_CHEST, ITEM_BOOTS, ITEM_SHIELD,
    ITEM_ACCESSORY, ITEM_POTION, ITEM_FOOD, ITEM_QUEST, ITEM_MATERIAL, ITEM_ARTIFACT,
    RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY,
    WEAPON_SWORD, WEAPON_AXE, WEAPON_HAMMER, WEAPON_SPEAR, WEAPON_DAGGER,
    ELEMENT_NONE, ELEMENT_FIRE, ELEMENT_ICE, ELEMENT_LIGHTNING
)
from rpg.animation import item_assets

class Item:
    """
    Representation of an item in the player's inventory or world.
    Tracks item quantity, stats, type, rarity, weapon class, element, and icon assets.
    """
    def __init__(
        self,
        name: str,
        item_type: str,
        rarity: str = RARITY_COMMON,
        quantity: int = 1,
        max_stack: int = 99,
        stats: Dict[str, int] = None,
        description: str = "",
        weapon_class: str = WEAPON_SWORD,
        element: str = ELEMENT_NONE
    ) -> None:
        self.name = name
        self.item_type = item_type
        self.rarity = rarity
        self.quantity = quantity
        self.max_stack = max_stack
        self.stats = stats if stats is not None else {}
        self.description = description
        self.weapon_class = weapon_class
        self.element = element

        # --- ARPG LOOT AFFIXES & SOCKET SYSTEM ---
        self.sockets: int = 0
        self.socketed_runes: list = []  # list of rune item names
        self.affixes: list = []  # list of dicts: {"type": "prefix"/"suffix", "name": str, "stat": str, "value": int/float}

        # Load procedural icon asset
        self.icon = self._get_procedural_icon()

    def add_socket_rune(self, rune_name: str) -> bool:
        """Inserts a socket rune into an available socket."""
        if len(self.socketed_runes) < self.sockets:
            self.socketed_runes.append(rune_name)
            return True
        return False

    def get_affix_display_name(self) -> str:
        """Constructs ARPG name (e.g. 'Flaming Steel Blade of Precision')."""
        prefix_str = " ".join([a["name"] for a in self.affixes if a["type"] == "prefix"])
        suffix_str = " ".join([a["name"] for a in self.affixes if a["type"] == "suffix"])
        parts = []
        if prefix_str:
            parts.append(prefix_str)
        parts.append(self.name)
        if suffix_str:
            parts.append(f"of {suffix_str}")
        return " ".join(parts)

    def _get_procedural_icon(self) -> pygame.Surface:
        """Retrieves procedural icon matching this item category."""
        icon_surf = None
        # 1. Exact Item Name Matches
        if "Wooden Shield" in self.name:
            icon_surf = item_assets.get("shield_wooden")
        elif "Iron Aegis" in self.name:
            icon_surf = item_assets.get("shield_iron")
        elif "Oak Wood" in self.name:
            icon_surf = item_assets.get("log_oak")
        elif "Timber" in self.name or "Plank" in self.name:
            icon_surf = item_assets.get("material_wood")
        elif "Iron Ore" in self.name:
            icon_surf = item_assets.get("material_iron")
        elif "Beast Leather" in self.name:
            icon_surf = item_assets.get("material_leather")
        elif "Stone" in self.name or "Rock" in self.name:
            icon_surf = item_assets.get("material_stone")
        elif "Red Potion" in self.name:
            icon_surf = item_assets.get("potion_red")
        elif "Blue Potion" in self.name:
            icon_surf = item_assets.get("potion_blue")
        elif "Apple" in self.name:
            icon_surf = item_assets.get("apple")
        elif "Bread" in self.name:
            icon_surf = item_assets.get("food")
        elif "Gold Coins" in self.name or "Gold Coin" in self.name:
            icon_surf = item_assets.get("gold_coins")
        elif "Amulet" in self.name:
            icon_surf = item_assets.get("amulet_glow")
        elif "Dungeon Key" in self.name or "Key" in self.name:
            icon_surf = item_assets.get("key_dungeon")
        elif "Scroll" in self.name:
            icon_surf = item_assets.get("quest")
        elif "Asterra Heart" in self.name or "Ruby Heart" in self.name:
            icon_surf = item_assets.get("artifact")

        # 2. Check weapon class subclasses
        if icon_surf is None and self.item_type == ITEM_WEAPON:
            wc = getattr(self, "weapon_class", "sword")
            if f"weapon_{wc}" in item_assets:
                icon_surf = item_assets[f"weapon_{wc}"]
            else:
                icon_surf = item_assets.get("weapon")

        # 3. Fall back to item type asset
        if icon_surf is None:
            icon_surf = item_assets.get(self.item_type)

        # 4. Guarantee non-None Surface fallback for test safety
        if icon_surf is None:
            icon_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
            icon_surf.fill((220, 180, 50, 200))

        return icon_surf




    def copy(self) -> 'Item':
        """Creates a clone of this item (useful for copying template objects)."""
        return Item(
            name=self.name,
            item_type=self.item_type,
            rarity=self.rarity,
            quantity=self.quantity,
            max_stack=self.max_stack,
            stats=self.stats.copy(),
            description=self.description,
            weapon_class=self.weapon_class,
            element=self.element
        )

# Item templates database
ITEM_DATABASE: Dict[str, Dict[str, Any]] = {
    # Weapons - Swords
    "Rusty Sword": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_SWORD,
        "element": ELEMENT_NONE,
        "rarity": RARITY_COMMON,
        "max_stack": 1,
        "stats": {"atk": 4},
        "description": "A basic, slightly rusty metal sword."
    },
    "Steel Blade": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_SWORD,
        "element": ELEMENT_NONE,
        "rarity": RARITY_RARE,
        "max_stack": 1,
        "stats": {"atk": 12, "crit": 5},
        "description": "A sharp, well-balanced steel broadsword."
    },
    "Asterra Sword": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_SWORD,
        "element": ELEMENT_LIGHTNING,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"atk": 25, "magic": 10, "crit": 12},
        "description": "A mythical glowing blade forged in Asterra's core."
    },
    "Flame Blade": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_SWORD,
        "element": ELEMENT_FIRE,
        "rarity": RARITY_RARE,
        "max_stack": 1,
        "stats": {"atk": 10, "magic": 5},
        "description": "An enchanted blade glowing with eternal flame."
    },
    "Frost Edge": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_SWORD,
        "element": ELEMENT_ICE,
        "rarity": RARITY_RARE,
        "max_stack": 1,
        "stats": {"atk": 9, "magic": 6},
        "description": "A frozen longsword that chills targets on contact."
    },

    # Weapons - Axes
    "Iron Axe": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_AXE,
        "element": ELEMENT_NONE,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 1,
        "stats": {"atk": 9},
        "description": "Heavy iron cleaver that pierces through armor."
    },

    # Weapons - Hammers
    "War Hammer": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_HAMMER,
        "element": ELEMENT_NONE,
        "rarity": RARITY_RARE,
        "max_stack": 1,
        "stats": {"atk": 14, "speed": -1},
        "description": "Massive battle hammer that stuns targets with crushing blows."
    },

    # Weapons - Spears
    "Hunters Spear": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_SPEAR,
        "element": ELEMENT_NONE,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 1,
        "stats": {"atk": 8, "crit": 4},
        "description": "Long thrusting polearm with extended strike reach."
    },

    # Weapons - Daggers
    "Shadow Dagger": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_DAGGER,
        "element": ELEMENT_NONE,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"atk": 7, "crit": 15, "speed": 1},
        "description": "Light, rapid assassin dagger capable of swift 4-hit combos."
    },

    # Primordial Pact-Infused Relic Weapons
    "Voidbrand Scythe": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_SPEAR,
        "element": ELEMENT_NONE,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"atk": 18, "crit": 12, "reach": 1.5},
        "description": "Primordial scythe infused with abyssal void energy. Extended reach and void pulse hits."
    },
    "Titan Cragcleaver": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_AXE,
        "element": ELEMENT_NONE,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"atk": 22, "def": 4, "speed": -1},
        "description": "Colossal granite battleaxe forged from Asterra bedrock. Crushes enemy armor on impact."
    },
    "Sunfire Morningstar": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_HAMMER,
        "element": ELEMENT_FIRE,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"atk": 16, "hp": 20, "magic": 10},
        "description": "Radiant solar morningstar burning with celestial dawnfire. Illuminates darkness on every strike."
    },
    
    # Shields
    "Wooden Shield": {
        "item_type": ITEM_SHIELD,
        "rarity": RARITY_COMMON,
        "max_stack": 1,
        "stats": {"def": 2},
        "description": "A simple wooden shield made of planks."
    },
    "Iron Aegis": {
        "item_type": ITEM_SHIELD,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"def": 10, "hp": 15},
        "description": "A heavy reinforced iron buckler that deflects most blows."
    },

    # Armor sets
    "Iron Helmet": {
        "item_type": ITEM_HELMET,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 1,
        "stats": {"def": 3},
        "description": "A heavy metal helmet offering decent head protection."
    },
    "Dragon Horn Helmet": {
        "item_type": ITEM_HELMET,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"def": 8, "atk": 4, "hp": 25},
        "description": "Forged from dragon skin and horns."
    },
    "Leather Chest": {
        "item_type": ITEM_CHEST,
        "rarity": RARITY_COMMON,
        "max_stack": 1,
        "stats": {"def": 2, "speed": 1},
        "description": "A light chestplate crafted from tanned hide."
    },
    "Iron Chestplate": {
        "item_type": ITEM_CHEST,
        "rarity": RARITY_RARE,
        "max_stack": 1,
        "stats": {"def": 8, "speed": -1},
        "description": "Polished steel plates offering heavy chest defense."
    },
    "Obsidian Mail": {
        "item_type": ITEM_CHEST,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"def": 18, "hp": 40, "magic": 5},
        "description": "Sturdy mail crafted from dark crystalline volcanic glass."
    },
    "Leather Boots": {
        "item_type": ITEM_BOOTS,
        "rarity": RARITY_COMMON,
        "max_stack": 1,
        "stats": {"def": 1, "speed": 2},
        "description": "Soft leather shoes that improve movement speed."
    },
    "Greaves of Speed": {
        "item_type": ITEM_BOOTS,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"def": 4, "speed": 6},
        "description": "Enchanted winged footwear that lets you move like wind."
    },

    # Accessories
    "Glow Amulet": {
        "item_type": ITEM_ACCESSORY,
        "rarity": RARITY_RARE,
        "max_stack": 1,
        "stats": {"magic": 8, "mana": 20},
        "description": "A magical talisman emitting a faint warm glow."
    },

    # Potions & Consumables
    "Red Potion": {
        "item_type": ITEM_POTION,
        "rarity": RARITY_COMMON,
        "max_stack": 10,
        "stats": {"heal_hp": 40},
        "description": "A glass vial containing sweet healing nectar."
    },
    "Blue Potion": {
        "item_type": ITEM_POTION,
        "rarity": RARITY_COMMON,
        "max_stack": 10,
        "stats": {"heal_mp": 25},
        "description": "A glass vial of liquid stardust that restores mana."
    },
    "Baked Bread": {
        "item_type": ITEM_FOOD,
        "rarity": RARITY_COMMON,
        "max_stack": 10,
        "stats": {"heal_hp": 15, "heal_stam": 30},
        "description": "Warm, fresh bread baked in a village stone oven."
    },
    "Forest Apple": {
        "item_type": ITEM_FOOD,
        "rarity": RARITY_COMMON,
        "max_stack": 10,
        "stats": {"heal_hp": 8, "heal_stam": 10},
        "description": "A crisp, red apple harvested from wild forest trees."
    },

    # Materials
    "Gold Coins": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 9999,
        "stats": {},
        "description": "A shiny pouch of Asterra gold currency."
    },
    "Iron Ore": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Unrefined iron nuggets found in cavern chests, mined rocks, and dropped by armored foes."
    },
    "iron_ore": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Unrefined iron nuggets found in cavern chests, mined rocks, and dropped by armored foes."
    },
    "Oak Wood": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Sturdy timber gathered from forest wolves, beasts, and woodland supply crates."
    },
    "oak_wood": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Sturdy timber gathered from forest wolves, beasts, and woodland supply crates."
    },
    "Timber": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Sturdy wood timber carried by forest beasts, used in crafting & infrastructure building."
    },
    "Beast Leather": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Tanned hide harvested from forest wolves and beasts."
    },
    "herb": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Wild medicinal herbs gathered from forest undergrowth."
    },
    "Herb": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Wild medicinal herbs gathered from forest undergrowth."
    },
    "wolf_pelt": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Warm pelt from predatory wolves used in crafting and trading."
    },
    "Wolf Pelt": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Warm pelt from predatory wolves used in crafting and trading."
    },
    "starlight_crystal": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_EPIC,
        "max_stack": 20,
        "stats": {"magic": 8},
        "description": "Luminescent crystal harvested from ancient ruins."
    },
    "Starlight Crystal": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_EPIC,
        "max_stack": 20,
        "stats": {"magic": 8},
        "description": "Luminescent crystal harvested from ancient ruins."
    },
    "Granite Stone": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Dense granite stone mined from Asterra bedrock, used in dungeon fortifications and masonry."
    },
    "granite_stone": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Dense granite stone mined from Asterra bedrock, used in dungeon fortifications and masonry."
    },
    "Stone": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Sturdy quarried stone used for crafting and dungeon architectural construction."
    },
    "stone": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Sturdy quarried stone used for crafting and dungeon architectural construction."
    },
    "Luminescent Spore": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 50,
        "stats": {"magic": 3},
        "description": "Bioluminescent fungal spores harvested from the Sunken Mire and deep crypts."
    },
    "luminescent_spore": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 50,
        "stats": {"magic": 3},
        "description": "Bioluminescent fungal spores harvested from the Sunken Mire and deep crypts."
    },
    "festive_honey_bread": {
        "item_type": ITEM_FOOD,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 10,
        "stats": {"heal_hp": 35, "heal_stam": 50},
        "description": "Sweet festival bread baked with Asterra wild honey."
    },
    "Festive Honey Bread": {
        "item_type": ITEM_FOOD,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 10,
        "stats": {"heal_hp": 35, "heal_stam": 50},
        "description": "Sweet festival bread baked with Asterra wild honey."
    },
    "Beast Capture Net": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 10,
        "stats": {},
        "description": "Heavy weighted mesh net crafted to ensnare weakened monsters (<20% HP) for dungeon domestication."
    },
    "beast_capture_net": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 10,
        "stats": {},
        "description": "Heavy weighted mesh net crafted to ensnare weakened monsters (<20% HP) for dungeon domestication."
    },
    
    # Rare Artifacts & Primordial Materials
    "Chrono-Weaver Hourglass": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"magic": 10},
        "description": "Mythical sands of time enclosed in celestial brass. Activating rewinds the world up to 3 days into the past."
    },
    "chrono_weaver_hourglass": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"magic": 10},
        "description": "Mythical sands of time enclosed in celestial brass. Activating rewinds the world up to 3 days into the past."
    },
    "Aeon Core": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 5,
        "stats": {"magic": 15, "defense": 15},
        "description": "Primordial pulsating core of stabilized temporal essence harvested from the defeated Aeon Sentinel."
    },
    "aeon_core": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 5,
        "stats": {"magic": 15, "defense": 15},
        "description": "Primordial pulsating core of stabilized temporal essence harvested from the defeated Aeon Sentinel."
    },
    "Ancient Relic": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 20,
        "stats": {"magic": 5},
        "description": "Ancient glowing artifact relic retrieved from Asterra's primordial crypts."
    },
    "ancient_relic": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 20,
        "stats": {"magic": 5},
        "description": "Ancient glowing artifact relic retrieved from Asterra's primordial crypts."
    },
    "Topaz": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 20,
        "stats": {"magic": 6},
        "description": "Golden sun gemstone shimmering with radiant solar energy."
    },
    "topaz": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 20,
        "stats": {"magic": 6},
        "description": "Golden sun gemstone shimmering with radiant solar energy."
    },
    "Silver Ore": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Precious lustrous ore mined from deep caverns."
    },
    "silver_ore": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Precious lustrous ore mined from deep caverns."
    },
    "Mire Reed": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Fibrous wetland reeds harvested from the Sunken Mire."
    },
    "mire_reed": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Fibrous wetland reeds harvested from the Sunken Mire."
    },
    "Leech Mucus": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 99,
        "stats": {"magic": 3},
        "description": "Viscous secretions from bog leeches used in alchemy."
    },
    "leech_mucus": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 99,
        "stats": {"magic": 3},
        "description": "Viscous secretions from bog leeches used in alchemy."
    },
    "Sunken Relic": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_EPIC,
        "max_stack": 20,
        "stats": {"magic": 10},
        "description": "Waterlogged ancient relic recovered from the deep Sunken Mire."
    },
    "sunken_relic": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_EPIC,
        "max_stack": 20,
        "stats": {"magic": 10},
        "description": "Waterlogged ancient relic recovered from the deep Sunken Mire."
    },
    "Bog Blossom": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Rare purple orchid blooming in marsh peat. Petals absorb ambient arcane moisture."
    },
    "bog_blossom": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Rare purple orchid blooming in marsh peat. Petals absorb ambient arcane moisture."
    },
    "Glow Lotus": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 99,
        "stats": {"magic": 4},
        "description": "Bioluminescent aquatic flower floating in low-tide pools. Emits a steady cyan radiance."
    },
    "glow_lotus": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 99,
        "stats": {"magic": 4},
        "description": "Bioluminescent aquatic flower floating in low-tide pools. Emits a steady cyan radiance."
    },
    "Luminescent Spore": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 99,
        "stats": {"magic": 5},
        "description": "Glowing mire fungal spores harvested from ancient bogwood."
    },
    "luminescent_spore": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 99,
        "stats": {"magic": 5},
        "description": "Glowing mire fungal spores harvested from ancient bogwood."
    },
    "Waterstrider Elixir": {
        "item_type": ITEM_POTION,
        "rarity": RARITY_RARE,
        "max_stack": 10,
        "stats": {"waterstrider_dur": 180.0},
        "description": "Grants Waterstrider Blessing for 180s (100% speed mobility in deep swamp water and mud)."
    },
    "waterstrider_elixir": {
        "item_type": ITEM_POTION,
        "rarity": RARITY_RARE,
        "max_stack": 10,
        "stats": {"waterstrider_dur": 180.0},
        "description": "Grants Waterstrider Blessing for 180s (100% speed mobility in deep swamp water and mud)."
    },
    "Mire Cleansing Draught": {
        "item_type": ITEM_POTION,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 10,
        "stats": {"cleansing_draught_dur": 240.0},
        "description": "Instantly cures poison and grants 240s immunity to swamp toxins and marsh miasma."
    },
    "mire_cleansing_draught": {
        "item_type": ITEM_POTION,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 10,
        "stats": {"cleansing_draught_dur": 240.0},
        "description": "Instantly cures poison and grants 240s immunity to swamp toxins and marsh miasma."
    },
    "Leyline Surge Tonic": {
        "item_type": ITEM_POTION,
        "rarity": RARITY_EPIC,
        "max_stack": 10,
        "stats": {"leyline_surge_dur": 120.0},
        "description": "Consumes Leyline resonance to grant +25% Magic Damage and 3x Mana Regeneration for 120s."
    },
    "leyline_surge_tonic": {
        "item_type": ITEM_POTION,
        "rarity": RARITY_EPIC,
        "max_stack": 10,
        "stats": {"leyline_surge_dur": 120.0},
        "description": "Consumes Leyline resonance to grant +25% Magic Damage and 3x Mana Regeneration for 120s."
    },

    # Phase 3: Submerged Temple Boss Drops & Leyline Resonant Equipment
    "Tidal Scale": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_EPIC,
        "max_stack": 20,
        "stats": {"def": 2},
        "description": "Iridescent armored leviathan scale that repels both corrosive acid and raging tides."
    },
    "tidal_scale": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_EPIC,
        "max_stack": 20,
        "stats": {"def": 2},
        "description": "Iridescent armored leviathan scale that repels both corrosive acid and raging tides."
    },
    "Conduit Core": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 10,
        "stats": {"magic": 15},
        "description": "Vibrant pulsing crystal core harvested from an ancient Leyline heart."
    },
    "conduit_core": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 10,
        "stats": {"magic": 15},
        "description": "Vibrant pulsing crystal core harvested from an ancient Leyline heart."
    },
    "Leviathan Scale Mail": {
        "item_type": ITEM_CHEST,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"def": 14, "max_hp": 35},
        "description": "Heavy plate mail forged from reinforced tidal scales. Grants immense defense and resilience."
    },
    "leviathan_scale_mail": {
        "item_type": ITEM_CHEST,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"def": 14, "max_hp": 35},
        "description": "Heavy plate mail forged from reinforced tidal scales. Grants immense defense and resilience."
    },
    "Tidecaller Trident": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_SPEAR,
        "element": ELEMENT_NONE,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"atk": 20, "magic": 12, "reach": 1.6},
        "description": "Ancient relic spear resonating with aquatic Leyline force. Expands reach and summons tidal shockwaves."
    },
    "tidecaller_trident": {
        "item_type": ITEM_WEAPON,
        "weapon_class": WEAPON_SPEAR,
        "element": ELEMENT_NONE,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"atk": 20, "magic": 12, "reach": 1.6},
        "description": "Ancient relic spear resonating with aquatic Leyline force. Expands reach and summons tidal shockwaves."
    },
    "Conduit Ring of Leylines": {
        "item_type": ITEM_ACCESSORY,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"mana": 30, "magic": 10, "cooldown_reduction": 0.15},
        "description": "Ring inscribed with Leyline glyphs. Expands maximum Mana and accelerates ability cooldowns."
    },
    "conduit_ring_of_leylines": {
        "item_type": ITEM_ACCESSORY,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"mana": 30, "magic": 10, "cooldown_reduction": 0.15},
        "description": "Ring inscribed with Leyline glyphs. Expands maximum Mana and accelerates ability cooldowns."
    },
    "Asterra Heart": {
        "item_type": ITEM_ARTIFACT,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 5,
        "stats": {"magic": 15},
        "description": "A pulsating ruby crystal carrying the core magic of Asterra."
    },
    
    # Quest Items
    "Ancient Scroll": {
        "item_type": ITEM_QUEST,
        "rarity": RARITY_RARE,
        "max_stack": 1,
        "stats": {},
        "description": "A dusty scroll written in an ancient, forgotten language."
    },
    "Dungeon Key": {
        "item_type": ITEM_QUEST,
        "rarity": RARITY_EPIC,
        "max_stack": 5,
        "stats": {},
        "description": "A heavy copper key inscribed with skull markings."
    },
    "Syndicate Cipher Fragment #1": {
        "item_type": ITEM_QUEST,
        "rarity": RARITY_RARE,
        "max_stack": 1,
        "stats": {},
        "description": "An intercepted encrypted codex fragment detailing the Shadow Syndicate's Day 30 coup infiltration."
    },
    "syndicate_cipher_fragment_1": {
        "item_type": ITEM_QUEST,
        "rarity": RARITY_RARE,
        "max_stack": 1,
        "stats": {},
        "description": "An intercepted encrypted codex fragment detailing the Shadow Syndicate's Day 30 coup infiltration."
    },
    "Syndicate Cipher Fragment #2": {
        "item_type": ITEM_QUEST,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {},
        "description": "Conclusive royal signet letter intercepted from Shadow Assassins detailing the Grand Usurper's inner coup circle."
    },
    "syndicate_cipher_fragment_2": {
        "item_type": ITEM_QUEST,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {},
        "description": "Conclusive royal signet letter intercepted from Shadow Assassins detailing the Grand Usurper's inner coup circle."
    },
    "Usurper's Royal Signet Ring": {
        "item_type": ITEM_ACCESSORY,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"atk": 12, "defense": 6, "magic": 10},
        "description": "Engraved sovereign ring recovered from Grand Inquisitor Vane. Radiates overwhelming authority and +15% boss damage."
    },
    "usurpers_royal_signet_ring": {
        "item_type": ITEM_ACCESSORY,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"atk": 12, "defense": 6, "magic": 10},
        "description": "Engraved sovereign ring recovered from Grand Inquisitor Vane. Radiates overwhelming authority and +15% boss damage."
    },
    "Crown of Shadows": {
        "item_type": ITEM_HELMET,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"defense": 10, "max_mana": 40},
        "description": "Diadem woven from pure obsidian void shadows. Grants +10 Defense, +40 Max MP, and 30% void resistance."
    },
    "crown_of_shadows": {
        "item_type": ITEM_HELMET,
        "rarity": RARITY_EPIC,
        "max_stack": 1,
        "stats": {"defense": 10, "max_mana": 40},
        "description": "Diadem woven from pure obsidian void shadows. Grants +10 Defense, +40 Max MP, and 30% void resistance."
    },
    "Shadow Residue": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 99,
        "stats": {"magic": 8},
        "description": "Purified psychic ectoplasm extracted after slaying a Shadow Parasite. Radiates calm void energy."
    },
    "shadow_residue": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 99,
        "stats": {"magic": 8},
        "description": "Purified psychic ectoplasm extracted after slaying a Shadow Parasite. Radiates calm void energy."
    },
    "Rune of Fire": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 20,
        "stats": {"atk": 5},
        "description": "An elemental rune that adds +5 Attack Power when socketed."
    },
    "Rune of Vitality": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 20,
        "stats": {"hp": 25},
        "description": "A life rune that adds +25 Max Health when socketed."
    },
    "Rune of Precision": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_RARE,
        "max_stack": 20,
        "stats": {"crit": 5},
        "description": "A sharp rune that adds +5% Crit Chance when socketed."
    },
    "Rune of Shielding": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_UNCOMMON,
        "max_stack": 20,
        "stats": {"def": 4},
        "description": "A protective rune that adds +4 Defense when socketed."
    }
}

# --- ARPG AFFIX & RUNE DEFINITIONS ---
PREFIX_TABLE = [
    {"name": "Heavy", "stat": "atk", "range": (2, 5), "type": "prefix"},
    {"name": "Vicious", "stat": "atk", "range": (5, 10), "type": "prefix"},
    {"name": "Sharp", "stat": "crit", "range": (3, 7), "type": "prefix"},
    {"name": "Fortified", "stat": "def", "range": (2, 4), "type": "prefix"},
    {"name": "Titan's", "stat": "hp", "range": (15, 35), "type": "prefix"},
    {"name": "Arcane", "stat": "magic", "range": (4, 9), "type": "prefix"},
    {"name": "Swift", "stat": "speed", "range": (0.2, 0.5), "type": "prefix"},
]

SUFFIX_TABLE = [
    {"name": "Strength", "stat": "atk", "range": (2, 6), "type": "suffix"},
    {"name": "Precision", "stat": "crit", "range": (4, 8), "type": "suffix"},
    {"name": "Protection", "stat": "def", "range": (2, 5), "type": "suffix"},
    {"name": "Vitality", "stat": "hp", "range": (10, 30), "type": "suffix"},
    {"name": "Haste", "stat": "speed", "range": (0.2, 0.4), "type": "suffix"},
    {"name": "Wisdom", "stat": "mana", "range": (15, 30), "type": "suffix"},
]

RUNE_DATABASE = {
    "Rune of Fire": {"stat": "atk", "value": 5, "desc": "+5 Attack Power"},
    "Rune of Vitality": {"stat": "hp", "value": 25, "desc": "+25 Max HP"},
    "Rune of Precision": {"stat": "crit", "value": 5, "desc": "+5% Crit Chance"},
    "Rune of Shielding": {"stat": "def", "value": 4, "desc": "+4 Defense"},
}

import random

def roll_affixes(item: Item, roll_chance: float = 0.4) -> None:
    """Randomly rolls rarity, affixes, and sockets on equipment items."""
    if item.item_type not in [ITEM_WEAPON, ITEM_HELMET, ITEM_CHEST, ITEM_BOOTS, ITEM_SHIELD, ITEM_ACCESSORY]:
        return

    # If item is already Legendary, preserve its rarity tier
    if item.rarity == RARITY_LEGENDARY:
        affix_count = 2
        item.sockets = 2
    else:
        # Roll rarity
        r = random.random()
        if r < 0.05:
            item.rarity = RARITY_LEGENDARY
            affix_count = 3
            item.sockets = random.choice([1, 2])
        elif r < 0.15:
            item.rarity = RARITY_EPIC
            affix_count = 2
            item.sockets = random.choice([1, 2])
        elif r < 0.35:
            item.rarity = RARITY_RARE
            affix_count = 2
            item.sockets = 1
        elif r < 0.60:
            item.rarity = RARITY_UNCOMMON
            affix_count = 1
            item.sockets = 0
        else:
            item.rarity = RARITY_COMMON
            affix_count = 0
            item.sockets = 0

    if affix_count == 0:
        return

    # Select prefixes and suffixes
    pools = []
    if affix_count >= 1:
        pools.append(random.choice(PREFIX_TABLE))
    if affix_count >= 2:
        pools.append(random.choice(SUFFIX_TABLE))
    if affix_count >= 3:
        # Pick another prefix or suffix
        pools.append(random.choice(PREFIX_TABLE + SUFFIX_TABLE))

    for template in pools:
        val = random.randint(template["range"][0], template["range"][1]) if isinstance(template["range"][0], int) else round(random.uniform(*template["range"]), 2)
        affix = {
            "name": template["name"],
            "type": template["type"],
            "stat": template["stat"],
            "value": val,
        }
        item.affixes.append(affix)
        # Add stat directly into item.stats
        curr = item.stats.get(template["stat"], 0)
        item.stats[template["stat"]] = curr + val


def create_item(name: str, quantity: int = 1, roll_equipment_affixes: bool = True) -> Union[Item, None]:
    """Factory function that creates an Item instance from the database templates."""
    template = ITEM_DATABASE.get(name)
    if template:
        item = Item(
            name=name,
            item_type=template["item_type"],
            rarity=template["rarity"],
            quantity=quantity,
            max_stack=template["max_stack"],
            stats=template["stats"].copy(),
            description=template["description"],
            weapon_class=template.get("weapon_class", WEAPON_SWORD),
            element=template.get("element", ELEMENT_NONE)
        )
        if roll_equipment_affixes and item.item_type in [ITEM_WEAPON, ITEM_HELMET, ITEM_CHEST, ITEM_BOOTS, ITEM_SHIELD, ITEM_ACCESSORY]:
            roll_affixes(item)
        return item
    print(f"Warning: Item templates for '{name}' was not found.")
    return None
