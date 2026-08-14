"""
Echoes of Asterra - Dynamic Bounty Notice Board System
Generates procedural kill/gather contracts with scaling gold+XP rewards.
Contracts refresh on rest or map re-entry. Players can accept up to 3 simultaneously.
"""
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class BountyContract:
    """A single bounty contract from the Notice Board."""
    bounty_id: str
    title: str
    description: str
    bounty_type: str  # "kill" or "gather"
    target: str       # enemy_key or item_name
    target_display: str
    required_count: int
    current_count: int = 0
    gold_reward: int = 0
    xp_reward: int = 0
    is_accepted: bool = False
    is_completed: bool = False
    is_turned_in: bool = False

    def progress(self, amount: int = 1) -> bool:
        """Increments progress. Returns True if this hit completed the bounty."""
        if self.is_turned_in or not self.is_accepted:
            return False
        self.current_count = min(self.current_count + amount, self.required_count)
        if self.current_count >= self.required_count and not self.is_completed:
            self.is_completed = True
            return True
        return False


# --- Bounty Template Pools ---
KILL_BOUNTIES = [
    {"target": "slime", "display": "Slime", "count_range": (3, 8), "gold_base": 25, "xp_base": 40},
    {"target": "wolf", "display": "Wolf", "count_range": (2, 5), "gold_base": 35, "xp_base": 55},
    {"target": "goblin", "display": "Goblin", "count_range": (3, 6), "gold_base": 40, "xp_base": 60},
    {"target": "skeleton", "display": "Skeleton", "count_range": (2, 5), "gold_base": 45, "xp_base": 70},
    {"target": "mage", "display": "Dark Mage", "count_range": (1, 3), "gold_base": 60, "xp_base": 90},
    {"target": "knight", "display": "Knight", "count_range": (1, 3), "gold_base": 70, "xp_base": 100},
]

GATHER_BOUNTIES = [
    {"target": "Red Potion", "display": "Red Potion", "count_range": (2, 5), "gold_base": 20, "xp_base": 30},
    {"target": "Oak Wood", "display": "Oak Wood", "count_range": (3, 8), "gold_base": 15, "xp_base": 25},
    {"target": "Iron Ore", "display": "Iron Ore", "count_range": (2, 5), "gold_base": 30, "xp_base": 40},
    {"target": "Asterra Heart", "display": "Asterra Heart", "count_range": (1, 2), "gold_base": 80, "xp_base": 120},
]

MAX_ACTIVE_BOUNTIES = 3
BOARD_REFRESH_SIZE = 5  # Number of bounties shown on the board


