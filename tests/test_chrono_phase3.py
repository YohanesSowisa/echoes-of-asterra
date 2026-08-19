"""
Unit tests for Pillar #8: Chrono-Echoes & Spacetime Fractures — Phase 3 (Temporal Rifts & Déjà-Vu Reactivity).
Tests WEATHER_TEMPORAL_RIFT weather, 0.75x time dilation factors, NPC deja-vu memories,
custom contextual dialogue branches for Eldrin/Silas/Dennis/Faye/Mira, and save/load persistence.
"""
import unittest
import pygame
from rpg.events import EventBus
from rpg.chrono import ChronoManager
from rpg.weather import WeatherSystem, WEATHER_TEMPORAL_RIFT, WEATHER_CLEAR
from rpg.npc_memory import NPCMemoryManager
from rpg.items import create_item
from rpg.inventory import Inventory
from rpg.equipment import Equipment


class MockPlayer:
    def __init__(self, gold: int = 100, hp: float = 100.0, level: int = 1, x: int = 100, y: int = 100):
        self.gold = gold
        self.hp = hp
        self.max_hp = 100.0
        self.base_max_hp = 100.0
        self.mana = 100.0
        self.max_mana = 100.0
        self.base_max_mana = 100.0
        self.stamina = 100.0
        self.max_stamina = 100.0
        self.base_atk = 20.0
        self.atk = 20.0
        self.base_def = 5.0
        self.defense = 5.0
        self.base_magic = 10.0
        self.magic = 10.0
        self.base_speed = 4.0
        self.speed = 4.0
        self.base_crit = 0.05
        self.crit_chance = 0.05
        self.exp = 0
        self.xp = 0
        self.level = level
        self.rect = pygame.Rect(x, y, 32, 32)
        self.inventory = Inventory(size=20)
        self.equipment = Equipment()
        self.game = None


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.chrono_manager = ChronoManager(self.event_bus)
        self.npc_memory = NPCMemoryManager()
        self.npc_memory.register_event_listeners(self.event_bus)
        self.weather = WeatherSystem()
        self.player = MockPlayer()
        self.player.game = self
        self.day = 1
        self.time_of_day = 8.0
        self.current_map_name = "village"
        self.quest_manager = None
        self.defeated_bosses = []
        self.world_flags = {}
        self.ui_sprites = pygame.sprite.Group()
        self.visible_sprites = pygame.sprite.Group()
        self.dropped_items = pygame.sprite.Group()
        self.particles = None


