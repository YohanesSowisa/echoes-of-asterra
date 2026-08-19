"""
Unit tests for Pillar #7: The Living Dungeon Sovereign: Crypt Architect — Phase 4 (Multi-Floor Expansion & Mythos Climax).
Tests subterranean multi-floor excavations (Floor 2: Deep Catacombs, Floor 3: Abyssal Vaults),
title 'The Lord of the Deep Catacombs', Mythos chronicle inscriptions, multi-floor defense rating,
and save/load persistence.
"""
import unittest
from rpg.events import EventBus
from rpg.dungeon_architect import (
    DungeonArchitectManager,
    TRAP_SPIKE,
    TRAP_PORTCULLIS,
    TRAP_MIMIC_CHEST,
    MAX_DUNGEON_FLOORS
)
from rpg.mythos import MythosManager
from rpg.items import create_item
from rpg.inventory import Inventory


class MockPlayer:
    def __init__(self, gold: int = 1000):
        self.gold = gold
        self.titles = set()
        self.inventory = Inventory(size=20)


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.dungeon_architect = DungeonArchitectManager(self.event_bus)
        self.mythos = MythosManager()
        self.mythos.register_event_listeners(self.event_bus)
        self.player = MockPlayer()


class TestDungeonArchitectPhase4(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.da = self.game.dungeon_architect
        self.mythos = self.game.mythos
        self.player = self.game.player
        self.da.claim_dungeon_core(self.player)

    def test_expand_floor_2_requirements(self):
        """Tests unlocking Floor 2 (Deep Catacombs) with gold and infamy requirements."""
        self.player.gold = 500
        self.da.dungeon_infamy = 20  # Insufficient infamy (<50)

        # 1. Infamy gate
        succ1, msg1 = self.da.expand_dungeon_floor(self.player)
        self.assertFalse(succ1)
        self.assertIn("Requires 50 Dungeon Infamy", msg1)

        # 2. Gold gate
        self.da.dungeon_infamy = 50
        self.player.gold = 100  # Insufficient gold (<200g)
        succ2, msg2 = self.da.expand_dungeon_floor(self.player)
        self.assertFalse(succ2)
        self.assertIn("Requires 200 Gold", msg2)

        # 3. Successful excavation
        self.player.gold = 300
        succ3, msg3 = self.da.expand_dungeon_floor(self.player)
        self.assertTrue(succ3)
        self.assertIn("Deep Catacombs", msg3)
        self.assertEqual(self.player.gold, 100)  # 300 - 200
        self.assertEqual(self.da.max_unlocked_floor, 2)
        self.assertEqual(self.da.current_floor, 2)
        self.assertEqual(self.da.get_floor_name(2), "Deep Catacombs")

    def test_expand_floor_3_sovereign_climax(self):
        """Tests unlocking Floor 3 (Abyssal Vaults), prestige title, and Mythos chronicle."""
        # Unlock Floor 2 first
        self.da.dungeon_infamy = 120
        self.player.gold = 1000
        self.da.expand_dungeon_floor(self.player)  # To Floor 2

        # Unlock Floor 3
        succ, msg = self.da.expand_dungeon_floor(self.player)
        self.assertTrue(succ)
        self.assertIn("Abyssal Vaults", msg)
        self.assertEqual(self.da.max_unlocked_floor, 3)
        self.assertEqual(self.da.current_floor, 3)
        self.assertEqual(self.da.get_floor_name(3), "Abyssal Vaults")

        # Verify prestige title awarded
        self.assertIn("The Lord of the Deep Catacombs", self.player.titles)

        # Verify generational Mythos timeline recorded
        mythos_events = [e for e in self.mythos.timeline if e.get("event_type") == "DUNGEON_SOVEREIGNTY_ESTABLISHED"]
        self.assertEqual(len(mythos_events), 1)
        self.assertEqual(mythos_events[0]["actor"], "The Lord of the Deep Catacombs")
        self.assertEqual(mythos_events[0]["target"], "Abyssal Vaults")

        # Max floor capacity reached
        succ_overflow, msg_overflow = self.da.expand_dungeon_floor(self.player)
        self.assertFalse(succ_overflow)
        self.assertIn("already been excavated", msg_overflow)

    def test_switch_floor_and_view(self):
        """Tests navigating architect view between unlocked subterranean floors."""
        self.da.dungeon_infamy = 100
        self.player.gold = 800
        self.da.expand_dungeon_floor(self.player)  # Floor 2 unlocked

        # Switch to Floor 1
        succ1, _ = self.da.switch_floor(1)
        self.assertTrue(succ1)
        self.assertEqual(self.da.current_floor, 1)

        # Switch back to Floor 2
        succ2, _ = self.da.switch_floor(2)
        self.assertTrue(succ2)
        self.assertEqual(self.da.current_floor, 2)

        # Switch to locked Floor 3 -> fails
        succ3, msg3 = self.da.switch_floor(3)
        self.assertFalse(succ3)
        self.assertIn("Floor 3 is not unlocked yet", msg3)

    def test_multi_floor_composite_defense_rating(self):
        """Tests cumulative defense ratings calculated across all excavated floors."""
        self.da.dungeon_infamy = 100
        self.player.gold = 1000
        self.player.inventory.add_item(create_item("Granite Stone", 10))
        self.player.inventory.add_item(create_item("Iron Ore", 10))

        # Floor 1: Spike Trap (35 * 1.15 = 40)
        self.da.place_trap(TRAP_SPIKE, 1, 1, self.player, floor=1)

        # Unlock Floor 2 and place Iron Portcullis (15 * 1.15 = 17)
        self.da.expand_dungeon_floor(self.player)
        self.da.place_trap(TRAP_PORTCULLIS, 2, 2, self.player, floor=2)

        f1_def = self.da.get_dungeon_defense_rating(floor=1)
        f2_def = self.da.get_dungeon_defense_rating(floor=2)
        total_def = self.da.get_total_dungeon_defense_rating()

        self.assertEqual(total_def, f1_def + f2_def)
        self.assertGreater(total_def, f1_def)

    def test_save_and_restore_multi_floor_state(self):
        """Tests serialization and state restoration of multi-floor crypt lairs."""
        self.da.dungeon_infamy = 150
        self.player.gold = 1000
        self.da.expand_dungeon_floor(self.player)  # Floor 2
        self.da.expand_dungeon_floor(self.player)  # Floor 3
        self.da.switch_floor(2)

        data = self.da.to_dict()
        self.assertEqual(data["max_unlocked_floor"], 3)
        self.assertEqual(data["current_floor"], 2)

        new_da = DungeonArchitectManager()
        new_da.from_dict(data)
        self.assertEqual(new_da.max_unlocked_floor, 3)
        self.assertEqual(new_da.current_floor, 2)
        self.assertEqual(new_da.get_floor_name(3), "Abyssal Vaults")


if __name__ == "__main__":
    unittest.main()
