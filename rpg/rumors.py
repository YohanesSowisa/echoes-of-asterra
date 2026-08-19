"""
Echoes of Asterra - The Rumor Mill Engine
Simulates rumor creation, organic propagation between NPCs, and progressive information distortion over time.
NPCs share rumors with the player during dialogue interactions.
"""
import random
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set, Tuple
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
    },
    {
        "id": "rumor_bran_bribes",
        "topic": "Corrupt Guard",
        "origin": "faye",
        "true_content": "Ranger Faye saw Guard Lieutenant Bran accepting heavy coin purses from masked cloaked figures at the Forest crossroads.",
        "distorted_content": "Lieutenant Bran has traded the entire village garrison to shadow assassins for chests of rubies!",
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
    Manages the global rumor ecosystem. Rumors spread daily between NPCs
    based on proximity and friendship networks, distorting over time.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.rumors: Dict[str, Rumor] = {}
        self.npc_list = ["eldrin", "silas", "dennis", "mira", "faye", "garth", "bran", "kai"]
        self._init_default_rumors()

        if self.event_bus:
            self.register_event_listeners(self.event_bus)
            self.event_bus.subscribe("boss_defeated", self._on_boss_defeated)
            self.event_bus.subscribe("spore_blight_escalated", self._on_spore_blight_escalated)
            self.event_bus.subscribe("suspect_neutralized", self._on_suspect_neutralized)
            self.event_bus.subscribe("npc_compromised", self._on_npc_compromised)
            self.event_bus.subscribe("npc_exorcised", self._on_npc_exorcised)
            self.event_bus.subscribe("sabotage_staged", self._on_sabotage_staged)
            self.event_bus.subscribe("sabotage_prevented", self._on_sabotage_prevented)
            self.event_bus.subscribe("conspiracy_resolved", self._on_conspiracy_resolved)
            self.event_bus.subscribe("continental_trade_monopoly_achieved", self._on_trade_monopoly_achieved)

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

    def add_custom_rumor(
        self,
        rumor_id: str,
        topic: str,
        origin_npc: str,
        true_content: str,
        distorted_content: str,
        is_true: bool = True
    ) -> Rumor:
        """Adds or updates a dynamic rumor into the rumor mill system."""
        r = Rumor(
            rumor_id=rumor_id,
            topic=topic,
            origin_npc=origin_npc,
            true_content=true_content,
            distorted_content=distorted_content,
            is_true=is_true,
            distortion_level=0.0,
            known_by_npcs={origin_npc}
        )
        self.rumors[rumor_id] = r
        if self.event_bus:
            self.event_bus.emit(
                "rumor_added",
                rumor_id=rumor_id,
                topic=topic,
                origin_npc=origin_npc
            )
        return r

    def check_monopoly_rumors(self, monopoly_manager: Any) -> None:
        """Injects dynamic market rumors reacting to commodity hoarding and trade embargoes."""
        if not monopoly_manager:
            return

        # 1. Iron Ore Hoarding Rumor
        if hasattr(monopoly_manager, "is_hoarding") and monopoly_manager.is_hoarding("iron_ore") and "rumor_iron_hoarding" not in self.rumors:
            self.add_custom_rumor(
                rumor_id="rumor_iron_hoarding",
                topic="Iron Scarcity",
                origin_npc="dennis",
                true_content="Blacksmith Dennis laments that an iron cartel is hoarding all ore, driving weapon prices through the roof!",
                distorted_content="They say all the iron mines collapsed and soldiers are fighting with wooden sticks!",
                is_true=True
            )

        # 2. Bandit Medical Herb Embargo Rumor
        if hasattr(monopoly_manager, "is_faction_embargoed") and monopoly_manager.is_faction_embargoed("bandits", "medicinal_herb") and "rumor_bandit_herb_embargo" not in self.rumors:
            self.add_custom_rumor(
                rumor_id="rumor_bandit_herb_embargo",
                topic="Bandit Starvation",
                origin_npc="silas",
                true_content="Merchant Silas whispers that bandit raiding parties in the ruins are succumbing to infected wounds after their herb supply was cut off!",
                distorted_content="The bandit dens are completely abandoned, haunted by plague ghosts!",
                is_true=True
            )

    def _on_boss_defeated(self, boss_id: str = "", **kwargs: Any) -> None:
        if boss_id == "mire_leviathan":
            self.add_custom_rumor(
                "rumor_leviathan_slain",
                "Mire Leviathan Slain",
                "eldrin",
                "The champion braved the Submerged Temple and slew Morvath, stabilizing the marsh tides!",
                "They say the hero single-handedly wrestled a ten-headed leviathan from the deep mud!",
                is_true=True
            )

    def _on_spore_blight_escalated(self, rot_level: float = 60.0, **kwargs: Any) -> None:
        self.add_custom_rumor(
            "rumor_spore_blight",
            "Leyline Spore Blight",
            "faye",
            "Toxic fungal rot is spreading from the Mire, mutating forest wolves into aggressive spore-carriers!",
            "They say giant walking mushrooms are devouring our hunters in the Emerald Forest!",
            is_true=True
        )

    def _on_suspect_neutralized(self, suspect_id: str = "", suspect_name: str = "", **kwargs: Any) -> None:
        if suspect_id == "bran":
            self.add_custom_rumor(
                "rumor_bran_exposed",
                "Conspiracy Operative Exposed",
                "eldrin",
                "Lieutenant Bran was confronted and disarmed! Encrypted Syndicate orders were found on his person!",
                "They say Bran was a shadow shapeshifter sent to overthrow the Asterra crown!",
                is_true=True
            )

    def _on_npc_compromised(self, npc_id: str = "", name: str = "", **kwargs: Any) -> None:
        self.add_custom_rumor(
            f"rumor_compromised_{npc_id}",
            "Strange Mind Affliction",
            "silas",
            f"{name} has been acting strangely detached, muttering about shadows and void commands.",
            f"They say {name} has traded their very soul to the shadow syndicate for forbidden power!",
            is_true=True
        )

    def _on_npc_exorcised(self, npc_id: str = "", name: str = "", **kwargs: Any) -> None:
        self.add_custom_rumor(
            f"rumor_exorcised_{npc_id}",
            "Mind Exorcism Miracle",
            "eldrin",
            f"The champion cast out a Shadow Parasite from {name}, restoring their rightful mind!",
            f"The hero wrestled a shadowy demon straight out of {name}'s skull in a flash of holy starlight!",
            is_true=True
        )

    def _on_sabotage_staged(self, sabotage_id: str = "", target_point_id: str = "", target_map: str = "", **kwargs: Any) -> None:
        self.add_custom_rumor(
            f"rumor_{sabotage_id}",
            "Covert Sabotage Plot",
            "faye",
            f"Shadow cultists have been spotted lurking near {target_point_id} in the {target_map}! A sabotage plot is underway!",
            f"Shadow assassins are planting explosive dark stones to sink the entire {target_map} underground!",
            is_true=True
        )

    def _on_sabotage_prevented(self, sabotage_id: str = "", target_point_id: str = "", **kwargs: Any) -> None:
        self.add_custom_rumor(
            f"rumor_rescued_{sabotage_id}",
            "Mage Guild Envoy Rescued",
            "eldrin",
            f"The brave champion defended Envoy Vaelin from Shadow Assassins, exposing royal signet coup ciphers!",
            f"The hero obliterated twenty shadow ninjas in single combat to protect the high wizard!",
            is_true=True
        )

    def _on_conspiracy_resolved(self, ending: str = "total_purge", description: str = "", **kwargs: Any) -> None:
        if ending == "total_purge":
            topic = "Conspiracy Total Purge"
            true_txt = "The Grand Usurper has fallen! The Shadow Syndicate is eradicated from Asterra!"
            dist_txt = "The hero summoned the sun itself to vaporize the Grand Usurper and all his shadow legions!"
        elif ending == "shadow_sovereign":
            topic = "The Shadow Sovereign Reigns"
            true_txt = "The champion has assumed command of the Shadow Syndicate, ruling Asterra from the dark throne!"
            dist_txt = "The hero transformed into a ten-foot shadow monarch with demon wings!"
        else:
            topic = "The Syndicate Coup"
            true_txt = "The Syndicate has seized the kingdom in an iron grip. Resistance whispers in the dark."
            dist_txt = "Asterra has fallen under the eternal night of the shadow overlords!"

        self.add_custom_rumor(
            f"rumor_ending_{ending}",
            topic,
            "eldrin",
            true_txt,
            dist_txt,
            is_true=True
        )

    def _on_trade_monopoly_achieved(self, title: str = "Merchant Sovereign of Asterra", **kwargs: Any) -> None:
        self.add_custom_rumor(
            "rumor_continental_monopoly",
            "Continental Trade Monopoly",
            "silas",
            f"Every road across Asterra now bows to the {title}! Automated courier relays ensure total trade supremacy.",
            f"They say the {title} controls every coin and wagon moving across the continent!",
            is_true=True
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
        """Deserializes rumor state including custom dynamic rumors."""
        if not data:
            return
        rd = data.get("rumors", {})
        for k, v in rd.items():
            if k in self.rumors:
                r = self.rumors[k]
                r.distortion_level = v.get("distortion_level", r.distortion_level)
                r.known_by_npcs = set(v.get("known_by_npcs", list(r.known_by_npcs)))
            else:
                # Dynamic custom rumor restored from save
                self.rumors[k] = Rumor(
                    rumor_id=v.get("rumor_id", k),
                    topic=v.get("topic", "Rumor"),
                    origin_npc=v.get("origin_npc", "eldrin"),
                    true_content=v.get("true_content", ""),
                    distorted_content=v.get("distorted_content", ""),
                    is_true=v.get("is_true", True),
                    distortion_level=v.get("distortion_level", 0.0),
                    known_by_npcs=set(v.get("known_by_npcs", []))
                )

    def reset(self) -> None:
        """Resets active rumors to default un-distorted templates."""
        self.rumors.clear()
        self._init_default_rumors()


RumorManager = RumorBoard


