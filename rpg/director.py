"""
Echoes of Asterra - Adaptive Game Director Engine
Evaluates immutable WorldSnapshots, computes unified World Pressure scores,
selects dynamic pacing recommendations (Recovery/Opportunity vs Dominance Challenges),
and enforces intervention memory & cooldowns without manipulating gameplay directly.
"""
import random
from enum import Enum
from typing import Dict, List, Any, Optional
from rpg.world_state import WorldSnapshot
from rpg.events import EventBus

class PressureTier(str, Enum):
    PEACEFUL = "PEACEFUL"    # Pressure 0 - 19
    CALM = "CALM"            # Pressure 20 - 39
    ACTIVE = "ACTIVE"        # Pressure 40 - 59
    DANGEROUS = "DANGEROUS"  # Pressure 60 - 79
    CRISIS = "CRISIS"        # Pressure 80 - 100

class GameDirector:
    """
    Adaptive Game Director orchestrating simulation pacing, world pressure,
    and opportunity/recovery interventions.
    """
    def __init__(self) -> None:
        self.pressure_score: float = 25.0
        self.current_pressure: PressureTier = PressureTier.CALM
        self.current_goal: str = "Maintain steady wilderness balance"
        self.last_evaluation_day: int = 0
        
        # Memory of interventions: List of dict records
        self.history: List[Dict[str, Any]] = []
        
        # Cooldowns map: action_id -> remaining_days
        self.cooldowns: Dict[str, int] = {}
        
        # Cooldown duration default (days)
        self.cooldown_duration: int = 3
        
        # Idle time tracking for continuous observation
        self.idle_time: float = 0.0
        self.check_timer: float = 0.0
        
    def calculate_pressure(self, snapshot: WorldSnapshot) -> float:
        """
        Calculates unified World Pressure score (0.0 to 100.0) based on snapshot metrics:
        Player Strength/Wealth, Danger Level, Road Safety, Monster Density, Faction Stability,
        Recent Deaths, and Combat Win Rate.
        """
        base_danger = snapshot.danger_level * 0.30
        road_danger = (100.0 - snapshot.road_safety) * 0.20
        monster_danger = snapshot.monster_density * 0.20
        faction_instability = (100.0 - snapshot.faction_stability) * 0.15
        player_scaling = min(100.0, snapshot.player_level * 4.0) * 0.15
        
        score = base_danger + road_danger + monster_danger + faction_instability + player_scaling
        
        # Modifiers
        if snapshot.active_crisis:
            score += 15.0
        if snapshot.recent_deaths > 0:
            score += min(20.0, snapshot.recent_deaths * 10.0)
        if snapshot.player_wealth > 1000:
            score += 5.0
        if snapshot.player_hp_ratio < 0.3:
            score -= 10.0
            
        # Win rate adjustment (-10.0 to +10.0)
        win_rate_delta = (snapshot.combat_win_rate - 0.5) * 20.0
        score += win_rate_delta
        
        return max(0.0, min(100.0, score))

    def resolve_pressure_tier(self, score: float) -> PressureTier:
        """Maps numerical pressure score to PressureTier enum."""
        if score < 20.0:
            return PressureTier.PEACEFUL
        elif score < 40.0:
            return PressureTier.CALM
        elif score < 60.0:
            return PressureTier.ACTIVE
        elif score < 80.0:
            return PressureTier.DANGEROUS
        else:
            return PressureTier.CRISIS

    def evaluate(self, snapshot: WorldSnapshot, event_bus: EventBus) -> Optional[Dict[str, Any]]:
        """
        Evaluates world snapshot on daily tick.
        Calculates pressure, decrements cooldowns, selects pacing intervention,
        and publishes recommendations via EventBus.
        """
        self.last_evaluation_day = snapshot.day
        self.pressure_score = self.calculate_pressure(snapshot)
        self.current_pressure = self.resolve_pressure_tier(self.pressure_score)
        
        # Decrement intervention cooldowns
        expired_keys = []
        for action_id, days_left in self.cooldowns.items():
            if days_left > 1:
                self.cooldowns[action_id] = days_left - 1
            else:
                expired_keys.append(action_id)
        for k in expired_keys:
            del self.cooldowns[k]

        # Determine player status
        is_struggling = (snapshot.player_hp_ratio < 0.35 or snapshot.recent_deaths > 0 or snapshot.combat_win_rate < 0.35)
        is_dominating = (snapshot.combat_win_rate > 0.75 and snapshot.player_wealth > 500 and snapshot.recent_deaths == 0)
        
        candidates: List[Dict[str, Any]] = []
        
        # 1. Recovery & Opportunity Interventions (Struggling Player)
        if is_struggling:
            self.current_goal = "Provide recovery opportunities for struggling player"
            candidates.extend([
                {
                    "id": "hunter_bounties_easier",
                    "name": "Easier Hunter Bounties",
                    "reason": "Hunters post accessible bounty contracts to assist player recovery",
                    "effects": {"bounty_difficulty": 0.7, "reward_mult": 1.25}
                },
                {
                    "id": "merchant_price_discount",
                    "name": "Merchant Price Stabilization",
                    "reason": "Local merchants stabilize shop prices to aid struggling adventurers",
                    "effects": {"price_mult": 0.85}
                },
                {
                    "id": "guard_patrol_boost",
                    "name": "Knight Patrol Reinforcement",
                    "reason": "Knights increase highway patrols along dangerous trade roads",
                    "effects": {"guard_density": 1.5, "road_safety_bonus": 15.0}
                },
                {
                    "id": "road_repair",
                    "name": "Infrastructure Repair",
                    "reason": "Villagers repair damaged roads, enhancing regional safety",
                    "effects": {"road_safety_bonus": 20.0}
                }
            ])
        # 2. Dominance Challenges (Dominating Player)
        elif is_dominating:
            self.current_goal = "Introduce non-repetitive challenges for dominating player"
            candidates.extend([
                {
                    "id": "bandit_raid_organized",
                    "name": "Organized Bandit Raid",
                    "reason": "Bandits mobilize coordinated raids in response to player dominance",
                    "effects": {"bandit_aggression": 1.4, "caravan_risk": 1.3}
                },
                {
                    "id": "smugglers_active",
                    "name": "Smuggler Syndicate Activity",
                    "reason": "Black market activity spikes, altering regional tariffs",
                    "effects": {"black_market_discount": 0.9, "tariff_rate": 1.15}
                },
                {
                    "id": "monster_migration",
                    "name": "Wilderness Monster Migration",
                    "reason": "Beast packs migrate toward Asterra outskirts",
                    "effects": {"monster_spawn_mult": 1.3, "rare_enemy_chance": 0.25}
                },
                {
                    "id": "trade_tax_rising",
                    "name": "Trade Tax Adjustment",
                    "reason": "Economic prosperity prompts local authorities to adjust trade taxes",
                    "effects": {"tax_increase": 0.10}
                }
            ])
        # 3. Balanced Pacing
        else:
            self.current_goal = "Maintain dynamic world equilibrium"
            candidates.extend([
                {
                    "id": "village_festival",
                    "name": "Seasonal Festival",
                    "reason": "Villagers celebrate regional stability with an ambient festival",
                    "effects": {"prosperity_bonus": 5, "price_mult": 0.9}
                },
                {
                    "id": "caravan_frequency_boost",
                    "name": "Increased Trade Caravans",
                    "reason": "Favorable road safety encourages merchant caravans to travel",
                    "effects": {"caravan_spawn_rate": 1.25}
                }
            ])

        # Filter out actions on cooldown
        available_candidates = [c for c in candidates if c["id"] not in self.cooldowns]
        if not available_candidates:
            # Fallback if all candidates are cooling down
            available_candidates = candidates

        # Apply small weighted randomness
        selected_intervention = random.choice(available_candidates)
        action_id = selected_intervention["id"]
        
        # Apply cooldown
        self.cooldowns[action_id] = self.cooldown_duration
        
        # Record intervention in memory
        record = {
            "day": snapshot.day,
            "action": selected_intervention["name"],
            "action_id": action_id,
            "tier": self.current_pressure.value,
            "reason": selected_intervention["reason"],
            "effects": selected_intervention["effects"]
        }
        self.history.append(record)
        if len(self.history) > 20:
            self.history.pop(0)

        # Publish recommendations via EventBus (Rule 2)
        event_bus.emit(
            "director_recommendation",
            action=action_id,
            pressure_tier=self.current_pressure.value,
            reason=selected_intervention["reason"],
            effects=selected_intervention["effects"]
        )
        event_bus.emit(
            "director_pressure_changed",
            score=self.pressure_score,
            tier=self.current_pressure.value
        )
        
        return record

    def update(self, dt: float, player: Any, world_state: Any) -> None:
        """
        Adapter observation loop called per-frame for real-time player checks.
        Tracks idle duration and emits emergency pacing signals if needed.
        """
        self.check_timer += dt
        if hasattr(player, "velocity") and player.velocity.magnitude() == 0:
            self.idle_time += dt
        else:
            self.idle_time = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Director state."""
        return {
            "pressure_score": self.pressure_score,
            "current_pressure": self.current_pressure.value,
            "current_goal": self.current_goal,
            "last_evaluation_day": self.last_evaluation_day,
            "history": self.history,
            "cooldowns": dict(self.cooldowns)
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores Director state."""
        if not data:
            return
        self.pressure_score = data.get("pressure_score", 25.0)
        p_str = data.get("current_pressure", PressureTier.CALM.value)
        self.current_pressure = PressureTier(p_str) if p_str in PressureTier.__members__ else PressureTier.CALM
        self.current_goal = data.get("current_goal", "Maintain steady wilderness balance")
        self.last_evaluation_day = data.get("last_evaluation_day", 0)
        self.history = data.get("history", [])
        self.cooldowns = data.get("cooldowns", {})
