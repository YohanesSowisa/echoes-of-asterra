"""
Unit tests for Pillar #8: Chrono-Echoes & Spacetime Fractures — Phase 1 (3-Day Atomic Rewind Engine).
Tests rolling 3-day timeline snapshot recording, Chrono-Weaver Hourglass validation,
atomic world/inventory rollback, event bus notifications, and save/load persistence.
"""
import unittest
import pygame
from rpg.events import EventBus
from rpg.chrono import ChronoManager, MAX_ROLLING_DAYS
from rpg.items import create_item
from rpg.inventory import Inventory


class MockPlayer:
    def __init__(self, gold: int = 100, hp: float = 100.0, level: int = 1, x: int = 100, y: int = 100):
        self.gold = gold
        self.hp = hp
        self.max_hp = 100.0
        self.stamina = 100.0
        self.max_stamina = 100.0
        self.exp = 0
        self.level = level
        self.rect = pygame.Rect(x, y, 32, 32)
        self.inventory = Inventory(size=20)
        self.equipment = None


class MockQuestManager:
    def __init__(self):
        self.quest_status = {"quest_1": "in_progress"}

    def to_dict(self):
        return dict(self.quest_status)

    def from_dict(self, data):
        self.quest_status = dict(data)


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.chrono_manager = ChronoManager(self.event_bus)
        self.player = MockPlayer()
        self.day = 1
        self.time_of_day = 8.0
        self.current_map_name = "village"
        self.quest_manager = MockQuestManager()
        self.defeated_bosses = []
        self.world_flags = {"flag_village_cleared": False}


