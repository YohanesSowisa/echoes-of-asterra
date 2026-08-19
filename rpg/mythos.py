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
from rpg.events import EventBus

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
        self.timeline: List[Dict[str, Any]] = []
        self.load_history()

    def register_event_listeners(self, event_bus: EventBus) -> None:
        """Registers global EventBus listeners for timeline tracking."""
        event_bus.subscribe("conspiracy_resolved", self._on_conspiracy_resolved)
        event_bus.subscribe("continental_trade_monopoly_achieved", self._on_trade_monopoly_achieved)
        event_bus.subscribe("syndicate_hq_constructed", self._on_syndicate_hq_constructed)
        event_bus.subscribe("dungeon_sovereignty_established", self._on_dungeon_sovereignty_established)
        event_bus.subscribe("temporal_fabric_mended", self._on_temporal_fabric_mended)

    def _on_conspiracy_resolved(self, ending: str = "total_purge", description: str = "", day: int = 1, **kwargs: Any) -> None:
        self.record_event({
            "event_type": "CONSPIRACY_RESOLVED",
            "category": CATEGORY_WORLD_CHANGE,
            "day": day,
            "actor": "Hero of Asterra",
            "target": "Shadow Syndicate",
            "location": "Asterra Citadel",
            "outcome": description,
            "ending": ending
        })

    def _on_trade_monopoly_achieved(self, title: str = "Merchant Sovereign of Asterra", day: int = 1, **kwargs: Any) -> None:
        self.record_event({
            "event_type": "CONTINENTAL_TRADE_MONOPOLY",
            "category": CATEGORY_WORLD_CHANGE,
            "day": day,
            "actor": title,
            "target": "Continental Trade Network",
            "location": "Asterra Realm",
            "outcome": "Achieved total continental trade monopoly across Asterra with Level 3 Trade Citadels and Automated Courier Relays."
        })

    def _on_syndicate_hq_constructed(self, cost: int = 250, title: str = "The Sovereign Baron", day: int = 1, **kwargs: Any) -> None:
        self.record_event({
            "event_type": "MERCHANT_SYNDICATE_FOUNDED",
            "category": CATEGORY_WORLD_CHANGE,
            "day": day,
            "actor": title,
            "target": "Asterra Merchant Syndicate HQ",
            "location": "Eastern Village District",
            "outcome": "Founded the Asterra Merchant Syndicate HQ and established the Continental Gold Vault banking institution."
        })

    def _on_dungeon_sovereignty_established(self, title: str = "The Lord of the Deep Catacombs", day: int = 1, **kwargs: Any) -> None:
        self.record_event({
            "event_type": "DUNGEON_SOVEREIGNTY_ESTABLISHED",
            "category": CATEGORY_WORLD_CHANGE,
            "day": day,
            "actor": title,
            "target": "Abyssal Vaults",
            "location": "Crypt Catacombs",
            "outcome": "Excavated the 3rd subterranean tier and claimed absolute sovereign mastery as The Lord of the Deep Catacombs."
        })

    def _on_temporal_fabric_mended(self, title: str = "Chrono-Weaver Supreme", total_rewinds: int = 0, day: int = 1, **kwargs: Any) -> None:
        self.record_event({
            "event_type": "TEMPORAL_FABRIC_MENDED",
            "category": CATEGORY_WORLD_CHANGE,
            "day": day,
            "actor": title,
            "target": "Aeon Sentinel",
            "location": "Spacetime Continuum",
            "item": "Aeon Core",
            "amount": 1,
            "faction": None,
            "outcome": f"The Spacetime Continuum was stabilized after defeating the Aeon Sentinel ({total_rewinds} rewinds), earning the title '{title}'."
        })

    def record_event(self, event_data: Dict[str, Any]) -> None:
        """Records a live semantic history event into the active timeline."""
        self.timeline.append(event_data)

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

        # Active Soul Pact details
        active_pact = None
        pact_tier = 1
        if hasattr(game, "pact_manager") and game.pact_manager:
            active_pact = game.pact_manager.state.active_pact_id
            pact_tier = game.pact_manager.state.pact_tier

        if active_pact:
            events.append({
                "event_type": "PRIMORDIAL_PACT_BOUND",
                "category": CATEGORY_WORLD_CHANGE,
                "day": day_count,
                "actor": hero_name,
                "target": f"{active_pact.capitalize()} Altar",
                "location": "World Altar",
                "item": None,
                "amount": pact_tier,
                "faction": None,
                "outcome": f"Bound to {active_pact.capitalize()} Soul Pact at Tier {pact_tier}"
            })

        wm = getattr(game, "world_manager", None)
        if wm and getattr(wm, "leviathan_defeated", False):
            events.append({
                "event_type": "LEVIATHAN_SLAIN",
                "category": CATEGORY_WORLD_CHANGE,
                "day": day_count,
                "actor": hero_name,
                "target": "Morvath, the Mire Leviathan",
                "location": "Submerged Temple",
                "item": "Conduit Core",
                "amount": 1,
                "faction": None,
                "outcome": "The Sunken Mire waters subsided and Asterra's Leylines awakened."
            })

        cm = getattr(game, "conspiracy_manager", None)
        conspiracy_ending = getattr(cm, "conspiracy_ending", None) if cm else None
        if cm and cm.conspiracy_resolved:
            events.append({
                "event_type": "CONSPIRACY_RESOLVED",
                "category": CATEGORY_WORLD_CHANGE,
                "day": day_count,
                "actor": hero_name,
                "target": "The Grand Usurper",
                "location": "Asterra Citadel",
                "item": None,
                "amount": 0,
                "faction": None,
                "outcome": f"Conspiracy resolved with ending: {conspiracy_ending}"
            })

        chr_m = getattr(game, "chrono_manager", None)
        if chr_m and getattr(chr_m, "is_sentinel_defeated", False):
            events.append({
                "event_type": "TEMPORAL_FABRIC_MENDED",
                "category": CATEGORY_WORLD_CHANGE,
                "day": day_count,
                "actor": hero_name,
                "target": "Aeon Sentinel",
                "location": "Spacetime Continuum",
                "item": "Aeon Core",
                "amount": 1,
                "faction": None,
                "outcome": f"Defeated the Aeon Sentinel, stabilized time ({chr_m.total_rewinds_performed} rewinds), and earned title '{chr_m.prestige_title}'"
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
            "active_soul_pact": active_pact,
            "soul_pact_tier": pact_tier,
            "donated_shields": getattr(player, "donated_shields", False),
            "conspiracy_ending": conspiracy_ending,
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

    def get_inherited_starting_epoch(self) -> str:
        """
        Determines the starting Cataclysm Epoch of a subsequent playthrough based on
        the historical deeds, catastrophes, and outcomes of the previous hero.
        """
        if not self.records:
            return "standard"

        last_record = self.records[-1]
        end_cause = str(last_record.get("end_cause", "")).lower()
        events = last_record.get("events", [])

        # 1. Scorched Blight Inheritance
        if (
            "fire" in end_cause or "ruins" in end_cause or "scorch" in end_cause or
            "lava" in end_cause or "flame" in end_cause or "compromised" in end_cause
        ):
            return "scorched"

        # 2. Deluge Epoch Inheritance
        if (
            "mire" in end_cause or "lake" in end_cause or "water" in end_cause or
            "drown" in end_cause or "tide" in end_cause or "rot" in end_cause or
            "leviathan" in end_cause
        ):
            return "deluge"

        # 3. Glacial Winter Inheritance
        if (
            "cave" in end_cause or "frost" in end_cause or "ice" in end_cause or
            "winter" in end_cause or "blizzard" in end_cause
        ):
            return "glacial"

        # Check last events for specific world changes or pacts
        for ev in reversed(events):
            ev_type = ev.get("event_type", "")
            if ev_type == "CONSPIRACY_RESOLVED" and ev.get("ending") == "compromised_kingdom":
                return "scorched"
            if ev_type == "PRIMORDIAL_PACT_BOUND":
                pact = str(ev.get("target", "")).lower()
                if "solar" in pact:
                    return "scorched"
                elif "titan" in pact:
                    return "glacial"
                elif "void" in pact:
                    return "deluge"

        return "standard"

