"""
Unit tests for Pillar #2: The Doomsday Infiltration: Shadow Syndicate & The Usurper — Phase 4.
Tests the Grand Usurper boss encounter, Phase 2 Usurper's Dominion enrage, assassin summons,
3 multi-branching endings (Total Purge, Shadow Sovereign, Compromised Kingdom),
Mythos chronicle recording, and save persistence.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.conspiracy import (
    ConspiracyManager,
    ENDING_TOTAL_PURGE,
    ENDING_SHADOW_SOVEREIGN,
    ENDING_COMPROMISED_KINGDOM
)
from rpg.enemy import GrandUsurperBoss, ShadowAssassin
from rpg.pacts import PactManager, PACT_VOID
from rpg.mythos import MythosManager
from rpg.npc_memory import NPCMemoryManager
from rpg.rumors import RumorBoard
from rpg.inventory import Inventory
from rpg.quests import QuestManager


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


class MockEquipment:
    def __init__(self):
        self.slots = {}


class MockWorldState:
    def __init__(self):
        self.day = 18


class MockPlayer(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((32, 32))
        self.pos = pygame.math.Vector2(300, 300)
        self.velocity = pygame.math.Vector2(0, 0)
        self.rect = pygame.Rect(300, 300, 32, 32)
        self.hitbox = pygame.Rect(304, 308, 24, 20)
        self.level = 8
        self.xp = 0
        self.gold = 150
        self.base_max_hp = 140
        self.max_hp = 140
        self.hp = 140
        self.base_max_mana = 70
        self.max_mana = 70
        self.mana = 70
        self.base_atk = 18
        self.atk = 18
        self.base_def = 8
        self.defense = 8
        self.speed = 4.0
        self.inventory = Inventory(24)
        self.equipment = MockEquipment()
        self.game = None
        self.particles = MockParticles()
        self.sound_manager = MockSound()

    def gain_xp(self, amount: int):
        self.xp += amount

    def gain_gold(self, amount: int):
        self.gold += amount

    def take_damage(self, amount: int):
        self.hp = max(0, self.hp - amount)


class MockGame:
    def __init__(self):
        self.game_state = "playing"
        self.event_bus = EventBus()
        self.quest_manager = QuestManager()
        self.player = MockPlayer()
        self.player.game = self
        self.world_state = MockWorldState()
        self.pact_manager = PactManager(self.event_bus)
        self.conspiracy_manager = ConspiracyManager(self.event_bus)
        self.conspiracy_manager.game_reference = self
        self.mythos_manager = MythosManager()
        self.mythos_manager.register_event_listeners(self.event_bus)
        self.npc_memory = NPCMemoryManager()
        self.npc_memory.register_event_listeners(self.event_bus)
        self.rumor_board = RumorBoard(self.event_bus)
        self.visible_sprites = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.dropped_items = pygame.sprite.Group()
        self.chests = pygame.sprite.Group()
        self.npcs = pygame.sprite.Group()
        self.waypoint_obelisks = pygame.sprite.Group()
        self.leyline_sprites = pygame.sprite.Group()
        self.mire_herb_sprites = pygame.sprite.Group()
        self.spore_nest_sprites = pygame.sprite.Group()
        self.enemies = []
        self.ui_sprites = []
        self.particles = MockParticles()
        self.sound_manager = MockSound()
        self.camera = MockCamera()


class TestConspiracyPhase4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.player = self.game.player
        self.cm = self.game.conspiracy_manager
        self.pm = self.game.pact_manager
        self.mythos = self.game.mythos_manager

    def test_grand_usurper_boss_combat_and_enrage(self):
        """Tests GrandUsurperBoss phase 1 stats, phase 2 enrage at 50% HP, assassin summons, and loot."""
        group = pygame.sprite.Group()
        boss = GrandUsurperBoss((400, 400), [group])
        boss.game = self.game

        self.assertEqual(boss.hp, 320)
        self.assertEqual(boss.atk, 20)
        self.assertEqual(boss.defense, 8)
        self.assertTrue(boss.is_boss)
        self.assertFalse(boss.phase_2_triggered)
        self.assertIn("Usurper's Royal Signet Ring", boss.loot_table)
        self.assertIn("Crown of Shadows", boss.loot_table)

        # Damage below 50% (160 HP)
        boss.take_damage(170)
        self.assertTrue(boss.phase_2_triggered)
        self.assertEqual(boss.defense, 12)  # 8 + 4
        self.assertEqual(boss.atk, 24)      # 20 + 4
        self.assertEqual(boss.speed, 3.0)
        # Should have summoned 2 assassins into enemies list
        self.assertEqual(len(self.game.enemies), 2)
        self.assertIsInstance(self.game.enemies[0], ShadowAssassin)

        # Kill boss
        boss.hp = 0
        boss.die()
        self.assertTrue(self.cm.conspiracy_resolved)
        self.assertEqual(self.cm.conspiracy_ending, ENDING_TOTAL_PURGE)

    def test_ending_total_purge(self):
        """Tests standard victory ending: Usurper defeated, syndicate influence wiped out."""
        self.cm.syndicate_influence = 45.0
        ending, desc = self.cm.resolve_conspiracy(self.player)

        self.assertEqual(ending, ENDING_TOTAL_PURGE)
        self.assertTrue(self.cm.conspiracy_resolved)
        self.assertEqual(self.cm.syndicate_influence, 0.0)

    def test_ending_shadow_soVEREIGN_with_void_pact(self):
        """Tests player ascending to the obsidian throne when holding Void Pact Tier 2+."""
        self.pm.state.active_pact_id = PACT_VOID
        self.pm.state.pact_tier = 2

        ending, desc = self.cm.resolve_conspiracy(self.player)

        self.assertEqual(ending, ENDING_SHADOW_SOVEREIGN)
        self.assertTrue(self.cm.conspiracy_resolved)
        self.assertEqual(self.cm.conspiracy_ending, ENDING_SHADOW_SOVEREIGN)

    def test_ending_compromised_kingdom_on_day30_timeout(self):
        """Tests Day 30 Coup success when unmitigated syndicate influence is >= 70%."""
        self.cm.syndicate_influence = 75.0
        self.cm.days_until_coup = 1

        self.cm._on_day_changed(day=30)

        self.assertTrue(self.cm.conspiracy_resolved)
        self.assertEqual(self.cm.conspiracy_ending, ENDING_COMPROMISED_KINGDOM)

    def test_mythos_recording_on_conspiracy_resolution(self):
        """Verifies that conspiracy endings are written into Mythos timeline and run chronicles."""
        ending, desc = self.cm.resolve_conspiracy(self.player, force_ending=ENDING_TOTAL_PURGE)

        # Check Mythos timeline
        conspiracy_events = [e for e in self.mythos.timeline if e.get("event_type") == "CONSPIRACY_RESOLVED"]
        self.assertGreaterEqual(len(conspiracy_events), 1)
        self.assertEqual(conspiracy_events[0]["ending"], ENDING_TOTAL_PURGE)

        # Record full run
        record = self.mythos.record_run(
            game=self.game,
            end_cause="Victory"
        )
        self.assertEqual(record.get("conspiracy_ending"), ENDING_TOTAL_PURGE)

    def test_conspiracy_phase4_persistence(self):
        """Tests serialization and deserialization of resolved conspiracy states."""
        self.cm.resolve_conspiracy(self.player, force_ending=ENDING_SHADOW_SOVEREIGN)

        data = self.cm.to_dict()
        self.assertTrue(data["conspiracy_resolved"])
        self.assertEqual(data["conspiracy_ending"], ENDING_SHADOW_SOVEREIGN)

        # Restore into clean manager
        new_cm = ConspiracyManager()
        new_cm.from_dict(data)
        self.assertTrue(new_cm.conspiracy_resolved)
        self.assertEqual(new_cm.conspiracy_ending, ENDING_SHADOW_SOVEREIGN)


if __name__ == "__main__":
    unittest.main()
