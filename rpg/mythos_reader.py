"""
Echoes of Asterra - Mythos Reader & Legacy Integration Engine
Connects past playthrough records in MythosManager to the active game session.
Injects ancestral relic weapons into procedural dungeons, generates legend dialogue nodes
for town NPCs, and applies historical world alignment bonuses.
"""
from typing import Dict, List, Any, Optional, Tuple
from rpg.dialogue import DialogueNode, DialogueChoice
from rpg.items import create_item, Item


class MythosReader:
    """
    Reads historical run records from MythosManager and injects
    legacy elements (ancestral relics, NPC legends, historical world buffs)
    into the active playthrough.
    """
    def __init__(self, game: Any) -> None:
        self.game = game

    @property
    def mythos_manager(self) -> Any:
        return getattr(self.game, "mythos_manager", None)

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

    def create_ancestral_relic_item(self) -> Optional[Item]:
        """Creates an actual Item object for the latest ancestral relic weapon."""
        if not self.mythos_manager:
            return create_item("Steel Blade")

        latest = self.mythos_manager.get_latest_record()
        if latest and "relic_weapon" in latest:
            rw = latest["relic_weapon"]
            relic_item = create_item(rw.get("favored_weapon", "Steel Blade"))
            if relic_item:
                relic_item.name = rw.get("name", f"Ancestral {relic_item.name}")
                relic_item.rarity = "legendary"
                relic_item.description = rw.get("description", relic_item.description)
                relic_item.stats["atk"] = relic_item.stats.get("atk", 10) + 4
                relic_item.stats["crit"] = relic_item.stats.get("crit", 5) + 5
                return relic_item

        return create_item("Steel Blade")

    def build_legend_dialogue_nodes(self) -> List[DialogueNode]:
        """
        Generates dialogue nodes for NPCs (Eldrin, Dennis, Mira) referencing
        past heroes, their weapons, and surviving lore.
        """
        nodes = []
        if not self.mythos_manager:
            return nodes

        latest = self.mythos_manager.get_latest_record()
        if not latest:
            # First run: default lore dialogue
            nodes.append(DialogueNode(
                "eldrin_mythos_legend",
                "Elder Eldrin",
                "You are the first champion in many generations to brave the shadows of Asterra. Make your own legend!",
                [DialogueChoice("I will not fail Asterra.", None)]
            ))
            return nodes

        hero_name = latest.get("hero_name", "the Ancient Champion")
        favored_weapon = latest.get("favored_weapon", "a noble blade")
        days = latest.get("days_lived", 1)
        end_cause = latest.get("end_cause", "vanquishing the darkness")

        # Elder Eldrin legend node
        eldrin_text = (
            f"Before you arrived, Champion {hero_name} fought for Asterra, wielding {favored_weapon} "
            f"for {days} days before {end_cause.lower()}. Their legacy echoes in the Crypt vaults."
        )
        nodes.append(DialogueNode(
            "eldrin_mythos_legend",
            "Elder Eldrin",
            eldrin_text,
            [DialogueChoice("I will honor their legacy.", None)]
        ))

        # Blacksmith Dennis legend node
        dennis_text = (
            f"Ah, {hero_name}... I remember forging gear for them. "
            f"They favored {favored_weapon}. If you search the deep caverns, you might find an ancestral blade."
        )
        nodes.append(DialogueNode(
            "dennis_mythos_legend",
            "Blacksmith Dennis",
            dennis_text,
            [DialogueChoice("I'll keep an eye out for it.", None)]
        ))

        return nodes

    def inject_legend_into_dialogue_manager(self, dialogue_manager: Any) -> None:
        """Registers all generated legend dialogue nodes into active DialogueManager."""
        nodes = self.build_legend_dialogue_nodes()
        for node in nodes:
            dialogue_manager.add_node(node)

    def apply_historical_world_buffs(self) -> Dict[str, Any]:
        """
        Applies starting world bonuses based on historical run records
        (e.g., faction standing boost if past runs favored a faction).
        """
        summary = {"faction_bonus": None, "prosperity_bonus": 0}
        if not self.mythos_manager:
            return summary

        victories = self.mythos_manager.get_faction_victory_counts()
        knights_count = victories.get("knights", 0)
        hunters_count = victories.get("hunters", 0)

        if hasattr(self.game, "factions"):
            if knights_count > hunters_count:
                self.game.factions.modify_reputation("knights", 10)
                summary["faction_bonus"] = "knights (+10 starting rep)"
            elif hunters_count > knights_count:
                self.game.factions.modify_reputation("hunters", 10)
                summary["faction_bonus"] = "hunters (+10 starting rep)"

        # Check past shield donations for settlement boost
        donated_any = any(r.get("donated_shields", False) for r in self.mythos_manager.records)
        if donated_any and hasattr(self.game, "living_world") and hasattr(self.game.living_world, "settlement"):
            if hasattr(self.game.living_world.settlement, "add_prosperity"):
                self.game.living_world.settlement.add_prosperity(5.0)
            elif hasattr(self.game.living_world.settlement, "prosperity"):
                # Fallback for dummy test objects
                try:
                    self.game.living_world.settlement.prosperity += 5.0
                except Exception:
                    pass
            summary["prosperity_bonus"] = 5

        return summary
