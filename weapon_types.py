"""
Echoes of Asterra - Weapon Classes & Elemental Combo System
Defines unique gameplay mechanics, movesets, combo lengths, armor piercing, and stun durations
for 5 distinct weapon classes (Sword, Axe, Hammer, Spear, Dagger) and elemental reactions.
"""
from dataclasses import dataclass
from typing import Dict, Tuple
from rpg.constants import (
    WEAPON_SWORD, WEAPON_AXE, WEAPON_HAMMER, WEAPON_SPEAR, WEAPON_DAGGER,
    ELEMENT_FIRE, ELEMENT_ICE, ELEMENT_LIGHTNING, ELEMENT_WIND, ELEMENT_POISON
)

@dataclass
class WeaponClassData:
    """Attributes and combat properties for a specific weapon class."""
    name: str
    attack_speed: float        # Swing duration in seconds
    range_multiplier: float    # Melee sweep reach multiplier
    combo_length: int          # Hits required to trigger finisher
    finisher_damage_mult: float# Damage multiplier on finisher hit
    finisher_aoe: bool         # Whether finisher hits in 360 radius
    stun_duration: float       # Stun duration in seconds applied to defender
    armor_pierce: float        # Fraction (0.0 to 1.0) of enemy defense ignored

WEAPON_CLASSES: Dict[str, WeaponClassData] = {
    WEAPON_SWORD: WeaponClassData(
        name="Sword",
        attack_speed=0.25,
        range_multiplier=1.0,
        combo_length=5,
        finisher_damage_mult=1.5,
        finisher_aoe=True,
        stun_duration=0.0,
        armor_pierce=0.0
    ),
    WEAPON_AXE: WeaponClassData(
        name="Axe",
        attack_speed=0.45,
        range_multiplier=1.0,
        combo_length=5,
        finisher_damage_mult=2.0,
        finisher_aoe=False,
        stun_duration=0.0,
        armor_pierce=0.50  # Pierces 50% defense
    ),
    WEAPON_HAMMER: WeaponClassData(
        name="Hammer",
        attack_speed=0.60,
        range_multiplier=0.85,
        combo_length=5,
        finisher_damage_mult=2.0,
        finisher_aoe=True,
        stun_duration=0.60,  # 0.6s stun
        armor_pierce=0.20
    ),
    WEAPON_SPEAR: WeaponClassData(
        name="Spear",
        attack_speed=0.35,
        range_multiplier=1.60,  # Extended thrust range
        combo_length=5,
        finisher_damage_mult=1.8,
        finisher_aoe=False,
        stun_duration=0.0,
        armor_pierce=0.15
    ),
    WEAPON_DAGGER: WeaponClassData(
        name="Dagger",
        attack_speed=0.14,  # Rapid attacks
        range_multiplier=0.70,
        combo_length=5,
        finisher_damage_mult=1.4,
        finisher_aoe=False,
        stun_duration=0.0,
        armor_pierce=0.0
    ),
}

@dataclass
class ElementalReaction:
    """Defines elemental interaction triggers and status effects."""
    name: str
    effect_type: str  # "dot", "stun", "aoe_chain", "miasma"
    damage: int
    duration: float

ELEMENTAL_REACTIONS: Dict[Tuple[str, str], ElementalReaction] = {
    (ELEMENT_FIRE, "oil"): ElementalReaction("Ignite", "dot", 6, 3.0),
    (ELEMENT_ICE, "wet"): ElementalReaction("Freeze", "stun", 0, 2.0),
    (ELEMENT_LIGHTNING, "wet"): ElementalReaction("Overload", "aoe_chain", 15, 0.0),
    (ELEMENT_WIND, ELEMENT_POISON): ElementalReaction("Miasma", "miasma", 10, 2.5),
}
