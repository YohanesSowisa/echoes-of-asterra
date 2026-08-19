"""
Unit tests for Quality of Life (QoL) Phase 2 features:
1. Modular HUD Declutter Toggle ([H])
2. Town Return / Waypoint Recall Channeling ([T]) & Interruption Rules
3. Equipment Stat Comparison Tooltip Logic
"""
import unittest
import pygame
from rpg.player import Player
from rpg.ui import UIManager
from rpg.items import create_item
from rpg.events import EventBus
from rpg.notification import NotificationManager


class MockWorldManager:
    def __init__(self):
        self.current_map_name = "crypt"
        self.current_map_grid = [[0] * 40 for _ in range(40)]
        self.loaded_maps = []

    def load_map(self, map_name, player, portal_spawn=True, portal_coord=None):
        self.current_map_name = map_name
        self.loaded_maps.append((map_name, portal_coord))
        if portal_coord:
            player.pos = pygame.math.Vector2(portal_coord[0], portal_coord[1])
            player.rect.center = (int(player.pos.x), int(player.pos.y))
            player.hitbox.center = player.rect.center


class MockSoundManager:
    def play_sound(self, name):
        pass


class MockParticles:
    def add_particle(self, particle):
        pass
    def create_wind_stream(self, pos, dir_vec):
        pass
    def create_ghost_afterimage(self, pos, image):
        pass
    def create_dust_puff(self, pos):
        pass


class MockInputHandler:
    def __init__(self):
        self.is_blocking = False
        self.is_running = False
        self.move_dir = pygame.math.Vector2(0, 0)
    def update_keyboard_states(self):
        pass
    def get_movement_vector(self):
        return self.move_dir
    def consume_action(self, action_name):
        return False


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.notification_manager = NotificationManager()
        self.world_manager = MockWorldManager()
        self.ui_manager = UIManager()
        self.input_handler = MockInputHandler()
        self.game_state = 1  # STATE_PLAYING


class TestQoLPhase2(unittest.TestCase):
    def setUp(self):
        if not pygame.get_init():
            pygame.init()
        self.game = MockGame()
        self.player = Player((400, 300), [], MockSoundManager(), MockParticles())
        self.player.game = self.game

    def test_hud_declutter_toggle(self):
        """UIManager should cycle through 'full' -> 'minimal' -> 'hidden' -> 'full'."""
        ui = UIManager()
        self.assertEqual(ui.hud_mode, "full")

        m1 = ui.toggle_hud_mode()
        self.assertEqual(m1, "minimal")
        self.assertEqual(ui.hud_mode, "minimal")

        m2 = ui.toggle_hud_mode()
        self.assertEqual(m2, "hidden")
        self.assertEqual(ui.hud_mode, "hidden")

        m3 = ui.toggle_hud_mode()
        self.assertEqual(m3, "full")
        self.assertEqual(ui.hud_mode, "full")

    def test_player_recall_channeling_and_teleport(self):
        """Player should channel recall for 3.0s and teleport to Asterra Village upon completion."""
        succ, _ = self.player.start_recall()
        self.assertTrue(succ)
        self.assertTrue(self.player.is_channeling_recall)
        self.assertEqual(self.player.recall_channel_timer, 3.0)

        # Partial tick
        self.player.update(1.0)
        self.assertTrue(self.player.is_channeling_recall)
        self.assertAlmostEqual(self.player.recall_channel_timer, 2.0)

        # Complete tick
        self.player.update(2.1)
        self.assertFalse(self.player.is_channeling_recall)
        self.assertEqual(self.game.world_manager.current_map_name, "overworld")
        self.assertEqual((self.player.pos.x, self.player.pos.y), (400.0, 300.0))

    def test_player_recall_interrupted_by_damage(self):
        """Taking damage must immediately cancel active recall channeling."""
        self.player.start_recall()
        self.assertTrue(self.player.is_channeling_recall)

        self.player.take_damage(10)
        self.assertFalse(self.player.is_channeling_recall)
        self.assertEqual(self.player.recall_channel_timer, 0.0)

    def test_player_recall_interrupted_by_movement(self):
        """Moving or attacking must cancel active recall channeling."""
        self.player.start_recall()
        self.assertTrue(self.player.is_channeling_recall)

        # Player moves via input
        self.game.input_handler.move_dir = pygame.math.Vector2(1.0, 0.0)
        self.player.update(0.1)

        self.assertFalse(self.player.is_channeling_recall)
        self.assertEqual(self.player.recall_channel_timer, 0.0)

    def test_tooltip_equipment_diff_calculation(self):
        """Comparing a new weapon against equipped weapon should compute correct net gain/drop."""
        rusty = create_item("Rusty Sword", 1, roll_equipment_affixes=False)   # Atk 4
        steel = create_item("Steel Blade", 1, roll_equipment_affixes=False)   # Atk 12, Crit 5
        self.player.equipment.equip(rusty, self.player)

        # Check net difference
        eq_weapon = self.player.equipment.slots["weapon"]
        self.assertEqual(eq_weapon.name, "Rusty Sword")

        diff_atk = steel.stats["atk"] - eq_weapon.stats["atk"]
        self.assertEqual(diff_atk, 8)  # +8 gain


if __name__ == "__main__":
    unittest.main()
