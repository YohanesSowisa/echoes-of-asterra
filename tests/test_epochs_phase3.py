"""
Unit tests for Pillar #4: The Cataclysm Epochs — Phase 3 (Generational Legacy State & Narrative Inheritance).
Tests Mythos-driven epoch inheritance from past hero runs, automatic starting epoch seeding,
generational crisis dialogues for Elder Eldrin, Dennis, and Silas, and end-to-end savegame persistence.
"""
import unittest
import os
import pygame
from typing import Any, Dict, List

from rpg.events import EventBus
from rpg.mythos import MythosManager
from rpg.epochs import (
    EpochManager,
    EPOCH_DEFAULT,
    EPOCH_DELUGE,
    EPOCH_SCORCHED,
    EPOCH_GLACIAL
)
from rpg.npc_memory import NPCMemoryManager


class MockWeather:
    def __init__(self):
        self.state = "clear"
    def set_weather(self, weather_type: str):
        self.state = weather_type
    def change_weather(self, weather_type: str):
        self.state = weather_type


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.weather = MockWeather()
        self.epoch_manager = EpochManager(self.event_bus)
        self.epoch_manager.game_reference = self
        self.conspiracy_manager = None
        self.pact_manager = None


class MockPlayer:
    def __init__(self, game):
        self.game = game


class TestEpochsPhase3(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.em = self.game.epoch_manager
        self.player = MockPlayer(self.game)
        self.mem_mgr = NPCMemoryManager()
        self.mem_mgr.register_event_listeners(self.game.event_bus)

    def test_mythos_get_inherited_starting_epoch(self):
        """Tests that MythosManager evaluates past run outcomes to infer next generational epoch."""
        mm = MythosManager()
        mm.records = []

        # 1. Empty records -> standard era
        self.assertEqual(mm.get_inherited_starting_epoch(), "standard")

        # 2. Hero died in Sunfire Ruins / Fire -> scorched epoch
        mm.records = [{
            "hero_name": "Hero Ignis",
            "end_cause": "Fell to volcanic flame in Sunfire Ruins",
            "events": []
        }]
        self.assertEqual(mm.get_inherited_starting_epoch(), "scorched")

        # 3. Hero drowned in Sunken Mire / Tide -> deluge epoch
        mm.records = [{
            "hero_name": "Hero Aquas",
            "end_cause": "Drowned during high tide in the Sunken Mire",
            "events": []
        }]
        self.assertEqual(mm.get_inherited_starting_epoch(), "deluge")

        # 4. Hero died in Granite Caverns / Frost -> glacial epoch
        mm.records = [{
            "hero_name": "Hero Boreas",
            "end_cause": "Frozen in Granite Cavern depths by frost beast",
            "events": []
        }]
        self.assertEqual(mm.get_inherited_starting_epoch(), "glacial")

        # 5. Hero died in Compromised Kingdom coup -> scorched epoch
        mm.records = [{
            "hero_name": "Hero Vane",
            "end_cause": "Fallen on Day 30",
            "events": [{
                "event_type": "CONSPIRACY_RESOLVED",
                "ending": "compromised_kingdom"
            }]
        }]
        self.assertEqual(mm.get_inherited_starting_epoch(), "scorched")

    def test_epoch_manager_determine_starting_epoch_from_mythos(self):
        """Tests that EpochManager automatically sets world state and weather from Mythos."""
        mm = MythosManager()
        mm.records = [{
            "hero_name": "Hero Mire",
            "end_cause": "Defeated by Tidal Leviathan in Sunken Mire",
            "events": []
        }]

        # Hook into EpochManager
        res = self.em.determine_starting_epoch_from_mythos(mm)
        self.assertEqual(res, EPOCH_DELUGE)
        self.assertEqual(self.em.current_epoch, EPOCH_DELUGE)
        self.assertEqual(self.game.weather.state, "rain")

        # Switch to Glacial history
        mm.records = [{
            "hero_name": "Hero Frost",
            "end_cause": "Lost in eternal winter blizzards",
            "events": []
        }]
        res = self.em.determine_starting_epoch_from_mythos(mm)
        self.assertEqual(res, EPOCH_GLACIAL)
        self.assertEqual(self.em.current_epoch, EPOCH_GLACIAL)
        self.assertEqual(self.game.weather.state, "snow")

    def test_generational_npc_dialogue_reactivity(self):
        """Tests that village NPCs speak with rich generational crisis dialogues for each epoch."""
        # 1. Deluge Epoch Dialogues
        self.em.set_epoch(EPOCH_DELUGE)
        d_eldrin = self.mem_mgr.get_dialogue_prefix("npc_eldrin", self.player)
        d_dennis = self.mem_mgr.get_dialogue_prefix("npc_dennis", self.player)
        d_silas = self.mem_mgr.get_dialogue_prefix("npc_silas", self.player)

        self.assertIn("great rains never ceased", d_eldrin)
        self.assertIn("Sunken Mire", d_eldrin)
        self.assertIn("damp air rusts my iron", d_dennis)
        self.assertIn("waterproof trade packs", d_silas)

        # 2. Scorched Epoch Dialogues
        self.em.set_epoch(EPOCH_SCORCHED)
        d_eldrin_s = self.mem_mgr.get_dialogue_prefix("npc_eldrin", self.player)
        d_dennis_s = self.mem_mgr.get_dialogue_prefix("npc_dennis", self.player)
        d_silas_s = self.mem_mgr.get_dialogue_prefix("npc_silas", self.player)

        self.assertIn("Ash rains from the heavens", d_eldrin_s)
        self.assertIn("molten fissures", d_eldrin_s)
        self.assertIn("volcanic fissures keeps my forge", d_dennis_s)
        self.assertIn("ash clouds", d_silas_s)

        # 3. Glacial Epoch Dialogues
        self.em.set_epoch(EPOCH_GLACIAL)
        d_eldrin_g = self.mem_mgr.get_dialogue_prefix("npc_eldrin", self.player)
        d_dennis_g = self.mem_mgr.get_dialogue_prefix("npc_dennis", self.player)
        d_silas_g = self.mem_mgr.get_dialogue_prefix("npc_silas", self.player)

        self.assertIn("frost came with the great blizzard", d_eldrin_g)
        self.assertIn("hammer clings to cold steel", d_dennis_g)
        self.assertIn("Thermal cloaks", d_silas_g)

    def test_full_pillar4_save_load_lifecycle(self):
        """Tests complete epoch serialization and deserialization across multiple switches."""
        self.em.set_epoch(EPOCH_SCORCHED)
        state_dict = self.em.to_dict()
        self.assertEqual(state_dict["current_epoch"], EPOCH_SCORCHED)

        new_em = EpochManager()
        new_em.from_dict(state_dict)
        self.assertEqual(new_em.current_epoch, EPOCH_SCORCHED)
        self.assertEqual(new_em.get_current_epoch_name(), "The Scorched Blight (Zaman Bara Api)")


if __name__ == "__main__":
    unittest.main()
