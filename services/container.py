"""
Echoes of Asterra - Service Container
Centralized Dependency Injection container passed to game states and entities.
"""
from typing import Optional, Any
from rpg.config import GameConfig, game_config
from rpg.services.navigation import NavigationService
from rpg.services.noise import NoiseService
from rpg.services.tween import TweenService
from rpg.services.admin_ui import AdminUIService


class ServiceContainer:
    """
    Dependency Injection container holding instances of all system services.
    Instantiated during game engine boot and passed down to GameContext.
    """
    def __init__(self, config: Optional[GameConfig] = None, event_bus: Optional[Any] = None) -> None:
        self.config = config or game_config
        self.event_bus = event_bus
        
        # Instantiate core services
        self.noise = NoiseService(self.config.noise)
        self.navigation = NavigationService(self.config.navigation, event_bus=self.event_bus)
        self.tween = TweenService(self.config.tween)
        self.admin_ui = AdminUIService(self.config.admin_ui)

    def reset_services(self) -> None:
        """Flushes caches and resets service states upon new game or load."""
        self.navigation.invalidate_cache()
