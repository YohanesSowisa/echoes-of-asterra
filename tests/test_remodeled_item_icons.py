import unittest
import pygame
from rpg.items import create_item
from rpg.animation import init_assets, item_assets

class TestRemodeledItemIcons(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((64, 64))
        init_assets()

    def test_gold_coins_icon_remodel(self):
        gold = create_item("Gold Coins", 10)
        self.assertIsNotNone(gold.icon)
        # Verify icon matches dedicated gold_coins surface, not artifact heart
        self.assertEqual(gold.icon, item_assets["gold_coins"])
        self.assertNotEqual(gold.icon, item_assets["artifact"])

    def test_forest_apple_icon_remodel(self):
        apple = create_item("Forest Apple", 1)
        bread = create_item("Baked Bread", 1)
        self.assertIsNotNone(apple.icon)
        self.assertIsNotNone(bread.icon)

        # Apple must use dedicated apple icon, not bread food icon
        self.assertEqual(apple.icon, item_assets["apple"])
        self.assertEqual(bread.icon, item_assets["food"])
        self.assertNotEqual(apple.icon, bread.icon)

    def test_wooden_shield_and_oak_wood_uniqueness(self):
        w_shield = create_item("Wooden Shield", 1)
        oak_wood = create_item("Oak Wood", 2)
        timber = create_item("Timber", 3)

        self.assertIsNotNone(w_shield)
        self.assertIsNotNone(oak_wood)
        self.assertIsNotNone(timber)

        # Wooden Shield must use round buckler icon, Oak Wood must use log icon, Timber uses planks
        self.assertEqual(w_shield.icon, item_assets["shield_wooden"])
        self.assertEqual(oak_wood.icon, item_assets["log_oak"])
        self.assertEqual(timber.icon, item_assets["material_wood"])

        self.assertNotEqual(w_shield.icon, oak_wood.icon)
        self.assertNotEqual(w_shield.icon, timber.icon)
        self.assertNotEqual(oak_wood.icon, timber.icon)

    def test_all_game_items_have_unique_valid_icons(self):
        w_shield = create_item("Wooden Shield", 1)
        i_aegis = create_item("Iron Aegis", 1)
        oak = create_item("Oak Wood", 1)
        leather = create_item("Beast Leather", 1)
        amulet = create_item("Glow Amulet", 1)
        key = create_item("Dungeon Key", 1)

        self.assertEqual(w_shield.icon, item_assets["shield_wooden"])
        self.assertEqual(i_aegis.icon, item_assets["shield_iron"])
        self.assertEqual(oak.icon, item_assets["log_oak"])
        self.assertEqual(leather.icon, item_assets["material_leather"])
        self.assertEqual(amulet.icon, item_assets["amulet_glow"])
        self.assertEqual(key.icon, item_assets["key_dungeon"])


if __name__ == "__main__":
    unittest.main()

