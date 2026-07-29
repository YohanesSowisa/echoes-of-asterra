"""
Echoes of Asterra - Conditional HP Bar & Visceral Injury System Unit Tests
Validates Enemy hit tracking, HP bar activation, and procedural mutilation surface transitions.
"""
import os
import sys
import unittest
import pygame

# Ensure parent of rpg directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# Initialize headless Pygame environment for testing
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((64, 64))

from rpg.enemy import Enemy, Slime
from rpg.sprite import get_injured_surface


class TestConditionalHPBarAndInjurySystem(unittest.TestCase):

    def setUp(self) -> None:
        self.group = pygame.sprite.Group()
        self.enemy = Slime((100.0, 100.0), [self.group])

    def test_enemy_initial_hp_bar_hidden(self) -> None:
        """Verifies an un-struck enemy has has_been_hit = False and HP bar is hidden."""
        self.assertFalse(self.enemy.has_been_hit)
        self.assertEqual(self.enemy.hp, self.enemy.max_hp)

    def test_taking_damage_activates_hp_bar(self) -> None:
        """Verifies taking damage sets has_been_hit = True and refreshes hp_bar_timer."""
        initial_hp = self.enemy.max_hp
        self.enemy.take_damage(5)
        self.assertTrue(self.enemy.has_been_hit)
        self.assertEqual(self.enemy.hp, initial_hp - 5)
        self.assertEqual(self.enemy.hp_bar_timer, 5.0)

    def test_procedural_injury_surface_transitions(self) -> None:
        """Verifies get_injured_surface transitions through Stage 0, Stage 1 (66%), and Stage 2 (33%)."""
        base_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        base_surf.fill((100, 200, 100, 255))

        # Stage 0: 100% HP -> Pristine
        surf_100 = get_injured_surface(base_surf, hp_ratio=1.0)
        self.assertEqual(surf_100, base_surf)

        # Stage 1: 50% HP (<= 66%) -> Lacerated / Blood Gashes
        surf_50 = get_injured_surface(base_surf, hp_ratio=0.5)
        self.assertNotEqual(surf_50, base_surf)
        self.assertIsInstance(surf_50, pygame.Surface)

        # Stage 2: 25% HP (<= 33%) -> Severed Limb / Extreme Mutilation
        surf_25 = get_injured_surface(base_surf, hp_ratio=0.25)
        self.assertNotEqual(surf_25, base_surf)
        self.assertNotEqual(surf_25, surf_50)
        self.assertIsInstance(surf_25, pygame.Surface)

    def test_boss_enrage_stage_transition(self) -> None:
        """Verifies Boss enrage stage triggers at <= 20% HP."""
        base_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        base_surf.fill((200, 100, 100, 255))

        surf_enrage = get_injured_surface(base_surf, hp_ratio=0.15, is_boss=True)
        self.assertIsInstance(surf_enrage, pygame.Surface)
        self.assertNotEqual(surf_enrage, base_surf)


if __name__ == "__main__":
    unittest.main()
