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

## 🌟 Living World Features (14 Integrated Subsystems)

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
11. **The Nemesis System & Vendetta Sieges (`nemesis.py`)**: Persistent bandit, cultist, and monster captains who remember encounters with the player, level up upon victory or escape, gain tactical traits (*Bloodthirsty, Craven, Cunning, Ironhide, Hero Slayer, Ambush Master*), and launch emergent **Vendetta Sieges** against world territories with loyal warband escorts. Features controlled escalation caps (max Lv.10, 3 traits), inter-siege cooldowns (5 days), territory seizure on timeout defeat, bonus gold (+100g) and Mythos legacy inscriptions on victory defense, and guaranteed UI early warnings.
12. **Companion Recruitment & Expeditions (`companion.py`)**: Recruitable allies (`Ranger Faye`, `Guard Kai`, `Scholar Mira`) with party following, tactical AI modes (`Attack`, `Tank`, `Heal`), shared combat XP, contextual weather/location banter, and autonomous offline resource expeditions.
13. **Seasonal Festival Minigames (`festival.py`)**: Interactive village square festival minigames including Target Archery Contest (timing gauge), Harvest Sprint (15s crop gathering reaction), and Dennis's Feast Challenge (push-your-luck fullness), with seasonal records, tiered gold/item rewards, custom titles (*"Asterra Marksman"*, *"Grand Harvester"*, *"Master of Feasts"*), and rumor mill dissemination.
14. **Ancestral Soul Pacts & Physical Mutations (`pacts.py`)**: Primordial covenant system binding the hero's soul at ancient world altars. Features 3 distinct paths: **Void Pact** (Crypt Floor 1 - +40% to +65% Melee Reach, *Abyssal Rift Vortex* gravity spell, metal shield restrictions), **Titan Pact** (Cave Depths - Super Armor poise immunity, +6 to +12 Base Defense, *Earthshatter Quake* stagger spell, roll stamina penalty), and **Solar Seraph Pact** (Sun Temple Ruins - +2.0 to +5.0 HP/Mana peace regen, expanded light radius, *Solar Cleansing Nova* burst, night vulnerability). Features 3 mastery tiers per pact, 100% in-memory procedural physical sprite mutations (eldritch tentacles, granite armor plates, feathered golden angel wings in `rpg/animation.py`), clean Purification Ritual cleansing at the Village Sanctuary Altar with 3-day recovery cooldowns, and reactive NPC memory dialogues & rumors.
15. **The Sunken Mire & Ancient Leylines (`sunken_mire.py`, `leylines.py`)**: Dynamic submerged wetland biome (`MAP_SUNKEN_MIRE`) governed by clock-driven **Tide Cycles** (High Tide flooding marshlands with 25% movement penalties and swamp toxins; Low Tide uncovering hidden mud isthmuses and sunken relic chests). Features amphibious predators (*Mire Lurker*, *Bog Leech*), the **Ancient Leyline Network** of arcane conduits across Asterra enabling instant fast-travel teleportation, **Leyline Overcharging** (24h zone-wide perpetual low tide and regional boons), harvestable mire flora (*Bog Blossom*, *Glow Lotus*, *Luminescent Spore*), **Mire Flora Alchemy** (*Waterstrider Elixir*, *Mire Cleansing Draught*, *Leyline Surge Tonic*), the **Submerged Temple of Asterra** (`MAP_SUBMERGED_TEMPLE`), multi-phase world boss **Morvath, the Mire Leviathan** (enrages at 50% HP with *Tidal Miasma Surge*), **Leyline Resonant Equipment** (*Leviathan Scale Mail*, *Tidecaller Trident*, *Conduit Ring of Leylines*), **Leyline Rot Contamination (0–100%)**, destroyable fungal **Spore Nests**, cross-zone monster mutations (**Spore-Host Wolves** with toxic death bursts), and dynamic emergent purification quests.
16. **The Doomsday Infiltration & Shadow Syndicate (`conspiracy.py`)**: Conspiracy tracking engine managing the impending Shadow Syndicate infiltration. Features a 30-day countdown timer (`days_until_coup`), **Syndicate Influence (0–100%)**, strict immutability safeguards protecting core story NPCs (`Elder Eldrin`, `Merchant Silas`, `Blacksmith Dennis`), peripheral suspect investigation (*Guard Lieutenant Bran* taking bribes at Forest Crossroads), boss duels, **Syndicate Cipher Fragments #1 & #2**, **Compromised Mind Mechanics** affecting secondary NPCs with cold detached speech and +40% economic surcharges, **Purification Exorcism Duels** against spectral `Shadow Parasites`, alchemical **Shadow Residue** loot, **Covert Sabotage Plots** against strategic control points with seamless territory allegiance shifts to the Void Cult upon timeout, high-threat **Shadow Assassin** strikes, the **Mage Guild Envoy Defense Quest**, the multi-phase world boss **Grand Inquisitor Vane, The Usurper** (enrages below 50% HP with *Usurper's Dominion*, summoning assassin bodyguards), endgame relic equipment (*Usurper's Royal Signet Ring*, *Crown of Shadows*), **3 Multi-Branching Endings** (*Total Purge*, *Shadow Sovereign*, *Compromised Kingdom*), cross-run **Mythos Legacy Recording**, living rumor dissemination, and real-time HUD coup tracking.
17. **Outpost Commander & Sovereign Caravans (`outpost.py`, `caravan.py`)**: Strategic territory fortresses constructible at secured faction control points (`stability >= 70%`, default cost 100g). Features physical stone watchtowers (`OutpostTowerSprite`) with royal heraldry banners, stationed garrison sentries (`OutpostGuardNPC`), **Daily Caravan Toll Taxation** (+10g daily per outpost from passing merchant caravans), regional stability locking in Faction Warfare, **Sovereign Player Caravans (`CARAVAN_SOVEREIGN_PLAYER`)** provisioned by upgraded settlement facilities (*Provisions*, *Refined Iron Goods*, *Tonic Crates*), **Trade Hub +30% Yield Boost**, **Companion Convoy Captains** (+100 XP upon arrival), **Dynamic Road Safety & Bandit Ambushes**, real-time **Emergency HUD Attack Alerts**, **Tactical Convoy Defense Skirmishes** against agile `BanditRaider` mercenaries, **Multi-Tier Outpost Upgrades** (Level 1: 10g/day & 2 guards; Level 2 Bastion: 25g/day & 3 guards; Level 3 Trade Citadel: 50g/day & 4 guards), **Automated Courier Relay Direct Deposits**, and the **Continental Trade Monopoly Milestone** (granting the title *"Merchant Sovereign of Asterra"* and Mythos legacy chronicles when 3+ outposts reach Level 3).
18. **The Cataclysm Epochs (`epochs.py`)**: Procedural generational overlay engine transforming world tilemaps dynamically in-memory without altering static disk assets. Features 4 distinct global eras:
    - **The Deluge Epoch (`EPOCH_DELUGE` - Zaman Air Bah)**: Floods 40%+ open grass terrains into vast archipelagos, generating **Procedural Wooden Raft Bridges (`wood_bridge`)** with breadth-first search pathfinding ensuring 100% path connectivity across all gateways, NPCs, chests, and waypoints, with continuous storm rain.
    - **The Scorched Blight (`EPOCH_SCORCHED` - Zaman Bara Api)**: Transforms surface landscapes into volcanic wastelands of charcoal ash (`ash_ground`), charred timber husks (`burnt_tree`), and active bubbling molten lava fissures (`magma`) that inflict thermal damage (-4 HP/s) unless protected by heat-resistant equipment or potions.
    - **The Glacial Winter (`EPOCH_GLACIAL` - Zaman Salju Abadi)**: Envelops Asterra in perpetual snowstorms (`snow`), snowy evergreen pines (`snow_tree`), and converts rivers/lakes into walkable slippery ice sheets (`ice`) governed by low-friction sliding momentum physics.
    - **Era of Balance (`EPOCH_DEFAULT`)**: The default temperate seasonal climate of peaceful Asterra.
    - **Generational Legacy State & Narrative Inheritance (`mythos.py`, `npc_memory.py`)**: Integrates with past hero runs in Mythos to dynamically seed starting epochs (e.g. fire/coup failures trigger Scorched Blight, swamp/drowning triggers Deluge, cavern/frost triggers Glacial Winter), paired with rich generational folklore dialogues from `Elder Eldrin`, `Blacksmith Dennis`, and `Merchant Silas`.
