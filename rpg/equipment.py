"""
Echoes of Asterra - Equipment Manager
Manages item slot attachments and dynamically recalculates player attributes.
"""
from typing import Dict, Optional, Any
from rpg.items import Item
from rpg.constants import ITEM_WEAPON, ITEM_SHIELD, ITEM_HELMET, ITEM_CHEST, ITEM_BOOTS, ITEM_ACCESSORY, ITEM_LEGS

class Equipment:
    """
    Manages player equipment slots and applies stat modifiers.
    Slots: weapon, helmet, chest, legs, boots, shield, accessory.
    """
    def __init__(self) -> None:
        self.slots: Dict[str, Optional[Item]] = {
            ITEM_WEAPON: None,
            ITEM_HELMET: None,
            ITEM_CHEST: None,
            ITEM_LEGS: None,
            ITEM_BOOTS: None,
            ITEM_SHIELD: None,
            ITEM_ACCESSORY: None
        }

    def equip(self, item: Item, player: Any) -> Optional[Item]:
        """
        Equips an item in its designated slot.
        Returns the previously equipped item in that slot (if any) to return to inventory.
        """
        slot_name = item.item_type
        if slot_name not in self.slots:
            # Accessory or other edge cases
            return item

        previous_item = self.slots[slot_name]
        self.slots[slot_name] = item
        
        # Recalculate player stats
        self.recalculate_player_stats(player)
        return previous_item

    def unequip(self, slot_name: str, player: Any) -> bool:
        """
        Unequips an item from the slot and moves it to the player's inventory.
        Returns True if successful, False if inventory is full.
        """
        item = self.slots.get(slot_name)
        if item is None:
            return False
            
        # Try to add to player inventory
        if player.inventory.add_item(item):
            self.slots[slot_name] = None
            self.recalculate_player_stats(player)
            # Play a click sound
            player.sound_manager.play_sound("click")
            return True
            
        return False

    def recalculate_player_stats(self, player: Any) -> None:
        """
        Summates base stats and equipment modifiers to re-verify player
        attributes (Atk, Def, Magic, Speed, Crit, Max HP, Max Mana).
        """
        # Save current HP/Mana percentages to keep scale correct
        hp_ratio = player.hp / max(1, player.max_hp)
        mana_ratio = player.mana / max(1, player.max_mana)
        
        # Reset modifiers
        bonus_atk = 0
        bonus_def = 0
        bonus_magic = 0
        bonus_speed = 0
        bonus_crit = 0
        bonus_hp = 0
        bonus_mana = 0

        # Scan slots and aggregate stats
        from rpg.items import RUNE_DATABASE
        for slot_item in self.slots.values():
            if slot_item:
                stats = slot_item.stats
                bonus_atk += stats.get("atk", 0)
                bonus_def += stats.get("def", 0)
                bonus_magic += stats.get("magic", 0)
                bonus_speed += stats.get("speed", 0)
                bonus_crit += stats.get("crit", 0)
                bonus_hp += stats.get("hp", 0)
                bonus_mana += stats.get("mana", 0)

                # Aggregate socketed runes
                for rune_name in getattr(slot_item, "socketed_runes", []):
                    rune_info = RUNE_DATABASE.get(rune_name)
                    if rune_info:
                        stat_key = rune_info["stat"]
                        val = rune_info["value"]
                        if stat_key == "atk":
                            bonus_atk += val
                        elif stat_key == "def":
                            bonus_def += val
                        elif stat_key == "crit":
                            bonus_crit += val
                        elif stat_key == "hp":
                            bonus_hp += val
                        elif stat_key == "magic":
                            bonus_magic += val
                        elif stat_key == "mana":
                            bonus_mana += val

        # Apply values to player
        player.max_hp = max(10, player.base_max_hp + bonus_hp)
        player.max_mana = max(5, player.base_max_mana + bonus_mana)
        
        player.atk = max(1, player.base_atk + bonus_atk)
        player.defense = max(0, player.base_def + bonus_def)
        player.magic = max(0, player.base_magic + bonus_magic)
        
        # Clip speed to reasonable ranges so walking isn't broken
        player.speed = max(1.5, player.base_speed + bonus_speed)
        player.crit_chance = max(0, player.base_crit + bonus_crit)
        
        # Scale current pools to match new boundaries
        player.hp = int(hp_ratio * player.max_hp)
        player.mana = int(mana_ratio * player.max_mana)
