"""
Unit tests for Pillar #3: Outpost Commander & Sovereign Caravans — Phase 3.
Tests real-time caravan ambushes, BanditRaider enemies, world map tactical skirmishes,
convoy rescue rewards, destruction on timeout, and save serialization.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.outpost import OutpostManager
from rpg.settlement import SettlementManager
from rpg.companion import CompanionManager
from rpg.caravan import (
    CaravanManager,
    CaravanEntity,
    CARAVAN_SOVEREIGN_PLAYER,
    CARAVAN_MERCHANT,
    CARGO_PROVISIONS
)
from rpg.enemy import BanditRaider
from rpg.faction_war import FactionWarManager
from rpg.inventory import Inventory
from rpg.world import WorldManager


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
        self.gold = 200
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
        self.settlement = SettlementManager()
        self.settlement.register_event_listeners(self.event_bus)
        self.outpost_manager = OutpostManager(self.event_bus)
        self.outpost_manager.game_reference = self
        self.companion_manager = CompanionManager(self.event_bus)
        self.companion_manager.game_reference = self
        self.caravan_manager = CaravanManager()
        self.caravan_manager.game_reference = self
        self.caravan_manager.register_event_listeners(self.event_bus)
        self.world_manager = WorldManager()
        self.world_manager.game = self
        self.visible_sprites = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.dropped_items = pygame.sprite.Group()
        self.chests = pygame.sprite.Group()
        self.npcs = pygame.sprite.Group()
        self.enemies = []
        self.outpost_sprites = pygame.sprite.Group()
        self.ui_sprites = []
        self.sound_manager = MockSound()
        self.particles = MockParticles()
        self.camera = MockCamera()


class TestOutpostPhase3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.player = self.game.player
        self.om = self.game.outpost_manager
        self.cm = self.game.caravan_manager
        self.sm = self.game.settlement
        self.comp_m = self.game.companion_manager
        self.fw = self.game.faction_war
        self.wm = self.game.world_manager

    def test_bandit_raider_stats_and_combat(self):
        """Tests BanditRaider entity attributes and loot table."""
        group = pygame.sprite.Group()
        raider = BanditRaider((150, 150), [group], caravan_target_id=1234)
        raider.game = self.game
        self.assertEqual(raider.hp, 85)
        self.assertEqual(raider.atk, 15)
        self.assertEqual(raider.defense, 4)
        self.assertEqual(raider.speed, 3.2)
        self.assertIn("Iron Ore", raider.loot_table)

    def test_caravan_ambush_triggering_and_progress_halt(self):
        """Tests that ambushing an active caravan sets state and halts travel progress."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)

        self.cm.commission_sovereign_caravan("forest_crossroads", CARGO_PROVISIONS, player=self.player)
        caravan = self.cm.active_caravans[0]
        c_id = caravan["id"]

        # Trigger Ambush
        success = self.cm.trigger_caravan_ambush(c_id)
        self.assertTrue(success)
        self.assertTrue(caravan["is_under_ambush"])
        self.assertIn(c_id, self.cm.active_ambushes)
        self.assertEqual(caravan["raiders_count"], 3)
        self.assertEqual(caravan["ambush_timer"], 60.0)

        # Updating while ambushed should decrease timer but NOT increase progress
        initial_prog = caravan["progress"]
        self.cm.update(dt=5.0)
        self.assertEqual(caravan["progress"], initial_prog)
        self.assertEqual(caravan["ambush_timer"], 55.0)

    def test_caravan_rescue_rewards_and_safety_increase(self):
        """Tests that defeating all 3 raiders rescues the convoy and delivers rewards."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)

        self.cm.commission_sovereign_caravan("forest_crossroads", CARGO_PROVISIONS, player=self.player)
        caravan = self.cm.active_caravans[0]
        c_id = caravan["id"]
        self.cm.trigger_caravan_ambush(c_id)

        initial_xp = self.player.xp
        initial_gold = self.player.gold
        initial_safety = self.cm.road_safety

        # Kill 2 raiders: still under ambush
        self.cm.on_ambush_enemy_killed(c_id, self.player)
        self.cm.on_ambush_enemy_killed(c_id, self.player)
        self.assertTrue(caravan["is_under_ambush"])
        self.assertEqual(caravan["raiders_count"], 1)

        # Kill 3rd raider: rescued!
        self.cm.on_ambush_enemy_killed(c_id, self.player)
        self.assertFalse(caravan["is_under_ambush"])
        self.assertNotIn(c_id, self.cm.active_ambushes)
        self.assertEqual(self.player.xp, initial_xp + 50)
        self.assertEqual(self.player.gold, initial_gold + 30)
        self.assertEqual(self.cm.road_safety, initial_safety + 10.0)

    def test_caravan_destruction_on_timeout(self):
        """Tests that failing to rescue the caravan within 60s destroys it and injures escort companion."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)

        kai = self.comp_m.companions["kai"]
        kai.is_recruited = True
        kai.is_in_party = False
        kai.hp = 100

        self.cm.commission_sovereign_caravan("forest_crossroads", CARGO_PROVISIONS, companion_id="kai", player=self.player)
        caravan = self.cm.active_caravans[0]
        c_id = caravan["id"]
        self.cm.trigger_caravan_ambush(c_id)

        # Advance 65 seconds (exceeds 60s timer)
        self.cm.update(dt=65.0)

        self.assertEqual(len(self.cm.active_caravans), 0)
        self.assertNotIn(c_id, self.cm.active_ambushes)
        self.assertFalse(kai.is_on_caravan)
        self.assertEqual(kai.hp, 65)  # 100 - 35 injury

    def test_world_map_ambush_spawning(self):
        """Tests that loading an ambushed zone spawns the CaravanEntity and 3x BanditRaider enemies."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)

        self.cm.commission_sovereign_caravan("forest_crossroads", CARGO_PROVISIONS, player=self.player)
        caravan = self.cm.active_caravans[0]
        self.cm.trigger_caravan_ambush(caravan["id"])

        # Load map 'forest'
        self.wm.load_map("forest", self.player)

        # Verify enemies contains BanditRaider
        raiders = [e for e in self.game.enemies if isinstance(e, BanditRaider)]
        self.assertEqual(len(raiders), 3)

    def test_ambush_serialization(self):
        """Tests save/load serialization of active ambushes and road safety."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)

        self.cm.commission_sovereign_caravan("forest_crossroads", CARGO_PROVISIONS, player=self.player)
        caravan = self.cm.active_caravans[0]
        self.cm.trigger_caravan_ambush(caravan["id"])
        self.cm.road_safety = 75.0

        data = self.cm.to_dict()
        self.assertIn("active_ambushes", data)
        self.assertEqual(data["road_safety"], 75.0)

        new_cm = CaravanManager()
        new_cm.from_dict(data)
        self.assertEqual(len(new_cm.active_ambushes), 1)
        self.assertEqual(new_cm.road_safety, 75.0)


if __name__ == "__main__":
    unittest.main()
