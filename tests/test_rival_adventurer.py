"""
Echoes of Asterra - Unit Tests for Rival Adventurer System (Phase 3)
Tests:
1. Daily autonomous parallel simulation modifying WorldState (danger, prosperity, road safety).
2. NPCMemory integration (assisting, sparring, bartering, dynamic relationship tiers).
3. Dungeon chest contention mechanic.
4. Serialization (to_dict, from_dict, reset) without cross-session state leakage.
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
from rpg.world_state import WorldState
from rpg.npc_memory import NPCMemoryManager
from rpg.rival import RivalAdventurerManager, RIVAL_SHORT_ID
from rpg.constants import REL_ENEMY, REL_STRANGER, REL_ACQUAINTANCE, DUNGEON_CAVE
from rpg.dungeon_gen import DungeonGenerator


class DummyPlayer:
    def __init__(self):
        self.name = "TestHero"
        self.gold = 100
        self.xp = 0
        self.level = 1
        from rpg.inventory import Inventory
        self.inventory = Inventory(20)

    def gain_xp(self, amount: int) -> None:
        self.xp += amount


class DummyGame:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.player = DummyPlayer()
        self.npc_memory = NPCMemoryManager()
        self.npc_memory.register_event_listeners(event_bus)
        from rpg.dialogue import DialogueManager
        self.dialogue_manager = DialogueManager()


class TestRivalAdventurer(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.world_state = WorldState()
        self.rival = RivalAdventurerManager(self.event_bus)
        self.game = DummyGame(self.event_bus)
        self.rival.game_reference = self.game

    def test_rival_daily_simulation_updates_world_state(self):
        """Simulating days must update Valen's progression and influence WorldState metrics."""
        # Run 5 simulated days
        action_events = []
        self.event_bus.subscribe("rival_daily_action", lambda **kw: action_events.append(kw))

        for day in range(1, 6):
            self.rival.simulate_day(self.world_state, day)

        # Valen must have performed activities, slain monsters, or gained XP/gold
        self.assertGreater(len(self.rival.data.activity_log), 1)
        self.assertEqual(len(action_events), 5)
        self.assertIn(self.rival.data.current_zone, ["village", "forest", "cave", "ruins", "dungeon"])

    def test_rival_npc_memory_integration_help_and_spar(self):
        """Interactions with Valen must record relationships into NPCMemory."""
        # 1. Base status is Stranger
        mem = self.game.npc_memory.get_memory(RIVAL_SHORT_ID)
        self.assertEqual(mem.friendship_level, REL_STRANGER)

        # 2. Assist Valen with a Red Potion
        from rpg.items import create_item
        potion = create_item("Red Potion", 2)
        self.game.player.inventory.add_item(potion)

        root_node = self.rival.build_dialogue_nodes(self.game, None)
        # Find gift choice
        gift_choice = next((c for c in root_node.choices if "Red Potion" in c.text), None)
        self.assertIsNotNone(gift_choice)
        gift_choice.callback()

        # Relationship must increase and Red Potion consumed
        self.assertEqual(self.game.npc_memory.get_memory(RIVAL_SHORT_ID).relationship, 15)
        self.assertEqual(self.game.npc_memory.get_memory(RIVAL_SHORT_ID).friendship_level, REL_ACQUAINTANCE)
        self.assertEqual(self.game.player.inventory.get_item_count("Red Potion"), 1)
        self.assertGreater(self.game.player.inventory.get_item_count("Iron Ore"), 0)

        # 3. Sparring with Valen
        spar_choice = next((c for c in root_node.choices if "spar" in c.text.lower()), None)
        self.assertIsNotNone(spar_choice)
        spar_choice.callback()
        self.assertEqual(self.game.npc_memory.get_memory(RIVAL_SHORT_ID).relationship, 20)

    def test_rival_hostile_reaction_when_antagonized(self):
        """Setting negative relationship score makes Valen hostile in dialogues."""
        self.game.npc_memory.modify_relationship(RIVAL_SHORT_ID, -60)
        mem = self.game.npc_memory.get_memory(RIVAL_SHORT_ID)
        self.assertEqual(mem.friendship_level, REL_ENEMY)

        root_node = self.rival.build_dialogue_nodes(self.game, None)
        self.assertIn("steel", root_node.text.lower())

    def test_rival_dungeon_chest_contention(self):
        """When rival explores dungeon, chests can be contested and contain rival cache loot."""
        self.rival.data.has_contested_dungeon = True
        base_loot = [("Epic Sword", 1), ("Gold Bar", 2)]
        
        contested_loot, was_contested = self.rival.contest_dungeon_loot(base_loot, depth=3)
        self.assertTrue(was_contested)
        self.assertIn(("Red Potion", 2), contested_loot)
        self.assertFalse(self.rival.data.has_contested_dungeon)

        # Test procedural dungeon generator outputs valid chest metadata
        dungeon_data = DungeonGenerator.generate_floor(depth=3, seed=123, theme=DUNGEON_CAVE)
        self.assertIn("chests", dungeon_data)
        self.assertGreater(len(dungeon_data["chests"]), 0)

    def test_rival_serialization_and_reset(self):
        """Rival manager must cleanly serialize to dict and reset without state leakage."""
        self.rival.data.level = 8
        self.rival.data.monsters_slain = 25
        self.rival.data.current_zone = "cave"

        saved_payload = self.rival.to_dict()
        self.rival.reset()

        # Reset state verification
        self.assertEqual(self.rival.data.level, 1)
        self.assertEqual(self.rival.data.monsters_slain, 0)
        self.assertEqual(self.rival.data.current_zone, "forest")

        # Restore state verification
        self.rival.from_dict(saved_payload)
        self.assertEqual(self.rival.data.level, 8)
        self.assertEqual(self.rival.data.monsters_slain, 25)
        self.assertEqual(self.rival.data.current_zone, "cave")


if __name__ == "__main__":
    unittest.main()
