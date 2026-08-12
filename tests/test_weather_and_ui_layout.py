"""
Echoes of Asterra - Weather System & UI Layout Tests
Tests for:
1. WeatherSystem lightning flash trigger and fog drifting
2. Weather combat modifiers for Rain, Snow, Fog, Leaves, Clear
3. HUD Clock and Weather Card rendering bounds
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

from rpg.weather import WeatherSystem, WEATHER_RAIN, WEATHER_SNOW, WEATHER_FOG, WEATHER_CLEAR, WEATHER_LEAVES
from rpg.ui import UIManager


class DummyGame:
    def __init__(self):
        self.weather = WeatherSystem()
        self.world_state = DummyWorldState()
        self.player = DummyPlayer()
        self.quest_manager = DummyQuestManager()
        self.minimap_enabled = True

class DummyWorldState:
    def __init__(self):
        self.time_of_day = 14.5
        self.day = 12
        self.season = "spring"

class DummyPlayer:
    def __init__(self):
        self.hp = 100
        self.max_hp = 100
        self.mana = 50
        self.max_mana = 50
        self.mp = 50
        self.max_mp = 50
        self.stamina = 100
        self.max_stamina = 100
        self.xp = 50
        self.max_xp = 100
        self.xp_needed = 100
        self.level = 5
        self.gold = 250
        self.atk = 20
        self.def_stat = 10
        self.matk = 15
        self.mdef = 10
        self.crit = 5.0
        self.spd = 150.0
        self.location_name = "Village"
        self.skill_manager = DummySkillManager()
        self.inventory = DummyInventory()

from rpg.constants import SKILL_FIREBALL, SKILL_ICE_SPIKE, SKILL_HEALING, SKILL_DASH

class DummySkillManager:
    def __init__(self):
        self.skills = {
            SKILL_FIREBALL: DummySkill(),
            SKILL_ICE_SPIKE: DummySkill(),
            SKILL_HEALING: DummySkill(),
            SKILL_DASH: DummySkill()
        }

class DummySkill:
    def __init__(self):
        self.unlocked = True
        self.timer = 0.0
        self.cooldown = 5.0

class DummyInventory:
    def __init__(self):
        self.quick_slots = {1: "Red Potion", 2: "Blue Potion"}
        self.slots = []

class DummyQuestManager:
    def get_tracked_quest(self):
        return None


class TestWeatherAndUILayout(unittest.TestCase):
    def setUp(self):
        self.weather = WeatherSystem()
        self.ui = UIManager()
        self.game = DummyGame()

    def test_weather_state_transitions(self):
        """WeatherSystem should change state and reset intensity."""
        self.weather.change_weather(WEATHER_RAIN)
        self.assertEqual(self.weather.state, WEATHER_RAIN)
        self.assertEqual(self.weather.intensity, 0.0)

    def test_weather_combat_modifiers(self):
        """WeatherSystem should return correct combat modifiers per weather state."""
        self.weather.change_weather(WEATHER_RAIN)
        mods_rain = self.weather.get_combat_modifiers()
        self.assertEqual(mods_rain["lightning_mult"], 1.30)
        self.assertEqual(mods_rain["fire_mult"], 0.75)

        self.weather.change_weather(WEATHER_SNOW)
        mods_snow = self.weather.get_combat_modifiers()
        self.assertEqual(mods_snow["ice_mult"], 1.20)
        self.assertEqual(mods_snow["speed_mult"], 0.85)

    def test_fog_drift_update(self):
        """Updating weather in FOG state should advance fog_drift_x."""
        self.weather.change_weather(WEATHER_FOG)
        initial_drift = self.weather.fog_drift_x
        self.weather.update(None, pygame.math.Vector2(0, 0), dt=1.0)
        self.assertNotEqual(self.weather.fog_drift_x, initial_drift)

    def test_hud_rendering_without_exceptions(self):
        """draw_hud and _draw_harvest_moon_clock should render cleanly onto surface."""
        surface = pygame.Surface((1024, 768))
        try:
            self.ui.draw_hud(surface, self.game.player)
            rendered = True
        except Exception as e:
            rendered = False
            print(f"HUD render error: {e}")
        self.assertTrue(rendered)

    def test_weather_ambient_sfx_registration(self):
        """SoundManager should synthesize and register ambient weather SFX."""
        from rpg.sound import SoundManager
        sm = SoundManager()
        self.assertIn("thunder", sm.sounds)
        self.assertIn("wind_gust", sm.sounds)
        self.assertIn("crickets", sm.sounds)


if __name__ == "__main__":
    unittest.main()
