"""
Echoes of Asterra - Centralized World Progression Engine
Manages regional unlock profiles, requirement evaluation, multi-stage region state machine
(UNKNOWN -> RUMOR_HEARD -> DISCOVERED -> LOCKED -> AVAILABLE -> UNLOCKED -> MASTERED),
alternative narrative unlock vectors, region identity metadata, and mastery tracking.
"""
import dataclasses
from enum import Enum
from typing import Dict, List, Set, Tuple, Any, Optional
from rpg.constants import (
    MAP_VILLAGE, MAP_FOREST, MAP_RUINS, MAP_CAVE, MAP_LAKE, MAP_MOUNTAIN, MAP_DUNGEON, MAP_CRYPT,
    FACTION_KNIGHTS, FACTION_HUNTERS, FACTION_BANDITS
)
from rpg.events import EventBus

class RegionState(str, Enum):
    UNKNOWN = "unknown"
    RUMOR_HEARD = "rumor_heard"
    DISCOVERED = "discovered"
    LOCKED = "locked"
    AVAILABLE = "available"
    UNLOCKED = "unlocked"
    MASTERED = "mastered"

class RequirementType(str, Enum):
    LEVEL = "level"
    QUEST = "quest"
    FACTION_REP = "faction_rep"
    NPC_RELATIONSHIP = "npc_relationship"
    VILLAGE_PROSPERITY = "village_prosperity"
    CONSTRUCTION_COMPLETE = "construction_complete"
    MEMORY = "memory"
    MYTHOS = "mythos"
    WORLD_EVENT = "world_event"
    BOSS_DEFEATED = "boss_defeated"
    ITEM_OWNED = "item_owned"
    ITEM_CRAFTED = "item_crafted"

class CompositeLogic(str, Enum):
    AND = "AND"
    OR = "OR"

@dataclasses.dataclass
class UnlockRequirement:
    """Individual narrative requirement condition."""
    category: RequirementType
    target_id: str
    target_value: Any
    narrative_clue: str

@dataclasses.dataclass
class RequirementGroup:
    """Group of requirements combined with AND or OR logic."""
    requirements: List[UnlockRequirement]
    logic: CompositeLogic = CompositeLogic.AND
    description: str = ""

@dataclasses.dataclass
class RegionIdentity:
    """Visual, audio, and gameplay identity parameters for a region."""
    enemies: List[str]
    resources: List[str]
    ambient_music: str
    lighting_tint: Tuple[int, int, int, int]
    weather_weights: Dict[str, float]
    regional_mechanic: str

@dataclasses.dataclass
class RegionMastery:
    """Mastery progress tracker for a region."""
    exploration_percent: float = 0.0
    landmarks_found: int = 0
    max_landmarks: int = 5
    elites_culled: int = 0
    max_elites: int = 3
    secrets_found: int = 0
    max_secrets: int = 2

    def update_percent(self) -> None:
        l_ratio = (self.landmarks_found / max(1, self.max_landmarks)) * 0.4
        e_ratio = (self.elites_culled / max(1, self.max_elites)) * 0.4
        s_ratio = (self.secrets_found / max(1, self.max_secrets)) * 0.2
        self.exploration_percent = min(100.0, (l_ratio + e_ratio + s_ratio) * 100.0)

    def is_mastered(self) -> bool:
        return self.landmarks_found >= self.max_landmarks and self.elites_culled >= self.max_elites and self.secrets_found >= self.max_secrets

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exploration_percent": self.exploration_percent,
            "landmarks_found": self.landmarks_found,
            "max_landmarks": self.max_landmarks,
            "elites_culled": self.elites_culled,
            "max_elites": self.max_elites,
            "secrets_found": self.secrets_found,
            "max_secrets": self.max_secrets
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RegionMastery':
        m = cls(
            exploration_percent=data.get("exploration_percent", 0.0),
            landmarks_found=data.get("landmarks_found", 0),
            max_landmarks=data.get("max_landmarks", 5),
            elites_culled=data.get("elites_culled", 0),
            max_elites=data.get("max_elites", 3),
            secrets_found=data.get("secrets_found", 0),
            max_secrets=data.get("max_secrets", 2)
        )
        m.update_percent()
        return m

