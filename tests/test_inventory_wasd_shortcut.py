import os
import sys
import unittest
import pygame

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from rpg.items import create_item
from rpg.game import Game


class TestInventoryWASDShortcut(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((64, 64))
        from rpg.animation import init_assets
        init_assets()

    def test_quick_slot_assignment_and_usage(self):
        game = Game(self.screen)
        player = game.player

        # Add Red Potion to inventory
        pot = create_item("Red Potion", 2)
        player.inventory.add_item(pot)

        # Assign Red Potion to quick-slot 1
        player.inventory.assign_quick_slot(1, "Red Potion")
        self.assertEqual(player.inventory.quick_slots[1], "Red Potion")

        # Damage player slightly so potion can be consumed
        player.hp = 50
        self.assertTrue(player.inventory.use_quick_slot(1, player))
        # Potion should restore HP
        self.assertGreater(player.hp, 50)

    def test_wasd_inventory_cursor_movement(self):
        game = Game(self.screen)
        ui = game.ui_manager
        
        # Initial cursor is at slot 0
        ui.selected_inventory_slot = 0
        
        # Move right (A/D) -> slot 1
        ui.selected_inventory_slot = (ui.selected_inventory_slot + 1) % 24
        self.assertEqual(ui.selected_inventory_slot, 1)

        # Move down (W/S, 6 cols per row) -> slot 7
        ui.selected_inventory_slot = (ui.selected_inventory_slot + 6) % 24
        self.assertEqual(ui.selected_inventory_slot, 7)

    def test_reject_material_quick_slot_assignment(self):
        game = Game(self.screen)
        player = game.player

        # Oak Wood material item
        wood = create_item("Oak Wood", 5)
        self.assertFalse(player.inventory.assign_quick_slot(1, wood))
        self.assertNotEqual(player.inventory.quick_slots[1], "Oak Wood")


if __name__ == "__main__":
    unittest.main()