class TestChronoPhase3(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.game = MockGame()
        self.chrono = self.game.chrono_manager
        self.memory = self.game.npc_memory
        self.weather = self.game.weather
        self.player = self.game.player

    def test_temporal_rift_weather_and_overlay(self):
        """Tests WEATHER_TEMPORAL_RIFT weather state, particle spawning, and overlay drawing."""
        self.weather.set_weather(WEATHER_TEMPORAL_RIFT)
        self.weather.intensity = 1.0
        self.assertEqual(self.weather.state, WEATHER_TEMPORAL_RIFT)

        # Update particles
        camera_offset = pygame.math.Vector2(100, 100)
        self.weather.update(particles=None, camera_offset=camera_offset, dt=0.1)
        self.assertTrue(len(self.weather.weather_particles) > 0)

        # Draw overlay onto a test surface
        surf = pygame.Surface((800, 600))
        self.weather.draw_weather_overlay(surf, camera_offset)
        # Should execute cleanly without exceptions

    def test_chrono_time_dilation_factor(self):
        """Tests 0.75x time dilation factor when temporal anomalies are active."""
        # 1. Baseline: No anomalies -> 1.0x factor
        self.assertFalse(self.chrono.is_temporal_rift_active())
        self.assertEqual(self.chrono.get_time_dilation_factor(), 1.0)

        # 2. Trigger Rewind -> 0.75x time dilation
        self.game.day = 1
        self.chrono.record_snapshot(self.game)
        self.game.day = 3
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))
        self.chrono.execute_temporal_rewind(self.game, days_to_rewind=2)

        self.assertTrue(self.chrono.is_temporal_rift_active())
        self.assertEqual(self.chrono.get_time_dilation_factor(), 0.75)

        # 3. Defeat Doppelganger -> Returns to 1.0x factor
        self.chrono.defeat_doppelganger()
        self.assertFalse(self.chrono.is_temporal_rift_active())
        self.assertEqual(self.chrono.get_time_dilation_factor(), 1.0)

    def test_npc_deja_vu_memory_and_dialogue_branches(self):
        """Tests automatic propagation of deja-vu memories and customized dialogue branches on rewind."""
        # Baseline: No deja vu
        eldrin_mem = self.memory.get_memory("eldrin")
        self.assertEqual(eldrin_mem.deja_vu_count, 0)
        self.assertEqual(self.memory.get_greeting_prefix("eldrin", self.player), "")

        # Execute 3-day rewind
        self.game.day = 1
        self.chrono.record_snapshot(self.game)
        self.game.day = 4
        self.player.inventory.add_item(create_item("Chrono-Weaver Hourglass", 1))
        self.chrono.execute_temporal_rewind(self.game, days_to_rewind=3)

        # Verify Deja-Vu memory registered across core NPCs
        self.assertEqual(self.memory.get_memory("eldrin").deja_vu_count, 1)
        self.assertEqual(self.memory.get_memory("silas").deja_vu_count, 1)
        self.assertEqual(self.memory.get_memory("dennis").deja_vu_count, 1)
        self.assertEqual(self.memory.get_memory("faye").deja_vu_count, 1)
        self.assertEqual(self.memory.get_memory("mira").deja_vu_count, 1)

        # Test Eldrin dialogue
        eldrin_dialogue = self.memory.get_greeting_prefix("eldrin", self.player)
        self.assertIn("sands of time", eldrin_dialogue)
        self.assertIn("leylines", eldrin_dialogue)

        # Test Silas dialogue
        silas_dialogue = self.memory.get_greeting_prefix("silas", self.player)
        self.assertIn("vivid dream", silas_dialogue)
        self.assertIn("iron stock", silas_dialogue)

        # Test Dennis dialogue
        dennis_dialogue = self.memory.get_greeting_prefix("dennis", self.player)
        self.assertIn("forge hammer", dennis_dialogue)
        self.assertIn("anvil", dennis_dialogue)

        # Test Faye dialogue
        faye_dialogue = self.memory.get_greeting_prefix("faye", self.player)
        self.assertIn("quiver", faye_dialogue)

        # Test Mira dialogue
        mira_dialogue = self.memory.get_greeting_prefix("mira", self.player)
        self.assertIn("chrono-weave", mira_dialogue)

        # Test Generic NPC dialogue
        guard_mem = self.memory.get_memory("guard_1")
        guard_mem.deja_vu_count = 1
        generic_dialogue = self.memory.get_greeting_prefix("guard_1", self.player)
        self.assertIn("dizziness", generic_dialogue)

    def test_save_and_restore_deja_vu_memories(self):
        """Tests serialization and state restoration of deja-vu memories in NPCMemoryManager."""
        self.memory.record_deja_vu_memory("eldrin", rewound_days=3, target_day=1)
        self.memory.record_deja_vu_memory("silas", rewound_days=2, target_day=2)

        data = self.memory.to_dict()
        self.assertEqual(data["eldrin"]["deja_vu_count"], 1)
        self.assertEqual(data["eldrin"]["last_deja_vu_day"], 1)
        self.assertEqual(data["silas"]["deja_vu_count"], 1)
        self.assertEqual(data["silas"]["last_deja_vu_day"], 2)

        new_mem_mgr = NPCMemoryManager()
        new_mem_mgr.from_dict(data)
        self.assertEqual(new_mem_mgr.get_memory("eldrin").deja_vu_count, 1)
        self.assertEqual(new_mem_mgr.get_memory("eldrin").last_deja_vu_day, 1)
        self.assertEqual(new_mem_mgr.get_memory("silas").deja_vu_count, 1)
        self.assertEqual(new_mem_mgr.get_memory("silas").last_deja_vu_day, 2)


if __name__ == "__main__":
    unittest.main()
