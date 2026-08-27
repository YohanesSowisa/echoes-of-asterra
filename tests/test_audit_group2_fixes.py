import unittest
import os
import pygame

from rpg.constants import STATE_PLAYING, MAP_VILLAGE
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from rpg.game import Game
from rpg.settlement import SPECIALIZATION_TRADE, SPECIALIZATION_MILITARY


class TestAuditGroup2Fixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        if not pygame.get_init():
            pygame.init()

    def setUp(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.game = Game(self.screen)
        self.game.start_new_game()

    # -------------------------------------------------------------------------
    # 5. Settlement Specialization Syncs to WorldState via Production Path
    # -------------------------------------------------------------------------
    def test_settlement_specialization_updates_world_state(self):
        settlement = self.game.living_world.settlement
        world_state = self.game.living_world.world_state
        self.game.player.gold = 500

        # Initial
        self.assertEqual(world_state.settlement_specialization, "")

        # Choose Trade Hub via set_specialization
        success, msg = settlement.set_specialization(SPECIALIZATION_TRADE, self.game.player, self.game.factions)
        self.assertTrue(success, f"Failed to set trade specialization: {msg}")
        self.assertEqual(settlement.specialization, SPECIALIZATION_TRADE)
        # Verify WorldState received the settlement_specialized event!
        self.assertEqual(world_state.settlement_specialization, SPECIALIZATION_TRADE)

        # Reset and choose Military Fortress
        settlement.specialization = None
        world_state.settlement_specialization = ""
        success, msg = settlement.set_specialization(SPECIALIZATION_MILITARY, self.game.player, self.game.factions)
        self.assertTrue(success, f"Failed to set military specialization: {msg}")
        self.assertEqual(world_state.settlement_specialization, SPECIALIZATION_MILITARY)

    # -------------------------------------------------------------------------
    # 6. DiscoveryManager Listens to territory_control_changed
    # -------------------------------------------------------------------------
    def test_discovery_reacts_to_territory_control_changed(self):
        dm = self.game.discovery_manager
        self.assertNotIn("lead_outposts", dm.triggered_leads)

        # Emit territory_control_changed (same event emitted by FactionWarManager)
        self.game.event_bus.emit(
            "territory_control_changed",
            control_point="Forest Crossroads",
            map_name="forest",
            old_owner="bandits",
            new_owner="knights"
        )

        # Verify outpost lead is triggered
        self.assertIn("lead_outposts", dm.triggered_leads)

    # -------------------------------------------------------------------------
    # 7a. quest_accepted Emission Triggers Discovery Conspiracy Lead
    # -------------------------------------------------------------------------
    def test_quest_accepted_triggers_conspiracy_lead(self):
        dm = self.game.discovery_manager
        self.assertNotIn("lead_conspiracy", dm.triggered_leads)

        # Accept main quest via QuestManager
        self.game.quest_manager.accept_quest("main_quest")

        # Verify quest_accepted event was emitted and received by DiscoveryManager
        self.assertIn("lead_conspiracy", dm.triggered_leads)

    # -------------------------------------------------------------------------
    # 7c. player_died Event Increments Death and Loss Counters in WorldState
    # -------------------------------------------------------------------------
    def test_player_died_increases_world_danger_level(self):
        world_state = self.game.living_world.world_state
        initial_deaths = world_state.recent_deaths
        initial_losses = world_state._combat_losses

        # Emit player_died
        self.game.event_bus.emit("player_died", player=self.game.player, map_name="forest")

        # WorldState _on_player_died records death and combat losses
        self.assertEqual(world_state.recent_deaths, initial_deaths + 1)
        self.assertEqual(world_state._combat_losses, initial_losses + 1)

    # -------------------------------------------------------------------------
    # 7d. gold_gained Event Triggers Wealthy Merchant Achievement
    # -------------------------------------------------------------------------
    def test_gold_gained_unlocks_achievement(self):
        ach_mgr = self.game.achievement_manager
        self.assertFalse(ach_mgr.achievements["wealthy_merchant"].unlocked)

        # Add 150 gold to player
        self.game.player.add_gold(150)

        # Verify achievement is unlocked via gold_gained event
        self.assertTrue(ach_mgr.achievements["wealthy_merchant"].unlocked)


if __name__ == "__main__":
    unittest.main()
