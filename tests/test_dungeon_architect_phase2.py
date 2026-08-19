"""
Unit tests for Pillar #7: The Living Dungeon Sovereign: Crypt Architect — Phase 2 (Beast Capture & Domestication).
Tests crafting Beast Capture Nets, capturing weakened wild monsters (<20% HP), boss immunity,
chamber stationing, defense rating contributions, and save/load persistence.
"""
import unittest
from rpg.events import EventBus
from rpg.dungeon_architect import DungeonArchitectManager
from rpg.items import create_item
from rpg.inventory import Inventory
from rpg.crafting import CraftingSystem


class MockEnemy:
    def __init__(self, enemy_type: str = "slime", hp: float = 100.0, max_hp: float = 100.0, atk: float = 12.0, is_boss: bool = False):
        self.enemy_type = enemy_type
        self.name = enemy_type.capitalize()
        self.hp = hp
        self.max_hp = max_hp
        self.atk = atk
        self.level = 1
        self.is_boss = is_boss
        self.is_dead = False

    def kill(self):
        self.is_dead = True


class MockPlayer:
    def __init__(self, gold: int = 500):
        self.gold = gold
        self.exp = 0
        self.titles = set()
        self.inventory = Inventory(size=20)

    def add_exp(self, amount: int):
        self.exp += amount


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.dungeon_architect = DungeonArchitectManager(self.event_bus)
        self.player = MockPlayer()


