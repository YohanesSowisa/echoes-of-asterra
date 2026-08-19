"""
Unit tests for Pillar #5: Sovereign Guilds & The Continental Monopoly — Phase 2 (Supply Hoarding & Faction Military Embargoes).
Tests iron ore hoarding thresholds, 2.5x store price surges, Knights of Asterra -20% defense penalties,
Bandit medical herb embargoes canceling HP regeneration, and dynamic town rumor dissemination.
"""
import unittest
import pygame
from rpg.events import EventBus
from rpg.constants import FACTION_KNIGHTS, FACTION_BANDITS
from rpg.monopoly import MonopolyManager
from rpg.economy import EconomyManager
from rpg.faction_war import FactionWarManager
from rpg.rumors import RumorManager
from rpg.enemy import BanditLeader


class MockPlayer:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 32, 32)
        self.pos = pygame.math.Vector2(0, 0)
        self.in_cutscene = False


class MockWorld:
    def __init__(self):
        self.current_map_grid = [["grass" for _ in range(10)] for _ in range(10)]


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.monopoly_manager = MonopolyManager(self.event_bus)
        self.economy_manager = EconomyManager()
        self.faction_war_manager = FactionWarManager()
        self.faction_war_manager.game_reference = self
        self.rumor_manager = RumorManager(self.event_bus)
        self.world_manager = MockWorld()
        self.player = MockPlayer()


class TestMonopolyPhase2(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.mm = self.game.monopoly_manager
        self.eco = self.game.economy_manager
        self.eco.stocks["ore"].current_stock = 60.0  # Set stock ratio to 0.60 -> base 1.0x price
        self.fw = self.game.faction_war_manager
        self.rumors = self.game.rumor_manager

    def test_iron_ore_hoarding_and_price_surge(self):
        """Tests that hoarding 30+ units of iron ore surges market prices by 2.5x."""
        # 1. Normal stock (10 iron ore)
        self.mm.warehouse.add_item("iron_ore", 10)
        self.assertFalse(self.mm.is_hoarding("iron_ore"))
        self.assertEqual(self.mm.get_commodity_price_multiplier("ore"), 1.0)
        base_eco_mult = self.eco.get_price_multiplier("ore", self.mm)
        self.assertEqual(base_eco_mult, 1.0)

        # 2. Hoard 30+ iron ore
        self.mm.warehouse.add_item("iron_ore", 25)  # Total: 35
        self.assertTrue(self.mm.is_hoarding("iron_ore"))
        self.assertEqual(self.mm.get_commodity_price_multiplier("ore"), 2.5)

        hoarded_eco_mult = self.eco.get_price_multiplier("ore", self.mm)
        self.assertEqual(hoarded_eco_mult, 2.5)

    def test_knights_defense_reduction_during_iron_embargo(self):
        """Tests that Knights of Asterra suffer a -20% DEF debuff during iron ore shortages."""
        # 1. Normal defense
        self.assertEqual(self.fw.get_faction_defense_multiplier(FACTION_KNIGHTS), 1.0)

        # 2. Hoard iron ore -> triggers passive iron shortage for Knights
        self.mm.warehouse.add_item("iron_ore", 30)
        self.assertTrue(self.mm.is_faction_embargoed(FACTION_KNIGHTS, "iron_ore"))
        self.assertEqual(self.fw.get_faction_defense_multiplier(FACTION_KNIGHTS), 0.8)

        # 3. Direct targeted embargo
        self.mm.warehouse.stock["iron_ore"] = 0
        self.mm.set_faction_embargo(FACTION_KNIGHTS, "iron_ore", True)
        self.assertTrue(self.mm.is_faction_embargoed(FACTION_KNIGHTS, "iron_ore"))
        self.assertEqual(self.fw.get_faction_defense_multiplier(FACTION_KNIGHTS), 0.8)

    def test_bandit_medical_herb_embargo_and_hp_regen(self):
        """Tests that cutting off medical herbs to Bandits cancels their HP regeneration."""
        sprite_group = pygame.sprite.Group()
        bandit = BanditLeader((100, 100), [sprite_group])
        bandit.game = self.game
        bandit.hp = 200.0  # Damaged (max 280)

        # 1. Without embargo: bandit regenerates HP (+3.0 HP/s)
        bandit.update(1.0)
        self.assertAlmostEqual(bandit.hp, 203.0, places=1)

        # 2. Impose medical herb embargo
        self.mm.set_faction_embargo("bandits", "medicinal_herb", True)
        self.assertTrue(self.mm.is_faction_embargoed("bandits", "medicinal_herb"))

        # 3. With embargo: bandit HP does NOT regenerate
        hp_before = bandit.hp
        bandit.update(1.0)
        self.assertEqual(bandit.hp, hp_before)

    def test_monopoly_rumors_propagation(self):
        """Tests dynamic town gossip generation when player hoards iron or embargoes factions."""
        # Hoard iron ore
        self.mm.warehouse.add_item("iron_ore", 32)
        # Embargo bandits
        self.mm.set_faction_embargo("bandits", "medicinal_herb", True)

        self.rumors.check_monopoly_rumors(self.mm)

        self.assertIn("rumor_iron_hoarding", self.rumors.rumors)
        r_iron = self.rumors.rumors["rumor_iron_hoarding"]
        self.assertEqual(r_iron.origin_npc, "dennis")
        self.assertIn("iron cartel is hoarding all ore", r_iron.true_content)

        self.assertIn("rumor_bandit_herb_embargo", self.rumors.rumors)
        r_herb = self.rumors.rumors["rumor_bandit_herb_embargo"]
        self.assertEqual(r_herb.origin_npc, "silas")
        self.assertIn("infected wounds", r_herb.true_content)

    def test_embargo_savegame_serialization(self):
        """Tests serialization and restoration of active embargoes in MonopolyManager."""
        self.mm.set_faction_embargo("bandits", "medicinal_herb", True)
        self.mm.set_faction_embargo("knights", "iron_ore", True)

        data = self.mm.to_dict()
        self.assertTrue(data["active_embargoes"]["bandits"]["medicinal_herb"])
        self.assertTrue(data["active_embargoes"]["knights"]["iron_ore"])

        new_mm = MonopolyManager()
        new_mm.from_dict(data)
        self.assertTrue(new_mm.is_faction_embargoed("bandits", "medicinal_herb"))
        self.assertTrue(new_mm.is_faction_embargoed("knights", "iron_ore"))


if __name__ == "__main__":
    unittest.main()
