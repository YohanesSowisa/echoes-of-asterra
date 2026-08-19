"""
Unit tests for Pillar #5: Sovereign Guilds & The Continental Monopoly — Phase 1 (Mining Rights & Commodity Warehouses).
Tests resource deed acquisitions, automated daily commodity yield deliveries,
warehouse storage limits, bulk market liquidations, and savegame persistence.
"""
import unittest
from rpg.events import EventBus
from rpg.monopoly import (
    MonopolyManager,
    DEED_MINING,
    DEED_HERBAL,
    DEED_LUMBER,
    COMMODITY_MARKET_PRICES
)


class MockPlayer:
    def __init__(self, gold: int = 200):
        self.gold = gold


class TestMonopolyPhase1(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.mm = MonopolyManager(self.event_bus)
        self.player = MockPlayer(gold=500)

    def test_monopoly_manager_initial_state(self):
        """Tests default unowned deeds and empty warehouse stockpile."""
        self.assertEqual(len(self.mm.deeds), 3)
        self.assertIn(DEED_MINING, self.mm.deeds)
        self.assertIn(DEED_HERBAL, self.mm.deeds)
        self.assertIn(DEED_LUMBER, self.mm.deeds)

        for deed in self.mm.deeds.values():
            self.assertFalse(deed.is_owned)

        self.assertEqual(self.mm.warehouse.get_total_items(), 0)
        self.assertEqual(self.mm.warehouse.capacity, 300)

    def test_purchase_resource_deed(self):
        """Tests purchasing territorial concession deeds with gold deduction and event emission."""
        poor_player = MockPlayer(gold=50)
        success, msg = self.mm.purchase_deed(DEED_MINING, poor_player)
        self.assertFalse(success)
        self.assertIn("Insufficient gold", msg)
        self.assertFalse(self.mm.deeds[DEED_MINING].is_owned)

        # Track event emission
        events = []
        self.event_bus.subscribe("deed_purchased", lambda **kw: events.append(kw))

        # Successful purchase
        success, msg = self.mm.purchase_deed(DEED_MINING, self.player)
        self.assertTrue(success)
        self.assertEqual(self.player.gold, 350)  # 500 - 150
        self.assertTrue(self.mm.deeds[DEED_MINING].is_owned)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["deed_id"], DEED_MINING)

        # Repurchase should fail
        success2, msg2 = self.mm.purchase_deed(DEED_MINING, self.player)
        self.assertFalse(success2)
        self.assertIn("already own", msg2)

    def test_automated_daily_commodity_deliveries(self):
        """Tests that owned concession deeds deliver raw commodities on day changes."""
        self.mm.purchase_deed(DEED_MINING, self.player)  # +3 iron_ore, +2 granite_stone
        self.mm.purchase_deed(DEED_HERBAL, self.player)  # +4 medicinal_herb, +2 luminescent_spore

        # Track delivery event
        delivery_events = []
        self.event_bus.subscribe("warehouse_stock_delivered", lambda **kw: delivery_events.append(kw))

        # Day 2 delivery
        delivered = self.mm.on_day_changed(day=2)
        self.assertEqual(delivered.get("iron_ore"), 3)
        self.assertEqual(delivered.get("granite_stone"), 2)
        self.assertEqual(delivered.get("medicinal_herb"), 4)
        self.assertEqual(delivered.get("luminescent_spore"), 2)

        self.assertEqual(self.mm.warehouse.get_stock("iron_ore"), 3)
        self.assertEqual(self.mm.warehouse.get_stock("medicinal_herb"), 4)
        self.assertEqual(len(delivery_events), 1)

        # Day 3 delivery (accumulation)
        self.mm.on_day_changed(day=3)
        self.assertEqual(self.mm.warehouse.get_stock("iron_ore"), 6)
        self.assertEqual(self.mm.warehouse.get_stock("granite_stone"), 4)
        self.assertEqual(self.mm.warehouse.get_stock("medicinal_herb"), 8)
        self.assertEqual(self.mm.warehouse.get_stock("luminescent_spore"), 4)

    def test_bulk_liquidate_commodities_to_gold(self):
        """Tests selling warehouse commodities directly to market at established unit prices."""
        self.mm.warehouse.add_item("iron_ore", 10)       # 10 * 8g = 80g
        self.mm.warehouse.add_item("granite_stone", 5)   # 5 * 4g = 20g
        self.player.gold = 100

        # Partial liquidation: sell 4 Iron Ore
        sold, revenue = self.mm.bulk_liquidate("iron_ore", count=4, player=self.player)
        self.assertEqual(sold, 4)
        self.assertEqual(revenue, 32)  # 4 * 8g
        self.assertEqual(self.player.gold, 132)
        self.assertEqual(self.mm.warehouse.get_stock("iron_ore"), 6)

        # Liquidate All
        total_sold, total_rev = self.mm.liquidate_all(player=self.player)
        # Remaining: 6 iron_ore (48g) + 5 granite_stone (20g) = 68g
        self.assertEqual(total_sold, 11)
        self.assertEqual(total_rev, 68)
        self.assertEqual(self.player.gold, 200)
        self.assertEqual(self.mm.warehouse.get_total_items(), 0)

    def test_warehouse_capacity_limits(self):
        """Tests warehouse capacity capping when adding bulk items."""
        self.mm.warehouse.capacity = 10
        stored1 = self.mm.warehouse.add_item("iron_ore", 8)
        self.assertEqual(stored1, 8)
        self.assertEqual(self.mm.warehouse.get_available_capacity(), 2)

        # Attempt to add 5 more -> only 2 fit
        stored2 = self.mm.warehouse.add_item("iron_ore", 5)
        self.assertEqual(stored2, 2)
        self.assertEqual(self.mm.warehouse.get_total_items(), 10)
        self.assertEqual(self.mm.warehouse.get_available_capacity(), 0)

    def test_monopoly_savegame_serialization(self):
        """Tests state serialization and restoration across playthroughs."""
        self.mm.purchase_deed(DEED_MINING, self.player)
        self.mm.warehouse.add_item("iron_ore", 15)
        self.mm.total_commodities_sold = 25
        self.mm.total_revenue_earned = 200

        data = self.mm.to_dict()
        self.assertTrue(data["deeds"][DEED_MINING]["is_owned"])
        self.assertEqual(data["warehouse"]["stock"]["iron_ore"], 15)

        new_mm = MonopolyManager()
        new_mm.from_dict(data)
        self.assertTrue(new_mm.deeds[DEED_MINING].is_owned)
        self.assertEqual(new_mm.warehouse.get_stock("iron_ore"), 15)
        self.assertEqual(new_mm.total_commodities_sold, 25)
        self.assertEqual(new_mm.total_revenue_earned, 200)


if __name__ == "__main__":
    unittest.main()
