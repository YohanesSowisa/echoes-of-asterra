"""
Echoes of Asterra - Mythos Reader & Legacy Integration Engine
Connects past playthrough records in MythosManager to the active game session.
Injects ancestral relic weapons and legacy armor into procedural dungeons,
generates multi-generational lore dialogues for town NPCs, and applies historical
faction warfare territory inheritance.
"""
from typing import Dict, List, Any, Optional, Tuple
from rpg.dialogue import DialogueNode, DialogueChoice
from rpg.items import create_item, Item


class MythosReader:
    """
    Reads historical run records from MythosManager and injects
    legacy elements (ancestral relics, multi-generational NPC legends, territory inheritance)
    into the active playthrough.
    """
    def __init__(self, game: Any) -> None:
        self.game = game

    @property
    def mythos_manager(self) -> Any:
        if self.game and hasattr(self.game, "mythos_manager"):
            return self.game.mythos_manager
        # Fallback: load directly from MythosManager if game context is omitted (e.g. procedural dungeon generation)
        from rpg.mythos import MythosManager
        return MythosManager()

    def get_ancestral_relic_loot(self) -> List[Tuple[str, int]]:
        """
        Retrieves ancestral relic weapon items based on past hero records.
        Returns loot tuples for insertion into dungeon chests or boss drops.
        """
        if not self.mythos_manager:
            return [("Steel Blade", 1)]

        latest = self.mythos_manager.get_latest_record()
        if latest and "relic_weapon" in latest:
            relic_data = latest["relic_weapon"]
            relic_name = relic_data.get("name", "Ancestral Blade")
            return [(relic_name, 1)]

        relics = self.mythos_manager.get_all_relics()
        if relics:
            relic_name = relics[-1].get("name", "Ancestral Blade")
            return [(relic_name, 1)]

        return [("Steel Blade", 1)]

    def get_ancestral_artifacts(self) -> List[Tuple[str, int]]:
        """
        Retrieves all legacy artifacts (weapon + armor + relics) for procedural dungeon placement.
        """
        if not self.mythos_manager:
            return [("Steel Blade", 1)]

        latest = self.mythos_manager.get_latest_record()
        if latest:
            artifacts: List[Tuple[str, int]] = []
            if "relic_weapon" in latest:
                artifacts.append((latest["relic_weapon"].get("name", "Ancestral Blade"), 1))
            if "relic_armor" in latest:
                artifacts.append((latest["relic_armor"].get("name", "Ancestral Aegis"), 1))
            if artifacts:
                return artifacts

        return [("Steel Blade", 1)]

    def create_ancestral_relic_item(self) -> Optional[Item]:
        """Creates an actual Item object for the latest ancestral relic weapon."""
        if not self.mythos_manager:
            return create_item("Steel Blade")

        latest = self.mythos_manager.get_latest_record()
        if latest and "relic_weapon" in latest:
            rw = latest["relic_weapon"]
            relic_item = create_item(latest.get("favored_weapon", "Steel Blade"))
            if relic_item:
                relic_item.name = rw.get("name", f"Ancestral {relic_item.name}")
                relic_item.rarity = "legendary"
                relic_item.description = rw.get("description", relic_item.description)
                relic_item.stats["atk"] = relic_item.stats.get("atk", 10) + 4
                relic_item.stats["crit"] = relic_item.stats.get("crit", 5) + 5
                return relic_item

        return create_item("Steel Blade")

    def create_ancestral_armor_item(self) -> Optional[Item]:
        """Creates an actual Item object for the latest ancestral relic armor."""
        if not self.mythos_manager:
            return create_item("Leather Chest")

        latest = self.mythos_manager.get_latest_record()
        if latest and "relic_armor" in latest:
            ra = latest["relic_armor"]
            base_armor = latest.get("favored_armor", "Leather Chest")
            armor_item = create_item(base_armor) or create_item("Leather Chest")
            if armor_item:
                armor_item.name = ra.get("name", f"Ancestral {armor_item.name}")
                armor_item.rarity = "legendary"
                armor_item.description = ra.get("description", armor_item.description)
                armor_item.stats["def"] = armor_item.stats.get("def", 5) + 3
                armor_item.stats["hp"] = armor_item.stats.get("hp", 0) + 25
                return armor_item

        return create_item("Leather Chest")

    def build_legend_dialogue_nodes(self) -> List[DialogueNode]:
        """
        Generates multi-generational dialogue nodes for NPCs (Eldrin, Dennis, Mira, Faye)
        referencing past heroes, their ancestors' encounters, and surviving world lore.
        """
        nodes = []
        if not self.mythos_manager:
            return nodes

        latest = self.mythos_manager.get_latest_record()
        if not latest:
            # First run: default folklore dialogue
            nodes.append(DialogueNode(
                "eldrin_mythos_legend",
                "Elder Eldrin",
                "You are the first champion in many generations to brave the shadows of Asterra. Make your own legend!",
                [DialogueChoice("I will not fail Asterra.", None)]
            ))
            return nodes

        hero_name = latest.get("hero_name", "the Ancient Champion")
        hero_title = latest.get("hero_title", "Champion of Asterra")
        favored_weapon = latest.get("favored_weapon", "a noble blade")
        favored_faction = latest.get("favored_faction", "the Knights").title()
        dominant_war_faction = latest.get("dominant_war_faction", "knights").title()
        days = latest.get("days_lived", 1)
        end_cause = latest.get("end_cause", "vanquishing the darkness")

        # 1. Elder Eldrin - Village Lore & Succession
        eldrin_text = (
            f"The village records chronicle that Champion {hero_name}, the {hero_title}, stood guard over Asterra "
            f"for {days} seasons wielding {favored_weapon} before {end_cause.lower()}. "
            f"Their ancestral relics are sealed within deep dungeon vaults."
        )
        nodes.append(DialogueNode(
            "eldrin_mythos_legend",
            "Elder Eldrin",
            eldrin_text,
            [DialogueChoice("I will honor their legacy.", None)]
        ))

        # 2. Blacksmith Dennis - Ancestral Craftsmanship Lore
        dennis_text = (
            f"My grandfather's memoirs speak of forging gear for {hero_name}. "
            f"He crafted {favored_weapon} for their quests. If you explore the sunken crypts, "
            f"you might discover their legendary ancestral relics."
        )
        nodes.append(DialogueNode(
            "dennis_mythos_legend",
            "Blacksmith Dennis",
            dennis_text,
            [DialogueChoice("I will search for their relics.", None)]
        ))

        # 3. Scholar Mira - Historical Faction Warfare Archives
        mira_text = (
            f"Ancient parchment rolls recount how {hero_name} allied with {favored_faction}, "
            f"shifting the territorial balance in favor of the {dominant_war_faction}. "
            f"The aftershocks of their victories still shape our realm's borders today."
        )
        nodes.append(DialogueNode(
            "mira_mythos_legend",
            "Scholar Mira",
            mira_text,
            [DialogueChoice("Fascinating history.", None)]
        ))

        # 4. Ranger Faye - Forest Oral Traditions
        faye_text = (
            f"The forest elders say {hero_name} walked these very game trails generations ago. "
            f"Their bravery inspired our rangers to hold the crossroads against the shadows."
        )
        nodes.append(DialogueNode(
            "faye_mythos_legend",
            "Ranger Faye",
            faye_text,
            [DialogueChoice("Their spirit protects the woods.", None)]
        ))

        return nodes

    def inject_legend_into_dialogue_manager(self, dialogue_manager: Any) -> None:
        """Registers all generated legend dialogue nodes into active DialogueManager."""
        nodes = self.build_legend_dialogue_nodes()
        for node in nodes:
            dialogue_manager.add_node(node)

    def apply_historical_world_buffs(self) -> Dict[str, Any]:
        """
        Applies starting world bonuses & territory inheritance based on historical run records:
        - Faction War territory control inheritance for previous winning faction.
        - Faction reputation starting bonus.
        - Settlement prosperity boost from past civic investments.
        """
        summary = {
            "faction_bonus": None,
            "prosperity_bonus": 0,
            "dominant_faction": None,
            "territory_inherited": False
        }
        if not self.mythos_manager:
            return summary

        # 1. Territory Control Inheritance in Faction Warfare
        fw = getattr(self.game, "faction_war", None)
        if not fw and hasattr(self.game, "living_world"):
            fw = getattr(self.game.living_world, "faction_war", None)
        if fw and hasattr(fw, "apply_mythos_inheritance"):
            dominant = fw.apply_mythos_inheritance(self.mythos_manager)
            if dominant:
                summary["dominant_faction"] = dominant
                summary["territory_inherited"] = True

        # 2. Starting Faction Reputation Boost
        victories = self.mythos_manager.get_faction_victory_counts()
        knights_count = victories.get("knights", 0)
        hunters_count = victories.get("hunters", 0)
        merchants_count = victories.get("merchants", 0)

        if hasattr(self.game, "factions"):
            if knights_count >= hunters_count and knights_count >= merchants_count and knights_count > 0:
                self.game.factions.modify_reputation("knights", 10)
                summary["faction_bonus"] = "knights (+10 starting rep)"
            elif hunters_count >= knights_count and hunters_count >= merchants_count and hunters_count > 0:
                self.game.factions.modify_reputation("hunters", 10)
                summary["faction_bonus"] = "hunters (+10 starting rep)"
            elif merchants_count > 0:
                self.game.factions.modify_reputation("merchants", 10)
                summary["faction_bonus"] = "merchants (+10 starting rep)"

        # 3. Settlement Prosperity Inheritance
        donated_any = any(r.get("donated_shields", False) for r in self.mythos_manager.records)
        if donated_any and hasattr(self.game, "living_world") and hasattr(self.game.living_world, "settlement"):
            if hasattr(self.game.living_world.settlement, "add_prosperity"):
                self.game.living_world.settlement.add_prosperity(5.0)
            elif hasattr(self.game.living_world.settlement, "prosperity"):
                try:
                    self.game.living_world.settlement.prosperity += 5.0
                except Exception as e:
                    import logging
                    logging.getLogger("MythosReader").warning("Could not increment settlement prosperity: %s", e, exc_info=True)
            summary["prosperity_bonus"] = 5

        return summary
