"""
Echoes of Asterra - Game Configuration
Centralized configuration source for engine settings, service feature flags, deterministic seeds, and performance budgets.
"""
import hashlib
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
class FeatureFlagConfig:
    tilemap: bool = True
    lighting: bool = True
    weather: bool = True
    navigation_async: bool = True
    admin_ui: bool = True
    profiling: bool = False

@dataclass
class AssetConfig:
    manifest_path: str = "assets/manifest.json"
    lazy_loading: bool = True
    fallback_texture_size: tuple = (64, 64)

@dataclass
class SeedConfig:
    world_seed: int = 133742

@dataclass
class ProfilingConfig:
    enabled: bool = False
    export_format: str = "json"
    export_filepath: str = "profiling_export.json"
    sample_window_size: int = 60

@dataclass
class PerformanceConfig:
    target_fps: int = 60
    max_frame_time_ms: float = 16.6
    rendering_budget_ms: float = 8.0
    ai_budget_ms: float = 2.0
    nav_budget_ms: float = 2.0
    particles_budget_ms: float = 1.0
    lighting_budget_ms: float = 1.0
    audio_budget_ms: float = 0.5

@dataclass
class GameConfig:
    navigation: NavigationConfig = field(default_factory=NavigationConfig)
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    tween: TweenConfig = field(default_factory=TweenConfig)
    admin_ui: AdminUIConfig = field(default_factory=AdminUIConfig)
    feature_flags: FeatureFlagConfig = field(default_factory=FeatureFlagConfig)
    asset: AssetConfig = field(default_factory=AssetConfig)
    seed: SeedConfig = field(default_factory=SeedConfig)
    profiling: ProfilingConfig = field(default_factory=ProfilingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

    def get_subsystem_seed(self, domain: str) -> int:
        """Generates an isolated deterministic seed for a procedural domain."""
        hash_input = f"{self.seed.world_seed}:{domain}".encode('utf-8')
        return int(hashlib.sha256(hash_input).hexdigest()[:8], 16)

# Global configuration instance
game_config = GameConfig()
