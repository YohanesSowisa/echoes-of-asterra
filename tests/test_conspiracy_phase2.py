"""
Unit tests for Pillar #2: The Doomsday Infiltration: Shadow Syndicate & The Usurper — Phase 2.
Tests secondary NPC brainwashing mechanics, immutable core safeguards, altered dialogues,
price surcharges, ShadowParasite combat duels, mind restoration exorcisms,
rumor propagation, and save persistence.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.constants import MAP_CAVE, MAP_VILLAGE
from rpg.conspiracy import ConspiracyManager, IMMUTABLE_CORE_NPCS
from rpg.enemy import ShadowParasite
from rpg.world import WorldManager
from rpg.npc_memory import NPCMemoryManager
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
        self.base_max_mana = 50
        self.max_mana = 50
        self.mana = 50
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


class TestConspiracyPhase2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.player = self.game.player
        self.cm = self.game.conspiracy_manager
        self.mem = self.game.npc_memory

    def test_compromised_npc_safeguards(self):
        """Verifies core storyline NPCs cannot be compromised, while secondary NPCs can."""
        for core_npc in IMMUTABLE_CORE_NPCS:
            self.assertFalse(self.cm.compromise_npc(core_npc))
            self.assertFalse(self.cm.is_npc_compromised(core_npc))

        # Secondary NPC should succeed
        self.assertTrue(self.cm.compromise_npc("garth"))
        self.assertTrue(self.cm.is_npc_compromised("garth"))

    def test_secondary_npc_compromise_and_dialogue_override(self):
        """Tests that a compromised NPC charges 1.4x surcharge and returns cold dialogue."""
        custom_cold = "The void calls from deep stone..."
        self.cm.compromise_npc("garth", custom_cold)

        self.assertTrue(self.cm.is_npc_compromised("garth"))
        self.assertEqual(self.cm.get_npc_price_multiplier("garth"), 1.4)

        # Dialogue prefix should return cold dialogue
        prefix = self.mem.get_greeting_prefix("garth", self.player)
        self.assertEqual(prefix, custom_cold)

    def test_shadow_parasite_combat_and_exorcism(self):
        """Tests ShadowParasite stats, death resolution, and automatic clean exorcism."""
        self.cm.syndicate_influence = 50.0
        self.cm.compromise_npc("garth")

        group = pygame.sprite.Group()
        parasite = ShadowParasite((300, 300), [group], target_npc_id="garth")
        parasite.game = self.game

        self.assertEqual(parasite.hp, 85)
        self.assertEqual(parasite.atk, 14)
        self.assertEqual(parasite.defense, 4)
        self.assertEqual(parasite.speed, 2.8)
        self.assertIn("Shadow Residue", parasite.loot_table)

        # Kill parasite -> triggers exorcism
        parasite.hp = 0
        parasite.die()

        # Garth should be cleansed
        self.assertFalse(self.cm.is_npc_compromised("garth"))
        self.assertEqual(self.cm.syndicate_influence, 40.0)  # 50 - 10
        self.assertTrue(self.player.inventory.has_item("Shadow Residue", 1))
        self.assertGreaterEqual(self.player.xp, 60)

    def test_exorcism_restores_memory_and_price(self):
        """Verifies that exorcism restores standard dialogue and 1.0x price multiplier."""
        self.cm.compromise_npc("garth")
        self.assertEqual(self.cm.get_npc_price_multiplier("garth"), 1.4)

        succ, msg = self.cm.exorcise_npc("garth", self.player)
        self.assertTrue(succ)
        self.assertEqual(self.cm.get_npc_price_multiplier("garth"), 1.0)

        # Greeting should no longer be cold dialogue
        prefix = self.mem.get_greeting_prefix("garth", self.player)
        self.assertNotEqual(prefix, "Leave me be. The Void sees through our fragile minds...")

    def test_rumor_dissemination_on_compromise_and_exorcism(self):
        """Tests that rumors propagate on NPC compromise and successful exorcism."""
        # 1. Compromise Garth
        self.cm.compromise_npc("garth")
        self.assertIn("rumor_compromised_garth", self.game.rumor_board.rumors)
        comp_rumor = self.game.rumor_board.rumors["rumor_compromised_garth"]
        self.assertEqual(comp_rumor.topic, "Strange Mind Affliction")

        # 2. Exorcise Garth
        self.cm.exorcise_npc("garth", self.player)
        self.assertIn("rumor_exorcised_garth", self.game.rumor_board.rumors)
        exor_rumor = self.game.rumor_board.rumors["rumor_exorcised_garth"]
        self.assertEqual(exor_rumor.topic, "Mind Exorcism Miracle")

    def test_conspiracy_phase2_persistence(self):
        """Tests serialization and deserialization of compromised NPCs state."""
        self.cm.compromise_npc("garth", "Darkness awaits...")
        self.cm.compromised_npcs["garth"].price_multiplier = 1.4

        data = self.cm.to_dict()
        self.assertIn("compromised_npcs", data)
        self.assertIn("garth", data["compromised_npcs"])
        self.assertTrue(data["compromised_npcs"]["garth"]["is_compromised"])
        self.assertEqual(data["compromised_npcs"]["garth"]["cold_dialogue"], "Darkness awaits...")

        # Restore into clean manager
        new_cm = ConspiracyManager()
        new_cm.from_dict(data)
        self.assertTrue(new_cm.is_npc_compromised("garth"))
        self.assertEqual(new_cm.compromised_npcs["garth"].cold_dialogue, "Darkness awaits...")
        self.assertEqual(new_cm.get_npc_price_multiplier("garth"), 1.4)


if __name__ == "__main__":
    unittest.main()
