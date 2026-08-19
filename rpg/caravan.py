"""
Echoes of Asterra - Diverse Caravan Simulation & Sovereign Trade System (Pillar #3)
Simulates ambient trade caravans (Merchant, Military Patrol, Refugee, Pilgrim, Tax Caravan)
and player-funded Sovereign Trade Convoys (CARAVAN_SOVEREIGN_PLAYER) connecting
the Village with fortified military outposts, escorted by companion captains.
Features real-time road safety, bandit ambush simulation, emergency HUD alerts, and rescue encounters.
"""
import random
import pygame
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional
from rpg.sprite import BaseSprite
from rpg.settings import TILE_SIZE, GRID_WIDTH, GRID_HEIGHT
from rpg.events import EventBus

CARAVAN_MERCHANT = "merchant"
CARAVAN_MILITARY = "military"
CARAVAN_REFUGEE = "refugee"
CARAVAN_PILGRIM = "pilgrim"
CARAVAN_TAX = "tax"
CARAVAN_SOVEREIGN_PLAYER = "sovereign_player"

CARGO_PROVISIONS = "provisions"
CARGO_REFINED_IRON = "refined_iron"
CARGO_TONIC_CRATES = "tonic_crates"

CARGO_DEFS: Dict[str, Dict[str, Any]] = {
    CARGO_PROVISIONS: {
        "name": "Village Provisions",
        "cost": 30,
        "base_yield": 60,
        "items": [("Herb", 2), ("Red Potion", 1)]
    },
    CARGO_REFINED_IRON: {
        "name": "Refined Iron Goods",
        "cost": 50,
        "base_yield": 110,
        "items": [("Iron Ore", 3), ("Red Potion", 1)]
    },
    CARGO_TONIC_CRATES: {
        "name": "Apothecary Tonic Crates",
        "cost": 60,
        "base_yield": 135,
        "items": [("Red Potion", 2), ("Mana Potion", 1)]
    }
}


@dataclass
class CaravanRoute:
    """Path connecting maps."""
    origin_map: str
    target_map: str
    waypoints: List[Tuple[float, float]]


class CaravanEntity(BaseSprite):
    """Physical sprite representing a traveling caravan on active map."""
    def __init__(self, c_type: str, pos: Tuple[float, float], groups: List[pygame.sprite.Group], companion_captain: Optional[str] = None) -> None:
        self._layer = 1
        super().__init__(pos, groups, layer=1)
        self.caravan_type = c_type
        self.companion_captain = companion_captain
        if c_type == CARAVAN_SOVEREIGN_PLAYER:
            self.hp = 150 if companion_captain else 100
            self.speed = 45.0
        elif c_type == CARAVAN_MILITARY:
            self.hp = 100
            self.speed = 50.0
        else:
            self.hp = 40
            self.speed = 35.0
        self.max_hp = self.hp
        
        # Procedural sprite image rendering
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        self._draw_caravan_texture()
        self.rect = self.image.get_rect(center=(int(pos[0]), int(pos[1])))
        self.hitbox = self.rect.copy()

    def _draw_caravan_texture(self) -> None:
        """Draws distinct visual badge per caravan type."""
        color_map = {
            CARAVAN_MERCHANT: (220, 180, 50),         # Gold/Yellow
            CARAVAN_MILITARY: (70, 130, 220),         # Knight Blue
            CARAVAN_REFUGEE: (160, 120, 90),          # Earth Brown
            CARAVAN_PILGRIM: (200, 230, 240),         # White/Cyan
            CARAVAN_TAX: (220, 80, 80),               # Crimson Red
            CARAVAN_SOVEREIGN_PLAYER: (145, 50, 200)  # Sovereign Royal Purple
        }
        c = color_map.get(self.caravan_type, (200, 200, 200))
        # Draw wooden cart / pack mule frame
        pygame.draw.rect(self.image, c, (4, 6, 24, 20), border_radius=4)
        pygame.draw.rect(self.image, (40, 30, 20), (4, 6, 24, 20), 2, border_radius=4)
        # Wheels
        pygame.draw.circle(self.image, (30, 30, 30), (8, 24), 4)
        pygame.draw.circle(self.image, (30, 30, 30), (24, 24), 4)

        if self.caravan_type == CARAVAN_SOVEREIGN_PLAYER:
            # Gold star / sovereign crown badge on the wagon canvas
            pygame.draw.circle(self.image, (255, 215, 0), (16, 15), 4)
            # Companion guard badge
            if self.companion_captain:
                pygame.draw.circle(self.image, (100, 255, 100), (26, 8), 3)