class TestDungeonArchitectPhase2(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.da = self.game.dungeon_architect
        self.player = self.game.player
        self.da.claim_dungeon_core(self.player)

    def test_craft_beast_capture_net(self):
        """Tests crafting a Beast Capture Net from Beast Leather and Iron Ore."""
        self.player.inventory.add_item(create_item("Beast Leather", 2))
        self.player.inventory.add_item(create_item("Iron Ore", 1))

        self.assertTrue(CraftingSystem.can_craft("Beast Capture Net", self.player.inventory))
        succ = CraftingSystem.craft("Beast Capture Net", self.player.inventory)
        self.assertTrue(succ)
        self.assertTrue(self.player.inventory.has_item("Beast Capture Net", 1))

    def test_capture_mechanic_threshold_and_immunity(self):
        """Tests capture health threshold (<=20%), boss immunity, and net consumption."""
        self.player.inventory.add_item(create_item("Beast Capture Net", 2))

        # 1. Unweakened enemy (80/100 HP = 80%) -> fails
        healthy_wolf = MockEnemy(enemy_type="wolf", hp=80.0, max_hp=100.0)
        succ_fail, msg_fail = self.da.capture_enemy(healthy_wolf, self.player)
        self.assertFalse(succ_fail)
        self.assertIn("Target is too strong", msg_fail)
        self.assertTrue(self.player.inventory.has_item("Beast Capture Net", 2))

        # 2. Boss enemy -> immune even if weakened
        boss_dragon = MockEnemy(enemy_type="boss_dragon", hp=10.0, max_hp=500.0, is_boss=True)
        succ_boss, msg_boss = self.da.capture_enemy(boss_dragon, self.player)
        self.assertFalse(succ_boss)
        self.assertIn("Boss monsters", msg_boss)

        # 3. Weakened wild enemy (15/100 HP = 15%) -> succeeds
        weak_wolf = MockEnemy(enemy_type="wolf", hp=15.0, max_hp=100.0, atk=18.0)
        succ_cap, msg_cap = self.da.capture_enemy(weak_wolf, self.player)
        self.assertTrue(succ_cap)
        self.assertIn("Successfully captured", msg_cap)
        self.assertTrue(weak_wolf.is_dead)
        self.assertEqual(self.player.exp, 25)
        self.assertEqual(self.player.inventory.get_item_count("Beast Capture Net"), 1)

        # Check captured monster in reserve roster
        self.assertEqual(len(self.da.captured_monsters), 1)
        cap_id = list(self.da.captured_monsters.keys())[0]
        monster = self.da.captured_monsters[cap_id]
        self.assertEqual(monster.monster_type, "wolf")
        self.assertEqual(monster.atk, 18.0)
        self.assertFalse(monster.is_stationed)

    def test_station_and_unassign_monster_in_chamber(self):
        """Tests assigning and recalling domesticated guardians to dungeon chambers."""
        self.player.inventory.add_item(create_item("Beast Capture Net", 1))
        skeleton = MockEnemy(enemy_type="skeleton", hp=10.0, max_hp=80.0, atk=14.0)
        self.da.capture_enemy(skeleton, self.player)

        monster_id = list(self.da.captured_monsters.keys())[0]

        # 1. Assign to chamber (2, 3) on Floor 1
        succ_sta, msg_sta = self.da.assign_monster_to_room(monster_id, grid_x=2, grid_y=3, floor=1)
        self.assertTrue(succ_sta)
        monster = self.da.captured_monsters[monster_id]
        self.assertTrue(monster.is_stationed)
        self.assertEqual(monster.assigned_grid_x, 2)
        self.assertEqual(monster.assigned_grid_y, 3)

        stationed = self.da.get_stationed_monsters(floor=1)
        self.assertEqual(len(stationed), 1)

        # 2. Recall to reserve
        succ_un, msg_un = self.da.unassign_monster(monster_id)
        self.assertTrue(succ_un)
        self.assertFalse(monster.is_stationed)
        self.assertIsNone(monster.assigned_grid_x)
        self.assertEqual(len(self.da.get_stationed_monsters(floor=1)), 0)

    def test_guardian_defense_rating_contribution(self):
        """Tests that stationed beasts boost dungeon defense score based on their attack power."""
        self.player.inventory.add_item(create_item("Beast Capture Net", 2))
        slime = MockEnemy(enemy_type="slime", hp=5.0, max_hp=50.0, atk=10.0)
        wolf = MockEnemy(enemy_type="wolf", hp=10.0, max_hp=100.0, atk=20.0)

        self.da.capture_enemy(slime, self.player)
        self.da.capture_enemy(wolf, self.player)

        m_ids = list(self.da.captured_monsters.keys())

        # Station both on Floor 1
        self.da.assign_monster_to_room(m_ids[0], 1, 1, floor=1)
        self.da.assign_monster_to_room(m_ids[1], 2, 2, floor=1)

        # Guardian defense: (10 * 2) + (20 * 2) = 20 + 40 = 60
        defense = self.da.get_dungeon_defense_rating(floor=1)
        self.assertEqual(defense, 60)

    def test_save_and_restore_captured_monsters(self):
        """Tests serialization and state restoration of captured and stationed monsters."""
        self.player.inventory.add_item(create_item("Beast Capture Net", 1))
        wolf = MockEnemy(enemy_type="wolf", hp=15.0, max_hp=100.0, atk=16.0)
        self.da.capture_enemy(wolf, self.player)

        m_id = list(self.da.captured_monsters.keys())[0]
        self.da.assign_monster_to_room(m_id, 4, 5, floor=1)

        data = self.da.to_dict()
        self.assertIn(m_id, data["captured_monsters"])
        self.assertTrue(data["captured_monsters"][m_id]["is_stationed"])

        new_da = DungeonArchitectManager()
        new_da.from_dict(data)
        self.assertIn(m_id, new_da.captured_monsters)
        restored_m = new_da.captured_monsters[m_id]
        self.assertEqual(restored_m.monster_type, "wolf")
        self.assertEqual(restored_m.atk, 16.0)
        self.assertTrue(restored_m.is_stationed)
        self.assertEqual(restored_m.assigned_grid_x, 4)
        self.assertEqual(restored_m.assigned_grid_y, 5)


if __name__ == "__main__":
    unittest.main()
