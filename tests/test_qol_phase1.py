"""
Unit tests for Quality of Life (QoL) Phase 1 features:
1. Auto-loot suction & proximity
2. Notification history ring buffer
3. Dialogue text speed & instant skip
4. Auto-sort inventory & quick-deposit matching commodities
"""
import unittest
from rpg.notification import NotificationManager, NotificationPriority
from rpg.dialogue import DialogueManager, DialogueNode
from rpg.inventory import Inventory
from rpg.items import create_item
from rpg.monopoly import MonopolyManager
from rpg.events import EventBus


class TestQoLPhase1(unittest.TestCase):
    def test_notification_history_buffer(self) -> None:
        """NotificationManager should log pushed toasts to history ring buffer (max 40)."""
        nm = NotificationManager(max_visible=3)
        self.assertEqual(len(nm.notification_history), 0)

        # Push multiple toasts
        nm.push_toast("First Notice", NotificationPriority.LOW, category="general")
        nm.push_toast("Siege Outbreak!", NotificationPriority.CRITICAL, category="siege")

        self.assertEqual(len(nm.notification_history), 2)
        # Newest toast should be at index 0
        self.assertEqual(nm.notification_history[0]["message"], "Siege Outbreak!")
        self.assertEqual(nm.notification_history[0]["priority"], "CRITICAL")
        self.assertEqual(nm.notification_history[1]["message"], "First Notice")

        # Test ring buffer cap (max 40)
        for i in range(50):
            nm.push_toast(f"Spam {i}", NotificationPriority.LOW)

        self.assertEqual(len(nm.notification_history), 40)
        self.assertEqual(nm.notification_history[0]["message"], "Spam 49")

    def test_dialogue_speed_modes_and_skip(self) -> None:
        """DialogueManager should support speed configuration and instant skip."""
        dm = DialogueManager()
        dm.set_type_speed("normal")
        self.assertEqual(dm.type_speed, 35.0)

        dm.set_type_speed("fast")
        self.assertEqual(dm.type_speed, 80.0)

        dm.set_type_speed("instant")
        self.assertEqual(dm.type_speed, 9999.0)

        # Test instant skip
        node = DialogueNode("test_node", "Dennis", "Welcome to the grand forge of Asterra! We have the finest iron blades.")
        dm.add_node(node)
        dm.start_dialogue("test_node")

        self.assertFalse(dm.typing_finished)
        self.assertEqual(dm.visible_text, "")

        dm.skip_typing()
        self.assertTrue(dm.typing_finished)
        self.assertEqual(dm.visible_text, node.text)

    def test_inventory_auto_sort(self) -> None:
        """Inventory auto_sort should group weapons, armor, consumables, and materials cleanly."""
        inv = Inventory(size=10)
        inv.add_item(create_item("Iron Ore", 5))
        inv.add_item(create_item("Steel Blade", 1))
        inv.add_item(create_item("Red Potion", 3))
        inv.add_item(create_item("Leather Chest", 1))

        inv.auto_sort()

        # Slots should be sorted with weapons and armor first, potions then materials
        sorted_names = [s.name for s in inv.slots if s is not None]
        self.assertEqual(sorted_names[0], "Steel Blade")     # Weapon (type rank 0)
        self.assertEqual(sorted_names[1], "Leather Chest")   # Armor (type rank 1/4)
        self.assertEqual(sorted_names[2], "Red Potion")      # Consumable (type rank 6)
        self.assertEqual(sorted_names[3], "Iron Ore")        # Material (type rank 7)

    def test_monopoly_quick_deposit_matching(self) -> None:
        """MonopolyManager should deposit matching inventory commodities to warehouse."""
        bus = EventBus()
        mm = MonopolyManager(bus)
        inv = Inventory(size=10)

        inv.add_item(create_item("Iron Ore", 15))
        inv.add_item(create_item("Herb", 10))
        inv.add_item(create_item("Steel Blade", 1))  # Non-commodity

        deposited = mm.deposit_matching_from_inventory(inv)
        self.assertEqual(deposited, 25)

        # Warehouse stock updated
        self.assertEqual(mm.warehouse.get_stock("iron_ore"), 15)
        self.assertEqual(mm.warehouse.get_stock("medicinal_herb"), 10)

        # Inventory commodities consumed, weapon preserved
        self.assertFalse(inv.has_item("Iron Ore", 1))
        self.assertFalse(inv.has_item("Herb", 1))
        self.assertTrue(inv.has_item("Steel Blade", 1))


if __name__ == "__main__":
    unittest.main()