class BountyManager:
    """
    Manages the bounty notice board: generates contracts, tracks progress,
    handles turn-ins, and refreshes the board periodically.
    """
    def __init__(self) -> None:
        self.available_bounties: List[BountyContract] = []
        self.active_bounties: List[BountyContract] = []
        self.completed_count: int = 0
        self._bounty_counter: int = 0

    def refresh_board(self, player_level: int = 1) -> None:
        """Generates a fresh set of bounty contracts scaled to player level."""
        self.available_bounties.clear()

        # Mix of kill and gather bounties
        templates = []
        kill_pool = random.sample(KILL_BOUNTIES, min(3, len(KILL_BOUNTIES)))
        gather_pool = random.sample(GATHER_BOUNTIES, min(2, len(GATHER_BOUNTIES)))
        templates.extend([(t, "kill") for t in kill_pool])
        templates.extend([(t, "gather") for t in gather_pool])
        random.shuffle(templates)

        for tmpl, btype in templates[:BOARD_REFRESH_SIZE]:
            self._bounty_counter += 1
            count = random.randint(*tmpl["count_range"])
            # Scale rewards with player level
            level_mult = 1.0 + (player_level - 1) * 0.12
            gold = int(tmpl["gold_base"] * level_mult * (count / tmpl["count_range"][0]))
            xp = int(tmpl["xp_base"] * level_mult * (count / tmpl["count_range"][0]))

            bounty = BountyContract(
                bounty_id=f"bounty_{self._bounty_counter}",
                title=f"{'Hunt' if btype == 'kill' else 'Gather'}: {tmpl['display']} x{count}",
                description=f"{'Eliminate' if btype == 'kill' else 'Collect'} {count} {tmpl['display']}.",
                bounty_type=btype,
                target=tmpl["target"],
                target_display=tmpl["display"],
                required_count=count,
                gold_reward=gold,
                xp_reward=xp,
            )
            self.available_bounties.append(bounty)

    def accept_bounty(self, bounty: BountyContract) -> Tuple[bool, str]:
        """Accept a bounty from the board. Returns (success, message)."""
        if len(self.active_bounties) >= MAX_ACTIVE_BOUNTIES:
            return False, f"Max {MAX_ACTIVE_BOUNTIES} active bounties!"
        if bounty.is_accepted:
            return False, "Bounty already accepted!"
        bounty.is_accepted = True
        self.active_bounties.append(bounty)
        if bounty in self.available_bounties:
            self.available_bounties.remove(bounty)
        return True, f"Accepted: {bounty.title}"

    def on_enemy_killed(self, enemy_key: str) -> Optional[BountyContract]:
        """Called when an enemy is killed. Progresses matching kill bounties."""
        for b in self.active_bounties:
            if b.bounty_type == "kill" and b.target == enemy_key and not b.is_completed:
                just_done = b.progress()
                if just_done:
                    return b
                return None  # Progressed but not done
        return None

    def on_item_gained(self, item_name: str, quantity: int = 1) -> Optional[BountyContract]:
        """Called when an item is collected. Progresses matching gather bounties."""
        for b in self.active_bounties:
            if b.bounty_type == "gather" and b.target == item_name and not b.is_completed:
                just_done = b.progress(quantity)
                if just_done:
                    return b
        return None

    def turn_in_bounty(self, bounty: BountyContract, player: Any) -> Tuple[bool, str]:
        """Turn in a completed bounty for rewards."""
        if not bounty.is_completed:
            return False, "Bounty not complete!"
        if bounty.is_turned_in:
            return False, "Already turned in!"

        bounty.is_turned_in = True
        player.gold += bounty.gold_reward
        player.gain_xp(bounty.xp_reward)
        self.completed_count += 1

        # Remove from active
        if bounty in self.active_bounties:
            self.active_bounties.remove(bounty)

        return True, f"+{bounty.gold_reward}g +{bounty.xp_reward}XP"

    def abandon_bounty(self, bounty: BountyContract) -> None:
        """Abandons an active bounty (resets progress)."""
        bounty.is_accepted = False
        bounty.current_count = 0
        bounty.is_completed = False
        if bounty in self.active_bounties:
            self.active_bounties.remove(bounty)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes bounty state for save system."""
        return {
            "completed_count": self.completed_count,
            "counter": self._bounty_counter,
            "active": [
                {
                    "id": b.bounty_id, "title": b.title, "desc": b.description,
                    "type": b.bounty_type, "target": b.target, "display": b.target_display,
                    "req": b.required_count, "cur": b.current_count,
                    "gold": b.gold_reward, "xp": b.xp_reward,
                    "done": b.is_completed, "turned_in": b.is_turned_in,
                }
                for b in self.active_bounties
            ],
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores bounty state from save data."""
        self.completed_count = data.get("completed_count", 0)
        self._bounty_counter = data.get("counter", 0)
        self.active_bounties.clear()
        for bd in data.get("active", []):
            b = BountyContract(
                bounty_id=bd["id"], title=bd["title"], description=bd["desc"],
                bounty_type=bd["type"], target=bd["target"], target_display=bd["display"],
                required_count=bd["req"], current_count=bd["cur"],
                gold_reward=bd["gold"], xp_reward=bd["xp"],
                is_accepted=True, is_completed=bd.get("done", False),
                is_turned_in=bd.get("turned_in", False),
            )
            self.active_bounties.append(b)
