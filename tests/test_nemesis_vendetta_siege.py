"""
Echoes of Asterra - Unit Tests for Nemesis Vendetta Sieges (Round 2 Feature #1)
Tests:
1. Siege trigger conditions (Lv.4+ or aggressive traits: Bloodthirsty, Cunning, Hero Slayer).
2. Inter-siege cooldown enforcement (min 5 days gap between sieges).
3. Active siege leader matching (active_siege_id guard on nemesis_killed).
4. Direct UI Notifications on siege start and final-day emergency countdown warning.
5. Progression behavior when Captain is at maximum cap (Lv.10, 3 traits).
6. Victory resolution (gold reward, stability restoration, prosperity boost, Mythos record, triumph rumor).
7. Defeat/Timeout resolution (territory fallen to bandits, stability drop, prosperity penalty, captain promotion).
8. Serialization roundtrip and schema v4 -> v5 backward-compatible auto-migration.
9. Manager reset lifecycle.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1024, 768))

from rpg.events import EventBus
from rpg.nemesis import (
    NemesisManager, NemesisCaptain, VendettaSiege,
    TRAIT_BLOODTHIRSTY, TRAIT_CUNNING, TRAIT_SLAYER, TRAIT_IRONHIDE
)
from rpg.world_state import WorldState
from rpg.rumors import RumorBoard
from rpg.faction_war import FactionWarManager
from rpg.mythos import MythosManager
from rpg.notification import NotificationManager, NotificationPriority
from rpg.save import SaveSystem, migrate_save, SAVE_SCHEMA_VERSION


class DummyGame:
    """Mock Game container for testing Nemesis Vendetta Siege integrations."""
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.living_world = type("LW", (), {})()
        self.living_world.world_state = WorldState()
        self.living_world.world_state.register_event_listeners(event_bus)
        self.living_world.rumors = RumorBoard(event_bus)
        self.living_world.faction_war = FactionWarManager()
        self.living_world.faction_war.register_event_listeners(event_bus)
        self.world_state = self.living_world.world_state
        self.notification_manager = NotificationManager()
        self.mythos_manager = MythosManager()
        self.player = type("Player", (), {
            "gold": 100,
            "hp": 100,
            "max_hp": 100
        })()
        self.enemies = []


class TestNemesisVendettaSiege(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.game = DummyGame(self.event_bus)
        self.nemesis_mgr = NemesisManager(self.event_bus)
        self.nemesis_mgr.game_reference = self.game

    def test_siege_trigger_conditions_and_single_active_cap(self):
        """Low-level captains cannot trigger sieges; Lv.4+ or trait captains can. Max 1 active siege."""
        # 1. Low level captain (Lv.2, no aggressive traits)
        low_cap = self.nemesis_mgr.create_nemesis("Weak Grunt", level=2, starting_traits=[TRAIT_IRONHIDE])
        res_low = self.nemesis_mgr.check_vendetta_siege_triggers(current_day=1, force_trigger=True)
        self.assertIsNone(res_low)

        # 2. High level captain (Lv.5)
        high_cap = self.nemesis_mgr.create_nemesis("Warlord Vex", level=5, starting_traits=[TRAIT_BLOODTHIRSTY])
        siege = self.nemesis_mgr.check_vendetta_siege_triggers(current_day=1, force_trigger=True)
        self.assertIsNotNone(siege)
        self.assertEqual(siege.captain_id, high_cap.captain_id)
        self.assertTrue(siege.is_active)
        self.assertEqual(self.nemesis_mgr.active_siege, siege)

        # 3. Attempting to trigger another siege while one is active returns None (max 1 active cap)
        second_cap = self.nemesis_mgr.create_nemesis("Zarok the Cruel", level=6, starting_traits=[TRAIT_SLAYER])
        res_blocked = self.nemesis_mgr.check_vendetta_siege_triggers(current_day=1, force_trigger=True)
        self.assertIsNone(res_blocked)

    def test_inter_siege_cooldown_enforcement(self):
        """After resolving a siege, a 5-day cooldown must elapse before another siege can trigger."""
        captain = self.nemesis_mgr.create_nemesis("Grask the Bloodthirsty", level=4, starting_traits=[TRAIT_BLOODTHIRSTY])
        siege = self.nemesis_mgr.trigger_vendetta_siege(captain.captain_id, current_day=1)
        self.assertIsNotNone(siege)

        # Resolve siege on Day 2
        self.nemesis_mgr.resolve_vendetta_siege(siege.siege_id, outcome="victory", player=self.game.player, current_day=2)
        self.assertIsNone(self.nemesis_mgr.active_siege)
        self.assertEqual(self.nemesis_mgr.last_siege_resolved_day, 2)

        # Days 3, 4, 5, 6 are inside the 5-day cooldown window (2 + 5 = 7)
        for day in range(3, 7):
            res = self.nemesis_mgr.check_vendetta_siege_triggers(current_day=day, force_trigger=False)
            self.assertIsNone(res, f"Siege should be blocked on cooldown Day {day}")

        # Day 7 (day 7 - 2 = 5 >= 5) allows triggering
        res_ready = self.nemesis_mgr.check_vendetta_siege_triggers(current_day=7, force_trigger=True)
        self.assertIsNotNone(res_ready)

    def test_active_siege_id_matching_guard(self):
        """Only defeating the specific siege leader resolves the active siege; unrelated kills do not."""
        siege_cap = self.nemesis_mgr.create_nemesis("Siege Commander", level=5, starting_traits=[TRAIT_CUNNING])
        other_cap = self.nemesis_mgr.create_nemesis("Wandering Bandit", level=3)

        siege = self.nemesis_mgr.trigger_vendetta_siege(siege_cap.captain_id, current_day=1)
        self.assertIsNotNone(siege)
        self.assertTrue(self.nemesis_mgr.active_siege.is_active)

        # Killing unrelated captain with mismatched active_siege_id does NOT resolve the siege
        self.event_bus.emit(
            "nemesis_killed",
            captain_id=other_cap.captain_id,
            captain_name=other_cap.name,
            active_siege_id="mismatched_siege_99",
            killer=self.game.player
        )
        self.assertTrue(self.nemesis_mgr.active_siege.is_active)

        # Killing the siege leader with matching active_siege_id DOES resolve the siege
        self.event_bus.emit(
            "nemesis_killed",
            captain_id=siege_cap.captain_id,
            captain_name=siege_cap.name,
            active_siege_id=siege.siege_id,
            killer=self.game.player
        )
        self.assertIsNone(self.nemesis_mgr.active_siege)
        self.assertEqual(self.nemesis_mgr.siege_history[-1].outcome, "victory")

    def test_ui_notifications_and_countdown_warnings(self):
        """Guaranteed UI toasts pushed on siege start and final day countdown emergency."""
        captain = self.nemesis_mgr.create_nemesis("Drakar the Butcher", level=4, starting_traits=[TRAIT_BLOODTHIRSTY])
        self.game.notification_manager.active_toasts.clear()
        self.game.notification_manager.toast_queue.clear()

        # Trigger siege
        siege = self.nemesis_mgr.trigger_vendetta_siege(captain.captain_id, target_territory="forest", current_day=1)
        self.assertIsNotNone(siege)

        # Check siege start notification
        all_toasts = self.game.notification_manager.active_toasts + self.game.notification_manager.toast_queue
        start_toasts = [n for n in all_toasts if "VENDETTA SIEGE" in n.message]
        self.assertGreaterEqual(len(start_toasts), 1)
        self.assertEqual(start_toasts[0].priority, NotificationPriority.HIGH)

        # Day tick 1 (2 days remaining)
        self.nemesis_mgr.update_siege_day_tick(current_day=2)
        self.assertEqual(siege.days_remaining, 2)

        # Day tick 2 (1 day remaining -> Critical Emergency Toast)
        self.nemesis_mgr.update_siege_day_tick(current_day=3)
        self.assertEqual(siege.days_remaining, 1)
        all_toasts_later = self.game.notification_manager.active_toasts + self.game.notification_manager.toast_queue
        emerg_toasts = [n for n in all_toasts_later if "SIEGE EMERGENCY" in n.message]
        self.assertGreaterEqual(len(emerg_toasts), 1)
        self.assertEqual(emerg_toasts[0].priority, NotificationPriority.CRITICAL)

    def test_captain_at_maximum_progression_cap(self):
        """Captains at Lv.10 and 3 traits can trigger sieges, but strictly never exceed caps."""
        max_cap = self.nemesis_mgr.create_nemesis(
            "Overlord Morzog",
            level=10,
            starting_traits=[TRAIT_BLOODTHIRSTY, TRAIT_CUNNING, TRAIT_SLAYER]
        )
        self.assertEqual(max_cap.level, 10)
        self.assertEqual(len(max_cap.traits), 3)

        # Attempting further level up respects hard cap
        max_cap.level_up(2)
        self.assertEqual(max_cap.level, 10)
        self.assertEqual(len(max_cap.traits), 3)

        # Max cap captain can still trigger a siege
        siege = self.nemesis_mgr.trigger_vendetta_siege(max_cap.captain_id, current_day=5)
        self.assertIsNotNone(siege)

        # If siege times out in defeat, captain cannot exceed Lv.10 or 3 traits
        self.nemesis_mgr.resolve_vendetta_siege(siege.siege_id, outcome="defeat", current_day=8)
        self.assertEqual(max_cap.level, 10)
        self.assertEqual(len(max_cap.traits), 3)

    def test_siege_victory_resolution_effects(self):
        """Victory grants bonus gold, restores territory stability and prosperity, records in Mythos, and seeds rumor."""
        captain = self.nemesis_mgr.create_nemesis("Brog Bonebreaker", level=4)
        siege = self.nemesis_mgr.trigger_vendetta_siege(captain.captain_id, target_territory="forest", current_day=1)

        # Faction War stability before victory
        cp = self.game.living_world.faction_war.control_points["forest_crossroads"]
        cp.stability = 40.0
        init_gold = self.game.player.gold
        init_prosp = self.game.world_state.prosperity

        # Resolve as victory
        res = self.nemesis_mgr.resolve_vendetta_siege(siege.siege_id, outcome="victory", player=self.game.player, current_day=2)
        self.assertTrue(res)

        # Checks
        self.assertEqual(self.game.player.gold, init_gold + 100)
        self.assertGreater(cp.stability, 40.0)
        self.assertGreaterEqual(self.game.world_state.prosperity, init_prosp + 10)

        # Mythos legacy entry
        events = self.game.mythos_manager.timeline
        siege_records = [e for e in events if e.get("event_type") == "vendetta_siege_defended"]
        self.assertGreaterEqual(len(siege_records), 1)

        # Rumor Mill entry
        rumors = self.game.living_world.rumors.rumors
        relief_rumors = [r for r in rumors.values() if "Relief of Forest" in r.topic]
        self.assertGreaterEqual(len(relief_rumors), 1)

    def test_siege_defeat_timeout_resolution_effects(self):
        """Defeat causes territory stability drop, faction shift to bandits, and captain promotion."""
        captain = self.nemesis_mgr.create_nemesis("Zarok the Cruel", level=4)
        siege = self.nemesis_mgr.trigger_vendetta_siege(captain.captain_id, target_territory="forest", current_day=1)

        cp = self.game.living_world.faction_war.control_points["forest_crossroads"]
        cp.stability = 80.0
        init_prosp = self.game.world_state.prosperity

        # Resolve as defeat
        res = self.nemesis_mgr.resolve_vendetta_siege(siege.siege_id, outcome="defeat", current_day=4)
        self.assertTrue(res)

        # Checks
        self.assertLess(cp.stability, 80.0)
        from rpg.constants import FACTION_BANDITS
        self.assertEqual(cp.controlling_faction, FACTION_BANDITS)
        self.assertLessEqual(self.game.world_state.prosperity, init_prosp - 10)
        self.assertEqual(captain.level, 5)
        self.assertIn("The Conqueror", captain.victory_titles)

    def test_siege_persistence_and_schema_v5_migration(self):
        """Serializing and deserializing NemesisManager preserves siege state and auto-migrates v4 schema."""
        captain = self.nemesis_mgr.create_nemesis("Malakor the Vile", level=5)
        siege = self.nemesis_mgr.trigger_vendetta_siege(captain.captain_id, target_territory="ruins", current_day=2)
        self.nemesis_mgr.last_siege_resolved_day = 1

        serialized = self.nemesis_mgr.to_dict()
        new_mgr = NemesisManager(self.event_bus)
        new_mgr.from_dict(serialized)

        self.assertIsNotNone(new_mgr.active_siege)
        self.assertEqual(new_mgr.active_siege.siege_id, siege.siege_id)
        self.assertEqual(new_mgr.active_siege.captain_name, captain.name)
        self.assertEqual(new_mgr.last_siege_resolved_day, 1)

        # Test Schema v4 -> v5 migration
        legacy_v4_data = {
            "save_schema_version": 4,
            "player": {"slot_name": "Hero", "level": 5},
            "nemesis": {"next_id": 2, "captains": {}},
            "living_world": {"nemesis": {"next_id": 2, "captains": {}}}
        }
        migrated = migrate_save(legacy_v4_data)
        self.assertEqual(migrated["save_schema_version"], SAVE_SCHEMA_VERSION)
        self.assertGreaterEqual(SAVE_SCHEMA_VERSION, 5)
        self.assertIn("active_siege", migrated["nemesis"])
        self.assertIn("last_siege_resolved_day", migrated["nemesis"])

    def test_siege_manager_reset(self):
        """Reset clears active siege, history, and resets cooldown trackers."""
        captain = self.nemesis_mgr.create_nemesis("Thraxis", level=4)
        self.nemesis_mgr.trigger_vendetta_siege(captain.captain_id, current_day=1)
        self.assertIsNotNone(self.nemesis_mgr.active_siege)

        self.nemesis_mgr.reset()
        self.assertIsNone(self.nemesis_mgr.active_siege)
        self.assertEqual(len(self.nemesis_mgr.siege_history), 0)
        self.assertEqual(self.nemesis_mgr.last_siege_resolved_day, -999)
        self.assertEqual(len(self.nemesis_mgr.captains), 0)


if __name__ == "__main__":
    unittest.main()
