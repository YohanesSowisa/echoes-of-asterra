"""
Echoes of Asterra - Persistent NPC Memory & Relationship System
Tracks hero interactions, crimes witnessed, gifts given, and quests completed for each NPC.
Drives dynamic dialogue greetings, rumor propagation, price discounts, and interaction refusals.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from rpg.constants import (
    REL_ENEMY, REL_STRANGER, REL_ACQUAINTANCE, REL_FRIEND, REL_CLOSE_FRIEND
)
from rpg.events import EventBus

@dataclass
class NPCMemory:
    """Stores persistent historical context and relationship score for a specific NPC."""
    npc_id: str
    relationship: int = 0  # Range: -100 to +100
    times_talked: int = 0
    times_attacked: int = 0
    gifts_given: List[str] = field(default_factory=list)
    quests_completed_for: List[str] = field(default_factory=list)
    crimes_witnessed: List[str] = field(default_factory=list)
    last_interaction_day: int = 0
    deja_vu_count: int = 0
    last_deja_vu_day: int = 0

    @property
    def friendship_level(self) -> str:
        if self.relationship <= -30:
            return REL_ENEMY
        elif self.relationship < 15:
            return REL_STRANGER
        elif self.relationship < 40:
            return REL_ACQUAINTANCE
        elif self.relationship < 75:
            return REL_FRIEND
        else:
            return REL_CLOSE_FRIEND

    def to_dict(self) -> Dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "relationship": self.relationship,
            "times_talked": self.times_talked,
            "times_attacked": self.times_attacked,
            "gifts_given": self.gifts_given,
            "quests_completed_for": self.quests_completed_for,
            "crimes_witnessed": self.crimes_witnessed,
            "last_interaction_day": self.last_interaction_day,
            "deja_vu_count": self.deja_vu_count,
            "last_deja_vu_day": self.last_deja_vu_day
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NPCMemory':
        return cls(
            npc_id=data["npc_id"],
            relationship=data.get("relationship", 0),
            times_talked=data.get("times_talked", 0),
            times_attacked=data.get("times_attacked", 0),
            gifts_given=data.get("gifts_given", []),
            quests_completed_for=data.get("quests_completed_for", []),
            crimes_witnessed=data.get("crimes_witnessed", []),
            last_interaction_day=data.get("last_interaction_day", 0),
            deja_vu_count=data.get("deja_vu_count", 0),
            last_deja_vu_day=data.get("last_deja_vu_day", 0)
        )

class NPCMemoryManager:
    """
    Manages memories for all non-player characters in Asterra.
    """
    def __init__(self) -> None:
        self.memories: Dict[str, NPCMemory] = {}

    def get_memory(self, npc_id: str) -> NPCMemory:
        """Retrieves or creates memory object for an NPC."""
        if npc_id not in self.memories:
            self.memories[npc_id] = NPCMemory(npc_id=npc_id)
        return self.memories[npc_id]

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes to global EventBus topics."""
        event_bus.subscribe("npc_talked", self._on_npc_talked)
        event_bus.subscribe("npc_attacked", self._on_npc_attacked)
        event_bus.subscribe("quest_completed", self._on_quest_completed)
        event_bus.subscribe("day_changed", self._on_day_changed)
        event_bus.subscribe("timeline_rewound", self._on_timeline_rewound)

    def modify_relationship(self, npc_id: str, amount: int) -> None:
        """Adjusts relationship score for an NPC."""
        mem = self.get_memory(npc_id)
        mem.relationship = max(-100, min(100, mem.relationship + amount))

    def record_gift(self, npc_id: str, item_name: str, value_bonus: int = 10) -> None:
        """Records a gift given to an NPC."""
        mem = self.get_memory(npc_id)
        mem.gifts_given.append(item_name)
        self.modify_relationship(npc_id, value_bonus)

    def get_greeting_prefix(self, npc_id: str, player: Optional[Any] = None) -> str:
        """Returns dynamic dialogue prefix based on relationship status, compromised mind, and active Soul Pacts."""
        # 1. Compromised Mind Reactivity Check
        if player and hasattr(player, "game") and player.game and hasattr(player.game, "conspiracy_manager"):
            cm = player.game.conspiracy_manager
            clean_id = npc_id.lower().replace(" ", "").replace("npc_", "")
            if cm and cm.is_npc_compromised(clean_id):
                c_data = cm.compromised_npcs.get(clean_id)
                if c_data:
                    return c_data.cold_dialogue

        # 2. Soul Pact Social Reactivity Check
        if player and hasattr(player, "game") and player.game and getattr(player.game, "pact_manager", None):
            pm = player.game.pact_manager
            if pm and hasattr(pm, "state") and pm.state:
                active_pact = getattr(pm.state, "active_pact_id", None)
                tier = getattr(pm.state, "pact_tier", 1)
                if active_pact == "void":
                    if "eldrin" in npc_id.lower():
                        if tier >= 2:
                            return "The void within you is deepening, Hero! The elders of Asterra fear the abyss will consume your very soul."
                        return "Hero... the dark miasma clinging to your flesh fills me with dread. What have you awakened in the deep crypts?"
                    elif "silas" in npc_id.lower() and tier >= 2:
                        return "By the trade winds! Those tentacles near my delicate goods cost extra hazard fees..."
                    return "Keep your shadowy appendages sheathed within our village walls, wanderer."
                elif active_pact == "titan":
                    if "eldrin" in npc_id.lower():
                        if tier >= 2:
                            return "The ancient stone warden has truly awakened within you. Asterra's bedrock bends to your command."
                        return "You carry the weight of ancient stone upon your shoulders, hero. May the mountain's fortitude never crush your spirit."
                    elif "dennis" in npc_id.lower() and tier >= 2:
                        return "Incredible granite forging across your shoulders! Come, let me discount your smithing repairs today."
                    return "By the gods, you walk like an animate fortress! Mind your heavy tread on our bridge."
                elif active_pact == "solar":
                    if "eldrin" in npc_id.lower():
                        if tier >= 2:
                            return "The radiant dawn shines through your eyes, Seraph! May your sunfire burn away Asterra's shadows."
                        return "The warmth of the morning star radiates from you, child of light. A blessing upon our village."
                    elif "silas" in npc_id.lower():
                        return "Ah, a Seraph of the Sun! Your radiant aura brings customers and fortune to my shop!"
                    return "Praise the morning sun, radiant wanderer! Safe travels under Asterra's light."

        # 3. Cataclysm Epoch Generational Crisis Dialogue (Pillar #4 Phase 3)
        if player and hasattr(player, "game") and player.game and hasattr(player.game, "epoch_manager"):
            em = player.game.epoch_manager
            if em and em.current_epoch != "standard":
                epoch = em.current_epoch
                clean_id = npc_id.lower().replace(" ", "").replace("npc_", "")
                if epoch == "deluge":
                    if "eldrin" in clean_id:
                        return "The great rains never ceased after your predecessor's journey into the Sunken Mire. We built these wooden raft bridges so our people may still travel."
                    elif "dennis" in clean_id:
                        return "The damp air rusts my iron faster than I can forge it. Mind your footing across those timber rafts, traveler."
                    elif "silas" in clean_id:
                        return "Caravans are delayed by high water, but my waterproof trade packs keep the finest goods dry!"
                elif epoch == "scorched":
                    if "eldrin" in clean_id:
                        return "Ash rains from the heavens... The fiery catastrophe of the past era has cracked our lands with molten fissures. Tread carefully."
                    elif "dennis" in clean_id:
                        return "The heat from the volcanic fissures keeps my forge blazingly hot, but our crops wither in the soot."
                    elif "silas" in clean_id:
                        return "Prices are soaring under the ash clouds, friend, but I still have rare supplies if you have gold."
                elif epoch == "glacial":
                    if "eldrin" in clean_id:
                        return "The frost came with the great blizzard and never departed. Even the deepest rivers are solid ice now."
                    elif "dennis" in clean_id:
                        return "My hammer clings to cold steel! Be sure you don't slip on the frozen river sheets."
                    elif "silas" in clean_id:
                        return "Brrr! Thermal cloaks are selling out fast in this eternal winter!"

        # 4. Spacetime Fracture Déjà-Vu Reactivity (Pillar #8 Phase 3)
        if player and hasattr(player, "game") and player.game and hasattr(player.game, "chrono_manager"):
            cm = player.game.chrono_manager
            if cm and cm.is_temporal_rift_active():
                deja_vu_text = self.get_deja_vu_dialogue(npc_id, player)
                if deja_vu_text:
                    return deja_vu_text

        mem = self.get_memory(npc_id)
        level = mem.friendship_level

        if level == REL_ENEMY:
            return "Get away from me, villain! I will not speak with you."
        elif level == REL_FRIEND:
            return "Ah, good to see you again my friend!"
        elif level == REL_CLOSE_FRIEND:
            return "Welcome back, my trusted ally! It is always an honor."
        elif level == REL_ACQUAINTANCE:
            return "Greetings traveler. Good to see you again."
        return ""  # Stranger = standard dialogue

    def get_dialogue_prefix(self, npc_id: str, player: Optional[Any] = None) -> str:
        """Alias for get_greeting_prefix."""
        return self.get_greeting_prefix(npc_id, player)

    def _on_npc_talked(self, npc_id: str = "", current_day: int = 1, **kwargs: Any) -> None:
        """Increments conversation counter and boosts relationship slightly once per day."""
        mem = self.get_memory(npc_id)
        mem.times_talked += 1
        if mem.last_interaction_day < current_day:
            mem.last_interaction_day = current_day
            self.modify_relationship(npc_id, 2)  # +2 per first talk each day

    def _on_npc_attacked(self, npc_id: str = "", witnesses: Optional[List[str]] = None, **kwargs: Any) -> None:
        """Severely reduces relationship when hero attacks NPCs or witnesses attack."""
        mem = self.get_memory(npc_id)
        mem.times_attacked += 1
        self.modify_relationship(npc_id, -30)
        
        # Witnesses also dislike hero
        if witnesses:
            for wit_id in witnesses:
                if wit_id != npc_id:
                    wit_mem = self.get_memory(wit_id)
                    wit_mem.crimes_witnessed.append(f"Attacked {npc_id}")
                    self.modify_relationship(wit_id, -15)

    def _on_quest_completed(self, quest_id: str = "", **kwargs: Any) -> None:
        """Completing NPC quests significantly improves relationship."""
        # Map quests to specific NPCs
        quest_npc_map = {
            "main_quest": "Eldrin",
            "forest_patrol": "Faye",
            "scholar_quest": "Mira",
            "blacksmith_quest": "Dennis",
            "lake_quest": "Kai"
        }
        target_npc = quest_npc_map.get(quest_id)
        if target_npc:
            mem = self.get_memory(target_npc)
            if quest_id not in mem.quests_completed_for:
                mem.quests_completed_for.append(quest_id)
                self.modify_relationship(target_npc, 25)

    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        """Propagates rumors between NPCs on day ticks."""
        # Check if any NPC witnessed crimes, propagate to others
        notable_crimes = []
        for mem in self.memories.values():
            if mem.crimes_witnessed:
                notable_crimes.extend(mem.crimes_witnessed)

        if notable_crimes:
            # Spread negative rumors slowly to other NPCs
            for mem in self.memories.values():
                if mem.relationship > -50 and len(mem.crimes_witnessed) == 0:
                    self.modify_relationship(mem.npc_id, -2)

    def _on_timeline_rewound(self, target_day: int = 1, days_rewound: int = 1, **kwargs: Any) -> None:
        """Broadcasts eerie deja-vu memories to Asterra's core inhabitants following a temporal rewind."""
        for npc_id in ["eldrin", "silas", "dennis", "faye", "mira", "kai"]:
            self.record_deja_vu_memory(npc_id, rewound_days=days_rewound, target_day=target_day)

    def record_deja_vu_memory(self, npc_id: str, rewound_days: int = 1, target_day: int = 1) -> None:
        """Records a temporal deja-vu psychic impression for an NPC."""
        mem = self.get_memory(npc_id)
        mem.deja_vu_count += 1
        mem.last_deja_vu_day = target_day

    def get_deja_vu_dialogue(self, npc_id: str, player: Optional[Any] = None) -> Optional[str]:
        """Returns eerie temporal déjà-vu dialogue when spoken to during or after a timeline rewind."""
        mem = self.get_memory(npc_id)
        if mem.deja_vu_count <= 0:
            return None
        clean_id = npc_id.lower().replace(" ", "").replace("npc_", "")
        if "eldrin" in clean_id:
            return "By the cosmos... I feel a profound shiver through the leylines. Hero, have we not spoken of this very fate three days hence? The sands of time feel disturbed."
        elif "silas" in clean_id:
            return "Strange... I had the most vivid dream that you bought all my iron stock yesterday, yet here it is on my shelf. Why does my purse feel lighter?"
        elif "dennis" in clean_id:
            return "Hold on... I swear on my forge hammer I already quenched this blade for you. Why is the anvil still cold? You bring strange winds with you, traveler."
        elif "faye" in clean_id:
            return "My arrows never miss, yet just now my quiver felt empty before I reached for it... A ghost of a hunt that hasn't happened yet."
        elif "mira" in clean_id:
            return "The leyline frequencies are overlapping in reverse. It's theoretically impossible unless... someone shattered a chrono-weave."
        return "A strange wave of dizziness just washed over me... as if this exact moment has already lived and died."

    def to_dict(self) -> Dict[str, Any]:
        """Serializes memories to dictionary for saves."""
        return {npc_id: mem.to_dict() for npc_id, mem in self.memories.items()}

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores memories from dictionary."""
        self.memories.clear()
        for npc_id, mem_data in data.items():
            self.memories[npc_id] = NPCMemory.from_dict(mem_data)

    def reset(self) -> None:
        """Resets all NPC memories to blank state."""
        self.memories.clear()
