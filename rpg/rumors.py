"""
Echoes of Asterra - The Rumor Mill Engine
Simulates rumor creation, organic propagation between NPCs, and progressive information distortion over time.
NPCs share rumors with the player during dialogue interactions.
"""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from rpg.events import EventBus

# Predefined initial world rumor templates (topic -> true content vs distorted version)
INITIAL_RUMOR_TEMPLATES = [
    {
        "id": "rumor_ruins_relic",
        "topic": "Ruins Treasure",
        "origin": "mira",
        "true_content": "Scholar Mira found evidence of an ancient relic buried in the Sunken Ruins.",
        "distorted_content": "They say a legendary golden sword of immense power is lying open in the ruins plaza!",
        "is_true": True
    },
    {
        "id": "rumor_wolf_migration",
        "topic": "Forest Shadows",
        "origin": "faye",
        "true_content": "Ranger Faye noticed wolves migrating south toward the lake crossroads.",
        "distorted_content": "A colossal shadow wolf packs is massing to destroy the northern bridge!",
        "is_true": True
    },
    {
        "id": "rumor_cave_iron",
        "topic": "Rich Ores",
        "origin": "garth",
        "true_content": "Miner Garth uncovered a rich vein of Iron Ore in the deeper cave chambers.",
        "distorted_content": "The cave walls are turning solid gold — miners are becoming rich overnight!",
        "is_true": True
    },
    {
        "id": "rumor_crypt_overlord",
        "topic": "Shadow Overlord",
        "origin": "eldrin",
        "true_content": "Elder Eldrin warns that dark energy pulses from the Endless Crypt floor 1.",
        "distorted_content": "The Shadow Overlord has risen and commands an army of undead at the village gates!",
        "is_true": True
    }
]

@dataclass
class Rumor:
    """Represents a piece of information propagating between NPCs."""
    rumor_id: str
    topic: str
    origin_npc: str
    true_content: str
    distorted_content: str
    is_true: bool = True
    distortion_level: float = 0.0  # 0.0 = accurate, >0.5 = distorted version
    known_by_npcs: Set[str] = field(default_factory=set)


class RumorBoard:
    """
    Manages global rumor simulation across Asterra.
    Propagates rumors between NPCs on day ticks with progressive distortion.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.rumors: Dict[str, Rumor] = {}
        self.npc_list = ["eldrin", "dennis", "silas", "faye", "garth", "kai", "mira"]
        self._init_default_rumors()

        if self.event_bus:
            self.register_event_listeners(self.event_bus)

    def _init_default_rumors(self) -> None:
        for t in INITIAL_RUMOR_TEMPLATES:
            r = Rumor(
                rumor_id=t["id"],
                topic=t["topic"],
                origin_npc=t["origin"],
                true_content=t["true_content"],
                distorted_content=t["distorted_content"],
                is_true=t["is_true"],
                distortion_level=0.0,
                known_by_npcs={t["origin"]}
            )
            self.rumors[r.rumor_id] = r

    def register_event_listeners(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        event_bus.subscribe("day_changed", self._on_day_changed)

    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        """Spreads rumors between NPCs daily and increases distortion on transfer."""
        for rumor in self.rumors.values():
            if not rumor.known_by_npcs:
                continue

            # Pick an NPC who knows the rumor
            teller = random.choice(list(rumor.known_by_npcs))
            # Pick a target NPC who doesn't know it yet
            unknown = [npc for npc in self.npc_list if npc not in rumor.known_by_npcs]

            if unknown and random.random() < 0.60:  # 60% chance to share rumor daily
                listener = random.choice(unknown)
                rumor.known_by_npcs.add(listener)

                # 25% chance of distortion upon rumor transmission
                if random.random() < 0.25:
                    rumor.distortion_level = min(1.0, rumor.distortion_level + 0.3)

                if self.event_bus:
                    self.event_bus.emit(
                        "rumor_spread",
                        rumor_id=rumor.rumor_id,
                        teller=teller,
                        listener=listener,
                        distortion=rumor.distortion_level
                    )

    def get_npc_rumor(self, npc_short_id: str) -> Optional[Tuple[str, str, float]]:
        """
        Returns an active rumor known by an NPC.
        Returns tuple: (topic, text_content, distortion_level).
        """
        known = [r for r in self.rumors.values() if npc_short_id in r.known_by_npcs]
        if not known:
            # Fallback rumor: tell original rumor if origin, else default
            origin_rumors = [r for r in self.rumors.values() if r.origin_npc == npc_short_id]
            if origin_rumors:
                r = origin_rumors[0]
                r.known_by_npcs.add(npc_short_id)
                return (r.topic, r.true_content, r.distortion_level)
            return None

        selected = random.choice(known)
        content = selected.distorted_content if selected.distortion_level >= 0.4 else selected.true_content
        return (selected.topic, content, selected.distortion_level)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes rumor state."""
        return {
            "rumors": {
                k: {
                    "rumor_id": v.rumor_id,
                    "topic": v.topic,
                    "origin_npc": v.origin_npc,
                    "true_content": v.true_content,
                    "distorted_content": v.distorted_content,
                    "is_true": v.is_true,
                    "distortion_level": v.distortion_level,
                    "known_by_npcs": list(v.known_by_npcs)
                } for k, v in self.rumors.items()
            }
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes rumor state."""
        if not data:
            return
        rd = data.get("rumors", {})
        for k, v in rd.items():
            if k in self.rumors:
                r = self.rumors[k]
                r.distortion_level = v.get("distortion_level", r.distortion_level)
                r.known_by_npcs = set(v.get("known_by_npcs", list(r.known_by_npcs)))
