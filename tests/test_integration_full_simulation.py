"""
Echoes of Asterra - Full Living World 30-Day Simulation Soak & Integration Test
Simulates >= 30 consecutive in-game days with all 22 subsystems and 8 master expansion pillars
active concurrently in a headless environment (SDL_VIDEODRIVER=dummy).

Features:
1. Virtual clock step ticker (Option A time compression): Advances 10.0s per frame without altering production code.
2. Cross-pillar scheduled event triggers (Companions, Pacts, Outposts, Nemesis, Epochs, Conspiracy, Monopoly, Chrono).
3. Continuous multi-pillar invariant checks at every day tick.
4. Per-manager execution time profiling via time.perf_counter.
5. Save/Load serialization roundtrip validation (Schema v7, slot 99).
"""
import os
import sys
import time
import unittest
from typing import Dict, List, Any

# Configure headless Pygame environment
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from rpg.constants import (
    STATE_PLAYING,
    MAP_VILLAGE,
    MAP_FOREST,
    MAP_LAKE
)
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT, DAY_LENGTH_SECONDS
from rpg.game import Game
from rpg.save import SaveSystem, get_save_path
from rpg.pacts import PACT_VOID, PACT_TITAN, PACT_SOLAR, PACT_NONE
from rpg.epochs import EPOCH_DEFAULT, EPOCH_DELUGE, EPOCH_SCORCHED, EPOCH_GLACIAL
from rpg.chrono import MAX_ROLLING_DAYS
from rpg.items import create_item


class VirtualClock:
    """Mock clock returning fixed virtual delta-time in milliseconds."""
    def __init__(self, virtual_dt_seconds: float = 10.0) -> None:
        self.virtual_dt_seconds = virtual_dt_seconds

    def tick(self, fps: int = 0) -> int:
        return int(self.virtual_dt_seconds * 1000)


