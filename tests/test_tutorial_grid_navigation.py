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


if __name__ == "__main__":
    unittest.main()
