"""
Echoes of Asterra - Pillar #7: The Living Dungeon Sovereign (Crypt Architect)
Engine for Dungeon Core claiming, grid-based dungeon lair room editing,
trap placement (Spikes, Iron Portcullis, Bait Mimic Chests), and defense execution.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
import pygame
from rpg.events import EventBus
from rpg.settings import TILE_SIZE

# Trap Type Constants
TRAP_SPIKE = "spike_trap"
TRAP_PORTCULLIS = "iron_portcullis"
TRAP_MIMIC_CHEST = "mimic_chest"


@dataclass
class TrapBlueprint:
    """Blueprint definition for a constructible dungeon defense trap."""
    trap_type: str
    name: str
    gold_cost: int
    material_cost: Dict[str, int]
    damage: int
    cooldown: float
    description: str


DEFAULT_TRAP_BLUEPRINTS: Dict[str, TrapBlueprint] = {
    TRAP_SPIKE: TrapBlueprint(
        trap_type=TRAP_SPIKE,
        name="Spike Trap",
        gold_cost=25,
        material_cost={"Granite Stone": 2},
        damage=35,
        cooldown=2.5,
        description="Retractable steel spikes dealing 35 physical pierce damage to passing intruders."
    ),
    TRAP_PORTCULLIS: TrapBlueprint(
        trap_type=TRAP_PORTCULLIS,
        name="Iron Portcullis",
        gold_cost=40,
        material_cost={"Iron Ore": 4},
        damage=15,
        cooldown=5.0,
        description="Reinforced iron gate that slams shut, impeding intruder movement."
    ),
    TRAP_MIMIC_CHEST: TrapBlueprint(
        trap_type=TRAP_MIMIC_CHEST,
        name="Bait Mimic Chest",
        gold_cost=50,
        material_cost={"Luminescent Spore": 1},
        damage=60,
        cooldown=4.0,
        description="Deceptive gold chest that chomps greedy intruders for 60 heavy damage."
    )
}

MAX_DUNGEON_FLOORS = 3
FLOOR_NAMES: Dict[int, str] = {
    1: "Forgotten Crypt",
    2: "Deep Catacombs",
    3: "Abyssal Vaults"
}
FLOOR_UNLOCK_COSTS: Dict[int, Tuple[int, int]] = {
    2: (200, 50),   # Floor 2: 200 Gold, 50 Infamy
    3: (400, 100)   # Floor 3: 400 Gold, 100 Infamy
}


@dataclass
class PlacedTrap:
    """Represents a live trap constructed inside the player's dungeon lair."""
    trap_id: str
    trap_type: str
    grid_x: int
    grid_y: int
    floor: int = 1
    cooldown_timer: float = 0.0
    is_active: bool = True

    @property
    def world_pos(self) -> Tuple[int, int]:
        return (self.grid_x * TILE_SIZE, self.grid_y * TILE_SIZE)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.grid_x * TILE_SIZE, self.grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trap_id": self.trap_id,
            "trap_type": self.trap_type,
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "floor": self.floor,
            "is_active": self.is_active
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlacedTrap":
        return cls(
            trap_id=data.get("trap_id", ""),
            trap_type=data.get("trap_type", TRAP_SPIKE),
            grid_x=data.get("grid_x", 0),
            grid_y=data.get("grid_y", 0),
            floor=data.get("floor", 1),
            is_active=data.get("is_active", True)
        )


@dataclass
class CapturedMonster:
    """Represents a wild monster captured and domesticated for dungeon defense."""
    monster_id: str
    monster_type: str
    name: str
    level: int = 1
    hp: float = 50.0
    max_hp: float = 50.0
    atk: float = 12.0
    assigned_grid_x: Optional[int] = None
    assigned_grid_y: Optional[int] = None
    assigned_floor: Optional[int] = None
    is_stationed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "monster_id": self.monster_id,
            "monster_type": self.monster_type,
            "name": self.name,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "atk": self.atk,
            "assigned_grid_x": self.assigned_grid_x,
            "assigned_grid_y": self.assigned_grid_y,
            "assigned_floor": self.assigned_floor,
            "is_stationed": self.is_stationed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapturedMonster":
        return cls(
            monster_id=data.get("monster_id", ""),
            monster_type=data.get("monster_type", "wild_beast"),
            name=data.get("name", "Domesticated Beast"),
            level=data.get("level", 1),
            hp=float(data.get("hp", 50.0)),
            max_hp=float(data.get("max_hp", 50.0)),
            atk=float(data.get("atk", 12.0)),
            assigned_grid_x=data.get("assigned_grid_x"),
            assigned_grid_y=data.get("assigned_grid_y"),
            assigned_floor=data.get("assigned_floor"),
            is_stationed=data.get("is_stationed", False)
        )


