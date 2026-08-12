"""
Echoes of Asterra - Dialogue System
Handles dialogue nodes, typing text animations, portraits, choices, and branching states.
"""
from typing import List, Dict, Callable, Optional

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
        """Sets the active node, resets scroll parameters, and guarantees a neutral exit choice."""
        node = self.nodes.get(node_id)
        if node:
            self.current_node = node
            self.visible_text = ""
            self.char_index = 0.0
            self.typing_finished = False
            self.selected_choice_idx = 0

            # Guarantee rumor choice and neutral "Leave / Back" choice for dialogue with options
            if node.choices:
                # 1. Inject "Heard any rumors?" option if not present and game rumors system active
                if hasattr(self, "game") and self.game and hasattr(self.game, "living_world") and hasattr(self.game.living_world, "rumors"):
                    if not node.id.endswith("_rumor_response") and not any("rumor" in c.text.lower() for c in node.choices):
                        npc_key = node.speaker_name.split()[-1].lower()
                        speaker_title = node.speaker_name
                        
                        def make_rumor_cb(spk=speaker_title, key=npc_key):
                            def rumor_callback():
                                rumor_info = self.game.living_world.rumors.get_npc_rumor(key)
                                if rumor_info:
                                    topic, content, distortion = rumor_info
                                    prefix = "⚡ [DISTORTED RUMOR] " if distortion >= 0.4 else "🗣️ [TOWN RUMOR] "
                                    r_node = DialogueNode(
                                        f"{key}_rumor_response",
                                        spk,
                                        f"{prefix}Regarding {topic}: \"{content}\"",
                                        [DialogueChoice("Interesting...", None)]
                                    )
                                    self.add_node(r_node)
                                    self.set_node(f"{key}_rumor_response")
                                else:
                                    r_node = DialogueNode(
                                        f"{key}_rumor_response",
                                        spk,
                                        "Quiet days in Asterra... I haven't heard any new rumors today.",
                                        [DialogueChoice("Fair enough.", None)]
                                    )
                                    self.add_node(r_node)
                                    self.set_node(f"{key}_rumor_response")
                            return rumor_callback

                        rumor_choice = DialogueChoice("🗣️ Heard any rumors?", None, make_rumor_cb())
                        node.choices.insert(max(0, len(node.choices) - 1), rumor_choice)

                # 2. Guarantee at least one neutral "Leave / Back" choice
                has_neutral_exit = any(
                    (c.callback is None and c.next_node_id is None) or
                    any(kw in c.text.lower() for kw in ["leave", "back", "close", "goodbye", "later", "not now", "keluar", "kembali", "tutup", "interesting", "fair enough"])
                    for c in node.choices
                )
                if not has_neutral_exit:
                    node.choices.append(DialogueChoice("Leave / Back", None))
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
