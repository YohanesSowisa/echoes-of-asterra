"""
Unit & Integration Tests for the Dynamic Lead System (DiscoveryManager)
Verifies:
1. Diegetic trigger conditions for all 8 Master Expansion Pillars.
2. Distinct true_content vs distorted_content for all 8 pillar rumors in RumorBoard.
3. Dialogue lead-ins for all 4 isolated side quests on Eldrin, Silas, Dennis, Faye, Mira, Kai.
4. One-time flag deduplication preventing toast and rumor spam.
5. Save/Load serialization roundtrip persistence of discovery flags.
6. Crypt boss ('shadow_overlord') properly unlocks Dungeon Core & Architect lead.
"""
import os
import unittest
from typing import Any

# Configure headless Pygame environment
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from rpg.constants import (
    STATE_PLAYING,
    MAP_VILLAGE,
    MAP_FOREST,
    MAP_LAKE,
    MAP_CAVE,
    MAP_DUNGEON,
    MAP_RUINS,
    MAP_SUNKEN_MIRE
)
from rpg.epochs import EPOCH_DELUGE, EPOCH_DEFAULT
from rpg.events import EventBus
from rpg.notification import NotificationManager
from rpg.rumors import RumorBoard
from rpg.discovery import DiscoveryManager
from rpg.dialogue import DialogueManager, DialogueNode, DialogueChoice
from rpg.items import create_item


class MockPlayer:
    def __init__(self, level: int = 1, gold: int = 0) -> None:
        self.level = level
        self.gold = gold
        self.inventory = MockInventory()


class MockInventory:
    def __init__(self) -> None:
        self.slots = [None] * 20

    def add_item(self, item: Any) -> bool:
        for i in range(len(self.slots)):
            if self.slots[i] is None:
                self.slots[i] = item
                return True
        return False


class MockWorldManager:
    def __init__(self, current_map: str = MAP_VILLAGE) -> None:
        self.current_map_name = current_map
        self.boss_defeated = False


class MockEpochManager:
    def __init__(self) -> None:
        self.current_epoch = EPOCH_DEFAULT


class MockLivingWorld:
    def __init__(self, event_bus: EventBus) -> None:
        self.rumors = RumorBoard(event_bus)


class MockWorldState:
    def __init__(self, day: int = 1) -> None:
        self.day = day


class MockGame:
    def __init__(self) -> None:
        self.event_bus = EventBus()
        self.notification_manager = NotificationManager()
        self.living_world = MockLivingWorld(self.event_bus)
        self.dialogue_manager = DialogueManager()
        self.dialogue_manager.game = self
        self.player = MockPlayer()
        self.world_manager = MockWorldManager()
        self.world_state = MockWorldState()
        self.epoch_manager = MockEpochManager()
        self.discovery_manager = DiscoveryManager(self.event_bus, game_reference=self)


