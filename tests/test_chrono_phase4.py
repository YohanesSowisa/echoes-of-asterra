"""
Unit tests for Pillar #8: Chrono-Echoes & Spacetime Fractures — Phase 4 (The Aeon Sentinel & Mythos Climax).
Tests Aeon Sentinel summoning prerequisites, boss stats, Aeon Core loot drop,
prestige title 'Chrono-Weaver Supreme' award, Mythos chronicle inscription, and save/load persistence.
"""
import unittest
import pygame
from rpg.events import EventBus
from rpg.chrono import ChronoManager
from rpg.enemy import AeonSentinel
from rpg.mythos import MythosManager
from rpg.items import create_item
from rpg.inventory import Inventory
from rpg.equipment import Equipment


class MockPlayer:
    def __init__(self, gold: int = 100, hp: float = 100.0, level: int = 1, x: int = 100, y: int = 100):
        self.name = "Astraea"
        self.gold = gold
        self.hp = hp
        self.max_hp = 100.0
        self.base_max_hp = 100.0
        self.mana = 100.0
        self.max_mana = 100.0
        self.base_max_mana = 100.0
        self.stamina = 100.0
        self.max_stamina = 100.0
        self.base_atk = 25.0
        self.atk = 25.0
        self.base_def = 10.0
        self.defense = 10.0
        self.base_magic = 15.0
        self.magic = 15.0
        self.base_speed = 4.0
        self.speed = 4.0
        self.base_crit = 0.05
        self.crit_chance = 0.05
        self.exp = 0
        self.xp = 0
        self.level = level
        self.rect = pygame.Rect(x, y, 32, 32)
        self.inventory = Inventory(size=20)
        self.equipment = Equipment()
        self.game = None

    def gain_xp(self, amount: int):
        self.xp += amount
        self.exp += amount


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.chrono_manager = ChronoManager(self.event_bus)
        self.mythos_manager = MythosManager()
        self.player = MockPlayer()
        self.player.game = self
        self.day = 1
        self.time_of_day = 8.0
        self.current_map_name = "village"
        self.quest_manager = None
        self.defeated_bosses = []
        self.world_flags = {}
        self.ui_sprites = pygame.sprite.Group()
        self.visible_sprites = pygame.sprite.Group()
        self.dropped_items = pygame.sprite.Group()
        self.particles = None


class TestChronoPhase4(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.game = MockGame()
        self.chrono = self.game.chrono_manager
        self.mythos = self.game.mythos_manager
        self.player = self.game.player

    def test_can_summon_aeon_sentinel(self):
        """Tests prerequisites to confront the primordial Aeon Sentinel."""
        # 1. Before any rewinds -> Fails
        succ1, msg1 = self.chrono.can_summon_aeon_sentinel(self.player)
        self.assertFalse(succ1)
        self.assertIn("not disturbed the fabric", msg1)

        # 2. After performing rewind, but without Hourglass in inventory -> Fails
        self.game.day = 1
        self.chrono.record_snapshot(self.game)
        self.game.day = 3
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))
        self.chrono.execute_temporal_rewind(self.game, days_to_rewind=2)

        # Remove hourglass to test rejection
        self.player.inventory.slots = [None] * self.player.inventory.size
        succ2, msg2 = self.chrono.can_summon_aeon_sentinel(self.player)
        self.assertFalse(succ2)
        self.assertIn("Requires the 'Chrono-Weaver Hourglass'", msg2)

        # 3. Add back Hourglass -> Succeeds
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))
        succ3, msg3 = self.chrono.can_summon_aeon_sentinel(self.player)
        self.assertTrue(succ3)
        self.assertIn("Aeon Sentinel awakens", msg3)

    def test_aeon_sentinel_boss_and_stats(self):
        """Tests Aeon Sentinel boss stats, boss flag, and guaranteed loot table."""
        sentinel = AeonSentinel(pos=(200, 200), groups=[], level=10)
        sentinel.game = self.game

        self.assertTrue(sentinel.is_boss)
        self.assertEqual(sentinel.enemy_type, "aeon_sentinel")
        self.assertEqual(sentinel.max_hp, 450.0)
        self.assertEqual(sentinel.hp, 450.0)
        self.assertEqual(sentinel.atk, 38.0)
        self.assertEqual(sentinel.defense, 18.0)
        self.assertEqual(sentinel.loot_table.get("Aeon Core"), 1.0)
        self.assertEqual(sentinel.loot_table.get("Topaz"), 1.0)

    def test_on_aeon_sentinel_defeated_climax(self):
        """Tests slaying Aeon Sentinel, prestige title award, and Aeon Core reward."""
        self.game.day = 1
        self.chrono.record_snapshot(self.game)
        self.game.day = 3
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))
        self.chrono.execute_temporal_rewind(self.game, days_to_rewind=2)

        sentinel = AeonSentinel(pos=(200, 200), groups=[], level=10)
        sentinel.game = self.game

        # Defeat Sentinel
        sentinel.die()

        self.assertTrue(self.chrono.is_sentinel_defeated)
        self.assertEqual(self.chrono.prestige_title, "Chrono-Weaver Supreme")
        self.assertTrue(self.player.inventory.has_item("Aeon Core", 1))
        self.assertFalse(self.chrono.is_temporal_rift_active())

    def test_mythos_chronicle_inscription(self):
        """Tests permanent inscription of TEMPORAL_FABRIC_MENDED in Mythos records."""
        self.chrono.is_sentinel_defeated = True
        self.chrono.prestige_title = "Chrono-Weaver Supreme"
        self.chrono.total_rewinds_performed = 3

        record = self.mythos.record_run(
            game=self.game,
            end_cause="victory"
        )

        # Check events inside record
        temporal_events = [ev for ev in record.get("events", []) if ev.get("event_type") == "TEMPORAL_FABRIC_MENDED"]
        self.assertEqual(len(temporal_events), 1)
        ev = temporal_events[0]
        self.assertEqual(ev["target"], "Aeon Sentinel")
        self.assertEqual(ev["item"], "Aeon Core")
        self.assertIn("Chrono-Weaver Supreme", ev["outcome"])

    def test_save_and_restore_sentinel_state(self):
        """Tests save/load serialization of Aeon Sentinel climax progression."""
        self.chrono.is_sentinel_defeated = True
        self.chrono.prestige_title = "Chrono-Weaver Supreme"
        self.chrono.total_rewinds_performed = 4

        data = self.chrono.to_dict()
        self.assertTrue(data["is_sentinel_defeated"])
        self.assertEqual(data["prestige_title"], "Chrono-Weaver Supreme")

        new_chrono = ChronoManager()
        new_chrono.from_dict(data)
        self.assertTrue(new_chrono.is_sentinel_defeated)
        self.assertEqual(new_chrono.prestige_title, "Chrono-Weaver Supreme")


if __name__ == "__main__":
    unittest.main()
