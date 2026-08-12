"""
Echoes of Asterra - Phase 3 Reimagined Systems Tests
Tests for:
1. ConsequenceManager queueing and delayed day-tick execution
2. Wolf Overhunting → Deer Crop Devastation consequence chain
3. Dialogue node injection & emergent quest generation
4. Consequence state serialization
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
from rpg.consequences import ConsequenceManager, ConsequenceChain
from rpg.economy import EconomyManager
from rpg.ecology import EcologyManager
from rpg.world_state import WorldState
from rpg.dialogue import DialogueManager
from rpg.quests import QuestManager


class DummyGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.world_state = WorldState()
        self.dialogue_manager = DialogueManager()
        self.quest_manager = QuestManager()
        self.living_world = DummyLivingWorld()

class DummyLivingWorld:
    def __init__(self):
        self.economy = EconomyManager()
        self.ecology = EcologyManager()


class TestConsequenceEngine(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.cm = ConsequenceManager(self.event_bus)
        self.game = DummyGame()
        self.cm.game = self.game

    def test_queue_and_delayed_execution(self):
        """Consequence should be queued for due_day and only execute when day >= due_day."""
        queued = []
        executed = []
        self.event_bus.subscribe("consequence_queued", lambda chain_id, **kw: queued.append(chain_id))
        self.event_bus.subscribe("consequence_executed", lambda chain_id, **kw: executed.append(chain_id))

        # Queue on Day 1 with 2-day delay -> due on Day 3
        self.cm.queue_consequence("test_chain", delay_days=2, current_day=1, description="Test delayed action")
        self.assertIn("test_chain", queued)
        self.assertEqual(len(executed), 0)

        # Tick Day 2 -> Should NOT execute yet
        self.event_bus.emit("day_changed", day=2)
        self.assertEqual(len(executed), 0)

        # Tick Day 3 -> SHOULD execute now
        self.event_bus.emit("day_changed", day=3)
        self.assertIn("test_chain", executed)
        self.assertTrue(self.cm.active_chains["test_chain"].is_executed)

    def test_wolf_extinction_consequence_chain(self):
        """Depleting wolf population below threshold should trigger wolf_extinction_chain."""
        # Deplete wolf population in Ecology
        self.game.living_world.ecology.species["wolf"].current_population = 1

        # Emit enemy killed event for wolf
        self.event_bus.emit("enemy_killed", enemy_type="wolf")

        self.assertIn("wolf_extinction_chain", self.cm.active_chains)
        chain = self.cm.active_chains["wolf_extinction_chain"]
        self.assertTrue(chain.is_pending)
        self.assertEqual(chain.due_day, 3)  # Day 1 + 2

        # Advance clock to Day 3
        self.event_bus.emit("day_changed", day=3)

        self.assertTrue(chain.is_executed)

        # Verify Food stock was reduced by 40%
        food_stock = self.game.living_world.economy.stocks["food"].current_stock
        self.assertTrue(food_stock <= 40.0)

        # Verify Silas & Faye dialogue nodes were injected
        self.assertIn("silas_deer_crisis", self.game.dialogue_manager.nodes)
        self.assertIn("faye_deer_crisis", self.game.dialogue_manager.nodes)

        # Verify emergent quest "deer_culling_emergent" was generated & accepted
        self.assertIn("deer_culling_emergent", self.game.quest_manager.quests)
        q = self.game.quest_manager.quests["deer_culling_emergent"]
        from rpg.constants import QUEST_ACTIVE
        self.assertEqual(q.status, QUEST_ACTIVE)

    def test_consequence_serialization(self):
        """ConsequenceManager to_dict/from_dict should persist active and completed chains."""
        self.cm.queue_consequence("chain_a", delay_days=3, current_day=1)
        saved = self.cm.to_dict()

        new_cm = ConsequenceManager()
        new_cm.from_dict(saved)

        self.assertIn("chain_a", new_cm.active_chains)
        self.assertEqual(new_cm.active_chains["chain_a"].due_day, 4)


if __name__ == "__main__":
    unittest.main()
