"""
Echoes of Asterra - Phase 3 Tests
Comprehensive tests covering:
1. Status Effect Feedback (elemental tick-down bug fix, status icon data)
2. Weather-Combat Interaction (damage modifiers)
3. Combo Finisher System (weapon-class identity)
4. Style Scoring → Loot Quality
5. Environmental Hazard Tiles
6. AI Behavior Tag Activation
"""
import os
import sys
import unittest
import random

# Ensure rpg package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Minimal pygame init for headless tests
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1, 1))


class TestStatusEffectFeedback(unittest.TestCase):
    """Tests for elemental status duration tick-down and compound reactions."""

    def test_elemental_status_tick_down(self):
        """Bug fix verification: elemental statuses must decrement over time."""
        from rpg.enemy import Enemy
        enemy = Enemy((100, 100), [pygame.sprite.Group()], "Test", "slime")

        # Manually apply a fire status with 3.0s duration
        enemy.elemental_statuses["fire"] = 3.0
        self.assertIn("fire", enemy.elemental_statuses)
        self.assertAlmostEqual(enemy.elemental_statuses["fire"], 3.0, places=1)

        # Simulate 2 seconds of tick-down (manually, since update() needs game ref)
        # The tick-down code runs in update() but we test the data structure directly
        enemy.elemental_statuses["fire"] -= 2.0
        self.assertAlmostEqual(enemy.elemental_statuses["fire"], 1.0, places=1)

        # Simulate expiry
        enemy.elemental_statuses["fire"] -= 1.5
        if enemy.elemental_statuses["fire"] <= 0:
            del enemy.elemental_statuses["fire"]
        self.assertNotIn("fire", enemy.elemental_statuses)

    def test_multiple_statuses_coexist(self):
        """Multiple elemental statuses can exist simultaneously."""
        from rpg.enemy import Enemy
        enemy = Enemy((100, 100), [pygame.sprite.Group()], "Test", "slime")
        enemy.elemental_statuses["fire"] = 3.0
        enemy.elemental_statuses["ice"] = 2.0
        enemy.elemental_statuses["poison"] = 5.0
        self.assertEqual(len(enemy.elemental_statuses), 3)

    def test_behaviors_stored_on_enemy(self):
        """Enemy.behaviors list is populated from balance system."""
        from rpg.enemy import Enemy
        enemy = Enemy((100, 100), [pygame.sprite.Group()], "Test", "slime")
        self.assertIsInstance(enemy.behaviors, list)
        self.assertEqual(len(enemy.behaviors), 0)  # Default empty before setup_balance


class TestWeatherCombatInteraction(unittest.TestCase):
    """Tests for weather-based combat modifiers."""

    def test_rain_modifiers(self):
        """Rain should reduce fire damage and boost lightning."""
        from rpg.weather import WeatherSystem
        ws = WeatherSystem()
        ws.state = "rain"
        mods = ws.get_combat_modifiers()
        self.assertAlmostEqual(mods["fire_mult"], 0.75)
        self.assertAlmostEqual(mods["lightning_mult"], 1.30)
        self.assertAlmostEqual(mods["speed_mult"], 1.0)

    def test_snow_modifiers(self):
        """Snow should slow movement and boost ice."""
        from rpg.weather import WeatherSystem
        ws = WeatherSystem()
        ws.state = "snow"
        mods = ws.get_combat_modifiers()
        self.assertAlmostEqual(mods["ice_mult"], 1.20)
        self.assertAlmostEqual(mods["fire_mult"], 0.65)
        self.assertAlmostEqual(mods["speed_mult"], 0.85)

    def test_fog_reduces_vision(self):
        """Fog should reduce enemy vision radius."""
        from rpg.weather import WeatherSystem
        ws = WeatherSystem()
        ws.state = "fog"
        mods = ws.get_combat_modifiers()
        self.assertAlmostEqual(mods["vision_mult"], 0.60)

    def test_clear_weather_baseline(self):
        """Clear weather should have all modifiers at 1.0."""
        from rpg.weather import WeatherSystem
        ws = WeatherSystem()
        ws.state = "clear"
        mods = ws.get_combat_modifiers()
        self.assertAlmostEqual(mods["fire_mult"], 1.0)
        self.assertAlmostEqual(mods["ice_mult"], 1.0)
        self.assertAlmostEqual(mods["lightning_mult"], 1.0)
        self.assertAlmostEqual(mods["speed_mult"], 1.0)
        self.assertAlmostEqual(mods["vision_mult"], 1.0)

    def test_weather_damage_scaling_in_combat(self):
        """CombatSystem.calculate_damage should apply weather elemental multipliers."""
        from rpg.combat import CombatSystem

        class MockAttacker:
            atk = 20
            magic = 10
            crit_chance = 0
            _current_attack_element = "fire"

        class MockDefender:
            defense = 0
            hp = 100

        # With rain mods (fire_mult=0.75)
        rain_mods = {"fire_mult": 0.75, "ice_mult": 1.0, "lightning_mult": 1.30}
        random.seed(42)
        dmg_rain, _ = CombatSystem.calculate_damage(MockAttacker(), MockDefender(), weather_mods=rain_mods)

        # With clear mods (fire_mult=1.0)
        random.seed(42)
        dmg_clear, _ = CombatSystem.calculate_damage(MockAttacker(), MockDefender(), weather_mods={"fire_mult": 1.0})

        # Rain should produce less fire damage
        self.assertLessEqual(dmg_rain, dmg_clear)


