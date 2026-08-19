"""
Unit tests for Pillar #7: The Living Dungeon Sovereign: Crypt Architect — Phase 1 (Core Claiming & Trap Placement).
Tests Dungeon Core claiming, grid-based trap placement (Spikes, Iron Portcullis, Bait Mimic Chest),
resource costs and refunds, real-time trap collision/damage triggers, defense rating calculation, and save persistence.
"""
import unittest
import pygame
from rpg.events import EventBus
from rpg.dungeon_architect import (
    DungeonArchitectManager,
    TRAP_SPIKE,
    TRAP_PORTCULLIS,
    TRAP_MIMIC_CHEST
)
from rpg.items import create_item
from rpg.inventory import Inventory
from rpg.settings import TILE_SIZE


class MockEnemy:
    def __init__(self, x: int, y: int, hp: float = 100.0):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.hitbox = self.rect
        self.hp = hp
        self.max_hp = hp

    def take_damage(self, amount: int) -> None:
        self.hp = max(0.0, self.hp - amount)


class MockPlayer:
    def __init__(self, gold: int = 500):
        self.gold = gold
        self.titles = set()
        self.inventory = Inventory(size=20)


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.dungeon_architect = DungeonArchitectManager(self.event_bus)
        self.player = MockPlayer()


class TestDungeonArchitectPhase1(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.da = self.game.dungeon_architect
        self.player = self.game.player

    def test_claim_dungeon_core(self):
        """Tests claiming ownership of the Crypt Dungeon Core Stone."""
        self.assertFalse(self.da.core_claimed)

        succ, msg = self.da.claim_dungeon_core(self.player)
        self.assertTrue(succ)
        self.assertTrue(self.da.core_claimed)
        self.assertIn("Crypt Sovereign", self.player.titles)

        # Cannot claim twice
        succ2, msg2 = self.da.claim_dungeon_core(self.player)
        self.assertFalse(succ2)
        self.assertIn("already claimed", msg2)

    def test_place_and_remove_spike_trap(self):
        """Tests placing and dismantling a Spike Trap with gold/material costs and refunds."""
        # 1. Cannot place before claiming core
        succ, msg = self.da.place_trap(TRAP_SPIKE, 5, 8, self.player)
        self.assertFalse(succ)
        self.assertIn("Must claim the Dungeon Core", msg)

        self.da.claim_dungeon_core(self.player)

        # 2. Insufficient materials test (needs 2x Granite Stone)
        self.player.inventory.slots = [None] * self.player.inventory.size
        succ2, msg2 = self.da.place_trap(TRAP_SPIKE, 5, 8, self.player)
        self.assertFalse(succ2)
        self.assertIn("Missing required materials", msg2)

        # 3. Successful placement (cost 25g + 2 Granite Stone)
        self.player.inventory.add_item(create_item("Granite Stone", 2))
        self.player.gold = 100

        succ3, msg3 = self.da.place_trap(TRAP_SPIKE, 5, 8, self.player)
        self.assertTrue(succ3)
        self.assertEqual(self.player.gold, 75)  # 100 - 25
        self.assertFalse(self.player.inventory.has_item("Granite Stone", 1))

        pos_key = "1_5_8"
        self.assertIn(pos_key, self.da.placed_traps)
        trap = self.da.placed_traps[pos_key]
        self.assertEqual(trap.trap_type, TRAP_SPIKE)
        self.assertEqual(trap.world_pos, (5 * TILE_SIZE, 8 * TILE_SIZE))

        # 4. Dismantle trap (50% refund = 12g)
        succ_rem, msg_rem = self.da.remove_trap(5, 8, self.player)
        self.assertTrue(succ_rem)
        self.assertNotIn(pos_key, self.da.placed_traps)
        self.assertEqual(self.player.gold, 87)  # 75 + 12

    def test_place_portcullis_and_mimic_chest(self):
        """Tests placing Iron Portcullis and Bait Mimic Chest traps and duplicate position rejection."""
        self.da.claim_dungeon_core(self.player)
        self.player.gold = 300
        self.player.inventory.add_item(create_item("Iron Ore", 4))
        self.player.inventory.add_item(create_item("Luminescent Spore", 1))

        # Place Iron Portcullis at (3, 4)
        succ_port, _ = self.da.place_trap(TRAP_PORTCULLIS, 3, 4, self.player)
        self.assertTrue(succ_port)

        # Place Bait Mimic Chest at (6, 7)
        succ_mimic, _ = self.da.place_trap(TRAP_MIMIC_CHEST, 6, 7, self.player)
        self.assertTrue(succ_mimic)

        # Attempt duplicate placement at (3, 4) -> fails
        succ_dup, msg_dup = self.da.place_trap(TRAP_SPIKE, 3, 4, self.player)
        self.assertFalse(succ_dup)
        self.assertIn("already contains a trap", msg_dup)

    def test_trap_trigger_and_damage_application(self):
        """Tests collision detection, damage application, and cooldown recovery for placed traps."""
        self.da.claim_dungeon_core(self.player)
        self.player.gold = 200
        self.player.inventory.add_item(create_item("Granite Stone", 2))
        self.da.place_trap(TRAP_SPIKE, 4, 4, self.player)

        enemy = MockEnemy(x=4 * TILE_SIZE, y=4 * TILE_SIZE, hp=100.0)

        # 1. Enemy steps on trap -> takes 35 damage
        dmg = self.da.trigger_traps_for_entity(enemy, floor=1)
        self.assertEqual(dmg, 35)
        self.assertEqual(enemy.hp, 65.0)
        self.assertEqual(self.da.total_traps_triggered, 1)
        self.assertEqual(self.da.total_damage_dealt, 35)

        # 2. Immediate re-trigger -> on cooldown, 0 damage
        dmg_cd = self.da.trigger_traps_for_entity(enemy, floor=1)
        self.assertEqual(dmg_cd, 0)
        self.assertEqual(enemy.hp, 65.0)

        # 3. Advance time past cooldown (cooldown is 2.5s)
        self.da.update(3.0)

        # 4. Trigger again -> takes another 35 damage
        dmg2 = self.da.trigger_traps_for_entity(enemy, floor=1)
        self.assertEqual(dmg2, 35)
        self.assertEqual(enemy.hp, 30.0)
        self.assertEqual(self.da.total_traps_triggered, 2)
        self.assertEqual(self.da.total_damage_dealt, 70)

    def test_dungeon_defense_rating_calculation(self):
        """Tests dynamic defense score calculation and diversity multiplier."""
        self.da.claim_dungeon_core(self.player)
        self.player.gold = 500
        self.player.inventory.add_item(create_item("Granite Stone", 2))
        self.player.inventory.add_item(create_item("Iron Ore", 4))

        self.da.place_trap(TRAP_SPIKE, 1, 1, self.player)
        self.da.place_trap(TRAP_PORTCULLIS, 2, 2, self.player)

        # Spike(35) + Portcullis(15) = 50 base. 2 distinct types -> 1.0 + (2 * 0.15) = 1.30x -> 50 * 1.30 = 65
        score = self.da.get_dungeon_defense_rating(floor=1)
        self.assertEqual(score, 65)

    def test_save_and_restore_dungeon_architect_state(self):
        """Tests serialization and state restoration of Dungeon Architect subsystem."""
        self.da.claim_dungeon_core(self.player)
        self.player.gold = 500
        self.player.inventory.add_item(create_item("Granite Stone", 2))
        self.da.place_trap(TRAP_SPIKE, 3, 5, self.player)

        data = self.da.to_dict()
        self.assertTrue(data["core_claimed"])
        self.assertIn("1_3_5", data["placed_traps"])

        new_da = DungeonArchitectManager()
        new_da.from_dict(data)
        self.assertTrue(new_da.core_claimed)
        self.assertIn("1_3_5", new_da.placed_traps)
        restored_trap = new_da.placed_traps["1_3_5"]
        self.assertEqual(restored_trap.trap_type, TRAP_SPIKE)
        self.assertEqual(restored_trap.grid_x, 3)
        self.assertEqual(restored_trap.grid_y, 5)


if __name__ == "__main__":
    unittest.main()
