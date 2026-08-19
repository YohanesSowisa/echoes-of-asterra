"""
Unit tests for Ancestral Soul Pacts & Physical Mutations Subsystem.
Validates binding requirements, costs, mutual exclusivity, combat range & poise hooks,
cleansing rituals & cooldowns, procedural mutation rendering, social reactivity, and save schema v6 migration.
"""
import unittest
import os
import pygame
from typing import Any

from rpg.events import EventBus
from rpg.pacts import (
    PactManager,
    PACT_VOID,
    PACT_TITAN,
    PACT_SOLAR,
    PACT_NONE,
    PACT_DEFINITIONS
)
from rpg.animation import apply_pact_mutation_overlay
from rpg.save import migrate_save, SAVE_SCHEMA_VERSION


class MockInventory:
    def __init__(self):
        self.slots = []

    def add_item(self, item):
        self.slots.append(item)
        return True

    def remove_item(self, item):
        if item in self.slots:
            self.slots.remove(item)


class MockItem:
    def __init__(self, name: str, qty: int = 1, item_type: str = "material"):
        self.name = name
        self.qty = qty
        self.quantity = qty
        self.item_type = item_type
        self.max_stack = 99
        self.stats = {}


class MockEquipment:
    def __init__(self):
        self.slots = {
            "weapon": None,
            "armor": None,
            "shield": None,
            "accessory": None
        }

    def unequip(self, slot_name: str):
        self.slots[slot_name] = None


class MockPlayer:
    def __init__(self):
        self.level = 3
        self.gold = 500
        self.hp = 100
        self.max_hp = 100
        self.mana = 50
        self.max_mana = 50
        self.stamina = 100
        self.max_stamina = 100
        self.atk = 10
        self.base_atk = 10
        self.defense = 5
        self.base_def = 5
        self.speed = 4.0
        self.base_speed = 4.0
        self.inventory = MockInventory()
        self.equipment = MockEquipment()
        self.game = None


class MockGame:
    def __init__(self):
        self.event_bus = EventBus()
        self.pact_manager = PactManager(self.event_bus)
        self.pact_manager.game_reference = self
        self.notification_manager = None
        self.rumor_board = None


class TestAncestralSoulPacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.event_bus = EventBus()
        self.pact_mgr = PactManager(self.event_bus)
        self.game = MockGame()
        self.player = MockPlayer()
        self.player.game = self.game
        self.game.player = self.player
        self.game.pact_manager = self.pact_mgr
        self.pact_mgr.game_reference = self.game

    def test_pact_definitions_registry(self):
        """Verifies Void and Titan pact configurations in static registry."""
        self.assertIn(PACT_VOID, PACT_DEFINITIONS)
        self.assertIn(PACT_TITAN, PACT_DEFINITIONS)

        void_pact = PACT_DEFINITIONS[PACT_VOID]
        self.assertEqual(void_pact.name, "Void Pact")
        self.assertEqual(void_pact.altar_location, "crypt")
        self.assertEqual(void_pact.atk_range_mult, 1.40)
        self.assertEqual(void_pact.mana_cost_mult, 1.20)

        titan_pact = PACT_DEFINITIONS[PACT_TITAN]
        self.assertEqual(titan_pact.name, "Titan Pact")
        self.assertEqual(titan_pact.altar_location, "cave")
        self.assertTrue(titan_pact.is_poise_immune)
        self.assertEqual(titan_pact.defense_bonus, 6)
        self.assertEqual(titan_pact.stamina_cost_mult, 1.50)

    def test_pact_binding_requirements(self):
        """Checks level, gold, and offering item validation."""
        # 1. Level check (< 3 fails)
        self.player.level = 1
        success, msg = self.pact_mgr.bind_pact(PACT_VOID, self.player, current_day=1)
        self.assertFalse(success)
        self.assertIn("Level", msg)

        # 2. Gold check
        self.player.level = 3
        self.player.gold = 20  # Needs 75
        success, msg = self.pact_mgr.bind_pact(PACT_VOID, self.player, current_day=1)
        self.assertFalse(success)
        self.assertIn("Insufficient Gold", msg)

        # 3. Item check
        self.player.gold = 100
        success, msg = self.pact_mgr.bind_pact(PACT_VOID, self.player, current_day=1)
        self.assertFalse(success)
        self.assertIn("Missing required offering", msg)

    def test_pact_binding_success_and_event(self):
        """Tests successful binding to Void Pact and item deduction."""
        self.player.level = 3
        self.player.gold = 200
        self.player.inventory.add_item(MockItem("Ancient Relic", 1))

        bound_events = []
        self.event_bus.subscribe("pact_bound", lambda **kw: bound_events.append(kw))

        success, msg = self.pact_mgr.bind_pact(PACT_VOID, self.player, current_day=2)
        self.assertTrue(success)
        self.assertEqual(self.pact_mgr.state.active_pact_id, PACT_VOID)
        self.assertEqual(self.player.gold, 125)  # 200 - 75
        self.assertEqual(len(bound_events), 1)
        self.assertEqual(bound_events[0]["pact_id"], PACT_VOID)
        self.assertEqual(self.pact_mgr.get_attack_range_multiplier(), 1.40)

    def test_pact_mutual_exclusivity(self):
        """Enforces mutual exclusivity: binding Titan when Void is active fails without cleansing."""
        self.player.level = 4
        self.player.gold = 300
        self.player.inventory.add_item(MockItem("Ancient Relic", 1))
        self.player.inventory.add_item(MockItem("Iron Ore", 3))
        self.player.inventory.add_item(MockItem("Silver Ore", 1))

        # Bind Void Pact first
        success, _ = self.pact_mgr.bind_pact(PACT_VOID, self.player, current_day=1)
        self.assertTrue(success)

        # Try to bind Titan Pact directly
        success_titan, msg_titan = self.pact_mgr.bind_pact(PACT_TITAN, self.player, current_day=1)
        self.assertFalse(success_titan)
        self.assertIn("Purification Ritual", msg_titan)
        self.assertEqual(self.pact_mgr.state.active_pact_id, PACT_VOID)

    def test_void_pact_equipment_restriction(self):
        """Checks that Void Pact restricts and unequips metal shields."""
        self.player.inventory.add_item(MockItem("Ancient Relic", 1))
        metal_shield = MockItem("Iron Shield", 1, "shield")
        wood_shield = MockItem("Wooden Buckler", 1, "shield")

        self.player.equipment.slots["shield"] = metal_shield
        self.pact_mgr.bind_pact(PACT_VOID, self.player, current_day=1)

        # Metal shield should be unequipped
        self.assertIsNone(self.player.equipment.slots["shield"])
        self.assertFalse(self.pact_mgr.can_equip_item(metal_shield))
        self.assertTrue(self.pact_mgr.can_equip_item(wood_shield))

    def test_titan_pact_poise_immunity_and_stamina(self):
        """Checks Titan Super Armor poise immunity and stamina multiplier."""
        self.player.inventory.add_item(MockItem("Iron Ore", 3))
        self.player.inventory.add_item(MockItem("Silver Ore", 1))

        success, _ = self.pact_mgr.bind_pact(PACT_TITAN, self.player, current_day=1)
        self.assertTrue(success)
        self.assertTrue(self.pact_mgr.is_poise_immune())
        self.assertEqual(self.pact_mgr.get_defense_bonus(), 6)
        self.assertEqual(self.pact_mgr.get_stamina_cost_multiplier(), 1.50)
        self.assertEqual(self.pact_mgr.get_speed_multiplier(), 0.90)

    def test_pact_cleansing_ritual_and_cooldown(self):
        """Checks cleansing ritual cost, state rollback, and 3-day cooldown."""
        self.player.inventory.add_item(MockItem("Ancient Relic", 1))
        self.player.inventory.add_item(MockItem("Starlight Crystal", 1))
        self.player.gold = 400

        # Bind Void
        self.pact_mgr.bind_pact(PACT_VOID, self.player, current_day=1)
        self.assertEqual(self.pact_mgr.state.active_pact_id, PACT_VOID)

        # Cleanse on Day 2
        success, msg = self.pact_mgr.cleanse_pact(self.player, current_day=2)
        self.assertTrue(success)
        self.assertIsNone(self.pact_mgr.state.active_pact_id)
        self.assertEqual(self.player.gold, 400 - 75 - 150)
        self.assertEqual(self.pact_mgr.get_attack_range_multiplier(), 1.0)

        # Bind Titan on Day 3
        self.player.inventory.add_item(MockItem("Iron Ore", 3))
        self.player.inventory.add_item(MockItem("Silver Ore", 1))
        self.pact_mgr.bind_pact(PACT_TITAN, self.player, current_day=3)
        self.assertEqual(self.pact_mgr.state.active_pact_id, PACT_TITAN)

        # Attempt cleanse immediately on Day 3 (cooldown: 3 days since Day 2 -> ready on Day 5)
        self.player.inventory.add_item(MockItem("Starlight Crystal", 1))
        self.player.gold = 300
        success_cd, msg_cd = self.pact_mgr.cleanse_pact(self.player, current_day=3)
        self.assertFalse(success_cd)
        self.assertIn("recovering from a previous ritual", msg_cd)

        # Cleanse on Day 5 (Cooldown elapsed)
        success_ready, _ = self.pact_mgr.cleanse_pact(self.player, current_day=5)
        self.assertTrue(success_ready)
        self.assertIsNone(self.pact_mgr.state.active_pact_id)

    def test_procedural_mutation_surface_rendering(self):
        """Assures apply_pact_mutation_overlay generates valid Pygame surfaces without errors."""
        base_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        base_surf.fill((200, 100, 100, 255))

        # Void overlay
        void_surf = apply_pact_mutation_overlay(base_surf, PACT_VOID, "down", 0)
        self.assertIsNotNone(void_surf)
        self.assertEqual(void_surf.get_size(), (32, 32))

        # Titan overlay
        titan_surf = apply_pact_mutation_overlay(base_surf, PACT_TITAN, "right", 2)
        self.assertIsNotNone(titan_surf)
        self.assertEqual(titan_surf.get_size(), (32, 32))

        # None overlay
        none_surf = apply_pact_mutation_overlay(base_surf, PACT_NONE, "up", 0)
        self.assertEqual(none_surf, base_surf)

    def test_pact_social_reactivity(self):
        """Tests NPC memory greeting reactions to active soul pacts."""
        from rpg.npc_memory import NPCMemoryManager
        npc_mem = NPCMemoryManager()

        self.player.game = self.game
        self.game.pact_manager = self.pact_mgr

        # Baseline
        self.assertEqual(npc_mem.get_greeting_prefix("eldrin", self.player), "")

        # Void Pact Reaction
        self.pact_mgr.state.active_pact_id = PACT_VOID
        eldrin_greeting = npc_mem.get_greeting_prefix("eldrin", self.player)
        self.assertIn("dark miasma", eldrin_greeting)

        guard_greeting = npc_mem.get_greeting_prefix("guard_1", self.player)
        self.assertIn("shadowy appendages", guard_greeting)

        # Titan Pact Reaction
        self.pact_mgr.state.active_pact_id = PACT_TITAN
        titan_greeting = npc_mem.get_greeting_prefix("guard_1", self.player)
        self.assertIn("animate fortress", titan_greeting)

    def test_pact_serialization_and_schema_v6_migration(self):
        """Validates to_dict/from_dict and schema v6 save migration."""
        self.pact_mgr.state.active_pact_id = PACT_VOID
        self.pact_mgr.state.bound_day = 4
        self.pact_mgr.state.pact_history = [PACT_VOID]

        data = self.pact_mgr.to_dict()
        new_mgr = PactManager()
        new_mgr.from_dict(data)

        self.assertEqual(new_mgr.state.active_pact_id, PACT_VOID)
        self.assertEqual(new_mgr.state.bound_day, 4)
        self.assertEqual(new_mgr.state.pact_history, [PACT_VOID])

        # Test schema v5 -> v6 migration
        legacy_v5_save = {
            "save_schema_version": 5,
            "player": {"level": 5, "gold": 100},
            "quests": {},
            "world": {}
        }
        migrated = migrate_save(legacy_v5_save)
        self.assertEqual(migrated["save_schema_version"], SAVE_SCHEMA_VERSION)
        self.assertGreaterEqual(SAVE_SCHEMA_VERSION, 6)
    def test_pact_xp_gain_and_tier_ascension(self):
        """Tests gaining pact XP and advancing tiers (Tier 1 -> Tier 2 -> Tier 3)."""
        self.pact_mgr.state.active_pact_id = PACT_VOID
        self.assertEqual(self.pact_mgr.state.pact_tier, 1)
        self.assertEqual(self.pact_mgr.get_pact_tier_name(), "Novice")

        tier_events = []
        self.event_bus.subscribe("pact_tier_ascended", lambda **kw: tier_events.append(kw))

        # Award 200 XP -> remains Tier 1
        self.pact_mgr.gain_pact_xp(200)
        self.assertEqual(self.pact_mgr.state.pact_tier, 1)
        self.assertEqual(len(tier_events), 0)

        # Award 50 more XP (total 250) -> ascends to Tier 2 (Ascendant)
        ascended = self.pact_mgr.gain_pact_xp(50)
        self.assertTrue(ascended)
        self.assertEqual(self.pact_mgr.state.pact_tier, 2)
        self.assertEqual(self.pact_mgr.get_pact_tier_name(), "Ascendant")
        self.assertEqual(len(tier_events), 1)
        self.assertEqual(tier_events[0]["new_tier"], 2)

        # Award 500 more XP (total 750) -> ascends to Tier 3 (Paragon)
        ascended_3 = self.pact_mgr.gain_pact_xp(500)
        self.assertTrue(ascended_3)
        self.assertEqual(self.pact_mgr.state.pact_tier, 3)
        self.assertEqual(self.pact_mgr.get_pact_tier_name(), "Paragon")
        self.assertEqual(len(tier_events), 2)

    def test_tier_scaled_stat_multipliers(self):
        """Checks that reach and defense scale dynamically across tiers."""
        # Void reach scaling
        self.pact_mgr.state.active_pact_id = PACT_VOID
        self.pact_mgr.state.pact_tier = 1
        self.assertEqual(self.pact_mgr.get_attack_range_multiplier(), 1.40)
        self.pact_mgr.state.pact_tier = 2
        self.assertEqual(self.pact_mgr.get_attack_range_multiplier(), 1.50)
        self.pact_mgr.state.pact_tier = 3
        self.assertEqual(self.pact_mgr.get_attack_range_multiplier(), 1.65)

        # Titan defense scaling
        self.pact_mgr.state.active_pact_id = PACT_TITAN
        self.pact_mgr.state.pact_tier = 1
        self.assertEqual(self.pact_mgr.get_defense_bonus(), 6)
        self.pact_mgr.state.pact_tier = 2
        self.assertEqual(self.pact_mgr.get_defense_bonus(), 9)
        self.pact_mgr.state.pact_tier = 3
        self.assertEqual(self.pact_mgr.get_defense_bonus(), 12)

    def test_tier2_social_stigma_and_merchant_pricing(self):
        """Tests Silas surcharge for Void Tier 2+ and Dennis discount for Titan Tier 2+."""
        self.pact_mgr.state.active_pact_id = PACT_VOID
        self.pact_mgr.state.pact_tier = 1
        self.assertEqual(self.pact_mgr.get_merchant_price_multiplier("silas"), 1.0)

        # Ascend Void to Tier 2 -> 15% surcharge at Silas
        self.pact_mgr.state.pact_tier = 2
        self.assertEqual(self.pact_mgr.get_merchant_price_multiplier("silas"), 1.15)

        # Titan Tier 2 -> 10% discount at Dennis
        self.pact_mgr.state.active_pact_id = PACT_TITAN
        self.pact_mgr.state.pact_tier = 2
        self.assertEqual(self.pact_mgr.get_merchant_price_multiplier("dennis"), 0.90)

    def test_daily_faction_reputation_impact(self):
        """Tests that Void Tier 2+ slowly decays Knights faction reputation."""
        class MockFactionManager:
            def __init__(self):
                self.reps = {"knights": 50}
            def modify_reputation(self, faction, amount):
                self.reps[faction] += amount

        fm = MockFactionManager()
        self.game.factions = fm
        self.pact_mgr.state.active_pact_id = PACT_VOID
        self.pact_mgr.state.pact_tier = 2

        self.pact_mgr._on_day_changed(current_day=2)
        self.assertEqual(fm.reps["knights"], 49)

    def test_solar_pact_binding_and_regen(self):
        """Checks Solar Seraph binding, requirements, and peace HP/mana regen."""
        self.player.level = 3
        self.player.gold = 100
        self.player.inventory.add_item(MockItem("Topaz", 1))

        success, msg = self.pact_mgr.bind_pact(PACT_SOLAR, self.player, current_day=1)
        self.assertTrue(success)
        self.assertEqual(self.pact_mgr.state.active_pact_id, PACT_SOLAR)

        # Tier 1 peace regen (2.0 HP/s, 2.0 Mana/s)
        hp_reg, mana_reg = self.pact_mgr.get_peace_regen_bonus()
        self.assertEqual(hp_reg, 2.0)
        self.assertEqual(mana_reg, 2.0)
        self.assertEqual(self.pact_mgr.get_light_radius_multiplier(), 1.25)

        # Ascend to Tier 3 -> +5.0 regen, 1.70x light radius
        self.pact_mgr.state.pact_tier = 3
        hp_reg3, mana_reg3 = self.pact_mgr.get_peace_regen_bonus()
        self.assertEqual(hp_reg3, 5.0)
        self.assertEqual(mana_reg3, 5.0)
        self.assertEqual(self.pact_mgr.get_light_radius_multiplier(), 1.70)

    def test_solar_pact_night_vulnerability_and_restrictions(self):
        """Checks Solar Seraph +20% damage at night and dark robe equip restriction."""
        self.pact_mgr.state.active_pact_id = PACT_SOLAR
        self.assertEqual(self.pact_mgr.get_damage_taken_multiplier(is_night=False), 1.0)
        self.assertEqual(self.pact_mgr.get_damage_taken_multiplier(is_night=True), 1.20)

        dark_robe = MockItem("Cultist Shadow Robe", 1, "armor")
        steel_armor = MockItem("Steel Plate", 1, "armor")
        self.assertFalse(self.pact_mgr.can_equip_item(dark_robe))
        self.assertTrue(self.pact_mgr.can_equip_item(steel_armor))

    def test_cast_pact_abilities_all(self):
        """Tests active pact spell casting for Void, Titan, and Solar."""
        class MockEnemy:
            def __init__(self, x, y):
                self.x = x
                self.y = y
                self.rect = pygame.Rect(x, y, 20, 20)
                self.is_alive = True
                self.dmg_taken = 0
                self.stagger_dur = 0.0
            def take_damage(self, amt):
                self.dmg_taken += amt
            def apply_stagger(self, dur):
                self.stagger_dur = dur

        e1 = MockEnemy(10, 10)
        enemies = [e1]
        self.player.x = 20
        self.player.y = 20
        self.player.rect = pygame.Rect(20, 20, 20, 20)

        # 1. Void: Abyssal Rift Vortex
        self.pact_mgr.state.active_pact_id = PACT_VOID
        self.player.mana = 50
        succ_v, msg_v = self.pact_mgr.cast_pact_ability(self.player, enemies)
        self.assertTrue(succ_v)
        self.assertEqual(self.player.mana, 20)  # 50 - (25 * 1.2) = 20
        self.assertGreater(e1.dmg_taken, 0)

        # 2. Titan: Earthshatter Quake
        self.pact_mgr.state.active_pact_id = PACT_TITAN
        self.player.stamina = 100
        succ_t, msg_t = self.pact_mgr.cast_pact_ability(self.player, enemies)
        self.assertTrue(succ_t)
        self.assertEqual(self.player.stamina, 55)  # 100 - (30 * 1.5) = 55
        self.assertEqual(e1.stagger_dur, 2.0)

        # 3. Solar: Solar Cleansing Nova
        self.pact_mgr.state.active_pact_id = PACT_SOLAR
        self.player.hp = 50
        self.player.mana = 50
        succ_s, msg_s = self.pact_mgr.cast_pact_ability(self.player, enemies)
        self.assertTrue(succ_s)
        self.assertEqual(self.player.hp, 85)  # 50 + 35 = 85
        self.assertEqual(self.player.mana, 23)  # 50 - (30 * 0.9) = 23

    def test_solar_procedural_mutation_surface_rendering(self):
        """Assures Solar Seraph wings & halo render cleanly on Pygame surfaces."""
        base_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        base_surf.fill((100, 150, 200, 255))

        for tier in [1, 2, 3]:
            solar_surf = apply_pact_mutation_overlay(base_surf, PACT_SOLAR, "down", 0, pact_tier=tier)
            self.assertIsNotNone(solar_surf)
            self.assertEqual(solar_surf.get_size(), (32, 32))

    def test_primordial_weapon_item_creation(self):
        """Verifies creation and legendary attributes of Primordial Relic Weapons."""
        from rpg.items import create_item, RARITY_LEGENDARY
        scythe = create_item("Voidbrand Scythe", 1, roll_equipment_affixes=False)
        self.assertIsNotNone(scythe)
        self.assertEqual(scythe.rarity, RARITY_LEGENDARY)
        self.assertEqual(scythe.stats.get("atk"), 18)

        cleaver = create_item("Titan Cragcleaver", 1, roll_equipment_affixes=False)
        self.assertIsNotNone(cleaver)
        self.assertEqual(cleaver.rarity, RARITY_LEGENDARY)
        self.assertEqual(cleaver.stats.get("atk"), 22)

        morningstar = create_item("Sunfire Morningstar", 1, roll_equipment_affixes=False)
        self.assertIsNotNone(morningstar)
        self.assertEqual(morningstar.rarity, RARITY_LEGENDARY)
        self.assertEqual(morningstar.stats.get("atk"), 16)

    def test_primordial_weapon_crafting_recipes(self):
        """Tests crafting validation for Primordial Weapons at facility level 2."""
        from rpg.crafting import CraftingSystem
        from rpg.inventory import Inventory
        from rpg.items import create_item

        inv = Inventory(size=12)
        inv.add_item(create_item("Steel Blade", 1))
        inv.add_item(create_item("Ancient Relic", 2))

        self.assertTrue(CraftingSystem.can_craft("Voidbrand Scythe", inv, facility_level=2))
        self.assertFalse(CraftingSystem.can_craft("Voidbrand Scythe", inv, facility_level=1))

        crafted = CraftingSystem.craft("Voidbrand Scythe", inv, facility_level=2)
        self.assertTrue(crafted)
        self.assertTrue(inv.has_item("Voidbrand Scythe", 1))

    def test_mythos_recording_soul_pact_legacy(self):
        """Tests MythosManager recording active soul pact in cross-run history."""
        from rpg.mythos import MythosManager
        mythos = MythosManager()

        self.pact_mgr.state.active_pact_id = PACT_VOID
        self.pact_mgr.state.pact_tier = 2

        record = mythos.record_run(self.game, end_cause="ascended")
        self.assertEqual(record["active_soul_pact"], PACT_VOID)
        self.assertEqual(record["soul_pact_tier"], 2)

        # Check recorded event
        pact_events = [ev for ev in record["events"] if ev.get("event_type") == "PRIMORDIAL_PACT_BOUND"]
        self.assertEqual(len(pact_events), 1)
        self.assertEqual(pact_events[0]["amount"], 2)


if __name__ == "__main__":
    unittest.main()
