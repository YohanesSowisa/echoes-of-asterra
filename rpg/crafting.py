"""
Echoes of Asterra - Crafting System
Defines recipes, required materials, and coordinates the assembly of items.
"""
from typing import Dict, List, Tuple, Any
from rpg.items import create_item
from rpg.inventory import Inventory

# Struct representing a Recipe: result_name -> (ingredient_dict, quantity, min_facility_level)
CRAFTING_RECIPES: Dict[str, Tuple[Dict[str, int], int, int]] = {
    "Steel Blade": ({"Iron Ore": 4, "Timber": 2}, 1, 1),
    "Wooden Shield": ({"Timber": 4}, 1, 1),
    "Iron Aegis": ({"Iron Ore": 6, "Timber": 2}, 1, 2),
    "Iron Helmet": ({"Iron Ore": 5}, 1, 1),
    "Leather Chest": ({"Beast Leather": 5}, 1, 1),
    "Leather Boots": ({"Beast Leather": 3}, 1, 1),
    "Red Potion": ({"Forest Apple": 2}, 1, 1),
    "Blue Potion": ({"Forest Apple": 1, "Beast Leather": 1}, 1, 2),
    "Asterra Sword": ({"Iron Ore": 10, "Beast Leather": 5, "Timber": 5}, 1, 3),
    "Dragon Horn Helmet": ({"Iron Ore": 8, "Beast Leather": 4}, 1, 3),
    "Rune of Fire": ({"Iron Ore": 2, "Red Potion": 1}, 1, 1),
    "Rune of Vitality": ({"Beast Leather": 2, "Forest Apple": 2}, 1, 1),
    "Rune of Precision": ({"Iron Ore": 3}, 1, 2),
    "Rune of Shielding": ({"Timber": 3, "Iron Ore": 1}, 1, 1),
}

class CraftingSystem:
    """
    Validates material counts and processes the creation, socketing, and disenchanting of items.
    """
    @staticmethod
    def get_recipes_list() -> List[str]:
        """Returns a list of all craftable item names."""
        return list(CRAFTING_RECIPES.keys())

    @staticmethod
    def can_craft(recipe_name: str, inventory: Inventory, facility_level: int = 1) -> bool:
        """
        Returns True if the inventory has enough ingredients to craft the item,
        facility meets min level, and there is room in the inventory.
        """
        recipe = CRAFTING_RECIPES.get(recipe_name)
        if not recipe:
            return False

        ingredients, qty, min_lvl = recipe
        if facility_level < min_lvl:
            return False

        # Verify ingredients
        for item_name, req_qty in ingredients.items():
            if not inventory.has_item(item_name, req_qty):
                return False

        # Check space in inventory
        temp_item = create_item(recipe_name, qty)
        if temp_item is None:
            return False

        has_space = False
        for slot in inventory.slots:
            if slot is None:
                has_space = True
                break
            if slot.name == recipe_name and slot.quantity + qty <= slot.max_stack:
                has_space = True
                break

        return has_space

    @staticmethod
    def craft(recipe_name: str, inventory: Inventory, facility_level: int = 1) -> bool:
        """
        Crafts the item. Consumes ingredients and adds the result to the inventory.
        Returns True if crafting succeeded, False otherwise.
        """
        if not CraftingSystem.can_craft(recipe_name, inventory, facility_level):
            return False

        recipe = CRAFTING_RECIPES[recipe_name]
        ingredients, qty, _ = recipe

        # Consume ingredients
        for item_name, req_qty in ingredients.items():
            inventory.remove_item(item_name, req_qty)

        # Add crafted item
        result_item = create_item(recipe_name, qty)
        if result_item:
            inventory.add_item(result_item)
            return True

        return False

    @staticmethod
    def socket_rune(target_item: Any, rune_name: str, inventory: Inventory) -> bool:
        """Sockets a rune item into an open socket of target_item, granting stat bonuses."""
        from rpg.items import RUNE_DATABASE
        if not target_item or len(target_item.socketed_runes) >= target_item.sockets:
            return False

        if not inventory.has_item(rune_name, 1):
            return False

        rune_info = RUNE_DATABASE.get(rune_name)
        if not rune_info:
            return False

        if inventory.remove_item(rune_name, 1):
            target_item.add_socket_rune(rune_name)
            stat_name = rune_info["stat"]
            stat_val = rune_info["value"]
            curr = target_item.stats.get(stat_name, 0)
            target_item.stats[stat_name] = curr + stat_val
            return True
        return False

    @staticmethod
    def disenchant_equipment(target_item: Any, inventory: Inventory) -> bool:
        """Disenchants unwanted equipment into raw materials based on item rarity."""
        from rpg.constants import (
            ITEM_WEAPON, ITEM_HELMET, ITEM_CHEST, ITEM_BOOTS, ITEM_SHIELD, ITEM_ACCESSORY,
            RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY
        )
        if not target_item or target_item.item_type not in [
            ITEM_WEAPON, ITEM_HELMET, ITEM_CHEST, ITEM_BOOTS, ITEM_SHIELD, ITEM_ACCESSORY
        ]:
            return False

        # Determine salvage yields
        if target_item.rarity in [RARITY_LEGENDARY, RARITY_EPIC]:
            yield_mat = "Iron Ore"
            yield_qty = 3
        elif target_item.rarity == RARITY_RARE:
            yield_mat = "Iron Ore"
            yield_qty = 2
        else:
            yield_mat = "Timber"
            yield_qty = 2

        # Remove item from inventory
        inventory.remove_item(target_item.name, 1)
        salvage = create_item(yield_mat, yield_qty)
        if salvage:
            inventory.add_item(salvage)
            return True
        return False