19. **Sovereign Guilds & The Continental Monopoly (`monopoly.py`)**: Advanced macro-economic and territorial resource control system. Features:
    - **Territorial Concession Deeds**: Purchasable crown resource deeds granting exclusive regional extraction rights: *Granite Cavern Mining Concession* (150g, yields +3 Iron Ore & +2 Granite Stone/day), *Deep Forest Herbal Rights* (100g, yields +4 Medicinal Herbs & +2 Luminescent Spores/day), and *Verdant Woodlands Timber Concession* (120g, yields +5 Oak Timber/day).
    - **Guild Commodity Warehouse (`GuildWarehouse`)**: Dedicated 300-capacity commodity stockpile receiving automated daily raw material deliveries from owned deeds.
    - **Bulk Market Liquidation**: Enables one-click bulk liquidation of stockpiled commodities directly to Silas/Market for gold (Iron Ore 8g, Herbs 6g, Spores 10g, Timber 5g, Stone 4g).
    - **Supply Hoarding & Price Surges**: Stockpiling $\ge 30$ units (80%+) of world Iron Ore triggers acute market scarcity, causing iron weapon and mineral store prices to surge by **2.5x**.
    - **Faction Military Embargoes**: Iron shortages or targeted trade embargoes against the Knights of Asterra inflict a **-20% DEF debuff** (0.8x) during territory wars. Cutting off medical herbs to Bandits cancels all out-of-combat/field dressing **Bandit HP regeneration**.
    - **Asterra Merchant Syndicate HQ & Gold Vault Banking**: Players owning 2+ deeds can construct the eastern headquarters (250g), unlocking the **Guild Gold Vault** with **+2% daily compound interest**.
    - **"The Sovereign Baron" Prestige Title & Perks**: Grants a permanent **30% merchant discount** at all shops, enables **Diplomatic Bribery** (50g) to pacify hostile factions, and inscribes permanent `MERCHANT_SYNDICATE_FOUNDED` historical events into generational `Mythos` chronicles.
    - **Living Economic Rumors**: Dynamically propagates market gossip (`rumor_iron_hoarding`, `rumor_bandit_herb_embargo`) reflecting citizen and merchant distress.
    - **Interactive Warehouse & Deeds UI Modal**: High-fidelity modal displaying real-time stockpile meters, liquidation actions, and deed acquisition cards.
