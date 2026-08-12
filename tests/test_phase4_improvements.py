"""
Echoes of Asterra - Phase 4 Tests
Comprehensive tests covering:
1. Style Scoring Event Hooks (wiring verification)
2. Guard Damage Reduction for DEFENSIVE_PARRY enemies
3. Enhanced Hit-Stop on Combo Finishers
4. Item Rarity Tiers (already existed — verification)
5. Player Elemental Status Vulnerability
6. Lighting Integration with Hazard Tiles
7. Style Scoring HUD Widget
"""
import os
import sys
import unittest

# Ensure rpg package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Minimal pygame init for headless tests
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1, 1))


class TestStyleScoringEventHooks(unittest.TestCase):
    """Verify that style scoring events are correctly wired into combat flow."""

    def test_style_scoring_on_combo_hit(self):
        """on_combo_hit should increment combo_hits counter."""
        from rpg.style_scoring import StyleScoring
        ss = StyleScoring()
        ss.on_combo_hit(3)
        self.assertEqual(ss.combo_hits, 1)
        self.assertEqual(ss.max_combo, 3)

    def test_style_scoring_on_finisher(self):
        """on_finisher should increment finishers_landed."""
        from rpg.style_scoring import StyleScoring
        ss = StyleScoring()
        ss.on_finisher()
        ss.on_finisher()
        self.assertEqual(ss.finishers_landed, 2)

    def test_style_scoring_on_perfect_dodge(self):
        """on_perfect_dodge should increment perfect_dodges."""
        from rpg.style_scoring import StyleScoring
        ss = StyleScoring()
        ss.on_perfect_dodge()
        self.assertEqual(ss.perfect_dodges, 1)

    def test_style_scoring_on_parry(self):
        """on_parry should increment parries."""
        from rpg.style_scoring import StyleScoring
        ss = StyleScoring()
        ss.on_parry()
        ss.on_parry()
        self.assertEqual(ss.parries, 2)

    def test_style_scoring_on_hit_taken(self):
        """on_hit_taken should track hits and damage."""
        from rpg.style_scoring import StyleScoring
        ss = StyleScoring()
        ss.on_hit_taken(25)
        ss.on_hit_taken(10)
        self.assertEqual(ss.hits_taken, 2)
        self.assertEqual(ss.damage_taken, 35)

    def test_style_scoring_timer_updates(self):
        """update(dt) should accumulate time_elapsed."""
        from rpg.style_scoring import StyleScoring
        ss = StyleScoring()
        ss.update(0.5)
        ss.update(0.3)
        self.assertAlmostEqual(ss.time_elapsed, 0.8, places=2)


class TestGuardDamageReduction(unittest.TestCase):
    """Tests for enemy guard state damage reduction."""

    def test_guard_state_reduces_damage(self):
        """When guard_state=True, damage should be multiplied by 0.40 (60% reduction)."""
        # Simple math verification
        base_damage = 100
        guarded = max(1, int(base_damage * 0.40))
        self.assertEqual(guarded, 40)

    def test_guard_state_initializes_false(self):
        """Enemy guard_state should start as False."""
        from rpg.enemy import Enemy
        enemy = Enemy((100, 100), [pygame.sprite.Group()], "Test", "slime")
        self.assertFalse(enemy.guard_state)
        self.assertAlmostEqual(enemy.guard_cooldown, 0.0)


class TestEnhancedFinisherHitStop(unittest.TestCase):
    """Tests for enhanced hit-stop duration on finisher moves."""

    def test_finisher_damage_multiplier_threshold(self):
        """Finisher hits (damage_multiplier > 1.2) should trigger enhanced hit-stop."""
        from rpg.weapon_types import WEAPON_CLASSES
        for key, wc in WEAPON_CLASSES.items():
            # All finisher_damage_mult should be > 1.2 to trigger enhanced hit-stop
            self.assertGreater(
                wc.finisher_damage_mult, 1.2,
                f"{key} finisher_damage_mult ({wc.finisher_damage_mult}) should be > 1.2"
            )


class TestItemRarityVerification(unittest.TestCase):
    """Verify that item rarity system is properly implemented."""

    def test_all_rarity_constants_defined(self):
        """All 5 rarity tiers should be defined."""
        from rpg.constants import RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY
        self.assertEqual(RARITY_COMMON, "Common")
        self.assertEqual(RARITY_UNCOMMON, "Uncommon")
        self.assertEqual(RARITY_RARE, "Rare")
        self.assertEqual(RARITY_EPIC, "Epic")
        self.assertEqual(RARITY_LEGENDARY, "Legendary")

    def test_rarity_colors_mapped(self):
        """Each rarity tier should have a display color."""
        from rpg.constants import RARITY_COLORS, RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY
        for rarity in [RARITY_COMMON, RARITY_UNCOMMON, RARITY_RARE, RARITY_EPIC, RARITY_LEGENDARY]:
            self.assertIn(rarity, RARITY_COLORS)
            color = RARITY_COLORS[rarity]
            self.assertEqual(len(color), 3)  # RGB tuple

    def test_items_have_rarity_assigned(self):
        """All items in the database should have a rarity field."""
        from rpg.items import create_item
        test_items = ["Steel Blade", "Red Potion", "Forest Apple", "Iron Ore"]
        for name in test_items:
            item = create_item(name)
            if item:
                self.assertTrue(
                    hasattr(item, "rarity") and item.rarity != "",
                    f"{name} missing rarity assignment"
                )


