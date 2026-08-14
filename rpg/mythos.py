"""
Echoes of Asterra - Mythos Inheritance System
Manages persistent world legacy across playthroughs.
Saves past run metadata (hero build, legendary choices, faction victories, ancestral weapons)
into a lightweight mythos_history.json file. Past runs become the ancient folklore, statues,
and buried crypt relics of future world generations.
"""
import os
import json
import random
from typing import Dict, List, Any, Optional, TypedDict

# Event Taxonomy Constants
CATEGORY_COMBAT = "COMBAT"
CATEGORY_ECONOMY = "ECONOMY"
CATEGORY_SETTLEMENT = "SETTLEMENT"
CATEGORY_FACTION = "FACTION"
CATEGORY_ARTIFACT = "ARTIFACT"
CATEGORY_WORLD_CHANGE = "WORLD_CHANGE"

MYTHOS_SCHEMA_VERSION = 1
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MYTHOS_FILE_PATH = os.path.join(BASE_DIR, "saves", "mythos_history.json")


class MythosEventDict(TypedDict, total=False):
    """Strongly-typed structure for historical mythos events."""
    event_type: str
    category: str
    day: int
    actor: str
    target: Optional[str]
    location: Optional[str]
    item: Optional[str]
    amount: int
    faction: Optional[str]
    outcome: str

class MythosRecordDict(TypedDict, total=False):
    """Strongly-typed structure for past hero run records."""
    hero_name: str
    run_id: str
    days_lived: int
    end_cause: str
    favored_weapon: str
    favored_faction: str
    hero_level: int
    donated_shields: bool
    events: List[MythosEventDict]
    relic_weapon: Dict[str, Any]

