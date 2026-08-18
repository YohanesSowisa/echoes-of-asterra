"""
Echoes of Asterra - Seasonal Festival Minigames System (Fitur #3)
Expands the 'Village Festival' world event into 3 interactive seasonal minigames:
1. Target Archery Contest (Precision timing gauge)
2. Harvest Sprint (Fast reaction gathering against clock)
3. Dennis's Feast & Brew Challenge (Turn-based push-your-luck stamina contest)
With seasonal score records, tiered prizes, custom titles, and RumorBoard integration.
"""
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

from rpg.events import EventBus
from rpg.constants import (
    COLOR_WHITE, COLOR_GOLD, COLOR_GREEN, COLOR_BLUE, COLOR_RED, COLOR_GRAY,
    COLOR_UI_BG, COLOR_UI_BORDER, COLOR_CYAN
)

logger = logging.getLogger("FestivalSystem")

MINIGAME_ARCHERY = "archery"
MINIGAME_HARVEST = "harvest"
MINIGAME_FEAST = "feast"

VALID_MINIGAMES = [MINIGAME_ARCHERY, MINIGAME_HARVEST, MINIGAME_FEAST]


@dataclass
class FestivalScoreRecord:
    """Historical score record for a seasonal festival minigame."""
    minigame_id: str
    season: str
    year: int
    score: int
    tier: str  # "Participant", "Bronze", "Silver", "Gold"
    reward_claimed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "minigame_id": self.minigame_id,
            "season": self.season,
            "year": self.year,
            "score": self.score,
            "tier": self.tier,
            "reward_claimed": self.reward_claimed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FestivalScoreRecord':
        if not data:
            return cls(MINIGAME_ARCHERY, "spring", 1, 0, "Participant")
        return cls(
            minigame_id=data.get("minigame_id", MINIGAME_ARCHERY),
            season=data.get("season", "spring"),
            year=data.get("year", 1),
            score=data.get("score", 0),
            tier=data.get("tier", "Participant"),
            reward_claimed=data.get("reward_claimed", True)
        )


