"""
Echoes of Asterra - Companion Recruitment & Autonomous Expedition System (Fitur #2)
Provides customizable party companions (Ranger Faye, Guard Kai, Scholar Mira)
with combat support AI modes (Attack, Tank, Heal), level progression, contextual dialogue banter,
and autonomous resource expeditions across Asterra's zones.
"""
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

from rpg.events import EventBus
from rpg.constants import (
    REL_ENEMY, REL_STRANGER, REL_ACQUAINTANCE, REL_FRIEND, REL_CLOSE_FRIEND,
    COLOR_WHITE, COLOR_GOLD, COLOR_GREEN, COLOR_BLUE, COLOR_RED, COLOR_GRAY,
    COLOR_UI_BG, COLOR_UI_BORDER, COLOR_CYAN
)

logger = logging.getLogger("CompanionSystem")

# Tactical Combat Modes
MODE_ATTACK = "attack"
MODE_TANK = "tank"
MODE_HEAL = "heal"
VALID_MODES = [MODE_ATTACK, MODE_TANK, MODE_HEAL]

# Expedition Zones & Target Multipliers
EXPEDITION_ZONES = {
    "forest": {"name": "Emerald Forest", "risk": 15, "gold_mult": 1.0, "items": ["Herb", "Iron Ore", "Wolf Pelt"]},
    "cave": {"name": "Gloom Caverns", "risk": 35, "gold_mult": 1.5, "items": ["Silver Ore", "Crystal Shard", "Bat Wing"]},
    "ruins": {"name": "Sunken Ruins", "risk": 55, "gold_mult": 2.2, "items": ["Ancient Core", "Gold Ore", "Arcane Dust"]},
    "dungeon": {"name": "Deep Crypt", "risk": 75, "gold_mult": 3.0, "items": ["Starlight Crystal", "Rune Fragment", "Elixir of Life"]}
}


@dataclass
class ExpeditionData:
    """State for an autonomous resource expedition."""
    zone: str = "forest"
    days_remaining: int = 0
    total_days: int = 1
    is_completed: bool = False
    rewards_gold: int = 0
    rewards_items: List[str] = field(default_factory=list)
    damage_taken: int = 0
    xp_gained: int = 0
    status_summary: str = "Ready for dispatch"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone": self.zone,
            "days_remaining": self.days_remaining,
            "total_days": self.total_days,
            "is_completed": self.is_completed,
            "rewards_gold": self.rewards_gold,
            "rewards_items": list(self.rewards_items),
            "damage_taken": self.damage_taken,
            "xp_gained": self.xp_gained,
            "status_summary": self.status_summary
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExpeditionData':
        if not data:
            return cls()
        return cls(
            zone=data.get("zone", "forest"),
            days_remaining=data.get("days_remaining", 0),
            total_days=data.get("total_days", 1),
            is_completed=data.get("is_completed", False),
            rewards_gold=data.get("rewards_gold", 0),
            rewards_items=list(data.get("rewards_items", [])),
            damage_taken=data.get("damage_taken", 0),
            xp_gained=data.get("xp_gained", 0),
            status_summary=data.get("status_summary", "Ready for dispatch")
        )


