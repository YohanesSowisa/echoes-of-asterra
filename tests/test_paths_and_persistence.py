"""
Tests for Centralized Path & Storage Resolution Engine (rpg/paths.py)
and Persistence Across All 6 Subsystems:
- SaveSystem (rpg/save.py)
- MythosManager (rpg/mythos.py)
- AchievementManager (rpg/achievements.py)
- BestiaryManager (rpg/bestiary.py)
- MemoryManager (rpg/memory.py)
- ReputationManager (rpg/social.py)
"""
import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch

from rpg.paths import get_persistent_data_dir, get_saves_dir, get_save_file_path, BASE_DIR
import rpg.save as save_mod
import rpg.mythos as mythos_mod
import rpg.achievements as achievements_mod
import rpg.bestiary as bestiary_mod
import rpg.memory as memory_mod
import rpg.social as social_mod


class TestPathsAndPersistence(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_paths_default_non_frozen(self):
        """When not frozen, get_persistent_data_dir returns BASE_DIR (repo root)."""
        with patch.object(sys, "frozen", False, create=True):
            data_dir = get_persistent_data_dir()
            self.assertEqual(data_dir, BASE_DIR)
            self.assertTrue(os.path.isdir(data_dir))
            # Verify assets exist in BASE_DIR
            self.assertTrue(os.path.exists(os.path.join(data_dir, "assets", "fonts", "game_font.ttf")))

    def test_paths_frozen_mode(self):
        """When frozen (PyInstaller executable), get_persistent_data_dir returns exe directory."""
        dummy_exe = os.path.join(self.test_dir, "EchoesOfAsterra")
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(sys, "executable", dummy_exe):
            data_dir = get_persistent_data_dir()
            self.assertEqual(data_dir, self.test_dir)
            saves_dir = get_saves_dir()
            self.assertEqual(saves_dir, os.path.join(self.test_dir, "saves"))
            self.assertTrue(os.path.isdir(saves_dir))

    def test_subsystem_save_paths_use_centralized_paths(self):
        """Verify all 6 subsystems reference paths resolved via rpg.paths."""
        self.assertTrue(save_mod.get_save_path(1).endswith(os.path.join("saves", "savegame_1.json")))
        self.assertTrue(mythos_mod.MYTHOS_FILE_PATH.endswith(os.path.join("saves", "mythos_history.json")))
        self.assertTrue(achievements_mod.ACHIEVEMENTS_SAVE_PATH.endswith(os.path.join("saves", "achievements.json")))
        self.assertTrue(bestiary_mod.BESTIARY_SAVE_PATH.endswith(os.path.join("saves", "bestiary.json")))
        self.assertTrue(memory_mod.MEMORIES_SAVE_PATH.endswith(os.path.join("saves", "memories.json")))
        self.assertTrue(social_mod.SOCIAL_SAVE_PATH.endswith(os.path.join("saves", "social_reputation.json")))

    def test_persistence_cycle_all_subsystems(self):
        """Verify saving and loading across all 6 persistent systems in an isolated folder."""
        isolated_saves = os.path.join(self.test_dir, "saves")
        os.makedirs(isolated_saves, exist_ok=True)

        # 1. SaveSystem
        with patch("rpg.save.get_save_file_path", return_value=os.path.join(isolated_saves, "savegame_88.json")):
            slot_path = save_mod.get_save_path(88)
            self.assertEqual(slot_path, os.path.join(isolated_saves, "savegame_88.json"))
            save_data = {
                "save_schema_version": save_mod.SAVE_SCHEMA_VERSION,
                "player": {"name": "TestHero", "level": 10, "hp": 100, "max_hp": 100, "pos": [100, 200]},
                "quests": {},
                "world": {}
            }
            with open(slot_path, "w") as f:
                import json
                json.dump(save_data, f)
            self.assertTrue(os.path.exists(slot_path))
            with open(slot_path, "r") as f:
                loaded = json.load(f)
            migrated = save_mod.migrate_save(loaded)
            self.assertEqual(migrated["player"]["name"], "TestHero")

        # 2. Mythos
        mythos_file = os.path.join(isolated_saves, "mythos_history.json")
        with patch.object(mythos_mod, "MYTHOS_FILE_PATH", mythos_file):
            from rpg.mythos import MythosManager
            mm = MythosManager()
            mm.records.append({"hero_name": "Hero", "day": 1, "end_cause": "Victory"})
            mm.save_history()
            self.assertTrue(os.path.exists(mythos_file))
            mm2 = MythosManager()
            self.assertTrue(len(mm2.records) >= 1)

        # 3. Achievements
        ach_file = os.path.join(isolated_saves, "achievements.json")
        with patch.object(achievements_mod, "ACHIEVEMENTS_SAVE_PATH", ach_file):
            from rpg.achievements import AchievementManager
            am = AchievementManager()
            am.unlock("first_blood")
            am.save_achievements()
            self.assertTrue(os.path.exists(ach_file))
            am2 = AchievementManager()
            self.assertTrue(am2.achievements["first_blood"].unlocked)

        # 4. Bestiary
        best_file = os.path.join(isolated_saves, "bestiary.json")
        with patch.object(bestiary_mod, "BESTIARY_SAVE_PATH", best_file):
            from rpg.bestiary import BestiaryManager
            bm = BestiaryManager()
            bm.record_kill("goblin")
            bm.save_bestiary()
            self.assertTrue(os.path.exists(best_file))
            bm2 = BestiaryManager()
            bm2.load_bestiary()
            self.assertEqual(bm2.entries["goblin"].kills, 1)

        # 5. Memory
        mem_file = os.path.join(isolated_saves, "memories.json")
        with patch.object(memory_mod, "MEMORIES_SAVE_PATH", mem_file):
            from rpg.memory import MemoryManager
            mem_mgr = MemoryManager()
            mem_mgr.add_memory("mem_1", "settlement", 4)
            with open(mem_file, "w") as f:
                import json
                json.dump(mem_mgr.to_dict(), f)
            self.assertTrue(os.path.exists(mem_file))
            mem_mgr2 = MemoryManager()
            with open(mem_file, "r") as f:
                mem_mgr2.from_dict(json.load(f))
            self.assertEqual(len(mem_mgr2.memories), 1)

        # 6. Social
        soc_file = os.path.join(isolated_saves, "social_reputation.json")
        with patch.object(social_mod, "SOCIAL_SAVE_PATH", soc_file):
            from rpg.social import ReputationManager
            sm = ReputationManager()
            sm.modify_global_reputation(25)
            with open(soc_file, "w") as f:
                import json
                json.dump(sm.to_dict(), f)
            self.assertTrue(os.path.exists(soc_file))
            sm2 = ReputationManager()
            with open(soc_file, "r") as f:
                sm2.from_dict(json.load(f))
            self.assertEqual(sm2.global_reputation, 25)


if __name__ == "__main__":
    unittest.main()
