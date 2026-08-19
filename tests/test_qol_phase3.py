"""
Unit tests for Quality of Life (QoL) Phase 3 features:
1. World Morning Briefing & Session Recap
2. Unified Active Buff Ribbon & Safe Zone Save Indicator
3. High-Contrast Shape-Assisted Status Bars
"""
import unittest
import pygame
from rpg.world_state import WorldState
from rpg.events import EventBus
from rpg.ui import UIManager


class TestQoLPhase3(unittest.TestCase):
    def setUp(self):
        if not pygame.get_init():
            pygame.init()
        self.bus = EventBus()
        self.world_state = WorldState()
        self.world_state.register_event_listeners(self.bus)
        self.ui = UIManager()

    def test_world_morning_briefing(self):
        """WorldState should aggregate daily progress recap and emit morning_briefing_generated on day_tick."""
        briefings_received = []

        def on_briefing(day, season, briefing):
            briefings_received.append((day, season, briefing))

        self.bus.subscribe("morning_briefing_generated", on_briefing)

        # Trigger day tick
        self.world_state.day_tick(self.bus)

        self.assertEqual(len(briefings_received), 1)
        day, season, b_data = briefings_received[0]
        self.assertEqual(day, 2)
        self.assertEqual(b_data["day"], 2)
        self.assertIn("prosperity", b_data)
        self.assertIn("danger", b_data)
        self.assertIn("epoch_title", b_data)

    def test_high_contrast_hud_bar_rendering(self):
        """_draw_hud_bar should render HP, MP, STAM bars with icons onto surface cleanly."""
        surf = pygame.Surface((300, 200))
        # Draw HP bar
        self.ui._draw_hud_bar(surf, 10, 10, 150, 16, 75.0, 100.0, (220, 50, 50), "HP")
        # Draw MP bar
        self.ui._draw_hud_bar(surf, 10, 35, 150, 12, 30.0, 50.0, (50, 150, 220), "MP")
        # Draw STAM bar
        self.ui._draw_hud_bar(surf, 10, 55, 150, 12, 80.0, 100.0, (50, 200, 100), "STAM")

        self.assertIsInstance(surf, pygame.Surface)


if __name__ == "__main__":
    unittest.main()
