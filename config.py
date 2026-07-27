"""
Echoes of Asterra - Game Configuration
Centralized configuration source for engine settings, service feature flags, and performance budgets.
"""
from dataclasses import dataclass, field

@dataclass
class NavigationConfig:
    enable_astar: bool = True
    recalc_interval_seconds: float = 0.5
    target_move_threshold_pixels: float = 64.0  # 1 tile in 64x64 grid

@dataclass
class NoiseConfig:
    enable_simplex: bool = True
    default_scale: float = 0.05

@dataclass
class TweenConfig:
    enable_easing: bool = True

@dataclass
class AdminUIConfig:
    enable_pygame_gui: bool = True
    theme_path: str = "assets/ui/theme.json"

@dataclass
class PerformanceConfig:
    target_fps: int = 60
    max_frame_time_ms: float = 16.6
    nav_budget_ms: float = 2.0
    ui_budget_ms: float = 1.0

@dataclass
class GameConfig:
    navigation: NavigationConfig = field(default_factory=NavigationConfig)
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    tween: TweenConfig = field(default_factory=TweenConfig)
    admin_ui: AdminUIConfig = field(default_factory=AdminUIConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

# Global configuration instance
game_config = GameConfig()
