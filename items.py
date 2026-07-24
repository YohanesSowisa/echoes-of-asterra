"""
Echoes of Asterra - Items System
Defines item class structures, rarities, stat modifiers, and an item database factory.
"""
import pygame
from typing import Dict, Any, Union
from rpg.constants import (
    ITEM_WEAPON, ITEM_HELMET, ITEM_CHEST, ITEM_LEGS, ITEM_BOOTS, ITEM_SHIELD,
    ITEM_ACCESSORY, ITEM_POTION, ITEM_FOOD, ITEM_QUEST, ITEM_MATERIAL, ITEM_ARTIFACT,
    RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY
)
from rpg.animation import item_assets

class Item:
    """
    Representation of an item in the player's inventory or world.
    Tracks item quantity, stats, type, rarity, and icon assets.
    """
    def __init__(
        self,
        name: str,
        item_type: str,
        rarity: str = RARITY_COMMON,
        quantity: int = 1,
        max_stack: int = 99,
        stats: Dict[str, int] = None,
        description: str = ""
    ) -> None:
        self.name = name
        self.item_type = item_type
        self.rarity = rarity
        self.quantity = quantity
        self.max_stack = max_stack
        self.stats = stats if stats is not None else {}
        self.description = description
        
        # Load procedural icon asset
        self.icon = self._get_procedural_icon()

    def _get_procedural_icon(self) -> pygame.Surface:
        """Retrieves procedural icon matching this item category."""
        # Check specific names first, then fall back to item type
        if "Red Potion" in self.name:
            return item_assets.get("potion_red")
        elif "Blue Potion" in self.name:
            return item_assets.get("potion_blue")
        elif "Iron Ore" in self.name:
            return item_assets.get("material_iron")
        elif "Wood" in self.name or "Plank" in self.name:
            return item_assets.get("material_wood")
        elif "Heart" in self.name or "Amulet" in self.name:
            return item_assets.get("artifact")
        elif "Scroll" in self.name or "Key" in self.name:
            return item_assets.get("quest")
            
        return item_assets.get(self.item_type, pygame.Surface((32, 32), pygame.SRCALPHA))

    def copy(self) -> 'Item':
        """Creates a clone of this item (useful for copying template objects)."""
        return Item(
            name=self.name,
            item_type=self.item_type,
            rarity=self.rarity,
            quantity=self.quantity,
            max_stack=self.max_stack,
            stats=self.stats.copy(),
            description=self.description
        )

# Item templates database
ITEM_DATABASE: Dict[str, Dict[str, Any]] = {
    # Weapons
    "Rusty Sword": {
        "item_type": ITEM_WEAPON,
        "rarity": RARITY_COMMON,
        "max_stack": 1,
        "stats": {"atk": 4},
        "description": "A basic, slightly rusty metal sword."
    },
    "Steel Blade": {
        "item_type": ITEM_WEAPON,
        "rarity": RARITY_RARE,
        "max_stack": 1,
        "stats": {"atk": 12, "crit": 5},
        "description": "A sharp, well-balanced steel broadsword."
    },
    "Asterra Sword": {
        "item_type": ITEM_WEAPON,
        "rarity": RARITY_LEGENDARY,
        "max_stack": 1,
        "stats": {"atk": 25, "magic": 10, "crit": 12},
        "description": "A mythical glowing blade forged in Asterra's core."
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
            description=template["description"]
        )
    print(f"Warning: Item templates for '{name}' was not found.")
    return None
