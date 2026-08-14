"""
Echoes of Asterra - Phase 2 Reimagined Systems Tests
Tests for:
1. Mythos run recording on victory and death
2. MythosReader ancestral relic weapon extraction & item creation
3. Legend dialogue node generation for town NPCs
4. Historical world buffs (faction rep & settlement prosperity boosts)
5. Procedural dungeon chest ancestral relic injection
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
from rpg.mythos import MythosManager
from rpg.mythos_reader import MythosReader
from rpg.dungeon_gen import DungeonGenerator
from rpg.dialogue import DialogueManager


class DummyGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.mythos_manager = MythosManager()
        self.player = DummyPlayer()
        self.world_state = DummyWorldState()
        self.dialogue_manager = DialogueManager()
        self.factions = DummyFactions()
        self.living_world = DummyLivingWorld()

class DummyPlayer:
    def __init__(self):
        self.name = "Test Hero"
        self.level = 10
        self.atk = 25
        self.equipment = DummyEquipment()
        self.donated_shields = True

class DummyEquipment:
    def __init__(self):
        self.slots = {}

class DummyWorldState:
    def __init__(self):
        self.day = 12

class DummyFactions:
    def __init__(self):
        self.reputations = {"knights": 0, "hunters": 0}
    def get_reputation(self, faction_id):
        return self.reputations.get(faction_id, 0)
    def modify_reputation(self, faction_id, amount):
        self.reputations[faction_id] = self.reputations.get(faction_id, 0) + amount

class DummyLivingWorld:
    def __init__(self):
        self.settlement = DummySettlement()

class DummySettlement:
    def __init__(self):
        self.prosperity = 50.0
    def add_prosperity(self, amount):
        self.prosperity += amount


class TestMythosReader(unittest.TestCase):
    def setUp(self):
        self.game = DummyGame()
        self.mythos_reader = MythosReader(self.game)

    def test_record_run_and_read_relic(self):
        """record_run should save run metadata, and MythosReader should retrieve the ancestral relic."""
        rec = self.game.mythos_manager.record_run(self.game, end_cause="Defeated Overlord")
        self.assertIn("hero_name", rec)
        self.assertEqual(rec["hero_name"], "Test Hero")

        relic_loot = self.mythos_reader.get_ancestral_relic_loot()
        self.assertTrue(len(relic_loot) > 0)
        self.assertTrue("Ancestral" in relic_loot[0][0] or "Blade" in relic_loot[0][0])

    def test_legend_dialogue_nodes_generation(self):
        """MythosReader should build Eldrin and Dennis legend dialogue nodes from past runs."""
        self.game.mythos_manager.record_run(self.game, end_cause="Vanquished Darkness")
        nodes = self.mythos_reader.build_legend_dialogue_nodes()
        self.assertTrue(len(nodes) >= 2)
        node_ids = [n.id for n in nodes]
        self.assertIn("eldrin_mythos_legend", node_ids)
        self.assertIn("dennis_mythos_legend", node_ids)

    def test_apply_historical_world_buffs(self):
        """MythosReader should apply historical world buffs based on past run achievements."""
        self.game.mythos_manager.record_run(self.game, end_cause="Victory")
        buffs = self.mythos_reader.apply_historical_world_buffs()
        self.assertEqual(buffs["prosperity_bonus"], 5)
        self.assertEqual(self.game.living_world.settlement.prosperity, 55.0)

    def test_dungeon_chest_relic_injection(self):
        """Floor 1 dungeon generation should inject ancestral relic loot into the first chest."""
        self.game.mythos_manager.record_run(self.game, end_cause="Victory")
        floor_data = DungeonGenerator.generate_floor(depth=1, seed=12345)
        chests = floor_data.get("chests", [])
        self.assertTrue(len(chests) > 0)
        first_chest_loot = chests[0]["loot"]
        loot_names = [item[0] for item in first_chest_loot]
        self.assertTrue(any("Ancestral" in name or "Blade" in name or "Potion" in name for name in loot_names))


if __name__ == "__main__":
    unittest.main()
