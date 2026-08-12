"""
Unit tests for Emergent Dynamic Quest Generator.
"""
import unittest
from rpg.events import EventBus
from rpg.world_state import WorldState
from rpg.quests import QuestManager, QUEST_ACTIVE
from rpg.emergent_quests import EmergentQuestGenerator

class TestEmergentQuests(unittest.TestCase):
    def setUp(self) -> None:
        self.event_bus = EventBus()
        self.world_state = WorldState()
        self.quest_manager = QuestManager()
        self.generator = EmergentQuestGenerator(self.event_bus)

    def test_emergent_militia_quest_trigger(self) -> None:
        """Tests that high danger and low guard strength triggers militia quest."""
        self.world_state.danger_level = 65.0
        self.world_state.guard_strength = 40.0

        quest = self.generator.evaluate_world(self.world_state, self.quest_manager, day=2)
        self.assertIsNotNone(quest)
        self.assertIn("emergent_militia_day_2", self.quest_manager.quests)
        self.assertEqual(quest.status, QUEST_ACTIVE)

    def test_emergent_caravan_quest_trigger(self) -> None:
        """Tests low road safety triggers highway clearance quest."""
        self.world_state.danger_level = 20.0
        self.world_state.road_safety = 30.0

        quest = self.generator.evaluate_world(self.world_state, self.quest_manager, day=3)
        self.assertIsNotNone(quest)
        self.assertIn("emergent_caravan_day_3", self.quest_manager.quests)

    def test_no_duplicate_emergent_quests_on_same_day(self) -> None:
        """Tests that generator does not duplicate the same emergent quest ID twice."""
        self.world_state.danger_level = 70.0
        self.world_state.guard_strength = 30.0

        q1 = self.generator.evaluate_world(self.world_state, self.quest_manager, day=5)
        q2 = self.generator.evaluate_world(self.world_state, self.quest_manager, day=5)

        self.assertIsNotNone(q1)
        self.assertIsNone(q2)

if __name__ == "__main__":
    unittest.main()
