# Echoes of Asterra — Living World Expansion

> 📘 **Dokumen Serah Terima AI / Developer**: Lihat [handover.md](handover.md) untuk panduan arsitektur & kelanjutan proyek di sesi chat baru.  
> 📜 **Histori Log Pembaruan**: Lihat [update_logs.md](update_logs.md) untuk riwayat lengkap penambahan fitur & perbaikan bug.

**Echoes of Asterra** is a complete, production-quality, top-down Action RPG built from scratch in Python 3.12+ using **Pygame Community Edition (`pygame-ce`)**.

The game features an explorable world across multiple procedural maps, real-time combo combat with weapon identities, deeply integrated living world systems (Dynamic World, Player-Driven Faction Warfare, Monster Ecology, Persistent NPC Memory, Multi-Day Consequence Chains, Rumor Mill Gossip, Cross-Run Mythos Inheritance, and Procedural Endless Dungeons), deep RPG mechanics (leveling, inventory, equipment, crafting, and mutually exclusive alliance quests), branching dialogue, ambient systems (day-night cycle, dynamic atmospheric weather with thunderstorm lightning & fog), and a procedural audio synthesizer.

---

## 🎮 Controls Reference

| Action | Control (Keyboard/Mouse) |
| :--- | :--- |
| **Move** | `W`, `A`, `S`, `D` |
| **Sprinting** | Hold `Left Shift` |
| **Dodge Roll / Phase Dash** | `Spacebar` |
| **Melee Attack / Combo** | `J` or Left Click |
| **Shield Block / Parry** | Hold `K` or Hold Right Click (requires equipped shield) |
| **Interact** | `F` (Talk to NPCs, Open chests, Harvest items) |
| **Quick Ability Skills** | `Q` (Fireball), `E` (Ice Spike), `C` (Healing), `X` (Dash) |
| **Quick Consumable Slots** | `1`, `2`, `3`, `4` (Health Potions, Mana Potions, Food) |
| **Backpack Inventory** | Toggle `I` |
| **Quest Journal** | Toggle `N` |
| **Character Sheet & Factions** | Toggle `V` (Tabs 1–6: Factions, Social, Town, Achiev, Bestiary, Nemesis) |
| **Crafting Forge** | Toggle `G` |
| **Radar Minimap** | Toggle `M` |
| **Use Consumables / Equip** | Right-click item inside inventory Backpack |
| **Unequip Gear** | Right-click equipped slot in Character Sheet |
| **Sell Items at Silas** | Right-click backpack items while Silas shop is open |
| **Save / Load Game** | Pause the game (`ESC`), select Save/Load buttons |
| **Pause Game / Exit Shop** | Press `ESC` |

---

## 🌟 Living World Features (13 Integrated Subsystems)

