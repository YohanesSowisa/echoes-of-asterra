"""
Echoes of Asterra - Style Scoring System
Evaluates per-encounter combat performance (combos, dodges, parries, elemental reactions,
time-to-kill, damage taken) and computes a S/A/B/C/D grade that influences loot rarity rolls.
"""
from typing import Dict


class StyleGrade:
    """Enumeration of style grades with associated loot rarity modifiers."""
    S = "S"   # +40% legendary chance
    A = "A"   # +20% epic chance
    B = "B"   # Baseline (no modifier)
    C = "C"   # -10% rare chance
    D = "D"   # -25% rare chance

    RARITY_MODIFIERS: Dict[str, float] = {
        "S": 1.40,
        "A": 1.20,
        "B": 1.00,
        "C": 0.90,
        "D": 0.75,
    }

    GRADE_COLORS: Dict[str, tuple] = {
        "S": (255, 215, 0),    # Gold
        "A": (100, 220, 255),  # Cyan
        "B": (200, 200, 200),  # Silver
        "C": (180, 140, 100),  # Bronze
        "D": (120, 120, 120),  # Gray
    }


class StyleScoring:
    """
    Tracks combat performance metrics during a fight and evaluates a final grade.
    One instance is maintained per active combat encounter (reset on encounter start).
    """
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Resets all tracking metrics for a new encounter."""
        self.combo_hits: int = 0
        self.max_combo: int = 0
        self.perfect_dodges: int = 0
        self.parries: int = 0
        self.elemental_reactions: int = 0
        self.finishers_landed: int = 0
        self.hits_taken: int = 0
        self.damage_taken: int = 0
        self.time_elapsed: float = 0.0
        self.kills: int = 0

    def on_combo_hit(self, combo_count: int) -> None:
        """Records a combo hit."""
        self.combo_hits += 1
        self.max_combo = max(self.max_combo, combo_count)

    def on_perfect_dodge(self) -> None:
        """Records a perfect dodge."""
        self.perfect_dodges += 1

    def on_parry(self) -> None:
        """Records a successful parry."""
        self.parries += 1

    def on_elemental_reaction(self) -> None:
        """Records an elemental compound reaction trigger."""
        self.elemental_reactions += 1

    def on_finisher(self) -> None:
        """Records a combo finisher landed."""
        self.finishers_landed += 1

    def on_hit_taken(self, damage: int) -> None:
        """Records damage received by the player."""
        self.hits_taken += 1
        self.damage_taken += damage

    def on_kill(self) -> None:
        """Records an enemy kill."""
        self.kills += 1

    def update(self, dt: float) -> None:
        """Ticks encounter timer."""
        self.time_elapsed += dt

    def evaluate(self) -> str:
        """
        Computes a letter grade (S/A/B/C/D) based on accumulated combat metrics.
        Score formula rewards aggression, precision, and style variety while penalizing damage taken.
        """
        score = 0.0

        # Reward combos (max 25 points)
        score += min(25.0, self.max_combo * 5.0)

        # Reward perfect dodges (max 20 points)
        score += min(20.0, self.perfect_dodges * 10.0)

        # Reward parries (max 20 points)
        score += min(20.0, self.parries * 10.0)

        # Reward elemental reactions (max 15 points)
        score += min(15.0, self.elemental_reactions * 7.5)

        # Reward finishers (max 10 points)
        score += min(10.0, self.finishers_landed * 5.0)

        # Time bonus: faster kills score higher (max 10 points, decays over 30s)
        if self.time_elapsed > 0 and self.kills > 0:
            speed_score = max(0.0, 10.0 - (self.time_elapsed / self.kills) * 0.33)
            score += speed_score

        # Penalty: damage taken (reduces score)
        score -= self.hits_taken * 5.0
        score -= self.damage_taken * 0.1

        # Clamp to 0-100
        score = max(0.0, min(100.0, score))

        # Grade thresholds
        if score >= 80.0:
            return StyleGrade.S
        elif score >= 60.0:
            return StyleGrade.A
        elif score >= 35.0:
            return StyleGrade.B
        elif score >= 15.0:
            return StyleGrade.C
        else:
            return StyleGrade.D

    def get_loot_modifier(self) -> float:
        """Returns the loot rarity drop chance multiplier based on current grade."""
        grade = self.evaluate()
        return StyleGrade.RARITY_MODIFIERS.get(grade, 1.0)

    def get_grade_color(self) -> tuple:
        """Returns the display color for the current grade."""
        grade = self.evaluate()
        return StyleGrade.GRADE_COLORS.get(grade, (200, 200, 200))
