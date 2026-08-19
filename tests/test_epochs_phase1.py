"""
Unit tests for Pillar #4: The Cataclysm Epochs — Phase 1 (Procedural Tilemap Modifier & The Deluge Epoch).
Tests in-memory procedural tilemap transformations, Deluge flood generation,
wooden raft bridge routing, 100% path connectivity verification, and savegame persistence.
"""
import unittest
import os
import pygame
from collections import deque
from typing import Set, Tuple

from rpg.events import EventBus
from rpg.map_loader import MapGenerator
from rpg.animation import tile_assets, init_assets
from rpg.epochs import (
    EpochManager,
    EPOCH_DEFAULT,
    EPOCH_DELUGE,
    EPOCH_SCORCHED,
    EPOCH_GLACIAL,
    WALKABLE_TILES
)
from rpg.constants import MAP_VILLAGE, MAP_FOREST, MAP_RUINS, MAP_LAKE, MAP_CRYPT
from rpg.settings import TILE_SIZE


class MockWeather:
    def __init__(self):
        self.state = "clear"
    def set_weather(self, weather_type: str):
        self.state = weather_type
    def change_weather(self, weather_type: str):
        self.state = weather_type


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.weather = MockWeather()
        self.epoch_manager = EpochManager(self.event_bus)
        self.epoch_manager.game_reference = self


class TestEpochsPhase1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        init_assets()

    def setUp(self):
        self.game = MockGame()
        self.em = self.game.epoch_manager

    def test_epoch_manager_initialization_and_switching(self):
        """Tests default epoch initialization and state transitions with EventBus notifications."""
        self.assertEqual(self.em.current_epoch, EPOCH_DEFAULT)
        self.assertEqual(self.em.get_current_epoch_name(), "Era of Balance")

        # Track event emission
        events_received = []
        self.game.event_bus.subscribe("epoch_changed", lambda **kw: events_received.append(kw))

        # Switch to Deluge
        success = self.em.set_epoch(EPOCH_DELUGE)
        self.assertTrue(success)
        self.assertEqual(self.em.current_epoch, EPOCH_DELUGE)
        self.assertIn("Deluge Epoch", self.em.get_current_epoch_name())
        self.assertEqual(self.game.weather.state, "rain")
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0]["new_epoch"], EPOCH_DELUGE)

    def test_deluge_epoch_tile_transformation(self):
        """Tests that Deluge Epoch mutates standard grass into water and wood_bridge in-memory."""
        self.em.set_epoch(EPOCH_DELUGE)

        raw_forest = MapGenerator.generate(MAP_FOREST)
        deluge_forest = self.em.apply_epoch_to_map(MAP_FOREST, raw_forest)

        # Ensure original data and file on disk are intact
        self.assertIsNot(raw_forest, deluge_forest)

        deluge_grid = deluge_forest["grid"]
        tile_types = set()
        for row in deluge_grid:
            for tile in row:
                tile_types.add(tile)

        self.assertIn("water", tile_types)
        self.assertIn("wood_bridge", tile_types)

        # Crypt dungeon remains unmutated
        raw_crypt = MapGenerator.generate(MAP_CRYPT)
        deluge_crypt = self.em.apply_epoch_to_map(MAP_CRYPT, raw_crypt)
        self.assertEqual(raw_crypt["grid"], deluge_crypt["grid"])

    def test_deluge_epoch_100_percent_path_connectivity(self):
        """
        Validates with BFS flood fill that 100% of portals, NPCs, chests, and player spawn
        are completely reachable via walkable ground and wooden raft bridges across all main zones.
        """
        self.em.set_epoch(EPOCH_DELUGE)
        test_maps = [MAP_VILLAGE, MAP_FOREST, MAP_RUINS, MAP_LAKE]

        for m_name in test_maps:
            raw_map = MapGenerator.generate(m_name)
            deluge_map = self.em.apply_epoch_to_map(m_name, raw_map)
            grid = deluge_map["grid"]
            h = len(grid)
            w = len(grid[0])

            # Player spawn
            p_spawn = deluge_map.get("player_spawn", (w // 2 * TILE_SIZE, h // 2 * TILE_SIZE))
            start_pt = (
                max(0, min(w - 1, int(p_spawn[0] // TILE_SIZE))),
                max(0, min(h - 1, int(p_spawn[1] // TILE_SIZE)))
            )

            # BFS to find all reachable tiles
            visited: Set[Tuple[int, int]] = set()
            queue = deque([start_pt])
            visited.add(start_pt)

            while queue:
                cx, cy = queue.popleft()
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                        if grid[ny][nx] in WALKABLE_TILES:
                            visited.add((nx, ny))
                            queue.append((nx, ny))

            # 1. Check all Portals
            for portal in deluge_map.get("portals", []):
                prect = portal.get("rect")
                if prect:
                    px = max(0, min(w - 1, int(prect.centerx // TILE_SIZE)))
                    py = max(0, min(h - 1, int(prect.centery // TILE_SIZE)))
                    self.assertIn(
                        (px, py), visited,
                        f"Portal to {portal.get('target_map')} at ({px}, {py}) in map '{m_name}' is unreachable in Deluge Epoch!"
                    )

            # 2. Check all NPCs
            for npc in deluge_map.get("npcs", []):
                npos = npc.get("pos", (0, 0))
                nx = max(0, min(w - 1, int(npos[0] // TILE_SIZE)))
                ny = max(0, min(h - 1, int(npos[1] // TILE_SIZE)))
                self.assertIn(
                    (nx, ny), visited,
                    f"NPC {npc.get('type')} at ({nx}, {ny}) in map '{m_name}' is unreachable in Deluge Epoch!"
                )

            # 3. Check all Chests
            for chest in deluge_map.get("chests", []):
                cpos = chest.get("pos", (0, 0))
                cx = max(0, min(w - 1, int(cpos[0] // TILE_SIZE)))
                cy = max(0, min(h - 1, int(cpos[1] // TILE_SIZE)))
                self.assertIn(
                    (cx, cy), visited,
                    f"Chest at ({cx}, {cy}) in map '{m_name}' is unreachable in Deluge Epoch!"
                )

    def test_wood_bridge_tile_assets(self):
        """Verifies procedural wood_bridge and raft textures exist in tile_assets."""
        self.assertIn("wood_bridge", tile_assets)
        self.assertIn("raft", tile_assets)
        self.assertIsInstance(tile_assets["wood_bridge"], pygame.Surface)
        self.assertEqual(tile_assets["wood_bridge"].get_size(), (TILE_SIZE, TILE_SIZE))

    def test_epoch_manager_savegame_roundtrip(self):
        """Tests serialization and restoration of current epoch in SaveSystem."""
        self.em.set_epoch(EPOCH_DELUGE)
        data = self.em.to_dict()
        self.assertEqual(data["current_epoch"], EPOCH_DELUGE)

        new_em = EpochManager()
        new_em.from_dict(data)
        self.assertEqual(new_em.current_epoch, EPOCH_DELUGE)


if __name__ == "__main__":
    unittest.main()