1. **Dynamic World (`world_state.py`)**: Persistent day/season simulation engine tracking prosperity (0-100), danger level (0-100), and 8 dynamic world events (Village Festival, Merchant Caravan, Bandit Outbreak, Harvest Season, etc.).
2. **Faction Warfare & Reputation (`factions.py`, `faction_war.py`)**: 6 factions (Knights, Mages, Hunters, Merchants, Bandits, Void Cult). Territory control points (*Forest Crossroads, Cave Depths, Ruins Plaza, Lake Pier*) shift based on player reputation and combat activity (`zone_kills`).
3. **Multi-Day Delayed Consequence Chains (`consequences.py`)**: Player interventions trigger causal ripples that arrive 2-3 in-game days later (e.g. overhunting wolves causes deer overpopulation, destroying food stocks and triggering emergent quests).
4. **The Rumor Mill & Gossip Distortion (`rumors.py`)**: NPCs spread rumors daily with a 25% chance of exaggeration/bualan (`⚡ [DISTORTED RUMOR]`). Players can ask any town NPC `🗣️ Heard any rumors?` to gather intelligence.
5. **Cross-Run Mythos Inheritance (`mythos.py`, `mythos_reader.py`)**: Past hero victories and deaths persist in history, spawning Ancestral Relic weapons in Crypt chests and generating legend dialogues for village NPCs in subsequent playthroughs.
6. **Mutually Exclusive Alliance Quests (`quests.py`)**: Player decisions create permanent narrative forks (`exclusive_with`). Pledging to "The Knight's Vow" permanently locks "The Void Covenant" and shifts faction standing drastically.
7. **Persistent NPC Memory (`npc_memory.py`)**: NPCs remember hero interactions, completed quests, gifts, and witnessed crimes. Friendship tiers evolve (Enemy, Stranger, Acquaintance, Friend, Close Friend), altering greeting prefixes and merchant discounts.
8. **Monster Ecology (`ecology.py`)**: Simulated species dynamics with predator-prey hunting, territory tracking, natural reproduction, nocturnal/diurnal activity windows, and over-hunting migration.
9. **Weapon Identity & Combo Combat (`weapon_types.py`)**: 5 weapon classes (Sword, Axe, Hammer, Spear, Dagger) with distinct attack speeds, ranges, armor-piercing capabilities, stuns, combo chains, finisher multipliers, and elemental reactions (Thermal Blast, Corrosive Explosion).
10. **Procedural Endless Dungeon (`dungeon_gen.py`)**: BSP (Binary Space Partitioning) algorithm generating infinite replayable dungeon levels with scaling depth difficulty, traps, theme biomes (Crypt, Cave, Temple, Ice, Volcano), and boss chambers every 5 floors.
11. **The Nemesis System (`nemesis.py`)**: Persistent bandit, cultist, and monster captains who remember encounters with the player, level up upon victory or escape, gain tactical traits (*Bloodthirsty, Craven, Cunning, Ironhide, Hero Slayer, Ambush Master*), claim regional territories (reducing road safety and stability), seed dynamic rumors across village NPCs, and drop unique named loot recorded in the Bestiary and Mythos history.
12. **Companion Recruitment & Expeditions (`companion.py`)**: Recruitable allies (`Ranger Faye`, `Guard Kai`, `Scholar Mira`) with party following, tactical AI modes (`Attack`, `Tank`, `Heal`), shared combat XP, contextual weather/location banter, and autonomous offline resource expeditions.
13. **Seasonal Festival Minigames (`festival.py`)**: Interactive village square festival minigames including Target Archery Contest (timing gauge), Harvest Sprint (15s crop gathering reaction), and Dennis's Feast Challenge (push-your-luck fullness), with seasonal records, tiered gold/item rewards, custom titles (*"Asterra Marksman"*, *"Grand Harvester"*, *"Master of Feasts"*), and rumor mill dissemination.

---

## 🚀 Installation & Play

1. **Ensure Python 3.12+ is installed.**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Launch the game:**
   ```bash
   python main.py
   ```

---

## 🏗️ Folder Structure

