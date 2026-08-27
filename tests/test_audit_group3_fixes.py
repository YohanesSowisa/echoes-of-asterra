import unittest
import os
import pygame

from rpg.constants import STATE_PLAYING, MAP_VILLAGE, MAP_DUNGEON
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from rpg.game import Game
from rpg.epochs import EpochManager, EPOCH_DELUGE, EPOCH_SCORCHED, EPOCH_GLACIAL
from rpg.enemy import GrandUsurperBoss
from rpg.save import migrate_save, SAVE_SCHEMA_VERSION


class TestAuditGroup3Fixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        if not pygame.get_init():
            pygame.init()

    def setUp(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.game = Game(self.screen)
        self.game.start_new_game()

    # -------------------------------------------------------------------------
    # 8. Epoch Overlays Exclude Interior Dungeons
    # -------------------------------------------------------------------------
    def test_epoch_overlay_excludes_dungeon(self):
        epoch_mgr = self.game.epoch_manager
        sample_map_data = {
            "width": 10,
            "height": 10,
            "grid": [[0 for _ in range(10)] for _ in range(10)],
            "tiles": [[0 for _ in range(10)] for _ in range(10)]
        }

        for epoch in [EPOCH_DELUGE, EPOCH_SCORCHED, EPOCH_GLACIAL]:
            epoch_mgr.set_epoch(epoch)
            # Apply to dungeon map name
            result = epoch_mgr.apply_epoch_to_map("dungeon", sample_map_data)
            # Result must remain unmutated (direct reference returned)
            self.assertEqual(result, sample_map_data)

    # -------------------------------------------------------------------------
    # 9. GrandUsurperBoss Emits boss_defeated on Death
    # -------------------------------------------------------------------------
    def test_grand_usurper_boss_emits_boss_defeated(self):
        events_received = []

        def on_boss_defeated(**kwargs):
            events_received.append(kwargs)

        self.game.event_bus.subscribe("boss_defeated", on_boss_defeated)

        # Spawn and defeat GrandUsurperBoss
        boss = GrandUsurperBoss((400, 300), [self.game.visible_sprites])
        boss.game = self.game
        boss.hp = 0
        boss.die()

        # Verify boss_defeated event was emitted with boss_id="grand_usurper"
        self.assertTrue(len(events_received) >= 1)
        usurper_events = [e for e in events_received if e.get("boss_id") == "grand_usurper"]
        self.assertEqual(len(usurper_events), 1)
        self.assertEqual(usurper_events[0]["boss_name"], "Grand Inquisitor Vane")

    # -------------------------------------------------------------------------
    # 10. Save Migration Normalizes All 7 Newer Subsystems & Upgrades Schema to 8
    # -------------------------------------------------------------------------
    def test_migrate_save_normalizes_7_subsystem_keys(self):
        legacy_save = {
            "save_schema_version": 1,
            "player": {"level": 1, "gold": 50},
            "quests": {}
        }

        migrated = migrate_save(legacy_save)

        # Assert schema version upgraded
        self.assertEqual(migrated["save_schema_version"], 8)
        self.assertEqual(SAVE_SCHEMA_VERSION, 8)

        # Assert all 7 newer subsystems are safely defaulted to dictionaries
        for key in ["conspiracy", "outposts", "epochs", "monopoly", "dungeon_architect", "chrono", "discovery"]:
            self.assertIn(key, migrated, f"Missing key in migrated save: {key}")
            self.assertIsInstance(migrated[key], dict)

    # -------------------------------------------------------------------------
    # 11. OutpostManager Tracks and Serializes last_daily_revenue
    # -------------------------------------------------------------------------
    def test_outpost_manager_tracks_last_daily_revenue(self):
        outpost_mgr = self.game.outpost_manager
        world_state = self.game.living_world.world_state

        # Initial
        self.assertEqual(outpost_mgr.last_daily_revenue, 0)

        # Build an outpost at forest_crossroads
        self.game.player.gold = 500
        success, msg = outpost_mgr.build_outpost("forest_crossroads", self.game.player, self.game.living_world.faction_war)
        self.assertTrue(success, f"Failed to build outpost: {msg}")

        # Simulate day change
        outpost_mgr._on_day_changed(day=2)

        # Verify last_daily_revenue tracked
        self.assertEqual(outpost_mgr.last_daily_revenue, 10)  # Level 1 daily toll = 10g

        # Verify morning briefing captures trade_revenue
        briefing = world_state.get_morning_briefing(self.game)
        self.assertEqual(briefing.get("trade_revenue"), 10)

        # Verify roundtrip serialization of last_daily_revenue
        data = outpost_mgr.to_dict()
        self.assertEqual(data["last_daily_revenue"], 10)
        outpost_mgr.reset()
        self.assertEqual(outpost_mgr.last_daily_revenue, 0)
        outpost_mgr.from_dict(data)
        self.assertEqual(outpost_mgr.last_daily_revenue, 10)


if __name__ == "__main__":
    unittest.main()
