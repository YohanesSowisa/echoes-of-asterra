"""
Echoes of Asterra - Game Entry Point
Initializes Pygame window settings, pre-computes assets, and boots the game loop.
"""
import os
import sys
import asyncio

# Dynamic path bootstrap to prevent ModuleNotFoundError: No module named 'rpg'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pygame
pygame.mixer.pre_init(44100, -16, 2, 4096)  # MUST be called before pygame.init() to fix WASM audio crackling!
pygame.init()  # Init early for font monkey-patching

# --- WASM COMPATIBILITY: Monkey-patch SysFont ---
# Emscripten/Pygbag hangs or crashes when querying system fonts via SysFont.
def _safe_sysfont(name, size, bold=False, italic=False):
    return pygame.font.Font(None, size)
pygame.font.SysFont = _safe_sysfont

from rpg.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from rpg.constants import GAME_TITLE
from rpg.animation import init_assets
from rpg.game import Game

async def main() -> None:
    """Main program entry point."""
    # 1. Initialize Pygame core modules
    pygame.init()

    # Configure display screen (Remove SCALED mode for WASM compatibility)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(GAME_TITLE)
    
    # [WASM-Specific] Style the browser DOM to make the game fill the window and remove gray borders
    import sys
    if sys.platform == "emscripten":
        try:
            import platform
            window = platform.window
            document = window.document
            document.body.style.backgroundColor = "black"
            document.body.style.margin = "0"
            document.body.style.overflow = "hidden"
            canvas = document.getElementById("canvas")
            if canvas:
                canvas.style.width = "100vw"
                canvas.style.height = "100vh"
                canvas.style.objectFit = "contain" # Preserves 16:9 aspect ratio but scales to maximum size
        except Exception as e:
            print(f"WASM: Failed to inject DOM styling: {e}")

    await asyncio.sleep(0)  # Yield to browser DOM

    # Load custom icon (draw simple pixel art sword to icon surface)
    icon_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.line(icon_surf, (240, 245, 255), (6, 26), (26, 6), 3)
    pygame.draw.circle(icon_surf, (200, 160, 40), (6, 26), 4)
    pygame.display.set_icon(icon_surf)

    # 2. Pre-compute and pre-render all procedural pixel-art assets
    print("Echoes of Asterra: Generating procedural visual assets in memory...")
    await asyncio.sleep(0)  # Yield before heavy asset generation
    await init_assets()
    print("Echoes of Asterra: Graphical assets compiled successfully.")
    await asyncio.sleep(0)  # Yield after heavy asset generation

    # 3. Instantiate Game engine coordinator
    game_engine = Game(screen)
    await asyncio.sleep(0)

    # 4. Main gameplay execution loop
    print("Echoes of Asterra: Booting game loop. Starting state: MENU.")
    try:
        while True:
            # Update all game logic systems
            game_engine.update()

            # Draw frame buffers
            game_engine.draw()

            await asyncio.sleep(0)

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
    asyncio.run(main())
