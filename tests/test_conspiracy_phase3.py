"""
Unit tests for Pillar #2: The Doomsday Infiltration: Shadow Syndicate & The Usurper — Phase 3.
Tests covert sabotage plots, 3-day countdown timers, seamless control point shifts,
ShadowAssassin combat, Envoy escort quest integration, Syndicate Cipher Fragment #2 discovery,
rumor propagation, and save persistence.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.conspiracy import ConspiracyManager
from rpg.enemy import ShadowAssassin
from rpg.faction_war import FactionWarManager
from rpg.factions import FactionManager, FACTION_CULTISTS, FACTION_KNIGHTS
from rpg.npc_memory import NPCMemoryManager
from rpg.rumors import RumorBoard
from rpg.inventory import Inventory
from rpg.quests import QuestManager, QUEST_ACTIVE, QUEST_COMPLETED


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
        self.level = 6
        self.xp = 0
        self.gold = 100
        self.base_max_hp = 120
        self.max_hp = 120
        self.hp = 120
        self.base_max_mana = 60
        self.max_mana = 60
        self.mana = 60
        self.base_atk = 15
        self.atk = 15
        self.base_def = 7
        self.defense = 7
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
        self.quest_manager = QuestManager()
        self.player = MockPlayer()
        self.player.game = self
        self.faction_manager = FactionManager()
        self.factions = self.faction_manager
        self.faction_war = FactionWarManager()
        self.faction_war.register_event_listeners(self.event_bus)
        self.faction_war.faction_manager = self.faction_manager
        self.conspiracy_manager = ConspiracyManager(self.event_bus)
        self.conspiracy_manager.game_reference = self
        self.npc_memory = NPCMemoryManager()
        self.npc_memory.register_event_listeners(self.event_bus)
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


class TestConspiracyPhase3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.player = self.game.player
        self.cm = self.game.conspiracy_manager
        self.qm = self.game.quest_manager
        self.fw = self.game.faction_war

    def test_covert_sabotage_staging_and_timer(self):
        """Verifies sabotage staging when influence >= 50% and daily countdown."""
        self.cm.syndicate_influence = 55.0
        self.cm._on_day_changed(day=2)

        self.assertIn("sabotage_ruins_plaza", self.cm.covert_sabotages)
        sabotage = self.cm.covert_sabotages["sabotage_ruins_plaza"]
        self.assertTrue(sabotage.is_active)
        self.assertEqual(sabotage.days_left, 3)

        # Tick 1 day
        self.cm._on_day_changed(day=3)
        self.assertEqual(sabotage.days_left, 2)

    def test_covert_territory_shift_on_timeout(self):
        """Tests that an unaddressed sabotage causes control point ownership to shift to cult."""
        self.cm.syndicate_influence = 55.0
        self.cm.stage_sabotage("ruins_plaza", "ruins")

        # Initial owner of ruins_plaza
        self.assertIn("ruins_plaza", self.fw.control_points)

        # Advance 3 days to expire sabotage
        self.cm._on_day_changed(day=2)  # 2 days left
        self.cm._on_day_changed(day=3)  # 1 day left
        self.cm._on_day_changed(day=4)  # 0 days left -> executed!

        sabotage = self.cm.covert_sabotages["sabotage_ruins_plaza"]
        self.assertFalse(sabotage.is_active)
        self.assertTrue(sabotage.is_executed)
        self.assertEqual(self.fw.control_points["ruins_plaza"].controlling_faction, "cult")

    def test_shadow_assassin_combat(self):
        """Tests ShadowAssassin enemy stats and combat rewards."""
        group = pygame.sprite.Group()
        assassin = ShadowAssassin((200, 200), [group])
        assassin.game = self.game

        self.assertEqual(assassin.hp, 95)
        self.assertEqual(assassin.atk, 17)
        self.assertEqual(assassin.defense, 5)
        self.assertEqual(assassin.speed, 3.6)
        self.assertIn("Shadow Residue", assassin.loot_table)

        # Slaying assassin
        assassin.hp = 0
        assassin.die()
        self.assertGreaterEqual(self.player.xp, 15)

    def test_prevent_sabotage_and_cipher_discovery(self):
        """Tests foiling a sabotage, -15% influence reduction, and cipher fragment #2 drop."""
        self.cm.syndicate_influence = 50.0
        self.cm.stage_sabotage("ruins_plaza", "ruins")

        succ, msg = self.cm.prevent_sabotage("sabotage_ruins_plaza", self.player)
        self.assertTrue(succ)
        self.assertEqual(self.cm.syndicate_influence, 35.0)  # 50 - 15
        self.assertIn("Syndicate Cipher Fragment #2", self.cm.cipher_fragments)
        self.assertTrue(self.player.inventory.has_item("Syndicate Cipher Fragment #2", 1))

    def test_quest_conspiracy_envoy_progression(self):
        """Tests the Envoy protection quest tracking Shadow Assassin kills."""
        self.assertIn("quest_conspiracy_envoy", self.qm.quests)
        self.qm.accept_quest("quest_conspiracy_envoy")
        quest = self.qm.quests["quest_conspiracy_envoy"]
        self.assertEqual(quest.status, QUEST_ACTIVE)

        # Simulate 3 kills
        self.qm.handle_kill("Shadow Assassin")
        self.qm.handle_kill("Shadow Assassin")
        self.qm.handle_kill("Shadow Assassin")

        self.assertTrue(quest.objectives[0].is_complete())

    def test_rumor_dissemination_on_sabotage_and_prevention(self):
        """Tests that rumors propagate on sabotage staging and successful prevention."""
        # 1. Stage sabotage
        self.cm.stage_sabotage("ruins_plaza", "ruins")
        self.assertIn("rumor_sabotage_ruins_plaza", self.game.rumor_board.rumors)
        staged_rumor = self.game.rumor_board.rumors["rumor_sabotage_ruins_plaza"]
        self.assertEqual(staged_rumor.topic, "Covert Sabotage Plot")

        # 2. Prevent sabotage
        self.cm.prevent_sabotage("sabotage_ruins_plaza", self.player)
        self.assertIn("rumor_rescued_sabotage_ruins_plaza", self.game.rumor_board.rumors)
        prevent_rumor = self.game.rumor_board.rumors["rumor_rescued_sabotage_ruins_plaza"]
        self.assertEqual(prevent_rumor.topic, "Mage Guild Envoy Rescued")

    def test_conspiracy_phase3_persistence(self):
        """Tests serialization and deserialization of covert sabotage operations."""
        self.cm.stage_sabotage("ruins_plaza", "ruins")
        self.cm.covert_sabotages["sabotage_ruins_plaza"].days_left = 2

        data = self.cm.to_dict()
        self.assertIn("covert_sabotages", data)
        self.assertIn("sabotage_ruins_plaza", data["covert_sabotages"])
        self.assertEqual(data["covert_sabotages"]["sabotage_ruins_plaza"]["days_left"], 2)

        # Restore into clean manager
        new_cm = ConspiracyManager()
        new_cm.from_dict(data)
        self.assertIn("sabotage_ruins_plaza", new_cm.covert_sabotages)
        self.assertEqual(new_cm.covert_sabotages["sabotage_ruins_plaza"].days_left, 2)
        self.assertTrue(new_cm.covert_sabotages["sabotage_ruins_plaza"].is_active)


if __name__ == "__main__":
    unittest.main()
