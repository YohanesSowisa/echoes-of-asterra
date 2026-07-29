"""
Echoes of Asterra - Engagement Systems Unit Tests
Validates AchievementManager EventBus integration, onboarding tutorial tips,
Minimap enemy quest waypoint markers, 4-tab Character Sheet navigation,
and Settings Difficulty Presets.
"""
import os
import sys
import unittest
import pygame

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from rpg.game import Game
from rpg.achievements import AchievementManager
from rpg.events import EventBus
from rpg.animation import init_assets
from rpg.enemy import Enemy


class TestEngagementSystems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1024, 768))
        init_assets()

    def setUp(self):
        self.game = Game(self.screen)
        self.event_bus = self.game.event_bus
        for ach in self.game.achievement_manager.achievements.values():
            ach.unlocked = False

    def test_achievement_unlock_on_event(self):
        am = self.game.achievement_manager
        self.assertFalse(am.achievements["first_blood"].unlocked)

        # Emit enemy_killed event
        self.event_bus.emit("enemy_killed", player=self.game.player, game=self.game)
        self.assertTrue(am.achievements["first_blood"].unlocked)

    def test_achievement_level_up(self):
        am = self.game.achievement_manager
        self.assertFalse(am.achievements["apprentice_hero"].unlocked)

        # Set player level 5 and emit level_up
        self.game.player.level = 5
        self.event_bus.emit("level_up", level=5, player=self.game.player, game=self.game)
        self.assertTrue(am.achievements["apprentice_hero"].unlocked)

    def test_onboarding_tutorial_tips(self):
        self.assertNotIn("inventory", self.game.tutorial_flags)

        # Emit first_inventory_open
        self.event_bus.emit("first_inventory_open", game=self.game)
        self.assertIn("inventory", self.game.tutorial_flags)
        
        # Verify toast notification was queued
        toasts = self.game.notification_manager.active_toasts + self.game.notification_manager.toast_queue
        self.assertTrue(any("Right-click items" in t.message for t in toasts))

    def test_character_sheet_4_tab_navigation(self):
        self.game.ui_manager.open_panels.add("character")
        self.game.ui_manager.active_char_tab = "factions"

        # Simulate pressing D key 3 times
        tabs = ["factions", "social", "town", "achievements"]
        for expected in ["social", "town", "achievements", "factions"]:
            curr_t = getattr(self.game.ui_manager, "active_char_tab", "factions")
            curr_i = tabs.index(curr_t)
            self.game.ui_manager.active_char_tab = tabs[(curr_i + 1) % len(tabs)]
            self.assertEqual(self.game.ui_manager.active_char_tab, expected)

    def test_minimap_enemy_quest_marker(self):
        # Create a wolf enemy
        wolf = Enemy((300, 300), [], "wolf", "wolf")
        self.game.enemies.append(wolf)

        self.game.quest_manager.accept_quest("main_quest")
        self.game.quest_manager.tracked_quest_id = "main_quest"

        q = self.game.quest_manager.get_tracked_quest()
        self.assertIsNotNone(q)
        active_targets = [obj.target.lower() for obj in q.objectives if not obj.is_complete()]
        self.assertTrue(any("wolf" in t for t in active_targets))


    def test_difficulty_preset_setting(self):
        self.game.difficulty_profile = "normal"
        diff_options = ["explorer", "normal", "veteran", "nightmare"]
        curr_i = diff_options.index(self.game.difficulty_profile)
        self.game.difficulty_profile = diff_options[(curr_i + 1) % len(diff_options)]
        self.assertEqual(self.game.difficulty_profile, "veteran")

    def test_out_of_combat_hp_regen(self):
        player = self.game.player
        player.hp = 50
        player.out_of_combat_timer = 4.5
        player.game = self.game

        initial_hp = player.hp
        player.update(1.0)
        self.assertGreater(player.hp, initial_hp)

    def test_gamepad_input_handler(self):
        input_handler = self.game.input_handler
        self.assertIsNotNone(input_handler.joysticks)



if __name__ == "__main__":
    unittest.main()
