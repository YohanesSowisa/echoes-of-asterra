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
from rpg.enemy import DroppedItem

class TestRespawnSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((64, 64))
        from rpg.animation import init_assets
        init_assets()


    def test_dropped_item_despawn_timer(self):
        item = create_item("Red Potion", 1)
        group = pygame.sprite.Group()
        drop = DroppedItem((10.0, 10.0), item, [group], despawn_time=300.0)
        self.assertEqual(drop.despawn_timer, 300.0)
        
        # Fast-forward timer by 301 seconds
        drop.update(301.0)
        self.assertNotIn(drop, group)

    def test_respawn_penalties_and_drops(self):
        from rpg.game import Game
        game = Game(self.screen)
        player = game.player

        # Set player stats and add inventory item
        player.xp = 100
        player.xp_needed = 200
        player.gold = 100
        pot = create_item("Red Potion", 2)
        player.inventory.add_item(pot)

        # Trigger death
        player.take_damage(999)
        self.assertEqual(player.state, "dead")

        # Trigger respawn
        game.respawn_player()

        # Check state restored
        self.assertEqual(player.state, "idle")
        self.assertEqual(player.hp, player.max_hp)

        # Check penalties: -25% XP of xp_needed (50 XP lost -> 50 remaining)
        self.assertEqual(player.xp, 50)
        # Check Gold penalty: -30% Gold (30 Gold lost -> 70 remaining)
        self.assertEqual(player.gold, 70)

        # Check map is Village
        self.assertEqual(game.world_manager.current_map_name, "village")

        # Check persistent floating items saved for death map
        self.assertTrue(len(game.world_manager.persistent_dropped_items["village"]) >= 1)
        self.assertTrue(len(game.dropped_items) >= 1)


if __name__ == "__main__":
    unittest.main()
