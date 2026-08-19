"""
Echoes of Asterra - Outpost Commander & Sovereign Caravans System (Pillar #3)
Manages strategic outpost construction at faction control points, guard garrisons,
daily toll taxation from passing trade caravans, regional stability locks,
multi-tier outpost upgrades (Levels 1-3), Automated Courier Relays, and Continental Trade Monopoly.
"""
import pygame
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

from rpg.settings import TILE_SIZE
from rpg.sprite import BaseSprite
from rpg.events import EventBus

OUTPOST_COST_GOLD = 100
OUTPOST_MIN_STABILITY = 70.0

OUTPOST_UPGRADE_COST_LVL2 = 150
OUTPOST_UPGRADE_COST_LVL3 = 300

OUTPOST_TOLL_LVL1 = 10
OUTPOST_DAILY_TOLL = OUTPOST_TOLL_LVL1
OUTPOST_TOLL_LVL2 = 25
OUTPOST_TOLL_LVL3 = 50

OUTPOST_GARRISON_LVL1 = 2
OUTPOST_GARRISON_LVL2 = 3
OUTPOST_GARRISON_LVL3 = 4

OUTPOST_TACTICAL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "forest_crossroads": {
        "name": "Forest Crossroads Outpost",
        "map_name": "forest",
        "tower_pos": (16 * TILE_SIZE, 12 * TILE_SIZE),
        "guard_positions": [
            (15 * TILE_SIZE, 12 * TILE_SIZE),
            (17 * TILE_SIZE, 12 * TILE_SIZE),
            (15 * TILE_SIZE, 14 * TILE_SIZE),
            (17 * TILE_SIZE, 14 * TILE_SIZE)
        ]
    },
    "cave_depths": {
        "name": "Cave Depths Outpost",
        "map_name": "cave",
        "tower_pos": (8 * TILE_SIZE, 7 * TILE_SIZE),
        "guard_positions": [
            (7 * TILE_SIZE, 7 * TILE_SIZE),
            (9 * TILE_SIZE, 7 * TILE_SIZE),
            (7 * TILE_SIZE, 9 * TILE_SIZE),
            (9 * TILE_SIZE, 9 * TILE_SIZE)
        ]
    },
    "ruins_plaza": {
        "name": "Ruins Plaza Outpost",
        "map_name": "ruins",
        "tower_pos": (15 * TILE_SIZE, 13 * TILE_SIZE),
        "guard_positions": [
            (14 * TILE_SIZE, 13 * TILE_SIZE),
            (16 * TILE_SIZE, 13 * TILE_SIZE),
            (14 * TILE_SIZE, 15 * TILE_SIZE),
            (16 * TILE_SIZE, 15 * TILE_SIZE)
        ]
    },
    "lake_pier": {
        "name": "Lake Pier Outpost",
        "map_name": "lake",
        "tower_pos": (15 * TILE_SIZE, 10 * TILE_SIZE),
        "guard_positions": [
            (14 * TILE_SIZE, 10 * TILE_SIZE),
            (16 * TILE_SIZE, 10 * TILE_SIZE),
            (14 * TILE_SIZE, 12 * TILE_SIZE),
            (16 * TILE_SIZE, 12 * TILE_SIZE)
        ]
    }
}


@dataclass
class OutpostData:
    """Represents a strategic fortified outpost constructed at a territory control point."""
    outpost_id: str
    name: str
    control_point_id: str
    map_name: str
    is_built: bool = False
    level: int = 1
    unclaimed_toll_gold: int = 0
    total_toll_collected: int = 0
    daily_toll_income: int = OUTPOST_TOLL_LVL1
    garrison_count: int = OUTPOST_GARRISON_LVL1
    caravan_arrivals_count: int = 0
    has_automated_courier: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outpost_id": self.outpost_id,
            "name": self.name,
            "control_point_id": self.control_point_id,
            "map_name": self.map_name,
            "is_built": self.is_built,
            "level": self.level,
            "unclaimed_toll_gold": self.unclaimed_toll_gold,
            "total_toll_collected": self.total_toll_collected,
            "daily_toll_income": self.daily_toll_income,
            "garrison_count": self.garrison_count,
            "caravan_arrivals_count": self.caravan_arrivals_count,
            "has_automated_courier": self.has_automated_courier
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OutpostData":
        return cls(
            outpost_id=data.get("outpost_id", ""),
            name=data.get("name", "Fortified Outpost"),
            control_point_id=data.get("control_point_id", ""),
            map_name=data.get("map_name", "forest"),
            is_built=data.get("is_built", False),
            level=int(data.get("level", 1)),
            unclaimed_toll_gold=int(data.get("unclaimed_toll_gold", 0)),
            total_toll_collected=int(data.get("total_toll_collected", 0)),
            daily_toll_income=int(data.get("daily_toll_income", OUTPOST_TOLL_LVL1)),
            garrison_count=int(data.get("garrison_count", OUTPOST_GARRISON_LVL1)),
            caravan_arrivals_count=int(data.get("caravan_arrivals_count", 0)),
            has_automated_courier=bool(data.get("has_automated_courier", False))
        )


