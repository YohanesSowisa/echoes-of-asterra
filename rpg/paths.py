"""
Echoes of Asterra - Centralized Path & Storage Resolution Engine
Manages path discovery for assets, persistent game saves, and runtime data.
Ensures full compatibility between native development runs, packaged
PyInstaller standalone binaries (frozen mode), and browser environments.
"""
import os
import sys

# Compute project root (echoes-of-asterra/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_persistent_data_dir() -> str:
    """
    Returns the persistent directory for player data, save files, and configuration.
    
    When running as a packaged PyInstaller executable (sys.frozen is True), files stored
    in sys._MEIPASS are ephemeral and cleaned up on application exit. To ensure player
    progress, achievements, bestiary, and social reputation survive across application launches,
    persistent data is stored in the directory adjacent to the executable.
    
    In development / source mode, persistent data is stored in the project root (BASE_DIR).
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return BASE_DIR


def get_saves_dir() -> str:
    """
    Returns the persistent directory path for save game files and ensures it exists.
    """
    saves_dir = os.path.join(get_persistent_data_dir(), "saves")
    os.makedirs(saves_dir, exist_ok=True)
    return saves_dir


def get_save_file_path(filename: str) -> str:
    """
    Resolves the absolute path for a specific persistent save file.
    """
    return os.path.join(get_saves_dir(), filename)
