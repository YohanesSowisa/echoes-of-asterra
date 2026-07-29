"""
Echoes of Asterra - Administrative UI Service
Encapsulates pygame_gui for administrative menus (Settings, Save/Load slots).
Core gameplay HUD and Harvest Moon dialogue panels remain custom.
"""
import os
import logging
import pygame
from typing import Optional, Dict, Any
from rpg.config import AdminUIConfig, game_config
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT

logger = logging.getLogger("AdminUIService")

# Optional third-party pygame_gui import
try:
    import pygame_gui
    PYGAME_GUI_AVAILABLE = True
except ImportError:
    pygame_gui = None
    PYGAME_GUI_AVAILABLE = False


class AdminUIService:
    """
    Service wrapper for administrative GUI controls (Settings, Save/Load browser).
    """
    def __init__(self, config: Optional[AdminUIConfig] = None) -> None:
        self.config = config or game_config.admin_ui
        self.manager: Optional[Any] = None
        
        if self.config.enable_pygame_gui and PYGAME_GUI_AVAILABLE:
            try:
                theme_path = self.config.theme_path
                if os.path.exists(theme_path):
                    self.manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT), theme_path)
                else:
                    self.manager = pygame_gui.UIManager((SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception as e:
                logger.warning(f"Failed to initialize pygame_gui manager ({e}). Falling back.")
                self.manager = None

    def process_event(self, event: pygame.event.Event) -> None:
        """Public API: Feeds Pygame events to pygame_gui UIManager when active."""
        if self.manager:
            try:
                self.manager.process_events(event)
            except Exception as e:
                logger.warning(f"Failed processing GUI event: {e}")

    def update(self, time_delta: float) -> None:
        """Public API: Updates UIManager animation timers."""
        if self.manager:
            try:
                self.manager.update(time_delta)
            except Exception as e:
                logger.warning(f"Failed updating GUI manager: {e}")

    def draw_settings_panel(self, surface: pygame.Surface) -> None:
        """Public API: Renders settings widgets onto surface if available."""
        if self.manager:
            try:
                self.manager.draw_ui(surface)
            except Exception as e:
                logger.warning(f"Failed drawing settings panel: {e}")

    def draw_save_browser(self, surface: pygame.Surface, slots_meta: Dict[int, Any]) -> None:
        """Public API: Renders save slot browser widgets onto surface if available."""
        if self.manager:
            try:
                self.manager.draw_ui(surface)
            except Exception as e:
                logger.warning(f"Failed drawing save browser: {e}")

