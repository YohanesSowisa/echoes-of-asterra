"""
Unit tests for Pillar #7: The Living Dungeon Sovereign: Crypt Architect — Phase 3 (Raider Invasions & Defense Simulation).
Tests periodic 3-day deterministic raider assaults, defense simulation victories and breaches,
gold/infamy/material rewards, Nemesis warband branding, and save/load persistence.
"""
import unittest
from rpg.events import EventBus
from rpg.dungeon_architect import (
    DungeonArchitectManager,
    TRAP_SPIKE,
    TRAP_PORTCULLIS,
    TRAP_MIMIC_CHEST
)
from rpg.items import create_item
from rpg.inventory import Inventory


class MockPlayer:
    def __init__(self, gold: int = 200):
        self.gold = gold
        self.titles = set()
        self.inventory = Inventory(size=20)


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.dungeon_architect = DungeonArchitectManager(self.event_bus)
        self.player = MockPlayer()


class TestDungeonArchitectPhase3(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.da = self.game.dungeon_architect
        self.player = self.game.player
        self.da.claim_dungeon_core(self.player)

    def test_periodic_3_day_invasion_triggers(self):
        """Tests deterministic 3-day interval triggering of AI adventurer raiding parties."""
        # Day 1 & 2: No invasion
        self.assertIsNone(self.da.trigger_daily_invasion(day=1))
        self.assertIsNone(self.da.trigger_daily_invasion(day=2))

        # Day 3: Triggers invasion
        inv3 = self.da.trigger_daily_invasion(day=3)
        self.assertIsNotNone(inv3)
        self.assertEqual(inv3["day"], 3)
        self.assertEqual(inv3["raider_power"], 90)  # 60 + 3*10
        self.assertEqual(inv3["raider_count"], 4)   # 3 + 3//3
        self.assertEqual(self.da.last_invasion_day, 3)

        # Day 4 & 5: Cooldown active -> no new invasion
        self.assertIsNone(self.da.trigger_daily_invasion(day=4))
        self.assertIsNone(self.da.trigger_daily_invasion(day=5))

        # Day 6: Triggers next 3-day wave
        inv6 = self.da.trigger_daily_invasion(day=6)
        self.assertIsNotNone(inv6)
        self.assertEqual(inv6["day"], 6)
        self.assertEqual(inv6["raider_power"], 120)  # 60 + 6*10

    def test_simulate_defense_victory(self):
        """Tests successful defense simulation when traps + guardians >= raider power."""
        # 1. Fortify dungeon (Spike + Mimic Chest + Portcullis)
        self.player.gold = 500
        self.player.inventory.add_item(create_item("Granite Stone", 4))
        self.player.inventory.add_item(create_item("Iron Ore", 4))
        self.player.inventory.add_item(create_item("Luminescent Spore", 2))

        self.da.place_trap(TRAP_SPIKE, 1, 1, self.player)
        self.da.place_trap(TRAP_PORTCULLIS, 2, 2, self.player)
        self.da.place_trap(TRAP_MIMIC_CHEST, 3, 3, self.player)
        # Defense rating: (35+15+60) * (1.0 + 3*0.15) = 110 * 1.45 = 159

        # Trigger Day 3 invasion (power = 90, bounty = 75)
        self.da.trigger_daily_invasion(day=3)
        self.assertIsNotNone(self.da.active_invasion)

        self.player.gold = 100
        succ, msg, data = self.da.simulate_invasion_defense(self.player, floor=1)
        self.assertTrue(succ)
        self.assertIn("Dungeon defenses held", msg)
        self.assertEqual(self.player.gold, 175)  # 100 + 75
        self.assertEqual(self.da.dungeon_infamy, 30)
        self.assertEqual(self.da.total_invasions_repelled, 1)
        self.assertIsNone(self.da.active_invasion)

        # Verified material salvage added to player inventory
        self.assertTrue(self.player.inventory.has_item("Iron Ore", 2))
        self.assertTrue(self.player.inventory.has_item("Timber", 2))
        self.assertTrue(self.player.inventory.has_item("Beast Leather", 2))

    def test_simulate_defense_breached(self):
        """Tests breached defense simulation when dungeon defense < raider power."""
        # Weak defense (no traps placed -> defense = 0)
        self.assertEqual(self.da.get_dungeon_defense_rating(floor=1), 0)

        # Trigger Day 3 invasion (power = 90)
        self.da.trigger_daily_invasion(day=3)

        self.player.gold = 100
        succ, msg, data = self.da.simulate_invasion_defense(self.player, floor=1)
        self.assertFalse(succ)
        self.assertIn("Defenses breached", msg)
        self.assertEqual(self.player.gold, 80)  # 100 - 20 (plundered)
        self.assertEqual(self.da.total_invasions_failed, 1)
        self.assertIsNone(self.da.active_invasion)

    def test_nemesis_warband_invasion_naming(self):
        """Tests branding the raiding party under an active Nemesis banner."""
        inv = self.da.trigger_daily_invasion(day=3, nemesis_name="Grimclaw the Executioner")
        self.assertIsNotNone(inv)
        self.assertEqual(inv["raider_name"], "Nemesis Warband of Grimclaw the Executioner")
        self.assertEqual(inv["raider_type"], "Nemesis Outlaws")

    def test_save_and_restore_invasion_state(self):
        """Tests serialization and restoration of invasion progress and dungeon infamy."""
        self.da.trigger_daily_invasion(day=3)
        self.da.dungeon_infamy = 90
        self.da.total_invasions_repelled = 3
        self.da.total_invasions_failed = 1

        data = self.da.to_dict()
        self.assertEqual(data["last_invasion_day"], 3)
        self.assertEqual(data["dungeon_infamy"], 90)
        self.assertEqual(data["total_invasions_repelled"], 3)
        self.assertEqual(data["total_invasions_failed"], 1)

        new_da = DungeonArchitectManager()
        new_da.from_dict(data)
        self.assertEqual(new_da.last_invasion_day, 3)
        self.assertEqual(new_da.dungeon_infamy, 90)
        self.assertEqual(new_da.total_invasions_repelled, 3)
        self.assertEqual(new_da.total_invasions_failed, 1)


if __name__ == "__main__":
    unittest.main()
