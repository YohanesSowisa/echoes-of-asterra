"""
Echoes of Asterra - Evolution & Developer Telemetry Balance Engine
Centralized, data-driven balance engine featuring:
- Configurable Growth Profiles (early_fast, medium, slow, boss)
- Behavior Layer Tags (PACK_TACTICS, DEFENSIVE_PARRY, RANGED_KITE, RETREAT_LOW_HP, BERSERK)
- Global Difficulty Profiles (EXPLORER, NORMAL, VETERAN, NIGHTMARE)
- Living Danger Score Engine (Combat + Environment + Regional State + Player Status + Guard Support)
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Tuple, Any, Optional

class ScalingPolicy(Enum):
    """Defines how an enemy's level scales relative to player/region."""
    STATIC = auto()      # Fixed level (e.g. Critters, Level 1)
    SOFT_SCALE = auto()  # Soft regional scaling with level clamps
    FULL_SCALE = auto()  # Dynamic full scaling (Rival Champions, Bosses)
    FLOOR_BASED = auto() # Scaled purely by Dungeon Floor depth

class BehaviorTag(Enum):
    """Behavioral layers assigned to enemy archetypes."""
    PACK_TACTICS = auto()    # Coordinates attack with nearby pack members
    DEFENSIVE_PARRY = auto() # Enters parry stance when attacked
    RANGED_KITE = auto()     # Maintains distance away from player
    RETREAT_LOW_HP = auto()  # Flees when health drops below 25%
    BERSERK = auto()         # Increases ATK & Speed at low health

# --- COMPONENT 1: CONFIGURABLE GROWTH PROFILES ---
@dataclass
class GrowthProfile:
    """Polynomial coefficients (a * L + b * L^2) for stat growth."""
    lin_coeff: float
    quad_coeff: float

GROWTH_PROFILES: Dict[str, GrowthProfile] = {
    "early_fast": GrowthProfile(lin_coeff=0.12, quad_coeff=0.003),
    "medium": GrowthProfile(lin_coeff=0.08, quad_coeff=0.002),
    "slow": GrowthProfile(lin_coeff=0.05, quad_coeff=0.001),
    "boss": GrowthProfile(lin_coeff=0.15, quad_coeff=0.005),
}

# --- COMPONENT 4: GLOBAL DIFFICULTY PROFILES ---
@dataclass
class DifficultyProfile:
    name: str
    hp_mult: float
    dmg_mult: float
    xp_mult: float
    potion_heal_mult: float
    ai_aggro_mult: float

DIFFICULTY_PROFILES: Dict[str, DifficultyProfile] = {
    "explorer": DifficultyProfile("Explorer", hp_mult=0.75, dmg_mult=0.70, xp_mult=1.20, potion_heal_mult=1.30, ai_aggro_mult=0.70),
    "normal": DifficultyProfile("Normal", hp_mult=1.00, dmg_mult=1.00, xp_mult=1.00, potion_heal_mult=1.00, ai_aggro_mult=1.00),
    "veteran": DifficultyProfile("Veteran", hp_mult=1.30, dmg_mult=1.35, xp_mult=1.15, potion_heal_mult=0.85, ai_aggro_mult=1.30),
    "nightmare": DifficultyProfile("Nightmare", hp_mult=1.70, dmg_mult=1.75, xp_mult=1.30, potion_heal_mult=0.65, ai_aggro_mult=1.60),
}

# --- REGIONAL BALANCE DEFINITIONS ---
@dataclass
class RegionBalance:
    name: str
    min_level: int
    max_level: int
    scaling_factor: float

REGION_BALANCES: Dict[str, RegionBalance] = {
    "village": RegionBalance(name="Village Fields", min_level=1, max_level=5, scaling_factor=0.05),
    "forest": RegionBalance(name="Forest Crossroads", min_level=5, max_level=10, scaling_factor=0.15),
    "lake": RegionBalance(name="Lake Sanctuary", min_level=10, max_level=15, scaling_factor=0.25),
    "cave": RegionBalance(name="Deep Caverns", min_level=15, max_level=20, scaling_factor=0.30),
    "ruins": RegionBalance(name="Ancient Ruins", min_level=20, max_level=30, scaling_factor=0.35),
    "crypt": RegionBalance(name="Endless Crypt", min_level=10, max_level=100, scaling_factor=0.50),
}

# --- ENEMY ARCHETYPE BALANCE DEFINITIONS ---
@dataclass
class EnemyBalance:
    base_level: int
    policy: ScalingPolicy
    hp_base: int
    atk_base: int
    def_base: int
    xp_base: int
    gold_base: int
    hp_profile_key: str = "medium"
    atk_profile_key: str = "medium"
    behaviors: List[BehaviorTag] = field(default_factory=list)
    abilities_by_level: Dict[int, str] = field(default_factory=dict)

