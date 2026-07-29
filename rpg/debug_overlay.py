"""
Echoes of Asterra - Developer Debug Overlay
Developer-only overlay system activated via F9, F10, and F11 hotkeys.
Renders real-time HUD visual diagnostics for Simulation Overview, Director Decisions,
and Scheduler Statistics. Never shown in release builds.
"""
import pygame
from typing import Optional, Any

from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT

class DebugOverlay:
    """
    Developer debug overlay renderer.
    F9: Simulation Overview
    F10: Director Decisions
    F11: Scheduler Statistics
    """
    def __init__(self) -> None:
        self.active_panel: Optional[str] = None  # None, "overview", "director", "scheduler"
        
        # Pygame fonts
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Consolas", 18, bold=True)
        self.font_header = pygame.font.SysFont("Consolas", 14, bold=True)
        self.font_body = pygame.font.SysFont("Consolas", 12)

    def handle_keydown(self, key: int) -> bool:
        """
        Handles F8, F9, F10, F11 hotkeys. Returns True if key event was consumed.
        """
        if key == pygame.K_F8:
            self.active_panel = None if self.active_panel == "eventbus" else "eventbus"
            return True
        elif key == pygame.K_F9:
            self.active_panel = None if self.active_panel == "overview" else "overview"
            return True
        elif key == pygame.K_F10:
            self.active_panel = None if self.active_panel == "director" else "director"
            return True
        elif key == pygame.K_F11:
            self.active_panel = None if self.active_panel == "scheduler" else "scheduler"
            return True
        return False

    def draw(self, surface: pygame.Surface, game_context: Any) -> None:
        """Renders active debug panel on target Pygame surface."""
        if not self.active_panel or not game_context:
            return
            
        if self.active_panel == "eventbus":
            self._draw_eventbus_panel(surface, game_context)
        elif self.active_panel == "overview":
            self._draw_overview_panel(surface, game_context)
        elif self.active_panel == "director":
            self._draw_director_panel(surface, game_context)
        elif self.active_panel == "scheduler":
            self._draw_scheduler_panel(surface, game_context)

    def _draw_card_frame(self, surface: pygame.Surface, x: int, y: int, w: int, h: int, title: str, subtitle: str = "") -> None:
        """Helper drawing styled translucent dark container frame."""
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((12, 16, 26, 235))
        surface.blit(overlay, (x, y))
        
        # Outer border
        pygame.draw.rect(surface, (0, 180, 216), (x, y, w, h), width=2, border_radius=4)
        
        # Header bar
        pygame.draw.rect(surface, (20, 32, 50), (x, y, w, 32), border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.line(surface, (0, 180, 216), (x, y + 32), (x + w, y + 32), width=1)
        
        title_surf = self.font_title.render(title, True, (255, 255, 255))
        surface.blit(title_surf, (x + 12, y + 6))
        
        if subtitle:
            sub_surf = self.font_body.render(subtitle, True, (160, 200, 220))
            surface.blit(sub_surf, (x + w - sub_surf.get_width() - 12, y + 8))

    def _draw_overview_panel(self, surface: pygame.Surface, game: Any) -> None:
        """F9 Panel: Simulation Overview metrics."""
        x, y, w, h = 20, 20, 480, 380
        self._draw_card_frame(surface, x, y, w, h, "[F9] WORLD SIMULATION OVERVIEW", "DEV DEBUG")
        
        world_state = getattr(game, "world_state", None)
        living_world = getattr(game, "living_world", None)
        director = getattr(living_world, "director", None) if living_world else None
        
        pressure_str = director.current_pressure.value if director else "UNKNOWN"
        pressure_score = director.pressure_score if director else 0.0
        
        # Pressure color coding
        pressure_colors = {
            "PEACEFUL": (46, 204, 113),
            "CALM": (52, 152, 219),
            "ACTIVE": (241, 196, 15),
            "DANGEROUS": (230, 126, 34),
            "CRISIS": (231, 76, 60)
        }
        color = pressure_colors.get(pressure_str, (200, 200, 200))
        
        lines = [
            ("Current World Pressure:", f"{pressure_str} ({pressure_score:.1f} / 100)"),
            ("Village Prosperity:", f"{getattr(world_state, 'prosperity', 0)} / 100"),
            ("Road Safety Score:", f"{getattr(world_state, 'road_safety', 50.0):.1f} / 100"),
            ("Guard Strength:", f"{getattr(world_state, 'guard_strength', 60.0):.1f}"),
            ("Bandit Strength:", f"{getattr(world_state, 'bandit_strength', 40.0):.1f}"),
            ("Regional Danger Level:", f"{getattr(world_state, 'danger_level', 20.0):.1f}"),
            ("Trade Activity Index:", f"{getattr(world_state, 'trade_activity', 50.0):.1f}"),
            ("Monster Density:", f"{getattr(world_state, 'monster_density', 30.0):.1f}"),
            ("Faction Stability:", f"{getattr(world_state, 'faction_stability', 65.0):.1f}"),
            ("Active Crisis:", f"{getattr(world_state, 'active_crisis', 'None') or 'None'}"),
            ("Current Weather:", f"{getattr(getattr(game, 'weather', None), 'current_weather', 'Clear')}")
        ]
        
        curr_y = y + 44
        for label, val in lines:
            lbl_surf = self.font_body.render(label, True, (180, 200, 220))
            val_surf = self.font_header.render(val, True, color if "Pressure" in label else (240, 240, 240))
            surface.blit(lbl_surf, (x + 16, curr_y))
            surface.blit(val_surf, (x + 220, curr_y))
            curr_y += 28

    def _draw_director_panel(self, surface: pygame.Surface, game: Any) -> None:
        """F10 Panel: Director Decisions & Memory."""
        x, y, w, h = 20, 20, 520, 440
        self._draw_card_frame(surface, x, y, w, h, "[F10] ADAPTIVE GAME DIRECTOR DECISIONS", "DEV DEBUG")
        
        living_world = getattr(game, "living_world", None)
        director = getattr(living_world, "director", None) if living_world else None
        
        if not director:
            err_surf = self.font_body.render("GameDirector not initialized.", True, (255, 100, 100))
            surface.blit(err_surf, (x + 16, y + 50))
            return
            
        curr_y = y + 44
        
        # 1. Current Goal
        goal_lbl = self.font_body.render("Current Goal:", True, (180, 200, 220))
        goal_val = self.font_header.render(director.current_goal, True, (255, 215, 0))
        surface.blit(goal_lbl, (x + 16, curr_y))
        surface.blit(goal_val, (x + 140, curr_y))
        curr_y += 26
        
        # 2. Cooldowns
        cd_lbl = self.font_header.render("Active Action Cooldowns:", True, (0, 180, 216))
        surface.blit(cd_lbl, (x + 16, curr_y))
        curr_y += 22
        
        if director.cooldowns:
            for act_id, days_left in director.cooldowns.items():
                txt = f" • {act_id}: {days_left} day(s) cooldown remaining"
                surf = self.font_body.render(txt, True, (200, 220, 240))
                surface.blit(surf, (x + 24, curr_y))
                curr_y += 18
        else:
            surf = self.font_body.render(" • No active cooldowns", True, (140, 160, 180))
            surface.blit(surf, (x + 24, curr_y))
            curr_y += 18
            
        curr_y += 10
        
        # 3. Interventions History
        hist_lbl = self.font_header.render("Recent Interventions Memory:", True, (0, 180, 216))
        surface.blit(hist_lbl, (x + 16, curr_y))
        curr_y += 22
        
        recent = director.history[-6:] if director.history else []
        if recent:
            for rec in reversed(recent):
                day = rec.get("day", "?")
                act = rec.get("action", "Unknown")
                tier = rec.get("tier", "CALM")
                reason = rec.get("reason", "")
                
                header_str = f"Day {day} [{tier}]: {act}"
                h_surf = self.font_header.render(header_str, True, (240, 240, 240))
                r_surf = self.font_body.render(f"  Reason: {reason}", True, (170, 190, 210))
                
                surface.blit(h_surf, (x + 24, curr_y))
                curr_y += 18
                surface.blit(r_surf, (x + 24, curr_y))
                curr_y += 22
        else:
            surf = self.font_body.render(" • No interventions recorded yet.", True, (140, 160, 180))
            surface.blit(surf, (x + 24, curr_y))

    def _draw_scheduler_panel(self, surface: pygame.Surface, game: Any) -> None:
        """F11 Panel: World Scheduler metrics."""
        x, y, w, h = 20, 20, 480, 380
        self._draw_card_frame(surface, x, y, w, h, "[F11] WORLD SCHEDULER STATISTICS", "DEV DEBUG")
        
        living_world = getattr(game, "living_world", None)
        scheduler = getattr(living_world, "scheduler", None) if living_world else None
        
        if not scheduler:
            err_surf = self.font_body.render("WorldScheduler not initialized.", True, (255, 100, 100))
            surface.blit(err_surf, (x + 16, y + 50))
            return
            
        time_str = f"{scheduler.hour:02d}:{scheduler.minute:02d}"
        
        lines = [
            ("Simulation Day:", f"Day {scheduler.day}"),
            ("In-Game Time:", f"{time_str} (Hour {scheduler.time_of_day:.2f})"),
            ("Season & Year:", f"{scheduler.season}, Year {scheduler.year}"),
            ("Current Week:", f"Week {scheduler.week}"),
            ("Total Real Seconds:", f"{scheduler.total_real_seconds:.1f} s"),
            ("Active Subscribers:", str(scheduler.get_subscriber_counts()))
        ]
        
        curr_y = y + 44
        for label, val in lines:
            lbl_surf = self.font_body.render(label, True, (180, 200, 220))
            val_surf = self.font_header.render(val, True, (255, 215, 0) if "Time" in label else (240, 240, 240))
            surface.blit(lbl_surf, (x + 16, curr_y))
            surface.blit(val_surf, (x + 200, curr_y))
            curr_y += 24
            
        curr_y += 10
        stats_hdr = self.font_header.render("Dispatched Tick Statistics:", True, (0, 180, 216))
        surface.blit(stats_hdr, (x + 16, curr_y))
        curr_y += 22
        
        for tick_name, count in scheduler.tick_counts.items():
            t_surf = self.font_body.render(f" • {tick_name.capitalize()} Ticks:", True, (180, 200, 220))
            c_surf = self.font_header.render(str(count), True, (240, 240, 240))
            surface.blit(t_surf, (x + 24, curr_y))
            surface.blit(c_surf, (x + 200, curr_y))
            curr_y += 20

    def _draw_eventbus_panel(self, surface: pygame.Surface, game_context: Any) -> None:
        """Renders live EventBus Signal Stream & Microsecond Subsystem Timings (F8)."""
        w, h = 640, 420
        x = (SCREEN_WIDTH - w) // 2
        y = (SCREEN_HEIGHT - h) // 2
        
        self._draw_card_frame(surface, x, y, w, h, "[F8] EVENTBUS SIGNAL INSPECTOR & PROFILER", "Live Signal Stream & Subsystem Timings")
        
        # Pull telemetry object
        telemetry = getattr(game_context, "telemetry", None)
        if not telemetry:
            lbl = self.font_body.render("Telemetry logger active.", True, (180, 180, 180))
            surface.blit(lbl, (x + 16, y + 50))
            return

        curr_y = y + 46
        # Subsystem Timing breakdown
        tb_hdr = self.font_header.render("Subsystem Execution Timings (ms):", True, (0, 180, 216))
        surface.blit(tb_hdr, (x + 16, curr_y))
        curr_y += 20
        
        tb_str = "  ".join([f"{k}: {v}ms" for k, v in telemetry.subsystem_timings.items()])
        tb_surf = self.font_body.render(tb_str, True, (255, 215, 0))
        surface.blit(tb_surf, (x + 20, curr_y))
        curr_y += 26

        # Signal Stream Stream Header
        st_hdr = self.font_header.render("Recent EventBus Signals (Live Stream):", True, (0, 180, 216))
        surface.blit(st_hdr, (x + 16, curr_y))
        curr_y += 20

        # Display recent 12 signals
        recent_signals = telemetry.signal_stream[-12:]
        for t_stamp, ev_name, payload in reversed(recent_signals):
            line_txt = f"[{t_stamp}] {ev_name.upper():<24} ({payload})"
            l_surf = self.font_body.render(line_txt, True, (200, 220, 240))
            surface.blit(l_surf, (x + 20, curr_y))
            curr_y += 18