class OutpostManager:
    """
    Coordinates player-built military outposts across Asterra's territory control points.
    Locks regional stability against decay, collects daily merchant tolls, maintains garrisons,
    and manages multi-tier upgrades to achieve the Continental Trade Monopoly.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.outposts: Dict[str, OutpostData] = {}
        self.continental_monopoly_achieved: bool = False
        self.game_reference: Any = None
        self.reset()

        if self.event_bus:
            self.event_bus.subscribe("day_changed", self._on_day_changed)

    def reset(self) -> None:
        """Resets all outposts to unbuilt initial state."""
        self.outposts.clear()
        self.continental_monopoly_achieved = False
        for cp_id, config in OUTPOST_TACTICAL_CONFIGS.items():
            self.outposts[cp_id] = OutpostData(
                outpost_id=f"outpost_{cp_id}",
                name=config["name"],
                control_point_id=cp_id,
                map_name=config["map_name"],
                is_built=False,
                level=1,
                unclaimed_toll_gold=0,
                total_toll_collected=0,
                daily_toll_income=OUTPOST_TOLL_LVL1,
                garrison_count=OUTPOST_GARRISON_LVL1,
                has_automated_courier=False
            )

    def has_outpost(self, cp_id: str) -> bool:
        """Returns True if a fortified outpost is built and active at the given control point."""
        return bool(cp_id in self.outposts and self.outposts[cp_id].is_built)

    def get_level_3_outposts_count(self) -> int:
        """Returns count of outposts that have reached Level 3 (Trade Citadels)."""
        return sum(1 for o in self.outposts.values() if o.is_built and o.level >= 3)

    def can_build_outpost(self, cp_id: str, player: Any, faction_war: Any = None) -> Tuple[bool, str]:
        """Validates if requirements are met to construct a new outpost."""
        if cp_id not in self.outposts:
            return False, f"Unknown control point '{cp_id}'."

        outpost = self.outposts[cp_id]
        if outpost.is_built:
            return False, f"{outpost.name} has already been constructed."

        # Check stability via faction_war
        fw = faction_war
        if not fw and self.game_reference:
            fw = getattr(self.game_reference, "faction_war", None) or getattr(self.game_reference, "living_world", None)
            if hasattr(fw, "faction_war"):
                fw = fw.faction_war

        if fw and hasattr(fw, "control_points") and cp_id in fw.control_points:
            cp = fw.control_points[cp_id]
            if cp.stability < OUTPOST_MIN_STABILITY:
                return False, f"Territory stability is too low ({int(cp.stability)}% / {int(OUTPOST_MIN_STABILITY)}% required). Clear monsters or secure faction standing first!"

        p_gold = getattr(player, "gold", 0)
        if p_gold < OUTPOST_COST_GOLD:
            return False, f"Insufficient gold! Construction costs {OUTPOST_COST_GOLD}g (You have {p_gold}g)."

        return True, "Ready for construction."

    def build_outpost(self, cp_id: str, player: Any, faction_war: Any = None) -> Tuple[bool, str]:
        """Constructs a Level 1 fortified outpost at the specified control point."""
        can_build, reason = self.can_build_outpost(cp_id, player, faction_war)
        if not can_build:
            return False, reason

        if hasattr(player, "gold"):
            player.gold -= OUTPOST_COST_GOLD

        outpost = self.outposts[cp_id]
        outpost.is_built = True
        outpost.level = 1
        outpost.daily_toll_income = OUTPOST_TOLL_LVL1
        outpost.garrison_count = OUTPOST_GARRISON_LVL1

        # Lock control point stability to 100%
        fw = faction_war
        if not fw and self.game_reference:
            fw = getattr(self.game_reference, "faction_war", None) or getattr(self.game_reference, "living_world", None)
            if hasattr(fw, "faction_war"):
                fw = fw.faction_war

        if fw and hasattr(fw, "control_points") and cp_id in fw.control_points:
            cp = fw.control_points[cp_id]
            cp.stability = 100.0
            cp.contested = False

        if self.event_bus:
            self.event_bus.emit(
                "outpost_constructed",
                outpost_id=outpost.outpost_id,
                name=outpost.name,
                control_point_id=cp_id,
                map_name=outpost.map_name
            )

        return True, f"Successfully established {outpost.name}! 2 hired guards have been garrisoned, and caravan tolls are active."

    def can_upgrade_outpost(self, cp_id: str, player: Any) -> Tuple[bool, str]:
        """Validates whether an existing outpost can be upgraded to the next tier."""
        if cp_id not in self.outposts or not self.outposts[cp_id].is_built:
            return False, "No constructed outpost found at this location."

        outpost = self.outposts[cp_id]
        if outpost.level >= 3:
            return False, f"{outpost.name} is already at maximum fortification tier (Level 3 Trade Citadel)."

        next_level = outpost.level + 1
        upgrade_cost = OUTPOST_UPGRADE_COST_LVL2 if next_level == 2 else OUTPOST_UPGRADE_COST_LVL3

        p_gold = getattr(player, "gold", 0)
        if p_gold < upgrade_cost:
            return False, f"Insufficient gold! Upgrading to Level {next_level} costs {upgrade_cost}g (You have {p_gold}g)."

        return True, f"Ready to upgrade to Level {next_level} for {upgrade_cost}g."

    def upgrade_outpost(self, cp_id: str, player: Any) -> Tuple[bool, str]:
        """
        Upgrades an outpost:
        - Level 2 (150g): Fortified Bastion & Ballistas (+25g daily toll, 3 garrison guards).
        - Level 3 (300g): Grand Trade Citadel & Automated Courier Relays (+50g daily toll, 4 garrison guards, auto-deposit dividends).
        Reaching 3+ Level 3 outposts unlocks the Continental Trade Monopoly triumph!
        """
        can_up, reason = self.can_upgrade_outpost(cp_id, player)
        if not can_up:
            return False, reason

        outpost = self.outposts[cp_id]
        next_level = outpost.level + 1
        cost = OUTPOST_UPGRADE_COST_LVL2 if next_level == 2 else OUTPOST_UPGRADE_COST_LVL3

        if hasattr(player, "gold"):
            player.gold -= cost

        outpost.level = next_level
        if next_level == 2:
            outpost.daily_toll_income = OUTPOST_TOLL_LVL2
            outpost.garrison_count = OUTPOST_GARRISON_LVL2
            upgrade_title = "Fortified Bastion & Ballistas"
        else:
            outpost.daily_toll_income = OUTPOST_TOLL_LVL3
            outpost.garrison_count = OUTPOST_GARRISON_LVL3
            outpost.has_automated_courier = True
            upgrade_title = "Trade Citadel & Automated Courier Relay"

        if self.event_bus:
            self.event_bus.emit(
                "outpost_upgraded",
                outpost_id=outpost.outpost_id,
                name=outpost.name,
                level=outpost.level,
                daily_toll=outpost.daily_toll_income,
                garrison_count=outpost.garrison_count
            )

        # Check Continental Trade Monopoly (3+ Level 3 outposts)
        if self.get_level_3_outposts_count() >= 3 and not self.continental_monopoly_achieved:
            self.continental_monopoly_achieved = True
            title = "Merchant Sovereign of Asterra"
            if hasattr(player, "title"):
                player.title = title

            if self.event_bus:
                self.event_bus.emit(
                    "continental_trade_monopoly_achieved",
                    title=title,
                    level_3_count=self.get_level_3_outposts_count()
                )

        return True, f"Successfully upgraded {outpost.name} to Level {outpost.level} ({upgrade_title})! Daily toll increased to {outpost.daily_toll_income}g."

    def collect_toll(self, cp_id: str, player: Any) -> Tuple[int, str]:
        """Collects accumulated caravan toll taxes from an outpost."""
        if cp_id not in self.outposts or not self.outposts[cp_id].is_built:
            return 0, "No active outpost found at this location."

        outpost = self.outposts[cp_id]
        gold_amount = outpost.unclaimed_toll_gold
        if gold_amount <= 0:
            return 0, f"No unclaimed caravan tolls available at {outpost.name}."

        outpost.unclaimed_toll_gold = 0
        outpost.total_toll_collected += gold_amount

        if hasattr(player, "gain_gold"):
            player.gain_gold(gold_amount)
        elif hasattr(player, "gold"):
            player.gold += gold_amount

        if self.event_bus:
            self.event_bus.emit(
                "outpost_toll_collected",
                outpost_id=outpost.outpost_id,
                amount=gold_amount,
                total=outpost.total_toll_collected
            )

        return gold_amount, f"Collected {gold_amount}g in trade caravan tolls from {outpost.name}!"

    def collect_all_tolls(self, player: Any) -> Tuple[int, str]:
        """Collects all unclaimed caravan tolls across all constructed outposts."""
        total_collected = 0
        collected_outposts = 0
        for cp_id, outpost in self.outposts.items():
            if outpost.is_built and outpost.unclaimed_toll_gold > 0:
                gold = outpost.unclaimed_toll_gold
                outpost.unclaimed_toll_gold = 0
                outpost.total_toll_collected += gold
                total_collected += gold
                collected_outposts += 1

        if total_collected > 0:
            if hasattr(player, "gain_gold"):
                player.gain_gold(total_collected)
            elif hasattr(player, "gold"):
                player.gold += total_collected

            if self.event_bus:
                self.event_bus.emit(
                    "outpost_all_tolls_collected",
                    amount=total_collected,
                    outpost_count=collected_outposts
                )
            return total_collected, f"Collected a total of {total_collected}g in trade tolls across {collected_outposts} outposts!"

        return 0, "No unclaimed caravan tolls currently available."

    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        """
        Accrues daily trade caravan tolls, executes automated courier relay direct deposits
        for Level 3 outposts, and preserves regional stability.
        """
        player = getattr(self.game_reference, "player", None) if self.game_reference else None

        for outpost in self.outposts.values():
            if outpost.is_built:
                if outpost.has_automated_courier or outpost.level >= 3:
                    # Automated Courier Relay: directly deposit to player's bank
                    if player:
                        if hasattr(player, "gain_gold"):
                            player.gain_gold(outpost.daily_toll_income)
                        elif hasattr(player, "gold"):
                            player.gold += outpost.daily_toll_income
                        outpost.total_toll_collected += outpost.daily_toll_income
                else:
                    outpost.unclaimed_toll_gold += outpost.daily_toll_income

        # Enforce stability lock on faction war control points
        if self.game_reference:
            fw = getattr(self.game_reference, "faction_war", None) or getattr(self.game_reference, "living_world", None)
            if hasattr(fw, "faction_war"):
                fw = fw.faction_war
            if fw and hasattr(fw, "control_points"):
                for cp_id, outpost in self.outposts.items():
                    if outpost.is_built and cp_id in fw.control_points:
                        cp = fw.control_points[cp_id]
                        cp.stability = max(cp.stability, 85.0)
                        cp.contested = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes outpost states for savegame."""
        return {
            "outposts": {k: v.to_dict() for k, v in self.outposts.items()},
            "continental_monopoly_achieved": self.continental_monopoly_achieved
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores outpost states from savegame."""
        if not isinstance(data, dict):
            return
        raw_outposts = data.get("outposts", {})
        if isinstance(raw_outposts, dict):
            for k, v in raw_outposts.items():
                if k in self.outposts:
                    self.outposts[k] = OutpostData.from_dict(v)
                else:
                    self.outposts[k] = OutpostData.from_dict(v)
        self.continental_monopoly_achieved = bool(data.get("continental_monopoly_achieved", False))


class OutpostTowerSprite(BaseSprite):
    """
    Interactable fortified stone watchtower rendered on world maps.
    Visual aesthetics evolve with multi-tier upgrades (Lvl 1 Watchtower -> Lvl 2 Bastion -> Lvl 3 Citadel).
    """
    def __init__(self, pos: Tuple[int, int], cp_id: str, groups: List[pygame.sprite.Group], level: int = 1) -> None:
        super().__init__((float(pos[0] + 24), float(pos[1] + 32)), groups, layer=1)
        self.grid_pos = pos
        self.cp_id = cp_id
        self.level = level
        self.image = pygame.Surface((48, 64), pygame.SRCALPHA)
        self._render_procedural_tower()
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = pygame.Rect(pos[0] + 4, pos[1] + 28, 40, 32)
        self.game: Any = None

    def _render_procedural_tower(self) -> None:
        """Renders fortified stone watchtower texture scaling with upgrade level."""
        self.image.fill((0, 0, 0, 0))
        # Main stone wall tower
        base_color = (70, 75, 85) if self.level == 1 else ((60, 65, 80) if self.level == 2 else (85, 80, 100))
        inner_color = (95, 100, 115) if self.level == 1 else ((115, 120, 140) if self.level == 2 else (145, 135, 165))
        pygame.draw.rect(self.image, base_color, (4, 12, 40, 50), border_radius=4)
        pygame.draw.rect(self.image, inner_color, (6, 14, 36, 46), border_radius=3)

        # Stone brick highlights
        for y in range(18, 55, 8):
            pygame.draw.line(self.image, (50, 55, 65), (6, y), (41, y), 1)

        # Wooden arched entrance gate
        pygame.draw.rect(self.image, (85, 55, 30), (16, 40, 16, 22), border_radius=4)
        pygame.draw.rect(self.image, (45, 25, 15), (18, 42, 12, 18), border_radius=3)

        # Top stone battlements / crenellations
        pygame.draw.rect(self.image, (110, 115, 130), (2, 4, 44, 10), border_radius=2)
        for x in [4, 16, 28, 40]:
            pygame.draw.rect(self.image, (125, 130, 145), (x, 0, 6, 6))

        if self.level == 1:
            # Blue/Gold Royal Outpost Banner
            pygame.draw.rect(self.image, (30, 90, 200), (22, 16, 8, 14))
            pygame.draw.polygon(self.image, (30, 90, 200), [(22, 30), (30, 30), (26, 35)])
            pygame.draw.line(self.image, (255, 215, 0), (22, 16), (29, 16), 2)
        elif self.level == 2:
            # Level 2 Bastion: Ballistas on battlements + Golden Crest
            pygame.draw.rect(self.image, (180, 100, 30), (6, 2, 8, 4))
            pygame.draw.rect(self.image, (180, 100, 30), (34, 2, 8, 4))
            pygame.draw.circle(self.image, (255, 215, 0), (24, 22), 5)
        else:
            # Level 3 Citadel: Radiant Golden Spire & Courier Relay Flag
            pygame.draw.polygon(self.image, (255, 215, 0), [(24, -6), (18, 4), (30, 4)])
            pygame.draw.circle(self.image, (0, 240, 255), (24, -2), 3)
            # Emerald Courier Pennant
            pygame.draw.polygon(self.image, (50, 220, 100), [(30, 4), (44, 10), (30, 16)])

    def interact(self, player: Any) -> Optional[str]:
        """Interacts with the outpost tower to claim tolls or inspect garrison."""
        if not self.game or not hasattr(self.game, "outpost_manager"):
            return None

        om: OutpostManager = self.game.outpost_manager
        outpost = om.outposts.get(self.cp_id)
        if not outpost or not outpost.is_built:
            return None

        from rpg.combat import DamageNumber
        if outpost.has_automated_courier or outpost.level >= 3:
            msg = f"{outpost.name} (Lvl 3 Trade Citadel): Automated Courier Relay Active. Daily tolls ({outpost.daily_toll_income}g/day) deposited directly to your purse!"
            DamageNumber(self.rect.center, "💎 COURIER RELAY ACTIVE", (0, 240, 255), [self.game.ui_sprites], size=14)
            return msg
        elif outpost.unclaimed_toll_gold > 0:
            gold, msg = om.collect_toll(self.cp_id, player)
            DamageNumber(self.rect.center, f"+{gold}g CARAVAN TOLLS!", (255, 215, 0), [self.game.ui_sprites], size=16)
            if hasattr(self.game, "sound_manager"):
                self.game.sound_manager.play_sound("coin")
            return msg
        else:
            msg = f"{outpost.name} (Lvl {outpost.level}): Garrison Active ({outpost.garrison_count} Guards). No pending tolls."
            DamageNumber(self.rect.center, "🛡️ GARRISON SECURE", (100, 220, 255), [self.game.ui_sprites], size=14)
            return msg


from rpg.npc import NPC

class OutpostGuardNPC(NPC):
    """Stationed sentry guarding the outpost perimeter and saluting the player Commander."""
    def __init__(self, pos: Tuple[float, float], groups: List[pygame.sprite.Group] = None, name: str = "Outpost Sentry") -> None:
        super().__init__(pos, groups or [], name=name, asset_key="guard_village", can_wander=False)

    def interact(self, player: Any = None) -> str:
        """Salutes the player with military outpost greetings."""
        from rpg.combat import DamageNumber
        if self.game and hasattr(self.game, "ui_sprites"):
            DamageNumber(self.rect.center, "⚔️ 'At your command!'", (200, 230, 255), [self.game.ui_sprites], size=12)
        return f"Greetings, Commander! The roads around this outpost remain safe under our watch."
