"""
Unit tests for Pillar #4: The Cataclysm Epochs — Phase 2 (The Scorched Blight & Glacial Winter Epochs).
Tests Scorched Blight and Glacial Winter procedural transformations,
Magma hazard thermal burn ticks and mitigation, Glacial ice sliding momentum physics,
multi-epoch switching, and savegame persistence.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.map_loader import MapGenerator
from rpg.animation import tile_assets, init_assets
from rpg.epochs import (
    EpochManager,
    EPOCH_DEFAULT,
    EPOCH_DELUGE,
    EPOCH_SCORCHED,
    EPOCH_GLACIAL
)
from rpg.constants import (
    MAP_VILLAGE, MAP_FOREST, MAP_RUINS, MAP_LAKE, MAP_CRYPT,
    ITEM_BOOTS
)
from rpg.items import create_item
from rpg.settings import TILE_SIZE
from rpg.player import Player


class MockWeather:
    def __init__(self):
        self.state = "clear"
    def set_weather(self, weather_type: str):
        self.state = weather_type
    def change_weather(self, weather_type: str):
        self.state = weather_type


class MockInput:
    def __init__(self):
        self.move_dir = pygame.math.Vector2(0, 0)
        self.is_running = False
        self.is_blocking = False
        self.actions = set()

    def update_keyboard_states(self):
        pass

    def consume_action(self, action_name: str) -> bool:
        if action_name in self.actions:
            self.actions.remove(action_name)
            return True
        return False


class MockSoundManager:
    def play_sound(self, *args, **kwargs):
        pass


class MockParticles:
    def add_particle(self, *args, **kwargs):
        pass
    def create_dust_puff(self, *args, **kwargs):
        pass
    def create_wind_stream(self, *args, **kwargs):
        pass
    def create_ghost_afterimage(self, *args, **kwargs):
        pass


class MockGame:
    def __init__(self):
        self.game_state = "playing"
        self.dt = 0.016
        self.event_bus = EventBus()
        self.weather = MockWeather()
        self.input_handler = MockInput()
        self.epoch_manager = EpochManager(self.event_bus)
        self.epoch_manager.game_reference = self
        self.ui_manager = type("MockUI", (), {"open_panels": set()})()
        self.ui_sprites = pygame.sprite.Group()
        self.visible_sprites = pygame.sprite.Group()
        self.chests = pygame.sprite.Group()
        self.world_manager = type("MockWorld", (), {"current_map_grid": [], "current_map_name": "forest"})()


class TestEpochsPhase2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        init_assets()

    def setUp(self):
        self.game = MockGame()
        self.em = self.game.epoch_manager
        self.player = Player((200, 200), [self.game.visible_sprites], MockSoundManager(), MockParticles())
        self.player.game = self.game

    def test_scorched_epoch_tile_transformation(self):
        """Tests that Scorched Blight converts grass to ash, trees to burnt_tree, and spawns magma."""
        self.em.set_epoch(EPOCH_SCORCHED)
        self.assertEqual(self.em.current_epoch, EPOCH_SCORCHED)
        self.assertIn("Scorched", self.em.get_current_epoch_name())

        raw_forest = MapGenerator.generate(MAP_FOREST)
        scorched_forest = self.em.apply_epoch_to_map(MAP_FOREST, raw_forest)
        grid = scorched_forest["grid"]

        tile_types = set(tile for row in grid for tile in row)
        self.assertIn("ash_ground", tile_types)
        self.assertIn("burnt_tree", tile_types)
        self.assertIn("magma", tile_types)

        # Ensure spawn area is safe (no magma underfoot)
        p_spawn = scorched_forest.get("player_spawn", (300, 300))
        sx = int(p_spawn[0] // TILE_SIZE)
        sy = int(p_spawn[1] // TILE_SIZE)
        self.assertNotEqual(grid[sy][sx], "magma")

    def test_glacial_epoch_tile_transformation(self):
        """Tests that Glacial Winter converts grass to snow, trees to snow_tree, and water to ice."""
        self.em.set_epoch(EPOCH_GLACIAL)
        self.assertEqual(self.em.current_epoch, EPOCH_GLACIAL)
        self.assertIn("Glacial", self.em.get_current_epoch_name())

        raw_lake = MapGenerator.generate(MAP_LAKE)
        glacial_lake = self.em.apply_epoch_to_map(MAP_LAKE, raw_lake)
        grid = glacial_lake["grid"]

        tile_types = set(tile for row in grid for tile in row)
        self.assertIn("snow", tile_types)
        self.assertIn("snow_tree", tile_types)
        self.assertIn("ice", tile_types)

    def test_magma_hazard_burn_and_immunity(self):
        """Tests that standing on magma inflicts burn damage unless protected by fire boots/elixirs."""
        # Setup 3x3 grid with magma at center
        grid = [["ash_ground", "ash_ground", "ash_ground"],
                ["ash_ground", "magma", "ash_ground"],
                ["ash_ground", "ash_ground", "ash_ground"]]
        self.game.world_manager.current_map_grid = grid

        # Position player on center magma tile (1, 1) -> (48, 48)
        self.player.pos.x = TILE_SIZE + TILE_SIZE // 2
        self.player.pos.y = TILE_SIZE + TILE_SIZE // 2
        self.player.hitbox.center = (int(self.player.pos.x), int(self.player.pos.y))
        self.player.hp = 100
        self.player.out_of_combat_timer = 0.0

        # Unprotected tick for 0.6s (triggers 1 magma damage tick: -2 HP)
        self.player.update(0.6)
        self.assertEqual(self.player.hp, 98)

        # Equip Firewalker boots
        fire_boots = create_item("Leather Boots")
        fire_boots.name = "Firewalker Leather Boots"
        self.player.equipment.equip(fire_boots, self.player)

        # Tick again for 0.6s -> no damage because boots prevent magma burn
        hp_after_equip = self.player.hp
        self.player.out_of_combat_timer = 0.0
        self.player.update(0.6)
        self.assertEqual(self.player.hp, hp_after_equip)

    def test_glacial_ice_sliding_physics(self):
        """Tests that ice tiles apply low-friction inertia sliding momentum."""
        grid = [["ice" for _ in range(5)] for _ in range(5)]
        self.game.world_manager.current_map_grid = grid

        self.player.pos.x = 2 * TILE_SIZE
        self.player.pos.y = 2 * TILE_SIZE
        self.player.hitbox.center = (int(self.player.pos.x), int(self.player.pos.y))

        # Press right movement key
        self.game.input_handler.move_dir = pygame.math.Vector2(1, 0)
        self.player.handle_movement_input(self.game.input_handler)
        self.assertGreater(self.player.velocity.x, 0)

        # Release keys -> on ice, player should slide (velocity.x remains > 0 due to inertia)
        self.game.input_handler.move_dir = pygame.math.Vector2(0, 0)
        self.player.handle_movement_input(self.game.input_handler)
        self.assertGreater(self.player.velocity.x, 0)

    def test_multi_epoch_switching_and_weather(self):
        """Tests switching across all 4 epochs and verified weather integration."""
        # 1. Standard
        self.em.set_epoch(EPOCH_DEFAULT)
        self.assertEqual(self.em.current_epoch, EPOCH_DEFAULT)

        # 2. Deluge (Rain)
        self.em.set_epoch(EPOCH_DELUGE)
        self.assertEqual(self.em.current_epoch, EPOCH_DELUGE)
        self.assertEqual(self.game.weather.state, "rain")

        # 3. Scorched (Fog/Embers)
        self.em.set_epoch(EPOCH_SCORCHED)
        self.assertEqual(self.em.current_epoch, EPOCH_SCORCHED)
        self.assertEqual(self.game.weather.state, "fog")

        # 4. Glacial (Snow)
        self.em.set_epoch(EPOCH_GLACIAL)
        self.assertEqual(self.em.current_epoch, EPOCH_GLACIAL)
        self.assertEqual(self.game.weather.state, "snow")

    def test_epoch_phase2_savegame_serialization(self):
        """Tests serialization and restoration for Scorched and Glacial epochs."""
        self.em.set_epoch(EPOCH_SCORCHED)
        data_s = self.em.to_dict()
        self.assertEqual(data_s["current_epoch"], EPOCH_SCORCHED)

        new_em = EpochManager()
        new_em.from_dict(data_s)
        self.assertEqual(new_em.current_epoch, EPOCH_SCORCHED)

        self.em.set_epoch(EPOCH_GLACIAL)
        data_g = self.em.to_dict()
        new_em.from_dict(data_g)
        self.assertEqual(new_em.current_epoch, EPOCH_GLACIAL)


if __name__ == "__main__":
    unittest.main()