class CaravanManager:
    """
    Spawns, simulates, and updates physical traveling caravans across Asterra.
    Supports player-commissioned Sovereign Caravans connected with settlement facilities
    and dynamic bandit ambush defense skirmishes (Pillar #3 Phase 3).
    """
    def __init__(self) -> None:
        self.event_bus: Optional[EventBus] = None
        self.active_caravans: List[Dict[str, Any]] = []
        self.active_ambushes: Dict[int, Dict[str, Any]] = {}
        self.spawn_timer = 0.0
        self.road_safety: float = 50.0  # 0 to 100
        self.game_reference: Any = None

    def register_event_listeners(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        event_bus.subscribe("day_changed", self._on_day_changed)
        event_bus.subscribe("road_safety_increased", self._on_road_safety_increased)

    def _on_road_safety_increased(self, amount: float = 10.0, **kwargs: Any) -> None:
        self.road_safety = min(100.0, self.road_safety + float(amount))

    def _on_day_changed(self, **kwargs: Any) -> None:
        """Spawns 1-2 new ambient caravans daily based on world state and adjusts safety."""
        # Safety naturally decays slightly without military patrols
        self.road_safety = max(20.0, self.road_safety - 2.0)
        types = [CARAVAN_MERCHANT, CARAVAN_MILITARY, CARAVAN_REFUGEE, CARAVAN_PILGRIM, CARAVAN_TAX]
        selected_type = random.choice(types)
        self.spawn_caravan(selected_type)

    def spawn_caravan(self, c_type: str = CARAVAN_MERCHANT) -> None:
        """Instantiates a new ambient caravan route."""
        routes = [
            ("village", "forest"),
            ("forest", "ruins"),
            ("village", "cave"),
            ("forest", "lake")
        ]
        origin, target = random.choice(routes)
        caravan_data = {
            "id": random.randint(1000, 9999),
            "type": c_type,
            "origin": origin,
            "target": target,
            "current_map": origin,
            "progress": 0.0,
            "cargo": "goods" if c_type == CARAVAN_MERCHANT else ("gold" if c_type == CARAVAN_TAX else "supplies"),
            "pos": (GRID_WIDTH // 2 * TILE_SIZE, GRID_HEIGHT // 2 * TILE_SIZE),
            "companion_captain": None,
            "cost": 0,
            "base_yield": 0,
            "is_under_ambush": False,
            "ambush_checked": False,
            "ambush_timer": 0.0,
            "raiders_count": 0
        }
        self.active_caravans.append(caravan_data)
        if self.event_bus:
            self.event_bus.emit("caravan_spawned", caravan_type=c_type, origin=origin, target=target)

    def commission_sovereign_caravan(
        self,
        target_cp_id: str,
        cargo_id: str = CARGO_PROVISIONS,
        companion_id: Optional[str] = None,
        player: Any = None,
        settlement_manager: Any = None,
        companion_manager: Any = None,
        outpost_manager: Any = None
    ) -> Tuple[bool, str]:
        """
        Commissions a custom Sovereign Player Caravan from Village to a constructed Outpost.
        Validates target outpost, cargo availability, player funds, and companion readiness.
        """
        # 1. Resolve Outpost Manager & check target outpost
        om = outpost_manager
        if not om and self.game_reference:
            om = getattr(self.game_reference, "outpost_manager", None)
        if not om or not om.has_outpost(target_cp_id):
            return False, f"Cannot dispatch caravan: No active outpost built at '{target_cp_id}'."

        outpost = om.outposts[target_cp_id]
        target_map = outpost.map_name

        # 2. Check Cargo definition
        if cargo_id not in CARGO_DEFS:
            return False, f"Unknown trade cargo '{cargo_id}'."
        cargo_info = CARGO_DEFS[cargo_id]
        cost = cargo_info["cost"]

        # Check funds
        p_gold = getattr(player, "gold", 0) if player else 0
        if p_gold < cost:
            return False, f"Insufficient funds to provision caravan! Cost is {cost}g (You have {p_gold}g)."

        # 3. Check Companion Captain (if assigned)
        comp_mgr = companion_manager
        if not comp_mgr and self.game_reference:
            comp_mgr = getattr(self.game_reference, "companion_manager", None)

        comp_name = None
        if companion_id and comp_mgr:
            comp = comp_mgr.companions.get(companion_id)
            if not comp or not comp.is_recruited:
                return False, f"Companion '{companion_id}' is not recruited."
            if comp.is_in_party:
                return False, f"{comp.name} is currently in your active party. Remove them from party first."
            if comp.expedition and not comp.expedition.is_completed:
                return False, f"{comp.name} is away on an expedition."
            if getattr(comp, "is_on_caravan", False):
                return False, f"{comp.name} is already escorting another caravan."

            comp.is_on_caravan = True
            comp_name = comp.name

        # Deduct gold
        if player:
            if hasattr(player, "gold"):
                player.gold -= cost

        caravan_data = {
            "id": random.randint(10000, 99999),
            "type": CARAVAN_SOVEREIGN_PLAYER,
            "origin": "village",
            "target": target_map,
            "target_cp_id": target_cp_id,
            "current_map": "village",
            "progress": 0.0,
            "cargo": cargo_id,
            "cargo_name": cargo_info["name"],
            "cost": cost,
            "base_yield": cargo_info["base_yield"],
            "companion_captain": companion_id,
            "pos": (GRID_WIDTH // 2 * TILE_SIZE, GRID_HEIGHT // 2 * TILE_SIZE),
            "is_under_ambush": False,
            "ambush_checked": False,
            "ambush_timer": 0.0,
            "raiders_count": 0
        }
        self.active_caravans.append(caravan_data)

        if self.event_bus:
            self.event_bus.emit(
                "sovereign_caravan_dispatched",
                caravan_id=caravan_data["id"],
                target_outpost=outpost.name,
                cargo=cargo_info["name"],
                captain=comp_name
            )

        captain_str = f" Captain: {comp_name}." if comp_name else ""
        return True, f"Sovereign Caravan dispatched to {outpost.name} carrying {cargo_info['name']}!{captain_str}"

    def trigger_caravan_ambush(self, caravan_id: int) -> bool:
        """Explicitly forces a bandit ambush on an active traveling caravan (useful for tests and story triggers)."""
        for caravan in self.active_caravans:
            if caravan["id"] == caravan_id:
                caravan["is_under_ambush"] = True
                caravan["ambush_map"] = caravan["target"]
                caravan["ambush_timer"] = 60.0
                caravan["raiders_count"] = 3
                self.active_ambushes[caravan_id] = caravan
                if self.event_bus:
                    self.event_bus.emit(
                        "caravan_ambushed",
                        caravan_id=caravan_id,
                        map_name=caravan["target"],
                        caravan_type=caravan["type"]
                    )
                return True
        return False

    def on_ambush_enemy_killed(self, caravan_id: Optional[int], player: Any = None) -> None:
        """Called when a BanditRaider enemy attacking the caravan is slain by the player."""
        if not caravan_id or caravan_id not in self.active_ambushes:
            # Check if there is any active ambush to resolve
            if self.active_ambushes:
                caravan_id = list(self.active_ambushes.keys())[0]
            else:
                return

        caravan = self.active_ambushes[caravan_id]
        caravan["raiders_count"] = max(0, caravan.get("raiders_count", 3) - 1)

        if caravan["raiders_count"] == 0:
            # Convoy fully saved!
            caravan["is_under_ambush"] = False
            if caravan_id in self.active_ambushes:
                del self.active_ambushes[caravan_id]

            # Deliver rescue rewards to player
            if player:
                if hasattr(player, "gain_xp"):
                    player.gain_xp(50)
                elif hasattr(player, "xp"):
                    player.xp += 50

                if hasattr(player, "gain_gold"):
                    player.gain_gold(30)
                elif hasattr(player, "gold"):
                    player.gold += 30

            # Boost road safety
            if self.event_bus:
                self.event_bus.emit("road_safety_increased", amount=10.0)
                self.event_bus.emit(
                    "caravan_rescued",
                    caravan_id=caravan_id,
                    map_name=caravan.get("target", "forest")
                )
            else:
                self.road_safety = min(100.0, self.road_safety + 10.0)

    def get_active_ambush_for_map(self, map_name: str) -> Optional[Dict[str, Any]]:
        """Returns the first active ambush happening in the given map region, if any."""
        for caravan in self.active_ambushes.values():
            if caravan.get("ambush_map") == map_name or caravan.get("target") == map_name:
                return caravan
        return None

    def update(self, dt: float, current_map: str = "", visible_sprites: pygame.sprite.Group = None) -> None:
        """Updates caravan positions, checks ambush triggers, and handles map travel or arrivals."""
        self.spawn_timer += dt
        if self.spawn_timer >= 60.0:  # Spawn ambient caravan every 60 seconds
            self.spawn_timer = 0.0
            self.spawn_caravan(random.choice([CARAVAN_MERCHANT, CARAVAN_MILITARY]))

        for caravan in list(self.active_caravans):
            # If under ambush, progress halts and timer ticks down
            if caravan.get("is_under_ambush", False):
                caravan["ambush_timer"] = max(0.0, caravan.get("ambush_timer", 60.0) - dt)
                if caravan["ambush_timer"] <= 0.0:
                    # Caravan destroyed!
                    c_id = caravan["id"]
                    self.active_caravans.remove(caravan)
                    if c_id in self.active_ambushes:
                        del self.active_ambushes[c_id]

                    # Release companion with injury penalty
                    comp_id = caravan.get("companion_captain")
                    if comp_id and self.game_reference and hasattr(self.game_reference, "companion_manager"):
                        cm = self.game_reference.companion_manager
                        comp = cm.companions.get(comp_id)
                        if comp:
                            comp.is_on_caravan = False
                            comp.hp = max(10, comp.hp - 35)

                    if self.event_bus:
                        self.event_bus.emit("caravan_destroyed", caravan_id=c_id, map_name=caravan["target"])
                continue

            # Check mid-journey ambush chance
            if not caravan.get("ambush_checked") and 0.25 <= caravan.get("progress", 0.0) <= 0.75:
                caravan["ambush_checked"] = True
                # Ambush probability inversely proportional to road safety (e.g. 50 safety -> 25% chance)
                ambush_risk = max(0.05, (100.0 - self.road_safety) / 200.0)
                if random.random() < ambush_risk:
                    self.trigger_caravan_ambush(caravan["id"])
                    continue

            caravan["progress"] += dt * 0.05  # Travel speed
            
            if caravan["progress"] >= 1.0:
                self._handle_caravan_arrival(caravan)

    def _handle_caravan_arrival(self, caravan: Dict[str, Any]) -> None:
        """Processes caravan arrival at destination, distributing rewards and granting companion XP."""
        c_type = caravan["type"]
        target_map = caravan["target"]
        if caravan in self.active_caravans:
            self.active_caravans.remove(caravan)
        if caravan["id"] in self.active_ambushes:
            del self.active_ambushes[caravan["id"]]

        if c_type == CARAVAN_SOVEREIGN_PLAYER:
            cargo_id = caravan.get("cargo", CARGO_PROVISIONS)
            cargo_info = CARGO_DEFS.get(cargo_id, CARGO_DEFS[CARGO_PROVISIONS])
            base_gold = caravan.get("base_yield", cargo_info["base_yield"])

            # Check Trade Hub Specialization multiplier (+30%)
            gold_mult = 1.0
            sm = getattr(self.game_reference, "settlement", None) if self.game_reference else None
            if not sm and self.game_reference and hasattr(self.game_reference, "living_world"):
                sm = getattr(self.game_reference.living_world, "settlement", None)
            if sm and getattr(sm, "specialization", "") == "trade_hub":
                gold_mult = 1.30

            total_gold = int(base_gold * gold_mult)

            # Deliver gold to player
            player = getattr(self.game_reference, "player", None) if self.game_reference else None
            if player:
                if hasattr(player, "gain_gold"):
                    player.gain_gold(total_gold)
                elif hasattr(player, "gold"):
                    player.gold += total_gold

                # Deliver cargo items
                if hasattr(player, "inventory") and player.inventory:
                    from rpg.items import create_item
                    for item_name, qty in cargo_info.get("items", []):
                        it = create_item(item_name, qty)
                        if it:
                            player.inventory.add_item(it)

            # Release companion and grant XP
            comp_id = caravan.get("companion_captain")
            if comp_id and self.game_reference and hasattr(self.game_reference, "companion_manager"):
                cm = self.game_reference.companion_manager
                comp = cm.companions.get(comp_id)
                if comp:
                    comp.is_on_caravan = False
                    comp.gain_xp(100)

            # Increment Outpost arrivals count
            target_cp = caravan.get("target_cp_id")
            if target_cp and self.game_reference and hasattr(self.game_reference, "outpost_manager"):
                om = self.game_reference.outpost_manager
                if target_cp in om.outposts:
                    om.outposts[target_cp].caravan_arrivals_count += 1

            if self.event_bus:
                self.event_bus.emit(
                    "sovereign_caravan_arrived",
                    target_map=target_map,
                    cargo=cargo_info["name"],
                    gold_earned=total_gold,
                    captain=caravan.get("companion_captain")
                )
        else:
            if self.event_bus:
                self.event_bus.emit("caravan_arrived", caravan_type=c_type, cargo_type=caravan.get("cargo"), target_map=target_map)
                if c_type == CARAVAN_MILITARY:
                    self.event_bus.emit("road_safety_increased", amount=15.0)
                elif c_type == CARAVAN_PILGRIM:
                    self.event_bus.emit("prosperity_changed", amount=3.0)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes caravan and ambush state."""
        return {
            "caravans": self.active_caravans,
            "active_ambushes": self.active_ambushes,
            "spawn_timer": self.spawn_timer,
            "road_safety": self.road_safety
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes caravan state."""
        if data:
            self.active_caravans = data.get("caravans", [])
            # Reconstruct dict keyed by int IDs
            raw_ambushes = data.get("active_ambushes", {})
            self.active_ambushes = {int(k): v for k, v in raw_ambushes.items()} if isinstance(raw_ambushes, dict) else {}
            self.spawn_timer = data.get("spawn_timer", 0.0)
            self.road_safety = float(data.get("road_safety", 50.0))