class FestivalManager:
    """
    Coordinates interactive festival minigames, calculates scores & tiered prizes,
    tracks seasonal records, and disseminates victory rumors.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.game_reference: Any = None
        self.is_festival_active: bool = False
        self.seasonal_records: Dict[str, Dict[str, int]] = {
            "spring": {"archery": 0, "harvest": 0, "feast": 0},
            "summer": {"archery": 0, "harvest": 0, "feast": 0},
            "autumn": {"archery": 0, "harvest": 0, "feast": 0},
            "winter": {"archery": 0, "harvest": 0, "feast": 0}
        }
        self.high_scores: Dict[str, int] = {"archery": 0, "harvest": 0, "feast": 0}
        self.champion_titles_awarded: List[str] = []

        # Active Minigame State
        self.current_minigame: Optional[str] = None
        self.archery_shots_left: int = 5
        self.archery_accumulated_score: int = 0

        # Feast challenge state
        self.feast_player_fullness: int = 0
        self.feast_player_score: int = 0
        self.feast_dennis_score: int = 0
        self.feast_is_over: bool = False

        if self.event_bus:
            self.register_event_listeners(self.event_bus)

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Subscribes to world events."""
        self.event_bus = event_bus
        event_bus.subscribe("world_event_started", self._on_world_event_started)
        event_bus.subscribe("world_event_ended", self._on_world_event_ended)

    def _on_world_event_started(self, event_id: str = "", **kwargs: Any) -> None:
        if event_id == "village_festival":
            self.is_festival_active = True
            logger.info("Village Festival has begun! Minigames are now open in Asterra Square.")

    def _on_world_event_ended(self, event_id: str = "", **kwargs: Any) -> None:
        if event_id == "village_festival":
            self.is_festival_active = False
            self.current_minigame = None
            logger.info("Village Festival has concluded.")

    # --- 1. ARCHERY CONTEST LOGIC ---

    def start_archery_contest(self) -> None:
        """Initializes a 5-shot Archery contest."""
        self.current_minigame = MINIGAME_ARCHERY
        self.archery_shots_left = 5
        self.archery_accumulated_score = 0

    def shoot_archery_arrow(self, timing_pos: float) -> Tuple[int, str]:
        """
        Takes a shot based on timing bar position (0.0 to 1.0, with center 0.5 as Bullseye).
        Returns: (shot_score, hit_grade)
        """
        if self.archery_shots_left <= 0:
            return 0, "No arrows left"

        self.archery_shots_left -= 1
        dist_from_center = abs(timing_pos - 0.5)

        if dist_from_center <= 0.05:
            score = 100
            grade = "BULLSEYE!"
        elif dist_from_center <= 0.15:
            score = 75
            grade = "Inner Ring"
        elif dist_from_center <= 0.30:
            score = 45
            grade = "Outer Ring"
        else:
            score = 15
            grade = "Grazed Edge"

        self.archery_accumulated_score += score
        return score, grade

    # --- 2. HARVEST SPRINT LOGIC ---

    def evaluate_harvest_sprint(self, crops_collected: int, time_remaining: float) -> int:
        """
        Calculates Harvest Sprint score based on gathered crops (max 8) and remaining time.
        Max potential score: 500.
        """
        base_crop_score = min(8, crops_collected) * 50  # up to 400 pts
        time_bonus = int(max(0.0, time_remaining) * 10)  # up to 100 pts (10s remaining = 100 pts)
        total_score = min(500, base_crop_score + time_bonus)
        return total_score

    # --- 3. DENNIS'S FEAST CHALLENGE LOGIC ---

    def start_feast_challenge(self) -> None:
        """Starts a push-your-luck feast against Blacksmith Dennis."""
        self.current_minigame = MINIGAME_FEAST
        self.feast_player_fullness = 0
        self.feast_player_score = 0
        self.feast_dennis_score = random.randint(75, 105)
        self.feast_is_over = False

    def feast_action(self, action_type: str) -> Tuple[bool, str, int, int]:
        """
        Performs a feast turn action:
        - 'roast': +25 score, +20-30 fullness
        - 'mead': +15 score, +10-18 fullness
        - 'pace': +5 score, -10 fullness
        - 'pass': Locks in score and evaluates victory vs Dennis.
        Returns: (is_round_over, outcome_message, current_score, current_fullness)
        """
        if self.feast_is_over:
            return True, "Challenge already completed", self.feast_player_score, self.feast_player_fullness

        if action_type == "roast":
            self.feast_player_score += 25
            self.feast_player_fullness += random.randint(18, 28)
            msg = "Chowed down hearty roast boar! (+25 pts)"
        elif action_type == "mead":
            self.feast_player_score += 15
            self.feast_player_fullness += random.randint(10, 18)
            msg = "Guzzled sparkling honey mead! (+15 pts)"
        elif action_type == "pace":
            self.feast_player_score += 5
            self.feast_player_fullness = max(0, self.feast_player_fullness - 12)
            msg = "Paced breath and digested. (-12 fullness)"
        elif action_type == "pass":
            self.feast_is_over = True
            if self.feast_player_score > self.feast_dennis_score:
                msg = f"Victory! You out-ate Dennis ({self.feast_player_score} vs {self.feast_dennis_score})!"
            else:
                msg = f"Dennis won this round ({self.feast_dennis_score} vs {self.feast_player_score})."
            return True, msg, self.feast_player_score, self.feast_player_fullness
        else:
            msg = "Unknown action."

        # Check for indigestion overflow
        if self.feast_player_fullness > 100:
            self.feast_is_over = True
            self.feast_player_score = max(10, self.feast_player_score // 2)
            msg = "Indigestion! You overate and had to step down! (Score halved)"
            return True, msg, self.feast_player_score, self.feast_player_fullness

        return False, msg, self.feast_player_score, self.feast_player_fullness

    # --- REWARDS & RECORD EVALUATION ---

    def finalize_minigame_score(
        self,
        minigame_id: str,
        score: int,
        season: str = "spring",
        player: Any = None
    ) -> Dict[str, Any]:
        """
        Evaluates final score against tiers, updates high scores, awards prizes,
        and broadcasts rumors across town.
        """
        if minigame_id not in VALID_MINIGAMES:
            return {}

        # Update records
        season_clean = season.lower() if season.lower() in self.seasonal_records else "spring"
        prev_best = self.seasonal_records[season_clean].get(minigame_id, 0)
        is_new_record = score > prev_best
        if is_new_record:
            self.seasonal_records[season_clean][minigame_id] = score
        if score > self.high_scores.get(minigame_id, 0):
            self.high_scores[minigame_id] = score

        # Tier calculation (based on 500 max baseline for archery/harvest, or 120 for feast)
        max_bench = 120 if minigame_id == MINIGAME_FEAST else 500
        ratio = score / float(max_bench)

        if ratio >= 0.85:
            tier = "Gold"
            gold_reward = 80
            items_reward = ["Starlight Crystal", "Festive Honey Bread"]
            title_awarded = {
                MINIGAME_ARCHERY: "Asterra Marksman",
                MINIGAME_HARVEST: "Grand Harvester",
                MINIGAME_FEAST: "Master of Feasts"
            }.get(minigame_id, "Festival Champion")
        elif ratio >= 0.60:
            tier = "Silver"
            gold_reward = 45
            items_reward = ["Silver Ore", "Festive Honey Bread"]
            title_awarded = None
        elif ratio >= 0.35:
            tier = "Bronze"
            gold_reward = 20
            items_reward = ["Festive Honey Bread"]
            title_awarded = None
        else:
            tier = "Participant"
            gold_reward = 5
            items_reward = []
            title_awarded = None

        # Give rewards to player
        if player:
            if hasattr(player, "gold"):
                player.gold += gold_reward
            if hasattr(player, "inventory") and hasattr(player.inventory, "add_item"):
                from rpg.items import create_item
                for it in items_reward:
                    try:
                        item_obj = create_item(it.lower().replace(" ", "_"))
                        if item_obj:
                            player.inventory.add_item(item_obj)
                    except Exception:
                        pass

        # Award Title & Mythos
        if title_awarded and title_awarded not in self.champion_titles_awarded:
            self.champion_titles_awarded.append(title_awarded)
            if player and hasattr(player, "game"):
                if hasattr(player.game, "reputation_manager"):
                    player.game.reputation_manager.active_title = title_awarded

        # Broadcast Rumor
        if self.event_bus:
            self.event_bus.emit(
                "festival_minigame_completed",
                minigame_id=minigame_id,
                score=score,
                tier=tier,
                is_new_record=is_new_record,
                title=title_awarded
            )

            # Seed dynamic gossip into RumorBoard if gold tier
            if tier == "Gold" and self.game_reference and hasattr(self.game_reference, "living_world"):
                rumor_board = getattr(self.game_reference.living_world, "rumors", None)
                if rumor_board and hasattr(rumor_board, "add_custom_rumor"):
                    rumor_board.add_custom_rumor(
                        rumor_id=f"festival_{minigame_id}_win",
                        topic=f"Champion of the {minigame_id.title()} Contest",
                        origin_npc="Dennis",
                        true_content=f"The hero achieved a staggering {score} points in the {minigame_id.title()} festival minigame!",
                        distorted_content=f"Rumors say the hero scored over a thousand points in the festival and drank Dennis under the table!"
                    )

        return {
            "minigame": minigame_id,
            "score": score,
            "tier": tier,
            "gold": gold_reward,
            "items": items_reward,
            "title": title_awarded,
            "is_new_record": is_new_record
        }

    def reset(self) -> None:
        """Resets festival state."""
        self.is_festival_active = False
        self.current_minigame = None
        self.seasonal_records = {
            "spring": {"archery": 0, "harvest": 0, "feast": 0},
            "summer": {"archery": 0, "harvest": 0, "feast": 0},
            "autumn": {"archery": 0, "harvest": 0, "feast": 0},
            "winter": {"archery": 0, "harvest": 0, "feast": 0}
        }
        self.high_scores = {"archery": 0, "harvest": 0, "feast": 0}
        self.champion_titles_awarded = []

    def to_dict(self) -> Dict[str, Any]:
        """Serializes festival manager state."""
        return {
            "is_festival_active": self.is_festival_active,
            "seasonal_records": {s: dict(rec) for s, rec in self.seasonal_records.items()},
            "high_scores": dict(self.high_scores),
            "champion_titles_awarded": list(self.champion_titles_awarded)
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes festival manager state."""
        if not data:
            return
        self.is_festival_active = data.get("is_festival_active", False)
        if "seasonal_records" in data:
            self.seasonal_records = {s: dict(rec) for s, rec in data["seasonal_records"].items()}
        if "high_scores" in data:
            self.high_scores = dict(data["high_scores"])
        if "champion_titles_awarded" in data:
            self.champion_titles_awarded = list(data["champion_titles_awarded"])
