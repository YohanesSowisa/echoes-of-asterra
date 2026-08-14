"""
Echoes of Asterra - Phase 5 Reimagined Systems Tests
Tests for:
1. Quest mutual exclusion system (exclusive_with logic)
2. Fork quests: Knight's Vow vs Void Covenant availability & locking
3. Alliance chosen EventBus triggers and faction reputation shifts
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from rpg.events import EventBus
from rpg.quests import QuestManager, QUEST_ACTIVE
from rpg.factions import FactionManager, FACTION_KNIGHTS, FACTION_CULTISTS


class TestQuestForkAlliance(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.qm = QuestManager()
        self.qm.event_bus = self.event_bus
        self.factions = FactionManager()
        self.factions.register_event_listeners(self.event_bus)

    def test_fork_quest_initial_availability(self):
        """Prerequisite main_quest active step 1 should make both fork quests available."""
        self.qm.quests["main_quest"].status = QUEST_ACTIVE
        self.qm.quests["main_quest"].objectives[0].current_count = 1

        self.assertTrue(self.qm.is_quest_available("knight_path_quest"))
        self.assertTrue(self.qm.is_quest_available("shadow_path_quest"))

    def test_accepting_knight_path_locks_shadow_path(self):
        """Accepting Knight's Vow quest should lock Void Covenant quest."""
        self.qm.quests["main_quest"].status = QUEST_ACTIVE
        self.qm.quests["main_quest"].objectives[0].current_count = 1

        # Accept Knight path
        self.qm.accept_quest("knight_path_quest")
        self.assertEqual(self.qm.quests["knight_path_quest"].status, QUEST_ACTIVE)

        # Shadow path should no longer be available
        self.assertFalse(self.qm.is_quest_available("shadow_path_quest"))

        # Attempting to accept Shadow path should fail
        self.qm.accept_quest("shadow_path_quest")
        self.assertNotEqual(self.qm.quests["shadow_path_quest"].status, QUEST_ACTIVE)

    def test_alliance_chosen_faction_reputation_shifts(self):
        """Accepting Knight path should boost Knight rep and penalize Cultist rep."""
        self.qm.quests["main_quest"].status = QUEST_ACTIVE
        self.qm.quests["main_quest"].objectives[0].current_count = 1

        initial_knight_rep = self.factions.get_reputation(FACTION_KNIGHTS)
        initial_cult_rep = self.factions.get_reputation(FACTION_CULTISTS)

        self.qm.accept_quest("knight_path_quest")

        new_knight_rep = self.factions.get_reputation(FACTION_KNIGHTS)
        new_cult_rep = self.factions.get_reputation(FACTION_CULTISTS)

        self.assertEqual(new_knight_rep, initial_knight_rep + 30)
        self.assertEqual(new_cult_rep, initial_cult_rep - 35)


if __name__ == "__main__":
    unittest.main()
