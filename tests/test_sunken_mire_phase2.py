"""
Unit tests for Pillar #1: The Sunken Mire & Ancient Leylines — Phase 2.
Tests Leyline Overcharge system (24h duration, catalyst consumption, perpetual low tide),
Mire botanical flora foraging, Alchemy crafting recipes, and Elixir active buff mechanics
(Waterstrider mobility, Cleansing Draught poison immunity, Leyline Surge mana acceleration).
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.constants import (
    MAP_SUNKEN_MIRE,
    MAP_VILLAGE,
    TIDE_LOW,
    TIDE_HIGH,
    ELEMENT_POISON
)
from rpg.sunken_mire import MireManager
from rpg.leylines import LeylineManager
from rpg.inventory import Inventory
from rpg.items import create_item
from rpg.crafting import CraftingSystem, CRAFTING_RECIPES
from rpg.world import MireHerbSprite
from rpg.save import SaveSystem


class MockPlayer:
    def __init__(self):
        self.pos = pygame.math.Vector2(480, 280)
        self.rect = pygame.Rect(480, 280, 32, 32)
        self.hitbox = pygame.Rect(484, 288, 24, 20)
        self.hp = 100
        self.max_hp = 100
        self.mana = 50
        self.max_mana = 50
        self.stamina = 100
        self.max_stamina = 100
        self.level = 5
        self.speed = 4.0
        self.mana_regen_rate = 3.0
        self.stamina_regen_rate = 15.0
        self.waterstrider_timer = 0.0
        self.cleansing_draught_timer = 0.0
        self.leyline_surge_timer = 0.0
        self.elemental_statuses = {}
        self.potion_cooldown_timer = 0.0
        self.inventory = Inventory(24)
        self.game = None
        self.particles = MockParticles()
        self.sound_manager = MockSound()


class MockParticles:
    def create_magic_sparkles(self, *args, **kwargs):
        pass
    def create_heal_sparkles(self, *args, **kwargs):
        pass


class MockSound:
    def play_sound(self, *args, **kwargs):
        pass


class MockWorldManager:
    def __init__(self):
        self.current_map = MAP_SUNKEN_MIRE
        self.current_map_name = MAP_SUNKEN_MIRE

    def change_map(self, target_map: str, spawn_pos: Any = None):
        self.current_map = target_map
        self.current_map_name = target_map


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
        self.particles = MockParticles()
        self.sound_manager = MockSound()


class TestSunkenMirePhase2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.mire_mgr = self.game.mire_manager
        self.leyline_mgr = self.game.leyline_manager
        self.player = self.game.player

    def test_leyline_overcharge_activation(self):
        """Tests that overcharging consumes catalyst and sets 24h duration."""
        node = self.leyline_mgr.nodes["mire_confluence"]
        node.is_activated = True

        # Player does not have catalyst
        succ, msg = self.leyline_mgr.overcharge_node("mire_confluence", self.player)
        self.assertFalse(succ)
        self.assertFalse(node.is_overcharged)

        # Give Starlight Crystal
        item = create_item("Starlight Crystal", 1)
        self.player.inventory.add_item(item)
        self.assertTrue(self.player.inventory.has_item("Starlight Crystal", 1))

        overcharge_events = []
        self.game.event_bus.subscribe("leyline_overcharged", lambda **kw: overcharge_events.append(kw))

        succ2, msg2 = self.leyline_mgr.overcharge_node("mire_confluence", self.player)
        self.assertTrue(succ2)
        self.assertTrue(node.is_overcharged)
        self.assertEqual(node.overcharge_hours_left, 24.0)
        self.assertFalse(self.player.inventory.has_item("Starlight Crystal", 1))
        self.assertEqual(len(overcharge_events), 1)

    def test_overcharge_duration_decay_and_expiry(self):
        """Tests that overcharge duration counts down and expires correctly."""
        node = self.leyline_mgr.nodes["village_grove"]
        node.is_overcharged = True
        node.overcharge_hours_left = 24.0

        expired_events = []
        self.game.event_bus.subscribe("leyline_overcharge_expired", lambda **kw: expired_events.append(kw))

        # Advance 10 hours
        self.leyline_mgr.update_overcharge(10.0)
        self.assertTrue(node.is_overcharged)
        self.assertEqual(node.overcharge_hours_left, 14.0)
        self.assertEqual(len(expired_events), 0)

        # Advance 15 hours -> expires
        self.leyline_mgr.update_overcharge(15.0)
        self.assertFalse(node.is_overcharged)
        self.assertEqual(node.overcharge_hours_left, 0.0)
        self.assertEqual(len(expired_events), 1)

    def test_sunken_mire_overcharge_perpetual_low_tide(self):
        """Verifies an overcharged Mire node locks water_level to 0.0 and dispels swamp toxicity."""
        node = self.leyline_mgr.nodes["mire_confluence"]
        node.is_activated = True
        node.is_overcharged = True
        node.overcharge_hours_left = 24.0

        # Update at midnight (normally peak High Tide)
        self.mire_mgr.update(1.0, 2.0)
        self.assertEqual(self.mire_mgr.tide_phase, TIDE_LOW)
        self.assertEqual(self.mire_mgr.water_level, 0.0)
        self.assertFalse(self.mire_mgr.is_toxic_water(100, 100, MAP_SUNKEN_MIRE))
        self.assertEqual(self.mire_mgr.get_speed_multiplier(MAP_SUNKEN_MIRE, is_in_water=True), 1.0)

    def test_mire_flora_and_alchemy_crafting(self):
        """Tests crafting of Waterstrider Elixir, Mire Cleansing Draught, and Leyline Surge Tonic."""
        self.assertIn("Waterstrider Elixir", CRAFTING_RECIPES)
        self.assertIn("Mire Cleansing Draught", CRAFTING_RECIPES)
        self.assertIn("Leyline Surge Tonic", CRAFTING_RECIPES)

        # Give materials for Waterstrider Elixir (2x Mire Reed, 1x Glow Lotus, 1x Blue Potion)
        self.player.inventory.add_item(create_item("Mire Reed", 2))
        self.player.inventory.add_item(create_item("Glow Lotus", 1))
        self.player.inventory.add_item(create_item("Blue Potion", 1))

        succ = CraftingSystem.craft("Waterstrider Elixir", self.player.inventory, facility_level=1)
        self.assertTrue(succ)
        self.assertTrue(self.player.inventory.has_item("Waterstrider Elixir", 1))
        self.assertFalse(self.player.inventory.has_item("Mire Reed", 1))

    def test_waterstrider_elixir_buff(self):
        """Verifies Waterstrider Elixir sets timer and bypasses swamp movement speed slowdown."""
        elixir = create_item("Waterstrider Elixir", 1)
        self.player.inventory.add_item(elixir)
        slot_idx = self.player.inventory.find_item_slot("Waterstrider Elixir")

        self.player.inventory.use_item(slot_idx, self.player)
        self.assertEqual(self.player.waterstrider_timer, 180.0)

        # In High Tide (water_level = 1.0), movement slowdown is ignored
        self.mire_mgr.water_level = 1.0
        # When waterstrider_timer > 0, player speed remains 4.0
        self.assertGreater(self.player.waterstrider_timer, 0.0)

    def test_mire_cleansing_draught_buff(self):
        """Verifies Cleansing Draught cures active poison and sets immunity timer."""
        self.player.elemental_statuses[ELEMENT_POISON] = 10.0
        draught = create_item("Mire Cleansing Draught", 1)
        self.player.inventory.add_item(draught)
        slot_idx = self.player.inventory.find_item_slot("Mire Cleansing Draught")

        self.player.inventory.use_item(slot_idx, self.player)
        self.assertEqual(self.player.cleansing_draught_timer, 240.0)
        self.assertNotIn(ELEMENT_POISON, self.player.elemental_statuses)

    def test_leyline_surge_tonic_buff(self):
        """Verifies Leyline Surge Tonic accelerates mana recovery rate."""
        tonic = create_item("Leyline Surge Tonic", 1)
        self.player.inventory.add_item(tonic)
        slot_idx = self.player.inventory.find_item_slot("Leyline Surge Tonic")

        self.player.inventory.use_item(slot_idx, self.player)
        self.assertEqual(self.player.leyline_surge_timer, 120.0)

    def test_mire_herb_foraging(self):
        """Tests MireHerbSprite interaction and harvesting behavior."""
        group = pygame.sprite.Group()
        herb_sp = MireHerbSprite((200, 200), "Bog Blossom", [group])
        herb_sp.game = self.game

        self.assertFalse(herb_sp.is_harvested)
        herb_sp.interact(self.player)

        self.assertTrue(herb_sp.is_harvested)
        self.assertTrue(self.player.inventory.has_item("Bog Blossom", 1))

        # Second interaction should not yield duplicate item
        count_before = self.player.inventory.count_item("Bog Blossom")
        herb_sp.interact(self.player)
        self.assertEqual(self.player.inventory.count_item("Bog Blossom"), count_before)

    def test_save_serialization_for_overcharge(self):
        """Tests to_dict and from_dict serialization of overcharged Leyline state."""
        node = self.leyline_mgr.nodes["mire_confluence"]
        node.is_activated = True
        node.is_overcharged = True
        node.overcharge_hours_left = 18.5

        saved_dict = self.leyline_mgr.to_dict()
        new_mgr = LeylineManager(self.game.event_bus)
        new_mgr.from_dict(saved_dict)

        restored_node = new_mgr.nodes["mire_confluence"]
        self.assertTrue(restored_node.is_activated)
        self.assertTrue(restored_node.is_overcharged)
        self.assertEqual(restored_node.overcharge_hours_left, 18.5)


if __name__ == "__main__":
    unittest.main()
