"""
Echoes of Asterra - Dialogue System
Handles dialogue nodes, typing text animations, portraits, choices, and branching states.
"""
from typing import List, Tuple, Dict, Callable, Optional, Any

class DialogueChoice:
    """
    Represents a branching selection option in a conversation.
    """
    def __init__(self, text: str, next_node_id: Optional[str], callback: Optional[Callable[[], None]] = None) -> None:
        self.text = text
        self.next_node_id = next_node_id
        self.callback = callback

class DialogueNode:
    """
    A single screen/frame of dialogue from an NPC.
    """
    def __init__(
        self,
        node_id: str,
        speaker_name: str,
        text: str,
        choices: Optional[List[DialogueChoice]] = None,
        portrait_key: str = "default"
    ) -> None:
        self.id = node_id
        self.speaker_name = speaker_name
        self.text = text
        self.choices = choices if choices is not None else []
        self.portrait_key = portrait_key

class DialogueManager:
    """
    Main dialogue state machine.
    Manages characters animation text, scrolling indexes, selection cursor.
    """
    def __init__(self) -> None:
        self.nodes: Dict[str, DialogueNode] = {}
        self.current_node: Optional[DialogueNode] = None
        
        # Typing animation variables
        self.visible_text = ""
        self.char_index = 0.0
        self.type_speed = 35.0  # Characters per second
        self.typing_finished = False
        
        # Choice selection variables
        self.selected_choice_idx = 0

    def add_node(self, node: DialogueNode) -> None:
        """Registers a dialogue node."""
        self.nodes[node.id] = node

    def start_dialogue(self, node_id: str) -> None:
        """Triggers the start of a conversation from a registered node."""
        self.set_node(node_id)

    def set_node(self, node_id: str) -> None:
        """Sets the active node and resets scroll parameters."""
        node = self.nodes.get(node_id)
        if node:
            self.current_node = node
            self.visible_text = ""
            self.char_index = 0.0
            self.typing_finished = False
            self.selected_choice_idx = 0
        else:
            self.close()

    def update(self, dt: float) -> None:
        """Updates text spelling/typing animation timer."""
        if not self.current_node or self.typing_finished:
            return
            
        target_text = self.current_node.text
        self.char_index += self.type_speed * dt
        
        # Clip index and check if done
        idx = int(self.char_index)
        if idx >= len(target_text):
            self.visible_text = target_text
            self.typing_finished = True
        else:
            self.visible_text = target_text[:idx]

    def advance(self) -> None:
        """
        Advances the dialogue. If text is typing, skips typing animation.
        If choices exist, performs the highlighted choice action.
        If no choices exist, advances to next node or closes.
        """
        if not self.current_node:
            return

        # 1. Skip spelling animation if in progress
        if not self.typing_finished:
            self.visible_text = self.current_node.text
            self.typing_finished = True
            return

        # 2. Process choice selection if present
        if self.current_node.choices:
            choice = self.current_node.choices[self.selected_choice_idx]
            # Fire callback if registered
            if choice.callback:
                choice.callback()
            # Advance to next node
            if choice.next_node_id:
                self.set_node(choice.next_node_id)
            else:
                self.close()
        else:
            # Simple linear dialogue with no choices: close
            self.close()

    def select_next_choice(self) -> None:
        """Moves highlighted choice cursor down."""
        if self.current_node and self.current_node.choices:
            self.selected_choice_idx = (self.selected_choice_idx + 1) % len(self.current_node.choices)

    def select_prev_choice(self) -> None:
        """Moves highlighted choice cursor up."""
        if self.current_node and self.current_node.choices:
            self.selected_choice_idx = (self.selected_choice_idx - 1) % len(self.current_node.choices)

    def close(self) -> None:
        """Terminates dialogue, exiting to standard play state."""
        self.current_node = None
        self.visible_text = ""
        self.typing_finished = False
