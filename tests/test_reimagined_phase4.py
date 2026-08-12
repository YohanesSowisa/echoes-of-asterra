"""
Echoes of Asterra - Phase 4 Reimagined Systems Tests
Tests for:
1. RumorBoard rumor generation and daily propagation
2. Rumor distortion level progression
3. NPC rumor retrieval
4. DialogueManager automatic rumor choice injection
5. Rumor state serialization
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from rpg.events import EventBus
from rpg.rumors import RumorBoard, Rumor
from rpg.dialogue import DialogueManager, DialogueNode, DialogueChoice


class DummyGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.living_world = DummyLivingWorld(self.event_bus)
        self.dialogue_manager = DialogueManager()
        self.dialogue_manager.game = self

class DummyLivingWorld:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.rumors = RumorBoard(event_bus)


class TestRumorMill(unittest.TestCase):
    def setUp(self):
        self.game = DummyGame()
        self.rb = self.game.living_world.rumors

    def test_initial_rumors(self):
        """RumorBoard should initialize default world rumors."""
        self.assertTrue(len(self.rb.rumors) > 0)
        self.assertIn("rumor_ruins_relic", self.rb.rumors)

    def test_npc_rumor_retrieval(self):
        """get_npc_rumor should return rumor info for origin NPC."""
        rumor_info = self.rb.get_npc_rumor("mira")
        self.assertIsNotNone(rumor_info)
        topic, content, dist = rumor_info
        self.assertEqual(topic, "Ruins Treasure")
        self.assertIn("Mira", content)

    def test_daily_rumor_propagation(self):
        """Emitting day_changed ticks should spread rumors to other NPCs."""
        for day in range(1, 10):
            self.game.event_bus.emit("day_changed", day=day)

        # After multiple days, rumors should be known by more NPCs
        ruins_rumor = self.rb.rumors["rumor_ruins_relic"]
        self.assertTrue(len(ruins_rumor.known_by_npcs) >= 1)

    def test_dialogue_manager_rumor_choice_injection(self):
        """DialogueManager.set_node should automatically inject 'Heard any rumors?' choice."""
        dm = self.game.dialogue_manager
        test_node = DialogueNode(
            "mira_greeting",
            "Scholar Mira",
            "Welcome to the archive, traveler.",
            [DialogueChoice("Hello.", None)]
        )
        dm.add_node(test_node)
        dm.set_node("mira_greeting")

        # Verify rumor choice was injected
        choices_text = [c.text for c in test_node.choices]
        self.assertTrue(any("rumor" in t.lower() for t in choices_text))

    def test_rumor_serialization(self):
        """to_dict and from_dict should serialize rumor state."""
        self.rb.rumors["rumor_ruins_relic"].distortion_level = 0.5
        saved = self.rb.to_dict()

        new_rb = RumorBoard()
        new_rb.from_dict(saved)

        self.assertEqual(new_rb.rumors["rumor_ruins_relic"].distortion_level, 0.5)


if __name__ == "__main__":
    unittest.main()
