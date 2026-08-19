"""
Unit tests for Pillar #8: Chrono-Echoes & Spacetime Fractures — Phase 2 (Chrono-Doppelganger Mirror Boss).
Tests Temporal Fracture spawning, player profile/equipment mirroring for the paradox shadow boss,
boss combat stats, anomaly defeat resolution, and save/load persistence.
"""
import unittest
import pygame
from rpg.events import EventBus
from rpg.chrono import ChronoManager
from rpg.enemy import ChronoDoppelganger
from rpg.items import create_item
from rpg.inventory import Inventory
from rpg.equipment import Equipment


class MockPlayer:
    def __init__(self, gold: int = 100, hp: float = 100.0, level: int = 1, x: int = 100, y: int = 100):
        self.gold = gold
        self.hp = hp
        self.max_hp = 100.0
        self.base_max_hp = 100.0
        self.mana = 100.0
        self.max_mana = 100.0
        self.base_max_mana = 100.0
        self.stamina = 100.0
        self.max_stamina = 100.0
        self.base_atk = 24.0
        self.atk = 24.0
        self.base_def = 5.0
        self.defense = 5.0
        self.base_magic = 10.0
        self.magic = 10.0
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

    def gain_xp(self, amount: int):
        self.xp += amount
        self.exp += amount

    def add_exp(self, amount: int):
        self.gain_xp(amount)


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.chrono_manager = ChronoManager(self.event_bus)
        self.player = MockPlayer()
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


class TestChronoPhase2(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.game = MockGame()
        self.chrono = self.game.chrono_manager
        self.player = self.game.player

    def test_temporal_fracture_spawned_on_rewind(self):
        """Tests that rewinding time leaves a Temporal Fracture at pre-rewind coordinates."""
        # Day 1 Snapshot
        self.game.day = 1
        self.chrono.record_snapshot(self.game)

        # Advance to Day 3 at specific position
        self.game.day = 3
        self.player.rect.x, self.player.rect.y = 350, 420
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))

        succ, msg, _ = self.chrono.execute_temporal_rewind(self.game, days_to_rewind=2)
        self.assertTrue(succ)
        self.assertIn("Paradox Chrono-Doppelganger has manifested", msg)

        # Check Temporal Fracture
        self.assertEqual(len(self.chrono.active_fractures), 1)
        fracture = self.chrono.active_fractures[0]
        self.assertEqual(fracture.pos, (350.0, 420.0))
        self.assertEqual(fracture.map_name, "village")
        self.assertEqual(fracture.created_day, 3)

    def test_chrono_doppelganger_mirrors_player(self):
        """Tests that the Chrono-Doppelganger accurately mirrors player weapon, armor, and stats."""
        # Day 1 Snapshot
        self.game.day = 1
        self.chrono.record_snapshot(self.game)

        # Advance to Day 4 with custom weapon and armor
        self.game.day = 4
        self.player.level = 5
        self.player.max_hp = 120.0
        self.player.base_atk = 32.0
        self.player.rect.x, self.player.rect.y = 200, 300

        scythe = create_item("Voidbrand Scythe", 1)
        chest = create_item("Leather Chest", 1)
        self.player.equipment.equip(scythe, self.player)
        self.player.equipment.equip(chest, self.player)

        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))

        succ, _, _ = self.chrono.execute_temporal_rewind(self.game, days_to_rewind=3)
        self.assertTrue(succ)

        dop = self.chrono.active_doppelganger
        self.assertIsNotNone(dop)
        self.assertEqual(dop.level, 5)
        self.assertEqual(dop.atk, 32.0)
        self.assertEqual(dop.hp, 150.0)  # 100.0 max_hp * 1.5
        self.assertEqual(dop.equipped_weapon, "Voidbrand Scythe")
        self.assertEqual(dop.equipped_armor, "Leather Chest")
        self.assertEqual(dop.pos, (200.0, 300.0))
        self.assertTrue(dop.is_active)

    def test_chrono_doppelganger_enemy_class(self):
        """Tests ChronoDoppelganger boss enemy instantiation and defeat resolution."""
        # Setup active anomaly
        self.game.day = 1
        self.chrono.record_snapshot(self.game)
        self.game.day = 3
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))
        self.chrono.execute_temporal_rewind(self.game, days_to_rewind=2)

        # Create enemy instance
        dop_profile = self.chrono.active_doppelganger
        boss = ChronoDoppelganger(
            pos=dop_profile.pos,
            groups=[],
            level=dop_profile.level,
            max_hp=dop_profile.max_hp,
            atk=dop_profile.atk,
            weapon_name=dop_profile.equipped_weapon,
            armor_name=dop_profile.equipped_armor
        )
        boss.game = self.game

        self.assertTrue(boss.is_boss)
        self.assertEqual(boss.enemy_type, "chrono_doppelganger")
        self.assertEqual(boss.hp, dop_profile.max_hp)

        # Defeat the boss
        boss.die()
        self.assertFalse(self.chrono.active_doppelganger.is_active)
        self.assertEqual(len(self.chrono.active_fractures), 0)

    def test_save_and_restore_fracture_and_doppelganger(self):
        """Tests serialization and state restoration of active fractures and doppelganger profiles."""
        self.game.day = 1
        self.chrono.record_snapshot(self.game)
        self.game.day = 3
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))
        self.chrono.execute_temporal_rewind(self.game, days_to_rewind=2)

        data = self.chrono.to_dict()
        self.assertEqual(len(data["active_fractures"]), 1)
        self.assertIsNotNone(data["active_doppelganger"])

        new_chrono = ChronoManager()
        new_chrono.from_dict(data)
        self.assertEqual(len(new_chrono.active_fractures), 1)
        self.assertEqual(new_chrono.active_fractures[0].created_day, 3)
        self.assertIsNotNone(new_chrono.active_doppelganger)
        self.assertTrue(new_chrono.active_doppelganger.is_active)


if __name__ == "__main__":
    unittest.main()
