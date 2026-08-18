"""
Echoes of Asterra - Unit Tests for Companion System (Fitur #2)
Tests:
1. Companion candidate initialization, recruitment, and party assignment (Max 1 active party companion).
2. Archetype stat growth (Ranger, Guardian, Mage) and level-up mechanics.
3. Tactical combat modes (Attack, Tank, Heal).
4. Autonomous resource expeditions, risk vs danger level calculations, and reward claiming.
5. Contextual dialogue banter generation (weather, dungeon, combat).
6. CompanionSprite following physics, combat aggression, and healing pulse behavior.
7. Save/load serialization roundtrip and save schema v3 -> v4 migration.
8. Manager reset lifecycle preventing cross-slot leakage.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1024, 768))

from rpg.events import EventBus
from rpg.companion import (
    CompanionManager, Companion, CompanionSprite,
    MODE_ATTACK, MODE_TANK, MODE_HEAL
)
from rpg.world_state import WorldState
from rpg.inventory import Inventory
from rpg.save import SaveSystem, migrate_save, SAVE_SCHEMA_VERSION


class DummyGame:
    """Mock Game container for testing companion integrations."""
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.living_world = type("LW", (), {})()
        self.living_world.world_state = WorldState()
        self.living_world.world_state.register_event_listeners(event_bus)
        self.world_state = self.living_world.world_state
        self.player = type("Player", (), {
            "hp": 100,
            "max_hp": 100,
            "gold": 50,
            "pos": pygame.math.Vector2(200, 200),
            "rect": pygame.Rect(184, 184, 32, 32),
            "inventory": Inventory(20)
        })()
        self.enemies = []
        self.particles = None
        self.ui_sprites = pygame.sprite.Group()


class TestCompanionSystem(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.game = DummyGame(self.event_bus)
        self.companion_mgr = CompanionManager(self.event_bus)
        self.companion_mgr.game_reference = self.game

    def test_companion_recruitment_and_party_limit(self):
        """Test candidate recruitment and ensuring only 1 companion is active in party."""
        self.assertIn("faye", self.companion_mgr.companions)
        self.assertIn("kai", self.companion_mgr.companions)
        self.assertIn("mira", self.companion_mgr.companions)

        # Unrecruited companion cannot join party
        self.assertFalse(self.companion_mgr.set_active_party_companion("faye"))

        # Recruit Faye and Kai
        self.assertTrue(self.companion_mgr.recruit_companion("faye"))
        self.assertTrue(self.companion_mgr.recruit_companion("kai"))

        faye = self.companion_mgr.companions["faye"]
        kai = self.companion_mgr.companions["kai"]
        self.assertTrue(faye.is_recruited)
        self.assertTrue(kai.is_recruited)

        # Set Faye to active party
        self.assertTrue(self.companion_mgr.set_active_party_companion("faye"))
        self.assertTrue(faye.is_in_party)
        self.assertFalse(kai.is_in_party)
        self.assertEqual(self.companion_mgr.get_active_companion(), faye)

        # Switching to Kai should automatically remove Faye from party
        self.assertTrue(self.companion_mgr.set_active_party_companion("kai"))
        self.assertFalse(faye.is_in_party)
        self.assertTrue(kai.is_in_party)
        self.assertEqual(self.companion_mgr.get_active_companion(), kai)

        # Dismissing companion
        self.assertTrue(self.companion_mgr.set_active_party_companion(None))
        self.assertIsNone(self.companion_mgr.get_active_companion())

    def test_companion_modes_and_archetype_progression(self):
        """Verify archetype-specific stat scaling and mode switching."""
        faye = self.companion_mgr.companions["faye"]  # Ranger
        kai = self.companion_mgr.companions["kai"]    # Guardian
        mira = self.companion_mgr.companions["mira"]  # Mage

        # Tactical Mode assignment
        self.assertTrue(faye.assign_mode(MODE_ATTACK))
        self.assertTrue(kai.assign_mode(MODE_TANK))
        self.assertTrue(mira.assign_mode(MODE_HEAL))
        self.assertFalse(faye.assign_mode("invalid_mode"))

        # Level up Ranger (DPS focus)
        old_atk = faye.atk
        faye.level_up(1)
        self.assertGreater(faye.atk, old_atk)

        # Level up Guardian (Defense & HP focus)
        old_def = kai.defense
        old_hp = kai.max_hp
        kai.level_up(1)
        self.assertGreater(kai.defense, old_def)
        self.assertGreater(kai.max_hp, old_hp)

        # Level up Mage (Magic/ATK focus)
        old_mira_atk = mira.atk
        mira.level_up(1)
        self.assertGreater(mira.atk, old_mira_atk)

    def test_companion_autonomous_expeditions(self):
        """Test dispatching companion on expedition, day ticks, risk, and claiming rewards."""
        self.companion_mgr.recruit_companion("faye")
        faye = self.companion_mgr.companions["faye"]

        # Dispatch to Forest for 2 days
        self.assertTrue(self.companion_mgr.dispatch_expedition("faye", "forest", 2))
        self.assertIsNotNone(faye.expedition)
        self.assertEqual(faye.expedition.days_remaining, 2)
        self.assertFalse(faye.expedition.is_completed)

        # Companion on expedition cannot join party
        self.assertFalse(self.companion_mgr.set_active_party_companion("faye"))

        # Day 1 tick
        self.companion_mgr._on_day_changed(day=1, season="spring")
        self.assertEqual(faye.expedition.days_remaining, 1)
        self.assertFalse(faye.expedition.is_completed)

        # Day 2 tick -> completes expedition
        self.companion_mgr._on_day_changed(day=2, season="spring")
        self.assertEqual(faye.expedition.days_remaining, 0)
        self.assertTrue(faye.expedition.is_completed)
        self.assertGreater(faye.expedition.rewards_gold, 0)
        self.assertGreater(len(faye.expedition.rewards_items), 0)

        # Claim expedition rewards
        init_gold = self.game.player.gold
        res = self.companion_mgr.claim_expedition_rewards("faye", self.game.player)
        self.assertIsNotNone(res)
        gold_gained, items_gained = res
        self.assertGreater(gold_gained, 0)
        self.assertEqual(self.game.player.gold, init_gold + gold_gained)
        self.assertIsNone(faye.expedition)

    def test_companion_shared_xp_and_contextual_banter(self):
        """Companions in active party gain shared XP and produce contextual banter."""
        self.companion_mgr.recruit_companion("mira")
        self.companion_mgr.set_active_party_companion("mira")
        mira = self.companion_mgr.companions["mira"]

        # Monster defeated emits shared XP
        init_xp = mira.xp
        self.companion_mgr._on_enemy_killed(enemy_name="Skeleton", xp_yield=40)
        self.assertEqual(mira.xp, init_xp + 40)

        # Banter checks
        banter_idle = self.companion_mgr.get_contextual_banter("idle")
        self.assertIn("Scholar Mira", banter_idle)
        self.assertIn("leylines", banter_idle)

        banter_rain = self.companion_mgr.get_contextual_banter("weather_rain")
        self.assertIn("Scholar Mira", banter_rain)
        self.assertIn("lightning", banter_rain)

    def test_companion_sprite_following_and_healing_pulse(self):
        """Test CompanionSprite movement and heal pulse when player is injured."""
        self.companion_mgr.recruit_companion("mira")
        self.companion_mgr.set_active_party_companion("mira")
        mira = self.companion_mgr.companions["mira"]
        mira.assign_mode(MODE_HEAL)

        visible_group = pygame.sprite.Group()
        comp_sprite = CompanionSprite((100, 100), [visible_group], mira)
        comp_sprite.game = self.game

        # 1. Follow Player
        comp_sprite.update(0.1)
        self.assertNotEqual(comp_sprite.pos, pygame.math.Vector2(100, 100))

        # 2. Heal pulse when player HP is low (e.g. 40/100)
        self.game.player.hp = 40
        comp_sprite.action_cooldown = 0.0
        comp_sprite.update(0.1)
        self.assertGreater(self.game.player.hp, 40)
        self.assertGreater(comp_sprite.action_cooldown, 0.0)

    def test_save_load_persistence_and_schema_v4_migration(self):
        """Test save/load roundtrip and schema v3 -> v4 auto-migration."""
        self.companion_mgr.recruit_companion("kai")
        kai = self.companion_mgr.companions["kai"]
        kai.level_up(2)
        kai.assign_mode(MODE_TANK)

        serialized = self.companion_mgr.to_dict()
        new_mgr = CompanionManager(self.event_bus)
        new_mgr.from_dict(serialized)

        restored_kai = new_mgr.companions["kai"]
        self.assertTrue(restored_kai.is_recruited)
        self.assertEqual(restored_kai.level, 5)
        self.assertEqual(restored_kai.mode, MODE_TANK)

        # Test Schema v3 -> v4 Migration
        legacy_v3_data = {
            "save_schema_version": 3,
            "player": {"slot_name": "Hero", "level": 4, "gold": 120},
            "nemesis": {},
            "living_world": {"world_state": {}, "nemesis": {}}
        }
        migrated = migrate_save(legacy_v3_data)
        self.assertEqual(migrated["save_schema_version"], SAVE_SCHEMA_VERSION)
        self.assertIn("companions", migrated)
        self.assertIn("festival", migrated)
        self.assertIn("companions", migrated["living_world"])
        self.assertIn("festival", migrated["living_world"])

    def test_companion_manager_reset(self):
        """Verify reset clears recruited state and resets candidate roster."""
        self.companion_mgr.recruit_companion("faye")
        self.assertTrue(self.companion_mgr.companions["faye"].is_recruited)

        self.companion_mgr.reset()
        self.assertFalse(self.companion_mgr.companions["faye"].is_recruited)
        self.assertIsNone(self.companion_mgr.get_active_companion())


if __name__ == "__main__":
    unittest.main()