@dataclass
class Companion:
    """Individual companion entity model."""
    companion_id: str
    name: str
    title: str
    archetype: str  # "ranger", "guardian", "mage"
    asset_key: str = "knight"
    level: int = 1
    xp: int = 0
    max_hp: int = 100
    hp: int = 100
    atk: int = 15
    defense: int = 10
    speed: float = 3.5
    mode: str = MODE_ATTACK
    is_recruited: bool = False
    is_in_party: bool = False
    is_on_caravan: bool = False
    personality: str = "brave"
    expedition: Optional[ExpeditionData] = None
    equipped_gear: Dict[str, Any] = field(default_factory=dict)
    banter_history: List[str] = field(default_factory=list)

    def level_up(self, levels: int = 1) -> None:
        """Increases companion attributes according to their archetype."""
        self.level += levels
        if self.archetype == "ranger":
            self.max_hp += 12 * levels
            self.atk += 5 * levels
            self.defense += 2 * levels
            self.speed = min(5.0, self.speed + 0.1 * levels)
        elif self.archetype == "guardian":
            self.max_hp += 22 * levels
            self.atk += 3 * levels
            self.defense += 6 * levels
        elif self.archetype == "mage":
            self.max_hp += 10 * levels
            self.atk += 6 * levels
            self.defense += 2 * levels
        else:
            self.max_hp += 15 * levels
            self.atk += 4 * levels
            self.defense += 3 * levels
        self.hp = self.max_hp

    def gain_xp(self, amount: int) -> bool:
        """Gains XP and checks for level-ups (Level N requires N * 100 XP)."""
        self.xp += amount
        leveled = False
        while self.xp >= self.level * 100 and self.level < 20:
            self.xp -= self.level * 100
            self.level_up(1)
            leveled = True
        return leveled

    def assign_mode(self, new_mode: str) -> bool:
        """Assigns combat behavior mode."""
        if new_mode in VALID_MODES:
            self.mode = new_mode
            return True
        return False

    def start_expedition(self, zone: str, days: int) -> bool:
        """Dispatches companion on an autonomous resource gathering mission."""
        if zone not in EXPEDITION_ZONES or days <= 0 or self.is_in_party:
            return False
        self.expedition = ExpeditionData(
            zone=zone,
            days_remaining=days,
            total_days=days,
            is_completed=False,
            status_summary=f"Exploring {EXPEDITION_ZONES[zone]['name']}..."
        )
        return True

    def update_expedition(self, days_passed: int = 1, danger_level: float = 0.0, prosperity: float = 50.0) -> Optional[ExpeditionData]:
        """Progresses expedition on day tick."""
        if not self.expedition or self.expedition.is_completed:
            return None

        self.expedition.days_remaining = max(0, self.expedition.days_remaining - days_passed)
        if self.expedition.days_remaining == 0:
            self.expedition.is_completed = True
            zone_info = EXPEDITION_ZONES.get(self.expedition.zone, EXPEDITION_ZONES["forest"])

            # Calculate rewards
            base_gold = int(random.randint(40, 70) * zone_info["gold_mult"] * self.expedition.total_days * (prosperity / 50.0))
            self.expedition.rewards_gold = base_gold

            # Roll items
            possible_items = zone_info["items"]
            item_count = random.randint(1, 2) * self.expedition.total_days
            self.expedition.rewards_items = [random.choice(possible_items) for _ in range(item_count)]

            # Calculate risk & damage
            risk_score = zone_info["risk"] + (danger_level * 0.4)
            if random.random() < (risk_score / 100.0):
                self.expedition.damage_taken = int(random.randint(15, 35) * (risk_score / 50.0))
                self.hp = max(10, self.hp - self.expedition.damage_taken)
                self.expedition.status_summary = f"Completed with skirmishes! Found {base_gold}g & {len(self.expedition.rewards_items)} items."
            else:
                self.expedition.status_summary = f"Triumphant return! Found {base_gold}g & {len(self.expedition.rewards_items)} items."

            # XP reward
            xp_reward = int(50 * zone_info["gold_mult"] * self.expedition.total_days)
            self.expedition.xp_gained = xp_reward
            self.gain_xp(xp_reward)

        return self.expedition

    def to_dict(self) -> Dict[str, Any]:
        return {
            "companion_id": self.companion_id,
            "name": self.name,
            "title": self.title,
            "archetype": self.archetype,
            "asset_key": self.asset_key,
            "level": self.level,
            "xp": self.xp,
            "max_hp": self.max_hp,
            "hp": self.hp,
            "atk": self.atk,
            "defense": self.defense,
            "speed": self.speed,
            "mode": self.mode,
            "is_recruited": self.is_recruited,
            "is_in_party": self.is_in_party,
            "is_on_caravan": self.is_on_caravan,
            "personality": self.personality,
            "expedition": self.expedition.to_dict() if self.expedition else None,
            "equipped_gear": dict(self.equipped_gear),
            "banter_history": list(self.banter_history[-10:])
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Companion':
        if not data:
            return cls("unknown", "Unknown", "Traveler", "ranger")
        exp_data = ExpeditionData.from_dict(data["expedition"]) if data.get("expedition") else None
        return cls(
            companion_id=data.get("companion_id", "unknown"),
            name=data.get("name", "Unknown"),
            title=data.get("title", "Traveler"),
            archetype=data.get("archetype", "ranger"),
            asset_key=data.get("asset_key", "knight"),
            level=data.get("level", 1),
            xp=data.get("xp", 0),
            max_hp=data.get("max_hp", 100),
            hp=data.get("hp", 100),
            atk=data.get("atk", 15),
            defense=data.get("defense", 10),
            speed=data.get("speed", 3.5),
            mode=data.get("mode", MODE_ATTACK),
            is_recruited=data.get("is_recruited", False),
            is_in_party=data.get("is_in_party", False),
            is_on_caravan=data.get("is_on_caravan", False),
            personality=data.get("personality", "brave"),
            expedition=exp_data,
            equipped_gear=dict(data.get("equipped_gear", {})),
            banter_history=list(data.get("banter_history", []))
        )


class CompanionManager:
    """
    Coordinates companion recruitment, party management, tactical combat support,
    and autonomous expeditions across the world.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.companions: Dict[str, Companion] = {}
        self.game_reference: Any = None
        self._initialize_default_companions()
        if self.event_bus:
            self.register_event_listeners(self.event_bus)

    def _initialize_default_companions(self) -> None:
        """Initializes the three core village candidates."""
        self.companions = {
            "faye": Companion(
                companion_id="faye",
                name="Ranger Faye",
                title="The Verdant Scout",
                archetype="ranger",
                asset_key="goblin",  # Distinct fast hunter sprite
                level=2,
                max_hp=95,
                hp=95,
                atk=18,
                defense=8,
                speed=4.2,
                mode=MODE_ATTACK,
                personality="observant"
            ),
            "kai": Companion(
                companion_id="kai",
                name="Guard Kai",
                title="Shield of Asterra",
                archetype="guardian",
                asset_key="knight",  # Heavy armor sprite
                level=3,
                max_hp=150,
                hp=150,
                atk=14,
                defense=20,
                speed=3.2,
                mode=MODE_TANK,
                personality="resolute"
            ),
            "mira": Companion(
                companion_id="mira",
                name="Scholar Mira",
                title="The Arcane Archivist",
                archetype="mage",
                asset_key="slime",  # Arcane glowing sprite
                level=2,
                max_hp=80,
                hp=80,
                atk=22,
                defense=6,
                speed=3.4,
                mode=MODE_HEAL,
                personality="scholarly"
            )
        }

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Registers event listeners on the central EventBus."""
        self.event_bus = event_bus
        event_bus.subscribe("day_changed", self._on_day_changed)
        event_bus.subscribe("enemy_killed", self._on_enemy_killed)

    def recruit_companion(self, companion_id: str) -> bool:
        """Recruits a companion into the roster."""
        if companion_id in self.companions:
            comp = self.companions[companion_id]
            comp.is_recruited = True
            logger.info("Recruited companion: %s", comp.name)
            if self.event_bus:
                self.event_bus.emit("companion_recruited", companion_id=companion_id, name=comp.name)
            return True
        return False

    def set_active_party_companion(self, companion_id: Optional[str]) -> bool:
        """Sets the active companion in party. Ensures max 1 active companion."""
        # Dismiss any current active companion
        for comp in self.companions.values():
            comp.is_in_party = False

        if companion_id and companion_id in self.companions:
            target = self.companions[companion_id]
            if not target.is_recruited:
                return False
            if target.expedition and not target.expedition.is_completed:
                logger.warning("%s is currently away on an expedition!", target.name)
                return False
            target.is_in_party = True
            logger.info("Set active party companion: %s", target.name)
            if self.event_bus:
                self.event_bus.emit("companion_joined_party", companion_id=companion_id, name=target.name)
            return True
        return True

    def get_active_companion(self) -> Optional[Companion]:
        """Returns the currently active party companion, if any."""
        for comp in self.companions.values():
            if comp.is_in_party:
                return comp
        return None

    def dispatch_expedition(self, companion_id: str, zone: str, days: int) -> bool:
        """Sends a recruited companion on an autonomous expedition."""
        if companion_id in self.companions:
            comp = self.companions[companion_id]
            if comp.is_recruited and not comp.is_in_party:
                success = comp.start_expedition(zone, days)
                if success and self.event_bus:
                    self.event_bus.emit(
                        "companion_expedition_started",
                        companion_id=companion_id,
                        zone=zone,
                        days=days
                    )
                return success
        return False

    def claim_expedition_rewards(self, companion_id: str, player: Any) -> Optional[Tuple[int, List[str]]]:
        """Claims rewards from a completed expedition and transfers to player."""
        if companion_id in self.companions:
            comp = self.companions[companion_id]
            if comp.expedition and comp.expedition.is_completed:
                gold = comp.expedition.rewards_gold
                items = list(comp.expedition.rewards_items)

                # Transfer gold & items
                if hasattr(player, "gold"):
                    player.gold += gold
                if hasattr(player, "inventory") and hasattr(player.inventory, "add_item"):
                    from rpg.items import create_item
                    for item_name in items:
                        try:
                            item_obj = create_item(item_name.lower().replace(" ", "_"))
                            if item_obj:
                                player.inventory.add_item(item_obj)
                        except Exception:
                            pass

                comp.expedition = None
                if self.event_bus:
                    self.event_bus.emit("companion_expedition_claimed", companion_id=companion_id, gold=gold, items=items)
                return gold, items
        return None

    def _on_day_changed(self, day: int = 1, season: str = "spring", **kwargs: Any) -> None:
        """Daily tick handler updating expeditions and health recovery."""
        danger = 0.0
        prosperity = 50.0
        if self.game_reference and hasattr(self.game_reference, "living_world"):
            ws = getattr(self.game_reference.living_world, "world_state", None)
            if ws:
                danger = ws.danger_level
                prosperity = ws.prosperity

        for comp in self.companions.values():
            # Recover resting companion HP
            if not comp.is_in_party and not (comp.expedition and not comp.expedition.is_completed):
                comp.hp = min(comp.max_hp, comp.hp + 25)

            # Update expeditions
            if comp.expedition and not comp.expedition.is_completed:
                comp.update_expedition(days_passed=1, danger_level=danger, prosperity=prosperity)
                if comp.expedition.is_completed and self.event_bus:
                    self.event_bus.emit(
                        "companion_expedition_completed",
                        companion_id=comp.companion_id,
                        name=comp.name,
                        zone=comp.expedition.zone
                    )

    def _on_enemy_killed(self, enemy_name: str = "", xp_yield: int = 10, **kwargs: Any) -> None:
        """Active companion receives shared XP from defeated monsters."""
        active = self.get_active_companion()
        if active:
            leveled = active.gain_xp(xp_yield)
            if leveled and self.event_bus:
                self.event_bus.emit("companion_leveled_up", companion_id=active.companion_id, level=active.level)

    def get_contextual_banter(self, context: str = "idle") -> str:
        """Generates contextual companion dialogue banter."""
        active = self.get_active_companion()
        if not active:
            return ""

        banters = {
            "faye": {
                "idle": "The wind carries the scent of pine and adventure.",
                "weather_rain": "Keep your bowstring dry, the rain is pouring hard.",
                "weather_snow": "Snow makes tracks easy to follow. Stay sharp.",
                "dungeon": "Ancient stone and dust... watch for hidden pressure plates.",
                "combat_win": "Right in the bullseye! Clean shot."
            },
            "kai": {
                "idle": "Stay behind my shield if things get messy.",
                "weather_rain": "Armor is going to rust if we stay out in this downpour too long.",
                "weather_snow": "Cold weather stiffens the joints, but duty never rests.",
                "dungeon": "Tight corridors favor a solid shield wall. Let me lead.",
                "combat_win": "None can breach the wall of Asterra!"
            },
            "mira": {
                "idle": "The leylines in this region resonate with ancient magic.",
                "weather_rain": "Rain amplifies lightning and water spells. Fascination in motion.",
                "weather_snow": "Fascinating crystalline structures falling from the sky.",
                "dungeon": "These inscriptions date back to the First Era of Asterra...",
                "combat_win": "A logical outcome. Arcane forces never fail."
            }
        }

        comp_banters = banters.get(active.companion_id, banters["faye"])
        banter_text = comp_banters.get(context, comp_banters.get("idle", "..."))
        active.banter_history.append(banter_text)
        return f"{active.name}: \"{banter_text}\""

    def reset(self) -> None:
        """Resets all companions for fresh session."""
        self._initialize_default_companions()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes companion manager state."""
        return {
            "companions": {cid: comp.to_dict() for cid, comp in self.companions.items()}
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes companion manager state."""
        if not data or "companions" not in data:
            return
        for cid, comp_data in data["companions"].items():
            if cid in self.companions:
                self.companions[cid] = Companion.from_dict(comp_data)
            else:
                self.companions[cid] = Companion.from_dict(comp_data)


import pygame
from rpg.sprite import BaseSprite


class CompanionSprite(BaseSprite):
    """
    World sprite representing an active follower companion with combat AI and visual status.
    """
    def __init__(self, pos: Tuple[float, float], groups: List[Any], companion: Companion) -> None:
        super().__init__(pos, groups, layer=1)
        self.companion = companion
        self.asset_key = companion.asset_key

        from rpg.animation import entity_assets
        if self.asset_key in entity_assets and "idle" in entity_assets[self.asset_key] and "down" in entity_assets[self.asset_key]["idle"]:
            self.image = entity_assets[self.asset_key]["idle"]["down"][0].copy()
        else:
            self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (100, 200, 255), (16, 16), 14)
            pygame.draw.circle(self.image, (255, 255, 255), (16, 16), 14, 2)

        self.rect = self.image.get_rect(center=pos)
        self.hitbox = self.rect.inflate(-6, -6)
        self.game: Any = None
        self.action_cooldown: float = 0.0
        self.font = pygame.font.Font(None, 16)

    def update(self, dt: float) -> None:
        """Companion movement, tethering to player, and combat behavior."""
        if not self.game or not hasattr(self.game, "player") or not self.game.player:
            return

        player = self.game.player
        p_vec = pygame.math.Vector2(player.rect.center)
        c_vec = pygame.math.Vector2(self.rect.center)
        dist_to_player = c_vec.distance_to(p_vec)

        # 1. Follow Movement (Tether ~60-80px behind player)
        if dist_to_player > 70.0:
            direction = (p_vec - c_vec)
            if direction.length_squared() > 0:
                direction = direction.normalize()
                move_speed = self.companion.speed * 45.0 * dt
                self.pos += direction * move_speed
                self.rect.center = (int(self.pos.x), int(self.pos.y))
                self.hitbox.center = self.rect.center

        # 2. Combat Action Cooldown
        self.action_cooldown = max(0.0, self.action_cooldown - dt)
        if self.action_cooldown <= 0.0:
            enemies = getattr(self.game, "enemies", [])
            living_enemies = [e for e in enemies if hasattr(e, "hp") and e.hp > 0]

            if self.companion.mode == MODE_ATTACK:
                for enemy in living_enemies:
                    e_vec = pygame.math.Vector2(enemy.rect.center)
                    if c_vec.distance_to(e_vec) <= 160.0:
                        dmg = max(1, self.companion.atk - getattr(enemy, "defense", 0))
                        enemy.hp = max(0, enemy.hp - dmg)
                        if hasattr(self.game, "particles") and self.game.particles:
                            self.game.particles.add_spark(enemy.rect.center, (255, 200, 50))
                        self.action_cooldown = 1.6
                        break

            elif self.companion.mode == MODE_TANK:
                for enemy in living_enemies:
                    e_vec = pygame.math.Vector2(enemy.rect.center)
                    if c_vec.distance_to(e_vec) <= 200.0:
                        dmg = max(1, (self.companion.atk // 2) - getattr(enemy, "defense", 0))
                        enemy.hp = max(0, enemy.hp - dmg)
                        self.action_cooldown = 2.0
                        break

            elif self.companion.mode == MODE_HEAL:
                if player.hp < player.max_hp * 0.65:
                    heal_amt = 20 + self.companion.level * 3
                    player.hp = min(player.max_hp, player.hp + heal_amt)
                    if hasattr(self.game, "particles") and self.game.particles:
                        self.game.particles.add_spark(player.rect.center, (100, 255, 120))
                    self.action_cooldown = 7.0

    def draw_hp_bar(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        """Renders companion name tag, mode badge, and HP bar above sprite."""
        screen_pos = self.rect.center - camera_offset
        bar_w = 40
        bar_h = 5
        bx = int(screen_pos.x - bar_w // 2)
        by = int(screen_pos.y - 28)

        mode_colors = {
            MODE_ATTACK: (255, 120, 100),
            MODE_TANK: (100, 180, 255),
            MODE_HEAL: (100, 255, 140)
        }
        mode_str = f"[{self.companion.mode.upper()[:3]}] {self.companion.name}"
        txt = self.font.render(mode_str, True, mode_colors.get(self.companion.mode, COLOR_WHITE))
        surface.blit(txt, (screen_pos.x - txt.get_width() // 2, by - 12))

        pygame.draw.rect(surface, (20, 22, 28), (bx, by, bar_w, bar_h), border_radius=2)
        pygame.draw.rect(surface, (80, 85, 95), (bx, by, bar_w, bar_h), 1, border_radius=2)
        hp_ratio = max(0.0, min(1.0, self.companion.hp / float(self.companion.max_hp)))
        fill_w = int(bar_w * hp_ratio)
        if fill_w > 0:
            pygame.draw.rect(surface, (80, 220, 100), (bx, by, fill_w, bar_h), border_radius=2)

