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
        
        # Load procedural icon asset
        self.icon = self._get_procedural_icon()

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
        "description": "Unrefined iron nuggets mined from deep cavern rocks."
    },
    "Oak Wood": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Sturdy timber cut from prime forest trees."
    },
    "Timber": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Sturdy wood timber gathered from forest trees, used in crafting & building."
    },
    "Beast Leather": {
        "item_type": ITEM_MATERIAL,
        "rarity": RARITY_COMMON,
        "max_stack": 99,
        "stats": {},
        "description": "Tanned hide harvested from forest wolves and beasts."
    },
    
    # Rare Artifacts
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
    }
}

def create_item(name: str, quantity: int = 1) -> Union[Item, None]:
    """Factory function that creates an Item instance from the database templates."""
    template = ITEM_DATABASE.get(name)
    if template:
        # Create a new copy
        return Item(
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
    print(f"Warning: Item templates for '{name}' was not found.")
    return None
