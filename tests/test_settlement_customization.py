"""
Echoes of Asterra - Unit Tests for Player-Driven Settlement Customization (Phase 4)
Tests:
1. Specialization selection (Military Fortress, Trade Hub, Arcane Sanctuary) via faction standing or gold.
2. Military Fortress: safe zone ATK/DEF buffs and extra guard patrol spawning.
3. Trade Hub: additional Silas shop discounts and trade boosts.
4. Arcane Sanctuary: passive mana regeneration in Village and rune crafting discounts.
5. Serialization (to_dict, from_dict, reset) without cross-session state leakage.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((64, 64))

from rpg.events import EventBus
from rpg.settlement import (
    SettlementManager,
    SPECIALIZATION_NONE,
    SPECIALIZATION_MILITARY,
    SPECIALIZATION_TRADE,
    SPECIALIZATION_ARCANE
)
from rpg.factions import FactionManager, FACTION_KNIGHTS, FACTION_MERCHANTS, FACTION_MAGES
from rpg.living_world import LivingWorldManager
from rpg.crafting import CraftingSystem
from rpg.inventory import Inventory
from rpg.items import create_item


class DummyPlayer:
    def __init__(self):
        self.name = "Hero"
        self.gold = 100
        self.hp = 100
        self.max_hp = 100
        self.mana = 10
        self.max_mana = 50
        self.base_atk = 10
        self.base_def = 5
        self.base_magic = 10
        self.base_speed = 4.0
        self.base_crit = 5
        self.base_max_hp = 100
        self.base_max_mana = 50
        self.atk = 10
        self.defense = 5
        self.speed = 4.0
        self.crit_chance = 5
        self.inventory = Inventory(20)
        from rpg.equipment import Equipment
        self.equipment = Equipment()


class DummyWorldManager:
    def __init__(self):
        self.current_map_name = "village"


class DummyGame:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.player = DummyPlayer()
        self.player.game = self
        self.world_manager = DummyWorldManager()
        self.factions = FactionManager()
        self.living_world = LivingWorldManager(event_bus)
        self.ui_sprites = pygame.sprite.Group()
        from rpg.dialogue import DialogueManager
        self.dialogue_manager = DialogueManager()


class TestSettlementCustomization(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.settlement = SettlementManager()
        self.settlement.register_event_listeners(self.event_bus)
        self.factions = FactionManager()
        self.player = DummyPlayer()

    def test_specialization_via_faction_standing_free(self):
        """Having 20+ reputation with the aligned faction allows free specialization."""
        self.factions.modify_reputation(FACTION_KNIGHTS, 30)  # Total 40 rep
        self.player.gold = 10  # Less than 75g

        success, msg = self.settlement.set_specialization(SPECIALIZATION_MILITARY, self.player, self.factions)
        self.assertTrue(success)
        self.assertEqual(self.settlement.specialization, SPECIALIZATION_MILITARY)
        self.assertEqual(self.player.gold, 10)  # Gold not deducted

    def test_specialization_via_gold_investment(self):
        """Without faction endorsement, player can specialize by paying 75 gold."""
        self.player.gold = 100
        self.factions.factions[FACTION_MERCHANTS].reputation = 0  # 0 rep

        success, msg = self.settlement.set_specialization(SPECIALIZATION_TRADE, self.player, self.factions)
        self.assertTrue(success)
        self.assertEqual(self.settlement.specialization, SPECIALIZATION_TRADE)
        self.assertEqual(self.player.gold, 25)  # 75g deducted

    def test_specialization_fails_when_lacking_both_rep_and_gold(self):
        """Specialization fails if player lacks both faction standing and 75 gold."""
        self.player.gold = 30
        self.factions.factions[FACTION_MAGES].reputation = 5

        success, msg = self.settlement.set_specialization(SPECIALIZATION_ARCANE, self.player, self.factions)
        self.assertFalse(success)
        self.assertEqual(self.settlement.specialization, SPECIALIZATION_NONE)

    def test_military_fortress_safe_zone_stat_buffs(self):
        """Military Fortress grants +15% ATK and +20% DEF only in Village safe zone."""
        self.settlement.specialization = SPECIALIZATION_MILITARY

        village_buffs = self.settlement.get_safe_zone_stat_buffs("village")
        self.assertEqual(village_buffs["atk_mult"], 1.15)
        self.assertEqual(village_buffs["def_mult"], 1.20)

        forest_buffs = self.settlement.get_safe_zone_stat_buffs("forest")
        self.assertEqual(forest_buffs["atk_mult"], 1.0)
        self.assertEqual(forest_buffs["def_mult"], 1.0)

        # Verify equipment recalculation with live game
        game = DummyGame(self.event_bus)
        game.living_world.settlement.specialization = SPECIALIZATION_MILITARY
        game.world_manager.current_map_name = "village"
        game.player.equipment.recalculate_player_stats(game.player)

        # Base 10 ATK * 1.15 = 11, Base 5 DEF * 1.20 = 6
        self.assertEqual(game.player.atk, 11)
        self.assertEqual(game.player.defense, 6)

    def test_trade_hub_shop_discount(self):
        """Trade Hub grants 15% discount integrated into LivingWorldManager price multiplier."""
        lw = LivingWorldManager(self.event_bus)
        lw.settlement.specialization = SPECIALIZATION_TRADE

        base_mult = lw.get_combined_price_multiplier("goods", "village", merchant_reputation=0.0, friendship_tier=0.0)
        # 1.0 * (1.0 - 0.15) = 0.85
        self.assertAlmostEqual(base_mult, 0.85, places=2)

    def test_arcane_sanctuary_mana_regen_and_rune_discount(self):
        """Arcane Sanctuary grants +5.0 Mana/s in Village and 25% rune crafting discount."""
        self.settlement.specialization = SPECIALIZATION_ARCANE

        self.assertEqual(self.settlement.get_safe_zone_mana_regen("village"), 5.0)
        self.assertEqual(self.settlement.get_safe_zone_mana_regen("cave"), 0.0)
        self.assertEqual(self.settlement.get_rune_crafting_discount(), 0.25)

        # Verify Crafting discount
        # Rune of Fire base req: {"Iron Ore": 2, "Red Potion": 1}
        # With 25% discount: 2 * 0.75 = 1 Iron Ore, 1 Red Potion
        reqs = CraftingSystem.get_recipe_ingredients("Rune of Fire", rune_discount=0.25)
        self.assertEqual(reqs["Iron Ore"], 1)
        self.assertEqual(reqs["Red Potion"], 1)

        inv = Inventory(10)
        inv.add_item(create_item("Iron Ore", 1))
        inv.add_item(create_item("Red Potion", 1))

        # Standard craft without discount requires 2 Iron Ore -> fails
        self.assertFalse(CraftingSystem.can_craft("Rune of Fire", inv, rune_discount=0.0))
        # With 25% discount -> succeeds
        self.assertTrue(CraftingSystem.can_craft("Rune of Fire", inv, rune_discount=0.25))

    def test_settlement_serialization_and_reset(self):
        """Settlement specialization must be preserved across save/load and cleanly reset."""
        self.settlement.specialization = SPECIALIZATION_MILITARY
        self.settlement.add_prosperity(30.0)

        saved = self.settlement.to_dict()
        self.assertEqual(saved["specialization"], SPECIALIZATION_MILITARY)

        self.settlement.reset()
        self.assertEqual(self.settlement.specialization, SPECIALIZATION_NONE)

        self.settlement.from_dict(saved)
        self.assertEqual(self.settlement.specialization, SPECIALIZATION_MILITARY)


if __name__ == "__main__":
    unittest.main()