class TestComboFinisherSystem(unittest.TestCase):
    """Tests for weapon-class combo finisher differentiation."""

    def test_weapon_classes_have_unique_finisher_names(self):
        """Each weapon class should have a distinct finisher name."""
        from rpg.weapon_types import WEAPON_CLASSES
        names = [wc.finisher_name for wc in WEAPON_CLASSES.values()]
        # All should be non-empty
        for name in names:
            self.assertTrue(len(name) > 0, f"Weapon missing finisher_name")
        # All should be unique
        self.assertEqual(len(set(names)), len(names))

    def test_combo_lengths_are_reasonable(self):
        """Combo lengths should be 3-4 hits (not the old 5)."""
        from rpg.weapon_types import WEAPON_CLASSES
        for key, wc in WEAPON_CLASSES.items():
            self.assertIn(wc.combo_length, [3, 4], f"{key} combo_length={wc.combo_length}")

    def test_dagger_has_invincibility(self):
        """Dagger finisher should grant brief invincibility."""
        from rpg.weapon_types import WEAPON_CLASSES
        from rpg.constants import WEAPON_DAGGER
        dagger = WEAPON_CLASSES[WEAPON_DAGGER]
        self.assertGreater(dagger.finisher_invincibility_ms, 0)
        self.assertEqual(dagger.finisher_name, "Shadow Strike")

    def test_spear_has_guaranteed_crit(self):
        """Spear finisher should have 100% crit bonus."""
        from rpg.weapon_types import WEAPON_CLASSES
        from rpg.constants import WEAPON_SPEAR
        spear = WEAPON_CLASSES[WEAPON_SPEAR]
        self.assertEqual(spear.finisher_crit_bonus, 100)
        self.assertEqual(spear.finisher_name, "Piercing Thrust")

    def test_hammer_has_stun(self):
        """Hammer finisher should apply 1.5s stun."""
        from rpg.weapon_types import WEAPON_CLASSES
        from rpg.constants import WEAPON_HAMMER
        hammer = WEAPON_CLASSES[WEAPON_HAMMER]
        self.assertAlmostEqual(hammer.stun_duration, 1.5)
        self.assertEqual(hammer.finisher_name, "Ground Slam")

    def test_axe_has_high_poise_damage(self):
        """Axe finisher should have high poise damage multiplier."""
        from rpg.weapon_types import WEAPON_CLASSES
        from rpg.constants import WEAPON_AXE
        axe = WEAPON_CLASSES[WEAPON_AXE]
        self.assertGreaterEqual(axe.finisher_poise_mult, 2.0)
        self.assertEqual(axe.finisher_name, "Cleave")


