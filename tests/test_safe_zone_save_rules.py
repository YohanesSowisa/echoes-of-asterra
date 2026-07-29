import unittest
import pygame
from rpg.constants import MAP_VILLAGE, MAP_FOREST

from rpg.game import Game
from rpg.enemy import Slime

class TestSafeZoneSaveRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1024, 768))

    def setUp(self):
        self.game = Game(self.screen)
        self.game.start_new_game()

    def test_village_is_always_safe_zone(self):
        self.game.world_manager.current_map_name = MAP_VILLAGE
        can_save, reason = self.game.is_save_allowed()
        self.assertTrue(can_save)
        self.assertIn("Village", reason)

    def test_forest_save_allowed_when_no_enemies_nearby(self):
        self.game.world_manager.current_map_name = MAP_FOREST
        self.game.enemies.clear()

        can_save, reason = self.game.is_save_allowed()
        self.assertTrue(can_save)
        self.assertEqual(reason, "Safe to save")

    def test_forest_save_blocked_when_enemy_nearby(self):
        self.game.world_manager.current_map_name = MAP_FOREST
        self.game.enemies.clear()

        # Place player at (100, 100) and enemy at (200, 100) -> distance 100 < 280px radius
        self.game.player.pos = pygame.math.Vector2(100, 100)
        slime = Slime((200, 100), [])
        self.game.enemies.append(slime)

        can_save, reason = self.game.is_save_allowed()
        self.assertFalse(can_save)
        self.assertIn("nearby", reason)

    def test_forest_save_blocked_when_in_combat_aggro(self):
        self.game.world_manager.current_map_name = MAP_FOREST
        self.game.enemies.clear()

        # Place enemy far away (500, 500) but aggro is active
        self.game.player.pos = pygame.math.Vector2(100, 100)
        slime = Slime((500, 500), [])
        slime.aggro = True
        self.game.enemies.append(slime)

        can_save, reason = self.game.is_save_allowed()
        self.assertFalse(can_save)
        self.assertIn("combat", reason.lower())



    def test_save_blocked_when_player_dead(self):
        self.game.world_manager.current_map_name = MAP_VILLAGE
        self.game.player.is_dead = True
        self.game.player.hp = 0

        can_save, reason = self.game.is_save_allowed()
        self.assertFalse(can_save)
        self.assertIn("fallen or defeated", reason.lower())

if __name__ == "__main__":
    unittest.main()
