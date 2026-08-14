"""
Echoes of Asterra - Unit Tests for Multi-Day Delayed Consequence Engine (Phase 4)
Tests:
1. Gradual Day-by-Day Progression (Day 1 -> Day 2 [pending] -> Day 3 [executed]).
2. Multi-Day Fast-Forward Jump (Simulating player absence / fast-forwarding time from Day 1 directly to Day 5).
3. Idempotency & Prevention of Double Execution.
4. Serialization and Deserialization across pending multi-day delays.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((64, 64))

from rpg.events import EventBus
from rpg.consequences import ConsequenceManager
from rpg.world_state import WorldState
from rpg.economy import EconomyManager
from rpg.dialogue import DialogueManager
from rpg.quests import QuestManager
from rpg.notification import NotificationManager


class DummyEcology:
    def __init__(self):
        self.populations = {"wolf": 1}

    def get_population(self, species: str) -> int:
        return self.populations.get(species, 0)


class DummyLivingWorld:
    def __init__(self, event_bus):
        self.economy = EconomyManager()
        self.economy.register_event_listeners(event_bus)
        self.ecology = DummyEcology()


class DummyGame:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.world_state = WorldState()
        self.world_state.register_event_listeners(event_bus)
        self.living_world = DummyLivingWorld(event_bus)
        self.dialogue_manager = DialogueManager()
        self.quest_manager = QuestManager()
        self.notification_manager = NotificationManager()
        self.consequences = ConsequenceManager(event_bus)
        self.consequences.game = self


class TestMultiDayConsequences(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.game = DummyGame(self.event_bus)

    def test_gradual_day_progression_execution(self):
        """Consequence queued on Day 1 with 2-day delay should execute on Day 3, not Day 2."""
        # Initial food stock
        initial_food = self.game.living_world.economy.stocks["food"].current_stock

        # 1. Trigger overhunting event on Day 1
        self.game.world_state.day = 1
        self.event_bus.emit("enemy_killed", enemy_type="wolf_alpha")

        # Verify chain is queued for Day 3
        chain = self.game.consequences.active_chains.get("wolf_extinction_chain")
        self.assertIsNotNone(chain)
        self.assertTrue(chain.is_pending)
        self.assertFalse(chain.is_executed)
        self.assertEqual(chain.due_day, 3)

        # 2. Advance to Day 2 (Day tick 2) - should remain pending
        self.game.world_state.day = 2
        self.event_bus.emit("day_changed", day=2)
        self.assertTrue(chain.is_pending)
        self.assertFalse(chain.is_executed)
        self.assertNotIn("deer_culling_emergent", self.game.quest_manager.quests)

        # 3. Advance to Day 3 (Day tick 3) - should trigger execution!
        self.game.world_state.day = 3
        self.event_bus.emit("day_changed", day=3)
        self.assertFalse(chain.is_pending)
        self.assertTrue(chain.is_executed)
        self.assertIn("wolf_extinction_chain", self.game.consequences.completed_chains)

        # Verify downstream world effects
        # - Food stock reduced by 40%
        current_food = self.game.living_world.economy.stocks["food"].current_stock
        self.assertLess(current_food, initial_food)

        # - Emergent Quest created & accepted
        self.assertIn("deer_culling_emergent", self.game.quest_manager.quests)
        self.assertEqual(self.game.quest_manager.quests["deer_culling_emergent"].status, "active")

        # - Reactive NPC dialogue added
        self.assertIn("silas_deer_crisis", self.game.dialogue_manager.nodes)
        self.assertIn("faye_deer_crisis", self.game.dialogue_manager.nodes)

    def test_multi_day_fast_forward_offline_skip(self):
        """Simulating multi-day fast-forward (jumping from Day 1 to Day 6) must execute overdue chains cleanly."""
        self.game.world_state.day = 1
        self.event_bus.emit("enemy_killed", enemy_type="wolf_pack")

        chain = self.game.consequences.active_chains.get("wolf_extinction_chain")
        self.assertIsNotNone(chain)
        self.assertEqual(chain.due_day, 3)

        # Fast forward time directly to Day 6 (simulating offline period / long sleep)
        self.game.world_state.day = 6
        self.event_bus.emit("day_changed", day=6)

        # Chain must be executed
        self.assertTrue(chain.is_executed)
        self.assertIn("wolf_extinction_chain", self.game.consequences.completed_chains)
        self.assertIn("consequence_deer_overpopulation", self.game.world_state.completed_event_ids)
        self.assertIn("deer_culling_emergent", self.game.quest_manager.quests)

    def test_idempotency_and_no_double_execution(self):
        """Executed consequence chains must never re-trigger on subsequent day ticks."""
        self.game.world_state.day = 1
        self.event_bus.emit("enemy_killed", enemy_type="wolf")

        # Fast forward to Day 3 (triggers execution)
        self.game.world_state.day = 3
        self.event_bus.emit("day_changed", day=3)
        self.assertTrue(self.game.consequences.active_chains["wolf_extinction_chain"].is_executed)

        food_after_first_exec = self.game.living_world.economy.stocks["food"].current_stock
        self.assertGreater(food_after_first_exec, 0)

        # Advance to Day 4, 5, 6
        self.game.world_state.day = 4
        self.event_bus.emit("day_changed", day=4)
        self.game.world_state.day = 5
        self.event_bus.emit("day_changed", day=5)

        # Killing more wolves should not re-queue the already completed chain
        self.event_bus.emit("enemy_killed", enemy_type="wolf")
        self.assertIn("wolf_extinction_chain", self.game.consequences.completed_chains)

    def test_serialization_across_pending_delay(self):
        """A pending chain must survive serialization and trigger correctly after load."""
        self.game.world_state.day = 1
        self.event_bus.emit("enemy_killed", enemy_type="wolf")

        saved_data = self.game.consequences.to_dict()

        # Create fresh manager and restore state
        new_manager = ConsequenceManager(self.event_bus)
        new_manager.game = self.game
        new_manager.from_dict(saved_data)

        self.assertIn("wolf_extinction_chain", new_manager.active_chains)
        chain = new_manager.active_chains["wolf_extinction_chain"]
        self.assertTrue(chain.is_pending)
        self.assertEqual(chain.due_day, 3)

        # Advance to Day 3
        self.event_bus.emit("day_changed", day=3)
        self.assertTrue(chain.is_executed)


if __name__ == "__main__":
    unittest.main()
