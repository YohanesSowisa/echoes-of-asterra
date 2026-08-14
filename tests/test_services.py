"""
Echoes of Asterra - Service Layer & Architecture Unit Tests
Validates ServiceContainer DAG initialization, AssetService fallbacks,
TilemapService ingestion, NavigationService pathfinding, and Profiling metrics.
"""
import os
import sys
import unittest
import pygame

# Ensure parent of rpg directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)



# Initialize headless Pygame display & mixer for testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((64, 64))

from rpg.config import GameConfig
from rpg.services import ServiceContainer


class TestEngineArchitectureServices(unittest.TestCase):

    def setUp(self) -> None:
        self.config = GameConfig()
        self.container = ServiceContainer(self.config)

    def tearDown(self) -> None:
        self.container.shutdown()

    def test_service_container_dag_initialization(self) -> None:
        """Verifies ServiceContainer instantiates all DAG layer services cleanly."""
        self.assertIsNotNone(self.container.data)
        self.assertIsNotNone(self.container.asset)
        self.assertIsNotNone(self.container.noise)
        self.assertIsNotNone(self.container.tween)
        self.assertIsNotNone(self.container.tilemap)
        self.assertIsNotNone(self.container.navigation)
        self.assertIsNotNone(self.container.admin_ui)
        self.assertIsNotNone(self.container.profiling)

    def test_asset_service_manifest_and_fallback(self) -> None:
        """Verifies AssetService resolves logical IDs and returns magenta fallback on missing asset."""
        asset_svc = self.container.asset
        # Non-existent asset ID should return fallback 64x64 magenta surface
        fallback_surf = asset_svc.get_texture("non_existent_asset_123")
        self.assertIsInstance(fallback_surf, pygame.Surface)
        self.assertEqual(fallback_surf.get_width(), 64)
        self.assertEqual(fallback_surf.get_height(), 64)

    def test_tilemap_service_procedural_fallback(self) -> None:
        """Verifies TilemapService generates decoupled TilemapData structure."""
        tile_svc = self.container.tilemap
        map_data = tile_svc.load_map("test_map_region")
        self.assertIsNotNone(map_data)
        self.assertEqual(map_data.map_id, "test_map_region")
        self.assertGreater(len(map_data.layers), 0)

    def test_navigation_service_api(self) -> None:
        """Verifies NavigationService stable public API methods."""
        nav_svc = self.container.navigation
        # Simple 5x5 walkable grid (0 = walkable, 1 = obstacle)
        grid = [
            [0, 0, 0, 0, 0],
            [0, 1, 1, 1, 0],
            [0, 0, 0, 1, 0],
            [0, 1, 0, 0, 0],
            [0, 0, 0, 0, 0]
        ]
        nav_svc.update_grid(grid)
        self.assertTrue(nav_svc.is_walkable(0, 0))
        self.assertFalse(nav_svc.is_walkable(1, 1))

        # Find path from (0, 0) to (256, 256)
        path = nav_svc.find_path((32.0, 32.0), (256.0, 256.0))
        self.assertIsInstance(path, list)
        self.assertGreater(len(path), 0)

    def test_data_service_save_migration(self) -> None:
        """Verifies DataService schema validation and V1 -> V2 migration."""
        data_svc = self.container.data
        v1_save = {
            "version": 1,
            "player": {"hp": 80.0, "gold": 25}
        }
        migrated = data_svc.validate_and_migrate_save(v1_save)
        self.assertEqual(migrated["version"], 2)
        self.assertEqual(migrated["player"]["hp"], 80.0)
        self.assertIn("stamina", migrated["player"])

    def test_deterministic_seed_propagation(self) -> None:
        """Verifies GameConfig.get_subsystem_seed produces deterministic, isolated hashes."""
        config = GameConfig()
        seed_dungeon_1 = config.get_subsystem_seed("dungeon")
        seed_dungeon_2 = config.get_subsystem_seed("dungeon")
        seed_loot = config.get_subsystem_seed("loot")

        self.assertEqual(seed_dungeon_1, seed_dungeon_2)
        self.assertNotEqual(seed_dungeon_1, seed_loot)

    def test_profiling_service_export(self) -> None:
        """Verifies ProfilingService records timing metrics and exports JSON report."""
        prof_svc = self.container.profiling
        prof_svc.enabled = True
        prof_svc.start_sample("test_service")
        import time
        time.sleep(0.005)
        prof_svc.end_sample("test_service")

        avg_ms = prof_svc.get_average_ms("test_service")
        self.assertGreater(avg_ms, 0.0)

        test_export_path = "test_profiling.json"
        prof_svc.export_json(test_export_path)
        self.assertTrue(os.path.exists(test_export_path))
        if os.path.exists(test_export_path):
            os.remove(test_export_path)


if __name__ == "__main__":
    unittest.main()
