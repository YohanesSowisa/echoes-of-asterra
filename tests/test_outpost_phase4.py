"""
Unit tests for Pillar #3: Outpost Commander & Sovereign Caravans — Phase 4.
Tests multi-tier outpost fortification upgrades (Levels 1-3), Automated Courier Relays,
Continental Trade Monopoly milestone, Mythos legacy recording, RumorBoard dissemination,
and save serialization.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.outpost import (
    OutpostManager,
    OutpostTowerSprite,
    OUTPOST_COST_GOLD,
    OUTPOST_UPGRADE_COST_LVL2,
    OUTPOST_UPGRADE_COST_LVL3,
    OUTPOST_TOLL_LVL1,
    OUTPOST_TOLL_LVL2,
    OUTPOST_TOLL_LVL3
)
from rpg.faction_war import FactionWarManager
from rpg.mythos import MythosManager
from rpg.rumors import RumorBoard
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
        self.level = 10
        self.xp = 0
        self.gold = 2000
        self.title = "Adventurer"
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
        self.mythos = MythosManager()
        self.mythos.register_event_listeners(self.event_bus)
        self.rumors = RumorBoard(self.event_bus)
        self.visible_sprites = pygame.sprite.Group()
        self.npcs = pygame.sprite.Group()
        self.enemies = []
        self.outpost_sprites = pygame.sprite.Group()
        self.ui_sprites = []
        self.sound_manager = MockSound()
        self.particles = MockParticles()
        self.camera = MockCamera()


class TestOutpostPhase4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.player = self.game.player
        self.om = self.game.outpost_manager
        self.fw = self.game.faction_war
        self.mythos = self.game.mythos
        self.rumors = self.game.rumors

    def test_outpost_multi_tier_upgrades(self):
        """Tests sequential outpost upgrades from Level 1 to Level 3 with stat and cost scaling."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        success, msg = self.om.build_outpost("forest_crossroads", self.player, self.fw)
        self.assertTrue(success)

        outpost = self.om.outposts["forest_crossroads"]
        self.assertEqual(outpost.level, 1)
        self.assertEqual(outpost.daily_toll_income, OUTPOST_TOLL_LVL1)
        self.assertEqual(outpost.garrison_count, 2)

        # Upgrade to Level 2 (150g)
        p_gold_before = self.player.gold
        success_l2, msg_l2 = self.om.upgrade_outpost("forest_crossroads", self.player)
        self.assertTrue(success_l2)
        self.assertEqual(outpost.level, 2)
        self.assertEqual(outpost.daily_toll_income, OUTPOST_TOLL_LVL2)
        self.assertEqual(outpost.garrison_count, 3)
        self.assertEqual(self.player.gold, p_gold_before - OUTPOST_UPGRADE_COST_LVL2)

        # Upgrade to Level 3 (300g)
        p_gold_before_l3 = self.player.gold
        success_l3, msg_l3 = self.om.upgrade_outpost("forest_crossroads", self.player)
        self.assertTrue(success_l3)
        self.assertEqual(outpost.level, 3)
        self.assertEqual(outpost.daily_toll_income, OUTPOST_TOLL_LVL3)
        self.assertEqual(outpost.garrison_count, 4)
        self.assertTrue(outpost.has_automated_courier)
        self.assertEqual(self.player.gold, p_gold_before_l3 - OUTPOST_UPGRADE_COST_LVL3)

        # Further upgrade should fail
        success_max, msg_max = self.om.upgrade_outpost("forest_crossroads", self.player)
        self.assertFalse(success_max)
        self.assertIn("maximum fortification", msg_max)

    def test_automated_courier_relay_daily_deposits(self):
        """Tests that Level 3 outposts automatically deposit daily tolls into player gold."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)
        self.om.upgrade_outpost("forest_crossroads", self.player)  # Lvl 2
        self.om.upgrade_outpost("forest_crossroads", self.player)  # Lvl 3

        p_gold_before_tick = self.player.gold
        outpost = self.om.outposts["forest_crossroads"]

        # Trigger day changed
        self.om._on_day_changed(day=2)

        # Player received 50g directly via courier relay
        self.assertEqual(self.player.gold, p_gold_before_tick + OUTPOST_TOLL_LVL3)
        # Unclaimed toll remains 0 since it was auto-collected
        self.assertEqual(outpost.unclaimed_toll_gold, 0)
        self.assertEqual(outpost.total_toll_collected, OUTPOST_TOLL_LVL3)

    def test_continental_trade_monopoly_achievement(self):
        """Tests that upgrading 3 outposts to Level 3 triggers the Continental Trade Monopoly milestone."""
        cps = ["forest_crossroads", "cave_depths", "ruins_plaza"]
        for cp in cps:
            self.fw.control_points[cp].stability = 80.0
            self.om.build_outpost(cp, self.player, self.fw)
            self.om.upgrade_outpost(cp, self.player)  # Lvl 2
            self.om.upgrade_outpost(cp, self.player)  # Lvl 3

        self.assertTrue(self.om.continental_monopoly_achieved)
        self.assertEqual(self.player.title, "Merchant Sovereign of Asterra")

        # Mythos chronicle recorded
        events = [e for e in self.mythos.timeline if e.get("event_type") == "CONTINENTAL_TRADE_MONOPOLY"]
        self.assertEqual(len(events), 1)

        # RumorBoard seeded
        self.assertIn("rumor_continental_monopoly", self.rumors.rumors)
        r = self.rumors.rumors["rumor_continental_monopoly"]
        self.assertIn("Merchant Sovereign", r.true_content)

    def test_outpost_tower_sprite_rendering_levels(self):
        """Tests that OutpostTowerSprite builds distinct surfaces and interaction dialogues per level."""
        tower_l1 = OutpostTowerSprite((100, 100), "forest_crossroads", [self.game.visible_sprites], level=1)
        tower_l1.game = self.game
        tower_l2 = OutpostTowerSprite((100, 100), "forest_crossroads", [self.game.visible_sprites], level=2)
        tower_l2.game = self.game
        tower_l3 = OutpostTowerSprite((100, 100), "forest_crossroads", [self.game.visible_sprites], level=3)
        tower_l3.game = self.game

        self.assertEqual(tower_l1.level, 1)
        self.assertEqual(tower_l2.level, 2)
        self.assertEqual(tower_l3.level, 3)

        # Interaction on Lvl 3 mentions courier relay
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)
        self.om.upgrade_outpost("forest_crossroads", self.player)
        self.om.upgrade_outpost("forest_crossroads", self.player)

        msg = tower_l3.interact(self.player)
        self.assertIn("Automated Courier Relay Active", msg)

    def test_outpost_phase4_savegame_serialization(self):
        """Tests serialization and deserialization of upgraded outposts and monopoly achievement."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)
        self.om.upgrade_outpost("forest_crossroads", self.player)
        self.om.upgrade_outpost("forest_crossroads", self.player)
        self.om.continental_monopoly_achieved = True

        data = self.om.to_dict()
        self.assertTrue(data["continental_monopoly_achieved"])
        self.assertEqual(data["outposts"]["forest_crossroads"]["level"], 3)
        self.assertTrue(data["outposts"]["forest_crossroads"]["has_automated_courier"])

        new_om = OutpostManager()
        new_om.from_dict(data)
        self.assertTrue(new_om.continental_monopoly_achieved)
        self.assertEqual(new_om.outposts["forest_crossroads"].level, 3)
        self.assertTrue(new_om.outposts["forest_crossroads"].has_automated_courier)


if __name__ == "__main__":
    unittest.main()