@dataclasses.dataclass
class RegionProfile:
    """Data-driven region unlock profile."""
    region_id: str
    name: str
    state: RegionState
    prerequisites: List[str]
    rumor: str
    narrative_lore: str
    requirement_groups: List[RequirementGroup]
    identity: RegionIdentity
    mastery: RegionMastery
    is_soft_gated: bool = False
    soft_gate_warning: str = ""

    @property
    def id(self) -> str:
        """Alias property for region_id for backwards compatibility."""
        return self.region_id

class ProgressionManager:
    """
    Centralized World Progression Evaluator & State Engine.
    Consumes public APIs from subsystems to evaluate requirements without acting as a God Object.
    """
    def __init__(self) -> None:
        self.event_bus: Optional[EventBus] = None
        self.regions: Dict[str, RegionProfile] = self._build_default_region_profiles()

    def register_event_listeners(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        event_bus.subscribe("day_changed", self._on_day_changed)
        event_bus.subscribe("enemy_killed", self._on_enemy_killed)
        event_bus.subscribe("quest_completed", self._on_quest_completed)

    def _build_default_region_profiles(self) -> Dict[str, RegionProfile]:
        profiles = {}
        
        # 1. Village (Starting Zone)
        profiles[MAP_VILLAGE] = RegionProfile(
            region_id=MAP_VILLAGE,
            name="Asterra Haven Village",
            state=RegionState.UNLOCKED,
            prerequisites=[],
            rumor="The peaceful settlement of Asterra Haven.",
            narrative_lore="A resilient frontier village rebuilt by settlers after the Great Cataclysm.",
            requirement_groups=[],
            identity=RegionIdentity(
                enemies=["Training Dummy"],
                resources=["Timber", "Stone", "Wild Herbs"],
                ambient_music="village_theme",
                lighting_tint=(255, 255, 255, 255),
                weather_weights={"clear": 0.7, "rain": 0.3},
                regional_mechanic="Safe Sanctuary (No enemy spawns)"
            ),
            mastery=RegionMastery(max_landmarks=3, max_elites=0, max_secrets=2)
        )
        profiles[MAP_VILLAGE].mastery.landmarks_found = 3
        profiles[MAP_VILLAGE].mastery.update_percent()
        
        # 2. Forest
        profiles[MAP_FOREST] = RegionProfile(
            region_id=MAP_FOREST,
            name="Verdant Wilderness",
            state=RegionState.UNLOCKED,  # Unlocked early via tutorial / Elder
            prerequisites=[MAP_VILLAGE],
            rumor="The ancient woods surrounding Asterra Haven.",
            narrative_lore="Dense canopy hiding wild beasts, ancient stone altars, and lost hunter outposts.",
            requirement_groups=[
                RequirementGroup(
                    requirements=[
                        UnlockRequirement(RequirementType.LEVEL, "player", 1, "Speak with Elder Eldrin to receive wilderness clearance.")
                    ],
                    logic=CompositeLogic.AND,
                    description="Elder Eldrin's Wilderness Approval"
                )
            ],
            identity=RegionIdentity(
                enemies=["Slime", "Wild Wolf", "Goblin Scout"],
                resources=["Oak Wood", "Iron Ore", "Forest Berries"],
                ambient_music="forest_theme",
                lighting_tint=(230, 245, 220, 255),
                weather_weights={"clear": 0.5, "rain": 0.3, "fog": 0.2},
                regional_mechanic="Dense Foliage (Increased surprise ambush rate)"
            ),
            mastery=RegionMastery(max_landmarks=4, max_elites=2, max_secrets=2)
        )
        
        # 3. Lake (Asterra Lake) - Alternative unlock vectors (Dennis Bridge OR Hunter Pass)
        profiles[MAP_LAKE] = RegionProfile(
            region_id=MAP_LAKE,
            name="Lake of Echoes",
            state=RegionState.DISCOVERED,
            prerequisites=[MAP_FOREST],
            rumor="The northern stone bridge across Asterra Lake collapsed after the heavy spring flood.",
            narrative_lore="A shimmering alpine lake concealing sunken ruins and rare aquatic flora.",
            requirement_groups=[
                # Vector A: Dennis Bridge Repair & Village Prosperity
                RequirementGroup(
                    requirements=[
                        UnlockRequirement(RequirementType.CONSTRUCTION_COMPLETE, "bridge_rebuilt", True, "Blacksmith Dennis needs timber & stone workers to repair the northern bridge."),
                        UnlockRequirement(RequirementType.VILLAGE_PROSPERITY, "village", 35, "Village prosperity must reach 35+ to fund bridge logistics.")
                    ],
                    logic=CompositeLogic.AND,
                    description="Northern Bridge Reconstruction"
                ),
                # Vector B: Hunter Faction Rep & Mountain Trail
                RequirementGroup(
                    requirements=[
                        UnlockRequirement(RequirementType.FACTION_REP, FACTION_HUNTERS, 25, "Hunters trust you enough to reveal the secret alpine pass around the lake.")
                    ],
                    logic=CompositeLogic.AND,
                    description="Hunter Faction Secret Trail"
                )
            ],
            identity=RegionIdentity(
                enemies=["Lake Siren", "Marsh Crawler", "Deep Slime"],
                resources=["Azure Lotus", "Silver Ore", "Pure Water"],
                ambient_music="lake_theme",
                lighting_tint=(210, 235, 255, 255),
                weather_weights={"clear": 0.4, "rain": 0.3, "fog": 0.3},
                regional_mechanic="Misty Mirror (Dense fog reduces field of view)"
            ),
            mastery=RegionMastery(max_landmarks=5, max_elites=3, max_secrets=3),
            is_soft_gated=True,
            soft_gate_warning="The swift river currents and collapsed bridge prevent safe passage across the waters."
        )

        # 4. Cave (Cave Depths)
        profiles[MAP_CAVE] = RegionProfile(
            region_id=MAP_CAVE,
            name="Crystal Depths Cavern",
            state=RegionState.RUMOR_HEARD,
            prerequisites=[MAP_FOREST],
            rumor="Boulders seal the entrance to Crystal Cavern until watchtowers clear the wild path.",
            narrative_lore="Subterranean caverns glowing with luminescent minerals and ancient elemental crystals.",
            requirement_groups=[
                RequirementGroup(
                    requirements=[
                        UnlockRequirement(RequirementType.BOSS_DEFEATED, "forest_guardian", True, "Defeat the Forest Guardian corrupted by dark magic."),
                        UnlockRequirement(RequirementType.CONSTRUCTION_COMPLETE, "watchtower_built", True, "Build the Watchtower to secure the cavern road.")
                    ],
                    logic=CompositeLogic.AND,
                    description="Cavern Security & Guardian Defeat"
                )
            ],
            identity=RegionIdentity(
                enemies=["Cave Bat", "Crystal Golem", "Deep Crawler"],
                resources=["Luminescent Crystal", "Mithril Shard", "Cave Fungus"],
                ambient_music="cave_theme",
                lighting_tint=(180, 200, 240, 255),
                weather_weights={"clear": 1.0},
                regional_mechanic="Subterranean Darkness (Requires torches or luminescent potions)"
            ),
            mastery=RegionMastery(max_landmarks=5, max_elites=3, max_secrets=3),
            is_soft_gated=True,
            soft_gate_warning="Heavy rockfalls block the narrow gorge path leading into the cavern."
        )

        # 5. Ruins (Ruins Plaza) - Alternative unlock vectors
        profiles[MAP_RUINS] = RegionProfile(
            region_id=MAP_RUINS,
            name="Sunken Ruins Plaza",
            state=RegionState.UNKNOWN,
            prerequisites=[MAP_FOREST, MAP_LAKE],
            rumor="Dangerous bandit outposts occupy the overgrown plaza of the ancient city ruins.",
            narrative_lore="Remnants of Asterra's fallen capital, guarded by rogue warlords and ancient constructs.",
            requirement_groups=[
                RequirementGroup(
                    requirements=[
                        UnlockRequirement(RequirementType.BOSS_DEFEATED, "bandit_leader", True, "Defeat the Bandit Warlord holding the plaza checkpoints."),
                        UnlockRequirement(RequirementType.FACTION_REP, FACTION_KNIGHTS, 20, "Earn 20+ reputation with the Knights of Asterra.")
                    ],
                    logic=CompositeLogic.AND,
                    description="Knight Escort Expedition"
                ),
                RequirementGroup(
                    requirements=[
                        UnlockRequirement(RequirementType.BOSS_DEFEATED, "bandit_leader", True, "Defeat the Bandit Warlord holding the plaza checkpoints."),
                        UnlockRequirement(RequirementType.FACTION_REP, FACTION_HUNTERS, 20, "Earn 20+ reputation with the Hunters Guild.")
                    ],
                    logic=CompositeLogic.AND,
                    description="Hunter Scout Infiltration"
                )
            ],
            identity=RegionIdentity(
                enemies=["Bandit Marauder", "Skeleton Archer", "Ruins Sentinel"],
                resources=["Ancient Relic", "Relic Fragment", "Runed Stone"],
                ambient_music="ruins_theme",
                lighting_tint=(240, 230, 200, 255),
                weather_weights={"clear": 0.6, "rain": 0.2, "fog": 0.2},
                regional_mechanic="Ruins Trap Defenses (Watch out for hidden arrow traps)"
            ),
            mastery=RegionMastery(max_landmarks=6, max_elites=4, max_secrets=4),
            is_soft_gated=True,
            soft_gate_warning="Bandit sentries shoot warning volleys at any unescorted traveler."
        )

        # 6. Crypt (Endless Crypt & Vault)
        profiles[MAP_CRYPT] = RegionProfile(
            region_id=MAP_CRYPT,
            name="Forbidden Catacombs",
            state=RegionState.UNKNOWN,
            prerequisites=[MAP_RUINS],
            rumor="An ancient void seal bars the deepest catacombs beneath the ruins.",
            narrative_lore="The endless crypt housing Asterra's forgotten heroes, relic vaults, and void corruption.",
            requirement_groups=[
                RequirementGroup(
                    requirements=[
                        UnlockRequirement(RequirementType.ITEM_OWNED, "Ancient Relic", 1, "Recover the Ancient Relic from the Ruins Plaza."),
                        UnlockRequirement(RequirementType.QUEST, "ruins_expedition", "completed", "Complete the Ruins Reconnaissance Expedition.")
                    ],
                    logic=CompositeLogic.AND,
                    description="Void Seal Shattering"
                )
            ],
            identity=RegionIdentity(
                enemies=["Crypt Wight", "Shadow Mage", "Void Behemoth", "Shadow Overlord"],
                resources=["Void Essence", "Starlight Gem", "Corrupted Bone"],
                ambient_music="crypt_theme",
                lighting_tint=(160, 140, 200, 255),
                weather_weights={"clear": 1.0},
                regional_mechanic="Void Corruption (Gradual stamina decay in deep chambers)"
            ),
            mastery=RegionMastery(max_landmarks=8, max_elites=5, max_secrets=5),
            is_soft_gated=True,
            soft_gate_warning="An unearthly void barrier repels all mortal flesh."
        )
        
        return profiles

    def discover_region(self, region_id: str, source: str = "rumor", event_bus: Optional[EventBus] = None) -> bool:
        """Transitions region from UNKNOWN to RUMOR_HEARD or DISCOVERED."""
        if region_id not in self.regions:
            return False
        profile = self.regions[region_id]
        if profile.state == RegionState.UNKNOWN:
            profile.state = RegionState.RUMOR_HEARD if source == "rumor" else RegionState.DISCOVERED
            bus = event_bus or self.event_bus
            if bus:
                bus.emit("region_discovered", region_id=region_id, name=profile.name, source=source)
            return True
        elif profile.state == RegionState.RUMOR_HEARD and source != "rumor":
            profile.state = RegionState.DISCOVERED
            bus = event_bus or self.event_bus
            if bus:
                bus.emit("region_discovered", region_id=region_id, name=profile.name, source=source)
            return True
        return False

    def evaluate_requirement(self, req: UnlockRequirement, game_context: Any) -> bool:
        """Evaluates single requirement condition against public subsystem APIs."""
        if not game_context:
            return False
            
        cat = req.category
        if cat == RequirementType.LEVEL:
            player = getattr(game_context, "player", None)
            return getattr(player, "level", 1) >= int(req.target_value) if player else False
            
        elif cat == RequirementType.QUEST:
            q_mgr = getattr(game_context, "quest_manager", None)
            if q_mgr and hasattr(q_mgr, "quests"):
                for q in q_mgr.quests:
                    if q.id == req.target_id:
                        return q.status == req.target_value
            return False
            
        elif cat == RequirementType.FACTION_REP:
            # Query FactionManager (game.factions) - the Single Source of Truth for faction standings
            fac_mgr = getattr(game_context, "factions", None)
            if fac_mgr and hasattr(fac_mgr, "get_reputation"):
                val = fac_mgr.get_reputation(req.target_id)
                return val >= float(req.target_value)
            return False
            
        elif cat == RequirementType.VILLAGE_PROSPERITY:
            ws = getattr(game_context, "world_state", None)
            return getattr(ws, "prosperity", 0) >= int(req.target_value) if ws else False
            
        elif cat == RequirementType.CONSTRUCTION_COMPLETE:
            lw = getattr(game_context, "living_world", None)
            settlement = getattr(lw, "settlement", None) if lw else getattr(game_context, "settlement", None)
            if settlement and hasattr(settlement, "upgrades") and settlement.upgrades.get(req.target_id, False):
                return True
            ws = getattr(game_context, "world_state", None)
            if ws and hasattr(ws, "completed_event_ids"):
                return req.target_id in ws.completed_event_ids
            return False
            
        elif cat == RequirementType.BOSS_DEFEATED:
            # Check world_state.completed_event_ids for boss defeat flags (e.g. "forest_guardian" or "boss_forest_guardian")
            ws = getattr(game_context, "world_state", None)
            if ws and hasattr(ws, "completed_event_ids"):
                boss_key = req.target_id if req.target_id.startswith("boss_") else f"boss_{req.target_id}"
                return req.target_id in ws.completed_event_ids or boss_key in ws.completed_event_ids
            # Fallback: check legacy world_manager.boss_defeated for Shadow Overlord
            wm = getattr(game_context, "world_manager", None)
            if wm and req.target_id == "shadow_overlord":
                return getattr(wm, "boss_defeated", False)
            return False
            
        elif cat == RequirementType.ITEM_OWNED:
            player = getattr(game_context, "player", None)
            if player and hasattr(player, "inventory"):
                count = 0
                for slot in player.inventory.slots:
                    if slot and slot.name == req.target_id:
                        count += slot.quantity
                return count >= int(req.target_value)
            return False
            
        return False

    def can_access_region(self, region_id: str, game_context: Any = None) -> Tuple[bool, str, RegionState]:
        """
        Evaluates if player can enter target region.
        Returns (can_access, narrative_clue, region_state).
        """
        if region_id not in self.regions:
            return True, "", RegionState.UNLOCKED
            
        profile = self.regions[region_id]
        
        # Already unlocked or mastered
        if profile.state in [RegionState.UNLOCKED, RegionState.MASTERED]:
            return True, "", profile.state
            
        # Check prerequisites
        for pre in profile.prerequisites:
            pre_prof = self.regions.get(pre)
            if pre_prof and pre_prof.state not in [RegionState.UNLOCKED, RegionState.MASTERED]:
                return False, f"Prerequisite region {pre_prof.name} must be explored first.", profile.state

        # If AVAILABLE state, allow transition and trigger physical unlock celebration
        if profile.state == RegionState.AVAILABLE:
            return True, "", profile.state

        # Evaluate requirement groups (Any satisfied group grants access!)
        if not profile.requirement_groups:
            return True, "", profile.state
            
        unmet_clues = []
        for group in profile.requirement_groups:
            group_satisfied = True
            for req in group.requirements:
                if not self.evaluate_requirement(req, game_context):
                    group_satisfied = False
                    unmet_clues.append(req.narrative_clue)
                    
            if group_satisfied:
                # Region requirements met! Promote to AVAILABLE
                profile.state = RegionState.AVAILABLE
                return True, "", profile.state

        # Blocked: return narrative clue
        primary_clue = unmet_clues[0] if unmet_clues else profile.rumor
        return False, primary_clue, profile.state

    def unlock_region(self, region_id: str, game_context: Any = None, event_bus: Optional[EventBus] = None) -> bool:
        """Performs full region unlock, triggering visual world changes and living celebrations."""
        if region_id not in self.regions:
            return False
            
        profile = self.regions[region_id]
        if profile.state in [RegionState.UNLOCKED, RegionState.MASTERED]:
            return False
            
        profile.state = RegionState.UNLOCKED
        bus = event_bus or self.event_bus
        
        if bus:
            bus.emit(
                "region_unlocked",
                region_id=region_id,
                name=profile.name,
                lore=profile.narrative_lore,
                identity=dataclasses.asdict(profile.identity)
            )
            bus.emit("world_event_started", event_id=f"unlock_{region_id}")

        # Record milestone memory if MemoryManager available
        if game_context:
            mem_mgr = getattr(game_context, "memory_manager", None)
            if mem_mgr and hasattr(mem_mgr, "add_memory"):
                mem_mgr.add_memory(
                    event_type="region_unlocked",
                    description=f"Unlocked access to {profile.name}.",
                    importance=8,
                    associated_npc="System"
                )

        return True

    def update_mastery(self, region_id: str, category: str, amount: int = 1, event_bus: Optional[EventBus] = None) -> None:
        """Updates region mastery metrics (landmarks, elites, secrets)."""
        if region_id not in self.regions:
            return
        profile = self.regions[region_id]
        mastery = profile.mastery
        
        if category == "landmark":
            mastery.landmarks_found = min(mastery.max_landmarks, mastery.landmarks_found + amount)
        elif category == "elite":
            mastery.elites_culled = min(mastery.max_elites, mastery.elites_culled + amount)
        elif category == "secret":
            mastery.secrets_found = min(mastery.max_secrets, mastery.secrets_found + amount)

        mastery.update_percent()

        if mastery.is_mastered() and profile.state != RegionState.MASTERED:
            profile.state = RegionState.MASTERED
            bus = event_bus or self.event_bus
            if bus:
                bus.emit("region_mastered", region_id=region_id, name=profile.name)

    def _on_day_changed(self, day: int, **kwargs: Any) -> None:
        """Daily tick evaluation."""
        pass

    def _on_enemy_killed(self, enemy_name: str = "", map_name: str = "", is_elite: bool = False, **kwargs: Any) -> None:
        if is_elite and map_name in self.regions:
            self.update_mastery(map_name, "elite", 1)

    def _on_quest_completed(self, quest_id: str = "", **kwargs: Any) -> None:
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Serializes progression state."""
        return {
            "regions": {
                r_id: {
                    "state": prof.state.value,
                    "mastery": prof.mastery.to_dict()
                } for r_id, prof in self.regions.items()
            }
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes progression state."""
        if not data:
            return
        reg_data = data.get("regions", {})
        for r_id, r_info in reg_data.items():
            if r_id in self.regions:
                prof = self.regions[r_id]
                st_str = r_info.get("state", RegionState.UNKNOWN.value)
                try:
                    prof.state = RegionState(st_str)
                except ValueError:
                    prof.state = RegionState.UNKNOWN
                if "mastery" in r_info:
                    prof.mastery = RegionMastery.from_dict(r_info["mastery"])
