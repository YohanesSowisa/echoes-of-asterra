"""
Unit tests for Item Affixes, Sockets, and Crafting Disenchanting.
"""
import unittest
from rpg.items import create_item, roll_affixes
from rpg.inventory import Inventory
from rpg.crafting import CraftingSystem

class TestItemAffixesAndSockets(unittest.TestCase):
    def test_roll_affixes_equipment(self) -> None:
        """Tests rolling affixes on weapons."""
        item = create_item("Steel Blade", roll_equipment_affixes=False)
        self.assertIsNotNone(item)
        self.assertEqual(len(item.affixes), 0)

        roll_affixes(item)
        # Verify stats and affix name generator
        name = item.get_affix_display_name()
        self.assertTrue(len(name) >= len("Steel Blade"))

    def test_socket_rune(self) -> None:
        """Tests socketing a Rune of Fire into a weapon."""
        item = create_item("Steel Blade", roll_equipment_affixes=False)
        item.sockets = 1
        inv = Inventory(12)
        rune = create_item("Rune of Fire")
        inv.add_item(rune)

        base_atk = item.stats.get("atk", 0)
        success = CraftingSystem.socket_rune(item, "Rune of Fire", inv)
        self.assertTrue(success)
        self.assertEqual(len(item.socketed_runes), 1)
        self.assertEqual(item.stats.get("atk"), base_atk + 5)

    def test_disenchant_equipment(self) -> None:
        """Tests disenchanting gear into raw materials."""
        item = create_item("Steel Blade", roll_equipment_affixes=False)
        inv = Inventory(12)
        inv.add_item(item)

        success = CraftingSystem.disenchant_equipment(item, inv)
        self.assertTrue(success)
        self.assertTrue(inv.has_item("Timber") or inv.has_item("Iron Ore"))

if __name__ == "__main__":
    unittest.main()
