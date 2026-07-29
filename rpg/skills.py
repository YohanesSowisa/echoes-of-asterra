"""
Echoes of Asterra - Skill System
Defines castable abilities, cooldown tracking, costs, and level unlock thresholds.
"""
from typing import Dict, List, Any
from rpg.constants import (
    SKILL_SWORD_MASTERY, SKILL_FIREBALL, SKILL_ICE_SPIKE, SKILL_DASH,
    SKILL_HEALING, SKILL_SHIELD, SKILL_LIGHTNING
)

class Skill:
    """
    Represents an active or passive ability.
    Tracks costs (Mana/Stamina), cooldown timers, and unlock status.
    """
    def __init__(
        self,
        name: str,
        cost_type: str,  # "mana" or "stamina"
        cost_val: int,
        level_req: int,
        cooldown: float,  # seconds
        description: str,
        is_passive: bool = False
    ) -> None:
        self.name = name
        self.cost_type = cost_type
        self.cost_val = cost_val
        self.level_req = level_req
        self.cooldown = cooldown
        self.description = description
        self.is_passive = is_passive
        
        self.timer = 0.0  # Remaining cooldown time in seconds
        self.unlocked = False

    def update(self, dt: float) -> None:
        """Ticks down the cooldown timer."""
        if self.timer > 0:
            self.timer = max(0.0, self.timer - dt)

    def is_ready(self, player_level: int) -> bool:
        """Checks if the skill is unlocked and off cooldown."""
        return self.unlocked and self.timer <= 0.0

    def trigger_cooldown(self) -> None:
        """Starts the cooldown timer."""
        self.timer = self.cooldown

class SkillManager:
    """
    Main coordinator of the player's skills.
    Handles level checks, cooldown ticks, and resource deduction for skill casts.
    """
    def __init__(self) -> None:
        self.skills: Dict[str, Skill] = {
            SKILL_SWORD_MASTERY: Skill(
                name=SKILL_SWORD_MASTERY,
                cost_type="mana",
                cost_val=0,
                level_req=1,
                cooldown=0.0,
                description="Passive: Increases your melee damage by 4.",
                is_passive=True
            ),
            SKILL_DASH: Skill(
                name=SKILL_DASH,
                cost_type="stamina",
                cost_val=15,
                level_req=2,
                cooldown=1.2,
                description="Dash forward quickly. Grants briefly invincibility frames."
            ),
            SKILL_HEALING: Skill(
                name=SKILL_HEALING,
                cost_type="mana",
                cost_val=20,
                level_req=3,
                cooldown=5.0,
                description="Uses magic to instantly recover 35 HP."
            ),
            SKILL_FIREBALL: Skill(
                name=SKILL_FIREBALL,
                cost_type="mana",
                cost_val=12,
                level_req=4,
                cooldown=2.0,
                description="Shoots a blazing fireball that deals high magical damage."
            ),
            SKILL_SHIELD: Skill(
                name=SKILL_SHIELD,
                cost_type="mana",
                cost_val=15,
                level_req=5,
                cooldown=8.0,
                description="Conjures a magical shield that absorbs the next incoming hit."
            ),
            SKILL_ICE_SPIKE: Skill(
                name=SKILL_ICE_SPIKE,
                cost_type="mana",
                cost_val=18,
                level_req=6,
                cooldown=3.0,
                description="Fires a frozen shard that slows down enemies on contact."
            ),
            SKILL_LIGHTNING: Skill(
                name=SKILL_LIGHTNING,
                cost_type="mana",
                cost_val=30,
                level_req=7,
                cooldown=10.0,
                description="Strikes all nearby enemies with severe lightning damage."
            )
        }

    def update(self, dt: float) -> None:
        """Updates cooldown timers for all active skills."""
        for skill in self.skills.values():
            skill.update(dt)

    def check_unlocks(self, player_level: int) -> List[str]:
        """
        Unlocks skills whose level requirement has been met.
        Returns a list of newly unlocked skill names.
        """
        unlocked_this_time = []
        for name, skill in self.skills.items():
            if not skill.unlocked and player_level >= skill.level_req:
                skill.unlocked = True
                unlocked_this_time.append(name)
        return unlocked_this_time

    def cast(self, name: str, player: Any) -> bool:
        """
        Tries to cast a skill. Checks resources, deducts cost,
        starts cooldown, and returns True if successful.
        Skill effect execution should be handled externally by the player class.
        """
        skill = self.skills.get(name)
        if not skill or not skill.is_ready(player.level) or skill.is_passive:
            return False

        # Verify resource cost
        if skill.cost_type == "mana":
            if player.mana < skill.cost_val:
                return False
            # Consume mana
            player.mana -= skill.cost_val
        elif skill.cost_type == "stamina":
            if player.stamina < skill.cost_val:
                return False
            # Consume stamina
            player.stamina -= skill.cost_val

        # Put on cooldown
        skill.trigger_cooldown()
        return True
