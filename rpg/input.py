"""
Echoes of Asterra - Input Handler
Manages player controls, mapping pygame key events and mouse presses into game actions.
"""
import pygame
from typing import Dict
from rpg.settings import (
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_RUN, KEY_ROLL,
    KEY_ATTACK, KEY_BLOCK, KEY_INTERACT, KEY_INVENTORY, KEY_CHARACTER,
    KEY_QUEST, KEY_CRAFTING, KEY_ESCAPE, KEY_SAVE, KEY_LOAD, KEY_MINIMAP,
    KEY_SKILL_1, KEY_SKILL_2, KEY_SKILL_3, KEY_SKILL_4
)

class InputHandler:
    """
    Tracks player inputs and translates raw keypresses into actions.
    Supports single-press actions (triggers) and continuous press states.
    """
    def __init__(self) -> None:
        # Movement vector
        self.move_dir = pygame.math.Vector2(0, 0)
        
        # Continuous press actions
        self.is_running = False
        self.is_blocking = False
        
        # Mouse tracking
        self.mouse_pos = pygame.math.Vector2(0, 0)
        self.mouse_clicked = False
        self.mouse_right_clicked = False
        
        # Single-press action triggers (reset on query or next frame)
        self.actions: Dict[str, bool] = {
            "attack": False,
            "roll": False,
            "interact": False,
            "inventory": False,
            "character": False,
            "quest": False,
            "crafting": False,
            "escape": False,
            "save": False,
            "load": False,
            "minimap": False,
            "skill_1": False,
            "skill_2": False,
            "skill_3": False,
            "skill_4": False
        }

        # Joystick / Gamepad support
        self.joysticks = []
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                js = pygame.joystick.Joystick(i)
                js.init()
                self.joysticks.append(js)
        except Exception as e:
            import logging
            logging.warning(f"Joystick initialization skipped: {e}")

    def process_events(self, events: list[pygame.event.Event]) -> None:
        """Processes pygame event list to capture single-press triggers."""
        # Reset mouse click and quick single-press action flags
        self.mouse_clicked = False
        self.mouse_right_clicked = False
        
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos.x, self.mouse_pos.y = event.pos
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.mouse_clicked = True
                elif event.button == 3:
                    self.mouse_right_clicked = True
            elif event.type == pygame.KEYDOWN:
                if event.key == KEY_ATTACK: self.actions["attack"] = True
                elif event.key == KEY_ROLL: self.actions["roll"] = True
                elif event.key == KEY_INTERACT: self.actions["interact"] = True
                elif event.key == KEY_INVENTORY: self.actions["inventory"] = True
                elif event.key == KEY_CHARACTER: self.actions["character"] = True
                elif event.key == KEY_QUEST: self.actions["quest"] = True
                elif event.key == KEY_CRAFTING: self.actions["crafting"] = True
                elif event.key == KEY_ESCAPE: self.actions["escape"] = True
                elif event.key == KEY_SAVE: self.actions["save"] = True
                elif event.key == KEY_LOAD: self.actions["load"] = True
                elif event.key == KEY_MINIMAP: self.actions["minimap"] = True
                elif event.key == KEY_SKILL_1: self.actions["skill_1"] = True
                elif event.key == KEY_SKILL_2: self.actions["skill_2"] = True
                elif event.key == KEY_SKILL_3: self.actions["skill_3"] = True
                elif event.key == KEY_SKILL_4: self.actions["skill_4"] = True
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0: self.actions["attack"] = True     # A button
                elif event.button == 1: self.actions["roll"] = True     # B button
                elif event.button == 2: self.actions["interact"] = True # X button
                elif event.button == 3: self.actions["inventory"] = True# Y button
                elif event.button == 6: self.actions["character"] = True# View button
                elif event.button == 7: self.actions["escape"] = True   # Menu button

    def update_keyboard_states(self) -> None:
        """Polls continuous keyboard and gamepad joystick states."""
        keys = pygame.key.get_pressed()
        
        # Calculate move direction
        self.move_dir.x = 0
        self.move_dir.y = 0
        
        if keys[KEY_LEFT]: self.move_dir.x -= 1
        if keys[KEY_RIGHT]: self.move_dir.x += 1
        if keys[KEY_UP]: self.move_dir.y -= 1
        if keys[KEY_DOWN]: self.move_dir.y += 1

        # Gamepad axis movement support (Left Analog Stick)
        if self.joysticks:
            for js in self.joysticks:
                try:
                    ax_x = js.get_axis(0)
                    ax_y = js.get_axis(1)
                    if abs(ax_x) > 0.2: self.move_dir.x += ax_x
                    if abs(ax_y) > 0.2: self.move_dir.y += ax_y
                except Exception:
                    pass
        
        if self.move_dir.length_squared() > 0:
            self.move_dir = self.move_dir.normalize()
            
        # Continuous modifiers
        self.is_running = keys[KEY_RUN]
        mouse_buttons = pygame.mouse.get_pressed()
        self.is_blocking = keys[KEY_BLOCK] or (len(mouse_buttons) >= 3 and mouse_buttons[2])

    def consume_action(self, action_name: str) -> bool:
        """Consumes a single-press action trigger and returns its status."""
        if self.actions.get(action_name, False):
            self.actions[action_name] = False
            return True
        return False

