"""
Unit tests for Pillar #3: Outpost Commander & Sovereign Caravans — Phase 2.
Tests Sovereign Player Caravans (CARAVAN_SOVEREIGN_PLAYER), settlement cargo tiers,
companion convoy captain escort & XP gains, Trade Hub +30% yield boost,
outpost arrival counts, and save serialization.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.outpost import OutpostManager
from rpg.settlement import (
    SettlementManager,
    SPECIALIZATION_TRADE,
    SPECIALIZATION_ARCANE
)
from rpg.companion import (
    CompanionManager,
    Companion,
    MODE_TANK
)
from rpg.caravan import (
    CaravanManager,
    CaravanEntity,
    CARAVAN_SOVEREIGN_PLAYER,
    CARGO_PROVISIONS,
    CARGO_REFINED_IRON,
    CARGO_TONIC_CRATES
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
        self.gold = 250
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
        self.visible_sprites = pygame.sprite.Group()
        self.npcs = pygame.sprite.Group()
        self.outpost_sprites = pygame.sprite.Group()
        self.ui_sprites = []
        self.sound_manager = MockSound()
        self.particles = MockParticles()


class TestOutpostPhase2(unittest.TestCase):
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

    def test_settlement_caravan_cargo_catalogue(self):
        """Tests that settlement tier and facility investments unlock advanced caravan trade cargoes."""
        # Tier 1 defaults: only Provisions
        cargoes = self.sm.get_available_caravan_cargoes()
        cargo_ids = [c["cargo_id"] for c in cargoes]
        self.assertIn("provisions", cargo_ids)
        self.assertNotIn("refined_iron", cargo_ids)
        self.assertNotIn("tonic_crates", cargo_ids)

        # Advance to Tier 2 (Prosperity >= 30)
        self.sm.add_prosperity(15.0)  # 20 + 15 = 35 -> Tier 2
        self.assertEqual(self.sm.growth_tier, 2)
        cargoes_t2 = self.sm.get_available_caravan_cargoes()
        cargo_ids_t2 = [c["cargo_id"] for c in cargoes_t2]
        self.assertIn("provisions", cargo_ids_t2)
        self.assertIn("refined_iron", cargo_ids_t2)
        self.assertIn("tonic_crates", cargo_ids_t2)

    def test_commission_sovereign_caravan_prerequisites(self):
        """Verifies validation rules when commissioning a sovereign caravan."""
        # 1. Target outpost not built
        success, reason = self.cm.commission_sovereign_caravan(
            target_cp_id="forest_crossroads",
            cargo_id=CARGO_PROVISIONS,
            player=self.player
        )
        self.assertFalse(success)
        self.assertIn("No active outpost", reason)

        # Build outpost at forest_crossroads
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)

        # 2. Insufficient gold
        self.player.gold = 10
        success, reason = self.cm.commission_sovereign_caravan(
            target_cp_id="forest_crossroads",
            cargo_id=CARGO_PROVISIONS,
            player=self.player
        )
        self.assertFalse(success)
        self.assertIn("Insufficient funds", reason)

        # 3. Companion in party error
        self.player.gold = 200
        kai = self.comp_m.companions["kai"]
        kai.is_recruited = True
        kai.is_in_party = True

        success, reason = self.cm.commission_sovereign_caravan(
            target_cp_id="forest_crossroads",
            cargo_id=CARGO_PROVISIONS,
            companion_id="kai",
            player=self.player
        )
        self.assertFalse(success)
        self.assertIn("active party", reason)

    def test_successful_sovereign_caravan_dispatch(self):
        """Tests that commissioning a sovereign caravan deducts gold and sets companion escort status."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)

        kai = self.comp_m.companions["kai"]
        kai.is_recruited = True
        kai.is_in_party = False
        self.player.gold = 200

        # Dispatch caravan
        success, msg = self.cm.commission_sovereign_caravan(
            target_cp_id="forest_crossroads",
            cargo_id=CARGO_REFINED_IRON,
            companion_id="kai",
            player=self.player
        )
        self.assertTrue(success)
        self.assertEqual(self.player.gold, 150)  # 200 - 50
        self.assertTrue(kai.is_on_caravan)
        self.assertEqual(len(self.cm.active_caravans), 1)

        caravan = self.cm.active_caravans[0]
        self.assertEqual(caravan["type"], CARAVAN_SOVEREIGN_PLAYER)
        self.assertEqual(caravan["companion_captain"], "kai")
        self.assertEqual(caravan["cargo"], CARGO_REFINED_IRON)

    def test_sovereign_caravan_arrival_and_yield_distribution(self):
        """Tests that completing a sovereign caravan delivers gold/items, grants companion XP, and updates outpost."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)

        kai = self.comp_m.companions["kai"]
        kai.is_recruited = True
        kai.is_in_party = False
        initial_xp = kai.xp
        self.player.gold = 200

        self.cm.commission_sovereign_caravan(
            target_cp_id="forest_crossroads",
            cargo_id=CARGO_REFINED_IRON,
            companion_id="kai",
            player=self.player
        )
        p_gold_after_cost = self.player.gold  # 150

        # Progress caravan to 1.0 (arrival)
        self.cm.update(dt=25.0)  # 25.0 * 0.05 = 1.25 -> arrival
        self.assertEqual(len(self.cm.active_caravans), 0)

        # Player received 110g base yield
        self.assertEqual(self.player.gold, p_gold_after_cost + 110)

        # Companion released and gained 100 XP
        self.assertFalse(kai.is_on_caravan)
        self.assertEqual(kai.xp, initial_xp + 100)

        # Outpost recorded arrival
        outpost = self.om.outposts["forest_crossroads"]
        self.assertEqual(outpost.caravan_arrivals_count, 1)

    def test_trade_hub_specialization_30_percent_yield_bonus(self):
        """Tests that Trade Hub settlement specialization applies a +30% profit bonus on arrivals."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)
        self.sm.specialization = SPECIALIZATION_TRADE

        self.player.gold = 100
        self.cm.commission_sovereign_caravan(
            target_cp_id="forest_crossroads",
            cargo_id=CARGO_PROVISIONS,
            player=self.player
        )
        # Cost 30 -> 70g remaining. Base yield = 60. With +30% = 78g. Total = 148g.
        self.cm.update(dt=25.0)
        self.assertEqual(self.player.gold, 70 + 78)

    def test_caravan_entity_rendering_and_stats(self):
        """Tests CaravanEntity instantiation with CARAVAN_SOVEREIGN_PLAYER."""
        group = pygame.sprite.Group()
        caravan_sp = CaravanEntity(CARAVAN_SOVEREIGN_PLAYER, (100, 100), [group], companion_captain="kai")
        self.assertEqual(caravan_sp.hp, 150)
        self.assertEqual(caravan_sp.speed, 45.0)
        self.assertEqual(caravan_sp.companion_captain, "kai")

    def test_sovereign_caravan_serialization(self):
        """Tests serialization and deserialization of active sovereign caravans."""
        self.fw.control_points["forest_crossroads"].stability = 80.0
        self.om.build_outpost("forest_crossroads", self.player, self.fw)
        self.player.gold = 200
        self.cm.commission_sovereign_caravan("forest_crossroads", CARGO_PROVISIONS, player=self.player)

        data = self.cm.to_dict()
        self.assertEqual(len(data["caravans"]), 1)
        self.assertEqual(data["caravans"][0]["type"], CARAVAN_SOVEREIGN_PLAYER)

        new_cm = CaravanManager()
        new_cm.from_dict(data)
        self.assertEqual(len(new_cm.active_caravans), 1)
        self.assertEqual(new_cm.active_caravans[0]["type"], CARAVAN_SOVEREIGN_PLAYER)


if __name__ == "__main__":
    unittest.main()
