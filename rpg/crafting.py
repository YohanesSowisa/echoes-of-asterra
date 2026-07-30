"""
Echoes of Asterra - Crafting System
Defines recipes, required materials, and coordinates the assembly of items.
"""
from typing import Dict, List, Tuple
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
}

class CraftingSystem:
    """
    Validates material counts and processes the creation of items.
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
