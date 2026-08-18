"""
Echoes of Asterra - Nemesis System
Simulates persistent bandit and cultist captains who remember encounters with the player,
level up upon victory, develop distinctive tactical traits, earn victory titles,
claim world territories (reducing road safety and stability), and seed rumors throughout Asterra.
"""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from rpg.events import EventBus

# Nemesis Tactical Traits
TRAIT_BLOODTHIRSTY = "Bloodthirsty"   # Enters berserk earlier (>50% HP), deals increased attack damage
TRAIT_CRAVEN = "Craven"               # Retreats with speed boost when HP < 30%
TRAIT_CUNNING = "Cunning"             # Shorter attack telegraph, evasive movement
TRAIT_IRONHIDE = "Ironhide"           # +50% poise, reduced stagger duration, +25% defense
TRAIT_SLAYER = "Hero Slayer"          # +30% bonus damage specifically against the player
TRAIT_AMBUSH = "Ambush Master"        # High initial movement speed and surprise burst damage

ALL_TRAITS = [
    TRAIT_BLOODTHIRSTY,
    TRAIT_CRAVEN,
    TRAIT_CUNNING,
    TRAIT_IRONHIDE,
    TRAIT_SLAYER,
    TRAIT_AMBUSH
]

FIRST_NAMES = [
    "Grask", "Vorgash", "Malakor", "Kraghar", "Zarok",
    "Brog", "Thraxis", "Drakar", "Ghaz", "Morzog",
    "Skalg", "Azgar", "Valok", "Gorath", "Rendak"
]

EPITHETS = [
    "the Scorcher", "Skullsplitter", "Shadowblade", "Bloodfang", "the Deceiver",
    "the Cruel", "the Swift", "Bonebreaker", "the Vile", "the Unbroken",
    "Ironjaw", "the Red", "the Butcher", "Voidtouched", "Grimfang"
]

VICTORY_TITLES = [
    "Hero Slayer",
    "Doom of Champions",
    "Scourge of Knights",
    "Bane of Asterra",
    "The Dread Warlord",
    "The Undefeated",
    "Harvester of Souls"
]

UNIQUE_LOOT_NAMES = [
    "Captain's Blood Cleaver",
    "Warlord's Iron Crest",
    "Bandit King's Shadow Ring",
    "Dread Trophy of the Nemesis",
    "Voidtouched Battle Signet",
    "Skullsplitter's War Axe",
    "Cruel Captain's Cloak"
]

TERRITORIES = ["forest", "cave", "ruins", "lake"]