class TestIntegrationFullSimulation(unittest.TestCase):
    """
    Soak and integration test executing the complete Game loop across 30+ in-game days.
    """

    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.game = Game(self.screen)
        self.game.start_new_game()

        # Option A: Virtual Clock Step Ticker (10.0 seconds virtual dt per frame)
        # 1 day (1440.0s) = 144 ticks. 30 days = 4,320 ticks.
        self.virtual_dt_seconds = 10.0
        self.game.clock = VirtualClock(self.virtual_dt_seconds)

        # Performance profiling accumulators
        self.timings: Dict[str, List[float]] = {}
        self._install_subsystem_profilers()

    def _install_subsystem_profilers(self) -> None:
        """Dynamically wraps subsystems to capture granular execution metrics."""
        targets = [
            ("game_update", self.game, "update"),
            ("living_world_orchestrator", self.game.living_world, "update"),
            ("world_scheduler_tick", self.game.living_world.scheduler, "update"),
            ("ai_director", self.game.living_world.director, "update"),
            ("npc_schedules_pathfinding", self.game.living_world.schedules, "update"),
            ("trade_caravans", self.game.living_world.caravans, "update"),
            ("faction_warfare", self.game.living_world.faction_war, "update"),
            ("mire_tide_engine", self.game.mire_manager, "update"),
            ("leyline_overcharge", self.game.leyline_manager, "update_overcharge"),
            ("weather_particles", self.game.weather, "update"),
            ("ambient_lighting", self.game.lighting, "update"),
            ("sprites_update_loop", self.game.visible_sprites, "update"),
            ("effects_visual_flash", self.game.effects_manager, "update"),
            ("dungeon_daily_invasion", getattr(self.game, "dungeon_architect", None), "trigger_daily_invasion")
        ]

        for key, obj, method_name in targets:
            if obj and hasattr(obj, method_name):
                self.timings[key] = []
                orig_method = getattr(obj, method_name)
                def make_wrapper(orig, k):
                    def wrapped(*args, **kwargs):
                        t0 = time.perf_counter()
                        res = orig(*args, **kwargs)
                        self.timings[k].append((time.perf_counter() - t0) * 1000.0)
                        return res
                    return wrapped
                setattr(obj, method_name, make_wrapper(orig_method, key))

        # Dynamically wrap all day_changed EventBus subscribers
        if hasattr(self.game, "event_bus") and "day_changed" in self.game.event_bus._listeners:
            wrapped_list = []
            for cb in self.game.event_bus._listeners["day_changed"]:
                owner = getattr(cb, "__self__", None)
                class_name = owner.__class__.__name__ if owner else getattr(cb, "__name__", "callback")
                tag = f"day_tick_{class_name.lower()}"
                self.timings[tag] = []
                def wrap_eb(orig, t_tag):
                    def wrapped(**kw):
                        t0 = time.perf_counter()
                        res = orig(**kw)
                        self.timings[t_tag].append((time.perf_counter() - t0) * 1000.0)
                        return res
                    return wrapped
                wrapped_list.append(wrap_eb(cb, tag))
            self.game.event_bus._listeners["day_changed"] = wrapped_list

    def tearDown(self) -> None:
        # Clean up temporary save slot 99 if created
        save_file = get_save_path(99)
        if os.path.exists(save_file):
            try:
                os.remove(save_file)
            except Exception:
                pass

    def _assert_invariants(self, current_day: int) -> None:
        """
        Enforces strict multi-pillar sanity invariants across world state, player,
        and all active expansion managers.
        """
        ws = self.game.world_state
        player = self.game.player

        # 1. World State Bounded Invariants
        self.assertGreaterEqual(ws.prosperity, 0.0, f"Day {current_day}: Prosperity underflow {ws.prosperity}")
        self.assertLessEqual(ws.prosperity, 100.0, f"Day {current_day}: Prosperity overflow {ws.prosperity}")
        self.assertGreaterEqual(ws.danger_level, 0.0, f"Day {current_day}: Danger underflow {ws.danger_level}")
        self.assertLessEqual(ws.danger_level, 100.0, f"Day {current_day}: Danger overflow {ws.danger_level}")
        self.assertGreaterEqual(ws.road_safety, 0.0, f"Day {current_day}: Road safety underflow {ws.road_safety}")
        self.assertLessEqual(ws.road_safety, 100.0, f"Day {current_day}: Road safety overflow {ws.road_safety}")
        self.assertGreaterEqual(ws.guard_strength, 0.0, f"Day {current_day}: Guard strength underflow {ws.guard_strength}")
        self.assertLessEqual(ws.guard_strength, 100.0, f"Day {current_day}: Guard strength overflow {ws.guard_strength}")
        self.assertGreaterEqual(ws.bandit_strength, 0.0, f"Day {current_day}: Bandit strength underflow {ws.bandit_strength}")
        self.assertLessEqual(ws.bandit_strength, 100.0, f"Day {current_day}: Bandit strength overflow {ws.bandit_strength}")
        self.assertGreaterEqual(ws.monster_density, 0.0, f"Day {current_day}: Monster density underflow {ws.monster_density}")
        self.assertLessEqual(ws.monster_density, 100.0, f"Day {current_day}: Monster density overflow {ws.monster_density}")

        # 2. Player & Inventory Invariants
        self.assertGreaterEqual(player.gold, 0, f"Day {current_day}: Player gold negative: {player.gold}")
        self.assertEqual(len(player.inventory.slots), player.inventory.size, f"Day {current_day}: Inventory slot count corrupted")
        
        seen_item_ids = set()
        for idx, item in enumerate(player.inventory.slots):
            if item is not None:
                self.assertGreaterEqual(getattr(item, "quantity", 1), 1, f"Day {current_day}: Item {item.name} in slot {idx} has invalid qty")
                item_obj_id = id(item)
                self.assertNotIn(item_obj_id, seen_item_ids, f"Day {current_day}: Duplicate item instance reference detected in inventory slot {idx}")
                seen_item_ids.add(item_obj_id)

        # 3. Pillar Subsystem Invariants
        # Pillar #2: Doomsday Conspiracy
        cm = self.game.conspiracy_manager
        self.assertGreaterEqual(cm.days_until_coup, 0, f"Day {current_day}: Coup days underflow: {cm.days_until_coup}")
        self.assertGreaterEqual(cm.syndicate_influence, 0.0, f"Day {current_day}: Syndicate influence underflow")
        self.assertLessEqual(cm.syndicate_influence, 100.0, f"Day {current_day}: Syndicate influence overflow")

        # Pillar #3: Frontier Outposts
        for cp_id, outpost in self.game.outpost_manager.outposts.items():
            self.assertGreaterEqual(outpost.unclaimed_toll_gold, 0, f"Day {current_day}: Outpost {cp_id} toll negative")

        # Pillar #5: Continental Monopoly
        self.assertGreaterEqual(self.game.monopoly_manager.vault_gold, 0, f"Day {current_day}: Vault gold negative")

        # Pillar #6: Ancestral Soul Pacts
        self.assertIn(
            self.game.pact_manager.state.active_pact_id,
            [None, PACT_VOID, PACT_TITAN, PACT_SOLAR],
            f"Day {current_day}: Invalid active pact id {self.game.pact_manager.state.active_pact_id}"
        )

        # Pillar #4: Cataclysm Epochs
        self.assertIn(
            self.game.epoch_manager.current_epoch,
            [EPOCH_DEFAULT, EPOCH_DELUGE, EPOCH_SCORCHED, EPOCH_GLACIAL],
            f"Day {current_day}: Invalid current epoch {self.game.epoch_manager.current_epoch}"
        )

        # Pillar #8: Chrono History Buffer
        self.assertLessEqual(
            len(self.game.chrono_manager.history),
            MAX_ROLLING_DAYS,
            f"Day {current_day}: Chrono history exceeded MAX_ROLLING_DAYS ({MAX_ROLLING_DAYS})"
        )

        # Pillar #7: Nemesis Vendetta Siege
        if self.game.nemesis_manager.active_siege is not None:
            self.assertGreaterEqual(
                self.game.nemesis_manager.active_siege.days_remaining,
                0,
                f"Day {current_day}: Active siege days remaining underflow"
            )

    def test_preliminary_short_boot_and_time_compression(self) -> None:
        """
        Sanity test running 2 in-game days to verify headless boot, virtual ticker,
        and continuous Game.update loop execution.
        """
        ticks_per_day = int(DAY_LENGTH_SECONDS / self.virtual_dt_seconds)  # 144
        initial_day = self.game.world_state.day

        for _ in range(ticks_per_day * 2):
            self.game.update()

        final_day = self.game.world_state.day
        self.assertGreaterEqual(final_day, initial_day + 2)
        self._assert_invariants(final_day)

    def test_full_30_day_soak_simulation_with_all_pillars(self) -> None:
        """
        Main soak test executing 30 consecutive in-game days with all 8 pillars actively triggered.
        Profiles manager execution time and validates save/load integrity at conclusion.
        """
        ticks_per_day = int(DAY_LENGTH_SECONDS / self.virtual_dt_seconds)  # 144 ticks / day
        total_days_target = 30
        last_evaluated_day = self.game.world_state.day

        # Milestone tracking flags
        events_triggered = {
            "companion_recruited": False,
            "expedition_dispatched": False,
            "pact_bound": False,
            "outpost_built": False,
            "siege_triggered": False,
            "siege_resolved": False,
            "epoch_shifted": False,
            "suspect_defeated": False,
            "deeds_purchased": False,
            "vault_deposited": False,
            "chrono_rewind": False
        }

        active_siege_id = None

        print(f"\n[Soak Test] Starting 30-Day Full Living World Simulation ({ticks_per_day * total_days_target} iterations)...")

        for current_tick in range(ticks_per_day * total_days_target):
            self.game.update()
            cur_day = self.game.world_state.day

            # Execute scheduled pillar actions upon reaching specific in-game days
            # Day 2: Recruit Companion & Dispatch Expedition
            if cur_day >= 2 and not events_triggered["companion_recruited"]:
                rec_ok = self.game.companion_manager.recruit_companion("faye")
                self.assertTrue(rec_ok, "Failed to recruit companion Ranger Faye")
                self.assertTrue(self.game.companion_manager.companions["faye"].is_recruited)
                events_triggered["companion_recruited"] = True

                # Dispatch on 2-day forest expedition
                disp_ok = self.game.companion_manager.dispatch_expedition("faye", "forest", 2)
                self.assertTrue(disp_ok, "Failed to dispatch Ranger Faye on forest expedition")
                events_triggered["expedition_dispatched"] = True

            # Day 5: Bind Ancestral Soul Pact (Void Pact)
            if cur_day >= 5 and not events_triggered["pact_bound"]:
                self.game.player.level = max(3, self.game.player.level)
                self.game.player.gold += 200
                relic_item = create_item("ancient_relic", 1) or create_item("Ancient Relic", 1)
                if relic_item:
                    self.game.player.inventory.add_item(relic_item)

                bind_ok, reason = self.game.pact_manager.bind_pact(PACT_VOID, self.game.player, current_day=cur_day)
                self.assertTrue(bind_ok, f"Failed to bind Void Pact on Day {cur_day}: {reason}")
                self.assertEqual(self.game.pact_manager.state.active_pact_id, PACT_VOID)
                events_triggered["pact_bound"] = True

            # Day 8: Construct Frontier Outpost at forest_crossroads
            if cur_day >= 8 and not events_triggered["outpost_built"]:
                self.game.player.gold += 300
                fw = self.game.living_world.faction_war
                if "forest_crossroads" in fw.control_points:
                    fw.control_points["forest_crossroads"].stability = 100.0
                    fw.control_points["forest_crossroads"].contested = False

                built_ok, reason = self.game.outpost_manager.build_outpost("forest_crossroads", self.game.player, fw)
                self.assertTrue(built_ok, f"Failed to build outpost on Day {cur_day}: {reason}")
                self.assertTrue(self.game.outpost_manager.has_outpost("forest_crossroads"))
                events_triggered["outpost_built"] = True

            # Day 12: Trigger Nemesis Vendetta Siege
            if cur_day >= 12 and not events_triggered["siege_triggered"]:
                captain = self.game.nemesis_manager.create_nemesis(level=4, map_name="forest", starting_traits=["Bloodthirsty"])
                self.assertIsNotNone(captain, "Failed to spawn nemesis captain for siege")
                siege = self.game.nemesis_manager.trigger_vendetta_siege(captain.captain_id, "forest", current_day=cur_day)
                self.assertIsNotNone(siege, "Failed to trigger nemesis vendetta siege")
                self.assertIsNotNone(self.game.nemesis_manager.active_siege)
                active_siege_id = siege.siege_id
                events_triggered["siege_triggered"] = True

            # Day 14: Resolve Nemesis Vendetta Siege (Victory defense before 3-day timeout)
            if cur_day >= 14 and not events_triggered["siege_resolved"] and active_siege_id:
                res_ok = self.game.nemesis_manager.resolve_vendetta_siege(
                    active_siege_id,
                    outcome="victory",
                    player=self.game.player,
                    current_day=cur_day
                )
                self.assertTrue(res_ok, "Failed to resolve nemesis vendetta siege")
                self.assertIsNone(self.game.nemesis_manager.active_siege)
                events_triggered["siege_resolved"] = True

            # Day 16: Trigger Cataclysm Epoch Shift (The Deluge Epoch)
            if cur_day >= 16 and not events_triggered["epoch_shifted"]:
                shift_ok = self.game.epoch_manager.set_epoch(EPOCH_DELUGE)
                self.assertTrue(shift_ok, "Failed to set epoch to Deluge")
                self.assertEqual(self.game.epoch_manager.current_epoch, EPOCH_DELUGE)
                events_triggered["epoch_shifted"] = True

            # Day 20: Investigate & Neutralize Conspiracy Suspect Bran
            if cur_day >= 20 and not events_triggered["suspect_defeated"]:
                cm = self.game.conspiracy_manager
                self.assertIn("bran", cm.suspects)
                neut_ok, _ = cm.neutralize_suspect("bran", self.game.player)
                self.assertTrue(neut_ok, "Failed to neutralize suspect Bran")
                self.assertTrue(cm.suspects["bran"].is_defeated)
                events_triggered["suspect_defeated"] = True

            # Day 24: Continental Monopoly Deeds, HQ, and Vault Banking
            if cur_day >= 24 and not events_triggered["deeds_purchased"]:
                self.game.player.gold += 1000
                d1_ok, _ = self.game.monopoly_manager.purchase_deed("mining_concession", self.game.player)
                d2_ok, _ = self.game.monopoly_manager.purchase_deed("herbal_rights", self.game.player)
                self.assertTrue(d1_ok, "Failed to purchase mining concession deed")
                self.assertTrue(d2_ok, "Failed to purchase herbal rights deed")
                events_triggered["deeds_purchased"] = True

                hq_ok, hq_msg = self.game.monopoly_manager.build_syndicate_hq(self.game.player)
                self.assertTrue(hq_ok, f"Failed to build Syndicate HQ: {hq_msg}")

                dep_ok, dep_msg = self.game.monopoly_manager.deposit_vault(150, self.game.player)
                self.assertTrue(dep_ok, f"Failed to deposit gold in vault: {dep_msg}")
                self.assertGreaterEqual(self.game.monopoly_manager.vault_gold, 150)
                events_triggered["vault_deposited"] = True

            # Day 27: Chrono Spacetime Rewind
            if cur_day >= 27 and not events_triggered["chrono_rewind"]:
                # Ensure Chrono-Weaver Hourglass is in inventory
                hourglass = create_item("chrono_weaver_hourglass", 1) or create_item("Chrono-Weaver Hourglass", 1)
                if hourglass:
                    self.game.player.inventory.add_item(hourglass)

                # Record current snapshot before rewind
                self.game.chrono_manager.record_snapshot(self.game)

                # Pre-check can_rewind
                can_r, reason = self.game.chrono_manager.can_rewind(self.game.player, days_to_rewind=2)
                self.assertTrue(can_r, f"Chrono pre-check failed: {reason}")

                # Execute atomic rewind
                rewind_success, rewind_msg, snap = self.game.chrono_manager.execute_temporal_rewind(
                    self.game,
                    days_to_rewind=2
                )
                self.assertTrue(rewind_success, f"Temporal rewind failed: {rewind_msg}")
                self.assertIsNotNone(snap)
                self.assertGreater(self.game.chrono_manager.total_rewinds_performed, 0)
                events_triggered["chrono_rewind"] = True

            # Check invariants at every day transition
            if cur_day != last_evaluated_day:
                self._assert_invariants(cur_day)
                last_evaluated_day = cur_day

        # Assert all 8 pillar events fired
        for event_name, triggered in events_triggered.items():
            self.assertTrue(triggered, f"Pillar event '{event_name}' was not triggered during simulation!")

        final_day = self.game.world_state.day
        self.assertGreaterEqual(final_day, total_days_target, f"Simulation reached day {final_day} (expected >= {total_days_target})")

        # Invariants check on completion
        self._assert_invariants(final_day)

        # -------------------------------------------------------------
        # Save / Load Persistence Integrity Roundtrip (Schema v7, Slot 99)
        # -------------------------------------------------------------
        pre_save_gold = self.game.player.gold
        pre_save_level = self.game.player.level
        pre_save_pact = self.game.pact_manager.state.active_pact_id
        pre_save_vault = self.game.monopoly_manager.vault_gold
        pre_save_epoch = self.game.epoch_manager.current_epoch
        pre_save_outpost = self.game.outpost_manager.has_outpost("forest_crossroads")

        # Save to slot 99
        save_success = SaveSystem.save_game(
            self.game.player,
            self.game.quest_manager,
            self.game.world_manager,
            slot=99,
            slot_name="SoakHero"
        )
        self.assertTrue(save_success, "SaveSystem.save_game returned False on Day 30")

        # Boot fresh instance and load
        new_game = Game(self.screen)
        load_success = SaveSystem.load_game(
            new_game.player,
            new_game.quest_manager,
            new_game.world_manager,
            slot=99
        )
        self.assertTrue(load_success, "SaveSystem.load_game returned False on deserializing slot 99")

        # Assert zero state loss or data corruption
        self.assertEqual(new_game.player.level, pre_save_level)
        self.assertEqual(new_game.player.gold, pre_save_gold)
        self.assertEqual(new_game.pact_manager.state.active_pact_id, pre_save_pact)
        self.assertEqual(new_game.monopoly_manager.vault_gold, pre_save_vault)
        self.assertEqual(new_game.epoch_manager.current_epoch, pre_save_epoch)
        self.assertEqual(new_game.outpost_manager.has_outpost("forest_crossroads"), pre_save_outpost)

        # -------------------------------------------------------------
        # Performance Profiling Report Output
        # -------------------------------------------------------------
        total_frames = len(self.timings.get("game_update", []))
        total_time_ms = sum(self.timings.get("game_update", []))
        avg_frame_ms = total_time_ms / max(1, total_frames)
        max_frame_ms = max(self.timings.get("game_update", [0.0])) if self.timings.get("game_update") else 0.0

        print("\n" + "=" * 80)
        print("          SOAK TEST PERFORMANCE PROFILING BENCHMARK (30 DAYS)          ")
        print("=" * 80)
        print(f"Total Simulation Frames : {total_frames:,} frames")
        print(f"Total Wall-Clock Time   : {total_time_ms / 1000.0:.3f} seconds")
        print(f"Average Game.update()   : {avg_frame_ms:.4f} ms / frame")
        print(f"Maximum Peak Frame      : {max_frame_ms:.4f} ms / frame")
        print(f"Effective FPS Rate      : {total_frames / (total_time_ms / 1000.0):.1f} updates/sec")
        print("-" * 80)
        print(f"{'Subsystem / Manager':<30} | {'Calls':<8} | {'Total (ms)':<12} | {'Avg (ms/call)':<14} | {'% Frame'}")
        print("-" * 80)

        # Sort subsystems by total accumulated execution time
        subsystem_stats = []
        for name, t_list in self.timings.items():
            if name == "game_update":
                continue
            calls = len(t_list)
            tot_ms = sum(t_list)
            avg_ms = tot_ms / max(1, calls)
            pct = (tot_ms / max(0.001, total_time_ms)) * 100.0
            subsystem_stats.append((name, calls, tot_ms, avg_ms, pct))

        subsystem_stats.sort(key=lambda x: x[2], reverse=True)
        for name, calls, tot_ms, avg_ms, pct in subsystem_stats:
            print(f"{name:<30} | {calls:<8} | {tot_ms:<12.3f} | {avg_ms:<14.5f} | {pct:>6.2f}%")
        print("=" * 80)


if __name__ == "__main__":
    unittest.main()
