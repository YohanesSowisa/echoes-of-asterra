"""
Echoes of Asterra - The Doomsday Infiltration Engine (Pillar #2)
Tracks the Shadow Syndicate conspiracy, 30-day coup countdown timer,
syndicate influence metrics, suspect investigations, compromised minds,
purification exorcisms, covert faction sabotages, multi-ending resolution,
and immutable NPC safeguards.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from rpg.events import EventBus

COUP_MAX_DAYS = 30
IMMUTABLE_CORE_NPCS = ["eldrin", "silas", "dennis"]

# Conspiracy Endings
ENDING_TOTAL_PURGE = "total_purge"
ENDING_COMPROMISED_KINGDOM = "compromised_kingdom"
ENDING_SHADOW_SOVEREIGN = "shadow_sovereign"


@dataclass
class SuspectData:
    """Represents a peripheral suspect involved in the Shadow Syndicate conspiracy."""
    suspect_id: str
    name: str
    title: str
    location: str
    status: str = "active"  # "active", "compromised", "neutralized"
    is_defeated: bool = False
    evidence_found: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suspect_id": self.suspect_id,
            "name": self.name,
            "title": self.title,
            "location": self.location,
            "status": self.status,
            "is_defeated": self.is_defeated,
            "evidence_found": self.evidence_found
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SuspectData":
        return cls(
            suspect_id=data.get("suspect_id", ""),
            name=data.get("name", ""),
            title=data.get("title", ""),
            location=data.get("location", ""),
            status=data.get("status", "active"),
            is_defeated=data.get("is_defeated", False),
            evidence_found=data.get("evidence_found", False)
        )


@dataclass
class CompromisedNPCData:
    """Represents a secondary NPC afflicted with a Compromised Mind by a Shadow Parasite."""
    npc_id: str
    name: str
    is_compromised: bool = True
    cold_dialogue: str = "Leave me be. The Void sees through our fragile minds..."
    price_multiplier: float = 1.4
    parasite_defeated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "name": self.name,
            "is_compromised": self.is_compromised,
            "cold_dialogue": self.cold_dialogue,
            "price_multiplier": self.price_multiplier,
            "parasite_defeated": self.parasite_defeated
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompromisedNPCData":
        return cls(
            npc_id=data.get("npc_id", ""),
            name=data.get("name", ""),
            is_compromised=data.get("is_compromised", True),
            cold_dialogue=data.get("cold_dialogue", "Leave me be. The Void sees through our fragile minds..."),
            price_multiplier=float(data.get("price_multiplier", 1.4)),
            parasite_defeated=data.get("parasite_defeated", False)
        )


@dataclass
class CovertSabotageData:
    """Represents an active covert sabotage operation targeting a military control point."""
    sabotage_id: str
    target_point_id: str
    target_map: str
    days_left: int = 3
    is_active: bool = True
    is_prevented: bool = False
    is_executed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sabotage_id": self.sabotage_id,
            "target_point_id": self.target_point_id,
            "target_map": self.target_map,
            "days_left": self.days_left,
            "is_active": self.is_active,
            "is_prevented": self.is_prevented,
            "is_executed": self.is_executed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CovertSabotageData":
        return cls(
            sabotage_id=data.get("sabotage_id", ""),
            target_point_id=data.get("target_point_id", ""),
            target_map=data.get("target_map", ""),
            days_left=int(data.get("days_left", 3)),
            is_active=data.get("is_active", True),
            is_prevented=data.get("is_prevented", False),
            is_executed=data.get("is_executed", False)
        )


class ConspiracyManager:
    """
    Subsystem managing the Shadow Syndicate infiltration, countdown to Day 30 Coup,
    syndicate influence tracking, suspect confrontations, covert territory sabotages,
    and multi-branching climax resolutions.
    """
    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus
        self.syndicate_influence: float = 35.0  # 0.0 to 100.0%
        self.days_until_coup: int = COUP_MAX_DAYS
        self.current_day: int = 1
        self.cipher_fragments: List[str] = []
        self.suspects: Dict[str, SuspectData] = {}
        self.compromised_npcs: Dict[str, CompromisedNPCData] = {}
        self.covert_sabotages: Dict[str, CovertSabotageData] = {}
        self.conspiracy_resolved: bool = False
        self.conspiracy_ending: Optional[str] = None
        self.game_reference: Any = None
        self.reset()

        if self.event_bus:
            self.event_bus.subscribe("day_changed", self._on_day_changed)

    def reset(self) -> None:
        """Resets conspiracy state to initial Day 1 conditions."""
        self.syndicate_influence = 35.0
        self.days_until_coup = COUP_MAX_DAYS
        self.current_day = 1
        self.cipher_fragments.clear()
        self.compromised_npcs.clear()
        self.covert_sabotages.clear()
        self.conspiracy_resolved = False
        self.conspiracy_ending = None
        self.suspects = {
            "bran": SuspectData(
                suspect_id="bran",
                name="Lieutenant Bran",
                title="Corrupt Guard Lieutenant",
                location="forest",
                status="active"
            )
        }

    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        """Ticks the daily countdown and calculates unmitigated influence growth & covert infiltration."""
        if self.conspiracy_resolved:
            return

        self.current_day = day
        self.days_until_coup = max(0, COUP_MAX_DAYS - day + 1)

        # Unmitigated active suspects increase syndicate influence by +2% daily
        active_suspects = sum(1 for s in self.suspects.values() if s.status == "active" and not s.is_defeated)
        if active_suspects > 0:
            self.syndicate_influence = min(100.0, self.syndicate_influence + (active_suspects * 2.0))

        # Active compromised NPCs increase influence by +1.5% daily
        active_compromised = sum(1 for c in self.compromised_npcs.values() if c.is_compromised)
        if active_compromised > 0:
            self.syndicate_influence = min(100.0, self.syndicate_influence + (active_compromised * 1.5))

        # High influence escalation: if influence >= 50% and no NPC currently compromised, compromise Miner Garth
        if self.syndicate_influence >= 50.0 and active_compromised == 0:
            self.compromise_npc("garth", "The deep rocks speak of darkness... do not stand in our way.")

        # 1. Tick active sabotage countdowns
        for sabotage in list(self.covert_sabotages.values()):
            if sabotage.is_active:
                sabotage.days_left -= 1
                if sabotage.days_left <= 0:
                    sabotage.is_active = False
                    sabotage.is_executed = True
                    self.syndicate_influence = min(100.0, self.syndicate_influence + 10.0)
                    
                    # Shift control point to cult if faction_war exists
                    if self.game_reference:
                        fw = getattr(self.game_reference, "faction_war", None) or getattr(self.game_reference, "factions", None)
                        if fw and hasattr(fw, "covert_shift_ownership"):
                            fw.covert_shift_ownership(sabotage.target_point_id, "cult")

                    if self.event_bus:
                        self.event_bus.emit(
                            "sabotage_executed",
                            sabotage_id=sabotage.sabotage_id,
                            target_point_id=sabotage.target_point_id,
                            target_map=sabotage.target_map
                        )

        # 2. Phase 3 Covert Sabotage: if influence >= 50% and no active sabotage, stage sabotage on Ruins Plaza
        active_sabotages = [s for s in self.covert_sabotages.values() if s.is_active]
        if self.syndicate_influence >= 50.0 and len(active_sabotages) == 0:
            self.stage_sabotage("ruins_plaza", "ruins")

        # Phase 4 Coup Resolution on Day 30 timeout
        if (self.days_until_coup <= 0 or day >= COUP_MAX_DAYS) and not self.conspiracy_resolved:
            if self.syndicate_influence >= 70.0:
                player = getattr(self.game_reference, "player", None) if self.game_reference else None
                self.resolve_conspiracy(player=player, force_ending=ENDING_COMPROMISED_KINGDOM)

        if self.event_bus:
            if self.days_until_coup <= 5 and not self.conspiracy_resolved:
                self.event_bus.emit(
                    "coup_imminent_warning",
                    days_left=self.days_until_coup,
                    influence=self.syndicate_influence
                )

    def is_npc_protected(self, npc_id: str) -> bool:
        """Guarantees essential core storyline NPCs can never be compromised or assassinated."""
        clean_id = npc_id.lower().replace(" ", "").replace("npc_", "")
        return clean_id in IMMUTABLE_CORE_NPCS

    def is_npc_compromised(self, npc_id: str) -> bool:
        """Checks whether an NPC is currently afflicted with a Compromised Mind."""
        clean_id = npc_id.lower().replace(" ", "").replace("npc_", "")
        return bool(clean_id in self.compromised_npcs and self.compromised_npcs[clean_id].is_compromised)

    def get_npc_price_multiplier(self, npc_id: str) -> float:
        """Returns price surcharge multiplier for an NPC (1.4x if compromised, 1.0x normal)."""
        clean_id = npc_id.lower().replace(" ", "").replace("npc_", "")
        if clean_id in self.compromised_npcs and self.compromised_npcs[clean_id].is_compromised:
            return self.compromised_npcs[clean_id].price_multiplier
        return 1.0

    def compromise_npc(self, npc_id: str, cold_dialogue: Optional[str] = None) -> bool:
        """
        Afflicts a secondary NPC with Compromised Mind status.
        Core storyline NPCs are strictly rejected.
        """
        if self.is_npc_protected(npc_id):
            return False

        clean_id = npc_id.lower().replace(" ", "").replace("npc_", "")
        name = clean_id.title()
        if clean_id == "garth":
            name = "Miner Garth"
        elif clean_id == "faye":
            name = "Ranger Faye"
        elif clean_id == "mira":
            name = "Scholar Mira"

        default_diag = cold_dialogue or "Leave me be. The Void sees through our fragile minds..."
        self.compromised_npcs[clean_id] = CompromisedNPCData(
            npc_id=clean_id,
            name=name,
            is_compromised=True,
            cold_dialogue=default_diag,
            price_multiplier=1.4,
            parasite_defeated=False
        )

        if self.event_bus:
            self.event_bus.emit(
                "npc_compromised",
                npc_id=clean_id,
                name=name,
                syndicate_influence=self.syndicate_influence
            )

        return True

    def exorcise_npc(self, npc_id: str, player: Any = None) -> Tuple[bool, str]:
        """
        Purges the Shadow Parasite from an afflicted NPC, restoring their sanity,
        reducing syndicate influence by -10%, and rewarding alchemical Shadow Residue.
        """
        clean_id = npc_id.lower().replace(" ", "").replace("npc_", "")
        if clean_id not in self.compromised_npcs or not self.compromised_npcs[clean_id].is_compromised:
            return False, f"{clean_id.title()} is not compromised."

        c_data = self.compromised_npcs[clean_id]
        c_data.is_compromised = False
        c_data.parasite_defeated = True

        # Reduce syndicate influence
        self.syndicate_influence = max(0.0, self.syndicate_influence - 10.0)

        # Reward player with Shadow Residue and XP
        if player:
            if hasattr(player, "inventory") and player.inventory:
                from rpg.items import create_item
                residue = create_item("Shadow Residue", 1)
                if residue:
                    player.inventory.add_item(residue)
            if hasattr(player, "gain_xp"):
                player.gain_xp(60)

        if self.event_bus:
            self.event_bus.emit(
                "npc_exorcised",
                npc_id=clean_id,
                name=c_data.name,
                remaining_influence=self.syndicate_influence
            )

        return True, f"{c_data.name}'s mind has been purged of the Shadow Parasite! Influence reduced to {int(self.syndicate_influence)}%."

    def stage_sabotage(self, point_id: str = "ruins_plaza", map_name: str = "ruins") -> bool:
        """Initiates a 3-day covert sabotage plot against a strategic control point."""
        sabotage_id = f"sabotage_{point_id}"
        if sabotage_id in self.covert_sabotages:
            return False

        self.covert_sabotages[sabotage_id] = CovertSabotageData(
            sabotage_id=sabotage_id,
            target_point_id=point_id,
            target_map=map_name,
            days_left=3,
            is_active=True,
            is_prevented=False,
            is_executed=False
        )

        if self.event_bus:
            self.event_bus.emit(
                "sabotage_staged",
                sabotage_id=sabotage_id,
                target_point_id=point_id,
                target_map=map_name,
                days_left=3
            )

        return True

    def prevent_sabotage(self, sabotage_id: str = "sabotage_ruins_plaza", player: Any = None) -> Tuple[bool, str]:
        """
        Foils an active covert sabotage operation, reducing syndicate influence by 15%,
        and rewarding Syndicate Cipher Fragment #2.
        """
        sabotage = self.covert_sabotages.get(sabotage_id)
        if not sabotage:
            return False, f"Unknown sabotage operation '{sabotage_id}'."
        if not sabotage.is_active:
            return False, f"Sabotage '{sabotage_id}' is no longer active."

        sabotage.is_active = False
        sabotage.is_prevented = True

        # Reduce influence
        self.syndicate_influence = max(0.0, self.syndicate_influence - 15.0)

        # Award Cipher Fragment #2
        fragment_name = "Syndicate Cipher Fragment #2"
        if fragment_name not in self.cipher_fragments:
            self.cipher_fragments.append(fragment_name)

        if player and hasattr(player, "inventory") and player.inventory:
            from rpg.items import create_item
            frag_item = create_item(fragment_name, 1)
            if frag_item:
                player.inventory.add_item(frag_item)

        if self.event_bus:
            self.event_bus.emit(
                "sabotage_prevented",
                sabotage_id=sabotage_id,
                target_point_id=sabotage.target_point_id,
                remaining_influence=self.syndicate_influence
            )

        return True, f"Covert sabotage on {sabotage.target_point_id} successfully prevented! Influence reduced to {int(self.syndicate_influence)}%."

    def neutralize_suspect(self, suspect_id: str, player: Any = None) -> Tuple[bool, str]:
        """
        Marks a peripheral suspect neutralized upon defeat, reduces syndicate influence by 15%,
        and awards an encrypted Syndicate Cipher Fragment.
        """
        suspect = self.suspects.get(suspect_id)
        if not suspect:
            return False, f"Unknown suspect '{suspect_id}'."
        if suspect.is_defeated:
            return False, f"{suspect.name} has already been neutralized."

        suspect.is_defeated = True
        suspect.status = "neutralized"
        suspect.evidence_found = True

        # Reduce influence
        self.syndicate_influence = max(0.0, self.syndicate_influence - 15.0)

        # Award Cipher Fragment #1
        fragment_name = "Syndicate Cipher Fragment #1"
        if fragment_name not in self.cipher_fragments:
            self.cipher_fragments.append(fragment_name)

        if player and hasattr(player, "inventory") and player.inventory:
            from rpg.items import create_item
            frag_item = create_item(fragment_name, 1)
            if frag_item:
                player.inventory.add_item(frag_item)

        if self.event_bus:
            self.event_bus.emit(
                "suspect_neutralized",
                suspect_id=suspect_id,
                suspect_name=suspect.name,
                remaining_influence=self.syndicate_influence
            )

        return True, f"{suspect.name} has been neutralized! Syndicate influence reduced to {int(self.syndicate_influence)}%."

    def resolve_conspiracy(self, player: Any = None, force_ending: Optional[str] = None) -> Tuple[str, str]:
        """
        Evaluates and resolves the conspiracy outcome into one of 3 branching endings:
        1. ENDING_TOTAL_PURGE: Grand Usurper defeated, conspiracy destroyed.
        2. ENDING_SHADOW_SOVEREIGN: Player with Void Pact Tier 2+ assumes control of the Syndicate.
        3. ENDING_COMPROMISED_KINGDOM: Day 30 Coup succeeds, kingdom falls into shadow oppression.
        """
        if self.conspiracy_resolved:
            return self.conspiracy_ending or ENDING_TOTAL_PURGE, "Conspiracy has already been resolved."

        if force_ending:
            chosen_ending = force_ending
        else:
            # Check Void Pact Standing
            is_void_master = False
            if player and hasattr(player, "game") and player.game and hasattr(player.game, "pact_manager"):
                pm = player.game.pact_manager
                if pm.state.active_pact_id == "void" and pm.state.pact_tier >= 2:
                    is_void_master = True

            if is_void_master:
                chosen_ending = ENDING_SHADOW_SOVEREIGN
            elif self.syndicate_influence < 70.0:
                chosen_ending = ENDING_TOTAL_PURGE
            else:
                chosen_ending = ENDING_COMPROMISED_KINGDOM

        self.conspiracy_resolved = True
        self.conspiracy_ending = chosen_ending

        if chosen_ending == ENDING_TOTAL_PURGE:
            self.syndicate_influence = 0.0
            desc = "The Grand Usurper has fallen! The Shadow Syndicate is eradicated from Asterra!"
        elif chosen_ending == ENDING_SHADOW_SOVEREIGN:
            self.syndicate_influence = 100.0
            desc = "The Hero ascends the obsidian throne as the Shadow Sovereign of Asterra!"
        else:  # ENDING_COMPROMISED_KINGDOM
            self.syndicate_influence = 100.0
            desc = "The Day 30 Coup succeeds! The Shadow Syndicate seizes Asterra in iron darkness!"

        if self.event_bus:
            self.event_bus.emit(
                "conspiracy_resolved",
                ending=chosen_ending,
                influence=self.syndicate_influence,
                description=desc,
                day=self.current_day
            )

        return chosen_ending, desc

    def to_dict(self) -> Dict[str, Any]:
        """Serializes conspiracy manager state for savegame."""
        return {
            "syndicate_influence": round(self.syndicate_influence, 2),
            "days_until_coup": self.days_until_coup,
            "current_day": self.current_day,
            "cipher_fragments": list(self.cipher_fragments),
            "conspiracy_resolved": self.conspiracy_resolved,
            "conspiracy_ending": self.conspiracy_ending,
            "suspects": {k: v.to_dict() for k, v in self.suspects.items()},
            "compromised_npcs": {k: v.to_dict() for k, v in self.compromised_npcs.items()},
            "covert_sabotages": {k: v.to_dict() for k, v in self.covert_sabotages.items()}
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restores conspiracy manager state from savegame."""
        if not isinstance(data, dict):
            return
        self.syndicate_influence = float(data.get("syndicate_influence", 35.0))
        self.days_until_coup = int(data.get("days_until_coup", COUP_MAX_DAYS))
        self.current_day = int(data.get("current_day", 1))
        self.cipher_fragments = list(data.get("cipher_fragments", []))
        self.conspiracy_resolved = bool(data.get("conspiracy_resolved", False))
        self.conspiracy_ending = data.get("conspiracy_ending", None)
        if "suspects" in data and isinstance(data["suspects"], dict):
            self.suspects = {k: SuspectData.from_dict(v) for k, v in data["suspects"].items()}
        if "compromised_npcs" in data and isinstance(data["compromised_npcs"], dict):
            self.compromised_npcs = {k: CompromisedNPCData.from_dict(v) for k, v in data["compromised_npcs"].items()}
        if "covert_sabotages" in data and isinstance(data["covert_sabotages"], dict):
            self.covert_sabotages = {k: CovertSabotageData.from_dict(v) for k, v in data["covert_sabotages"].items()}
