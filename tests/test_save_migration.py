"""
Echoes of Asterra - Unit Tests for Save System Versioning & Migration (Phase 2)
Tests:
1. Automatic migration of legacy v1 saves (missing schema version, string items, legacy quest format).
2. Preservation of player stats, inventory, equipment, and manager states across schema upgrades.
3. Graceful handling of corrupted/partial/empty save files.
4. Full save and load roundtrip with schema_version verification.
"""
import os
import sys
import json
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1024, 768))

from rpg.save import SaveSystem, migrate_save, SAVE_SCHEMA_VERSION, get_save_path
from rpg.game import Game


class TestSaveMigration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_saves_dir = sys.modules["rpg.save"].SAVES_DIR
        sys.modules["rpg.save"].SAVES_DIR = self.test_dir

    def tearDown(self):
        sys.modules["rpg.save"].SAVES_DIR = self.original_saves_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_migrate_legacy_v1_save_missing_version(self):
        """A legacy v1 save without save_schema_version must be upgraded to v2 without data loss."""
        legacy_save = {
            # Notice: no save_schema_version
            "player": {
                "slot_name": "Old Hero",
                "save_date": "2024-01-01 12:00",
                "level": 5,
                "xp": 350,
                "gold": 250,
                "hp": 90,
                "mana": 40,
                "stamina": 85,
                "base_max_hp": 120,
                "base_max_mana": 60,
                "base_atk": 15,
                "base_def": 8,
                # Missing: base_magic, base_speed, base_crit
                "pos_x": 350.5,
                "pos_y": 420.0,
                "current_map": "forest",
                "inventory": [
                    "Iron Sword",  # legacy string format
                    "Red Potion",  # legacy string format
                    None,
                    {"name": "Iron Ore", "qty": 5}  # partial dict
                ],
                "equipment": {
                    "weapon": "Steel Blade",  # legacy string format
                    "armor": None
                },
                "skills_unlocked": ["Fireball"]
            },
            "quests": {
                "main_quest_1": 1  # legacy integer status format
            },
            "world": {
                "chests_opened": {"chest_1": True},
                "boss_defeated": False
            }
            # Missing all manager blocks: factions, npc_memories, social_reputation, decay_memories, ecology, etc.
        }

        migrated = migrate_save(legacy_save)

        # 1. Schema version must be upgraded
        self.assertEqual(migrated.get("save_schema_version"), SAVE_SCHEMA_VERSION)

        # 2. Player core stats must be preserved
        p = migrated["player"]
        self.assertEqual(p["slot_name"], "Old Hero")
        self.assertEqual(p["level"], 5)
        self.assertEqual(p["xp"], 350)
        self.assertEqual(p["gold"], 250)
        self.assertEqual(p["current_map"], "forest")

        # 3. Missing base stats must be safely defaulted
        self.assertEqual(p["base_magic"], 10)
        self.assertEqual(p["base_speed"], 4.0)
        self.assertEqual(p["base_crit"], 5)

        # 4. Inventory items must be normalized to rich dictionaries
        inv = p["inventory"]
        self.assertGreaterEqual(len(inv), 20)
        self.assertIsInstance(inv[0], dict)
        self.assertEqual(inv[0]["name"], "Iron Sword")
        self.assertEqual(inv[0]["qty"], 1)
        self.assertEqual(inv[0]["rarity"], "Common")
        self.assertIsInstance(inv[1], dict)
        self.assertEqual(inv[1]["name"], "Red Potion")
        self.assertIsNone(inv[2])
        self.assertEqual(inv[3]["name"], "Iron Ore")
        self.assertEqual(inv[3]["qty"], 5)

        # 5. Equipment slots must be normalized
        eq = p["equipment"]
        self.assertIsInstance(eq["weapon"], dict)
        self.assertEqual(eq["weapon"]["name"], "Steel Blade")
        self.assertIsNone(eq["armor"])
        self.assertIsNone(eq["shield"])
        self.assertIsNone(eq["accessory"])

        # 6. Legacy quest integer status must be normalized
        self.assertIn("main_quest_1", migrated["quests"])
        self.assertEqual(migrated["quests"]["main_quest_1"]["status"], 1)
        self.assertEqual(migrated["quests"]["main_quest_1"]["progress"], [])

        # 7. Subsystems must be initialized with default containers
        self.assertIn("factions", migrated)
        self.assertIn("npc_memories", migrated)
        self.assertIn("social_reputation", migrated)
        self.assertIn("decay_memories", migrated)
        self.assertIn("ecology", migrated)
        self.assertIn("tutorial_flags", migrated)

    def test_migrate_corrupt_or_empty_payload(self):
        """Migrating empty or malformed dictionaries should never crash."""
        empty_res = migrate_save({})
        self.assertEqual(empty_res["save_schema_version"], SAVE_SCHEMA_VERSION)
        self.assertIn("player", empty_res)
        self.assertEqual(empty_res["player"]["level"], 1)

        non_dict_res = migrate_save(None)
        self.assertEqual(non_dict_res["save_schema_version"], SAVE_SCHEMA_VERSION)

    def test_save_and_load_roundtrip_includes_schema_version(self):
        """Saving and loading via SaveSystem must output and consume save_schema_version."""
        screen = pygame.display.set_mode((1024, 768))
        game = Game(screen)
        game.start_new_game()
        game.player.gold = 777
        game.player.level = 3

        # Save to slot 99
        save_success = SaveSystem.save_game(
            game.player, game.quest_manager, game.world_manager, slot=99, slot_name="TestHero"
        )
        self.assertTrue(save_success)

        # Check raw JSON on disk
        filepath = get_save_path(99)
        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "r") as f:
            disk_data = json.load(f)
        self.assertEqual(disk_data.get("save_schema_version"), SAVE_SCHEMA_VERSION)

        # Check slot meta
        meta = SaveSystem.get_slot_meta(99)
        self.assertTrue(meta["exists"])
        self.assertEqual(meta["slot_name"], "TestHero")
        self.assertEqual(meta["level"], 3)
        self.assertEqual(meta["gold"], 777)
        self.assertEqual(meta["schema_version"], SAVE_SCHEMA_VERSION)

        # Reset game and load from slot 99
        game.start_new_game()
        self.assertEqual(game.player.gold, 10)  # starter gold
        load_success = SaveSystem.load_game(
            game.player, game.quest_manager, game.world_manager, slot=99
        )
        self.assertTrue(load_success)
        self.assertEqual(game.player.gold, 777)
        self.assertEqual(game.player.level, 3)


if __name__ == "__main__":
    unittest.main()
