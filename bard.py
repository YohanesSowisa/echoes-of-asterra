"""
Echoes of Asterra - Procedural Bard Memory Song Engine
Composes dynamic ballad stanzas referencing recorded player memories, titles, and reputation.
"""
from typing import List, Optional
from rpg.memory import MemoryManager
from rpg.social import ReputationManager

class BardSongEngine:
    """Procedurally composes ballad songs from active player memories."""
    @staticmethod
    def compose_song(memory_manager: Optional[MemoryManager], reputation_manager: Optional[ReputationManager]) -> str:
        active_title = reputation_manager.active_title if reputation_manager else "Wanderer"
        stanzas = [f"♪ Gather 'round, travelers, and hear the ballad of the {active_title}! ♪\n"]

        has_any_memory = False

        if memory_manager:
            if memory_manager.has_memory("donated_iron_ore"):
                stanzas.append("♫ They say the Iron Benefactor carried ore upon weary shoulders,\nand because of that gift, the village guards stand bolder! ♫")
                has_any_memory = True

            if memory_manager.has_memory("cleared_dungeon_crypt"):
                stanzas.append("♫ Deep beneath the ancient crypt where shadows creep,\nthe Champion silenced the halls of eternal sleep! ♫")
                has_any_memory = True

            if memory_manager.has_memory("challenged_greed_altar"):
                stanzas.append("♫ When tempted by the Greed Altar's burning light,\nthey faced the dark curse and stood victorious in fight! ♫")
                has_any_memory = True

        if not has_any_memory:
            stanzas.append("♫ Across the misty valleys of Asterra, a new hero walks,\nand soon the world will whisper of their destiny in taverns and talks! ♫")

        return "\n\n".join(stanzas)
