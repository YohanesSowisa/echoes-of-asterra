"""
Echoes of Asterra - Service Container
Centralized Dependency Injection container passed to game states and entities.
Enforces DAG dependency ordering and formal service lifecycle phases (Boot, Context Bind, Reset, Shutdown).
"""
import logging
from typing import Optional, Any
from rpg.config import GameConfig, game_config
from rpg.services.data import DataService
from rpg.services.asset import AssetService
from rpg.services.noise import NoiseService
from rpg.services.tween import TweenService
from rpg.services.tilemap import TilemapService
from rpg.services.navigation import NavigationService
from rpg.services.admin_ui import AdminUIService
from rpg.services.profiling import ProfilingService

logger = logging.getLogger("ServiceContainer")


class ServiceContainer:
    """
    Dependency Injection container holding instances of all engine system services.
    Enforces a strict Directed Acyclic Graph (DAG) initialization order.
    """
    def __init__(self, config: Optional[GameConfig] = None, event_bus: Optional[Any] = None) -> None:
        self.config = config or game_config
        self.event_bus = event_bus
        
        # Lifecycle Phase 1: Boot Core Foundation Services (Layer 0 DAG)
        self.data = DataService()
        self.asset = AssetService(self.config.asset)
        self.noise = NoiseService(self.config.noise)
        self.tween = TweenService(self.config.tween)
        self.profiling = ProfilingService(self.config.profiling)
        
        # Lifecycle Phase 1b: Derived Subsystem Services (Layer 1 DAG)
        self.tilemap = TilemapService(asset_service=self.asset, feature_flags=self.config.feature_flags)
        
        # Lifecycle Phase 2: Context-Bound System Services (Layer 2 DAG)
        self.navigation = NavigationService(self.config.navigation, event_bus=self.event_bus)
        self.admin_ui = AdminUIService(self.config.admin_ui)
        
        logger.info("ServiceContainer initialized successfully following strict DAG ordering.")

    def reset_services(self) -> None:
        """
        Lifecycle Phase 3: Transition / Reset Phase.
        Flushes caches and invalidates temporary data upon map transitions or game load.
        """
        self.navigation.invalidate_cache()
        self.tilemap.clear_cache()
        self.asset.unload_unused()
        logger.info("ServiceContainer: Reset services successfully completed.")

    def shutdown(self) -> None:
        """
        Lifecycle Phase 4: Shutdown Phase.
        Exports telemetry and releases system resources on engine exit.
        """
        self.profiling.export_json()
        self.asset.unload_unused()
        logger.info("ServiceContainer: Shutdown complete.")
