"""
Unit tests for Pillar #3: Outpost Commander & Sovereign Caravans — Phase 1.
Tests strategic outpost construction at control points, stability requirements,
gold deduction, daily caravan toll accrual, stability locking in Faction Warfare,
physical tower sprite & guard spawning in world maps, and save persistence.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.outpost import (
    OutpostManager,
    OutpostData,
    OutpostTowerSprite,
    OutpostGuardNPC,
    OUTPOST_COST_GOLD,
    OUTPOST_MIN_STABILITY,
    OUTPOST_DAILY_TOLL
)
from rpg.faction_war import FactionWarManager
from rpg.inventory import Inventory


class MockParticles:
    def create_magic_sparkles(self, *args, **kwargs):
        pass
    def create_heal_sparkles(self, *args, **kwargs):
        pass
    def create_levelup_splash(self, *args, **kwargs):
        pass
    def create_kill_splash(self, *args, **kwargs):
        pass


class MockSound:
    def play_sound(self, *args, **kwargs):
        pass
    def play_music(self, *args, **kwargs):
        pass


class MockCamera:
    def trigger_shake(self, *args, **kwargs):
        pass
    def set_map_size(self, *args, **kwargs):
        pass


class MockPlayer(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.pos = pygame.math.Vector2(300, 300)
        self.velocity = pygame.math.Vector2(0, 0)
        self.rect = pygame.Rect(300, 300, 32, 32)
        self.hitbox = pygame.Rect(304, 308, 24, 20)
        self.level = 5
        self.xp = 0
        self.gold = 150
        self.base_max_hp = 100
        self.max_hp = 100
        self.hp = 100
        self.base_max_mana = 50
        self.max_mana = 50
        self.mana = 50
        self.base_atk = 15
        self.atk = 15
        self.base_def = 6
        self.defense = 6
        self.speed = 4.0
        self.inventory = Inventory(24)
        self.game = None
        self.particles = MockParticles()
        self.sound_manager = MockSound()

    def gain_gold(self, amount: int):
        self.gold += amount

    def gain_xp(self, amount: int):
        self.xp += amount


class MockGame:
    def __init__(self):
        self.game_state = "playing"
        self.event_bus = EventBus()
        self.player = MockPlayer()
        self.player.game = self
        self.faction_war = FactionWarManager()
        self.faction_war.game_reference = self
        self.outpost_manager = OutpostManager(self.event_bus)
        self.outpost_manager.game_reference = self
        self.visible_sprites = pygame.sprite.Group()
        self.npcs = pygame.sprite.Group()
        self.outpost_sprites = pygame.sprite.Group()
        self.ui_sprites = []
        self.sound_manager = MockSound()
        self.particles = MockParticles()


class TestOutpostPhase1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.player = self.game.player
        self.om = self.game.outpost_manager
        self.fw = self.game.faction_war

    def test_outpost_data_defaults_and_serialization(self):
        """Verifies initial configuration and serialization of outpost data models."""
        self.assertIn("forest_crossroads", self.om.outposts)
        outpost = self.om.outposts["forest_crossroads"]
        self.assertFalse(outpost.is_built)
        self.assertEqual(outpost.daily_toll_income, OUTPOST_DAILY_TOLL)
        self.assertEqual(outpost.garrison_count, 2)

        # Serialization roundtrip
        outpost.is_built = True
        outpost.unclaimed_toll_gold = 30
        data = self.om.to_dict()

        new_om = OutpostManager()
        new_om.from_dict(data)
        self.assertTrue(new_om.has_outpost("forest_crossroads"))
        self.assertEqual(new_om.outposts["forest_crossroads"].unclaimed_toll_gold, 30)

    def test_outpost_construction_prerequisites(self):
        """Verifies construction requirements: valid control point, stability >= 70%, gold >= 100g."""
        # 1. Unknown control point
        can_b, reason = self.om.can_build_outpost("invalid_cp", self.player, self.fw)
        self.assertFalse(can_b)
        self.assertIn("Unknown control point", reason)

        # 2. Low stability (<70%)
        self.fw.control_points["forest_crossroads"].stability = 40.0
        can_b, reason = self.om.can_build_outpost("forest_crossroads", self.player, self.fw)
        self.assertFalse(can_b)
        self.assertIn("stability is too low", reason)

        # 3. Insufficient gold (<100g)
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.player.gold = 50
        can_b, reason = self.om.can_build_outpost("forest_crossroads", self.player, self.fw)
        self.assertFalse(can_b)
        self.assertIn("Insufficient gold", reason)

        # 4. Valid prerequisites
        self.player.gold = 150
        can_b, reason = self.om.can_build_outpost("forest_crossroads", self.player, self.fw)
        self.assertTrue(can_b)

    def test_successful_outpost_construction(self):
        """Tests that constructing an outpost deducts gold, sets is_built=True, and locks stability to 100%."""
        self.fw.control_points["forest_crossroads"].stability = 75.0
        self.player.gold = 150

        success, msg = self.om.build_outpost("forest_crossroads", self.player, self.fw)
        self.assertTrue(success)
        self.assertEqual(self.player.gold, 50)  # 150 - 100
        self.assertTrue(self.om.has_outpost("forest_crossroads"))
        self.assertEqual(self.fw.control_points["forest_crossroads"].stability, 100.0)
        self.assertFalse(self.fw.control_points["forest_crossroads"].contested)

        # Attempt duplicate build
        can_again, reason_again = self.om.can_build_outpost("forest_crossroads", self.player, self.fw)
        self.assertFalse(can_again)
        self.assertIn("already been constructed", reason_again)

    def test_daily_toll_revenue_accrual_and_collection(self):
        """Tests daily caravan toll generation and player gold collection."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)

        outpost = self.om.outposts["forest_crossroads"]
        self.assertEqual(outpost.unclaimed_toll_gold, 0)

        # Advance 2 days
        self.om._on_day_changed(day=2)
        self.assertEqual(outpost.unclaimed_toll_gold, 10)
        self.om._on_day_changed(day=3)
        self.assertEqual(outpost.unclaimed_toll_gold, 20)

        # Collect toll
        initial_gold = self.player.gold
        collected, msg = self.om.collect_toll("forest_crossroads", self.player)
        self.assertEqual(collected, 20)
        self.assertEqual(self.player.gold, initial_gold + 20)
        self.assertEqual(outpost.unclaimed_toll_gold, 0)
        self.assertEqual(outpost.total_toll_collected, 20)

    def test_collect_all_tolls_across_multiple_outposts(self):
        """Tests multi-outpost toll batch collection."""
        self.player.gold = 300
        for cp in ["forest_crossroads", "cave_depths"]:
            self.fw.control_points[cp].stability = 85.0
            self.om.build_outpost(cp, self.player, self.fw)

        # 3 days pass
        for d in [2, 3, 4]:
            self.om._on_day_changed(day=d)

        # 30g from each of the 2 outposts = 60g total
        p_gold_before = self.player.gold
        total, msg = self.om.collect_all_tolls(self.player)
        self.assertEqual(total, 60)
        self.assertEqual(self.player.gold, p_gold_before + 60)

    def test_faction_war_stability_lock(self):
        """Tests that active outposts lock control points against stability degradation during skirmishes."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        success, _ = self.om.build_outpost("forest_crossroads", self.player, self.fw)
        self.assertTrue(success)

        # Force day change in faction war with high enemy zone kill activity
        self.fw._on_day_changed()

        cp = self.fw.control_points["forest_crossroads"]
        self.assertGreaterEqual(cp.stability, 85.0)
        self.assertFalse(cp.contested)

    def test_outpost_tower_sprite_and_guard_interactions(self):
        """Tests procedural OutpostTowerSprite and OutpostGuardNPC interactions."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        success, _ = self.om.build_outpost("forest_crossroads", self.player, self.fw)
        self.assertTrue(success)
        self.om._on_day_changed(day=2)

        tower = OutpostTowerSprite((100, 100), "forest_crossroads", [self.game.visible_sprites])
        tower.game = self.game

        # Interact with tower to collect tolls
        initial_gold = self.player.gold
        msg = tower.interact(self.player)
        self.assertIsNotNone(msg)
        self.assertEqual(self.player.gold, initial_gold + 10)

        # Guard greeting
        guard = OutpostGuardNPC((120, 100), name="Crossroads Sentry", groups=[self.game.visible_sprites])
        guard.game = self.game
        g_msg = guard.interact(self.player)
        self.assertIn("Commander", g_msg)


if __name__ == "__main__":
    unittest.main()
