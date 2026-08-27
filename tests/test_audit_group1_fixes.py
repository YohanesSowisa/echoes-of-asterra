import unittest
import os
import shutil
import tempfile
import pygame

from rpg.constants import (
    STATE_PLAYING,
    MAP_VILLAGE,
    MAP_SUNKEN_MIRE
)
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from rpg.game import Game
from rpg.epochs import EPOCH_DEFAULT, EPOCH_DELUGE, EPOCH_SCORCHED
from rpg.quests import QUEST_NOT_STARTED, QUEST_ACTIVE, QUEST_COMPLETED
from rpg.items import create_item
from rpg.save import SaveSystem


class TestAuditGroup1Fixes(unittest.TestCase):
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

    def tearDown(self):
        pass

    # -------------------------------------------------------------------------
    # 1. Leyline Fast Travel Calls load_map (No change_map crash)
    # -------------------------------------------------------------------------
    def test_leyline_fast_travel_loads_map_cleanly(self):
        leyline_mgr = self.game.leyline_manager
        node = leyline_mgr.nodes.get("mire_confluence")
        self.assertIsNotNone(node)
        node.is_activated = True

        # Teleport to mire confluence node
        success, msg = leyline_mgr.fast_travel(self.game.player, "mire_confluence", self.game.world_manager)
        self.assertTrue(success, f"Fast travel failed: {msg}")
        self.assertIn("Teleported across the Leylines", msg)
        self.assertEqual(self.game.world_manager.current_map_name, MAP_SUNKEN_MIRE)
        # Target node pos for mire_confluence is (480, 280) -> spawn at (480, 316)
        self.assertEqual(int(self.game.player.pos.x), 480)
        self.assertEqual(int(self.game.player.pos.y), 316)

    # -------------------------------------------------------------------------
    # 2. Morning Briefing Epoch Title Retrieval
    # -------------------------------------------------------------------------
    def test_morning_briefing_retrieves_epoch_title_without_crash(self):
        # Default epoch
        self.game.epoch_manager.set_epoch(EPOCH_DEFAULT)
        briefing_default = self.game.living_world.world_state.get_morning_briefing(self.game)
        self.assertEqual(briefing_default["epoch_title"], "Era of Balance")

        # Switch to Deluge
        self.game.epoch_manager.set_epoch(EPOCH_DELUGE)
        briefing_deluge = self.game.living_world.world_state.get_morning_briefing(self.game)
        self.assertEqual(briefing_deluge["epoch_title"], "The Deluge Epoch (Zaman Air Bah)")

        # Switch to Scorched
        self.game.epoch_manager.set_epoch(EPOCH_SCORCHED)
        briefing_scorched = self.game.living_world.world_state.get_morning_briefing(self.game)
        self.assertEqual(briefing_scorched["epoch_title"], "The Scorched Blight (Zaman Bara Api)")

    # -------------------------------------------------------------------------
    # 3. QuestManager Serialization & Chrono Rewind Rollback
    # -------------------------------------------------------------------------
    def test_quest_manager_to_dict_and_from_dict(self):
        qm = self.game.quest_manager
        qm.accept_quest("slime_quest")
        qm.quests["slime_quest"].objectives[0].set_progress(3)
        qm.set_tracked_quest("slime_quest")

        serialized = qm.to_dict()
        self.assertIn("quests", serialized)
        self.assertEqual(serialized["tracked_quest_id"], "slime_quest")
        self.assertEqual(serialized["quests"]["slime_quest"]["status"], QUEST_ACTIVE)
        self.assertEqual(serialized["quests"]["slime_quest"]["progress"], [3])

        # Modify active state
        qm.quests["slime_quest"].objectives[0].set_progress(5)
        qm.quests["slime_quest"].status = QUEST_COMPLETED

        # Restore from serialized
        qm.from_dict(serialized)
        self.assertEqual(qm.quests["slime_quest"].status, QUEST_ACTIVE)
        self.assertEqual(qm.quests["slime_quest"].objectives[0].current_count, 3)
        self.assertEqual(qm.tracked_quest_id, "slime_quest")

    def test_chrono_rewind_rolls_back_quest_states(self):
        qm = self.game.quest_manager
        qm.accept_quest("main_quest")
        qm.quests["main_quest"].objectives[0].set_progress(1)

        # Capture snapshot
        chrono = self.game.chrono_manager
        snap = chrono.record_snapshot(self.game)
        self.assertIsNotNone(snap)
        self.assertTrue(len(snap.quest_states) > 0)
        self.assertEqual(snap.quest_states["quests"]["main_quest"]["progress"], [1, 0, 0, 0])

        # Progress in subsequent timeline: complete main_quest, accept and complete slime_quest
        qm.quests["main_quest"].objectives[0].set_progress(3)
        qm.quests["main_quest"].status = QUEST_COMPLETED
        qm.accept_quest("slime_quest")
        qm.quests["slime_quest"].objectives[0].set_progress(5)
        qm.quests["slime_quest"].status = QUEST_COMPLETED

        self.assertEqual(qm.quests["main_quest"].status, QUEST_COMPLETED)
        self.assertEqual(qm.quests["slime_quest"].status, QUEST_COMPLETED)

        # Add Chrono-Weaver Hourglass to inventory so rewind check passes
        hourglass = create_item("Chrono-Weaver Hourglass")
        if hourglass:
            self.game.player.inventory.add_item(hourglass)

        # Execute Temporal Rewind back to snapshot
        can_r, reason = chrono.can_rewind(self.game.player, days_to_rewind=1)
        self.assertTrue(can_r, f"can_rewind failed: {reason}")
        success, msg, _ = chrono.execute_temporal_rewind(self.game, days_to_rewind=1)
        self.assertTrue(success, f"execute_temporal_rewind failed: {msg}")

        # Assert quest state was cleanly rolled back to Snapshot condition!
        self.assertEqual(qm.quests["main_quest"].status, QUEST_ACTIVE)
        self.assertEqual(qm.quests["main_quest"].objectives[0].current_count, 1)
        self.assertEqual(qm.quests["slime_quest"].status, QUEST_NOT_STARTED)
        self.assertEqual(qm.quests["slime_quest"].objectives[0].current_count, 0)

    # -------------------------------------------------------------------------
    # 4. Save & Load Full Roundtrip Persists DiscoveryManager triggered_leads
    # -------------------------------------------------------------------------
    def test_save_game_and_load_game_restores_discovery_leads(self):
        dm = self.game.discovery_manager
        custom_leads = {"lead_sunken_mire", "lead_conspiracy", "lead_dungeon_architect"}
        dm.triggered_leads.update(custom_leads)
        saved_leads = set(dm.triggered_leads)

        # Save game into test slot 97
        save_success = SaveSystem.save_game(self.game.player, self.game.quest_manager, self.game.world_manager, slot=97)
        self.assertTrue(save_success)

        # Clear discovery manager leads in current memory
        dm.triggered_leads.clear()
        self.assertEqual(len(dm.triggered_leads), 0)

        # Load game from test slot 97
        load_success = SaveSystem.load_game(self.game.player, self.game.quest_manager, self.game.world_manager, slot=97)
        self.assertTrue(load_success)

        # Assert all saved leads are fully restored after load
        self.assertTrue(custom_leads.issubset(dm.triggered_leads))
        for lead in custom_leads:
            self.assertIn(lead, dm.triggered_leads)

        # Cleanup slot 97
        SaveSystem.delete_slot(97)


if __name__ == "__main__":
    unittest.main()
