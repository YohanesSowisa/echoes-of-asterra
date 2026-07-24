"""
Echoes of Asterra - Crafting System
Defines recipes, required materials, and coordinates the assembly of items.
"""
from typing import Dict, List, Tuple
from rpg.items import create_item
from rpg.inventory import Inventory

# Struct representing a Recipe: result_name -> (ingredient_dict, quantity)
CRAFTING_RECIPES: Dict[str, Tuple[Dict[str, int], int]] = {
    "Steel Blade": ({"Iron Ore": 4, "Timber": 2}, 1),
    "Wooden Shield": ({"Timber": 4}, 1),
    "Iron Aegis": ({"Iron Ore": 6, "Timber": 2}, 1),
    "Iron Helmet": ({"Iron Ore": 5}, 1),
    "Leather Chest": ({"Beast Leather": 5}, 1),
    "Leather Boots": ({"Beast Leather": 3}, 1),
    "Red Potion": ({"Forest Apple": 2}, 1),
    "Blue Potion": ({"Forest Apple": 1, "Beast Leather": 1}, 1),
    "Asterra Sword": ({"Iron Ore": 10, "Beast Leather": 5, "Timber": 5}, 1),
    "Dragon Horn Helmet": ({"Iron Ore": 8, "Beast Leather": 4}, 1)
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
    def can_craft(recipe_name: str, inventory: Inventory) -> bool:
        """
        Returns True if the inventory has enough ingredients to craft the item,
        and there is room in the inventory for the resulting item.
        """
        recipe = CRAFTING_RECIPES.get(recipe_name)
        if not recipe:
            return False
            
        ingredients, qty = recipe
        
        # Verify ingredients
        for item_name, req_qty in ingredients.items():
            if not inventory.has_item(item_name, req_qty):
                return False
                
        # Check space in inventory
        # If inventory is fully saturated and we can't stack, can_craft should return False
        temp_item = create_item(recipe_name, qty)
        if temp_item is None:
            return False
            
        # Simplistic space check: does an empty slot exist or can we stack it?
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
    def craft(recipe_name: str, inventory: Inventory) -> bool:
        """
        Crafts the item. Consumes ingredients and adds the result to the inventory.
        Returns True if crafting succeeded, False otherwise.
        """
        if not CraftingSystem.can_craft(recipe_name, inventory):
            return False
            
        recipe = CRAFTING_RECIPES[recipe_name]
        ingredients, qty = recipe
        
        # Consume ingredients
        for item_name, req_qty in ingredients.items():
            inventory.remove_item(item_name, req_qty)
            
        # Add crafted item
        result_item = create_item(recipe_name, qty)
        if result_item:
            inventory.add_item(result_item)
            return True
            
        return False
