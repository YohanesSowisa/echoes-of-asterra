"""
Echoes of Asterra - Ancestral Soul Pacts & Physical Mutations Subsystem
Allows the hero to bind to ancient primordial pacts (Void Pact and Titan Pact)
that confer profound combat powers paired with mechanical trade-offs, procedural
physical sprite mutations, social reactivity, and heavy cleansing rituals.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

from rpg.events import EventBus

PACT_NONE = "none"
PACT_VOID = "void"
PACT_TITAN = "titan"
PACT_SOLAR = "solar"
ALL_PACTS = [PACT_VOID, PACT_TITAN, PACT_SOLAR]


@dataclass
class PactDefinition:
    """Static metadata and mechanical parameters for a Soul Pact."""
    pact_id: str
    name: str
    title: str
    description: str
    lore: str
    altar_location: str  # "crypt", "cave", or "ruins"
    altar_name: str
    gold_cost: int = 75
    required_level: int = 3
    required_items: Dict[str, int] = field(default_factory=dict)
    atk_range_mult: float = 1.0
    defense_bonus: int = 0
    speed_mult: float = 1.0
    stamina_cost_mult: float = 1.0
    mana_cost_mult: float = 1.0
    is_poise_immune: bool = False
    restricted_item_keywords: List[str] = field(default_factory=list)


# Registry of available Soul Pacts
PACT_DEFINITIONS: Dict[str, PactDefinition] = {
    PACT_VOID: PactDefinition(
        pact_id=PACT_VOID,
        name="Void Pact",
        title="Bearer of the Abyssal Reach",
        description="+40% Melee Reach & Void Pulse attacks. +20% Mana Skill cost, cannot wield metal shields.",
        lore="A forbidden communion with the Void Leviathan beneath Asterra. Replaces your weapon arm with undulating shadowy tentacles.",
        altar_location="crypt",
        altar_name="The Void Nexus Altar",
        gold_cost=75,
        required_level=3,
        required_items={"Ancient Relic": 1},
        atk_range_mult=1.40,
        defense_bonus=0,
        speed_mult=1.0,
        stamina_cost_mult=1.0,
        mana_cost_mult=1.20,
        is_poise_immune=False,
        restricted_item_keywords=["iron shield", "tower shield", "steel shield", "metal shield"]
    ),
    PACT_TITAN: PactDefinition(
        pact_id=PACT_TITAN,
        name="Titan Pact",
        title="Vessel of the Stone Warden",
        description="Immunity to Poise Stagger & +6 Base Defense. +50% Dash Stamina cost, -10% Movement Speed.",
        lore="An ancient rite of earth-melding in the deep caverns. Encases your chest and shoulders in indestructible granite plates.",
        altar_location="cave",
        altar_name="The Titan Lith Altar",
        gold_cost=75,
        required_level=3,
        required_items={"Iron Ore": 3, "Silver Ore": 1},
        atk_range_mult=1.0,
        defense_bonus=6,
        speed_mult=0.90,
        stamina_cost_mult=1.50,
        mana_cost_mult=1.0,
        is_poise_immune=True,
        restricted_item_keywords=[]
    ),
    PACT_SOLAR: PactDefinition(
        pact_id=PACT_SOLAR,
        name="Solar Seraph Pact",
        title="Vessel of the Morning Star",
        description="Radiant Sunfire Aura, +2.0 HP/s & Mana/s Peace Regen. +20% Damage taken at night, cannot equip dark robes.",
        lore="An ancient communion at the Sun Temple ruins. Sprouts celestial golden feathered wings and a radiant sunfire halo.",
        altar_location="ruins",
        altar_name="The Sunfire Altar",
        gold_cost=75,
        required_level=3,
        required_items={"Topaz": 1},
        atk_range_mult=1.0,
        defense_bonus=2,
        speed_mult=1.05,
        stamina_cost_mult=1.0,
        mana_cost_mult=0.90,
        is_poise_immune=False,
        restricted_item_keywords=["cultist", "shadow", "dark robe", "void cloak"]
    )
}


@dataclass
class PlayerPactState:
    """Dynamic persistent state of the player's active and historic Soul Pacts."""
    active_pact_id: Optional[str] = None
    bound_day: int = 1
    pact_tier: int = 1
    pact_xp: int = 0
    pact_history: List[str] = field(default_factory=list)
    last_cleansed_day: int = -999
    cleansing_cooldown_days: int = 3
    cleansing_gold_cost: int = 150
    cleansing_item: str = "Starlight Crystal"

    @property
    def xp_needed_for_next_tier(self) -> int:
        if self.pact_tier == 1:
            return 250
        elif self.pact_tier == 2:
            return 750
        return 999999

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_pact_id": self.active_pact_id,
            "bound_day": self.bound_day,
            "pact_tier": self.pact_tier,
            "pact_xp": self.pact_xp,
            "pact_history": list(self.pact_history),
            "last_cleansed_day": self.last_cleansed_day,
            "cleansing_cooldown_days": self.cleansing_cooldown_days,
            "cleansing_gold_cost": self.cleansing_gold_cost,
            "cleansing_item": self.cleansing_item
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlayerPactState":
        if not data:
            return cls()
        return cls(
            active_pact_id=data.get("active_pact_id"),
            bound_day=data.get("bound_day", 1),
            pact_tier=data.get("pact_tier", 1),
            pact_xp=data.get("pact_xp", 0),
            pact_history=data.get("pact_history", []),
            last_cleansed_day=data.get("last_cleansed_day", -999),
            cleansing_cooldown_days=data.get("cleansing_cooldown_days", 3),
            cleansing_gold_cost=data.get("cleansing_gold_cost", 150),
            cleansing_item=data.get("cleansing_item", "Starlight Crystal")
        )