class TestChronoPhase1(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.game = MockGame()
        self.chrono = self.game.chrono_manager
        self.player = self.game.player

    def test_record_snapshots_and_ring_buffer(self):
        """Tests recording daily atomic snapshots and maintaining a 3-day rolling ring buffer."""
        # Day 1
        self.game.day = 1
        self.player.gold = 100
        self.chrono.record_snapshot(self.game)
        self.assertEqual(len(self.chrono.history), 1)
        self.assertEqual(self.chrono.history[0].day, 1)

        # Day 2
        self.game.day = 2
        self.player.gold = 200
        self.chrono.record_snapshot(self.game)
        self.assertEqual(len(self.chrono.history), 2)

        # Day 3
        self.game.day = 3
        self.player.gold = 300
        self.chrono.record_snapshot(self.game)
        self.assertEqual(len(self.chrono.history), 3)

        # Day 4: Should discard Day 1, keeping [Day 2, Day 3, Day 4]
        self.game.day = 4
        self.player.gold = 400
        self.chrono.record_snapshot(self.game)
        self.assertEqual(len(self.chrono.history), MAX_ROLLING_DAYS)
        self.assertEqual([s.day for s in self.chrono.history], [2, 3, 4])
        self.assertEqual([s.player_gold for s in self.chrono.history], [200, 300, 400])

    def test_can_rewind_validation(self):
        """Tests validation requirements: non-empty history and Chrono-Weaver Hourglass possession."""
        # 1. Empty history -> fails
        succ1, msg1 = self.chrono.can_rewind(self.player)
        self.assertFalse(succ1)
        self.assertIn("No timeline snapshots", msg1)

        # 2. Record snapshot, but no Hourglass in inventory -> fails
        self.chrono.record_snapshot(self.game)
        succ2, msg2 = self.chrono.can_rewind(self.player)
        self.assertFalse(succ2)
        self.assertIn("Requires the 'Chrono-Weaver Hourglass'", msg2)

        # 3. Add Chrono-Weaver Hourglass -> succeeds
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))
        succ3, msg3 = self.chrono.can_rewind(self.player)
        self.assertTrue(succ3)
        self.assertIn("radiates temporal energy", msg3)

    def test_execute_temporal_rewind_success(self):
        """Tests complete atomic rollback of player, inventory, world state, and day counters."""
        # 1. Day 1 Baseline State
        self.game.day = 1
        self.player.gold = 100
        self.player.level = 1
        self.player.rect.x, self.player.rect.y = 120, 150
        self.player.inventory.add_item(create_item("Iron Ore", 5))
        self.chrono.record_snapshot(self.game)

        # 2. Advance to Day 4 (Player modifies inventory, gold, level, quests, flags)
        self.game.day = 2
        self.chrono.record_snapshot(self.game)
        self.game.day = 3
        self.chrono.record_snapshot(self.game)

        self.game.day = 4
        self.player.gold = 999
        self.player.level = 5
        self.player.rect.x, self.player.rect.y = 500, 600
        self.player.inventory.slots = [None] * self.player.inventory.size
        self.player.inventory.add_item(create_item("Titan Cragcleaver", 1))
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))
        self.game.world_flags["flag_village_cleared"] = True
        self.game.quest_manager.quest_status["quest_1"] = "completed"

        # 3. Execute 3-day temporal rewind
        succ, msg, snap = self.chrono.execute_temporal_rewind(self.game, days_to_rewind=3)
        self.assertTrue(succ)
        self.assertIn("Temporal fracture unleashed", msg)

        # 4. Verify Atomic Rollback
        self.assertEqual(self.game.day, 1)
        self.assertEqual(self.player.gold, 100)
        self.assertEqual(self.player.level, 1)
        self.assertEqual(self.player.rect.x, 120)
        self.assertEqual(self.player.rect.y, 150)
        self.assertTrue(self.player.inventory.has_item("Iron Ore", 5))
        self.assertFalse(self.player.inventory.has_item("Titan Cragcleaver", 1))
        self.assertFalse(self.game.world_flags["flag_village_cleared"])
        self.assertEqual(self.game.quest_manager.quest_status["quest_1"], "in_progress")
        self.assertEqual(self.chrono.total_rewinds_performed, 1)
        self.assertEqual(self.chrono.total_days_rewound, 3)
        self.assertEqual(self.chrono.last_rewind_day, 1)

    def test_event_bus_emission(self):
        """Tests EventBus notifications for snapshot recording and timeline rewinds."""
        events_emitted = []
        self.game.event_bus.subscribe("chrono_snapshot_recorded", lambda **kw: events_emitted.append(("recorded", kw)))
        self.game.event_bus.subscribe("timeline_rewound", lambda **kw: events_emitted.append(("rewound", kw)))

        self.chrono.record_snapshot(self.game)
        self.assertEqual(len(events_emitted), 1)
        self.assertEqual(events_emitted[0][0], "recorded")

        self.game.day = 3
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))
        self.chrono.execute_temporal_rewind(self.game, days_to_rewind=2)

        self.assertEqual(len(events_emitted), 2)
        self.assertEqual(events_emitted[1][0], "rewound")

    def test_save_and_restore_chrono_state(self):
        """Tests serialization and restoration of ChronoManager state."""
        self.chrono.record_snapshot(self.game)
        self.chrono.total_rewinds_performed = 2
        self.chrono.total_days_rewound = 6
        self.chrono.last_rewind_day = 1

        data = self.chrono.to_dict()
        self.assertEqual(data["total_rewinds_performed"], 2)
        self.assertEqual(data["total_days_rewound"], 6)
        self.assertEqual(data["last_rewind_day"], 1)
        self.assertEqual(len(data["history"]), 1)

        new_chrono = ChronoManager()
        new_chrono.from_dict(data)
        self.assertEqual(new_chrono.total_rewinds_performed, 2)
        self.assertEqual(new_chrono.total_days_rewound, 6)
        self.assertEqual(new_chrono.last_rewind_day, 1)
        self.assertEqual(len(new_chrono.history), 1)
        self.assertEqual(new_chrono.history[0].day, 1)


if __name__ == "__main__":
    unittest.main()