20. **The Living Dungeon Sovereign: Crypt Architect (`dungeon_architect.py`)**: Grid-based personal dungeon management and lair defense system. Features:
    - **Dungeon Core Claiming**: Enables players to claim the primordial *Dungeon Core Stone* in the crypt, unlocking sovereign ownership and the title *"Crypt Sovereign"*.
    - **Architect Grid Trap Placement**: Construct lethal defense traps on dungeon grid tiles using gold and materials: *Spike Trap* (25g + 2 Granite Stone: 35 physical damage), *Iron Portcullis* (40g + 4 Iron Ore: 15 damage & movement obstruction), and *Bait Mimic Chest* (50g + 1 Luminescent Spore: 60 damage chomping strike).
    - **Beast Capture & Domestication**: Craft `Beast Capture Net` tools at the Blacksmith (2x Beast Leather, 1x Iron Ore, 20g) to ensnare weakened wild monsters (<20% HP). Captured beasts enter the dungeon reserve roster.
    - **Chamber Stationing & Guardian Synergy**: Domesticated beasts can be stationed at designated dungeon chambers, patrolling friendly to the player and boosting overall dungeon defense rating.
    - **Periodic 3-Day Raider Invasions**: Every 3 in-game days, AI rival adventurers, bandit warbands, or Nemesis outlaws assault the lair.
    - **Defense Simulation & Infamy Spoils**: Automatically or interactively tests traps and beast guardians against raider power. Repelling raiders awards **+30 Dungeon Infamy**, **+60–120 Gold**, and crafting material salvage (`Iron Ore`, `Timber`, `Beast Leather`).
    - **Multi-Floor Excavations & Sovereign Climax**: Deepen the lair into Floor 2 (*Deep Catacombs*, 200g + 50 Infamy) and Floor 3 (*Abyssal Vaults*, 400g + 100 Infamy), granting the legendary title *"The Lord of the Deep Catacombs"* and inscribing `DUNGEON_SOVEREIGNTY_ESTABLISHED` into generational `Mythos` chronicles.
    - **Real-Time Intruder Trap Collision Engine**: Detects enemy collisions with placed traps, automatically triggering damage, combat numbers, particles, and cooldown timers.
    - **Architectural Defense Rating**: Dynamic calculation of dungeon defense strength featuring trap synergy, diversity multipliers, and guardian attack power across all subterranean floors.
21. **Chrono-Echoes & Spacetime Fractures (`chrono.py`, `weather.py`, `npc_memory.py`, `mythos.py`)**: Non-destructive temporal manipulation, rolling timeline snapshot engine, paradox mirror boss duels, NPC déjà-vu reactivity, and the Aeon Sentinel continuum climax. Features:
    - **Rolling 3-Day Ring Buffer (`TimelineSnapshot`)**: Captures atomic point-in-time state snapshots across world day, clock, player stats, gold, XP, position, inventory, equipment, quests, and flags.
    - **Relic Item: Chrono-Weaver Hourglass & Aeon Core**: Legendary artifacts required to manipulate continuum energies and craft primordial gear.
    - **Atomic 3-Day Spacetime Rollback**: Rewinds world day, character metrics, and quest states cleanly with zero duplicate items, state desynchronization, or save file corruption.
    - **Temporal Fractures & Chrono-Doppelganger Mirror Boss (`ChronoDoppelganger`)**: Tampering with spacetime leaves an anomaly fissure and spawns a mirror shadow boss equipped with the player's pre-rewind gear, stats, and combat combos until vanquished.
    - **Atmospheric Temporal Rifts & Time Dilation (`WEATHER_TEMPORAL_RIFT`)**: Chromatic inverted violet-cyan sky tint with drifting chrono sparkles and 0.75x time-slow dilation during active fractures.
    - **NPC Déjà-Vu Reactivity (`NPCMemory`, `get_deja_vu_dialogue`)**: Village figures (Eldrin, Silas, Dennis, Faye, Mira) experience psychic resonance of erased timelines, unlocking contextual dialogue branches.
    - **Primordial Climax Boss: Aeon Sentinel (`AeonSentinel`) & Mythos Chronicle**: Face the ancient guardian of the spacetime fabric to stabilize the continuum, earning the prestige title *"Chrono-Weaver Supreme"* and inscribing `TEMPORAL_FABRIC_MENDED` into generational `Mythos` records.

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