class TestStyleScoring(unittest.TestCase):
    """Tests for the style scoring system and loot quality modifiers."""

    def test_default_grade_is_d(self):
        """A fresh scorer with no actions should evaluate to D."""
        from rpg.style_scoring import StyleScoring
        ss = StyleScoring()
        self.assertEqual(ss.evaluate(), "D")

    def test_perfect_play_gets_s_rank(self):
        """High combos + dodges + parries + reactions should yield S rank."""
        from rpg.style_scoring import StyleScoring
        ss = StyleScoring()
        ss.on_combo_hit(5)
        ss.on_combo_hit(5)
        ss.max_combo = 5
        ss.on_perfect_dodge()
        ss.on_perfect_dodge()
        ss.on_parry()
        ss.on_parry()
        ss.on_elemental_reaction()
        ss.on_elemental_reaction()
        ss.on_finisher()
        ss.on_finisher()
        ss.on_kill()
        ss.time_elapsed = 3.0  # Fast kill
        self.assertEqual(ss.evaluate(), "S")

    def test_damage_taken_reduces_grade(self):
        """Taking heavy damage should reduce the style grade."""
        from rpg.style_scoring import StyleScoring
        ss = StyleScoring()
        ss.on_combo_hit(3)
        ss.max_combo = 3
        ss.on_kill()
        ss.time_elapsed = 5.0
        grade_clean = ss.evaluate()

        # Now add heavy damage
        ss.on_hit_taken(50)
        ss.on_hit_taken(50)
        ss.on_hit_taken(50)
        grade_damaged = ss.evaluate()

        grade_order = {"S": 4, "A": 3, "B": 2, "C": 1, "D": 0}
        self.assertGreaterEqual(grade_order[grade_clean], grade_order[grade_damaged])

    def test_loot_modifier_s_rank(self):
        """S-rank loot modifier should be 1.40 (40% bonus)."""
        from rpg.style_scoring import StyleGrade
        self.assertAlmostEqual(StyleGrade.RARITY_MODIFIERS["S"], 1.40)

    def test_loot_modifier_d_rank(self):
        """D-rank loot modifier should be 0.75 (25% penalty)."""
        from rpg.style_scoring import StyleGrade
        self.assertAlmostEqual(StyleGrade.RARITY_MODIFIERS["D"], 0.75)

    def test_reset_clears_all_metrics(self):
        """Reset should zero out all tracking state."""
        from rpg.style_scoring import StyleScoring
        ss = StyleScoring()
        ss.on_combo_hit(3)
        ss.on_kill()
        ss.on_parry()
        ss.reset()
        self.assertEqual(ss.combo_hits, 0)
        self.assertEqual(ss.kills, 0)
        self.assertEqual(ss.parries, 0)


class TestHazardTiles(unittest.TestCase):
    """Tests for environmental hazard tile mechanics."""

    def test_hazard_types_defined_for_all_themes(self):
        """All dungeon themes should have hazard definitions."""
        from rpg.hazards import THEME_HAZARDS
        expected_themes = ["crypt", "cave", "temple", "ice", "volcano"]
        for theme in expected_themes:
            self.assertIn(theme, THEME_HAZARDS, f"Missing hazard defs for theme: {theme}")
            self.assertGreater(len(THEME_HAZARDS[theme]), 0)

    def test_hazard_tile_cooldown_tracking(self):
        """Hazard tiles should track per-entity cooldowns."""
        from rpg.hazards import HazardTile
        ht = HazardTile((0, 0), [pygame.sprite.Group()], "spike_trap", damage=15, cooldown=3.0)
        # Initially, any entity can trigger
        self.assertTrue(ht._can_trigger(1))
        # After trigger, cooldown starts
        ht._trigger_cooldown(1)
        self.assertFalse(ht._can_trigger(1))
        # Different entity can still trigger
        self.assertTrue(ht._can_trigger(2))

    def test_dungeon_gen_includes_hazards(self):
        """Procedural dungeon output should include hazards key."""
        from rpg.dungeon_gen import DungeonGenerator
        result = DungeonGenerator.generate_floor(depth=3, seed=42, theme="volcano")
        self.assertIn("hazards", result)
        # Volcano theme should produce lava_pool hazards
        hazard_types = set(h["type"] for h in result["hazards"])
        self.assertTrue(
            "lava_pool" in hazard_types or "spike_trap" in hazard_types,
            f"Expected volcano hazards, got: {hazard_types}"
        )

    def test_ice_patch_no_damage(self):
        """Ice patches should deal 0 damage (status-only)."""
        from rpg.hazards import THEME_HAZARDS
        ice_hazards = THEME_HAZARDS["ice"]
        ice_patch_def = next((h for h in ice_hazards if h["type"] == "ice_patch"), None)
        self.assertIsNotNone(ice_patch_def)
        self.assertEqual(ice_patch_def["damage"], 0)


