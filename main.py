"""
Echoes of Asterra - Game Entry Point
Initializes Pygame window settings, pre-computes assets, and boots the game loop.
"""
import os
import sys

# Dynamic path bootstrap to prevent ModuleNotFoundError: No module named 'rpg'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pygame
from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from rpg.constants import GAME_TITLE
from rpg.animation import init_assets
from rpg.game import Game

def main() -> None:
    """Main program entry point."""
    # 1. Initialize Pygame core modules
    pygame.init()

    # Configure display screen (SCALED mode for high-DPI mouse alignment)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED)
    pygame.display.set_caption(GAME_TITLE)

    # Load custom icon (draw simple pixel art sword to icon surface)
    icon_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.line(icon_surf, (240, 245, 255), (6, 26), (26, 6), 3)
    pygame.draw.circle(icon_surf, (200, 160, 40), (6, 26), 4)
    pygame.display.set_icon(icon_surf)

    # 2. Pre-compute and pre-render all procedural pixel-art assets
    print("Echoes of Asterra: Generating procedural visual assets in memory...")
    init_assets()
    print("Echoes of Asterra: Graphical assets compiled successfully.")

    # 3. Instantiate Game engine coordinator
    game_engine = Game(screen)

    # 4. Main gameplay execution loop
    print("Echoes of Asterra: Booting game loop. Starting state: MENU.")
    try:
        while True:
            # Update all game logic systems
            game_engine.update()

            # Draw frame buffers
            game_engine.draw()

    except SystemExit:
        # Standard exit caught cleanly
        pass
    except Exception as e:
        print(f"Game Crash: An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'game_engine' in locals() and hasattr(game_engine, "services"):
            game_engine.services.shutdown()
        pygame.quit()


if __name__ == "__main__":
    main()
