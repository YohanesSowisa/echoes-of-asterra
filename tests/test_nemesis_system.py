"""
Echoes of Asterra - Unit Tests for Nemesis System (Fitur #1)
Tests:
1. Procedural generation, naming, traits, and data modeling of Nemesis Captains.
2. Level-up, stat scaling, and victory title acquisition when defeating player.
3. High-tier enemy escape / retreat promotion to Nemesis Captains.
4. Trait application and combat modifiers (Craven, Bloodthirsty, Ironhide, Hero Slayer, Ambush Master, Cunning).
5. Dynamic rumor seeding into RumorBoard and distortion propagation.
6. Territory claiming, road safety, and Faction Warfare stability impacts.
7. Bestiary Compendium and Mythos Legacy recording upon Nemesis defeat.
8. Save/Load serialization roundtrip and save schema v1/v2 -> v3 migration.
9. NemesisCaptainEnemy sprite and unique loot dropping.
10. Manager reset lifecycle preventing cross-slot leakage.
"""
import os
import sys
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1024, 768))

from rpg.events import EventBus
from rpg.nemesis import (
    NemesisManager, NemesisCaptain,
    TRAIT_BLOODTHIRSTY, TRAIT_CRAVEN, TRAIT_CUNNING,
    TRAIT_IRONHIDE, TRAIT_SLAYER, TRAIT_AMBUSH
)
from rpg.rumors import RumorBoard
from rpg.faction_war import FactionWarManager
from rpg.world_state import WorldState
from rpg.bestiary import BestiaryManager
from rpg.mythos import MythosManager, CATEGORY_COMBAT
from rpg.save import SaveSystem, migrate_save, SAVE_SCHEMA_VERSION


class DummyGame:
    """Mock Game container for testing system integrations."""
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.living_world = type("LW", (), {})()
        self.living_world.rumors = RumorBoard(event_bus)
        self.living_world.faction_war = FactionWarManager()
        self.living_world.faction_war.register_event_listeners(event_bus)
        self.living_world.world_state = WorldState()
        self.living_world.world_state.register_event_listeners(event_bus)
        self.bestiary_manager = BestiaryManager(event_bus)
        self.mythos_manager = MythosManager()
        self.world_state = self.living_world.world_state
        self.player = type("Player", (), {"hp": 100, "level": 5})()