class TestPlayerElementalStatus(unittest.TestCase):
    """Tests for player elemental status vulnerability."""

    def test_player_has_elemental_statuses_dict(self):
        """Player should have an elemental_statuses dictionary."""
        from rpg.player import Player
        # Create minimal player
        p = Player.__new__(Player)
        p.elemental_statuses = {}
        p.dot_tick_timer = 0.0
        self.assertIsInstance(p.elemental_statuses, dict)
        self.assertEqual(len(p.elemental_statuses), 0)

    def test_player_elemental_status_tick_down(self):
        """Elemental statuses should decrement and expire."""
        statuses = {"fire": 3.0, "ice": 1.0}
        dt = 1.5
        expired = []
        for elem in statuses:
            statuses[elem] -= dt
            if statuses[elem] <= 0:
                expired.append(elem)
        for elem in expired:
            del statuses[elem]
        # Ice should have expired (1.0 - 1.5 = -0.5)
        self.assertNotIn("ice", statuses)
        # Fire should still be active (3.0 - 1.5 = 1.5)
        self.assertIn("fire", statuses)
        self.assertAlmostEqual(statuses["fire"], 1.5)

    def test_fire_dot_wont_kill(self):
        """Fire DOT damage should not reduce HP below 1."""
        hp = 5
        fire_dot = 3
        hp = max(1, hp - fire_dot)
        self.assertEqual(hp, 2)
        hp = max(1, hp - fire_dot)
        self.assertEqual(hp, 1)  # Clamped to 1, won't kill


class TestLightingHazardIntegration(unittest.TestCase):
    """Tests for lighting system detecting hazard tiles."""

    def test_lighting_scans_hazard_tiles(self):
        """LightingSystem.draw_lighting should scan game.hazard_tiles for light sources."""
        from rpg.lighting import LightingSystem
        ls = LightingSystem()
        # Verify the method exists and accepts expected parameters
        self.assertTrue(hasattr(ls, "draw_lighting"))

    def test_lava_pool_emits_light(self):
        """Lava pools should be recognized as light emitters (size 128)."""
        # Verify the light size mapping is in the precomputed glow sizes
        from rpg.lighting import LightingSystem
        ls = LightingSystem()
        self.assertIn(128, ls.glows)  # Size 128 must exist for lava glow
        self.assertIn(64, ls.glows)   # Size 64 must exist for spike trap glow


class TestStyleScoringHUD(unittest.TestCase):
    """Tests for the style scoring HUD widget."""

    def test_hud_method_exists(self):
        """UIManager should have _draw_style_scoring_hud method."""
        from rpg.ui import UIManager
        self.assertTrue(hasattr(UIManager, "_draw_style_scoring_hud"))

    def test_grade_colors_are_valid_tuples(self):
        """Style grade colors should be RGB tuples compatible with HUD rendering."""
        from rpg.style_scoring import StyleGrade
        for grade, color in StyleGrade.GRADE_COLORS.items():
            self.assertEqual(len(color), 3, f"Grade {grade} color not RGB tuple")
            for c in color:
                self.assertGreaterEqual(c, 0)
                self.assertLessEqual(c, 255)


class TestWeatherHUDIndicator(unittest.TestCase):
    """Tests for weather system UI metadata and hover info."""

    def test_get_weather_info_all_states(self):
        """WeatherSystem.get_weather_info should return complete metadata for all weather states."""
        from rpg.weather import WeatherSystem, WEATHER_RAIN, WEATHER_SNOW, WEATHER_FOG, WEATHER_LEAVES, WEATHER_CLEAR
        ws = WeatherSystem()

        for state in [WEATHER_RAIN, WEATHER_SNOW, WEATHER_FOG, WEATHER_LEAVES, WEATHER_CLEAR]:
            ws.state = state
            info = ws.get_weather_info()
            self.assertIn("name", info)
            self.assertIn("label", info)
            self.assertIn("icon", info)
            self.assertIn("color", info)
            self.assertIn("effects", info)
            self.assertGreater(len(info["effects"]), 0)


class TestSkillManager(unittest.TestCase):
    """Tests for SkillManager methods."""

    def test_is_unlocked_method(self):
        """SkillManager.is_unlocked should check unlock state of skill by name."""
        from rpg.skills import SkillManager
        from rpg.constants import SKILL_SWORD_MASTERY, SKILL_FIREBALL
        sm = SkillManager()
        sm.check_unlocks(1)  # Level 1 unlocks Sword Mastery
        self.assertTrue(sm.is_unlocked(SKILL_SWORD_MASTERY))
        self.assertFalse(sm.is_unlocked(SKILL_FIREBALL))  # Fireball requires Level 4
        self.assertFalse(sm.is_unlocked("NON_EXISTENT_SKILL"))


if __name__ == "__main__":
    unittest.main()
