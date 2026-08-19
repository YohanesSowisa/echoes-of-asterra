"""
Unit tests for Pillar #1: The Sunken Mire & Ancient Leylines Subsystem.
Validates dynamic tide cycles (High/Low/Rising/Falling), water level calculations,
movement speed penalties, marsh toxicity & hazards, Leyline channeling,
fast-travel mechanics, mire purification fields, and save schema v7 migration.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.constants import (
    MAP_SUNKEN_MIRE,
    MAP_VILLAGE,
    MAP_LAKE,
    MAP_FOREST,
    TIDE_LOW,
    TIDE_RISING,
    TIDE_HIGH,
    TIDE_FALLING
)
from rpg.sunken_mire import MireManager
from rpg.leylines import LeylineManager, LeylineNode
from rpg.enemy import MireLurker, BogLeech
from rpg.map_loader import MapGenerator
from rpg.save import migrate_save, SAVE_SCHEMA_VERSION


class MockPlayer:
    def __init__(self):
        self.pos = pygame.math.Vector2(480, 280)
        self.rect = pygame.Rect(480, 280, 32, 32)
        self.hitbox = pygame.Rect(484, 288, 24, 20)
        self.mana = 50
        self.max_mana = 50
        self.level = 3
        self.speed = 4.0
        self.game = None


class MockWorldManager:
    def __init__(self):
        self.current_map = MAP_SUNKEN_MIRE
        self.current_map_name = MAP_SUNKEN_MIRE
        self.spawn_pos = None

    def change_map(self, target_map: str, spawn_pos: Any = None):
        self.current_map = target_map
        self.current_map_name = target_map
        self.spawn_pos = spawn_pos


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.mire_manager = MireManager(self.event_bus)
        self.mire_manager.game_reference = self
        self.leyline_manager = LeylineManager(self.event_bus)
        self.world_manager = MockWorldManager()
        self.player = MockPlayer()
        self.player.game = self
        self.ui_sprites = []


class TestSunkenMireAndLeylines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.mire_mgr = self.game.mire_manager
        self.leyline_mgr = self.game.leyline_manager
        self.player = self.game.player

    def test_tide_cycle_transitions(self):
        """Validates that tide phase and water level update based on in-game time."""
        # 03:00 -> Peak High Tide (water_level = 1.0)
        self.mire_mgr.update(1.0, 3.0)
        self.assertEqual(self.mire_mgr.tide_phase, TIDE_HIGH)
        self.assertEqual(self.mire_mgr.water_level, 1.0)

        # 07:30 -> Falling Tide (water_level = 0.5)
        self.mire_mgr.update(1.0, 7.5)
        self.assertEqual(self.mire_mgr.tide_phase, TIDE_FALLING)
        self.assertAlmostEqual(self.mire_mgr.water_level, 0.5, places=2)

        # 12:00 -> Low Tide (water_level = 0.0)
        self.mire_mgr.update(1.0, 12.0)
        self.assertEqual(self.mire_mgr.tide_phase, TIDE_LOW)
        self.assertEqual(self.mire_mgr.water_level, 0.0)

        # 16:30 -> Rising Tide (water_level = 0.5)
        self.mire_mgr.update(1.0, 16.5)
        self.assertEqual(self.mire_mgr.tide_phase, TIDE_RISING)
        self.assertAlmostEqual(self.mire_mgr.water_level, 0.5, places=2)

        # 21:00 -> High Tide (water_level = 1.0)
        self.mire_mgr.update(1.0, 21.0)
        self.assertEqual(self.mire_mgr.tide_phase, TIDE_HIGH)
        self.assertEqual(self.mire_mgr.water_level, 1.0)

    def test_high_tide_movement_slow(self):
        """Verifies movement speed penalty applies during high tide in Sunken Mire."""
        # Low Tide in Mire -> 1.0x speed
        self.mire_mgr.water_level = 0.0
        self.assertEqual(self.mire_mgr.get_speed_multiplier(MAP_SUNKEN_MIRE, is_in_water=True), 1.0)

        # High Tide in Mire -> 0.75x speed (25% reduction)
        self.mire_mgr.water_level = 1.0
        self.assertEqual(self.mire_mgr.get_speed_multiplier(MAP_SUNKEN_MIRE, is_in_water=True), 0.75)

        # High Tide in Village -> 1.0x speed (no penalty outside mire)
        self.assertEqual(self.mire_mgr.get_speed_multiplier(MAP_VILLAGE, is_in_water=True), 1.0)

    def test_mire_water_toxicity(self):
        """Verifies toxicity is triggered only during high tide in the Mire."""
        self.mire_mgr.water_level = 0.2
        self.assertFalse(self.mire_mgr.is_toxic_water(100, 100, MAP_SUNKEN_MIRE))

        self.mire_mgr.water_level = 0.85
        self.assertTrue(self.mire_mgr.is_toxic_water(100, 100, MAP_SUNKEN_MIRE))
        self.assertFalse(self.mire_mgr.is_toxic_water(100, 100, MAP_VILLAGE))

    def test_leyline_channeling_and_activation(self):
        """Tests channeling player mana to activate dormant Leyline conduits."""
        node = self.leyline_mgr.nodes.get("mire_confluence")
        self.assertIsNotNone(node)
        self.assertFalse(node.is_activated)

        # Channel with 50 mana -> 10 deducted, activated = True
        self.player.mana = 50
        succ, msg = self.leyline_mgr.channel_node("mire_confluence", self.player)
        self.assertTrue(succ)
        self.assertEqual(self.player.mana, 40)
        self.assertTrue(node.is_activated)

        # Channel already active node -> fails without deducting mana
        succ2, msg2 = self.leyline_mgr.channel_node("mire_confluence", self.player)
        self.assertFalse(succ2)
        self.assertEqual(self.player.mana, 40)

    def test_leyline_fast_travel(self):
        """Tests query and teleportation between activated Leyline nodes."""
        # Village is activated by default
        self.assertTrue(self.leyline_mgr.nodes["village_grove"].is_activated)
        self.leyline_mgr.nodes["mire_confluence"].is_activated = True

        # When in Mire, destination list should contain Village
        destinations = self.leyline_mgr.get_fast_travel_destinations(MAP_SUNKEN_MIRE)
        dest_ids = [d.node_id for d in destinations]
        self.assertIn("village_grove", dest_ids)
        self.assertNotIn("mire_confluence", dest_ids)

        # Teleport to Village
        succ, msg = self.leyline_mgr.fast_travel(self.player, "village_grove", self.game.world_manager)
        self.assertTrue(succ)
        self.assertEqual(self.game.world_manager.current_map, MAP_VILLAGE)

    def test_leyline_mire_purification(self):
        """Verifies active Mire Leyline node dispels water toxicity and tide slow within its aura."""
        node = self.leyline_mgr.nodes["mire_confluence"]
        node.is_activated = True
        node_x, node_y = node.pos

        # High tide peak
        self.mire_mgr.water_level = 1.0

        # Position right beside node -> purified
        self.player.pos = pygame.math.Vector2(node_x + 10, node_y + 10)
        self.assertTrue(self.leyline_mgr.is_position_purified(self.player.pos.x, self.player.pos.y, MAP_SUNKEN_MIRE))
        self.assertFalse(self.mire_mgr.is_toxic_water(self.player.pos.x, self.player.pos.y, MAP_SUNKEN_MIRE))
        self.assertEqual(self.mire_mgr.get_speed_multiplier(MAP_SUNKEN_MIRE, is_in_water=True), 1.0)

        # Position far from node (800px away) -> not purified
        far_x, far_y = node_x + 800, node_y + 800
        self.assertFalse(self.leyline_mgr.is_position_purified(far_x, far_y, MAP_SUNKEN_MIRE))
        self.assertTrue(self.mire_mgr.is_toxic_water(far_x, far_y, MAP_SUNKEN_MIRE))

    def test_mire_enemy_classes(self):
        """Tests MireLurker and BogLeech stats and loot rewards."""
        group = pygame.sprite.Group()
        lurker = MireLurker((100, 100), [group])
        self.assertEqual(lurker.name, "Mire Lurker")
        self.assertEqual(lurker.hp, 65)
        self.assertIn("Mire Reed", lurker.loot_table)

        leech = BogLeech((150, 150), [group])
        self.assertEqual(leech.name, "Bog Leech")
        self.assertEqual(leech.hp, 35)
        self.assertIn("Leech Mucus", leech.loot_table)

    def test_sunken_mire_map_generation(self):
        """Validates procedural layout for MAP_SUNKEN_MIRE."""
        map_data = MapGenerator.generate(MAP_SUNKEN_MIRE)
        self.assertIsNotNone(map_data)
        self.assertIn("grid", map_data)
        self.assertIn("enemies", map_data)
        self.assertIn("chests", map_data)
        self.assertIn("portals", map_data)
        self.assertGreater(len(map_data["enemies"]), 0)
        self.assertGreater(len(map_data["chests"]), 0)

        # Verify lake has portal to sunken_mire
        lake_data = MapGenerator.generate(MAP_LAKE)
        target_maps = [p["target_map"] for p in lake_data["portals"]]
        self.assertIn(MAP_SUNKEN_MIRE, target_maps)

    def test_save_schema_v7_migration(self):
        """Verifies v6 save files automatically upgrade to v7 with mire and leyline states."""
        legacy_v6_payload = {
            "save_schema_version": 6,
            "player": {"level": 5, "gold": 250},
            "quests": {},
            "world": {},
            "pacts": {"active_pact_id": "void", "pact_tier": 2}
        }
        migrated = migrate_save(legacy_v6_payload)
        self.assertEqual(migrated["save_schema_version"], SAVE_SCHEMA_VERSION)
        self.assertEqual(migrated["save_schema_version"], 7)
        self.assertIn("sunken_mire", migrated)
        self.assertIn("leylines", migrated)
        self.assertEqual(migrated["sunken_mire"]["tide_phase"], "low")


if __name__ == "__main__":
    unittest.main()
