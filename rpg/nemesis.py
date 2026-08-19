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
class VendettaSiege:
    """Represents an active or historic Vendetta Siege event led by a Nemesis Captain."""
    siege_id: str
    captain_id: str
    captain_name: str
    target_territory: str
    duration_days: int = 3
    days_remaining: int = 3
    is_active: bool = True
    minions_count: int = 3
    is_resolved: bool = False
    outcome: Optional[str] = None  # "victory", "defeat", or None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "siege_id": self.siege_id,
            "captain_id": self.captain_id,
            "captain_name": self.captain_name,
            "target_territory": self.target_territory,
            "duration_days": self.duration_days,
            "days_remaining": self.days_remaining,
            "is_active": self.is_active,
            "minions_count": self.minions_count,
            "is_resolved": self.is_resolved,
            "outcome": self.outcome
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VendettaSiege":
        return cls(
            siege_id=data.get("siege_id", "siege_default"),
            captain_id=data.get("captain_id", ""),
            captain_name=data.get("captain_name", ""),
            target_territory=data.get("target_territory", "forest"),
            duration_days=data.get("duration_days", 3),
            days_remaining=data.get("days_remaining", 3),
            is_active=data.get("is_active", True),
            minions_count=data.get("minions_count", 3),
            is_resolved=data.get("is_resolved", False),
            outcome=data.get("outcome", None)
        )


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
        """Increases captain power, health, attack, and stats up to max Lv.10 and 3 traits."""
        if self.level >= 10:
            return
        actual_gain = min(levels, 10 - self.level)
        self.level += actual_gain
        self.max_hp += 35 * actual_gain
        self.hp = self.max_hp
        self.atk += 6 * actual_gain
        self.defense += 2 * actual_gain
        self.speed = min(3.8, self.speed + 0.1 * actual_gain)

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
        
        # Vendetta Siege state
        self.active_siege: Optional[VendettaSiege] = None
        self.siege_history: List[VendettaSiege] = []
        self.last_siege_resolved_day: int = -999
        self.siege_cooldown_days: int = 5
        self.siege_counter: int = 1

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
        active_siege_id: Optional[str] = None,
        killer: Any = None,
        **kwargs: Any
    ) -> None:
        """Handles death of a Nemesis Captain and checks active siege resolution."""
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

            # 4. Check if this kill resolves the active Vendetta Siege
            if self.active_siege and self.active_siege.is_active:
                if active_siege_id == self.active_siege.siege_id or (active_siege_id is None and self.active_siege.captain_id == captain.captain_id):
                    current_day = 1
                    if self.game_reference and hasattr(self.game_reference, "world_state"):
                        current_day = getattr(self.game_reference.world_state, "day", 1)
                    self.resolve_vendetta_siege(
                        siege_id=self.active_siege.siege_id,
                        outcome="victory",
                        player=killer,
                        current_day=current_day
                    )

    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        """On daily ticks, updates siege timers, triggers new sieges, and updates territory roaming."""
        # 1. Update active siege countdown and timeout resolution
        self.update_siege_day_tick(day)

        # 2. Check conditions for high-tier Nemesis captains to launch a new Vendetta Siege
        self.check_vendetta_siege_triggers(day)

        # 3. 20% chance for undefeated captains to roam territories
        for captain in self.captains.values():
            if captain.active and not captain.is_defeated:
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

    # -------------------------------------------------------------
    # Vendetta Siege Methods
    # -------------------------------------------------------------
    def check_vendetta_siege_triggers(self, current_day: int, force_trigger: bool = False) -> Optional[VendettaSiege]:
        """
        Evaluates conditions for a high-tier Nemesis Captain to launch a Vendetta Siege.
        Requires captain level >= 4 or aggressive traits (Bloodthirsty, Cunning, Hero Slayer).
        Enforces 1 active siege max and a 5-day inter-siege cooldown.
        """
        if self.active_siege and self.active_siege.is_active:
            return None

        if not force_trigger and (current_day - self.last_siege_resolved_day < self.siege_cooldown_days):
            return None

        eligible = [
            c for c in self.captains.values()
            if c.active and not c.is_defeated and (
                c.level >= 4 or
                TRAIT_BLOODTHIRSTY in c.traits or
                TRAIT_CUNNING in c.traits or
                TRAIT_SLAYER in c.traits or
                c.kills_on_player >= 1
            )
        ]

        if not eligible:
            return None

        if force_trigger or random.random() < 0.35:
            # Pick highest threat captain
            captain = max(eligible, key=lambda c: (c.level, c.kills_on_player, len(c.traits)))
            target_terr = captain.claimed_territory if captain.claimed_territory in TERRITORIES else "forest"
            return self.trigger_vendetta_siege(captain.captain_id, target_terr, current_day)

        return None

    def trigger_vendetta_siege(
        self,
        captain_id: str,
        target_territory: Optional[str] = None,
        current_day: int = 1
    ) -> Optional[VendettaSiege]:
        """Initiates a Vendetta Siege against a designated world territory."""
        captain = self.captains.get(captain_id)
        if not captain or not captain.active or captain.is_defeated:
            return None

        target = target_territory or captain.claimed_territory or "forest"
        siege_id = f"siege_{captain_id}_d{current_day}_{self.siege_counter}"
        self.siege_counter += 1

        siege = VendettaSiege(
            siege_id=siege_id,
            captain_id=captain.captain_id,
            captain_name=captain.name,
            target_territory=target,
            duration_days=3,
            days_remaining=3,
            is_active=True,
            minions_count=3,
            is_resolved=False,
            outcome=None
        )
        self.active_siege = siege

        # 1. Register WorldEvent in WorldState
        if self.game_reference and hasattr(self.game_reference, "living_world"):
            ws = getattr(self.game_reference.living_world, "world_state", None)
            if ws and hasattr(ws, "active_events"):
                from rpg.world_state import WorldEvent
                evt = WorldEvent(
                    event_id=f"vendetta_siege_{siege_id}",
                    name=f"Vendetta Siege: {captain.name}",
                    description=f"{captain.name} is assaulting the {target.title()} with a warband!",
                    duration_days=3,
                    remaining_days=3,
                    effects={"danger_boost": 20, "prosperity_penalty": 10}
                )
                ws.active_events.append(evt)

        # 2. Push High Priority UI Notification
        if self.game_reference and hasattr(self.game_reference, "notification_manager") and self.game_reference.notification_manager:
            from rpg.notification import NotificationPriority
            self.game_reference.notification_manager.push_toast(
                f"⚔️ VENDETTA SIEGE: {captain.name} has attacked {target.title()}! (3 days left)",
                priority=NotificationPriority.HIGH
            )

        # 3. Seed early warning rumor in RumorBoard
        self._seed_siege_warning_rumor(captain, target)

        if self.event_bus:
            self.event_bus.emit(
                "vendetta_siege_started",
                siege_id=siege_id,
                captain_id=captain.captain_id,
                captain_name=captain.name,
                target_territory=target,
                duration_days=3
            )

        return siege

    def update_siege_day_tick(self, current_day: int) -> None:
        """Counts down days on the active siege and handles timeout defeat."""
        if not self.active_siege or not self.active_siege.is_active:
            return

        self.active_siege.days_remaining -= 1

        if self.active_siege.days_remaining == 1:
            # Emergency critical warning on final day
            if self.game_reference and hasattr(self.game_reference, "notification_manager") and self.game_reference.notification_manager:
                from rpg.notification import NotificationPriority
                self.game_reference.notification_manager.push_toast(
                    f"⚠️ SIEGE EMERGENCY: Final day to defend {self.active_siege.target_territory.title()} from {self.active_siege.captain_name}!",
                    priority=NotificationPriority.CRITICAL
                )
        elif self.active_siege.days_remaining <= 0:
            # Timeout defeat: Territory falls
            self.resolve_vendetta_siege(
                siege_id=self.active_siege.siege_id,
                outcome="defeat",
                current_day=current_day
            )

    def resolve_vendetta_siege(
        self,
        siege_id: str,
        outcome: str = "victory",
        player: Any = None,
        current_day: int = 1
    ) -> bool:
        """
        Resolves the active siege event on victory or timeout defeat.
        Enforces strict matching with the active siege ID.
        """
        if not self.active_siege or self.active_siege.siege_id != siege_id or not self.active_siege.is_active:
            return False

        siege = self.active_siege
        siege.is_active = False
        siege.is_resolved = True
        siege.outcome = outcome
        self.last_siege_resolved_day = current_day
        self.siege_history.append(siege)
        self.active_siege = None

        # Clean up WorldEvent
        if self.game_reference and hasattr(self.game_reference, "living_world"):
            ws = getattr(self.game_reference.living_world, "world_state", None)
            if ws and hasattr(ws, "active_events"):
                ws.active_events = [e for e in ws.active_events if e.event_id != f"vendetta_siege_{siege_id}"]

        captain = self.captains.get(siege.captain_id)

        if outcome == "victory":
            # 1. Bonus Gold & Loot for player
            if player and hasattr(player, "gold"):
                player.gold += 100

            # 2. Restore Stability & Prosperity
            if self.game_reference and hasattr(self.game_reference, "living_world"):
                lw = self.game_reference.living_world
                fw = getattr(lw, "faction_war", None)
                if fw and hasattr(fw, "control_points"):
                    for cp in fw.control_points.values():
                        if cp.map_name == siege.target_territory:
                            cp.stability = min(100.0, cp.stability + 25.0)
                            cp.contested = False
                ws = getattr(lw, "world_state", None)
                if ws:
                    ws.prosperity = min(100, getattr(ws, "prosperity", 50) + 10)
                    ws.road_safety = min(100.0, getattr(ws, "road_safety", 50.0) + 15.0)

            # 3. Mythos Legacy Record
            if self.game_reference and hasattr(self.game_reference, "mythos_manager") and self.game_reference.mythos_manager:
                from rpg.mythos import CATEGORY_COMBAT
                self.game_reference.mythos_manager.record_event({
                    "event_type": "vendetta_siege_defended",
                    "category": CATEGORY_COMBAT,
                    "day": current_day,
                    "actor": "Hero",
                    "target": siege.captain_name,
                    "location": siege.target_territory,
                    "outcome": f"Thwarted the Vendetta Siege of {siege.captain_name} at {siege.target_territory.title()}"
                })

            # 4. Push UI Notification
            if self.game_reference and hasattr(self.game_reference, "notification_manager") and self.game_reference.notification_manager:
                from rpg.notification import NotificationPriority
                self.game_reference.notification_manager.push_toast(
                    f"🎉 SIEGE DEFENDED: {siege.captain_name} was defeated! (+100g, +Territory Stability)",
                    priority=NotificationPriority.HIGH
                )

            # 5. Seed Triumph Rumor
            self._seed_siege_resolution_rumor(siege, outcome="victory")

        elif outcome == "defeat":
            # 1. Reduce Territory Stability & Shift to Bandits
            if self.game_reference and hasattr(self.game_reference, "living_world"):
                lw = self.game_reference.living_world
                fw = getattr(lw, "faction_war", None)
                from rpg.constants import FACTION_BANDITS
                if fw and hasattr(fw, "control_points"):
                    for cp in fw.control_points.values():
                        if cp.map_name == siege.target_territory:
                            cp.stability = max(0.0, cp.stability - 30.0)
                            cp.controlling_faction = FACTION_BANDITS
                            cp.contested = True
                ws = getattr(lw, "world_state", None)
                if ws:
                    ws.prosperity = max(0, getattr(ws, "prosperity", 50) - 10)
                    ws.danger_level = min(100, getattr(ws, "danger_level", 20) + 15)
                    ws.road_safety = max(0.0, getattr(ws, "road_safety", 50.0) - 20.0)

            # 2. Promote Captain (respecting max Lv.10 cap)
            if captain:
                captain.level_up(1)
                captain.victory_titles.append("The Conqueror")

            # 3. Push UI Notification
            if self.game_reference and hasattr(self.game_reference, "notification_manager") and self.game_reference.notification_manager:
                from rpg.notification import NotificationPriority
                self.game_reference.notification_manager.push_toast(
                    f"💀 SIEGE FALLEN: {siege.target_territory.title()} was sacked by {siege.captain_name}'s warband!",
                    priority=NotificationPriority.CRITICAL
                )

            # 4. Seed Panic Rumor
            self._seed_siege_resolution_rumor(siege, outcome="defeat")

        if self.event_bus:
            self.event_bus.emit(
                "vendetta_siege_resolved",
                siege_id=siege_id,
                outcome=outcome,
                captain_id=siege.captain_id,
                target_territory=siege.target_territory
            )

        return True

    def _seed_siege_warning_rumor(self, captain: NemesisCaptain, target_territory: str) -> None:
        """Seeds an early warning rumor about an impending siege on the RumorBoard."""
        if not self.game_reference:
            return
        lw = getattr(self.game_reference, "living_world", None)
        rumors = getattr(lw, "rumors", None) if lw else getattr(self.game_reference, "rumor_board", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            r_id = f"rumor_siege_warn_{captain.captain_id}_{self.siege_counter}"
            topic = f"Warband Sighted in {target_territory.title()}"
            true_txt = f"{captain.name} is gathering cutthroats to lay siege to the {target_territory.title()}!"
            dist_txt = f"They say {captain.name} leads an army of hundreds and vows to burn {target_territory.title()} to ashes!"
            rumors.add_custom_rumor(
                rumor_id=r_id,
                topic=topic,
                origin_npc="faye",
                true_content=true_txt,
                distorted_content=dist_txt
            )

    def _seed_siege_resolution_rumor(self, siege: VendettaSiege, outcome: str) -> None:
        """Seeds rumor about the siege outcome."""
        if not self.game_reference:
            return
        lw = getattr(self.game_reference, "living_world", None)
        rumors = getattr(lw, "rumors", None) if lw else getattr(self.game_reference, "rumor_board", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            r_id = f"rumor_siege_res_{siege.siege_id}_{outcome}"
            if outcome == "victory":
                topic = f"Relief of {siege.target_territory.title()}"
                true_txt = f"The hero shattered {siege.captain_name}'s siege at {siege.target_territory.title()}!"
                dist_txt = f"Bards sing that {siege.captain_name}'s entire horde fled screaming before the Hero's blade!"
            else:
                topic = f"Pillage of {siege.target_territory.title()}"
                true_txt = f"{siege.captain_name}'s warband overran the defenses of {siege.target_territory.title()}."
                dist_txt = f"Rumors claim {siege.target_territory.title()} has been reduced to smoldering rubble by {siege.captain_name}!"
            rumors.add_custom_rumor(
                rumor_id=r_id,
                topic=topic,
                origin_npc="eldrin" if outcome == "victory" else "dennis",
                true_content=true_txt,
                distorted_content=dist_txt
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
        self.active_siege = None
        self.siege_history.clear()
        self.last_siege_resolved_day = -999
        self.siege_counter = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serializes manager state."""
        return {
            "next_id": self._next_id,
            "captains": {k: v.to_dict() for k, v in self.captains.items()},
            "active_siege": self.active_siege.to_dict() if self.active_siege else None,
            "siege_history": [s.to_dict() for s in self.siege_history],
            "last_siege_resolved_day": self.last_siege_resolved_day,
            "siege_counter": self.siege_counter
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

        raw_active_siege = data.get("active_siege")
        self.active_siege = VendettaSiege.from_dict(raw_active_siege) if raw_active_siege else None

        raw_history = data.get("siege_history", [])
        self.siege_history = [VendettaSiege.from_dict(s) for s in raw_history]

        self.last_siege_resolved_day = data.get("last_siege_resolved_day", -999)
        self.siege_counter = data.get("siege_counter", 1)
