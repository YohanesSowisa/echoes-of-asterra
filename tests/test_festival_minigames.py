"""
Echoes of Asterra - Unit Tests for Seasonal Festival Minigames (Fitur #3)
Tests:
1. Festival activation and deactivation via WorldState world events.
2. Archery Contest: Gauge precision timing, ring hit grading, and 5-shot accumulation.
3. Harvest Sprint: Rapid crop gathering countdown and score calculation.
4. Dennis's Feast Challenge: Turn-based actions (Roast, Mead, Pace, Pass), fullness risk, and indigestion.
5. Reward tiers (Participant, Bronze, Silver, Gold), item rewards, and unique title acquisition.
6. RumorBoard dynamic gossip dissemination on gold tier achievement.
7. Seasonal records tracking across 4 seasons (Spring, Summer, Autumn, Winter).
8. Save/load serialization roundtrip and save schema v3 -> v4 migration.
9. FestivalManager reset lifecycle.
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
from rpg.festival import (
    FestivalManager,
    MINIGAME_ARCHERY, MINIGAME_HARVEST, MINIGAME_FEAST
)
from rpg.world_state import WorldState, EVENT_VILLAGE_FESTIVAL
from rpg.rumors import RumorBoard
from rpg.inventory import Inventory
from rpg.save import SaveSystem, migrate_save, SAVE_SCHEMA_VERSION


class DummyGame:
    """Mock Game container for festival minigames."""
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.living_world = type("LW", (), {})()
        self.living_world.world_state = WorldState()
        self.living_world.world_state.register_event_listeners(event_bus)
        self.living_world.rumors = RumorBoard(event_bus)
        self.world_state = self.living_world.world_state
        self.player = type("Player", (), {
            "gold": 50,
            "inventory": Inventory(20)
        })()
        self.reputation_manager = type("Rep", (), {"active_title": None})()
        self.player.game = self


class TestFestivalMinigames(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.game = DummyGame(self.event_bus)
        self.fest_mgr = FestivalManager(self.event_bus)
        self.fest_mgr.game_reference = self.game

    def test_festival_activation_via_event_bus(self):
        """Festival activates and deactivates via world event pub/sub."""
        self.assertFalse(self.fest_mgr.is_festival_active)

        # Start festival
        self.event_bus.emit("world_event_started", event_id=EVENT_VILLAGE_FESTIVAL)
        self.assertTrue(self.fest_mgr.is_festival_active)

        # End festival
        self.event_bus.emit("world_event_ended", event_id=EVENT_VILLAGE_FESTIVAL)
        self.assertFalse(self.fest_mgr.is_festival_active)

    def test_archery_contest_scoring(self):
        """Test Archery gauge timing precision and 5-shot round."""
        self.fest_mgr.start_archery_contest()
        self.assertEqual(self.fest_mgr.archery_shots_left, 5)
        self.assertEqual(self.fest_mgr.archery_accumulated_score, 0)

        # Shot 1: Bullseye (Center 0.50)
        score1, grade1 = self.fest_mgr.shoot_archery_arrow(0.50)
        self.assertEqual(score1, 100)
        self.assertEqual(grade1, "BULLSEYE!")
        self.assertEqual(self.fest_mgr.archery_shots_left, 4)

        # Shot 2: Inner Ring (0.40)
        score2, grade2 = self.fest_mgr.shoot_archery_arrow(0.40)
        self.assertEqual(score2, 75)
        self.assertEqual(grade2, "Inner Ring")

        # Shot 3: Outer Ring (0.25)
        score3, grade3 = self.fest_mgr.shoot_archery_arrow(0.25)
        self.assertEqual(score3, 45)
        self.assertEqual(grade3, "Outer Ring")

        # Shot 4: Edge (0.05)
        score4, grade4 = self.fest_mgr.shoot_archery_arrow(0.05)
        self.assertEqual(score4, 15)
        self.assertEqual(grade4, "Grazed Edge")

        # Shot 5: Bullseye (0.52)
        score5, grade5 = self.fest_mgr.shoot_archery_arrow(0.52)
        self.assertEqual(score5, 100)

        self.assertEqual(self.fest_mgr.archery_shots_left, 0)
        self.assertEqual(self.fest_mgr.archery_accumulated_score, 100 + 75 + 45 + 15 + 100)

    def test_harvest_sprint_evaluation(self):
        """Test Harvest Sprint score calculation based on crops and time left."""
        # 8 crops collected with 5.0 seconds remaining
        score_full = self.fest_mgr.evaluate_harvest_sprint(8, 5.0)
        self.assertEqual(score_full, 8 * 50 + 50)  # 450 pts

        # Partial crops collected with 0 seconds remaining
        score_partial = self.fest_mgr.evaluate_harvest_sprint(4, 0.0)
        self.assertEqual(score_partial, 200)

    def test_feast_challenge_actions_and_indigestion(self):
        """Test Feast challenge actions, indigestion penalty, and victory evaluation."""
        self.fest_mgr.start_feast_challenge()
        self.assertEqual(self.fest_mgr.feast_player_fullness, 0)
        self.assertEqual(self.fest_mgr.feast_player_score, 0)
        self.assertFalse(self.fest_mgr.feast_is_over)

        # 1. Action: Roast
        is_over, msg, score, fullness = self.fest_mgr.feast_action("roast")
        self.assertFalse(is_over)
        self.assertEqual(score, 25)
        self.assertGreater(fullness, 0)

        # 2. Action: Mead
        is_over, msg, score, fullness = self.fest_mgr.feast_action("mead")
        self.assertFalse(is_over)
        self.assertEqual(score, 40)

        # 3. Action: Pace
        old_full = fullness
        is_over, msg, score, fullness = self.fest_mgr.feast_action("pace")
        self.assertFalse(is_over)
        self.assertLess(fullness, old_full)

        # 4. Action: Pass
        is_over, msg, score, fullness = self.fest_mgr.feast_action("pass")
        self.assertTrue(is_over)

        # 5. Test Indigestion on Overeating
        self.fest_mgr.start_feast_challenge()
        self.fest_mgr.feast_player_fullness = 95
        is_over, msg, score, fullness = self.fest_mgr.feast_action("roast")
        self.assertTrue(is_over)
        self.assertIn("Indigestion", msg)

    def test_reward_tiers_and_rumor_propagation(self):
        """Verify high scores grant gold tier rewards, titles, and RumorBoard entries."""
        init_gold = self.game.player.gold
        res = self.fest_mgr.finalize_minigame_score(
            minigame_id=MINIGAME_ARCHERY,
            score=480,
            season="spring",
            player=self.game.player
        )

        self.assertEqual(res["tier"], "Gold")
        self.assertEqual(res["title"], "Asterra Marksman")
        self.assertEqual(self.game.reputation_manager.active_title, "Asterra Marksman")
        self.assertEqual(self.game.player.gold, init_gold + 80)

        # Verify rumor mill received gossip
        rumors = self.game.living_world.rumors.rumors
        archery_rumors = [r for k, r in rumors.items() if "Archery" in r.topic or "Archery" in r.true_content]
        self.assertGreaterEqual(len(archery_rumors), 1)

    def test_seasonal_records_tracking(self):
        """Seasonal best scores are tracked per season independently."""
        self.fest_mgr.finalize_minigame_score(MINIGAME_HARVEST, 350, season="spring")
        self.fest_mgr.finalize_minigame_score(MINIGAME_HARVEST, 420, season="autumn")

        self.assertEqual(self.fest_mgr.seasonal_records["spring"][MINIGAME_HARVEST], 350)
        self.assertEqual(self.fest_mgr.seasonal_records["autumn"][MINIGAME_HARVEST], 420)
        self.assertEqual(self.fest_mgr.high_scores[MINIGAME_HARVEST], 420)

    def test_save_load_persistence_and_schema_v4_migration(self):
        """Test festival serialization and schema v3 -> v4 auto-migration."""
        self.fest_mgr.seasonal_records["summer"]["archery"] = 490
        self.fest_mgr.high_scores["archery"] = 490
        self.fest_mgr.champion_titles_awarded.append("Asterra Marksman")

        serialized = self.fest_mgr.to_dict()
        new_mgr = FestivalManager(self.event_bus)
        new_mgr.from_dict(serialized)

        self.assertEqual(new_mgr.seasonal_records["summer"]["archery"], 490)
        self.assertEqual(new_mgr.high_scores["archery"], 490)
        self.assertIn("Asterra Marksman", new_mgr.champion_titles_awarded)

        # Schema v3 -> v4 Migration
        legacy_v3 = {
            "save_schema_version": 3,
            "player": {"slot_name": "Hero"},
            "living_world": {"world_state": {}}
        }
        migrated = migrate_save(legacy_v3)
        self.assertEqual(migrated["save_schema_version"], SAVE_SCHEMA_VERSION)
        self.assertIn("festival", migrated)
        self.assertIn("festival", migrated["living_world"])

    def test_festival_manager_reset(self):
        """Verify reset clears active minigame and seasonal high scores."""
        self.fest_mgr.high_scores["archery"] = 450
        self.fest_mgr.reset()
        self.assertEqual(self.fest_mgr.high_scores["archery"], 0)
        self.assertIsNone(self.fest_mgr.current_minigame)


if __name__ == "__main__":
    unittest.main()
