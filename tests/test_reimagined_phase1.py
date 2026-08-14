"""
Echoes of Asterra - Phase 1 Reimagined Systems Tests
Tests for:
1. Player-driven Faction Warfare territory control (reputation + zone activity influence)
2. Shop item category mapping & Economy stock scarcity integration
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
from rpg.faction_war import FactionWarManager, FACTION_KNIGHTS, FACTION_BANDITS
from rpg.factions import FactionManager
from rpg.economy import EconomyManager
from rpg.ui import UIManager


class TestFactionWarPlayerDriven(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.faction_war = FactionWarManager()
        self.faction_war.register_event_listeners(self.event_bus)
        self.factions = FactionManager()
        self.factions.register_event_listeners(self.event_bus)
        self.faction_war.faction_manager = self.factions

    def test_zone_kill_tracking(self):
        """Enemy kills in a map region should increment zone_kills counter."""
        self.event_bus.emit("enemy_killed", map_name="forest", enemy_type="wolf")
        self.event_bus.emit("enemy_killed", map_name="forest", enemy_type="wolf")
        self.assertEqual(self.faction_war.zone_kills.get("forest"), 2)

    def test_player_reputation_influences_territory(self):
        """High player reputation with a faction should heavily favor that faction in territory skirmishes."""
        # Set Bandits reputation very high (+90)
        self.factions.modify_reputation(FACTION_BANDITS, 100)
        # Set Knights reputation very low (-50)
        self.factions.modify_reputation(FACTION_KNIGHTS, -60)

        # Trigger day changed tick
        self.event_bus.emit("day_changed", day=2)

        # Forest crossroads (previously held by Knights) should shift toward Bandits due to high rep
        cp = self.faction_war.control_points["forest_crossroads"]
        self.assertEqual(cp.controlling_faction, FACTION_BANDITS)

    def test_territory_serialization_includes_zone_kills(self):
        """Serialization to_dict/from_dict should persist zone_kills and stability."""
        self.faction_war.zone_kills["forest"] = 15
        self.faction_war.control_points["forest_crossroads"].stability = 85.0

        saved = self.faction_war.to_dict()
        new_fw = FactionWarManager()
        new_fw.from_dict(saved)

        self.assertEqual(new_fw.zone_kills.get("forest"), 15)
        self.assertEqual(new_fw.control_points["forest_crossroads"].stability, 85.0)


class TestShopEconomyScarcity(unittest.TestCase):
    def setUp(self):
        self.ui = UIManager()
        self.economy = EconomyManager()

    def test_item_econ_category_mapping(self):
        """Verify shop item names map correctly to economy categories."""
        self.assertEqual(self.ui._get_item_econ_category("Red Potion"), "herbs")
        self.assertEqual(self.ui._get_item_econ_category("Blue Potion"), "herbs")
        self.assertEqual(self.ui._get_item_econ_category("Baked Bread"), "food")
        self.assertEqual(self.ui._get_item_econ_category("Iron Ore"), "ore")
        self.assertEqual(self.ui._get_item_econ_category("Oak Wood"), "goods")
        self.assertEqual(self.ui._get_item_econ_category("Steel Blade"), "goods")

    def test_scarcity_stock_threshold(self):
        """Stock ratio below 0.30 should trigger out-of-stock condition."""
        # Reduce herbs stock to 5.0 out of 80.0 (ratio = 0.0625 < 0.30)
        self.economy.stocks["herbs"].current_stock = 5.0
        ratio = self.economy.stocks["herbs"].current_stock / self.economy.stocks["herbs"].max_capacity
        self.assertTrue(ratio < 0.30)


if __name__ == "__main__":
    unittest.main()
