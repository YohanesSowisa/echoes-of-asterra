"""
Echoes of Asterra - Phase 1 Audit & Foundation Unit Tests
Tests for:
1. Manager lifecycle methods (.reset(), .to_dict(), .from_dict()) across all simulation engines.
2. Single Source of Truth shop price calculation (Economy + Faction Tax + Settlement + Reputation + Friendship).
3. Price bounding safeguards (never negative, never 0, clamped strictly [0.30x, 3.00x]).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rpg.events import EventBus
from rpg.living_world import LivingWorldManager
from rpg.memory import MemoryManager, MemoryCategory
from rpg.social import ReputationManager
from rpg.factions import FactionManager
from rpg.npc_memory import NPCMemoryManager
from rpg.emergent_quests import EmergentQuestGenerator
from rpg.consequences import ConsequenceManager


class TestPhase1AuditFoundation(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.living_world = LivingWorldManager(self.event_bus)
        self.factions = FactionManager()
        self.npc_memory = NPCMemoryManager()

    def test_manager_lifecycle_resets(self):
        """All core managers must implement reset(), to_dict(), and from_dict() and reset clean."""
        # 1. MemoryManager
        mem_mgr = MemoryManager(self.event_bus)
        mem_mgr.add_memory("mem_test_1", MemoryCategory.SETTLEMENT.value, 80, actor="dennis", details={"text": "Donated 5 Iron"})
        self.assertEqual(len(mem_mgr.memories), 1)
        mem_mgr.reset()
        self.assertEqual(len(mem_mgr.memories), 0)

        # 2. ReputationManager
        rep_mgr = ReputationManager(self.event_bus)
        rep_mgr.modify_global_reputation(50)
        self.assertEqual(rep_mgr.global_reputation, 50)
        rep_mgr.reset()
        self.assertEqual(rep_mgr.global_reputation, 0)

        # 3. FactionManager
        fac_mgr = FactionManager()
        fac_mgr.modify_reputation("knights", 40)
        self.assertEqual(fac_mgr.get_reputation("knights"), 50)
        fac_mgr.reset()
        self.assertEqual(fac_mgr.get_reputation("knights"), 10)

        # 4. EmergentQuestGenerator
        eq_gen = EmergentQuestGenerator(self.event_bus)
        eq_gen.active_emergent_ids.add("test_emergent_q1")
        eq_data = eq_gen.to_dict()
        eq_gen.reset()
        self.assertEqual(len(eq_gen.active_emergent_ids), 0)
        eq_gen.from_dict(eq_data)
        self.assertIn("test_emergent_q1", eq_gen.active_emergent_ids)

        # 5. ConsequenceManager
        cq_mgr = ConsequenceManager(self.event_bus)
        cq_mgr.completed_chains.add("chain_1")
        cq_mgr.reset()
        self.assertEqual(len(cq_mgr.completed_chains), 0)

        # 6. LivingWorldManager
        self.living_world.world_state.day = 15
        self.living_world.reset()
        self.assertEqual(self.living_world.world_state.day, 1)

    def test_shop_price_single_source_of_truth(self):
        """Single Source of Truth price formula must correctly aggregate all modifiers."""
        base_price = 100

        # Baseline price (neutral state)
        base_mult = self.living_world.get_combined_price_multiplier("goods", "village", merchant_reputation=0, friendship_tier=0)
        final_base = self.living_world.get_final_shop_price(base_price, "goods", "village", merchant_reputation=0, friendship_tier=0)
        self.assertAlmostEqual(base_mult, 1.0, delta=0.05)
        self.assertEqual(final_base, 100)

        # High merchant reputation (+100 Exalted -> 20% discount) & friendship (+100 -> 15% discount)
        discounted_mult = self.living_world.get_combined_price_multiplier("goods", "village", merchant_reputation=100, friendship_tier=100)
        final_discounted = self.living_world.get_final_shop_price(base_price, "goods", "village", merchant_reputation=100, friendship_tier=100)
        self.assertLess(discounted_mult, 1.0)
        self.assertLess(final_discounted, 100)

    def test_shop_price_bounds_and_safety(self):
        """Price multiplier must NEVER yield negative, zero, or exploding prices."""
        base_price = 10

        # Extreme discount stacking
        extreme_cheap_mult = self.living_world.get_combined_price_multiplier("goods", "village", merchant_reputation=500, friendship_tier=500)
        final_cheap_price = self.living_world.get_final_shop_price(base_price, "goods", "village", merchant_reputation=500, friendship_tier=500)
        self.assertGreaterEqual(extreme_cheap_mult, 0.30)
        self.assertGreaterEqual(final_cheap_price, 1)

        # Extreme inflation/tax stacking
        extreme_expensive_mult = self.living_world.get_combined_price_multiplier("goods", "village", merchant_reputation=-500, friendship_tier=-500)
        final_expensive_price = self.living_world.get_final_shop_price(1000, "goods", "village", merchant_reputation=-500, friendship_tier=-500)
        self.assertLessEqual(extreme_expensive_mult, 3.00)
        self.assertLessEqual(final_expensive_price, 3000)


if __name__ == "__main__":
    unittest.main()