class PactManager:
    """
    Orchestrator for binding, cleansing, tier mastery progression,
    query hooks, and event signals for Ancestral Soul Pacts and Physical Mutations.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.definitions: Dict[str, PactDefinition] = PACT_DEFINITIONS
        self.state: PlayerPactState = PlayerPactState()
        self.game_reference: Any = None

        if self.event_bus:
            self.register_event_listeners(self.event_bus)

    def register_event_listeners(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.event_bus.subscribe("enemy_killed", self._on_enemy_killed)
        self.event_bus.subscribe("day_changed", self._on_day_changed)

    # -------------------------------------------------------------
    # Binding & Cleansing Mechanics
    # -------------------------------------------------------------
    def bind_pact(self, pact_id: str, player: Any, current_day: int = 1) -> Tuple[bool, str]:
        """
        Binds the player to a specified Soul Pact if costs and requirements are satisfied.
        Enforces mutual exclusivity (1 active pact at a time).
        """
        if pact_id not in self.definitions:
            return False, f"Unknown Soul Pact ID: {pact_id}"

        defn = self.definitions[pact_id]

        # 1. Check if already bound to this pact
        if self.state.active_pact_id == pact_id:
            return False, f"You are already bound to the {defn.name}."

        # 2. Check mutual exclusivity (cannot bind second pact without cleansing)
        if self.state.active_pact_id and self.state.active_pact_id != pact_id:
            cur_pact = self.definitions.get(self.state.active_pact_id)
            cur_name = cur_pact.name if cur_pact else self.state.active_pact_id
            return False, f"You are already bound to the {cur_name}. You must undergo a Purification Ritual to cleanse it first."

        # 3. Check level requirement
        p_level = getattr(player, "level", 1)
        if p_level < defn.required_level:
            return False, f"Requires Player Level {defn.required_level} (Current: Lv.{p_level})."

        # 4. Check Gold cost
        p_gold = getattr(player, "gold", 0)
        if p_gold < defn.gold_cost:
            return False, f"Insufficient Gold: Requires {defn.gold_cost}g (Current: {p_gold}g)."

        # 5. Check item materials in inventory
        if hasattr(player, "inventory") and defn.required_items:
            for item_name, req_qty in defn.required_items.items():
                has_qty = self._count_player_item(player, item_name)
                # Flexible fallback for Void Pact: Ancient Relic OR 2x Crystal Shard
                if has_qty < req_qty:
                    if pact_id == PACT_VOID and item_name == "Ancient Relic":
                        fallback_qty = self._count_player_item(player, "Crystal Shard")
                        if fallback_qty >= 2:
                            continue
                    return False, f"Missing required offering: {req_qty}x {item_name}."

        # Deduct Gold
        player.gold -= defn.gold_cost

        # Deduct Items
        if hasattr(player, "inventory") and defn.required_items:
            for item_name, req_qty in defn.required_items.items():
                if self._count_player_item(player, item_name) >= req_qty:
                    self._remove_player_item(player, item_name, req_qty)
                elif pact_id == PACT_VOID and item_name == "Ancient Relic":
                    self._remove_player_item(player, "Crystal Shard", 2)

        # Apply Pact State
        self.state.active_pact_id = pact_id
        self.state.bound_day = current_day
        if pact_id not in self.state.pact_history:
            self.state.pact_history.append(pact_id)

        # Unequip restricted items if currently equipped
        self._enforce_equipment_restrictions(player, defn)

        # Push High-Priority Toast
        if self.game_reference and hasattr(self.game_reference, "notification_manager") and self.game_reference.notification_manager:
            from rpg.notification import NotificationPriority
            self.game_reference.notification_manager.push_toast(
                f"🔮 PACT FORGED: Bound to {defn.name}! ({defn.title})",
                priority=NotificationPriority.HIGH
            )

        # Seed Rumor on RumorBoard
        self._seed_pact_rumor(defn, outcome="bound")

        # Emit EventBus Signal
        if self.event_bus:
            self.event_bus.emit(
                "pact_bound",
                pact_id=pact_id,
                pact_name=defn.name,
                player=player,
                day=current_day
            )

        return True, f"Successfully bound your soul to the {defn.name}!"

    def cleanse_pact(self, player: Any, current_day: int = 1) -> Tuple[bool, str]:
        """
        Cleanses the active Soul Pact via Purification Ritual.
        Requires 150g + 1x Starlight Crystal and enforces a 3-day cooldown.
        """
        if not self.state.active_pact_id:
            return False, "You bear no active Soul Pact to cleanse."

        old_pact_id = self.state.active_pact_id
        old_defn = self.definitions.get(old_pact_id)
        old_name = old_defn.name if old_defn else old_pact_id

        # 1. Cooldown check
        days_since_cleansed = current_day - self.state.last_cleansed_day
        if days_since_cleansed < self.state.cleansing_cooldown_days:
            rem_days = self.state.cleansing_cooldown_days - days_since_cleansed
            return False, f"Your soul is still recovering from a previous ritual. Cleansing ready in {rem_days} days."

        # 2. Gold check
        p_gold = getattr(player, "gold", 0)
        if p_gold < self.state.cleansing_gold_cost:
            return False, f"Purification requires {self.state.cleansing_gold_cost}g (Current: {p_gold}g)."

        # 3. Item check (Starlight Crystal or Ancient Relic fallback)
        has_crystal = self._count_player_item(player, self.state.cleansing_item) >= 1
        has_relic = self._count_player_item(player, "Ancient Relic") >= 1
        if not has_crystal and not has_relic:
            return False, f"Purification requires 1x {self.state.cleansing_item} as a spiritual catalyst."

        # Deduct Gold and Material
        player.gold -= self.state.cleansing_gold_cost
        if has_crystal:
            self._remove_player_item(player, self.state.cleansing_item, 1)
        else:
            self._remove_player_item(player, "Ancient Relic", 1)

        # Reset Active Pact State
        self.state.active_pact_id = None
        self.state.last_cleansed_day = current_day

        # Push Toast
        if self.game_reference and hasattr(self.game_reference, "notification_manager") and self.game_reference.notification_manager:
            from rpg.notification import NotificationPriority
            self.game_reference.notification_manager.push_toast(
                f"✨ SOUL PURIFIED: Cleansed the {old_name}! Baseline humanity restored.",
                priority=NotificationPriority.HIGH
            )

        # Seed Rumor
        if old_defn:
            self._seed_pact_rumor(old_defn, outcome="cleansed")

        # Emit EventBus Signal
        if self.event_bus:
            self.event_bus.emit(
                "pact_cleansed",
                pact_id=old_pact_id,
                pact_name=old_name,
                player=player,
                day=current_day
            )

        return True, f"The Purification Ritual succeeded. Your soul has been cleansed of the {old_name}."

    # -------------------------------------------------------------
    # Pact Mastery Progression & Tier Scaling
    # -------------------------------------------------------------
    def gain_pact_xp(self, amount: int) -> bool:
        """
        Awards pact experience points (from slaying enemies or defeating bosses).
        Advances pact tier when reaching milestones:
        - Tier 1: 0 - 249 XP (Novice)
        - Tier 2: 250 - 749 XP (Ascendant)
        - Tier 3: 750+ XP (Paragon)
        """
        if not self.state.active_pact_id:
            return False

        old_tier = self.state.pact_tier
        self.state.pact_xp += amount

        new_tier = 1
        if self.state.pact_xp >= 750:
            new_tier = 3
        elif self.state.pact_xp >= 250:
            new_tier = 2

        if new_tier > old_tier:
            self.state.pact_tier = new_tier
            defn = self.get_active_pact()
            p_name = defn.name if defn else self.state.active_pact_id
            tier_title = self.get_pact_tier_name()

            # Push high priority celebration toast
            if self.game_reference and hasattr(self.game_reference, "notification_manager") and self.game_reference.notification_manager:
                from rpg.notification import NotificationPriority
                self.game_reference.notification_manager.push_toast(
                    f"⭐ PACT ASCENSION: {p_name} reached Tier {new_tier} ({tier_title})!",
                    priority=NotificationPriority.HIGH
                )

            # Emit EventBus signal
            if self.event_bus:
                self.event_bus.emit(
                    "pact_tier_ascended",
                    pact_id=self.state.active_pact_id,
                    new_tier=new_tier,
                    tier_title=tier_title
                )
            return True
        return False

    def get_pact_tier_name(self) -> str:
        """Returns the prestige title for current pact tier."""
        tier_names = {1: "Novice", 2: "Ascendant", 3: "Paragon"}
        return tier_names.get(self.state.pact_tier, "Novice")

    def _on_enemy_killed(self, enemy: Any = None, **kwargs: Any) -> None:
        """Event listener granting pact XP when monsters are defeated."""
        if not self.state.active_pact_id:
            return
        is_boss = getattr(enemy, "is_boss", False) if enemy else False
        xp_gain = 50 if is_boss else 15
        self.gain_pact_xp(xp_gain)

    def _on_day_changed(self, current_day: int = 1, **kwargs: Any) -> None:
        """Applies daily social stigma / faction standing impact when pact is active."""
        if not self.state.active_pact_id or self.state.pact_tier < 2:
            return

        # Void Tier 2+: Knights of Asterra faction reputation slowly decays (-1 daily)
        if self.state.active_pact_id == PACT_VOID and self.game_reference and hasattr(self.game_reference, "factions"):
            fm = self.game_reference.factions
            if hasattr(fm, "modify_reputation"):
                fm.modify_reputation("knights", -1)

    def get_merchant_price_multiplier(self, merchant_id: str = "silas") -> float:
        """Returns dynamic trade surcharge or discount based on active pact tier."""
        if not self.state.active_pact_id or self.state.pact_tier < 2:
            return 1.0

        # Void Pact Tier 2+: Silas charges +15% occult hazard surcharge
        if self.state.active_pact_id == PACT_VOID and "silas" in merchant_id.lower():
            return 1.15

        # Titan Pact Tier 2+: Dennis gives 10% discount on blacksmith goods
        if self.state.active_pact_id == PACT_TITAN and "dennis" in merchant_id.lower():
            return 0.90

        return 1.0

    # -------------------------------------------------------------
    # Query Hooks for Combat, Physics & UI
    # -------------------------------------------------------------
    def get_active_pact(self) -> Optional[PactDefinition]:
        """Returns active PactDefinition if bound, else None."""
        if self.state.active_pact_id in self.definitions:
            return self.definitions[self.state.active_pact_id]
        return None

    def get_attack_range_multiplier(self) -> float:
        """Returns melee attack range reach multiplier scaling with tier (1.40x -> 1.50x -> 1.65x)."""
        pact = self.get_active_pact()
        if not pact or pact.pact_id != PACT_VOID:
            return 1.0
        tier = self.state.pact_tier
        if tier == 1:
            return 1.40
        elif tier == 2:
            return 1.50
        return 1.65

    def is_poise_immune(self) -> bool:
        """Returns True if player is immune to poise stagger (Titan Super Armor)."""
        pact = self.get_active_pact()
        return pact.is_poise_immune if pact else False

    def get_stamina_cost_multiplier(self) -> float:
        """Returns dash stamina consumption multiplier (e.g. 1.5x for Titan Pact)."""
        pact = self.get_active_pact()
        return pact.stamina_cost_mult if pact else 1.0

    def get_mana_cost_multiplier(self) -> float:
        """Returns skill mana consumption multiplier (e.g. 1.2x for Void Pact)."""
        pact = self.get_active_pact()
        return pact.mana_cost_mult if pact else 1.0

    def get_speed_multiplier(self) -> float:
        """Returns movement speed multiplier (e.g. 0.9x for Titan Pact)."""
        pact = self.get_active_pact()
        return pact.speed_mult if pact else 1.0

    def get_defense_bonus(self) -> int:
        """Returns flat base defense bonus scaling with tier (+6 -> +9 -> +12 for Titan Pact)."""
        pact = self.get_active_pact()
        if not pact or pact.pact_id != PACT_TITAN:
            return 0
        tier = self.state.pact_tier
        if tier == 1:
            return 6
        elif tier == 2:
            return 9
        return 12

    def can_equip_item(self, item: Any) -> bool:
        """Validates if the player's active pact permits equipping this specific item."""
        pact = self.get_active_pact()
        if not pact or not pact.restricted_item_keywords:
            return True
        if not item:
            return True

        item_name = getattr(item, "name", "").lower()
        for kw in pact.restricted_item_keywords:
            if kw.lower() in item_name:
                return False
        return True

    def get_peace_regen_bonus(self) -> Tuple[float, float]:
        """Returns (hp_regen_bonus, mana_regen_bonus) per second while out of combat."""
        if self.state.active_pact_id != PACT_SOLAR:
            return 0.0, 0.0
        tier = self.state.pact_tier
        if tier == 1:
            return 2.0, 2.0
        elif tier == 2:
            return 3.5, 3.5
        return 5.0, 5.0

    def get_light_radius_multiplier(self) -> float:
        """Returns illumination radius multiplier for dark/night environments."""
        if self.state.active_pact_id != PACT_SOLAR:
            return 1.0
        tier = self.state.pact_tier
        if tier == 1:
            return 1.25
        elif tier == 2:
            return 1.45
        return 1.70

    def get_damage_taken_multiplier(self, is_night: bool = False) -> float:
        """Returns damage taken multiplier (+20% for Solar Seraph at night)."""
        if self.state.active_pact_id == PACT_SOLAR and is_night:
            return 1.20
        return 1.0

    def cast_pact_ability(self, player: Any, enemies: Optional[List[Any]] = None) -> Tuple[bool, str]:
        """
        Executes the signature Primordial Active Ability for the active soul pact:
        - Void: Abyssal Rift Vortex (25 Mana) -> pulls nearby enemies inward and deals 25 void damage.
        - Titan: Earthshatter Quake (30 Stamina) -> ground shockwave dealing 30 damage & 2.0s poise stagger.
        - Solar: Solar Cleansing Nova (30 Mana) -> heals player 35 HP and burns nearby foes for 25 holy damage.
        """
        if not self.state.active_pact_id:
            return False, "No active Soul Pact bound."

        p_id = self.state.active_pact_id
        tier = self.state.pact_tier
        tier_mult = 1.0 + (tier - 1) * 0.35

        if p_id == PACT_VOID:
            mana_cost = int(25 * self.get_mana_cost_multiplier())
            if getattr(player, "mana", 0) < mana_cost:
                return False, f"Not enough Mana ({getattr(player, 'mana', 0)}/{mana_cost}) for Abyssal Rift Vortex!"
            player.mana -= mana_cost

            p_pos = (getattr(player, "x", 0), getattr(player, "y", 0))
            if hasattr(player, "rect"):
                p_pos = player.rect.center
            hit_count = 0
            if enemies:
                for e in enemies:
                    if not getattr(e, "is_alive", True):
                        continue
                    e_pos = (getattr(e, "x", 0), getattr(e, "y", 0))
                    if hasattr(e, "rect"):
                        e_pos = e.rect.center
                    dx = p_pos[0] - e_pos[0]
                    dy = p_pos[1] - e_pos[1]
                    dist = (dx**2 + dy**2)**0.5
                    if dist <= 180:
                        pull_factor = 0.5
                        if hasattr(e, "x") and hasattr(e, "y"):
                            e.x += dx * pull_factor
                            e.y += dy * pull_factor
                        if hasattr(e, "take_damage"):
                            dmg = int(25 * tier_mult)
                            e.take_damage(dmg)
                        hit_count += 1

            if self.event_bus:
                self.event_bus.emit("pact_ability_cast", pact_id=p_id, ability_name="Abyssal Rift Vortex", hits=hit_count)
            return True, f"Cast Abyssal Rift Vortex! Pulled {hit_count} enemies."

        elif p_id == PACT_TITAN:
            stam_cost = int(30 * self.get_stamina_cost_multiplier())
            if getattr(player, "stamina", 0) < stam_cost:
                return False, f"Not enough Stamina ({int(getattr(player, 'stamina', 0))}/{stam_cost}) for Earthshatter Quake!"
            player.stamina -= stam_cost

            p_pos = (getattr(player, "x", 0), getattr(player, "y", 0))
            if hasattr(player, "rect"):
                p_pos = player.rect.center
            hit_count = 0
            if enemies:
                for e in enemies:
                    if not getattr(e, "is_alive", True):
                        continue
                    e_pos = (getattr(e, "x", 0), getattr(e, "y", 0))
                    if hasattr(e, "rect"):
                        e_pos = e.rect.center
                    dist = ((p_pos[0] - e_pos[0])**2 + (p_pos[1] - e_pos[1])**2)**0.5
                    if dist <= 140:
                        dmg = int(30 * tier_mult)
                        if hasattr(e, "take_damage"):
                            e.take_damage(dmg)
                        if hasattr(e, "apply_stagger"):
                            e.apply_stagger(2.0)
                        hit_count += 1

            if self.event_bus:
                self.event_bus.emit("pact_ability_cast", pact_id=p_id, ability_name="Earthshatter Quake", hits=hit_count)
            return True, f"Cast Earthshatter Quake! Staggered {hit_count} enemies."

        elif p_id == PACT_SOLAR:
            mana_cost = int(30 * self.get_mana_cost_multiplier())
            if getattr(player, "mana", 0) < mana_cost:
                return False, f"Not enough Mana ({getattr(player, 'mana', 0)}/{mana_cost}) for Solar Cleansing Nova!"
            player.mana -= mana_cost

            heal_amt = int(35 * tier_mult)
            if hasattr(player, "heal"):
                player.heal(heal_amt)
            elif hasattr(player, "hp") and hasattr(player, "max_hp"):
                player.hp = min(player.max_hp, player.hp + heal_amt)

            p_pos = (getattr(player, "x", 0), getattr(player, "y", 0))
            if hasattr(player, "rect"):
                p_pos = player.rect.center
            hit_count = 0
            if enemies:
                for e in enemies:
                    if not getattr(e, "is_alive", True):
                        continue
                    e_pos = (getattr(e, "x", 0), getattr(e, "y", 0))
                    if hasattr(e, "rect"):
                        e_pos = e.rect.center
                    dist = ((p_pos[0] - e_pos[0])**2 + (p_pos[1] - e_pos[1])**2)**0.5
                    if dist <= 150:
                        dmg = int(25 * tier_mult)
                        if hasattr(e, "take_damage"):
                            e.take_damage(dmg)
                        hit_count += 1

            if self.event_bus:
                self.event_bus.emit("pact_ability_cast", pact_id=p_id, ability_name="Solar Cleansing Nova", heal=heal_amt, hits=hit_count)
            return True, f"Cast Solar Cleansing Nova! Healed {heal_amt} HP and scorched {hit_count} enemies."

        return False, "Unknown pact ability."

    # -------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------
    def _count_player_item(self, player: Any, item_name: str) -> int:
        """Counts quantity of matching item in player inventory."""
        if not hasattr(player, "inventory"):
            return 0
        inv = player.inventory
        slots = getattr(inv, "slots", inv) if not isinstance(inv, list) else inv
        count = 0
        for it in slots:
            if it:
                it_name = getattr(it, "name", it.get("name", "") if isinstance(it, dict) else str(it))
                if it_name.lower() == item_name.lower():
                    qty = getattr(it, "qty", it.get("qty", 1) if isinstance(it, dict) else 1)
                    count += qty
        return count

    def _remove_player_item(self, player: Any, item_name: str, qty_to_remove: int) -> None:
        """Removes specified quantity of item from player inventory."""
        if not hasattr(player, "inventory"):
            return
        inv = player.inventory
        slots = getattr(inv, "slots", inv) if not isinstance(inv, list) else inv
        remaining = qty_to_remove
        for it in slots:
            if it and remaining > 0:
                it_name = getattr(it, "name", it.get("name", "") if isinstance(it, dict) else str(it))
                if it_name.lower() == item_name.lower():
                    if hasattr(it, "qty"):
                        take = min(it.qty, remaining)
                        it.qty -= take
                        remaining -= take
                        if it.qty <= 0 and hasattr(inv, "remove_item"):
                            inv.remove_item(it)
                    elif isinstance(it, dict):
                        take = min(it.get("qty", 1), remaining)
                        it["qty"] = it.get("qty", 1) - take
                        remaining -= take

    def _enforce_equipment_restrictions(self, player: Any, defn: PactDefinition) -> None:
        """Unequips restricted items (e.g. metal shields) when Void Pact is bound."""
        if not hasattr(player, "equipment") or not defn.restricted_item_keywords:
            return
        eq = player.equipment
        slots = getattr(eq, "slots", eq)
        if isinstance(slots, dict):
            for slot_key, it in list(slots.items()):
                if it and not self.can_equip_item(it):
                    # Unequip to inventory
                    if hasattr(eq, "unequip"):
                        eq.unequip(slot_key)
                    else:
                        slots[slot_key] = None

    def _seed_pact_rumor(self, defn: PactDefinition, outcome: str = "bound") -> None:
        """Seeds dynamic gossip on RumorBoard regarding the pact binding or cleansing."""
        if not self.game_reference:
            return
        lw = getattr(self.game_reference, "living_world", None)
        rumors = getattr(lw, "rumors", None) if lw else getattr(self.game_reference, "rumor_board", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            r_id = f"rumor_pact_{defn.pact_id}_{outcome}"
            if outcome == "bound":
                topic = f"Whispers of {defn.name}"
                true_txt = f"The Hero made an ancient covenant at {defn.altar_name} and took upon the {defn.name}."
                dist_txt = f"Word on the street is the Hero sold their soul to dark monstrosities for unnatural power!"
            else:
                topic = f"Purification of the Hero"
                true_txt = f"The Hero underwent a solemn Purification Ritual, renouncing the {defn.name}."
                dist_txt = f"They say holy priests cleansed the Hero with blazing starfire to burn away eldritch corruption!"

            rumors.add_custom_rumor(
                rumor_id=r_id,
                topic=topic,
                origin_npc="eldrin" if outcome == "cleansed" else "silas",
                true_content=true_txt,
                distorted_content=dist_txt
            )

    # -------------------------------------------------------------
    # Lifecycle & Persistence
    # -------------------------------------------------------------
    def reset(self) -> None:
        """Resets all soul pact data for a fresh game session."""
        self.state = PlayerPactState()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes manager state."""
        return {
            "state": self.state.to_dict()
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes manager state."""
        if not data:
            return
        raw_state = data.get("state", {})
        self.state = PlayerPactState.from_dict(raw_state)