@dataclass
class NemesisCaptain:
    """Represents an individual persistent Nemesis enemy with memory, progression, and traits."""
    captain_id: str
    name: str
    archetype: str = "bandit"
    asset_key: str = "knight"
    level: int = 3
    max_hp: int = 140
    hp: int = 140
    atk: int = 24
    defense: int = 5
    speed: float = 2.4
    traits: List[str] = field(default_factory=list)
    victory_titles: List[str] = field(default_factory=list)
    kills_on_player: int = 0
    escapes: int = 0
    claimed_territory: str = "forest"
    active: bool = True
    is_defeated: bool = False
    unique_loot_name: str = "Captain's Blood Cleaver"

    def level_up(self, levels: int = 1) -> None:
        """Increases captain power, health, attack, and stats."""
        self.level += levels
        self.max_hp += 35 * levels
        self.hp = self.max_hp
        self.atk += 6 * levels
        self.defense += 2 * levels
        self.speed = min(3.8, self.speed + 0.1 * levels)

        # Gain a new trait if under trait cap (max 3 traits)
        available_traits = [t for t in ALL_TRAITS if t not in self.traits]
        if available_traits and len(self.traits) < 3:
            new_trait = random.choice(available_traits)
            self.traits.append(new_trait)

    def add_victory(self, title: Optional[str] = None) -> str:
        """Records a kill against the player, levels up, and grants a victory title."""
        self.kills_on_player += 1
        self.level_up(1)

        if not title:
            avail_titles = [t for t in VICTORY_TITLES if t not in self.victory_titles]
            title = random.choice(avail_titles) if avail_titles else f"Slayer Mark {self.kills_on_player}"

        if title not in self.victory_titles:
            self.victory_titles.append(title)
        return title

    def record_escape(self) -> None:
        """Records a successful retreat/escape and grants a minor level boost."""
        self.escapes += 1
        self.level_up(1)
        if TRAIT_CRAVEN not in self.traits and len(self.traits) < 3:
            self.traits.append(TRAIT_CRAVEN)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes captain state."""
        return {
            "captain_id": self.captain_id,
            "name": self.name,
            "archetype": self.archetype,
            "asset_key": self.asset_key,
            "level": self.level,
            "max_hp": self.max_hp,
            "hp": self.hp,
            "atk": self.atk,
            "defense": self.defense,
            "speed": self.speed,
            "traits": list(self.traits),
            "victory_titles": list(self.victory_titles),
            "kills_on_player": self.kills_on_player,
            "escapes": self.escapes,
            "claimed_territory": self.claimed_territory,
            "active": self.active,
            "is_defeated": self.is_defeated,
            "unique_loot_name": self.unique_loot_name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NemesisCaptain":
        """Deserializes captain state."""
        return cls(
            captain_id=data.get("captain_id", "nemesis_0"),
            name=data.get("name", "Unknown Captain"),
            archetype=data.get("archetype", "bandit"),
            asset_key=data.get("asset_key", "knight"),
            level=data.get("level", 3),
            max_hp=data.get("max_hp", 140),
            hp=data.get("hp", 140),
            atk=data.get("atk", 24),
            defense=data.get("defense", 5),
            speed=data.get("speed", 2.4),
            traits=data.get("traits", []),
            victory_titles=data.get("victory_titles", []),
            kills_on_player=data.get("kills_on_player", 0),
            escapes=data.get("escapes", 0),
            claimed_territory=data.get("claimed_territory", "forest"),
            active=data.get("active", True),
            is_defeated=data.get("is_defeated", False),
            unique_loot_name=data.get("unique_loot_name", "Captain's Blood Cleaver")
        )


class NemesisManager:
    """
    Orchestrates generation, progression, territory claiming,
    and event integration for persistent Nemesis captains.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.game_reference: Any = None
        self.captains: Dict[str, NemesisCaptain] = {}
        self._next_id: int = 1

        if self.event_bus:
            self.register_event_listeners(self.event_bus)

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Registers EventBus topic listeners."""
        self.event_bus = event_bus
        event_bus.subscribe("player_killed_by_enemy", self._on_player_killed_by_enemy)
        event_bus.subscribe("enemy_escaped", self._on_enemy_escaped)
        event_bus.subscribe("nemesis_killed", self._on_nemesis_killed)
        event_bus.subscribe("day_changed", self._on_day_changed)

    def generate_name(self) -> str:
        """Generates a distinctive Nemesis name."""
        first = random.choice(FIRST_NAMES)
        epithet = random.choice(EPITHETS)
        return f"{first} {epithet}"

    def create_nemesis(
        self,
        name: Optional[str] = None,
        archetype: str = "bandit",
        asset_key: str = "knight",
        level: int = 3,
        map_name: str = "forest",
        starting_traits: Optional[List[str]] = None
    ) -> NemesisCaptain:
        """Creates and registers a new Nemesis Captain."""
        cap_id = f"nemesis_{self._next_id}"
        self._next_id += 1

        final_name = name if name else self.generate_name()
        traits = starting_traits if starting_traits is not None else [random.choice(ALL_TRAITS)]
        loot_name = random.choice(UNIQUE_LOOT_NAMES)

        captain = NemesisCaptain(
            captain_id=cap_id,
            name=final_name,
            archetype=archetype,
            asset_key=asset_key,
            level=level,
            max_hp=120 + level * 25,
            hp=120 + level * 25,
            atk=20 + level * 5,
            defense=4 + level * 2,
            speed=2.2 + min(0.8, level * 0.05),
            traits=traits,
            victory_titles=[],
            kills_on_player=0,
            escapes=0,
            claimed_territory=map_name if map_name in TERRITORIES else "forest",
            active=True,
            is_defeated=False,
            unique_loot_name=loot_name
        )

        self.captains[cap_id] = captain

        if self.event_bus:
            self.event_bus.emit(
                "nemesis_created",
                captain_id=cap_id,
                name=final_name,
                level=level,
                territory=captain.claimed_territory
            )

        return captain

    def _on_player_killed_by_enemy(
        self,
        enemy: Any = None,
        enemy_name: str = "Enemy",
        enemy_key: str = "bandit",
        map_name: str = "forest",
        **kwargs: Any
    ) -> None:
        """
        Triggered when player is slain in combat by an enemy.
        If killer was already a Nemesis Captain, promotes/buffs them.
        Otherwise promotes standard enemy to a new Nemesis Captain.
        """
        captain: Optional[NemesisCaptain] = None

        # Check if killer was an existing Nemesis
        nemesis_id = getattr(enemy, "nemesis_id", None)
        if nemesis_id and nemesis_id in self.captains:
            captain = self.captains[nemesis_id]
        else:
            # Check if there is an active Nemesis for this map and name
            for cap in self.captains.values():
                if cap.active and not cap.is_defeated and cap.name == enemy_name:
                    captain = cap
                    break

        if captain:
            # Level up existing Nemesis and grant title
            title = captain.add_victory()
        else:
            # Promote enemy to brand new Nemesis Captain
            enemy_lvl = getattr(enemy, "level", 3)
            asset_k = getattr(enemy, "asset_key", "knight")
            captain = self.create_nemesis(
                archetype=enemy_key,
                asset_key=asset_k,
                level=max(3, enemy_lvl + 1),
                map_name=map_name
            )
            title = captain.add_victory("Hero Slayer")

        # 1. Seed rumor in RumorBoard
        self._seed_nemesis_victory_rumor(captain, map_name, title)

        # 2. Reduce road safety / territory stability in Faction Warfare
        self._apply_territory_threat(captain)

        if self.event_bus:
            self.event_bus.emit(
                "nemesis_promoted",
                captain_id=captain.captain_id,
                name=captain.name,
                level=captain.level,
                title=title,
                kills=captain.kills_on_player
            )

    def _on_enemy_escaped(
        self,
        enemy: Any = None,
        enemy_name: str = "Enemy",
        enemy_key: str = "bandit",
        map_name: str = "forest",
        **kwargs: Any
    ) -> None:
        """
        Triggered when a high-tier enemy retreats with low HP and escapes.
        Promotes them to a Nemesis Captain or records escape.
        """
        nemesis_id = getattr(enemy, "nemesis_id", None)
        if nemesis_id and nemesis_id in self.captains:
            captain = self.captains[nemesis_id]
            captain.record_escape()
        else:
            enemy_lvl = getattr(enemy, "level", 2)
            asset_k = getattr(enemy, "asset_key", "knight")
            captain = self.create_nemesis(
                archetype=enemy_key,
                asset_key=asset_k,
                level=max(2, enemy_lvl),
                map_name=map_name,
                starting_traits=[TRAIT_CRAVEN]
            )
            captain.escapes = 1

    def _on_nemesis_killed(
        self,
        captain_id: str = "",
        captain_name: str = "",
        killer: Any = None,
        **kwargs: Any
    ) -> None:
        """Handles death of a Nemesis Captain."""
        captain = self.captains.get(captain_id)
        if not captain:
            for cap in self.captains.values():
                if cap.name == captain_name:
                    captain = cap
                    break

        if captain:
            captain.is_defeated = True
            captain.active = False

            # 1. Restore territory safety
            self._restore_territory_safety(captain)

            # 2. Record Bestiary and Mythos entries
            self._record_nemesis_defeat(captain)

            # 3. Seed defeat rumor
            self._seed_nemesis_defeat_rumor(captain)

    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        """On daily ticks, active Nemesis Captains have a chance to relocate or fortify territory."""
        for captain in self.captains.values():
            if captain.active and not captain.is_defeated:
                # 20% chance to roam to an adjacent territory
                if random.random() < 0.20:
                    old_t = captain.claimed_territory
                    avail = [t for t in TERRITORIES if t != old_t]
                    captain.claimed_territory = random.choice(avail)
                    if self.event_bus:
                        self.event_bus.emit(
                            "nemesis_relocated",
                            captain_id=captain.captain_id,
                            name=captain.name,
                            old_territory=old_t,
                            new_territory=captain.claimed_territory
                        )

    def _seed_nemesis_victory_rumor(self, captain: NemesisCaptain, map_name: str, title: str) -> None:
        """Seeds a dynamic rumor on RumorBoard about the Nemesis Captain's triumph."""
        if not self.game_reference:
            return
        lw = getattr(self.game_reference, "living_world", None)
        rumors = getattr(lw, "rumors", None) if lw else getattr(self.game_reference, "rumor_board", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            loc_label = map_name.replace("_", " ").title()
            r_id = f"rumor_nemesis_kill_{captain.captain_id}_{captain.kills_on_player}"
            topic = f"The Menace of {captain.name.split()[0]}"
            true_txt = f"{captain.name} ({title}) struck down an adventurer in the {loc_label}!"
            dist_txt = f"They say {captain.name} has slain dozens of seasoned knights and claims the {loc_label} as his bloody domain!"
            rumors.add_custom_rumor(
                rumor_id=r_id,
                topic=topic,
                origin_npc="faye" if map_name == "forest" else "eldrin",
                true_content=true_txt,
                distorted_content=dist_txt
            )

    def _seed_nemesis_defeat_rumor(self, captain: NemesisCaptain) -> None:
        """Seeds a celebration rumor when a Nemesis Captain is defeated."""
        if not self.game_reference:
            return
        lw = getattr(self.game_reference, "living_world", None)
        rumors = getattr(lw, "rumors", None) if lw else getattr(self.game_reference, "rumor_board", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            r_id = f"rumor_nemesis_defeated_{captain.captain_id}"
            topic = f"Fall of {captain.name.split()[0]}"
            true_txt = f"The dreaded {captain.name} was finally slain in combat by the Hero!"
            dist_txt = f"Word travels that {captain.name} was cleaved in two by a single strike from the legendary Hero!"
            rumors.add_custom_rumor(
                rumor_id=r_id,
                topic=topic,
                origin_npc="dennis",
                true_content=true_txt,
                distorted_content=dist_txt
            )

    def _apply_territory_threat(self, captain: NemesisCaptain) -> None:
        """Decreases road safety and stability in the captain's claimed territory."""
        if not self.game_reference:
            return
        # Faction War stability
        lw = getattr(self.game_reference, "living_world", None)
        if lw:
            fw = getattr(lw, "faction_war", None)
            if fw and hasattr(fw, "control_points"):
                for cp in fw.control_points.values():
                    if cp.map_name == captain.claimed_territory:
                        cp.stability = max(0.0, cp.stability - 15.0)
                        cp.contested = True
            ws = getattr(lw, "world_state", None)
            if ws and hasattr(ws, "road_safety"):
                ws.road_safety = max(0.0, ws.road_safety - 10.0)

    def _restore_territory_safety(self, captain: NemesisCaptain) -> None:
        """Restores territory stability and road safety upon captain's defeat."""
        if not self.game_reference:
            return
        lw = getattr(self.game_reference, "living_world", None)
        if lw:
            fw = getattr(lw, "faction_war", None)
            if fw and hasattr(fw, "control_points"):
                for cp in fw.control_points.values():
                    if cp.map_name == captain.claimed_territory:
                        cp.stability = min(100.0, cp.stability + 20.0)
            ws = getattr(lw, "world_state", None)
            if ws and hasattr(ws, "road_safety"):
                ws.road_safety = min(100.0, ws.road_safety + 15.0)

    def _record_nemesis_defeat(self, captain: NemesisCaptain) -> None:
        """Records defeat in Bestiary and Mythos subsystems."""
        if not self.game_reference:
            return
        # 1. Bestiary Record
        bm = getattr(self.game_reference, "bestiary_manager", None)
        if bm and hasattr(bm, "record_nemesis_defeat"):
            bm.record_nemesis_defeat(captain.name, captain.traits, captain.level)

        # 2. Mythos Legacy Record
        mm = getattr(self.game_reference, "mythos_manager", None)
        if mm and hasattr(mm, "record_event"):
            from rpg.mythos import CATEGORY_COMBAT
            current_day = 1
            if hasattr(self.game_reference, "world_state"):
                current_day = getattr(self.game_reference.world_state, "day", 1)
            mm.record_event({
                "event_type": "nemesis_defeated",
                "category": CATEGORY_COMBAT,
                "day": current_day,
                "actor": "Hero",
                "target": captain.name,
                "location": captain.claimed_territory,
                "outcome": f"Slain at Lv.{captain.level} (Kills on Player: {captain.kills_on_player})"
            })

    def get_active_captains(self) -> List[NemesisCaptain]:
        """Returns list of currently living, active Nemesis Captains."""
        return [c for c in self.captains.values() if c.active and not c.is_defeated]

    def get_captain_for_map(self, map_name: str) -> Optional[NemesisCaptain]:
        """Returns the active Nemesis Captain claiming a specific map, if any."""
        for c in self.captains.values():
            if c.active and not c.is_defeated and c.claimed_territory == map_name:
                return c
        return None

    def reset(self) -> None:
        """Resets all Nemesis data for a fresh game session."""
        self.captains.clear()
        self._next_id = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serializes manager state."""
        return {
            "next_id": self._next_id,
            "captains": {k: v.to_dict() for k, v in self.captains.items()}
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes manager state."""
        if not data:
            return
        self._next_id = data.get("next_id", 1)
        raw_captains = data.get("captains", {})
        self.captains.clear()
        for k, v in raw_captains.items():
            self.captains[k] = NemesisCaptain.from_dict(v)