class MythosManager:
    """
    Decoupled historical legacy & semantic knowledge layer.
    Saves past run metadata and structured event logs into mythos_history.json.
    Exposes high-level semantic query APIs for world gen, NPCs, economy, dungeons, and factions.
    """
    def __init__(self) -> None:
        self.version = MYTHOS_SCHEMA_VERSION
        self.records: List[MythosRecordDict] = []
        self.load_history()

    def load_history(self) -> None:
        """Loads past mythos records with backward-compatible schema handling."""
        if not os.path.exists(MYTHOS_FILE_PATH):
            self.records = []
            return
        try:
            with open(MYTHOS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "records" in data:
                    self.records = data.get("records", [])
                elif isinstance(data, list):
                    self.records = data
                else:
                    self.records = []
        except Exception as e:
            print(f"Echoes of Asterra: Mythos load warning ({e}). Initializing clean history.")
            self.records = []

    def save_history(self) -> None:
        """Saves current mythos records with schema version header."""
        os.makedirs(os.path.dirname(MYTHOS_FILE_PATH), exist_ok=True)
        payload = {
            "version": self.version,
            "records": self.records
        }
        try:
            with open(MYTHOS_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"Echoes of Asterra: Mythos save error ({e}).")

    def record_run(self, game: Any, end_cause: str = "Retired in Glory") -> Dict[str, Any]:
        """
        Extracts compact metadata and structured timeline event log from a run into mythos history.
        """
        player = game.player
        ws = getattr(game, "world_state", None)
        day_count = getattr(ws, "day", 1) if ws else 1
        hero_name = getattr(player, "name", "Champion Asterra")
        
        # Active weapon
        # Active weapon & armor
        from rpg.constants import ITEM_WEAPON, ITEM_ARMOR
        weapon_item = player.equipment.slots.get(ITEM_WEAPON)
        weapon_name = weapon_item.name if weapon_item else "Iron Dagger"
        armor_item = player.equipment.slots.get(ITEM_ARMOR)
        armor_name = armor_item.name if armor_item else "Leather Tunic"

        # Hero Title / Achievements
        hero_title = "Hero of Asterra"
        if hasattr(game, "reputation_manager") and getattr(game.reputation_manager, "active_title", None):
            hero_title = game.reputation_manager.active_title

        # Faction alignment
        favored_faction = "knights"
        if hasattr(game, "factions"):
            k_rep = game.factions.get_reputation("knights")
            h_rep = game.factions.get_reputation("hunters")
            m_rep = game.factions.get_reputation("merchants")
            if h_rep > k_rep and h_rep > m_rep:
                favored_faction = "hunters"
            elif m_rep > k_rep and m_rep > h_rep:
                favored_faction = "merchants"

        # Faction Warfare Dominance
        dominant_war_faction = favored_faction
        controlled_territories = []
        fw = getattr(game, "faction_war", None)
        if not fw and hasattr(game, "living_world"):
            fw = getattr(game.living_world, "faction_war", None)
        if fw and hasattr(fw, "control_points"):
            f_counts: Dict[str, int] = {}
            for cp in fw.control_points.values():
                f_counts[cp.controlling_faction] = f_counts.get(cp.controlling_faction, 0) + 1
            if f_counts:
                dominant_war_faction = max(f_counts, key=f_counts.get)
            controlled_territories = [cp.name for cp in fw.control_points.values() if cp.controlling_faction == dominant_war_faction]

        # Structured Semantic Events Log
        events = []
        if getattr(player, "donated_shields", False):
            events.append({
                "event_type": "TOWN_SECURITY_DONATION",
                "category": CATEGORY_SETTLEMENT,
                "day": day_count,
                "actor": hero_name,
                "target": "Blacksmith Dennis",
                "location": "Village",
                "item": "Iron Ore",
                "amount": 5,
                "faction": "knights",
                "outcome": "Town Guard Shields Forged (-15% Shop Tax)"
            })
        if getattr(player, "greed_curse_active", False):
            events.append({
                "event_type": "GREED_CURSE_ACTIVATED",
                "category": CATEGORY_WORLD_CHANGE,
                "day": day_count,
                "actor": hero_name,
                "target": "Ancient Greed Altar",
                "location": "Crypt",
                "item": None,
                "amount": 0,
                "faction": None,
                "outcome": "Enemies ATK +50%, Chest & Boss Loot Doubled"
            })

        p_atk = getattr(player, "atk", getattr(player, "base_atk", 10))
        p_def = getattr(player, "defense", getattr(player, "base_def", 5))

        relic_weapon = {
            "name": f"Ancestral {weapon_name}",
            "item_type": ITEM_WEAPON,
            "rarity": "legendary",
            "stats": {"atk": max(12, p_atk + 4), "crit": 10},
            "description": f"The ancient blade wielded by Champion {hero_name}, the {hero_title} on Day {day_count}."
        }

        relic_armor = {
            "name": f"{hero_name}'s Aegis of {hero_title.replace(' ', '')}",
            "item_type": ITEM_ARMOR,
            "rarity": "legendary",
            "stats": {"def": max(8, p_def + 3), "hp": 25},
            "description": f"Legendary protective armor passed down from {hero_name} ({hero_title})."
        }

        record = {
            "hero_name": hero_name,
            "hero_title": hero_title,
            "run_id": f"run_{len(self.records) + 1}",
            "days_lived": day_count,
            "end_cause": end_cause,
            "favored_weapon": weapon_name,
            "favored_armor": armor_name,
            "favored_faction": favored_faction,
            "dominant_war_faction": dominant_war_faction,
            "controlled_territories": controlled_territories,
            "hero_level": player.level,
            "donated_shields": getattr(player, "donated_shields", False),
            "events": events,
            "relic_weapon": relic_weapon,
            "relic_armor": relic_armor,
            "legacy_artifacts": [relic_weapon, relic_armor]
        }
        
        self.records.append(record)
        self.save_history()
        return record

    # --- SAFE PUBLIC KNOWLEDGE QUERY APIs ---

    def query_events(self, **filters: Any) -> List[MythosEventDict]:
        """
        Unified multi-field filter query for historical events.
        Supported keyword filters: category, location, actor, target, faction, event_type.
        """
        matched = []
        for r in self.records:
            for ev in r.get("events", []):
                match = True
                for k, v in filters.items():
                    if v is not None and ev.get(k) != v:
                        match = False
                        break
                if match:
                    matched.append(ev)
        return matched

    def get_latest_record(self) -> Optional[MythosRecordDict]:
        """Returns the most recent past run record safely."""
        if self.records:
            return self.records[-1]
        return None

    def get_random_past_legend(self) -> Optional[MythosRecordDict]:
        """Returns a random past hero record for bards & NPCs safely."""
        if self.records:
            return random.choice(self.records)
        return None

    def get_greatest_hero_by_faction(self, faction: str) -> Optional[MythosRecordDict]:
        """Returns the highest-level past hero aligned with a specific faction."""
        aligned = [r for r in self.records if r.get("favored_faction") == faction]
        if not aligned:
            return None
        return max(aligned, key=lambda r: (r.get("hero_level", 1), r.get("days_lived", 1)))

    def get_events_by_category(self, category: str) -> List[MythosEventDict]:
        """Convenience wrapper around query_events for category filtering."""
        return self.query_events(category=category)

    def get_events_by_location(self, location: str) -> List[MythosEventDict]:
        """Convenience wrapper around query_events for location filtering."""
        return self.query_events(location=location)

    def get_all_relics(self) -> List[Dict[str, Any]]:
        """Returns list of all ancestral relic items across all past runs."""
        relics = []
        for r in self.records:
            if "relic_weapon" in r:
                relics.append(r["relic_weapon"])
        return relics

    def get_all_legacy_artifacts(self) -> List[Dict[str, Any]]:
        """Returns list of all legacy weapons, armors, and relics across all runs."""
        artifacts = []
        for r in self.records:
            if "legacy_artifacts" in r and isinstance(r["legacy_artifacts"], list):
                artifacts.extend(r["legacy_artifacts"])
            elif "relic_weapon" in r:
                artifacts.append(r["relic_weapon"])
        return artifacts

    def get_dominant_war_faction(self) -> Optional[str]:
        """Returns the winning/dominant faction from the most recent run."""
        latest = self.get_latest_record()
        if latest and "dominant_war_faction" in latest:
            return latest["dominant_war_faction"]
        return None

    def get_faction_victory_counts(self) -> Dict[str, int]:
        """Returns counts of historical faction victories for starting world gen alignment."""
        counts = {"knights": 0, "hunters": 0, "merchants": 0}
        for r in self.records:
            fac = r.get("dominant_war_faction") or r.get("favored_faction", "knights")
            counts[fac] = counts.get(fac, 0) + 1
        return counts