```
echoes-of-asterra/
├── main.py                # Game launcher and display entry setup
├── requirements.txt       # Pygame Community Edition installation package
├── README.md              # Technical handbook (this file)
├── handover.md            # Technical architecture handover guide
├── update_logs.md         # Full historical update and fix log (WIB format)
├── assets/                # Map JSON layouts (village, forest, cave, ruins, dungeon) & audio WAV cache
├── saves/                 # JSON persistent save slots (savegame_X.json, memories, mythos, achievements, bestiary)
├── tests/                 # 19+ automated test suite modules
└── rpg/                   # Core Action RPG Engine Package
    ├── services/          # Modular service layer
    │   ├── admin_ui.py    # Admin & debug UI service
    │   ├── asset.py       # Asset manager service
    │   ├── container.py   # Dependency injection container
    │   ├── data.py        # Data loading & query service
    │   ├── navigation.py  # A* pathfinding & navigation mesh service
    │   ├── noise.py       # OpenSimplex noise generator service
    │   ├── profiling.py   # Performance profiling service
    │   ├── tilemap.py     # TMX tilemap renderer service
    │   └── tween.py       # Easing curve tweening service
    ├── game.py            # Core engine coordinator and main state machine
    ├── events.py          # Central EventBus for decoupled system messaging
    ├── nemesis.py         # Persistent Nemesis Captains & progression system
    ├── world_state.py     # Dynamic world simulation engine (days, seasons, events)
    ├── factions.py        # 6-faction reputation and price modifier system
    ├── faction_war.py    # Player-driven regional territory control manager
    ├── consequences.py   # Multi-day delayed causal consequence engine
    ├── rumors.py          # NPC rumor propagation & gossip distortion board
    ├── mythos.py, mythos_reader.py # Hero legacy persistence & ancestral relic reader
    ├── npc_memory.py, npc_schedule.py # Persistent NPC relationship memory & daily schedules
    ├── ecology.py, economy.py # Monster ecology & commodity stock/demand simulation
    ├── living_world.py    # Coordinator for economy, ecology, caravan, & faction war
    ├── weapon_types.py    # 5 weapon classes, combo movesets, elemental reactions
    ├── dungeon_gen.py     # BSP procedural endless dungeon floor generator
    ├── settings.py        # Frame rate, screen dimensions, bindings, configurations
    ├── constants.py       # Global color definitions, states, enums, item types
    ├── camera.py          # Centered tracking viewport with camera shakes
    ├── input.py           # Unified keyboard key polling and mouse clicks
    ├── save.py            # JSON-based saving/loading state serialization
    ├── collision.py       # Spatial culling AABB grid collision resolution
    ├── items.py           # Item database model, weapon classes, and properties
    ├── inventory.py       # Grid inventory backpack with sorting and dragging
    ├── equipment.py       # Sockets matching modifiers to player stats
    ├── crafting.py        # Crafting recipe validator consuming items
    ├── skills.py          # Active/passive spell trees and cast costs
    ├── combat.py          # Hit registration, damage calculations, Projectiles
    ├── emergent_quests.py # Dynamic emergency quest generator based on simulation state
    ├── hazards.py         # Environmental traps, spike tiles, and slippery ice mechanics
    ├── style_scoring.py   # Devil May Cry-style combat style rank evaluator
    ├── ai.py, director.py # Finite State Machine AI musuh & AI Director
    ├── quests.py          # Log tracking with talk/kill/collect objective tasks
    ├── dialogue.py        # Branching dialogues with typing text animation
    ├── npc.py             # Elder, Merchant Silas, Faye, Mira, Dennis interactions
    ├── player.py          # Hero movements, actions, combo state machine, leveling
    ├── enemy.py           # Slime, Wolf, Skeleton, Mage, Goblin, Knight archetypes
    ├── boss.py            # Final Shadow Overlord with Phase 1 & 2 patterns
    ├── animation.py       # Procedural pixel-art frames generation (renders in memory)
    ├── sprite.py          # BaseSprite and depth Y-sorted drawing group
    ├── ui.py              # HUD gauges, overlay menus, stats layouts, combo counter
    ├── minimap.py         # Real-time scaling radar coordinates tracker
    ├── particles.py       # Blood splatters, dust footsteps, magic sparks
    ├── sound.py           # In-memory procedural WAV synthesizer (SFX & BGM)
    ├── weather.py         # Rain cascades, lightning flashes, snow drift, fog veil, leaves
    ├── lighting.py        # Day-Night cycles and radial darkness masks carve-outs
    └── effects.py         # Screen flashes, hit-stops, outline highlights
```

---

## 🛠️ Architecture & Cross-System Integration

- **Event Bus Decoupling**: Systems communicate asynchronously via `EventBus` topics (`"enemy_killed"`, `"quest_completed"`, `"npc_talked"`, `"day_changed"`, `"item_bought"`, `"consequence_executed"`), eliminating tight circular dependencies.
- **Procedural Graphics & Audio**: On startup, `animation.py` renders pixel-art styles directly to Surfaces, and `sound.py` synthesizes PCM WAV structures in memory (including weather ambient SFX: thunder, wind gusts, crickets).
- **Y-Sorted Layered Drawing**: The `YSortedGroup` sorts drawing coordinates of chests, players, and trees dynamically by their bottom coordinates before drawing.
- **Spatial Collision Culling**: `CollisionSystem` divides grid tiles spatially, testing wall block intersections ONLY for adjacent neighboring tiles.
- **Rendering Culling**: Background drawing loops only blit tiles falling inside the viewport's camera bounding coordinates, maintaining a stable 60 FPS.
