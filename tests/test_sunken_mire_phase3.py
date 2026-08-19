"""
Unit tests for Pillar #1: The Sunken Mire & Ancient Leylines — Phase 3.
Tests Submerged Temple map generation, Tidal Boss 'Morvath the Mire Leviathan'
(Phase shifts, enrage mechanics, minion summons, drops), Temple Guardians,
Leyline Resonant Equipment crafting & equipping, and Mythos/Rumor propagation.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.constants import (
    MAP_SUNKEN_MIRE,
    MAP_SUBMERGED_TEMPLE,
    MAP_VILLAGE
)
from rpg.map_loader import MapGenerator
from rpg.enemy import TempleGuardian, MireLeviathanBoss, BogLeech
from rpg.inventory import Inventory
from rpg.items import create_item
from rpg.crafting import CraftingSystem, CRAFTING_RECIPES
from rpg.equipment import Equipment
from rpg.rumors import RumorBoard
from rpg.mythos import MythosManager
from rpg.world import WorldManager


class MockPlayer:
    def __init__(self):
        self.pos = pygame.math.Vector2(480, 280)
        self.rect = pygame.Rect(480, 280, 32, 32)
        self.hitbox = pygame.Rect(484, 288, 24, 20)
        self.level = 6
        self.xp = 0
        self.gold = 100
        self.name = "Hero of Asterra"
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
        self.base_magic = 8
        self.magic = 8
        self.base_speed = 4.0
        self.speed = 4.0
        self.base_crit = 5.0
        self.crit = 5.0
        self.cooldown_reduction = 0.0
        self.waterstrider_timer = 0.0
        self.cleansing_draught_timer = 0.0
        self.leyline_surge_timer = 0.0
        self.elemental_statuses = {}
        self.potion_cooldown_timer = 0.0
        self.inventory = Inventory(24)
        self.equipment = Equipment()
        self.game = None
        self.particles = MockParticles()
        self.sound_manager = MockSound()

    def gain_xp(self, amount: int):
        self.xp += amount

    def gain_gold(self, amount: int):
        self.gold += amount


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


class MockQuestManager:
    def handle_kill(self, kill_type: str):
        pass


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.world_manager = WorldManager()
        self.quest_manager = MockQuestManager()
        self.player = MockPlayer()
        self.player.game = self
        self.visible_sprites = pygame.sprite.Group()
        self.enemies = []
        self.dropped_items = pygame.sprite.Group()
        self.ui_sprites = []
        self.particles = MockParticles()
        self.sound_manager = MockSound()
        self.camera = MockCamera()
        self.rumor_board = RumorBoard(self.event_bus)


class TestSunkenMirePhase3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.game = MockGame()
        self.player = self.game.player

    def test_submerged_temple_map_generation(self):
        """Verifies procedural map generation for Submerged Temple and Mire portals."""
        # Generate Sunken Mire -> must have portal to Submerged Temple
        mire_data = MapGenerator.generate(MAP_SUNKEN_MIRE)
        temple_portals = [p for p in mire_data["portals"] if p["target_map"] == MAP_SUBMERGED_TEMPLE]
        self.assertGreater(len(temple_portals), 0)

        # Generate Submerged Temple
        temple_data = MapGenerator.generate(MAP_SUBMERGED_TEMPLE)
        self.assertIn("grid", temple_data)
        self.assertIn("portals", temple_data)
        self.assertIn("enemies", temple_data)
        self.assertIn("chests", temple_data)

        # Must have return portal to Sunken Mire
        mire_returns = [p for p in temple_data["portals"] if p["target_map"] == MAP_SUNKEN_MIRE]
        self.assertGreater(len(mire_returns), 0)

        # Must spawn Temple Guardians and Morvath
        enemy_types = [e["type"] for e in temple_data["enemies"]]
        self.assertIn("temple_guardian", enemy_types)
        self.assertIn("mire_leviathan", enemy_types)

    def test_mire_leviathan_boss_stats_and_phase_shift(self):
        """Tests Morvath base stats and Phase 2 Enrage shift at 50% HP."""
        group = pygame.sprite.Group()
        boss = MireLeviathanBoss((300, 300), [group])
        boss.game = self.game

        self.assertEqual(boss.hp, 280)
        self.assertEqual(boss.max_hp, 280)
        self.assertEqual(boss.atk, 18)
        self.assertEqual(boss.defense, 6)
        self.assertEqual(boss.phase, 1)
        self.assertFalse(boss.is_enraged)

        # Deal 140 damage (50% HP threshold)
        boss.take_damage(140)
        self.assertEqual(boss.hp, 140)
        self.assertEqual(boss.phase, 2)
        self.assertTrue(boss.is_enraged)
        self.assertEqual(boss.atk, 22)  # 18 + 4
        self.assertAlmostEqual(boss.speed, 3.2)  # 2.6 + 0.6
        self.assertEqual(boss.attack_cooldown, 1.1)

    def test_mire_leviathan_boss_death_and_drops(self):
        """Tests that slaying Morvath emits boss_defeated and drops Conduit Core & Tidal Scale."""
        group = pygame.sprite.Group()
        boss = MireLeviathanBoss((300, 300), [group])
        boss.game = self.game

        events = []
        self.game.event_bus.subscribe("boss_defeated", lambda **kw: events.append(kw))

        self.assertIn("Tidal Scale", boss.loot_table)
        self.assertIn("Conduit Core", boss.loot_table)
        self.assertIn("Sunken Relic", boss.loot_table)

        # Kill boss
        boss.hp = 0
        boss.die()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["boss_id"], "mire_leviathan")

    def test_resonant_equipment_crafting_recipes(self):
        """Tests crafting recipes for Leviathan Scale Mail, Tidecaller Trident, and Conduit Ring."""
        self.assertIn("Leviathan Scale Mail", CRAFTING_RECIPES)
        self.assertIn("Tidecaller Trident", CRAFTING_RECIPES)
        self.assertIn("Conduit Ring of Leylines", CRAFTING_RECIPES)

        # 1. Craft Leviathan Scale Mail (2x Tidal Scale, 4x Beast Leather, 4x Iron Ore)
        self.player.inventory.add_item(create_item("Tidal Scale", 2))
        self.player.inventory.add_item(create_item("Beast Leather", 4))
        self.player.inventory.add_item(create_item("Iron Ore", 4))

        succ_armor = CraftingSystem.craft("Leviathan Scale Mail", self.player.inventory, facility_level=2)
        self.assertTrue(succ_armor)
        self.assertTrue(self.player.inventory.has_item("Leviathan Scale Mail", 1))

        # 2. Craft Tidecaller Trident (2x Tidal Scale, 1x Conduit Core, 1x Steel Blade)
        self.player.inventory.add_item(create_item("Tidal Scale", 2))
        self.player.inventory.add_item(create_item("Conduit Core", 1))
        self.player.inventory.add_item(create_item("Steel Blade", 1))

        succ_weap = CraftingSystem.craft("Tidecaller Trident", self.player.inventory, facility_level=3)
        self.assertTrue(succ_weap)
        self.assertTrue(self.player.inventory.has_item("Tidecaller Trident", 1))

        # 3. Craft Conduit Ring of Leylines (1x Conduit Core, 1x Starlight Crystal, 2x Silver Ore)
        self.player.inventory.add_item(create_item("Conduit Core", 1))
        self.player.inventory.add_item(create_item("Starlight Crystal", 1))
        self.player.inventory.add_item(create_item("Silver Ore", 2))

        succ_acc = CraftingSystem.craft("Conduit Ring of Leylines", self.player.inventory, facility_level=2)
        self.assertTrue(succ_acc)
        self.assertTrue(self.player.inventory.has_item("Conduit Ring of Leylines", 1))

    def test_resonant_equipment_stats_and_equipping(self):
        """Verifies equipping resonant equipment applies stats to player."""
        # 1. Equip Leviathan Scale Mail
        scale_mail = create_item("Leviathan Scale Mail", 1)
        scale_mail.affixes = []
        self.player.equipment.equip(scale_mail, self.player)
        self.assertEqual(self.player.defense, 19)  # 5 base + 14 armor
        self.assertEqual(self.player.max_hp, 135)  # 100 base + 35 armor

        # 2. Equip Tidecaller Trident
        trident = create_item("Tidecaller Trident", 1)
        trident.affixes = []
        self.player.equipment.equip(trident, self.player)
        self.assertEqual(self.player.atk, 30)  # 10 base + 20 weapon
        self.assertEqual(self.player.magic, 20)  # 8 base + 12 weapon

        # 3. Equip Conduit Ring of Leylines
        ring = create_item("Conduit Ring of Leylines", 1)
        ring.affixes = []
        self.player.equipment.equip(ring, self.player)
        self.assertEqual(self.player.max_mana, 80)  # 50 base + 30 ring

    def test_temple_guardian_enemy_stats_and_loot(self):
        """Validates Temple Guardian construct enemy."""
        group = pygame.sprite.Group()
        guardian = TempleGuardian((200, 200), [group])

        self.assertEqual(guardian.hp, 90)
        self.assertEqual(guardian.atk, 16)
        self.assertEqual(guardian.defense, 8)
        self.assertIn("Tidal Scale", guardian.loot_table)

    def test_mythos_and_rumor_propagation_on_boss_defeat(self):
        """Verifies Leviathan defeat creates rumors and records in Mythos."""
        # Trigger boss defeat
        self.game.event_bus.emit(
            "boss_defeated",
            boss_id="mire_leviathan",
            boss_name="Morvath, the Mire Leviathan",
            location="submerged_temple"
        )

        # Check rumor added
        self.assertIn("rumor_leviathan_slain", self.game.rumor_board.rumors)
        rumor = self.game.rumor_board.rumors["rumor_leviathan_slain"]
        self.assertEqual(rumor.topic, "Mire Leviathan Slain")

        # Check Mythos run record
        self.game.world_manager.leviathan_defeated = True
        mythos = MythosManager()
        run_record = mythos.record_run(self.game, end_cause="Ascended Champion")
        timeline_types = [e["event_type"] for e in run_record["events"]]
        self.assertIn("LEVIATHAN_SLAIN", timeline_types)


if __name__ == "__main__":
    unittest.main()