ENEMY_BALANCES: Dict[str, EnemyBalance] = {
    "slime": EnemyBalance(
        base_level=1,
        policy=ScalingPolicy.SOFT_SCALE,
        hp_base=30, atk_base=9, def_base=1, xp_base=8, gold_base=3,
        hp_profile_key="early_fast", atk_profile_key="slow",
        behaviors=[BehaviorTag.RETREAT_LOW_HP],
        abilities_by_level={5: "Split Slime", 10: "Acid Splash"}
    ),
    "wolf": EnemyBalance(
        base_level=3,
        policy=ScalingPolicy.SOFT_SCALE,
        hp_base=55, atk_base=12, def_base=2, xp_base=16, gold_base=6,
        hp_profile_key="medium", atk_profile_key="medium",
        behaviors=[BehaviorTag.PACK_TACTICS, BehaviorTag.BERSERK],
        abilities_by_level={5: "Pounce Dash", 10: "Pack Howl", 15: "Bleeding Strike"}
    ),

    "bandit": EnemyBalance(
        base_level=5,
        policy=ScalingPolicy.SOFT_SCALE,
        hp_base=80, atk_base=22, def_base=4, xp_base=25, gold_base=10,
        hp_profile_key="medium", atk_profile_key="medium",
        behaviors=[BehaviorTag.DEFENSIVE_PARRY, BehaviorTag.RETREAT_LOW_HP],
        abilities_by_level={5: "Parry Stance", 10: "Smoke Bomb", 15: "Execute Strike"}
    ),
    "skeleton": EnemyBalance(
        base_level=8,
        policy=ScalingPolicy.SOFT_SCALE,
        hp_base=95, atk_base=26, def_base=5, xp_base=35, gold_base=12,
        hp_profile_key="medium", atk_profile_key="medium",
        behaviors=[BehaviorTag.DEFENSIVE_PARRY],
        abilities_by_level={5: "Shield Wall", 10: "Whirlwind"}
    ),
    "mage": EnemyBalance(
        base_level=10,
        policy=ScalingPolicy.SOFT_SCALE,
        hp_base=60, atk_base=28, def_base=2, xp_base=40, gold_base=15,
        hp_profile_key="slow", atk_profile_key="medium",
        behaviors=[BehaviorTag.RANGED_KITE],
        abilities_by_level={5: "Mana Shield", 10: "Teleport", 15: "Chain Lightning"}
    ),
    "boss": EnemyBalance(
        base_level=15,
        policy=ScalingPolicy.FULL_SCALE,
        hp_base=450, atk_base=48, def_base=10, xp_base=250, gold_base=100,
        hp_profile_key="boss", atk_profile_key="boss",
        behaviors=[BehaviorTag.BERSERK, BehaviorTag.DEFENSIVE_PARRY],
        abilities_by_level={5: "Ground Slam", 10: "Enrage", 15: "Cataclysm"}
    ),
    "forest_guardian": EnemyBalance(
        base_level=6,
        policy=ScalingPolicy.SOFT_SCALE,
        hp_base=250, atk_base=22, def_base=5, xp_base=100, gold_base=40,
        hp_profile_key="medium", atk_profile_key="medium",
        behaviors=[BehaviorTag.BERSERK, BehaviorTag.PACK_TACTICS],
        abilities_by_level={3: "Nature Roar", 6: "Thorn Charge", 10: "Root Snare"}
    ),
    "bandit_leader": EnemyBalance(
        base_level=10,
        policy=ScalingPolicy.SOFT_SCALE,
        hp_base=320, atk_base=28, def_base=6, xp_base=140, gold_base=60,
        hp_profile_key="medium", atk_profile_key="medium",
        behaviors=[BehaviorTag.DEFENSIVE_PARRY, BehaviorTag.BERSERK],
        abilities_by_level={5: "Parry Riposte", 8: "Smoke Bomb", 12: "Execute Strike"}
    ),
    "critter": EnemyBalance(
        base_level=1,
        policy=ScalingPolicy.STATIC,
        hp_base=5, atk_base=1, def_base=0, xp_base=2, gold_base=1,
        hp_profile_key="slow", atk_profile_key="slow",
        behaviors=[BehaviorTag.RETREAT_LOW_HP],
        abilities_by_level={}
    )
}


# --- TUNABLE GROWTH CURVES ENGINE ---
class GrowthCurve:
    """Calculates stat growth using configurable polynomial growth profiles."""
    @staticmethod
    def calculate_hp(base_hp: int, level: int, profile_key: str = "medium") -> int:
        prof = GROWTH_PROFILES.get(profile_key, GROWTH_PROFILES["medium"])
        lvl_eff = max(0, level - 1)
        mult = 1.0 + prof.lin_coeff * lvl_eff + prof.quad_coeff * (lvl_eff ** 2)
        return int(base_hp * mult)

    @staticmethod
    def calculate_atk(base_atk: int, level: int, profile_key: str = "medium") -> int:
        prof = GROWTH_PROFILES.get(profile_key, GROWTH_PROFILES["medium"])
        lvl_eff = max(0, level - 1)
        mult = 1.0 + prof.lin_coeff * lvl_eff + prof.quad_coeff * (lvl_eff ** 2)
        return int(base_atk * mult)

    @staticmethod
    def calculate_xp(base_xp: int, level: int) -> int:
        lvl_eff = max(0, level - 1)
        mult = 1.0 + 0.05 * lvl_eff
        return int(base_xp * mult)

    @staticmethod
    def calculate_gold(base_gold: int, level: int) -> int:
        lvl_eff = max(0, level - 1)
        mult = 1.0 + 0.04 * lvl_eff
        return int(base_gold * mult)

