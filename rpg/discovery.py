"""
Echoes of Asterra - Dynamic Lead & Discoverability Engine
Coordinates contextual, diegetic pointers for all 8 Master Expansion Pillars
and 4 isolated side quests via Notification Toasts, RumorBoard Gossip, and NPC Dialogue nodes.
"""
from typing import Set, Dict, Any, Optional, List, Tuple
from rpg.constants import (
    MAP_VILLAGE, MAP_FOREST, MAP_CAVE, MAP_DUNGEON, MAP_LAKE, MAP_RUINS, MAP_SUNKEN_MIRE
)
from rpg.epochs import EPOCH_DEFAULT
from rpg.notification import NotificationPriority
from rpg.dialogue import DialogueNode, DialogueChoice


class DiscoveryManager:
    """
    Central discovery coordinator evaluating one-time diegetic discovery triggers.
    Ensures zero duplicate spam and persists discovery flags in SaveSchema v7.
    """
    def __init__(self, event_bus: Optional[Any] = None, game_reference: Optional[Any] = None) -> None:
        self.event_bus = event_bus
        self.game = game_reference
        self.triggered_leads: Set[str] = set()

        if self.event_bus:
            self.register_event_listeners(self.event_bus)

    def register_event_listeners(self, event_bus: Any) -> None:
        """Subscribes to living-world events for reactive trigger evaluations."""
        self.event_bus = event_bus
        event_bus.subscribe("day_changed", self._on_day_changed)
        event_bus.subscribe("epoch_changed", self._on_epoch_changed)
        event_bus.subscribe("boss_defeated", self._on_boss_defeated)
        event_bus.subscribe("territory_control_changed", self._on_territory_control_changed)
        event_bus.subscribe("quest_accepted", self._on_quest_accepted)

    def evaluate_leads(self, game: Optional[Any] = None) -> None:
        """
        Evaluates world state, player progress, inventory, and current map
        to trigger pending one-time diegetic leads.
        """
        g = game or self.game
        if not g:
            return

        player = getattr(g, "player", None)
        world_state = getattr(g, "world_state", None)
        wm = getattr(g, "world_manager", None)
        current_map = getattr(wm, "current_map_name", "village") if wm else "village"
        day = getattr(world_state, "day", 1) if world_state else 1
        player_gold = getattr(player, "gold", 0) if player else 0
        player_level = getattr(player, "level", 1) if player else 1

        # Pillar 1: Sunken Mire & Leylines (Trigger: Lake or Sunken Mire visited, or Day >= 2)
        if (current_map in (MAP_LAKE, MAP_SUNKEN_MIRE) or day >= 2) and "lead_sunken_mire" not in self.triggered_leads:
            self._trigger_sunken_mire_lead(g)

        # Pillar 2: Doomsday Conspiracy (Trigger: Day >= 2 or main_quest active)
        if day >= 2 and "lead_conspiracy" not in self.triggered_leads:
            self._trigger_conspiracy_lead(g)

        # Pillar 3: Frontier Outposts & Caravans (Trigger: Gold >= 100 or CP stabilized)
        if player_gold >= 100 and "lead_outposts" not in self.triggered_leads:
            self._trigger_outposts_lead(g)

        # Pillar 4: Cataclysm Epochs (Trigger: Epoch shift or Day >= 15)
        epoch_mgr = getattr(g, "epoch_manager", None)
        cur_epoch = getattr(epoch_mgr, "current_epoch", EPOCH_DEFAULT) if epoch_mgr else EPOCH_DEFAULT
        if (cur_epoch != EPOCH_DEFAULT or day >= 15) and "lead_epochs" not in self.triggered_leads:
            self._trigger_epochs_lead(g)

        # Pillar 5: Continental Monopoly (Trigger: Player Gold >= 100)
        if player_gold >= 100 and "lead_monopoly" not in self.triggered_leads:
            self._trigger_monopoly_lead(g)

        # Pillar 6: Ancestral Soul Pacts (Trigger: Player Level >= 3 or Cave/Crypt/Ruins entered)
        if (player_level >= 3 or current_map in (MAP_CAVE, MAP_DUNGEON, MAP_RUINS)) and "lead_soul_pacts" not in self.triggered_leads:
            self._trigger_soul_pacts_lead(g)

        # Pillar 7: Living Dungeon Architect (Trigger: Crypt boss defeated)
        if wm and getattr(wm, "boss_defeated", False) and "lead_dungeon_architect" not in self.triggered_leads:
            self._trigger_dungeon_architect_lead(g)

        # Pillar 8: Chrono-Echoes (Trigger: Hourglass in inventory or Day >= 5)
        has_hourglass = False
        if player and hasattr(player, "inventory") and player.inventory:
            for slot in getattr(player.inventory, "slots", []):
                if slot and "hourglass" in getattr(slot, "name", "").lower():
                    has_hourglass = True
                    break
        if (has_hourglass or day >= 5) and "lead_chrono" not in self.triggered_leads:
            self._trigger_chrono_lead(g)

    # -------------------------------------------------------------------------
    # Event Listeners
    # -------------------------------------------------------------------------
    def _on_day_changed(self, day: int = 1, **kwargs: Any) -> None:
        self.evaluate_leads(self.game)

    def _on_epoch_changed(self, epoch_id: str = "", **kwargs: Any) -> None:
        if self.game:
            self._trigger_epochs_lead(self.game)

    def _on_boss_defeated(self, boss_id: str = "", **kwargs: Any) -> None:
        if boss_id in ("shadow_overlord", "crypt_guardian", "bone_monarch") and self.game:
            self._trigger_dungeon_architect_lead(self.game)

    def _on_territory_control_changed(self, control_point: str = "", map_name: str = "", old_owner: str = "", new_owner: str = "", **kwargs: Any) -> None:
        if self.game:
            self._trigger_outposts_lead(self.game)

    def _on_item_acquired(self, item_name: str = "", **kwargs: Any) -> None:
        if "hourglass" in item_name.lower() and self.game:
            self._trigger_chrono_lead(self.game)

    def _on_quest_accepted(self, quest_id: str = "", **kwargs: Any) -> None:
        if quest_id == "main_quest" and self.game:
            self._trigger_conspiracy_lead(self.game)

    # -------------------------------------------------------------------------
    # One-Time Pillar Triggers (Toasts + Distinct RumorBoard Gossip)
    # -------------------------------------------------------------------------
    def _trigger_sunken_mire_lead(self, game: Any) -> None:
        if "lead_sunken_mire" in self.triggered_leads:
            return
        self.triggered_leads.add("lead_sunken_mire")

        # 1. Notification Toast
        if hasattr(game, "notification_manager") and game.notification_manager:
            game.notification_manager.push_toast(
                "🌊 DISCOVERY: The Sunken Mire to the south has dynamic tides! Low tide reveals submerged paths.",
                priority=NotificationPriority.HIGH
            )

        # 2. RumorBoard Entry (Distinct True vs Distorted Content)
        rumors = getattr(getattr(game, "living_world", None), "rumors", None) or getattr(game, "rumors", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            rumors.add_custom_rumor(
                "rumor_lead_sunken_mire",
                "Sunken Mire Tides",
                "faye",
                "The wetlands south of Asterra Lake fluctuate with daily tides. When the water recedes during low tide, ancient submerged passages and rich leylines emerge!",
                "The southern wetlands are swallowing the earth whole—giant bog leeches and sea horrors are drowning anyone who steps into the mud!",
                is_true=True
            )

    def _trigger_conspiracy_lead(self, game: Any) -> None:
        if "lead_conspiracy" in self.triggered_leads:
            return
        self.triggered_leads.add("lead_conspiracy")

        # 1. Notification Toast
        if hasattr(game, "notification_manager") and game.notification_manager:
            game.notification_manager.push_toast(
                "🕵️ INVESTIGATION: Whispers speak of shadowy infiltrators corrupting guards and threatening the Mage Guild Envoy.",
                priority=NotificationPriority.HIGH
            )

        # 2. RumorBoard Entry
        rumors = getattr(getattr(game, "living_world", None), "rumors", None) or getattr(game, "rumors", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            rumors.add_custom_rumor(
                "rumor_lead_conspiracy",
                "Shadow Syndicate Infiltration",
                "eldrin",
                "Elder Eldrin suspects a Shadow Syndicate has infiltrated local authorities and is plotting an ambush on Envoy Vaelin in the Sunfire Ruins!",
                "A secret shadow cabal has already replaced half the village sentries with shape-shifting dark assassins!",
                is_true=True
            )

    def _trigger_outposts_lead(self, game: Any) -> None:
        if "lead_outposts" in self.triggered_leads:
            return
        self.triggered_leads.add("lead_outposts")

        # 1. Notification Toast
        if hasattr(game, "notification_manager") and game.notification_manager:
            game.notification_manager.push_toast(
                "🏰 FORTIFICATION: Secured territory control points can now be upgraded into fortified Outposts (100g)!",
                priority=NotificationPriority.HIGH
            )

        # 2. RumorBoard Entry
        rumors = getattr(getattr(game, "living_world", None), "rumors", None) or getattr(game, "rumors", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            rumors.add_custom_rumor(
                "rumor_lead_outposts",
                "Frontier Outpost Fortifications",
                "kai",
                "With regional roads secured, adventurers can construct fortified Frontier Outposts at control points for 100 gold to station guards and collect passing caravan tolls!",
                "The hero is building colossal border citadels and demanding forty gold coins from every merchant wagon that crosses the realm!",
                is_true=True
            )

    def _trigger_epochs_lead(self, game: Any) -> None:
        if "lead_epochs" in self.triggered_leads:
            return
        self.triggered_leads.add("lead_epochs")

        # 1. Notification Toast
        if hasattr(game, "notification_manager") and game.notification_manager:
            game.notification_manager.push_toast(
                "🌌 CATACLYSM EPOCH: Ancient environmental cycles are reshaping Asterra's terrain and hazards!",
                priority=NotificationPriority.HIGH
            )

        # 2. RumorBoard Entry
        rumors = getattr(getattr(game, "living_world", None), "rumors", None) or getattr(game, "rumors", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            rumors.add_custom_rumor(
                "rumor_lead_epochs",
                "Ancient Cataclysm Epochs",
                "eldrin",
                "Elder Eldrin warns of ancient cyclical Epochs—Deluges forming raft bridges, Scorched Blight spawning lava fissures, and Glacial Winter freezing lakes into solid ice.",
                "The ancient heavens are breaking apart, unleashing eternal celestial fire and endless blizzards to consume the continent!",
                is_true=True
            )

    def _trigger_monopoly_lead(self, game: Any) -> None:
        if "lead_monopoly" in self.triggered_leads:
            return
        self.triggered_leads.add("lead_monopoly")

        # 1. Notification Toast
        if hasattr(game, "notification_manager") and game.notification_manager:
            game.notification_manager.push_toast(
                "💰 COMMERCE: Merchant Silas is offering Crown Resource Concession Deeds in the market!",
                priority=NotificationPriority.HIGH
            )

        # 2. RumorBoard Entry
        rumors = getattr(getattr(game, "living_world", None), "rumors", None) or getattr(game, "rumors", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            rumors.add_custom_rumor(
                "rumor_lead_monopoly",
                "Crown Concession Deeds",
                "silas",
                "Merchant Silas has acquired royal resource concession deeds. Ambitious entrepreneurs can buy cavern, forest, and timber rights to build warehouse empires and earn bank vault interest!",
                "Silas is auctioning off every mountain and forest in Asterra to shadowy oligarchs for chests overflowing with diamonds!",
                is_true=True
            )

    def _trigger_soul_pacts_lead(self, game: Any) -> None:
        if "lead_soul_pacts" in self.triggered_leads:
            return
        self.triggered_leads.add("lead_soul_pacts")

        # 1. Notification Toast
        if hasattr(game, "notification_manager") and game.notification_manager:
            game.notification_manager.push_toast(
                "🔮 PRIMORDIAL ALTARS: Ancient sanctuaries in subterranean depths permit binding Ancestral Soul Pacts!",
                priority=NotificationPriority.HIGH
            )

        # 2. RumorBoard Entry
        rumors = getattr(getattr(game, "living_world", None), "rumors", None) or getattr(game, "rumors", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            rumors.add_custom_rumor(
                "rumor_lead_soul_pacts",
                "Primordial Soul Altars",
                "mira",
                "Scholar Mira discovered that offering relics at subterranean Primordial Altars allows champions to bind Void, Titan, or Solar soul pacts for legendary powers!",
                "Mad warlocks are sacrificing their humanity at unholy altars to sprout monstrous void tentacles and burning solar wings!",
                is_true=True
            )

    def _trigger_dungeon_architect_lead(self, game: Any) -> None:
        if "lead_dungeon_architect" in self.triggered_leads:
            return
        self.triggered_leads.add("lead_dungeon_architect")

        # 1. Notification Toast
        if hasattr(game, "notification_manager") and game.notification_manager:
            game.notification_manager.push_toast(
                "🏛️ CRYPT SOVEREIGN: The Dungeon Core Stone is now claimable! Construct traps and station captured beasts!",
                priority=NotificationPriority.CRITICAL
            )

        # 2. RumorBoard Entry
        rumors = getattr(getattr(game, "living_world", None), "rumors", None) or getattr(game, "rumors", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            rumors.add_custom_rumor(
                "rumor_lead_dungeon_architect",
                "The Crypt Core Stone",
                "dennis",
                "With the Crypt boss defeated, the primordial Core Stone is unclaimed. Slayers can claim it to build spike traps, portcullises, and station captured beasts against raiders!",
                "The hero has become the new lord of the crypts, raising armies of domesticated dungeon monsters and deathtraps underneath Asterra!",
                is_true=True
            )

    def _trigger_chrono_lead(self, game: Any) -> None:
        if "lead_chrono" in self.triggered_leads:
            return
        self.triggered_leads.add("lead_chrono")

        # 1. Notification Toast
        if hasattr(game, "notification_manager") and game.notification_manager:
            game.notification_manager.push_toast(
                "⏳ TEMPORAL PHENOMENON: The Chrono-Weaver Hourglass can rewind time up to 3 days into the past!",
                priority=NotificationPriority.HIGH
            )

        # 2. RumorBoard Entry
        rumors = getattr(getattr(game, "living_world", None), "rumors", None) or getattr(game, "rumors", None)
        if rumors and hasattr(rumors, "add_custom_rumor"):
            rumors.add_custom_rumor(
                "rumor_lead_chrono",
                "The Chrono-Weaver Hourglass",
                "mira",
                "Ancient texts tell of the Chrono-Weaver Hourglass capable of rolling back world time up to 3 days, though temporal fractures and mirror doppelgangers will arise.",
                "A forbidden relic can unravel reality itself, undoing history and creating evil cloned duplicates that hunt their creators!",
                is_true=True
            )

    # -------------------------------------------------------------------------
    # Diegetic NPC Dialogue Lead Injections (Reusing inject_rumor_choice pattern)
    # -------------------------------------------------------------------------
    def inject_npc_dialogue_leads(self, npc: Any, node: DialogueNode, npc_short_id: str) -> None:
        """
        Injects non-blocking discoverability dialogue choices into core NPCs.
        Follows the established inject_rumor_choice pattern in rpg/npc.py.
        """
        if not self.game or not hasattr(self.game, "dialogue_manager"):
            return

        dm = self.game.dialogue_manager
        short_id = npc_short_id.lower()

        # 1. Elder Eldrin: Conspiracy Lead, Epoch Lore, Bridge Repair, Mage Guild Envoy
        if short_id == "eldrin":
            # Conspiracy & Envoy Lead
            if not any("conspiracy" in c.text.lower() or "dark rumors" in c.text.lower() for c in node.choices):
                def conspiracy_cb():
                    c_node = DialogueNode(
                        "eldrin_lead_conspiracy",
                        npc.name,
                        "Our scouts report shadowy figures bribing guards near the Forest crossroads. Furthermore, Envoy Vaelin of the Mage Guild is journeying to the Sunfire Ruins. If you travel east, keep your guard up—the Syndicate seeks to destabilize Asterra!",
                        [DialogueChoice("I will investigate.", None)]
                    )
                    dm.add_node(c_node)
                    dm.set_node("eldrin_lead_conspiracy")
                node.choices.insert(0, DialogueChoice("🕵️ [INQUIRY] Ask about dark rumors in the village", None, conspiracy_cb))

            # Cataclysm Epoch Lore
            if not any("epoch" in c.text.lower() or "shifting weather" in c.text.lower() for c in node.choices):
                def epoch_cb():
                    e_node = DialogueNode(
                        "eldrin_lead_epoch",
                        npc.name,
                        "The legends of our forebears speak of Cataclysm Epochs—cosmic shifts where nature transforms the surface. In the Deluge, waterways rise and raft bridges form; in the Scorched Blight, molten fissures burn; in the Glacial Winter, lakes freeze into traversable ice. Prepare your gear accordingly!",
                        [DialogueChoice("Fascinating history.", None)]
                    )
                    dm.add_node(e_node)
                    dm.set_node("eldrin_lead_epoch")
                node.choices.insert(1, DialogueChoice("🌌 [LORE] Inquire about shifting weather and terrain", None, epoch_cb))

            # Side Quest Lead: Bridge Repair
            if not any("bridge" in c.text.lower() for c in node.choices):
                def bridge_cb():
                    b_node = DialogueNode(
                        "eldrin_lead_bridge",
                        npc.name,
                        "The northern stone bridge connecting our village to Asterra Lake collapsed during recent storms. If you bring 5 Oak Wood and 3 Iron Ores, we can reconstruct the crossing and restore the trade route!",
                        [DialogueChoice("I'll see to it.", None)]
                    )
                    dm.add_node(b_node)
                    dm.set_node("eldrin_lead_bridge")
                node.choices.insert(2, DialogueChoice("🌉 [TASK: BRIDGE] Inquire about the collapsed northern bridge", None, bridge_cb))

            # Side Quest Lead: Protect Mage Guild Envoy
            if not any("envoy" in c.text.lower() for c in node.choices):
                def envoy_cb():
                    v_node = DialogueNode(
                        "eldrin_lead_envoy",
                        npc.name,
                        "Urgent news from the Mage Guild! Envoy Vaelin is surveying ancient wards in the Sunfire Ruins, but shadow cultists plan an ambush. Please hurry to the Ruins and ensure her safety!",
                        [DialogueChoice("I'll protect the Envoy.", None)]
                    )
                    dm.add_node(v_node)
                    dm.set_node("eldrin_lead_envoy")
                node.choices.insert(3, DialogueChoice("🧙‍♂️ [TASK: ENVOY] Inquire about Mage Guild Envoy Vaelin", None, envoy_cb))

        # 2. Merchant Silas: Continental Monopoly Concession Deeds
        elif short_id == "silas":
            if not any("concession" in c.text.lower() or "deeds" in c.text.lower() for c in node.choices):
                def monopoly_cb():
                    m_node = DialogueNode(
                        "silas_lead_monopoly",
                        npc.name,
                        "Ah, a person of financial means! The Crown offers exclusive territorial concession deeds for caverns, forests, and timberland. Purchase them to receive daily deliveries into our Guild Warehouse, bank gold in our vault for 2% daily interest, or liquidate stockpiles for massive profits!",
                        [DialogueChoice("Good to know.", None)]
                    )
                    dm.add_node(m_node)
                    dm.set_node("silas_lead_monopoly")
                node.choices.insert(0, DialogueChoice("📜 [CONCESSIONS] Inquire about Crown Resource Deeds & Guild Warehouse", None, monopoly_cb))

        # 3. Blacksmith Dennis: Dungeon Architect Core Stone & Watchtower Construction
        elif short_id == "dennis":
            # Dungeon Architect Core Lead
            if not any("dungeon core" in c.text.lower() or "crypt" in c.text.lower() for c in node.choices):
                def dungeon_core_cb():
                    dc_node = DialogueNode(
                        "dennis_lead_dungeon_core",
                        npc.name,
                        "You cleared the dark forces from the crypt? Brilliant work! The primordial Dungeon Core Stone there is now unclaimed. If you claim it, you can craft defense traps like spike pits and portcullises, and even capture weakened beasts with nets to defend against periodic raiders!",
                        [DialogueChoice("I will claim the crypt core.", None)]
                    )
                    dm.add_node(dc_node)
                    dm.set_node("dennis_lead_dungeon_core")
                node.choices.insert(0, DialogueChoice("🏛️ [DUNGEON CORE] Inquire about defending the Crypt", None, dungeon_core_cb))

            # Side Quest Lead: Watchtower Construction
            if not any("watchtower" in c.text.lower() for c in node.choices):
                def watchtower_cb():
                    wt_node = DialogueNode(
                        "dennis_lead_watchtower",
                        npc.name,
                        "Our village defenses are vulnerable to sudden bandit raids from the eastern hills. Bring 3 Oak Wood and 2 Iron Ores to the Noticeboard project, and we can erect a proper fortified Watchtower!",
                        [DialogueChoice("I'll gather the materials.", None)]
                    )
                    dm.add_node(wt_node)
                    dm.set_node("dennis_lead_watchtower")
                node.choices.insert(1, DialogueChoice("🏹 [TASK: WATCHTOWER] Inquire about the village watchtower", None, watchtower_cb))

        # 4. Ranger Faye: Sunken Mire Wetlands & Slime Cleaning Bounties
        elif short_id == "faye":
            # Sunken Mire Lead
            if not any("marsh" in c.text.lower() or "mire" in c.text.lower() for c in node.choices):
                def mire_cb():
                    mr_node = DialogueNode(
                        "faye_lead_mire",
                        npc.name,
                        "The southern wetland—the Sunken Mire—is undergoing bizarre tidal shifts. If you venture down there, pay close attention to the tide phase: Low tide reveals submerged paths and ancient conduits, while High tide will slow you down and flood the passages.",
                        [DialogueChoice("Understood, Ranger.", None)]
                    )
                    dm.add_node(mr_node)
                    dm.set_node("faye_lead_mire")
                node.choices.insert(0, DialogueChoice("🌊 [RUMOR] Inquire about the southern marshland", None, mire_cb))

            # Side Quest Lead: Slime Cleaning
            if not any("slime" in c.text.lower() for c in node.choices):
                def slime_cb():
                    sl_node = DialogueNode(
                        "faye_lead_slime",
                        npc.name,
                        "Green slimes have been multiplying along the forest outskirts and scaring trade messengers. Check the Town Noticeboard—there is an active bounty rewarding gold and potions for clearing them out.",
                        [DialogueChoice("I'll squash some slimes.", None)]
                    )
                    dm.add_node(sl_node)
                    dm.set_node("faye_lead_slime")
                node.choices.insert(1, DialogueChoice("🟢 [TASK: SLIMES] Ask about slime bounties", None, slime_cb))

        # 5. Scholar Mira: Ancestral Soul Pacts & Chrono-Weaver Hourglass
        elif short_id == "mira":
            # Ancestral Soul Pacts Lead
            if not any("pact" in c.text.lower() or "altar" in c.text.lower() for c in node.choices):
                def pact_cb():
                    p_node = DialogueNode(
                        "mira_lead_pacts",
                        npc.name,
                        "During my excavations, I found mentions of Primordial Altars in the Crypt, Caverns, and Ruins. If you possess offering relics like Ancient Relics, Topaz, or Silver Ore, you can commune with ancient powers to bind a Soul Pact (Void, Titan, or Solar) for unique powers and combat mutations.",
                        [DialogueChoice("Intriguing mysteries.", None)]
                    )
                    dm.add_node(p_node)
                    dm.set_node("mira_lead_pacts")
                node.choices.insert(0, DialogueChoice("🔮 [PACTS] Inquire about ancient crypt altars", None, pact_cb))

            # Chrono-Weaver Hourglass Lead
            if not any("chrono" in c.text.lower() or "temporal" in c.text.lower() for c in node.choices):
                def chrono_cb():
                    ch_node = DialogueNode(
                        "mira_lead_chrono",
                        npc.name,
                        "The Chrono-Weaver Hourglass is one of the most mysterious relics in Asterra's history. It allows its bearer to rewind spacetime up to 3 days in the past. But beware—altering the continuum leaves temporal fractures and summons paradox mirror doppelgangers who mirror your abilities!",
                        [DialogueChoice("A perilous power.", None)]
                    )
                    dm.add_node(ch_node)
                    dm.set_node("mira_lead_chrono")
                node.choices.insert(1, DialogueChoice("⏳ [CHRONO] Inquire about temporal artifacts", None, chrono_cb))

        # 6. Guard Kai: Frontier Outpost Fortification
        elif short_id == "kai":
            if not any("outpost" in c.text.lower() or "fortify" in c.text.lower() for c in node.choices):
                def outpost_cb():
                    op_node = DialogueNode(
                        "kai_lead_outposts",
                        npc.name,
                        "Now that regional routes have been secured, you have the right to construct Frontier Outposts at control points for 100 gold. They lock territorial stability against raiders, station sentries, and collect passive trade tolls from passing merchant caravans.",
                        [DialogueChoice("I'll consider fortifying.", None)]
                    )
                    dm.add_node(op_node)
                    dm.set_node("kai_lead_outposts")
                node.choices.insert(0, DialogueChoice("🏰 [FORTIFY] Inquire about establishing Outposts", None, outpost_cb))

    # -------------------------------------------------------------------------
    # Lifecycle & Serialization (Schema v7 Compatible)
    # -------------------------------------------------------------------------
    def reset(self) -> None:
        """Resets all triggered discovery leads."""
        self.triggered_leads.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes discovery flags."""
        return {
            "triggered_leads": list(self.triggered_leads)
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserializes discovery flags."""
        if not data or not isinstance(data, dict):
            return
        raw_leads = data.get("triggered_leads", [])
        if isinstance(raw_leads, list):
            self.triggered_leads = set(raw_leads)