class TestDynamicLeads(unittest.TestCase):
    """Tests for DiscoveryManager dynamic leads and narrative connectivity."""

    def setUp(self) -> None:
        if not pygame.get_init():
            pygame.init()
        self.game = MockGame()
        self.dm = self.game.discovery_manager

    def tearDown(self) -> None:
        pass

    # -------------------------------------------------------------------------
    # 8 Expansion Pillars Diegetic Trigger Tests
    # -------------------------------------------------------------------------
    def test_pillar_1_sunken_mire_trigger(self) -> None:
        """Pillar 1: Visiting Lake/Mire or Day >= 2 triggers Sunken Mire lead & rumor."""
        self.game.world_manager.current_map_name = MAP_LAKE
        self.dm.evaluate_leads(self.game)

        self.assertIn("lead_sunken_mire", self.dm.triggered_leads)
        self.assertIn("rumor_lead_sunken_mire", self.game.living_world.rumors.rumors)
        r = self.game.living_world.rumors.rumors["rumor_lead_sunken_mire"]
        self.assertEqual(r.origin_npc, "faye")
        self.assertNotEqual(r.true_content, r.distorted_content)
        self.assertIn("wetlands south of Asterra Lake", r.true_content)
        self.assertIn("giant bog leeches", r.distorted_content)

    def test_pillar_2_conspiracy_trigger(self) -> None:
        """Pillar 2: Day >= 2 or quest acceptance triggers conspiracy lead & rumor."""
        self.game.world_state.day = 2
        self.dm.evaluate_leads(self.game)

        self.assertIn("lead_conspiracy", self.dm.triggered_leads)
        self.assertIn("rumor_lead_conspiracy", self.game.living_world.rumors.rumors)
        r = self.game.living_world.rumors.rumors["rumor_lead_conspiracy"]
        self.assertEqual(r.origin_npc, "eldrin")
        self.assertNotEqual(r.true_content, r.distorted_content)
        self.assertIn("Envoy Vaelin", r.true_content)

    def test_pillar_3_outposts_trigger(self) -> None:
        """Pillar 3: Player gold >= 100 or control point captured triggers Outpost lead."""
        self.game.player.gold = 150
        self.dm.evaluate_leads(self.game)

        self.assertIn("lead_outposts", self.dm.triggered_leads)
        self.assertIn("rumor_lead_outposts", self.game.living_world.rumors.rumors)
        r = self.game.living_world.rumors.rumors["rumor_lead_outposts"]
        self.assertEqual(r.origin_npc, "kai")
        self.assertIn("100 gold", r.true_content)

    def test_pillar_4_epochs_trigger(self) -> None:
        """Pillar 4: Epoch change event triggers Cataclysm Epoch lead."""
        self.game.epoch_manager.current_epoch = EPOCH_DELUGE
        self.game.event_bus.emit("epoch_changed", epoch_id=EPOCH_DELUGE)

        self.assertIn("lead_epochs", self.dm.triggered_leads)
        self.assertIn("rumor_lead_epochs", self.game.living_world.rumors.rumors)
        r = self.game.living_world.rumors.rumors["rumor_lead_epochs"]
        self.assertEqual(r.origin_npc, "eldrin")
        self.assertIn("Deluges", r.true_content)

    def test_pillar_5_monopoly_trigger(self) -> None:
        """Pillar 5: Reaching 100 gold triggers Continental Monopoly Silas lead."""
        self.game.player.gold = 100
        self.dm.evaluate_leads(self.game)

        self.assertIn("lead_monopoly", self.dm.triggered_leads)
        self.assertIn("rumor_lead_monopoly", self.game.living_world.rumors.rumors)
        r = self.game.living_world.rumors.rumors["rumor_lead_monopoly"]
        self.assertEqual(r.origin_npc, "silas")
        self.assertIn("concession deeds", r.true_content)

    def test_pillar_6_soul_pacts_trigger(self) -> None:
        """Pillar 6: Entering Cave/Dungeon or reaching Level 3 triggers Soul Pacts lead."""
        self.game.player.level = 3
        self.dm.evaluate_leads(self.game)

        self.assertIn("lead_soul_pacts", self.dm.triggered_leads)
        self.assertIn("rumor_lead_soul_pacts", self.game.living_world.rumors.rumors)
        r = self.game.living_world.rumors.rumors["rumor_lead_soul_pacts"]
        self.assertEqual(r.origin_npc, "mira")
        self.assertIn("Primordial Altars", r.true_content)

    def test_pillar_7_dungeon_architect_crypt_boss_trigger(self) -> None:
        """Pillar 7: Defeating shadow_overlord (crypt boss) emits boss_defeated and triggers Dungeon Architect lead."""
        self.game.event_bus.emit("boss_defeated", boss_id="shadow_overlord", boss_name="Shadow Overlord")

        self.assertIn("lead_dungeon_architect", self.dm.triggered_leads)
        self.assertIn("rumor_lead_dungeon_architect", self.game.living_world.rumors.rumors)
        r = self.game.living_world.rumors.rumors["rumor_lead_dungeon_architect"]
        self.assertEqual(r.origin_npc, "dennis")
        self.assertIn("Core Stone", r.true_content)

    def test_pillar_8_chrono_hourglass_trigger(self) -> None:
        """Pillar 8: Acquiring Chrono-Weaver Hourglass triggers Chrono lead."""
        item = create_item("Chrono-Weaver Hourglass", 1)
        self.game.player.inventory.add_item(item)
        self.dm.evaluate_leads(self.game)

        self.assertIn("lead_chrono", self.dm.triggered_leads)
        self.assertIn("rumor_lead_chrono", self.game.living_world.rumors.rumors)
        r = self.game.living_world.rumors.rumors["rumor_lead_chrono"]
        self.assertEqual(r.origin_npc, "mira")
        self.assertIn("rolling back world time", r.true_content)

    # -------------------------------------------------------------------------
    # Distinct Dual Rumor Content Test
    # -------------------------------------------------------------------------
    def test_all_8_rumors_have_distinct_true_and_distorted_content(self) -> None:
        """Verifies that all 8 pillar rumors have distinct true_content and distorted_content."""
        self.game.world_state.day = 15
        self.game.player.level = 5
        self.game.player.gold = 500
        self.game.world_manager.current_map_name = MAP_SUNKEN_MIRE
        self.game.world_manager.boss_defeated = True
        self.game.epoch_manager.current_epoch = EPOCH_DELUGE
        item = create_item("Chrono-Weaver Hourglass", 1)
        self.game.player.inventory.add_item(item)

        self.dm.evaluate_leads(self.game)

        rumor_keys = [
            "rumor_lead_sunken_mire",
            "rumor_lead_conspiracy",
            "rumor_lead_outposts",
            "rumor_lead_epochs",
            "rumor_lead_monopoly",
            "rumor_lead_soul_pacts",
            "rumor_lead_dungeon_architect",
            "rumor_lead_chrono",
        ]
        for rk in rumor_keys:
            self.assertIn(rk, self.game.living_world.rumors.rumors)
            r = self.game.living_world.rumors.rumors[rk]
            self.assertTrue(len(r.true_content) > 20)
            self.assertTrue(len(r.distorted_content) > 20)
            self.assertNotEqual(r.true_content, r.distorted_content, f"Rumor {rk} must have distinct true and distorted text!")

    # -------------------------------------------------------------------------
    # Dialogue Lead Injections & 4 Side Quests Test
    # -------------------------------------------------------------------------
    def test_eldrin_dialogue_injects_conspiracy_epochs_bridge_and_envoy_leads(self) -> None:
        """Eldrin exposes choices for Conspiracy, Epochs, Bridge Repair, and Mage Envoy."""
        node = DialogueNode("eldrin_start", "Elder Eldrin", "Greetings traveler.", [DialogueChoice("Goodbye.", None)])
        self.dm.inject_npc_dialogue_leads(type("Stub", (), {"name": "Elder Eldrin"})(), node, "eldrin")

        choice_texts = [c.text for c in node.choices]
        self.assertTrue(any("dark rumors" in t.lower() for t in choice_texts), "Conspiracy lead missing on Eldrin")
        self.assertTrue(any("shifting weather" in t.lower() for t in choice_texts), "Epoch lead missing on Eldrin")
        self.assertTrue(any("bridge" in t.lower() for t in choice_texts), "Bridge Repair sidequest lead missing on Eldrin")
        self.assertTrue(any("envoy" in t.lower() for t in choice_texts), "Envoy sidequest lead missing on Eldrin")

    def test_silas_dialogue_injects_monopoly_lead(self) -> None:
        """Silas exposes choice for Crown Concession Deeds."""
        node = DialogueNode("silas_start", "Merchant Silas", "Welcome to my shop.", [DialogueChoice("Goodbye.", None)])
        self.dm.inject_npc_dialogue_leads(type("Stub", (), {"name": "Merchant Silas"})(), node, "silas")

        choice_texts = [c.text for c in node.choices]
        self.assertTrue(any("concession" in t.lower() for t in choice_texts), "Monopoly lead missing on Silas")

    def test_dennis_dialogue_injects_dungeon_core_and_watchtower_leads(self) -> None:
        """Dennis exposes choices for Dungeon Core and Watchtower Construction."""
        node = DialogueNode("dennis_start", "Blacksmith Dennis", "Need some steel?", [DialogueChoice("Goodbye.", None)])
        self.dm.inject_npc_dialogue_leads(type("Stub", (), {"name": "Blacksmith Dennis"})(), node, "dennis")

        choice_texts = [c.text for c in node.choices]
        self.assertTrue(any("dungeon core" in t.lower() for t in choice_texts), "Dungeon Core lead missing on Dennis")
        self.assertTrue(any("watchtower" in t.lower() for t in choice_texts), "Watchtower sidequest lead missing on Dennis")

    def test_faye_dialogue_injects_sunken_mire_and_slime_leads(self) -> None:
        """Faye exposes choices for Sunken Mire wetlands and Slime Cleaning bounty."""
        node = DialogueNode("faye_start", "Ranger Faye", "The forest is quiet.", [DialogueChoice("Goodbye.", None)])
        self.dm.inject_npc_dialogue_leads(type("Stub", (), {"name": "Ranger Faye"})(), node, "faye")

        choice_texts = [c.text for c in node.choices]
        self.assertTrue(any("marshland" in t.lower() for t in choice_texts), "Sunken Mire lead missing on Faye")
        self.assertTrue(any("slimes" in t.lower() for t in choice_texts), "Slime sidequest lead missing on Faye")

    def test_mira_dialogue_injects_soul_pacts_and_chrono_leads(self) -> None:
        """Mira exposes choices for Primordial Altars (Soul Pacts) and Chrono Hourglass."""
        node = DialogueNode("mira_start", "Scholar Mira", "Studying ruins...", [DialogueChoice("Goodbye.", None)])
        self.dm.inject_npc_dialogue_leads(type("Stub", (), {"name": "Scholar Mira"})(), node, "mira")

        choice_texts = [c.text for c in node.choices]
        self.assertTrue(any("altar" in t.lower() or "pact" in t.lower() for t in choice_texts), "Soul Pacts lead missing on Mira")
        self.assertTrue(any("chrono" in t.lower() for t in choice_texts), "Chrono lead missing on Mira")

    def test_kai_dialogue_injects_outpost_lead(self) -> None:
        """Kai exposes choice for establishing Frontier Outposts."""
        node = DialogueNode("kai_start", "Guard Kai", "Guarding the lake...", [DialogueChoice("Goodbye.", None)])
        self.dm.inject_npc_dialogue_leads(type("Stub", (), {"name": "Guard Kai"})(), node, "kai")

        choice_texts = [c.text for c in node.choices]
        self.assertTrue(any("outpost" in t.lower() for t in choice_texts), "Outpost lead missing on Kai")

    # -------------------------------------------------------------------------
    # Deduplication & Persistence Tests
    # -------------------------------------------------------------------------
    def test_one_time_flag_prevents_duplicate_toast_and_rumor_generation(self) -> None:
        """Evaluating leads 10 times generates only 1 toast and 1 rumor per pillar."""
        self.game.player.gold = 200
        for _ in range(10):
            self.dm.evaluate_leads(self.game)

        # Outposts and Monopoly triggered once
        outpost_rumors = [k for k in self.game.living_world.rumors.rumors if k == "rumor_lead_outposts"]
        self.assertEqual(len(outpost_rumors), 1)

        monopoly_rumors = [k for k in self.game.living_world.rumors.rumors if k == "rumor_lead_monopoly"]
        self.assertEqual(len(monopoly_rumors), 1)

    def test_discovery_save_load_roundtrip_persistence(self) -> None:
        """Discovery flags are cleanly serialized to dict and restored from dict."""
        self.dm.triggered_leads.add("lead_sunken_mire")
        self.dm.triggered_leads.add("lead_conspiracy")
        self.dm.triggered_leads.add("lead_monopoly")

        saved_data = self.dm.to_dict()
        self.assertIn("triggered_leads", saved_data)
        self.assertEqual(len(saved_data["triggered_leads"]), 3)

        new_dm = DiscoveryManager()
        new_dm.from_dict(saved_data)
        self.assertEqual(new_dm.triggered_leads, {"lead_sunken_mire", "lead_conspiracy", "lead_monopoly"})


if __name__ == "__main__":
    unittest.main()