class DungeonArchitectManager:
    """
    Manages the player's sovereign personal crypt dungeon:
    - Dungeon Core claiming state
    - Grid-based trap construction and removal
    - Trap collision and damage simulation against enemies and raiders
    - Room layout and defense rating
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.core_claimed: bool = False
        self.current_floor: int = 1
        self.max_unlocked_floor: int = 1
        self.placed_traps: Dict[str, PlacedTrap] = {}
        self.captured_monsters: Dict[str, CapturedMonster] = {}
        self.total_traps_triggered: int = 0
        self.total_damage_dealt: int = 0
        self.blueprints = dict(DEFAULT_TRAP_BLUEPRINTS)
        self.dungeon_infamy: int = 0
        self.last_invasion_day: int = 0
        self.invasion_interval_days: int = 3
        self.active_invasion: Optional[Dict[str, Any]] = None
        self.total_invasions_repelled: int = 0
        self.total_invasions_failed: int = 0
        self.reset()
        if self.event_bus:
            self.event_bus.subscribe("boss_defeated", self._on_boss_defeated)
            self.event_bus.subscribe("day_changed", self._on_day_changed)

    def _on_boss_defeated(self, boss_id: str = "", **kwargs: Any) -> None:
        if boss_id in ["crypt_guardian", "bone_monarch"]:
            if not self.core_claimed:
                if self.event_bus:
                    self.event_bus.emit("dungeon_core_unlockable", floor=1)

    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        self.trigger_daily_invasion(day=day)

    def reset(self) -> None:
        """Resets the dungeon architect state to default."""
        self.core_claimed = False
        self.current_floor = 1
        self.max_unlocked_floor = 1
        self.placed_traps = {}
        self.captured_monsters = {}
        self.total_traps_triggered = 0
        self.total_damage_dealt = 0
        self.dungeon_infamy = 0
        self.last_invasion_day = 0
        self.active_invasion = None
        self.total_invasions_repelled = 0
        self.total_invasions_failed = 0

    def claim_dungeon_core(self, player: Any) -> Tuple[bool, str]:
        """Claims ownership of the Crypt Dungeon Core Stone."""
        if self.core_claimed:
            return False, "Dungeon Core Stone is already claimed."

        self.core_claimed = True

        if hasattr(player, "titles") and isinstance(player.titles, set):
            player.titles.add("Crypt Sovereign")

        if self.event_bus:
            self.event_bus.emit(
                "dungeon_core_claimed",
                floor=self.current_floor,
                title="Crypt Sovereign"
            )
            self.event_bus.emit("title_unlocked", title="Crypt Sovereign")

        return True, "Successfully claimed the Dungeon Core Stone! You are now the Crypt Sovereign."

    def place_trap(
        self,
        trap_type: str,
        grid_x: int,
        grid_y: int,
        player: Any,
        floor: int = 1
    ) -> Tuple[bool, str]:
        """
        Constructs a defense trap on the specified dungeon grid coordinate.
        Validates gold, material inventory, and grid availability.
        """
        if not self.core_claimed:
            return False, "Must claim the Dungeon Core Stone before constructing defenses."

        if trap_type not in self.blueprints:
            return False, f"Unknown trap type: '{trap_type}'."

        pos_key = f"{floor}_{grid_x}_{grid_y}"
        if pos_key in self.placed_traps:
            return False, f"Grid tile ({grid_x}, {grid_y}) already contains a trap."

        bp = self.blueprints[trap_type]

        # 1. Gold cost validation
        if getattr(player, "gold", 0) < bp.gold_cost:
            return False, f"Insufficient gold ({player.gold}/{bp.gold_cost} Gold required)."

        # 2. Material cost validation
        if hasattr(player, "inventory") and player.inventory:
            for mat_name, qty in bp.material_cost.items():
                if not player.inventory.has_item(mat_name, qty):
                    return False, f"Missing required materials: {qty}x {mat_name}."

        # 3. Deduct resources
        player.gold -= bp.gold_cost
        if hasattr(player, "inventory") and player.inventory:
            for mat_name, qty in bp.material_cost.items():
                player.inventory.remove_item(mat_name, qty)

        # 4. Construct trap
        trap_id = f"trap_{trap_type}_{floor}_{grid_x}_{grid_y}"
        placed = PlacedTrap(
            trap_id=trap_id,
            trap_type=trap_type,
            grid_x=grid_x,
            grid_y=grid_y,
            floor=floor
        )
        self.placed_traps[pos_key] = placed

        if self.event_bus:
            self.event_bus.emit(
                "trap_constructed",
                trap_id=trap_id,
                trap_type=trap_type,
                grid_x=grid_x,
                grid_y=grid_y,
                floor=floor
            )

        return True, f"Successfully placed {bp.name} at ({grid_x}, {grid_y})!"

    def remove_trap(
        self,
        grid_x: int,
        grid_y: int,
        player: Any,
        floor: int = 1
    ) -> Tuple[bool, str]:
        """
        Dismantles a placed trap, refunding 50% of the gold construction cost.
        """
        pos_key = f"{floor}_{grid_x}_{grid_y}"
        if pos_key not in self.placed_traps:
            return False, f"No trap found at ({grid_x}, {grid_y})."

        trap = self.placed_traps[pos_key]
        bp = self.blueprints.get(trap.trap_type)
        refund_gold = int(bp.gold_cost * 0.5) if bp else 0

        del self.placed_traps[pos_key]
        if hasattr(player, "gold"):
            player.gold += refund_gold

        if self.event_bus:
            self.event_bus.emit(
                "trap_dismantled",
                trap_id=trap.trap_id,
                trap_type=trap.trap_type,
                grid_x=grid_x,
                grid_y=grid_y,
                floor=floor,
                refund=refund_gold
            )

        return True, f"Dismantled {trap.trap_type} at ({grid_x}, {grid_y}). Refunded {refund_gold} Gold."

    def get_traps_for_floor(self, floor: int = 1) -> List[PlacedTrap]:
        """Returns all placed traps on the specified dungeon floor."""
        return [t for t in self.placed_traps.values() if t.floor == floor]

    def update(self, dt: float) -> None:
        """Ticks active trap cooldown timers."""
        for trap in self.placed_traps.values():
            if trap.cooldown_timer > 0:
                trap.cooldown_timer -= dt
                if trap.cooldown_timer <= 0:
                    trap.cooldown_timer = 0.0

    def trigger_traps_for_entity(self, entity: Any, floor: int = 1) -> int:
        """
        Checks entity collision against all placed traps on the floor.
        Triggers damage and cooldowns when stepped on.
        """
        if not hasattr(entity, "hitbox") and not hasattr(entity, "rect"):
            return 0

        entity_rect = getattr(entity, "hitbox", getattr(entity, "rect", None))
        if entity_rect is None:
            return 0

        total_damage = 0
        for trap in self.get_traps_for_floor(floor):
            if not trap.is_active or trap.cooldown_timer > 0:
                continue

            if trap.rect.colliderect(entity_rect):
                bp = self.blueprints.get(trap.trap_type)
                if not bp:
                    continue

                damage = bp.damage
                if hasattr(entity, "take_damage"):
                    entity.take_damage(damage)

                trap.cooldown_timer = bp.cooldown
                total_damage += damage
                self.total_traps_triggered += 1
                self.total_damage_dealt += damage

                if self.event_bus:
                    self.event_bus.emit(
                        "dungeon_trap_triggered",
                        trap_id=trap.trap_id,
                        trap_type=trap.trap_type,
                        damage=damage,
                        floor=floor
                    )

        return total_damage

    def can_capture_enemy(self, enemy: Any) -> Tuple[bool, str]:
        """
        Validates if an enemy can be captured with a Beast Capture Net.
        Criteria: Dungeon Core claimed, non-boss enemy, and HP <= 20% max HP.
        """
        if not self.core_claimed:
            return False, "Must claim the Dungeon Core Stone before capturing dungeon beasts."

        if getattr(enemy, "is_boss", False) or "boss" in getattr(enemy, "enemy_type", "").lower():
            return False, "Boss monsters and ancient lords are immune to capture nets."

        max_hp = getattr(enemy, "max_hp", 100.0)
        curr_hp = getattr(enemy, "hp", 100.0)

        if max_hp <= 0:
            return False, "Invalid target."

        if curr_hp / max_hp > 0.20:
            pct = int((curr_hp / max_hp) * 100)
            return False, f"Target is too strong ({pct}% HP). Weaken the beast below 20% HP to ensnare!"

        return True, "Target is sufficiently weakened and ready for capture!"

    def capture_enemy(self, enemy: Any, player: Any) -> Tuple[bool, str]:
        """
        Captures a weakened wild monster using a Beast Capture Net from inventory.
        """
        can_cap, reason = self.can_capture_enemy(enemy)
        if not can_cap:
            return False, reason

        # Check inventory for Beast Capture Net
        has_net = False
        if hasattr(player, "inventory") and player.inventory:
            for net_name in ["Beast Capture Net", "beast_capture_net"]:
                if player.inventory.has_item(net_name, 1):
                    player.inventory.remove_item(net_name, 1)
                    has_net = True
                    break

        if not has_net:
            return False, "No Beast Capture Net in inventory. Craft one at the Blacksmith!"

        monster_type = getattr(enemy, "enemy_type", getattr(enemy, "name", "wild_beast")).lower()
        monster_id = f"captured_{monster_type}_{len(self.captured_monsters) + 1}"
        name = f"Domesticated {monster_type.replace('_', ' ').title()}"
        max_hp = float(getattr(enemy, "max_hp", 60.0))
        atk = float(getattr(enemy, "atk", 14.0))
        level = getattr(enemy, "level", 1)

        captured = CapturedMonster(
            monster_id=monster_id,
            monster_type=monster_type,
            name=name,
            level=level,
            hp=max_hp,
            max_hp=max_hp,
            atk=atk
        )
        self.captured_monsters[monster_id] = captured

        # Despawn wild enemy and award capture EXP
        if hasattr(enemy, "kill"):
            enemy.kill()

        if hasattr(player, "add_exp"):
            player.add_exp(25)

        if self.event_bus:
            self.event_bus.emit(
                "beast_captured",
                monster_id=monster_id,
                monster_type=monster_type,
                name=name
            )

        return True, f"Successfully captured {name} with Beast Capture Net! Added to dungeon reserve roster."

    def assign_monster_to_room(
        self,
        monster_id: str,
        grid_x: int,
        grid_y: int,
        floor: int = 1
    ) -> Tuple[bool, str]:
        """
        Stations a domesticated monster in a specific dungeon chamber.
        """
        if monster_id not in self.captured_monsters:
            return False, f"Domesticated monster '{monster_id}' not found."

        monster = self.captured_monsters[monster_id]
        monster.assigned_grid_x = grid_x
        monster.assigned_grid_y = grid_y
        monster.assigned_floor = floor
        monster.is_stationed = True

        if self.event_bus:
            self.event_bus.emit(
                "monster_stationed",
                monster_id=monster_id,
                grid_x=grid_x,
                grid_y=grid_y,
                floor=floor
            )

        return True, f"Stationed {monster.name} at chamber ({grid_x}, {grid_y}) on Floor {floor}."

    def unassign_monster(self, monster_id: str) -> Tuple[bool, str]:
        """Recalls a stationed guardian monster back to the reserve roster."""
        if monster_id not in self.captured_monsters:
            return False, f"Domesticated monster '{monster_id}' not found."

        monster = self.captured_monsters[monster_id]
        monster.assigned_grid_x = None
        monster.assigned_grid_y = None
        monster.assigned_floor = None
        monster.is_stationed = False

        if self.event_bus:
            self.event_bus.emit("monster_unassigned", monster_id=monster_id)

        return True, f"Recalled {monster.name} back to reserve roster."

    def get_stationed_monsters(self, floor: int = 1) -> List[CapturedMonster]:
        """Returns all domesticated monsters stationed on the specified floor."""
        return [m for m in self.captured_monsters.values() if m.is_stationed and m.assigned_floor == floor]

    def get_dungeon_defense_rating(self, floor: int = 1) -> int:
        """Calculates total architectural and guardian defense score for the specified floor."""
        traps = self.get_traps_for_floor(floor)
        trap_score = sum(self.blueprints[t.trap_type].damage for t in traps if t.trap_type in self.blueprints)
        types_count = len(set(t.trap_type for t in traps))
        diversity_multiplier = 1.0 + (types_count * 0.15)
        architectural_defense = int(trap_score * diversity_multiplier)

        # Stationed Guardian ATK contribution
        guardians = self.get_stationed_monsters(floor)
        guardian_defense = sum(int(g.atk * 2.0) for g in guardians)

        return architectural_defense + guardian_defense

    def trigger_daily_invasion(self, day: int = 1, nemesis_name: str = "") -> Optional[Dict[str, Any]]:
        """
        Periodically triggers an AI adventurer/bandit invasion every 3 in-game days.
        """
        if not self.core_claimed or day < 3:
            return None

        if (day - self.last_invasion_day) < self.invasion_interval_days:
            return None

        self.last_invasion_day = day

        # Determine invading party composition
        if nemesis_name:
            raider_name = f"Nemesis Warband of {nemesis_name}"
            raider_type = "Nemesis Outlaws"
        else:
            raider_name = "Rival Adventurers (Seekers of Valen)"
            raider_type = "Rival Adventurers"

        raider_power = 60 + (day * 10)
        raider_count = 3 + min(5, day // 3)
        loot_bounty = 60 + (day * 5)
        materials_bounty = {"Iron Ore": 2, "Timber": 2, "Beast Leather": 2}

        self.active_invasion = {
            "day": day,
            "raider_name": raider_name,
            "raider_type": raider_type,
            "raider_power": raider_power,
            "raider_count": raider_count,
            "loot_bounty": loot_bounty,
            "materials_bounty": materials_bounty
        }

        if self.event_bus:
            self.event_bus.emit(
                "dungeon_invasion_triggered",
                day=day,
                raider_name=raider_name,
                raider_type=raider_type,
                raider_power=raider_power,
                raider_count=raider_count
            )

        return self.active_invasion

    def simulate_invasion_defense(self, player: Any, floor: int = 1) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Resolves an active invasion by comparing dungeon defense rating against raider power.
        Awards gold, infamy, and materials on success; penalizes gold on breach.
        """
        if not self.active_invasion:
            return False, "No active invasion threatening the dungeon.", {}

        defense_rating = self.get_dungeon_defense_rating(floor)
        raider_power = self.active_invasion["raider_power"]
        raider_name = self.active_invasion["raider_name"]
        gold_bounty = self.active_invasion["loot_bounty"]

        if defense_rating >= raider_power:
            # --- DEFENSE VICTORY ---
            infamy_gain = 30
            self.dungeon_infamy += infamy_gain
            self.total_invasions_repelled += 1

            if hasattr(player, "gold"):
                player.gold += gold_bounty

            if hasattr(player, "inventory") and player.inventory:
                from rpg.items import create_item
                for mat_name, qty in self.active_invasion.get("materials_bounty", {}).items():
                    item = create_item(mat_name, qty)
                    if item:
                        player.inventory.add_item(item)

            self.active_invasion = None

            if self.event_bus:
                self.event_bus.emit(
                    "dungeon_invasion_repelled",
                    raider_name=raider_name,
                    gold_reward=gold_bounty,
                    infamy_gain=infamy_gain
                )

            return True, f"Dungeon defenses held! Repelled {raider_name} and seized {gold_bounty} Gold in salvage!", {
                "gold": gold_bounty,
                "infamy": infamy_gain,
                "defense_rating": defense_rating,
                "raider_power": raider_power
            }

        else:
            # --- DEFENSE BREACH ---
            plundered_gold = min(getattr(player, "gold", 0), 20)
            self.total_invasions_failed += 1

            if hasattr(player, "gold"):
                player.gold -= plundered_gold

            self.active_invasion = None

            if self.event_bus:
                self.event_bus.emit(
                    "dungeon_invasion_breached",
                    raider_name=raider_name,
                    plundered_gold=plundered_gold
                )

            return False, f"Defenses breached by {raider_name}! Invaders plundered {plundered_gold} Gold before retreating.", {
                "plundered_gold": plundered_gold,
                "defense_rating": defense_rating,
                "raider_power": raider_power
            }

    def expand_dungeon_floor(self, player: Any) -> Tuple[bool, str]:
        """
        Excavates and unlocks the next subterranean dungeon floor down to Floor 3 (Abyssal Vaults).
        Requires sufficient Gold and Dungeon Infamy accumulated by repelling raider assaults.
        """
        if not self.core_claimed:
            return False, "Must claim the Dungeon Core Stone before excavating deeper crypt floors."

        next_floor = self.max_unlocked_floor + 1
        if next_floor > MAX_DUNGEON_FLOORS:
            return False, "All subterranean crypt floors (up to Floor 3: Abyssal Vaults) have already been excavated!"

        req_gold, req_infamy = FLOOR_UNLOCK_COSTS[next_floor]

        if self.dungeon_infamy < req_infamy:
            return False, f"Requires {req_infamy} Dungeon Infamy to excavate {FLOOR_NAMES[next_floor]} (Current: {self.dungeon_infamy}). Repel raider invasions to raise your infamy!"

        curr_gold = getattr(player, "gold", 0)
        if curr_gold < req_gold:
            return False, f"Requires {req_gold} Gold to excavate {FLOOR_NAMES[next_floor]} (Current: {curr_gold}g)."

        # Deduct gold and unlock floor
        if hasattr(player, "gold"):
            player.gold -= req_gold

        self.max_unlocked_floor = next_floor
        self.current_floor = next_floor
        floor_title = FLOOR_NAMES[next_floor]

        # Milestone Climax: Floor 3 unlocks the ultimate Sovereign title & Mythos chronicle
        if self.max_unlocked_floor == 3:
            if hasattr(player, "titles") and isinstance(player.titles, set):
                player.titles.add("The Lord of the Deep Catacombs")

            if self.event_bus:
                self.event_bus.emit(
                    "dungeon_sovereignty_established",
                    title="The Lord of the Deep Catacombs",
                    floor=3
                )

        if self.event_bus:
            self.event_bus.emit(
                "dungeon_floor_unlocked",
                floor=next_floor,
                floor_name=floor_title
            )

        return True, f"Successfully excavated Floor {next_floor}: {floor_title}! Expanded dungeon architect capacity."

    def switch_floor(self, floor: int) -> Tuple[bool, str]:
        """Switches the active dungeon architect view to the specified floor."""
        if 1 <= floor <= self.max_unlocked_floor:
            self.current_floor = floor
            return True, f"Switched architect view to Floor {floor}: {FLOOR_NAMES.get(floor, '')}."
        return False, f"Floor {floor} is not unlocked yet (Max unlocked: Floor {self.max_unlocked_floor})."

    def get_floor_name(self, floor: int) -> str:
        """Returns the narrative title for the specified floor index."""
        return FLOOR_NAMES.get(floor, f"Floor {floor}")

    def get_total_dungeon_defense_rating(self) -> int:
        """Calculates total composite defense rating across all unlocked subterranean floors."""
        return sum(self.get_dungeon_defense_rating(f) for f in range(1, self.max_unlocked_floor + 1))

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Dungeon Architect state for save files."""
        return {
            "core_claimed": self.core_claimed,
            "current_floor": self.current_floor,
            "max_unlocked_floor": self.max_unlocked_floor,
            "placed_traps": {k: t.to_dict() for k, t in self.placed_traps.items()},
            "captured_monsters": {k: m.to_dict() for k, m in self.captured_monsters.items()},
            "total_traps_triggered": self.total_traps_triggered,
            "total_damage_dealt": self.total_damage_dealt,
            "dungeon_infamy": self.dungeon_infamy,
            "last_invasion_day": self.last_invasion_day,
            "active_invasion": self.active_invasion,
            "total_invasions_repelled": self.total_invasions_repelled,
            "total_invasions_failed": self.total_invasions_failed
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores Dungeon Architect state from save files."""
        if not isinstance(data, dict):
            return

        self.core_claimed = data.get("core_claimed", False)
        self.current_floor = data.get("current_floor", 1)
        self.max_unlocked_floor = data.get("max_unlocked_floor", 1)
        self.total_traps_triggered = data.get("total_traps_triggered", 0)
        self.total_damage_dealt = data.get("total_damage_dealt", 0)
        self.dungeon_infamy = data.get("dungeon_infamy", 0)
        self.last_invasion_day = data.get("last_invasion_day", 0)
        self.active_invasion = data.get("active_invasion")
        self.total_invasions_repelled = data.get("total_invasions_repelled", 0)
        self.total_invasions_failed = data.get("total_invasions_failed", 0)

        self.placed_traps = {}
        pt = data.get("placed_traps", {})
        if isinstance(pt, dict):
            for k, t_data in pt.items():
                self.placed_traps[k] = PlacedTrap.from_dict(t_data)

        self.captured_monsters = {}
        cm = data.get("captured_monsters", {})
        if isinstance(cm, dict):
            for k, m_data in cm.items():
                self.captured_monsters[k] = CapturedMonster.from_dict(m_data)


