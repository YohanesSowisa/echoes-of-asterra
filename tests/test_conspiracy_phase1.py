"""
Unit tests for Pillar #2: The Doomsday Infiltration: Shadow Syndicate & The Usurper — Phase 1.
Tests conspiracy tracking engine, 30-day countdown timer, syndicate influence accumulation,
immutable core NPC safeguards, Corrupt Lieutenant Bran mini-boss confrontation,
Syndicate Cipher Fragment discovery, rumor propagation, and save persistence.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.constants import MAP_FOREST, MAP_VILLAGE
from rpg.conspiracy import ConspiracyManager, IMMUTABLE_CORE_NPCS
from rpg.enemy import CorruptLieutenantBran
from rpg.world import WorldManager
from rpg.rumors import RumorBoard
from rpg.inventory import Inventory
from rpg.items import create_item


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
        self.gold = 50
        self.base_max_hp = 100
        self.max_hp = 100
        self.hp = 100
        self.base_atk = 10
        self.atk = 10
        self.base_def = 5
        self.defense = 5
        self.speed = 4.0
        self.inventory = Inventory(24)
        self.game = None
        self.particles = MockParticles()
        self.sound_manager = MockSound()

    def gain_xp(self, amount: int):
        self.xp += amount

    def gain_gold(self, amount: int):
        self.gold += amount

    def take_damage(self, amount: int):
        self.hp = max(0, self.hp - amount)


class MockWorldState:
    def __init__(self):
        self.day = 1
        self.time_of_day = 12.0
        self.danger_level = 30.0
        self.guard_strength = 70.0
        self.road_safety = 70.0

    def get_spawn_modifier(self) -> float:
        return 1.0


class MockGame:
    def __init__(self):
        self.game_state = "playing"
        self.event_bus = EventBus()
        self.world_manager = WorldManager()
        self.quest_manager = QuestManager()
        self.player = MockPlayer()
        self.player.game = self
        self.conspiracy_manager = ConspiracyManager(self.event_bus)
        self.rumor_board = RumorBoard(self.event_bus)
        self.world_state = MockWorldState()
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


class TestConspiracyPhase1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.player = self.game.player
        self.cm = self.game.conspiracy_manager

    def test_conspiracy_initialization_and_safeguards(self):
        """Tests that the conspiracy engine initializes properly and protects core storyline NPCs."""
        self.assertEqual(self.cm.syndicate_influence, 35.0)
        self.assertEqual(self.cm.days_until_coup, 30)
        self.assertEqual(self.cm.current_day, 1)
        self.assertIn("bran", self.cm.suspects)
        self.assertEqual(self.cm.suspects["bran"].status, "active")

        # Verify core NPC immutability safeguards
        for core_npc in IMMUTABLE_CORE_NPCS:
            self.assertTrue(self.cm.is_npc_protected(core_npc))
            self.assertTrue(self.cm.is_npc_protected(f"npc_{core_npc}"))
        
        # Verify non-core characters are not protected
        self.assertFalse(self.cm.is_npc_protected("bran"))
        self.assertFalse(self.cm.is_npc_protected("garth"))

    def test_countdown_daily_tick_and_influence_growth(self):
        """Tests that days_until_coup decrements daily and active suspects increase influence."""
        warnings = []
        self.game.event_bus.subscribe("coup_imminent_warning", lambda **kw: warnings.append(kw))

        # Day 2 tick (1 active suspect -> +2% influence)
        self.cm._on_day_changed(day=2)
        self.assertEqual(self.cm.current_day, 2)
        self.assertEqual(self.cm.days_until_coup, 29)
        self.assertEqual(self.cm.syndicate_influence, 37.0)
        self.assertEqual(len(warnings), 0)

        # Day 26 tick (days left = 5 -> warning emitted)
        self.cm._on_day_changed(day=26)
        self.assertEqual(self.cm.days_until_coup, 5)
        self.assertGreaterEqual(len(warnings), 1)
        self.assertEqual(warnings[-1]["days_left"], 5)

    def test_corrupt_bran_combat_and_neutralization(self):
        """Tests CorruptLieutenantBran combat stats, defeat, and drop of Cipher Fragment #1."""
        group = pygame.sprite.Group()
        bran = CorruptLieutenantBran((300, 300), [group])
        bran.game = self.game

        self.assertEqual(bran.hp, 120)
        self.assertEqual(bran.atk, 18)
        self.assertEqual(bran.defense, 7)
        self.assertEqual(bran.exp_reward, 100)
        self.assertEqual(bran.gold_reward, 50)
        self.assertIn("Syndicate Cipher Fragment #1", bran.loot_table)

        # Defeat Bran
        bran.hp = 0
        bran.die()

        # Verify suspect neutralized in manager
        suspect = self.cm.suspects["bran"]
        self.assertTrue(suspect.is_defeated)
        self.assertEqual(suspect.status, "neutralized")
        self.assertEqual(self.cm.syndicate_influence, 20.0)  # 35.0 - 15.0
        self.assertIn("Syndicate Cipher Fragment #1", self.cm.cipher_fragments)
        self.assertTrue(self.player.inventory.has_item("Syndicate Cipher Fragment #1", 1))

    def test_rumor_dissemination_before_and_after_neutralization(self):
        """Tests that initial bribery rumors exist and exposure rumors propagate upon defeat."""
        # Initial rumor
        self.assertIn("rumor_bran_bribes", self.game.rumor_board.rumors)
        bribe_rumor = self.game.rumor_board.rumors["rumor_bran_bribes"]
        self.assertEqual(bribe_rumor.topic, "Corrupt Guard")

        # Neutralization event
        self.cm.neutralize_suspect("bran", self.player)
        self.assertIn("rumor_bran_exposed", self.game.rumor_board.rumors)
        exposed_rumor = self.game.rumor_board.rumors["rumor_bran_exposed"]
        self.assertEqual(exposed_rumor.topic, "Conspiracy Operative Exposed")

    def test_cross_zone_spawning_and_neutralization_suppression(self):
        """Tests that Bran spawns in Forest when active and is omitted after neutralization."""
        # 1. Active suspect -> Spawns in Forest
        self.game.world_manager.load_map(MAP_FOREST, self.player, portal_spawn=False)
        brans = [e for e in self.game.enemies if isinstance(e, CorruptLieutenantBran)]
        self.assertEqual(len(brans), 1)

        # 2. Neutralize suspect
        self.cm.neutralize_suspect("bran", self.player)

        # 3. Reload map -> Bran is suppressed
        self.game.enemies.clear()
        self.game.visible_sprites.empty()
        self.game.world_manager.load_map(MAP_FOREST, self.player, portal_spawn=False)
        brans_after = [e for e in self.game.enemies if isinstance(e, CorruptLieutenantBran)]
        self.assertEqual(len(brans_after), 0)

    def test_conspiracy_persistence_and_serialization(self):
        """Tests serialization and deserialization of the conspiracy state."""
        self.cm.syndicate_influence = 42.5
        self.cm.days_until_coup = 18
        self.cm.current_day = 13
        self.cm.cipher_fragments = ["Syndicate Cipher Fragment #1"]
        self.cm.suspects["bran"].is_defeated = True
        self.cm.suspects["bran"].status = "neutralized"

        data = self.cm.to_dict()
        self.assertEqual(data["syndicate_influence"], 42.5)
        self.assertEqual(data["days_until_coup"], 18)
        self.assertEqual(data["current_day"], 13)
        self.assertIn("Syndicate Cipher Fragment #1", data["cipher_fragments"])
        self.assertTrue(data["suspects"]["bran"]["is_defeated"])

        # Restore into clean manager
        new_cm = ConspiracyManager()
        new_cm.from_dict(data)
        self.assertEqual(new_cm.syndicate_influence, 42.5)
        self.assertEqual(new_cm.days_until_coup, 18)
        self.assertEqual(new_cm.current_day, 13)
        self.assertIn("Syndicate Cipher Fragment #1", new_cm.cipher_fragments)
        self.assertTrue(new_cm.suspects["bran"].is_defeated)
        self.assertEqual(new_cm.suspects["bran"].status, "neutralized")


if __name__ == "__main__":
    unittest.main()
