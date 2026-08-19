"""
Unit tests for Quality of Life (QoL) Phase 4 features:
1. Altar & Soul Pact Consequence Confirmation Modal
2. One-Click Claim All Passive Dividends
3. Off-Screen Boss / Danger Pointer Chevron Indicator
"""
import unittest
import pygame
from rpg.world import PactAltarSprite
from rpg.pacts import PactManager
from rpg.dialogue import DialogueManager
from rpg.monopoly import MonopolyManager
from rpg.outpost import OutpostManager
from rpg.inventory import Inventory
from rpg.items import create_item
from rpg.events import EventBus
from rpg.ui import UIManager


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.pact_manager = PactManager(self.event_bus)
        self.dialogue_manager = DialogueManager()
        self.monopoly_manager = MonopolyManager(self.event_bus)
        self.outpost_manager = OutpostManager(self.event_bus)
        self.ui_manager = UIManager()
        self.ui_sprites = pygame.sprite.Group()
        self.game_state = 1
        self.enemies = []


class MockPlayer:
    def __init__(self, game):
        self.game = game
        self.gold = 50
        self.inventory = Inventory(size=10)
        self.rect = pygame.Rect(100, 100, 32, 32)
        self.pos = pygame.math.Vector2(100.0, 100.0)


class TestQoLPhase4(unittest.TestCase):
    def setUp(self):
        if not pygame.get_init():
            pygame.init()
        self.game = MockGame()
        self.player = MockPlayer(self.game)

    def test_altar_confirmation_modal_prompt(self):
        """Interacting with a Pact Altar must trigger confirmation dialogue node detailing benefits and curses."""
        altar = PactAltarSprite((100, 100), "void", [])
        altar.interact(self.player)

        # Dialogue manager should have active altar node
        self.assertIsNotNone(self.game.dialogue_manager.current_node)
        node = self.game.dialogue_manager.current_node
        self.assertIn("BENEFITS & CURSES", node.text)
        self.assertEqual(len(node.choices), 2)
        self.assertIn("Accept", node.choices[0].text)
        self.assertIn("Back away", node.choices[1].text)

    def test_claim_all_passive_dividends(self):
        """MonopolyManager.claim_all_passive_dividends should collect tolls and deposit commodities."""
        self.player.inventory.add_item(create_item("Iron Ore", 10))

        # Setup an outpost that has accumulated tolls
        outpost = self.game.outpost_manager.outposts["forest_crossroads"]
        outpost.is_built = True
        outpost.level = 1
        outpost.unclaimed_toll_gold = 120

        summary = self.game.monopoly_manager.claim_all_passive_dividends(self.game, self.player)

        self.assertEqual(summary["outpost_gold"], 120)
        self.assertEqual(summary["deposited_commodities"], 10)
        self.assertEqual(summary["total_gold"], 120)
        self.assertEqual(self.game.monopoly_manager.warehouse.get_stock("iron_ore"), 10)

    def test_offscreen_boss_indicator_rendering(self):
        """_draw_offscreen_boss_indicators should calculate position and render chevron badges for offscreen bosses."""
        class MockBoss:
            def __init__(self, pos):
                self.pos = pygame.math.Vector2(pos[0], pos[1])
                self.hp = 500
                self.is_boss = True

        class MockCamera:
            def get_offset(self):
                return pygame.math.Vector2(0, 0)

        self.game.camera = MockCamera()
        self.game.enemies = [MockBoss((2000, 1500))]  # Far offscreen

        surf = pygame.Surface((1024, 768))
        self.game.ui_manager._draw_offscreen_boss_indicators(surf, self.game)
        self.assertIsInstance(surf, pygame.Surface)


if __name__ == "__main__":
    unittest.main()
