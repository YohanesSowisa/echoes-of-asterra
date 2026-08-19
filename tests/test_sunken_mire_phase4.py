"""
Unit tests for Pillar #1: The Sunken Mire & Ancient Leylines — Phase 4.
Tests Leyline Rot accumulation, Overcharge decay, Spore Nest cleansing,
cross-zone SporeHostWolf mutations in the Forest, toxic death bursts,
Emergent Leyline Purification quests, rumor propagation, and save persistence.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.constants import (
    MAP_SUNKEN_MIRE,
    MAP_FOREST,
    MAP_VILLAGE,
    QUEST_ACTIVE
)
from rpg.sunken_mire import MireManager
from rpg.leylines import LeylineManager
from rpg.enemy import Wolf, SporeHostWolf
from rpg.world import WorldManager, SporeNestSprite
from rpg.emergent_quests import EmergentQuestGenerator
from rpg.quests import QuestManager
from rpg.rumors import RumorBoard
from rpg.inventory import Inventory
from rpg.items import create_item


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
    def __init__(self, mire_manager=None):
        self.day = 3
        self.time_of_day = 12.0
        self.danger_level = 30.0
        self.guard_strength = 70.0
        self.road_safety = 70.0
        self.mire_manager = mire_manager

    def get_spawn_modifier(self) -> float:
        return 1.0


class MockGame:
    def __init__(self):
        self.game_state = "playing"
        self.event_bus = EventBus()
        self.world_manager = WorldManager()
        self.quest_manager = QuestManager()
        self.quest_manager.event_bus = self.event_bus
        self.player = MockPlayer()
        self.player.game = self
        self.mire_manager = MireManager(self.event_bus)
        self.mire_manager.game_reference = self
        self.leyline_manager = LeylineManager(self.event_bus)
        self.rumor_board = RumorBoard(self.event_bus)
        self.world_state = MockWorldState(self.mire_manager)
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


class TestSunkenMirePhase4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.player = self.game.player
        self.mm = self.game.mire_manager

    def test_rot_daily_accumulation_and_escalation(self):
        """Tests that active spore nests increase rot daily and emit escalation event at >=60%."""
        self.assertEqual(self.mm.rot_level, 15.0)
        escalations = []
        self.game.event_bus.subscribe("spore_blight_escalated", lambda **kw: escalations.append(kw))

        # Day 1: 3 nests active -> +15% -> 30%
        self.mm.on_day_changed(day=1)
        self.assertEqual(self.mm.rot_level, 30.0)
        self.assertEqual(len(escalations), 0)

        # Day 2: -> +15% -> 45%
        self.mm.on_day_changed(day=2)
        self.assertEqual(self.mm.rot_level, 45.0)
        self.assertEqual(len(escalations), 0)

        # Day 3: -> +15% -> 60% (Threshold reached!)
        self.mm.on_day_changed(day=3)
        self.assertEqual(self.mm.rot_level, 60.0)
        self.assertEqual(len(escalations), 1)
        self.assertEqual(escalations[0]["rot_level"], 60.0)

    def test_rot_overcharge_decay(self):
        """Tests that overcharging the Mire conduit decays Rot by -10% per day."""
        self.mm.rot_level = 50.0
        # Overcharge Mire node
        node = self.game.leyline_manager.get_node_by_map(MAP_SUNKEN_MIRE)
        self.assertIsNotNone(node)
        node.is_active = True
        node.is_overcharged = True
        node.overcharge_hours_left = 24.0

        # Day tick with overcharge active
        self.mm.on_day_changed(day=1)
        self.assertEqual(self.mm.rot_level, 40.0)

        # Day tick 2
        self.mm.on_day_changed(day=2)
        self.assertEqual(self.mm.rot_level, 30.0)

    def test_spore_nest_cleansing(self):
        """Tests manual and interactive spore nest cleansing."""
        self.mm.rot_level = 65.0
        self.assertTrue(self.mm.spore_nests["nest_west"])

        cleansed_events = []
        self.game.event_bus.subscribe("spore_nest_cleansed", lambda **kw: cleansed_events.append(kw))

        # 1. Cleanse via MireManager
        succ = self.mm.cleanse_spore_nest("nest_west")
        self.assertTrue(succ)
        self.assertFalse(self.mm.spore_nests["nest_west"])
        self.assertEqual(self.mm.rot_level, 40.0)  # 65 - 25
        self.assertEqual(len(cleansed_events), 1)

        # 2. Interactive cleansing via SporeNestSprite
        group = pygame.sprite.Group()
        nest_sp = SporeNestSprite((300, 300), "nest_center", False, [group])
        nest_sp.game = self.game

        nest_sp.interact(self.player)
        self.assertTrue(nest_sp.is_cleansed)
        self.assertFalse(self.mm.spore_nests["nest_center"])
        self.assertEqual(self.mm.rot_level, 15.0)  # 40 - 25
        self.assertTrue(self.player.inventory.has_item("Luminescent Spore", 2))
        self.assertEqual(self.player.xp, 30)

    def test_cross_zone_spore_host_wolf_mutation(self):
        """Tests that Forest wolves mutate into SporeHostWolf when Rot >= 60%."""
        # 1. Below threshold (rot = 15%) -> Standard Wolf
        self.mm.rot_level = 15.0
        self.game.world_manager.load_map(MAP_FOREST, self.player, portal_spawn=False)
        wolves = [e for e in self.game.enemies if isinstance(e, Wolf)]
        self.assertGreater(len(wolves), 0)
        self.assertFalse(any(isinstance(e, SporeHostWolf) for e in self.game.enemies))

        # 2. Above threshold (rot = 70%) -> Mutated SporeHostWolf
        self.mm.rot_level = 70.0
        self.game.enemies.clear()
        self.game.visible_sprites.empty()
        self.game.world_manager.load_map(MAP_FOREST, self.player, portal_spawn=False)
        spore_wolves = [e for e in self.game.enemies if isinstance(e, SporeHostWolf)]
        self.assertGreater(len(spore_wolves), 0)

    def test_spore_host_wolf_stats_and_death_burst(self):
        """Tests SporeHostWolf combat stats and 60px toxic death explosion."""
        group = pygame.sprite.Group()
        wolf = SporeHostWolf((300, 300), [group])
        wolf.game = self.game

        self.assertEqual(wolf.hp, 68)
        self.assertEqual(wolf.atk, 15)  # +25% over normal wolf (12)
        self.assertEqual(wolf.defense, 3)
        self.assertEqual(wolf.speed, 3.5)
        self.assertIn("Luminescent Spore", wolf.loot_table)

        # Place player 40px away (inside 60px burst radius)
        self.player.pos = pygame.math.Vector2(320, 320)
        self.player.hp = 100

        # Kill wolf
        wolf.hp = 0
        wolf.die()

        # Player should take 15 spore burst damage
        self.assertEqual(self.player.hp, 85)

    def test_emergent_purification_quest_trigger(self):
        """Verifies EmergentQuestGenerator injects crisis quest when Rot >= 60%."""
        generator = EmergentQuestGenerator(self.game.event_bus)
        self.mm.rot_level = 65.0

        quest = generator.evaluate_world(self.game.world_state, self.game.quest_manager, day=4)
        self.assertIsNotNone(quest)
        self.assertIn("Leyline Spore Blight Crisis", quest.title)
        self.assertEqual(quest.objectives[0].target, "spore_host_wolf")
        self.assertEqual(quest.objectives[0].required_count, 3)

    def test_rumor_dissemination_on_spore_blight(self):
        """Tests that Leyline Spore Blight rumors propagate on escalation."""
        self.game.event_bus.emit("spore_blight_escalated", rot_level=65.0, day=4)
        self.assertIn("rumor_spore_blight", self.game.rumor_board.rumors)
        rumor = self.game.rumor_board.rumors["rumor_spore_blight"]
        self.assertEqual(rumor.topic, "Leyline Spore Blight")

    def test_rot_persistence_and_serialization(self):
        """Verifies MireManager properly saves and restores rot_level and spore_nests."""
        self.mm.rot_level = 72.5
        self.mm.spore_nests["nest_west"] = False

        data = self.mm.to_dict()
        self.assertEqual(data["rot_level"], 72.5)
        self.assertFalse(data["spore_nests"]["nest_west"])
        self.assertTrue(data["spore_nests"]["nest_center"])

        # Restore into clean manager
        new_mm = MireManager()
        new_mm.from_dict(data)
        self.assertEqual(new_mm.rot_level, 72.5)
        self.assertFalse(new_mm.spore_nests["nest_west"])
        self.assertTrue(new_mm.spore_nests["nest_center"])


if __name__ == "__main__":
    unittest.main()
