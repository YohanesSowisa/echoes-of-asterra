"""
Echoes of Asterra - Inventory System
Manages player inventory slots, item sorting, stack logic, drag-and-drop actions, and item usage.
"""
from typing import List, Optional, Any, Tuple
from rpg.items import Item
from rpg.constants import ITEM_POTION, ITEM_FOOD, ITEM_WEAPON, ITEM_SHIELD, ITEM_HELMET, ITEM_CHEST, ITEM_BOOTS, ITEM_ACCESSORY, ITEM_LEGS

class Inventory:
    """
    Grid inventory system. Tracks slots, stacking, sorting, dragging,
    and handles item usage / equip triggers.
    """
    def __init__(self, size: int = 24) -> None:
        self.size = size
        self.slots: List[Optional[Item]] = [None] * size
        
        # Drag and drop tracking
        self.dragged_slot_idx: Optional[int] = None
        self.dragged_item: Optional[Item] = None

        # Quick-use hotbar shortcut bindings (Keys 1..4 -> item_name)
        self.quick_slots: dict[int, Optional[str]] = {
            1: "Red Potion",
            2: "Blue Potion",
            3: "Baked Bread",
            4: "Forest Apple"
        }

    def assign_quick_slot(self, slot_num: int, item_obj_or_name: Any) -> bool:
        """
        Binds a usable/equipable item to quick-slot 1..4.
        Returns False if the item is a material or quest item that cannot be used.
        """
        if not (1 <= slot_num <= 4):
            return False

        if isinstance(item_obj_or_name, str):
            item_name = item_obj_or_name
        else:
            if hasattr(item_obj_or_name, "item_type") and item_obj_or_name.item_type in ["material", "quest"]:
                return False
            item_name = getattr(item_obj_or_name, "name", str(item_obj_or_name))

        self.quick_slots[slot_num] = item_name
        return True


    def use_quick_slot(self, slot_num: int, player: Any) -> bool:
        """Finds item matching bound name in quick-slot 1..4 and consumes/uses it."""
        item_name = self.quick_slots.get(slot_num)
        if not item_name:
            return False

        for idx, item in enumerate(self.slots):
            if item and item.name == item_name:
                return self.use_item(idx, player)

        return False


    def add_item(self, item: Item) -> bool:
        """
        Tries to add an item to the inventory.
        First attempts to stack with existing items of the same type.
        Then places in the first empty slot.
        Returns True if successful, False if inventory is full.
        """
        # 1. Attempt to stack
        if item.max_stack > 1:
            for i, slot in enumerate(self.slots):
                if slot and slot.name == item.name:
                    space_available = slot.max_stack - slot.quantity
                    if space_available > 0:
                        add_qty = min(space_available, item.quantity)
                        slot.quantity += add_qty
                        item.quantity -= add_qty
                        if item.quantity <= 0:
                            return True

        # 2. Find empty slots
        for i, slot in enumerate(self.slots):
            if slot is None:
                self.slots[i] = item.copy()
                return True
                
        return False

    def auto_sort(self) -> None:
        """Sorts inventory items by Type, Rarity tier, and Item Name."""
        items = [s for s in self.slots if s is not None]
        
        rarity_order = {"Legendary": 0, "Epic": 1, "Rare": 2, "Uncommon": 3, "Common": 4}
        type_order = {"weapon": 0, "armor": 1, "shield": 2, "helmet": 3, "chest": 4, "boots": 5, "consumable": 6, "material": 7}
        
        def sort_key(item: Any) -> Tuple[int, int, str]:
            t_rank = type_order.get(getattr(item, "item_type", "material"), 8)
            r_rank = rarity_order.get(getattr(item, "rarity", "Common"), 5)
            return (t_rank, r_rank, getattr(item, "name", ""))
            
        items.sort(key=sort_key)
        self.slots = [None] * self.size
        for idx, it in enumerate(items):
            self.slots[idx] = it

    def remove_item(self, name: str, quantity: int = 1) -> bool:
        """
        Removes a specified quantity of items by name from the inventory.
        Used when consuming items, crafting, or completing quests.
        Returns True if the required quantity was successfully removed, False otherwise.
        """
        if not self.has_item(name, quantity):
            return False

        remaining_to_remove = quantity
        # Iterate backwards to consume from smaller/last stacks first
        for i in range(len(self.slots) - 1, -1, -1):
            slot = self.slots[i]
            if slot and slot.name == name:
                if slot.quantity >= remaining_to_remove:
                    slot.quantity -= remaining_to_remove
                    remaining_to_remove = 0
                    if slot.quantity <= 0:
                        self.slots[i] = None
                    return True
                else:
                    remaining_to_remove -= slot.quantity
                    self.slots[i] = None
                    
        return remaining_to_remove == 0

    def has_item(self, name: str, quantity: int = 1) -> bool:
        """Checks if the inventory contains a minimum quantity of an item by name."""
        return self.get_item_count(name) >= quantity

    def get_item_count(self, name: str) -> int:
        """Returns the total cumulative count of a specific item by name."""
        total = 0
        for slot in self.slots:
            if slot and slot.name == name:
                total += slot.quantity
        return total

    def sort_inventory(self) -> None:
        """
        Sorts items in-place:
        Empty slots go to the end. Filled slots are sorted by rarity,
        item category, then alphabetically by name.
        """
        # Pull all non-null items out
        active_items: List[Item] = [s for s in self.slots if s is not None]
        
        # Sort key weights
        rarity_weights = {
            "Legendary": 5,
            "Epic": 4,
            "Rare": 3,
            "Uncommon": 2,
            "Common": 1
        }
        
        # Sort items
        active_items.sort(
            key=lambda x: (
                -rarity_weights.get(x.rarity, 0),  # Descending rarity
                x.item_type,                      # Group by type
                x.name                            # Alphabetical
            )
        )
        
        # Clear slots and re-insert sorted items
        self.slots = [None] * self.size
        for i, item in enumerate(active_items):
            self.slots[i] = item

    def start_drag(self, slot_idx: int) -> None:
        """Flags a slot index as being dragged."""
        if 0 <= slot_idx < self.size and self.slots[slot_idx] is not None:
            self.dragged_slot_idx = slot_idx
            self.dragged_item = self.slots[slot_idx]

    def stop_drag(self, target_idx: int) -> None:
        """
        Completes the drag and drop. Swaps slots, stacks matching items,
        or drops the item back.
        """
        if self.dragged_slot_idx is None:
            return

        source_idx = self.dragged_slot_idx
        
        if 0 <= target_idx < self.size:
            source_item = self.slots[source_idx]
            target_item = self.slots[target_idx]
            
            # If target has the same item type, try stacking
            if target_item and source_item and target_item.name == source_item.name:
                space = target_item.max_stack - target_item.quantity
                if space > 0:
                    transfer_qty = min(space, source_item.quantity)
                    target_item.quantity += transfer_qty
                    source_item.quantity -= transfer_qty
                    
                    if source_item.quantity <= 0:
                        self.slots[source_idx] = None
                else:
                    # No space to stack, swap instead
                    self.slots[source_idx], self.slots[target_idx] = target_item, source_item
            else:
                # Different item/empty slot, swap them
                self.slots[source_idx], self.slots[target_idx] = target_item, source_item
                
        # Clear drag buffers
        self.dragged_slot_idx = None
        self.dragged_item = None

    def cancel_drag(self) -> None:
        """Cancels dragging and resets pointers."""
        self.dragged_slot_idx = None
        self.dragged_item = None

    def use_item(self, slot_idx: int, player: Any) -> bool:
        """
        Uses or equips an item in the slot. Consumes food/potion,
        or equips gear onto the player.
        """
        if not (0 <= slot_idx < self.size):
            return False
            
        item = self.slots[slot_idx]
        if item is None:
            return False

        # 1. Consumable Potions / Food (3.0s Potion Cooldown)
        if item.item_type in [ITEM_POTION, ITEM_FOOD]:
            if getattr(player, "potion_cooldown_timer", 0.0) > 0.0:
                from rpg.combat import DamageNumber
                DamageNumber(player.rect.center, f"Potion Cooldown ({player.potion_cooldown_timer:.1f}s)", (230, 80, 80), [player.game.ui_sprites], size=14)
                return False

            used = False
            
            # Apply HP recovery
            if "heal_hp" in item.stats:
                if player.hp < player.max_hp:
                    player.hp = min(player.max_hp, player.hp + item.stats["heal_hp"])
                    used = True
                    
            # Apply Mana recovery
            if "heal_mp" in item.stats:
                if player.mana < player.max_mana:
                    player.mana = min(player.max_mana, player.mana + item.stats["heal_mp"])
                    used = True

            # Apply Stamina recovery
            if "heal_stam" in item.stats:
                if player.stamina < player.max_stamina:
                    player.stamina = min(player.max_stamina, player.stamina + item.stats["heal_stam"])
                    used = True
            
            if used:
                player.potion_cooldown_timer = 3.0
                player.sound_manager.play_sound("heal")

                
                # Particle splash
                player.particles.create_heal_sparkles(player.hitbox.center)

                # Consume 1 from stack
                item.quantity -= 1
                if item.quantity <= 0:
                    self.slots[slot_idx] = None
                return True
                
        # 2. Equipable items (Weapon, Armor, Shield, Helmet, Boots, Accessory, Legs)
        elif item.item_type in [ITEM_WEAPON, ITEM_SHIELD, ITEM_HELMET, ITEM_CHEST, ITEM_BOOTS, ITEM_ACCESSORY, ITEM_LEGS]:
            # Temporarily pull the item out of inventory
            to_equip = self.slots[slot_idx]
            self.slots[slot_idx] = None
            
            # Try to equip. It returns the previously equipped item (if any)
            previous_item = player.equipment.equip(to_equip, player)
            
            # Put previous item back in the inventory slot (or find another slot)
            if previous_item:
                self.slots[slot_idx] = previous_item
            
            # Play a click sound
            player.sound_manager.play_sound("click")
            return True

        return False
