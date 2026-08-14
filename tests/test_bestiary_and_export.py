"""
Echoes of Asterra - Unit Tests for Bestiary Compendium & Save Export/Import
"""
import unittest
import shutil
import tempfile
from rpg.bestiary import BestiaryManager


class TestBestiaryAndExport(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.bestiary = BestiaryManager()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_bestiary_defaults_and_kill(self):
        self.assertIn("slime", self.bestiary.entries)
        entry = self.bestiary.entries["slime"]
        initial_kills = entry.kills

        unlocked = self.bestiary.record_kill("slime")
        self.assertTrue(unlocked)
        self.assertEqual(entry.kills, initial_kills + 1)
        self.assertTrue(entry.unlocked)

    def test_bestiary_partial_match(self):
        unlocked = self.bestiary.record_kill("slime_blue")
        self.assertTrue(unlocked)
        self.assertTrue(self.bestiary.entries["slime_blue"].unlocked)

    def test_bestiary_reset(self):
        self.bestiary.record_kill("slime")
        self.assertTrue(self.bestiary.entries["slime"].unlocked)
        self.bestiary.reset()
        self.assertFalse(self.bestiary.entries["slime"].unlocked)
        self.assertEqual(self.bestiary.entries["slime"].kills, 0)



if __name__ == "__main__":
    unittest.main()

