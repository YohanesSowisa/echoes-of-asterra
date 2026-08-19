"""
Unit tests for Pillar #5: Sovereign Guilds & The Continental Monopoly — Phase 3 (Syndicate HQ, Banking & Oligarch Prestige).
Tests Asterra Merchant Syndicate HQ construction, Gold Vault banking with +2% daily compound interest,
'The Sovereign Baron' prestige title with 30% merchant discounts, diplomatic bribery, and Mythos chronicle recording.
"""
import unittest
from rpg.events import EventBus
from rpg.monopoly import (
    MonopolyManager,
    DEED_MINING,
    DEED_HERBAL,
    DEED_LUMBER
)
from rpg.mythos import MythosManager


class MockFactionManager:
    def __init__(self):
        self.reputation = {"bandits": -20, "knights": 10}

    def modify_reputation(self, faction_id: str, amount: int):
        clean_fac = faction_id.lower()
        self.reputation[clean_fac] = self.reputation.get(clean_fac, 0) + amount


class MockPlayer:
    def __init__(self, gold: int = 1000):
        self.gold = gold
        self.titles = set()
        self.game = None


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.monopoly_manager = MonopolyManager(self.event_bus)
        self.mythos_manager = MythosManager()
        self.mythos_manager.register_event_listeners(self.event_bus)
        self.faction_manager = MockFactionManager()
        self.player = MockPlayer()
        self.player.game = self


class TestMonopolyPhase3(unittest.TestCase):
    def setUp(self):
        self.game = MockGame()
        self.mm = self.game.monopoly_manager
        self.mythos = self.game.mythos_manager
        self.player = self.game.player

    def test_syndicate_hq_construction_requirements(self):
        """Tests building the Asterra Merchant Syndicate HQ with deed prerequisites and gold cost."""
        # 1. Without deeds -> fails
        success, msg = self.mm.build_syndicate_hq(self.player)
        self.assertFalse(success)
        self.assertIn("at least 2 owned concession deeds", msg)

        # 2. Buy 2 deeds (Mining + Herbal = 250g)
        self.mm.purchase_deed(DEED_MINING, self.player)
        self.mm.purchase_deed(DEED_HERBAL, self.player)

        # 3. Insufficient gold test
        self.player.gold = 100
        success2, msg2 = self.mm.build_syndicate_hq(self.player)
        self.assertFalse(success2)
        self.assertIn("Insufficient gold", msg2)

        # 4. Successful build (cost 250g)
        self.player.gold = 500
        success3, msg3 = self.mm.build_syndicate_hq(self.player)
        self.assertTrue(success3)
        self.assertTrue(self.mm.syndicate_hq_built)
        self.assertEqual(self.player.gold, 250)  # 500 - 250
        self.assertIn("The Sovereign Baron", self.player.titles)

    def test_gold_vault_deposits_and_withdrawals(self):
        """Tests depositing and withdrawing gold from the Syndicate Gold Vault."""
        # 1. Attempt before building HQ -> fails
        succ, msg = self.mm.deposit_vault(100, self.player)
        self.assertFalse(succ)

        # Build HQ
        self.mm.purchase_deed(DEED_MINING, self.player)
        self.mm.purchase_deed(DEED_HERBAL, self.player)
        self.mm.build_syndicate_hq(self.player)

        self.player.gold = 1000

        # 2. Deposit 600 Gold
        succ_dep, msg_dep = self.mm.deposit_vault(600, self.player)
        self.assertTrue(succ_dep)
        self.assertEqual(self.mm.vault_gold, 600)
        self.assertEqual(self.player.gold, 400)

        # 3. Withdraw 250 Gold
        succ_with, msg_with = self.mm.withdraw_vault(250, self.player)
        self.assertTrue(succ_with)
        self.assertEqual(self.mm.vault_gold, 350)
        self.assertEqual(self.player.gold, 650)

        # 4. Overdraw fails
        succ_over, msg_over = self.mm.withdraw_vault(1000, self.player)
        self.assertFalse(succ_over)
        self.assertEqual(self.mm.vault_gold, 350)

    def test_daily_bank_interest_compound_growth(self):
        """Tests +2% daily compound interest accumulation on Vault deposits on day changes."""
        self.mm.purchase_deed(DEED_MINING, self.player)
        self.mm.purchase_deed(DEED_HERBAL, self.player)
        self.mm.build_syndicate_hq(self.player)

        self.player.gold = 2000
        self.mm.deposit_vault(1000, self.player)
        self.assertEqual(self.mm.vault_gold, 1000)

        # Day 2: 1000 * 1.02 = 1020
        self.mm.on_day_changed(day=2)
        self.assertEqual(self.mm.vault_gold, 1020)

        # Day 3: 1020 + 20 (2% of 1020 = 20.4) = 1040
        self.mm.on_day_changed(day=3)
        self.assertEqual(self.mm.vault_gold, 1040)

        # Day 4: 1040 + 20 = 1060
        self.mm.on_day_changed(day=4)
        self.assertEqual(self.mm.vault_gold, 1060)

    def test_sovereign_baron_merchant_discount_and_diplomatic_bribes(self):
        """Tests 30% store discounts and diplomatic bribery pacification as The Sovereign Baron."""
        self.assertEqual(self.mm.get_merchant_discount(), 0.0)
        self.assertFalse(self.mm.can_diplomatic_bribe())

        # Construct HQ -> unlocks Baron perks
        self.mm.purchase_deed(DEED_MINING, self.player)
        self.mm.purchase_deed(DEED_HERBAL, self.player)
        self.mm.build_syndicate_hq(self.player)

        self.assertEqual(self.mm.get_merchant_discount(), 0.30)
        self.assertTrue(self.mm.can_diplomatic_bribe())

        # Execute Diplomatic Bribe to Bandit faction
        self.player.gold = 100
        self.assertEqual(self.game.faction_manager.reputation["bandits"], -20)

        succ_bribe, msg_bribe = self.mm.execute_diplomatic_bribe("bandits", self.player, bribe_amount=50)
        self.assertTrue(succ_bribe)
        self.assertEqual(self.player.gold, 50)
        self.assertEqual(self.game.faction_manager.reputation["bandits"], 5)  # -20 + 25 = 5

    def test_mythos_and_save_lifecycle(self):
        """Tests chronicle logging and state restoration across save/load."""
        self.mm.purchase_deed(DEED_MINING, self.player)
        self.mm.purchase_deed(DEED_HERBAL, self.player)
        self.mm.build_syndicate_hq(self.player)
        self.mm.deposit_vault(500, self.player)

        # Verify Mythos recorded event
        events = [e for e in self.mythos.timeline if e.get("event_type") == "MERCHANT_SYNDICATE_FOUNDED"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["actor"], "The Sovereign Baron")

        # Save and restore
        data = self.mm.to_dict()
        self.assertTrue(data["syndicate_hq_built"])
        self.assertEqual(data["vault_gold"], 500)

        new_mm = MonopolyManager()
        new_mm.from_dict(data)
        self.assertTrue(new_mm.syndicate_hq_built)
        self.assertEqual(new_mm.vault_gold, 500)
        self.assertEqual(new_mm.get_merchant_discount(), 0.30)


if __name__ == "__main__":
    unittest.main()
