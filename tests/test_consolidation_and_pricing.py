"""
Echoes of Asterra - Unit Tests for Module Consolidation & Silas Pricing (Phase 2)
Tests:
1. Factions as Single Source of Truth for Faction Warfare.
2. Mythos and MythosReader unified schema and data sharing.
3. calculate_final_price() safety bounds:
   - Extreme discounts (reputation 100 + settlement max + trade spec + friend) clamped >= 0.30x.
   - Extreme markups (hostile reputation + tax + scarcity) clamped <= 3.00x.
   - Guaranteed >= 1 Gold and non-negative integer pricing.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((64, 64))

from rpg.events import EventBus
from rpg.factions import FactionManager, FACTION_KNIGHTS, FACTION_BANDITS
from rpg.faction_war import FactionWarManager
from rpg.mythos import MythosManager
from rpg.mythos_reader import MythosReader
from rpg.living_world import LivingWorldManager
from rpg.settlement import SPECIALIZATION_TRADE


class TestConsolidationAndPricing(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.faction_manager = FactionManager()
        self.faction_war = FactionWarManager()
        self.faction_war.faction_manager = self.faction_manager
        self.faction_war.register_event_listeners(self.event_bus)

        self.living_world = LivingWorldManager(self.event_bus)
        self.living_world.faction_war = self.faction_war

    def test_factions_single_source_of_truth_for_war(self):
        """FactionWar must read reputation exclusively from FactionManager without duplicating state."""
        self.faction_manager.modify_reputation(FACTION_KNIGHTS, 50)  # Exalted 60 rep
        self.assertEqual(self.faction_war.faction_manager.get_reputation(FACTION_KNIGHTS), 60)

        # Trigger day change skirmish
        self.event_bus.emit("day_changed", day=2)
        # Knights should strongly hold or capture forest_crossroads due to exalted reputation
        cp = self.faction_war.control_points["forest_crossroads"]
        self.assertEqual(cp.controlling_faction, FACTION_KNIGHTS)

    def test_calculate_final_price_extreme_discount_clamped(self):
        """Extreme discounts must be clamped to 0.30x minimum multiplier and >= 1 Gold."""
        # 1. Trade Consortium max reputation (100)
        self.living_world.settlement.add_prosperity(100.0)  # Max Tier (40% discount)
        self.living_world.settlement.specialization = SPECIALIZATION_TRADE  # Extra 15% discount
        
        # Base price 100g with extreme discounts
        final_price = self.living_world.calculate_final_price(
            base_price=100,
            category="goods",
            map_name="village",
            merchant_reputation=100.0,
            friendship_tier=100.0,
            is_scarce=False
        )
        
        # 100g * 0.442 = 44g
        self.assertGreaterEqual(final_price, 30)
        self.assertLessEqual(final_price, 45)

        # 2. Maximum possible combined discounts:
        # - High stock economy (0.6x)
        # - Silas market investment (-20%) + Max Tier (-20%) + Trade Spec (-15%) -> clamped to -40% total
        # - Trade Consortium exalted rep (-20%)
        # - Close friend bond (-15%)
        # Raw multiplier = 0.60 * (1 - 0.40) * 0.80 * 0.85 = 0.2448 -> strictly clamped to 0.30x (30g)
        self.living_world.settlement.growth_tier = 3
        self.living_world.economy.stocks["goods"].current_stock = self.living_world.economy.stocks["goods"].max_capacity
        deflated_price = self.living_world.calculate_final_price(
            base_price=100,
            category="goods",
            map_name="village",
            merchant_reputation=100.0,
            friendship_tier=100.0,
            is_scarce=False
        )
        self.assertEqual(deflated_price, 30)  # Exactly 0.30x clamp

        # Base price 1g item should still cost at least 1g
        cheap_price = self.living_world.calculate_final_price(
            base_price=1,
            category="goods",
            map_name="village",
            merchant_reputation=100.0,
            friendship_tier=100.0,
            is_scarce=False
        )
        self.assertEqual(cheap_price, 1)

    def test_calculate_final_price_extreme_markup_clamped(self):
        """Extreme markups (Hostile + High Taxes + Extreme Scarcity) must be clamped <= 3.00x."""
        # Force bandit control in forest (adds tax)
        self.faction_war.control_points["forest_crossroads"].controlling_faction = FACTION_BANDITS

        final_price = self.living_world.calculate_final_price(
            base_price=100,
            category="goods",
            map_name="forest",
            merchant_reputation=-100.0,  # Hostile -100
            friendship_tier=0.0,
            is_scarce=True  # 1.35x scarcity badge
        )

        # 100g * 3.00 max clamp = 300g
        self.assertLessEqual(final_price, 300)
        self.assertGreaterEqual(final_price, 120)

    def test_mythos_and_reader_unified_schema_sharing(self):
        """MythosManager and MythosReader must share the exact same schema structure."""
        mm = MythosManager()
        mm.records = []  # Clean test state

        class DummyPlayer:
            def __init__(self):
                self.name = "Galahad"
                self.level = 10
                self.atk = 30
                self.defense = 20
                from rpg.equipment import Equipment
                self.equipment = Equipment()

        class DummyGame:
            def __init__(self):
                self.player = DummyPlayer()
                self.mythos_manager = mm

        game = DummyGame()
        record = mm.record_run(game, end_cause="Vanquished Shadow")
        self.assertIsNotNone(record)

        reader = MythosReader(game)
        artifacts = reader.get_ancestral_artifacts()
        self.assertGreaterEqual(len(artifacts), 1)
        self.assertTrue(any("Galahad" in a[0] or "Ancestral" in a[0] for a in artifacts))


if __name__ == "__main__":
    unittest.main()