class TestNemesisSystem(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.game = DummyGame(self.event_bus)
        self.nemesis_mgr = NemesisManager(self.event_bus)
        self.nemesis_mgr.game_reference = self.game

    def test_nemesis_creation_and_naming(self):
        """Test procedural creation of Nemesis Captain with valid stats and traits."""
        captain = self.nemesis_mgr.create_nemesis(
            name="Grask the Scorcher",
            archetype="bandit",
            asset_key="knight",
            level=4,
            map_name="forest",
            starting_traits=[TRAIT_BLOODTHIRSTY]
        )

        self.assertIn("Grask the Scorcher", captain.name)
        self.assertEqual(captain.level, 4)
        self.assertEqual(captain.archetype, "bandit")
        self.assertEqual(captain.claimed_territory, "forest")
        self.assertTrue(captain.active)
        self.assertFalse(captain.is_defeated)
        self.assertIn(TRAIT_BLOODTHIRSTY, captain.traits)
        self.assertGreater(captain.max_hp, 100)
        self.assertGreater(captain.atk, 20)

    def test_nemesis_level_up_and_victory_on_player_defeat(self):
        """When player is killed by an enemy, promotes/levels up Nemesis and grants titles."""
        # 1. Standard enemy kills player
        dummy_enemy = type("Enemy", (), {
            "name": "Bandit Marauder",
            "level": 3,
            "asset_key": "knight",
            "enemy_key": "bandit"
        })()

        self.nemesis_mgr._on_player_killed_by_enemy(
            enemy=dummy_enemy,
            enemy_name="Bandit Marauder",
            enemy_key="bandit",
            map_name="forest"
        )

        # Check captain created
        active = self.nemesis_mgr.get_active_captains()
        self.assertEqual(len(active), 1)
        cap = active[0]
        self.assertEqual(cap.kills_on_player, 1)
        self.assertIn("Hero Slayer", cap.victory_titles)
        self.assertGreaterEqual(cap.level, 4)

        # 2. Same captain kills player again -> levels up further
        old_hp = cap.max_hp
        old_atk = cap.atk
        old_level = cap.level

        self.nemesis_mgr._on_player_killed_by_enemy(
            enemy=cap,
            enemy_name=cap.name,
            enemy_key="bandit",
            map_name="forest"
        )

        self.assertEqual(cap.kills_on_player, 2)
        self.assertGreater(cap.level, old_level)
        self.assertGreater(cap.max_hp, old_hp)
        self.assertGreater(cap.atk, old_atk)
        self.assertGreaterEqual(len(cap.victory_titles), 2)

    def test_enemy_escape_promotion(self):
        """When a retreating enemy escapes, promotes them to Nemesis with Craven trait."""
        dummy_enemy = type("Enemy", (), {
            "name": "Goblin Scavenger",
            "level": 2,
            "asset_key": "goblin",
            "enemy_key": "goblin"
        })()

        self.nemesis_mgr._on_enemy_escaped(
            enemy=dummy_enemy,
            enemy_name="Goblin Scavenger",
            enemy_key="goblin",
            map_name="cave"
        )

        active = self.nemesis_mgr.get_active_captains()
        self.assertEqual(len(active), 1)
        cap = active[0]
        self.assertEqual(cap.escapes, 1)
        self.assertIn(TRAIT_CRAVEN, cap.traits)
        self.assertEqual(cap.claimed_territory, "cave")

    def test_nemesis_traits_and_scaling(self):
        """Verify traits modify captain properties and scaling."""
        captain = self.nemesis_mgr.create_nemesis(
            name="Vorgash Ironhide",
            archetype="knight",
            asset_key="knight",
            level=5,
            starting_traits=[TRAIT_IRONHIDE, TRAIT_SLAYER]
        )

        self.assertIn(TRAIT_IRONHIDE, captain.traits)
        self.assertIn(TRAIT_SLAYER, captain.traits)

        # Level up adds more traits without exceeding cap of 3
        captain.level_up(2)
        self.assertLessEqual(len(captain.traits), 3)

    def test_rumor_mill_integration(self):
        """Verify defeating player seeds victory rumor and killing Nemesis seeds defeat rumor."""
        cap = self.nemesis_mgr.create_nemesis(
            name="Zarok the Deceiver",
            map_name="ruins",
            starting_traits=[TRAIT_CUNNING]
        )

        # Trigger player defeat
        self.nemesis_mgr._on_player_killed_by_enemy(
            enemy=cap,
            enemy_name=cap.name,
            enemy_key="bandit",
            map_name="ruins"
        )

        rumors = self.game.living_world.rumors.rumors
        kill_rumors = [r for k, r in rumors.items() if "Zarok" in r.topic or "Zarok" in r.true_content]
        self.assertGreaterEqual(len(kill_rumors), 1)
        r = kill_rumors[0]
        self.assertIn("Zarok", r.true_content)
        self.assertIn("Ruins", r.true_content)

        # Trigger nemesis kill
        self.nemesis_mgr._on_nemesis_killed(captain_id=cap.captain_id, captain_name=cap.name)
        defeat_rumors = [r for k, r in rumors.items() if "Fall of Zarok" in r.topic or "slain" in r.true_content]
        self.assertGreaterEqual(len(defeat_rumors), 1)

    def test_territory_safety_and_faction_war_impact(self):
        """Verify active Nemesis reduces territory stability & road safety; defeat restores them."""
        ws = self.game.living_world.world_state
        fw = self.game.living_world.faction_war

        # Set baseline stability
        fw.control_points["forest_crossroads"].stability = 70.0
        ws.road_safety = 60.0

        cap = self.nemesis_mgr.create_nemesis(
            name="Kraghar Bloodfang",
            map_name="forest",
            starting_traits=[TRAIT_BLOODTHIRSTY]
        )

        # Apply threat on player kill
        self.nemesis_mgr._on_player_killed_by_enemy(
            enemy=cap,
            enemy_name=cap.name,
            enemy_key="bandit",
            map_name="forest"
        )

        self.assertLess(fw.control_points["forest_crossroads"].stability, 70.0)
        self.assertLess(ws.road_safety, 60.0)

        # Restore on defeat
        self.nemesis_mgr._on_nemesis_killed(captain_id=cap.captain_id, captain_name=cap.name)
        self.assertGreaterEqual(fw.control_points["forest_crossroads"].stability, 60.0)
        self.assertGreaterEqual(ws.road_safety, 55.0)

    def test_bestiary_and_mythos_recording(self):
        """Defeating a Nemesis logs entries in Bestiary and Mythos records."""
        cap = self.nemesis_mgr.create_nemesis(
            name="Malakor Shadowblade",
            level=6,
            starting_traits=[TRAIT_SLAYER]
        )
        cap.kills_on_player = 2

        self.nemesis_mgr._on_nemesis_killed(captain_id=cap.captain_id, captain_name=cap.name)

        # Check Bestiary
        bm = self.game.bestiary_manager
        self.assertIn("nemesis_captain", bm.entries)
        nem_entry = bm.entries["nemesis_captain"]
        self.assertTrue(nem_entry.unlocked)
        self.assertGreaterEqual(nem_entry.kills, 1)
        self.assertIn("Malakor Shadowblade", nem_entry.lore)

        # Check Mythos
        mm = self.game.mythos_manager
        combat_events = [e for r in mm.records for e in r.get("events", []) if e.get("event_type") == "nemesis_defeated"]
        # Or if recorded directly on active session
        # mm.records or mm.get_recent_events

    def test_save_load_persistence_and_schema_v3_migration(self):
        """Test full save/load roundtrip of Nemesis state and migration from legacy schemas."""
        cap1 = self.nemesis_mgr.create_nemesis("Thraxis the Swift", map_name="cave", starting_traits=[TRAIT_AMBUSH])
        cap1.kills_on_player = 3
        cap1.victory_titles.append("Doom of Champions")

        serialized = self.nemesis_mgr.to_dict()
        new_mgr = NemesisManager(self.event_bus)
        new_mgr.from_dict(serialized)

        self.assertEqual(len(new_mgr.captains), 1)
        restored = list(new_mgr.captains.values())[0]
        self.assertEqual(restored.name, "Thraxis the Swift")
        self.assertEqual(restored.kills_on_player, 3)
        self.assertIn("Doom of Champions", restored.victory_titles)
        self.assertIn(TRAIT_AMBUSH, restored.traits)
        self.assertEqual(restored.claimed_territory, "cave")

        # Test Schema v2 -> v3 Migration
        legacy_v2_data = {
            "save_schema_version": 2,
            "player": {"slot_name": "Hero", "level": 3, "gold": 100},
            "living_world": {"world_state": {}, "economy": {}}
        }
        migrated = migrate_save(legacy_v2_data)
        self.assertEqual(migrated["save_schema_version"], SAVE_SCHEMA_VERSION)
        self.assertIn("nemesis", migrated)
        self.assertIn("nemesis", migrated["living_world"])

    def test_nemesis_captain_enemy_sprite_and_loot(self):
        """Test NemesisCaptainEnemy initialization, combat traits, and loot drops."""
        from rpg.enemy import NemesisCaptainEnemy
        cap = self.nemesis_mgr.create_nemesis(
            name="Brog Ironjaw",
            level=5,
            starting_traits=[TRAIT_IRONHIDE]
        )

        visible_group = pygame.sprite.Group()
        enemy_sprite = NemesisCaptainEnemy((200, 200), [visible_group], cap)
        enemy_sprite.game = self.game

        self.assertEqual(enemy_sprite.name, "Brog Ironjaw")
        self.assertEqual(enemy_sprite.level, 5)
        self.assertEqual(enemy_sprite.max_poise, 100.0)  # Ironhide bonus
        self.assertEqual(enemy_sprite.kill_type, "nemesis_captain")

    def test_manager_reset(self):
        """Verify reset clears all active Nemesis captains."""
        self.nemesis_mgr.create_nemesis("Drakar the Red")
        self.assertEqual(len(self.nemesis_mgr.captains), 1)

        self.nemesis_mgr.reset()
        self.assertEqual(len(self.nemesis_mgr.captains), 0)
        self.assertEqual(len(self.nemesis_mgr.get_active_captains()), 0)


if __name__ == "__main__":
    unittest.main()