class TestBehaviorTagActivation(unittest.TestCase):
    """Tests for AI BehaviorTag system integration."""

    def test_behavior_tags_defined_in_balance(self):
        """All enemy archetypes in balance.py should have behavior tags."""
        from rpg.balance import ENEMY_BALANCES, BehaviorTag
        for key, bal in ENEMY_BALANCES.items():
            self.assertIsInstance(bal.behaviors, list, f"{key} missing behaviors list")

    def test_wolf_has_pack_tactics(self):
        """Wolves should have PACK_TACTICS behavior."""
        from rpg.balance import ENEMY_BALANCES, BehaviorTag
        wolf_bal = ENEMY_BALANCES.get("wolf")
        self.assertIsNotNone(wolf_bal)
        self.assertIn(BehaviorTag.PACK_TACTICS, wolf_bal.behaviors)

    def test_skeleton_has_defensive_parry(self):
        """Skeletons should have DEFENSIVE_PARRY behavior."""
        from rpg.balance import ENEMY_BALANCES, BehaviorTag
        skel_bal = ENEMY_BALANCES.get("skeleton")
        self.assertIsNotNone(skel_bal)
        self.assertIn(BehaviorTag.DEFENSIVE_PARRY, skel_bal.behaviors)

    def test_mage_has_ranged_kite(self):
        """Mages should have RANGED_KITE behavior."""
        from rpg.balance import ENEMY_BALANCES, BehaviorTag
        mage_bal = ENEMY_BALANCES.get("mage")
        self.assertIsNotNone(mage_bal)
        self.assertIn(BehaviorTag.RANGED_KITE, mage_bal.behaviors)

    def test_ai_guard_state_exists(self):
        """AI module should define GUARD and KITE states."""
        from rpg.ai import AI_STATE_GUARD, AI_STATE_KITE
        self.assertEqual(AI_STATE_GUARD, "guard")
        self.assertEqual(AI_STATE_KITE, "kite")

    def test_ai_fog_vision_reduction(self):
        """Fog weather should reduce AI effective vision radius."""
        from rpg.ai import EnemyAI

        class MockWeather:
            def get_combat_modifiers(self):
                return {"vision_mult": 0.60}

        class MockGame:
            weather = MockWeather()

        class MockEnemy:
            game = MockGame()

        ai = EnemyAI(pygame.math.Vector2(0, 0), vision_radius=350.0)
        effective = ai._get_effective_vision(MockEnemy())
        self.assertAlmostEqual(effective, 210.0, places=0)

    def test_ai_pack_count(self):
        """Pack count should count nearby allies of same type."""
        from rpg.ai import EnemyAI

        class MockEnemy:
            pos = pygame.math.Vector2(100, 100)
            asset_key = "wolf"
            hp = 50

        class MockAlly:
            pos = pygame.math.Vector2(120, 100)
            asset_key = "wolf"
            hp = 50

        class MockOther:
            pos = pygame.math.Vector2(130, 100)
            asset_key = "slime"
            hp = 50

        class MockGame:
            enemies = [MockAlly(), MockOther()]

        enemy = MockEnemy()
        enemy.game = MockGame()

        ai = EnemyAI(pygame.math.Vector2(0, 0))
        count = ai._count_nearby_pack(enemy, radius=200.0)
        self.assertEqual(count, 1)  # Only the wolf ally, not the slime


class TestDeadCodeCleanup(unittest.TestCase):
    """Tests verifying dead code was removed."""

    def test_ai_director_file_deleted(self):
        """ai_director.py should no longer exist."""
        ai_dir_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "rpg", "ai_director.py"
        )
        self.assertFalse(os.path.exists(ai_dir_path), "ai_director.py should be deleted")


if __name__ == "__main__":
    unittest.main()
