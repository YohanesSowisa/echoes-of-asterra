"""
Echoes of Asterra - Unit Tests for New Game+ / Mythos Expansion (Phase 5)
Tests:
1. Legacy Artifacts generation (custom weapon and armor named after hero accomplishments).
2. Multi-generational NPC dialogue lore referencing past hero decisions and deeds.
3. World State & Faction Warfare territory inheritance across runs.
4. Procedural dungeon integration spawning inherited legacy artifacts.
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
from rpg.mythos import MythosManager
from rpg.mythos_reader import MythosReader
from rpg.faction_war import FactionWarManager
from rpg.constants import FACTION_KNIGHTS, DUNGEON_CRYPT
from rpg.dungeon_gen import DungeonGenerator
from rpg.equipment import Equipment
from rpg.items import create_item


class DummyPlayer:
    def __init__(self):
        self.name = "Arthur"
        self.level = 8
        self.gold = 300
        self.atk = 24
        self.defense = 14
        self.magic = 12
        self.equipment = Equipment()
        self.equipment.slots["weapon"] = create_item("Steel Blade")
        self.equipment.slots["chest"] = create_item("Leather Chest")
        self.donated_shields = True
        self.greed_curse_active = False


class DummyWorldState:
    def __init__(self):
        self.day = 12
        self.season = "autumn"
        self.prosperity = 65.0


class DummyReputationManager:
    def __init__(self):
        self.active_title = "Savior of Asterra"


class DummyFactions:
    def __init__(self):
        self.rep = {"knights": 45, "hunters": 15, "merchants": 20}

    def get_reputation(self, fac: str) -> int:
        return self.rep.get(fac, 0)

    def modify_reputation(self, fac: str, amount: int) -> None:
        self.rep[fac] = self.rep.get(fac, 0) + amount


class DummyGame:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.player = DummyPlayer()
        self.world_state = DummyWorldState()
        self.reputation_manager = DummyReputationManager()
        self.factions = DummyFactions()
        self.faction_war = FactionWarManager()
        self.mythos_manager = MythosManager()
        # Clean memory records for isolated testing
        self.mythos_manager.records = []
        self.mythos_reader = MythosReader(self)


class TestMythosExpansion(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.game = DummyGame(self.event_bus)

    def test_record_run_stores_legacy_artifacts_and_dominant_faction(self):
        """Ending a run must record both legacy weapon and armor artifacts, plus dominant war faction."""
        # Set Knights control over 3 points
        fw = self.game.faction_war
        fw.control_points["forest_crossroads"].controlling_faction = FACTION_KNIGHTS
        fw.control_points["lake_pier"].controlling_faction = FACTION_KNIGHTS
        fw.control_points["ruins_plaza"].controlling_faction = FACTION_KNIGHTS

        record = self.game.mythos_manager.record_run(self.game, end_cause="Vanquished Shadow Overlord")

        # Verify hero metadata
        self.assertEqual(record["hero_name"], "Arthur")
        self.assertEqual(record["hero_title"], "Savior of Asterra")
        self.assertEqual(record["days_lived"], 12)
        self.assertEqual(record["dominant_war_faction"], FACTION_KNIGHTS)

        # Verify legacy artifacts
        self.assertIn("legacy_artifacts", record)
        self.assertEqual(len(record["legacy_artifacts"]), 2)
        
        relic_weapon = record["relic_weapon"]
        relic_armor = record["relic_armor"]
        self.assertIn("Ancestral", relic_weapon["name"])
        self.assertIn("Arthur", relic_armor["name"])
        self.assertGreaterEqual(relic_weapon["stats"]["atk"], 28)
        self.assertGreaterEqual(relic_armor["stats"]["def"], 17)

    def test_multigeneration_npc_dialogue_lore(self):
        """MythosReader must construct multi-generational folklore dialogues for town NPCs."""
        # Record a past run
        self.game.mythos_manager.record_run(self.game, end_cause="Ascended to Legend")

        nodes = self.game.mythos_reader.build_legend_dialogue_nodes()
        self.assertGreaterEqual(len(nodes), 4)

        node_map = {n.id: n for n in nodes}
        self.assertIn("eldrin_mythos_legend", node_map)
        self.assertIn("dennis_mythos_legend", node_map)
        self.assertIn("mira_mythos_legend", node_map)
        self.assertIn("faye_mythos_legend", node_map)

        # Verify folklore contents reference past hero
        self.assertIn("Arthur", node_map["eldrin_mythos_legend"].text)
        self.assertIn("Arthur", node_map["dennis_mythos_legend"].text)
        self.assertIn("Knights", node_map["mira_mythos_legend"].text)
        self.assertIn("Arthur", node_map["faye_mythos_legend"].text)

    def test_faction_war_territory_inheritance(self):
        """The winning faction from past runs starts with territory dominance and stability bonus."""
        self.game.mythos_manager.record_run(self.game, end_cause="Completed Era")

        # Initialize fresh faction war manager
        new_fw = FactionWarManager()
        dominant = new_fw.apply_mythos_inheritance(self.game.mythos_manager)

        self.assertEqual(dominant, FACTION_KNIGHTS)
        self.assertEqual(new_fw.control_points["forest_crossroads"].controlling_faction, FACTION_KNIGHTS)
        self.assertEqual(new_fw.control_points["forest_crossroads"].stability, 80.0)
        self.assertEqual(new_fw.control_points["lake_pier"].controlling_faction, FACTION_KNIGHTS)
        self.assertEqual(new_fw.control_points["lake_pier"].stability, 80.0)

        # World buff summary verification
        summary = self.game.mythos_reader.apply_historical_world_buffs()
        self.assertEqual(summary["dominant_faction"], FACTION_KNIGHTS)
        self.assertTrue(summary["territory_inherited"])

    def test_dungeon_procedural_generation_spawns_legacy_artifacts(self):
        """Procedural dungeons must inject inherited ancestral artifacts into chest loot pools."""
        self.game.mythos_manager.record_run(self.game, end_cause="Vanquished Darkness")

        # Depth 1 floor
        floor_1 = DungeonGenerator.generate_floor(depth=1, seed=42, theme=DUNGEON_CRYPT)
        chest_0_loot_names = [item[0] for item in floor_1["chests"][0]["loot"]]
        self.assertTrue(any("Ancestral" in name for name in chest_0_loot_names))

        # Depth 2 floor
        floor_2 = DungeonGenerator.generate_floor(depth=2, seed=88, theme=DUNGEON_CRYPT)
        chest_0_loot_names_2 = [item[0] for item in floor_2["chests"][0]["loot"]]
        self.assertTrue(any("Arthur" in name or "Ancestral" in name for name in chest_0_loot_names_2))


if __name__ == "__main__":
    unittest.main()
