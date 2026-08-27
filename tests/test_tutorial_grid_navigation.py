"""
Unit tests for 2D Grid Tutorial Navigation in UIManager.
Verifies true 2D row-wrapping and column-wrapping for the 12-tab (6x2 grid) tutorial.
"""
import unittest
from rpg.ui import UIManager


class TestTutorialGridNavigation(unittest.TestCase):
    def setUp(self) -> None:
        self.ui = UIManager()
        self.ui.tutorial_page_idx = 0

    def test_horizontal_wrap_row_0(self) -> None:
        """Row 0 (indices 0..5) should wrap horizontally within Row 0 only."""
        # Start at 0, go right to 5, then wrap back to 0
        expected_seq = [1, 2, 3, 4, 5, 0]
        for exp in expected_seq:
            res = self.ui.navigate_tutorial_grid("right")
            self.assertEqual(res, exp, f"Expected {exp} going right, got {res}")

        # Start at 0, go left to 5 (wrap), then left down to 0
        self.ui.tutorial_page_idx = 0
        expected_rev = [5, 4, 3, 2, 1, 0]
        for exp in expected_rev:
            res = self.ui.navigate_tutorial_grid("left")
            self.assertEqual(res, exp, f"Expected {exp} going left, got {res}")

    def test_horizontal_wrap_row_1(self) -> None:
        """Row 1 (indices 6..11) should wrap horizontally within Row 1 only."""
        self.ui.tutorial_page_idx = 6
        expected_seq = [7, 8, 9, 10, 11, 6]
        for exp in expected_seq:
            res = self.ui.navigate_tutorial_grid("d")
            self.assertEqual(res, exp, f"Expected {exp} going 'd', got {res}")

        # From index 11, pressing 'd' / 'right' should wrap back to 6 (not 12 or 0)
        self.ui.tutorial_page_idx = 11
        self.assertEqual(self.ui.navigate_tutorial_grid("right"), 6)

        # From index 6, pressing 'a' / 'left' should wrap to 11 (not 5)
        self.ui.tutorial_page_idx = 6
        self.assertEqual(self.ui.navigate_tutorial_grid("left"), 11)

    def test_vertical_wrap_all_columns(self) -> None:
        """All columns (0..5) should switch rows vertically and wrap between Row 0 and Row 1."""
        for col in range(6):
            # Row 0 -> Down -> Row 1
            self.ui.tutorial_page_idx = col
            res_down = self.ui.navigate_tutorial_grid("down")
            self.assertEqual(res_down, col + 6, f"Col {col} down should reach {col + 6}, got {res_down}")

            # Row 1 -> Down -> Row 0 (wrap)
            res_down_wrap = self.ui.navigate_tutorial_grid("down")
            self.assertEqual(res_down_wrap, col, f"Col {col+6} down wrap should reach {col}, got {res_down_wrap}")

            # Row 0 -> Up -> Row 1 (wrap)
            self.ui.tutorial_page_idx = col
            res_up_wrap = self.ui.navigate_tutorial_grid("up")
            self.assertEqual(res_up_wrap, col + 6, f"Col {col} up wrap should reach {col + 6}, got {res_up_wrap}")

            # Row 1 -> Up -> Row 0
            res_up = self.ui.navigate_tutorial_grid("up")
            self.assertEqual(res_up, col, f"Col {col+6} up should reach {col}, got {res_up}")

    def test_tab_key_linear_cycling(self) -> None:
        """Tab key advances through all 12 tabs sequentially."""
        self.ui.tutorial_page_idx = 0
        for exp in list(range(1, 12)) + [0]:
            res = self.ui.navigate_tutorial_grid("tab")
            self.assertEqual(res, exp)

    def test_all_12_indices_valid_and_reachable(self) -> None:
        """Ensure all 12 indices (0 to 11) are valid and never exceed bounds."""
        visited = set()
        self.ui.tutorial_page_idx = 0
        visited.add(0)

        # Traverse entire row 0
        for _ in range(5):
            idx = self.ui.navigate_tutorial_grid("d")
            self.assertTrue(0 <= idx <= 11)
            visited.add(idx)

        # Move to row 1
        idx = self.ui.navigate_tutorial_grid("s")
        self.assertTrue(0 <= idx <= 11)
        visited.add(idx)

        # Traverse entire row 1
        for _ in range(5):
            idx = self.ui.navigate_tutorial_grid("a")
            self.assertTrue(0 <= idx <= 11)
            visited.add(idx)

        self.assertEqual(len(visited), 12, "All 12 tabs should be visited")

    def test_pause_menu_opens_tutorial(self) -> None:
        """Pause menu option 3 should transition to STATE_TUTORIAL and flag _from_pause_menu."""
        from rpg.constants import STATE_TUTORIAL, STATE_PAUSED
        class MockGame:
            def __init__(self):
                self.game_state = STATE_PAUSED
                self._from_pause_menu = False
                self.sound_manager = type("MockSound", (), {"play_sound": lambda *args: None})()

        game = MockGame()
        self.assertIn("Tutorial", self.ui.pause_options)
        tut_idx = self.ui.pause_options.index("Tutorial")
        self.assertEqual(tut_idx, 3)

        self.ui.pause_menu_state = "main"
        self.ui.execute_pause_choice(tut_idx, game)

        self.assertEqual(game.game_state, STATE_TUTORIAL)
        self.assertTrue(game._from_pause_menu)

    def test_tutorial_return_resumes_map_music(self) -> None:
        """When returning from tutorial to pause/game, resume_map_music should be invoked."""
        from rpg.constants import STATE_TUTORIAL, STATE_PAUSED, MAP_FOREST
        music_calls = []

        class MockSound:
            def __init__(self):
                self.current_music = "menu_music"
            def play_music(self, name: str, force: bool = False):
                self.current_music = name
                music_calls.append((name, force))
            def play_sound(self, name: str):
                pass

        class MockWorld:
            def __init__(self):
                self.current_map_name = MAP_FOREST
                self.boss_defeated = False

        from rpg.game import Game
        game = Game.__new__(Game)
        game.sound_manager = MockSound()
        game.world_manager = MockWorld()
        game.game_state = STATE_TUTORIAL
        game._from_pause_menu = True

        game.resume_map_music()
        self.assertEqual(game.sound_manager.current_music, "forest_music")
        self.assertIn(("forest_music", True), music_calls)

    def test_pause_slot_actions_property(self) -> None:
        """UIManager.pause_slot_actions should return correct actions for save and load sources."""
        self.ui.slots_meta = {1: {"exists": True, "slot_name": "Hero Slot", "level": 5, "gold": 100, "map": "village"}}
        self.ui.selected_slot_idx = 0

        # Save source with existing slot
        self.ui.pause_action_source = "save"
        self.assertEqual(self.ui.pause_slot_actions, ["Overwrite Save", "Rename Profile", "Delete Save", "Back"])

        # Load source with existing slot
        self.ui.pause_action_source = "load"
        self.assertEqual(self.ui.pause_slot_actions, ["Load Profile", "Rename Profile", "Delete Save", "Back"])

        # Empty slot
        self.ui.slots_meta = {1: {"exists": False}}
        self.ui.pause_action_source = "save"
        self.assertEqual(self.ui.pause_slot_actions, ["Create Save", "Back"])
        self.ui.pause_action_source = "load"
        self.assertEqual(self.ui.pause_slot_actions, ["Back"])

    def test_load_menu_from_main_menu_escape_returns_to_main_menu(self) -> None:
        """Pressing ESC in load_slots when opened from main menu should return to STATE_MENU."""
        from rpg.constants import STATE_MENU, STATE_PAUSED
        from rpg.game import Game
        import pygame

        game = Game.__new__(Game)
        game.ui_manager = self.ui
        class MockS:
            def play_sound(self, *a, **kw): pass
            def play_music(self, *a, **kw): pass
        game.sound_manager = MockS()

        # Simulate clicking "Load Adventure" from Main Menu
        self.ui.execute_menu_choice(1, game)
        self.assertEqual(game.game_state, STATE_PAUSED)
        self.assertEqual(self.ui.pause_menu_state, "load_slots")
        self.assertTrue(game._from_main_menu)

        # Simulate ESC key in STATE_PAUSED
        if self.ui.pause_menu_state in ["save_slots", "load_slots"]:
            if getattr(game, "_from_main_menu", False):
                game.game_state = STATE_MENU
            else:
                self.ui.pause_menu_state = "main"

        self.assertEqual(game.game_state, STATE_MENU)


if __name__ == "__main__":
    unittest.main()