# --- LEVEL CALCULATION ENGINE ---
def compute_enemy_level(
    enemy_key: str,
    map_name: str,
    player_level: int,
    floor_depth: int = 1
) -> int:
    """Computes an enemy's scaled level dynamically based on region, policy, and player level."""
    bal = ENEMY_BALANCES.get(enemy_key, ENEMY_BALANCES["slime"])
    
    if bal.policy == ScalingPolicy.STATIC:
        return bal.base_level
        
    if bal.policy == ScalingPolicy.FLOOR_BASED:
        return max(bal.base_level, 10 + (floor_depth - 1) * 2)

    reg_key = map_name.replace("map_", "").lower()
    reg = REGION_BALANCES.get(reg_key, REGION_BALANCES["village"])
    
    if bal.policy == ScalingPolicy.FULL_SCALE:
        raw_lvl = player_level
    else:
        raw_lvl = bal.base_level + int((player_level - bal.base_level) * reg.scaling_factor)

    return max(reg.min_level, min(reg.max_level, raw_lvl))

def compute_reward_multiplier(enemy_level: int, player_level: int) -> float:
    """Scales XP & Gold rewards based on level difference."""
    if player_level <= 0:
        return 1.0
    level_ratio = enemy_level / float(player_level)
    return max(0.2, min(2.5, level_ratio ** 0.85))

# --- COMPONENT 2: LIVING DANGER SCORE ENGINE ---
@dataclass
class LivingDangerScore:
    score: int
    category: str       # "PEACEFUL", "SAFE", "MODERATE", "DANGEROUS", "DEADLY"
    combat_power: int
    environment_mult: float
    simulation_mult: float
    reward_mult: float

class LivingDangerEngine:
    """
    Evaluates total Living Danger Score incorporating Combat, Environment (Weather/Night),
    Regional State (Crises/Prosperity/Road Safety), and Player Health/Curse Status.
    """
    @staticmethod
    def calculate(
        enemies: List[Any],
        player: Any,
        map_name: str = "village",
        time_of_day: str = "day",       # "day", "night"
        weather_type: str = "clear",    # "clear", "rain", "storm"
        road_safety: float = 50.0,
        has_watchtower: bool = False,
        is_crisis_active: bool = False
    ) -> LivingDangerScore:
        if not player:
            return LivingDangerScore(0, "PEACEFUL", 0, 1.0, 1.0, 1.0)

        # 1. Combat Power
        total_combat_power = 0
        for e in enemies:
            e_lvl = getattr(e, "level", 1)
            e_hp = getattr(e, "max_hp", 30)
            e_atk = getattr(e, "atk", 5)
            power = int(e_hp * 0.4 + e_atk * 4.0 + e_lvl * 8.0)
            if getattr(e, "is_boss", False):
                power *= 3.0
            total_combat_power += power

        count = len(enemies)
        count_mult = 1.0 + (count - 1) * 0.15 if count > 1 else 1.0

        # 2. Environmental Multipliers
        env_mult = 1.0
        if time_of_day == "night":
            env_mult *= 1.25
        if weather_type == "rain":
            env_mult *= 1.10
        elif weather_type == "storm":
            env_mult *= 1.30

        # 3. Regional Simulation Multipliers
        sim_mult = 1.0
        if is_crisis_active:
            sim_mult *= 1.35
        if road_safety < 30.0:
            sim_mult *= 1.20
        if has_watchtower:
            sim_mult *= 0.85  # Watchtower protects town region

        # 4. Player Health & Curse Modifiers
        player_hp_ratio = player.hp / max(1.0, float(player.max_hp))
        if player_hp_ratio < 0.3:
            sim_mult *= 1.30  # Critical health danger boost
        if getattr(player, "greed_curse_active", False):
            sim_mult *= 1.50  # Greed curse doubles world danger

        final_score = int(total_combat_power * count_mult * env_mult * sim_mult)
        
        # Determine Category
        if final_score < 30:
            category = "PEACEFUL"
            reward_mult = 0.8
        elif final_score < 100:
            category = "SAFE"
            reward_mult = 1.0
        elif final_score < 250:
            category = "MODERATE"
            reward_mult = 1.25
        elif final_score < 500:
            category = "DANGEROUS"
            reward_mult = 1.6
        else:
            category = "DEADLY"
            reward_mult = 2.2

        return LivingDangerScore(
            score=final_score,
            category=category,
            combat_power=int(total_combat_power * count_mult),
            environment_mult=env_mult,
            simulation_mult=sim_mult,
            reward_mult=reward_mult
        )
