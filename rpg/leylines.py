"""
Echoes of Asterra - Ancient Leyline Network
Manages arcane crystal conduits, channel activations, fast travel network,
and environmental water stabilization/purification fields.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
from rpg.constants import (
    MAP_VILLAGE,
    MAP_FOREST,
    MAP_LAKE,
    MAP_RUINS,
    MAP_CAVE,
    MAP_SUNKEN_MIRE
)
from rpg.events import EventBus


@dataclass
class LeylineNode:
    """Represents a persistent ancient Leyline conduit in the world."""
    node_id: str
    name: str
    region_map: str
    pos: Tuple[int, int]
    is_activated: bool = False
    purification_radius: float = 220.0
    is_overcharged: bool = False
    overcharge_hours_left: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "region_map": self.region_map,
            "pos": list(self.pos),
            "is_activated": self.is_activated,
            "purification_radius": self.purification_radius,
            "is_overcharged": self.is_overcharged,
            "overcharge_hours_left": self.overcharge_hours_left
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeylineNode":
        return cls(
            node_id=data["node_id"],
            name=data["name"],
            region_map=data["region_map"],
            pos=tuple(data.get("pos", [0, 0])),
            is_activated=data.get("is_activated", False),
            purification_radius=float(data.get("purification_radius", 220.0)),
            is_overcharged=data.get("is_overcharged", False),
            overcharge_hours_left=float(data.get("overcharge_hours_left", 0.0))
        )


DEFAULT_LEYLINE_NODES: List[LeylineNode] = [
    LeylineNode("village_grove", "Village Elder Grove", MAP_VILLAGE, (160, 240), is_activated=True),
    LeylineNode("forest_canopy", "Deep Forest Canopy", MAP_FOREST, (480, 240), is_activated=False),
    LeylineNode("lake_basin", "Sunken Basin Pier", MAP_LAKE, (280, 160), is_activated=False),
    LeylineNode("ruins_apex", "Sunfire Ruins Plaza", MAP_RUINS, (420, 280), is_activated=False),
    LeylineNode("cave_heart", "Granite Cavern Heart", MAP_CAVE, (480, 320), is_activated=False),
    LeylineNode("mire_confluence", "Primordial Mire Confluence", MAP_SUNKEN_MIRE, (480, 280), is_activated=False),
]


class LeylineManager:
    """
    Subsystem managing the discovery, channeling, fast-travel, and overcharge mechanics
    of the Ancient Leyline Network.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.nodes: Dict[str, LeylineNode] = {}
        self.reset()

    def reset(self) -> None:
        """Resets network to default node registry."""
        self.nodes = {node.node_id: LeylineNode(
            node_id=node.node_id,
            name=node.name,
            region_map=node.region_map,
            pos=node.pos,
            is_activated=node.is_activated,
            purification_radius=node.purification_radius,
            is_overcharged=False,
            overcharge_hours_left=0.0
        ) for node in DEFAULT_LEYLINE_NODES}

    def get_node_by_map(self, region_map: str) -> Optional[LeylineNode]:
        """Returns the Leyline node in the given map if one exists."""
        for node in self.nodes.values():
            if node.region_map == region_map:
                return node
        return None

    def is_region_overcharged(self, region_map: str) -> bool:
        """Returns True if the conduit in the given region map is currently overcharged."""
        node = self.get_node_by_map(region_map)
        return bool(node and node.is_overcharged and node.overcharge_hours_left > 0.0)

    def channel_node(self, node_id: str, player: Any) -> Tuple[bool, str]:
        """
        Channels player mana (10 Mana) into a dormant Leyline conduit to permanently activate it.
        """
        node = self.nodes.get(node_id)
        if not node:
            return False, "Unknown Leyline Conduit."
        if node.is_activated:
            return False, f"{node.name} is already resonating with ancient energy."

        mana_cost = 10
        if player.mana < mana_cost:
            return False, f"Not enough Mana to channel conduit ({player.mana}/{mana_cost} Mana required)."

        player.mana -= mana_cost
        node.is_activated = True

        if self.event_bus:
            self.event_bus.emit(
                "leyline_activated",
                node_id=node.node_id,
                node_name=node.name,
                region_map=node.region_map
            )

        return True, f"★ {node.name} Awakened! Arcane Leyline Network connected."

    def overcharge_node(self, node_id: str, player: Any) -> Tuple[bool, str]:
        """
        Infuses an activated conduit with a Starlight Crystal or Sunken Relic to overcharge it for 24h.
        """
        node = self.nodes.get(node_id)
        if not node:
            return False, "Unknown Leyline Conduit."
        if not node.is_activated:
            return False, "Conduit must be awakened before it can be overcharged."
        if node.is_overcharged and node.overcharge_hours_left > 0.0:
            return False, f"{node.name} is already overcharged ({node.overcharge_hours_left:.1f}h remaining)."

        # Check for catalyst in player inventory
        inv = getattr(player, "inventory", None)
        if not inv:
            return False, "Inventory not available."

        consumed_catalyst = None
        for cat_name in ["Starlight Crystal", "starlight_crystal", "Sunken Relic", "sunken_relic"]:
            if inv.has_item(cat_name, 1):
                inv.remove_item(cat_name, 1)
                consumed_catalyst = cat_name
                break

        if not consumed_catalyst:
            return False, "Requires 1x Starlight Crystal or 1x Sunken Relic to overcharge."

        node.is_overcharged = True
        node.overcharge_hours_left = 24.0

        if self.event_bus:
            self.event_bus.emit(
                "leyline_overcharged",
                node_id=node.node_id,
                node_name=node.name,
                region_map=node.region_map,
                duration_hours=24.0
            )

        return True, f"⚡ {node.name} OVERCHARGED for 24h! Regional surge unleashed."

    def update_overcharge(self, dt_hours: float) -> None:
        """Ticks down overcharge duration on active conduits."""
        for node in self.nodes.values():
            if node.is_overcharged:
                node.overcharge_hours_left -= dt_hours
                if node.overcharge_hours_left <= 0:
                    node.is_overcharged = False
                    node.overcharge_hours_left = 0.0
                    if self.event_bus:
                        self.event_bus.emit(
                            "leyline_overcharge_expired",
                            node_id=node.node_id,
                            region_map=node.region_map
                        )

    def get_fast_travel_destinations(self, current_map: str) -> List[LeylineNode]:
        """Returns all activated nodes available for fast travel excluding current map."""
        return [node for node in self.nodes.values() if node.is_activated and node.region_map != current_map]

    def fast_travel(self, player: Any, target_node_id: str, world_manager: Any) -> Tuple[bool, str]:
        """
        Teleports player to the target activated Leyline Conduit.
        """
        target_node = self.nodes.get(target_node_id)
        if not target_node:
            return False, "Target conduit does not exist."
        if not target_node.is_activated:
            return False, f"{target_node.name} is dormant and must be channeled first."

        # Change map and position player near node
        target_x, target_y = target_node.pos[0], target_node.pos[1] + 36
        world_manager.change_map(target_node.region_map, spawn_pos=(target_x, target_y))
        
        if self.event_bus:
            self.event_bus.emit(
                "leyline_teleport",
                destination_node=target_node.node_id,
                destination_map=target_node.region_map
            )

        return True, f"Teleported across the Leylines to {target_node.name}."

    def is_position_purified(self, x: float, y: float, current_map: str) -> bool:
        """
        Checks if the coordinates fall within the purification aura of an active Leyline node,
        or if the entire region is purified by an overcharged Leyline.
        """
        if self.is_region_overcharged(current_map):
            return True

        node = self.get_node_by_map(current_map)
        if not node or not node.is_activated:
            return False

        nx, ny = node.pos
        dist_sq = (x - nx) ** 2 + (y - ny) ** 2
        return dist_sq <= (node.purification_radius ** 2)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Leyline state for savegame."""
        return {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()}
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores Leyline state from savegame."""
        if not isinstance(data, dict):
            return
        saved_nodes = data.get("nodes", {})
        for nid, ndata in saved_nodes.items():
            if nid in self.nodes:
                self.nodes[nid].is_activated = ndata.get("is_activated", False)
                self.nodes[nid].purification_radius = float(ndata.get("purification_radius", 220.0))
                self.nodes[nid].is_overcharged = ndata.get("is_overcharged", False)
                self.nodes[nid].overcharge_hours_left = float(ndata.get("overcharge_hours_left", 0.0))
            else:
                self.nodes[nid] = LeylineNode.from_dict(ndata)
