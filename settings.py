"""
Echoes of Asterra - Settings
Configurable settings, screen metrics, player stats, and controls.
"""
import pygame

# Display settings
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
TARGET_FPS = 60

# Tile settings
TILE_SIZE = 48  # pixels per tile
GRID_WIDTH = 40  # tiles per map width (procedural maps will use this)
GRID_HEIGHT = 30  # tiles per map height

# UI settings
HUD_HEIGHT = 80
FONT_SIZE_SMALL = 14
FONT_SIZE_MEDIUM = 20
FONT_SIZE_LARGE = 32
FONT_SIZE_TITLE = 48

# Player Configuration
PLAYER_SPEED = 4.0
PLAYER_RUN_MULTIPLIER = 1.6
PLAYER_ROLL_SPEED = 8.0
PLAYER_ROLL_DURATION = 250  # milliseconds
PLAYER_ROLL_COOLDOWN = 600  # milliseconds
PLAYER_I_FRAMES_DURATION = 500  # milliseconds

# Particle systems
MAX_PARTICLES = 1000

# Day-Night Cycle settings
DAY_LENGTH_SECONDS = 1440.0  # length of a full day cycle (1s real life = 1m in game -> 1 day = 24 minutes)

# Sound configurations
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2
AUDIO_BUFFER_SIZE = 1024
MUSIC_VOLUME = 0.4
SFX_VOLUME = 0.6

# Key Bindings
KEY_UP = pygame.K_w
KEY_DOWN = pygame.K_s
KEY_LEFT = pygame.K_a
KEY_RIGHT = pygame.K_d
KEY_RUN = pygame.K_LSHIFT
KEY_ROLL = pygame.K_SPACE
KEY_ATTACK = pygame.K_j
KEY_BLOCK = pygame.K_k
KEY_SKILL_1 = pygame.K_1
KEY_SKILL_2 = pygame.K_2
KEY_SKILL_3 = pygame.K_3
KEY_SKILL_4 = pygame.K_4
KEY_INTERACT = pygame.K_e
KEY_INVENTORY = pygame.K_i
KEY_CHARACTER = pygame.K_c
KEY_QUEST = pygame.K_q
KEY_CRAFTING = pygame.K_g
KEY_ESCAPE = pygame.K_ESCAPE
KEY_SAVE = pygame.K_F5
KEY_LOAD = pygame.K_F9
KEY_MINIMAP = pygame.K_m
