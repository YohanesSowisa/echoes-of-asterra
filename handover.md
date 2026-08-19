# Echoes of Asterra — Project Context & Handover Guide

> **Dokumen Pengenalan Repositori & Panduan Serah Terima AI / Developer**  
> Dokumen ini dirancang khusus agar sesi chat baru (atau developer lain) dapat langsung memahami arsitektur, sistem yang sudah selesai dibuat, status saat ini, dan cara melanjutkan pengembangan game **Echoes of Asterra**.

---

## 🧭 1. Ringkasan Proyek

- **Nama Game**: *Echoes of Asterra*
- **Genre**: 2D Action RPG / Fantasy Settlement & Living World Simulation
- **Teknologi**: Python 3.10+, Pygame-ce 2.5+
- **Direktori Utama**: Root repositori (`echoes-of-asterra/`)
- **Cara Menjalankan Game**:
  ```bash
  python3 main.py
  ```


---

## 🏛️ 2. Arsitektur & Struktur Berkas Utama

```
echoes-of-asterra/
├── main.py                # Entry point launcher & Pygame display setup
├── requirements.txt       # Project dependencies (pygame-ce)
├── update_logs.md         # Full historical update and fix log (WIB format)
├── handover.md            # Technical handover handbook
├── README.md              # Project documentation
├── assets/                # Maps (JSON) & audio assets
├── saves/                 # Persistent state JSON files (achievements, bestiary, memories, mythos)
├── tests/                 # Comprehensive test suite (18+ test modules)
└── rpg/                   # Core game engine package
    ├── services/          # Service layer (Asset, Tilemap, Navigation, Noise, Container, Admin UI, Tween, Profiling, Data)
    ├── game.py            # Engine Orchestrator and main state machine
    ├── settings.py        # Display, keybindings, player speed & system constants
    ├── constants.py       # Color palettes, UI states, item & quest status constants
    ├── player.py          # Hero physics, combat combos, inventory & control state
    ├── ui.py              # HUD gauges, overlays, menus, tooltips & shop interface
    ├── npc.py, npc_memory.py, npc_schedule.py, rival.py # NPC objects, relationship memory, schedules, rival adventurer
    ├── memory.py, social.py, bard.py, mythos.py, mythos_reader.py # Memory, Social, Titles, Mythos legacy
    ├── consequences.py, rumors.py, emergent_quests.py # Delayed causal engine, Rumor board, Dynamic emergency quests
    ├── factions.py, faction_war.py, nemesis.py # Faction standings, regional warfare & persistent Nemesis captains
    ├── ecology.py, economy.py, living_world.py, world_state.py # Living world ecosystem & economy simulation
    ├── balance.py, telemetry.py, style_scoring.py # Difficulty scaling, telemetry, combat style evaluator
    ├── enemy.py, boss.py, ai.py, director.py # Enemy archetypes, boss mechanics & AI state machines
    ├── combat.py, weapon_types.py, skills.py, hazards.py # Hit resolution, combos, spell trees, traps
    ├── dungeon_gen.py, map_loader.py, world.py # BSP dungeon generation, map loading & world manager
    ├── items.py, inventory.py, equipment.py, crafting.py, settlement.py # Items, backpack, gear sockets, forge, settlement
    ├── save.py, events.py, scheduler.py # Serialization (Schema v3), EventBus pub/sub, day tick scheduler
    ├── camera.py, collision.py, particles.py, weather.py, lighting.py, sound.py # Viewport, AABB physics, SFX, Weather & Lighting
```

---

## 🌟 3. Fitur Utama yang Sudah Selesai Dibuat

### A. Living Reputation, Memory & Social Recognition Engine (Phase 1 – 4)
- **`rpg/memory.py`**:
  - `MemoryManager` mencatat memori sosial (`SocialMemory`) via event `EventBus` (`item_donated`, `quest_completed`, `enemy_killed`).
  - Rumus **Memory Decay Relevance Score**:
    $$\text{Relevance Score} = \text{Importance} \times \frac{1.0}{1.0 + 0.1 \times (\text{Hari Saat Ini} - \text{Hari Dibuat})}$$
- **`rpg/social.py`**:
  - Layer Reputasi Terpisah: **Global Reputation**, **NPC Personal Bonds**, dan **Faction Reputation**.
  - **Social Recognition Tiers**: `Hostile` $\rightarrow$ `Unknown` $\rightarrow$ `Recognized` $\rightarrow$ `Trusted` $\rightarrow$ `Respected` $\rightarrow$ `Friend` $\rightarrow$ `Hero` $\rightarrow$ `Legend`.
  - **`TitleEngine`**: Gelar emergen otomatis (*"Iron Benefactor"*, *"Crypt Delver"*, *"Scourge of Bandits"*, *"Guardian of Asterra"*).
- **`rpg/npc.py` & `rpg/ai.py`**:
  - Dialog kontekstual Dennis merespons memori sumbangan besi untuk guard.
  - Silas membuka **Stok Impor Langka Rahesian** saat hubungan mencapai tier `Trusted` / `Friend`.
  - Musuh (Bandit, Goblin, Mage) memiliki $15\%$ peluang **ragu-ragu (*hesitate*) atau mundur (*retreat*)** saat berhadapan dengan player bergelar *"Scourge of Bandits"*.
- **`rpg/bard.py` & `rpg/mythos.py`**:
  - NPC **Bard Finn** di Alun-Alun Desa menyanyikan lagu balada kepahlawanan prosedural dari memori aktif player.
  - Mythos Inheritance mengekspor gelar & memori utama ke patung pahlawan untuk generasi berikutnya.

### B. UI & Kontrol Karakter (Harvest Moon Freeze & Exclusive Single Panel)
- **Harvest Moon-style Control Freeze (`rpg/player.py`)**:
  - Ketika jendela UI apa pun (**`'V'`**, **`'I'`**, **`'N'`**, **`'G'`**), Dialog NPC, atau Toko Silas terbuka, kontrol gerakan (WASD), serangan (J), dash (Spasi), dan skill **dibekukan total** (`velocity = (0,0)`).
- **Exclusive Single Active Panel (`rpg/ui.py`)**:
  - Membuka satu panel UI otomatis menutup panel lain. Hanya 1 panel aktif di layar (mencegah tab overlapping).
- **Character Sheet UI (`'V'`)**:
  - Lebar panel `680px`, 6 Tab Interaktif (`[Factions]`, `[Social]`, `[Town]`, `[Achiev]`, `[Bestiary]`, `[Nemesis]`), navigasi keyboard (`A`/`D`, `Tab`, `1`–`6`, Tombol Panah), dan menampilkan **Gelar Aktif Player** pada header window.
- **In-Game Target FPS Setting**:
  - Opsi ganti FPS langsung di menu **Settings** (30, 60, 120, 144, Uncapped) dengan default **`MAX (UNCAPPED)`**.

### C. Combat Balance & Developer Telemetry Engine
- **`rpg/balance.py`**: Centralized balance engine dengan Profil Growth, Kebijakan Scaling, Kurva Polinomial, dan `LivingDangerEngine` (menghitung bahaya dunia dari pertarungan, cuaca, malam, & krisis).
- **`rpg/telemetry.py`**: Melacak analitik developer offline lokal (`rpg/saves/developer_metrics.json`).

### E. Companion Recruitment & Autonomous Expeditions (`rpg/companion.py`)
- **Recruitable Candidate Roster**: Tiga kandidat sekutu unik (`Ranger Faye` - DPS, `Guard Kai` - Tank, `Scholar Mira` - Healer) yang dapat direkrut setelah menyelesaikan quest atau memiliki gold cukup.
- **Tactical Combat Modes & AI**: Mode taktis party (`Attack`, `Tank`, `Heal`) yang menentukan perilaku AI sekutu saat mendampingi player (DPS fokus menyerang target terdekat, Tank melakukan taunt dan memiliki aggro tinggi, Healer meluncurkan aura penyembuhan saat HP player rendah).
- **Autonomous Resource Expeditions**: Player dapat mengirim sekutu untuk ekspedisi 1–3 hari ke berbagai zona (*forest*, *cave*, *ruins*, *dungeon*) untuk mengumpulkan gold dan material langka dengan kalkulasi risiko berbasis `danger_level` wilayah.
- **Contextual Banter & Party Progression**: Sekutu berbagi XP saat monster dikalahkan, naik level meningkatkan stat sesuai arketipe, dan mengeluarkan dialog banter kontekstual berdasarkan cuaca, lokasi, dan kemenangan pertempuran.

### F. Seasonal Village Festival Minigames (`rpg/festival.py`)
- **Perluasan Event Village Festival**: Mengubah event festival menjadi 3 minigame interaktif di alun-alun desa:
  1. **Target Archery Contest**: Minigame bidikan presisi dengan timing gauge meter bar bergerak untuk mencetak Bullseye, Inner Ring, dan Outer Ring (0–500 score).
  2. **Harvest Sprint**: Minigame uji reaksi cepat memanen tanaman desa melawan batas waktu 15 detik (0–500 score).
  3. **Dennis's Feast & Brew Challenge**: Minigame push-your-luck turn-based mengelola rasa kenyang (*fullness*) melawan Blacksmith Dennis.
- **Seasonal Records & Tiered Rewards**: Mencatat rekor terbaik per musim (*Spring, Summer, Autumn, Winter*), memberikan reward bertingkat (*Bronze, Silver, Gold*), memberikan gelar juara (*"Asterra Marksman"*, *"Grand Harvester"*, *"Master of Feasts"*), dan menyebarkan rumor kemenangan ke `RumorBoard`.

### G. Nemesis Vendetta Sieges (`rpg/nemesis.py`)
- **Dynamic Warband Assaults**: Captain level $\ge 4$ atau dengan trait agresif (*Bloodthirsty, Cunning, Hero Slayer*) memicu pengepungan wilayah berdurasi 3 hari in-game dengan pengawal minion.
- **Controlled Escalation Loop**: Cooldown global 5 hari antar-siege, batas maksimal 1 siege aktif bersamaan, cap maksimal Lv.10 dan 3 trait.
- **Definitive Match & Consequences**: Guard `active_siege_id` saat membunuh captain di medan siege, resolusi kemenangan (hadiah +100g, kestabilan & kemakmuran wilayah pulih, catatan permanen di `Mythos`), resolusi kekalahan (wilayah jatuh ke bandit, kestabilan anjlok, captain naik level).
- **Direct UI Alerts & Rumor Warning**: Notifikasi toast prioritas tinggi saat siege dimulai dan peringatan darurat hari terakhir.

### H. Ancestral Soul Pacts & Physical Mutations (`rpg/pacts.py`)
- **Primordial Covenants**: Sistem ikrar pakta purba di altar khusus dunia (3 jalur unik: Void, Titan, Solar Seraph).
- **Pact Mastery Tiers & Scaling**: 3 Tier Penguasaan (Novice $\rightarrow$ Ascendant $\rightarrow$ Paragon) yang terbuka melalui perolehan XP monster.
- **Procedural Physical Sprite Mutations (`rpg/animation.py`)**: Mutasi visual 100% in-memory (tentakel ungu dan mata ketiga dahi untuk Void; lempeng batu granit, pundak raksasa, dan tanduk kristal untuk Titan; sayap malaikat emas berbulu dan halo melayang untuk Solar).
- **Primordial Weapon Forging (`rpg/crafting.py`, `rpg/items.py`)**: Penempaan senjata legendaris berkat pakta (*Voidbrand Scythe*, *Titan Cragcleaver*, *Sunfire Morningstar*) di Blacksmith Dennis.
- **Cross-Run Mythos Inheritance (`rpg/mythos.py`)**: Pencatatan riwayat ikrar pakta dan pewarisan relik primordial leluhur ke hero generasi berikutnya.
- **Dedicated Spell Keybinding**: Tombol `Z` (`pygame.K_z`) untuk memicu mantra primordial aktif saat pertempuran.
- **Reversible Purification Ritual**: Pelepasan pakta di Sanctuary Altar Desa dengan biaya `150 Gold` + `1x Starlight Crystal` dan cooldown pemulihan 3 hari (`cleansing_cooldown_days = 3`).

### I. The Sunken Mire & Ancient Leylines (`rpg/sunken_mire.py`, `rpg/leylines.py`)
- **Submerged Wetland Biome (`MAP_SUNKEN_MIRE`)**: Peta rawa baru dengan kepulauan gambut yang terhubung ke Danau (`lake`).
- **Dynamic Tide Cycles**: Siklus pasang surut air laut/rawa berbasis waktu in-game. *High Tide* menenggelamkan jalur, memicu racun rawa, dan memberi penalti gerak 25%; *Low Tide* mengungkap jalur lumpur rahasia dan peti relik purba.
- **Marsh Ecology & Monsters**: Predator amfibi `MireLurker` dan parasit pengeroyok `BogLeech` yang menjatuhkan bahan rawa (`Mire Reed`, `Leech Mucus`, `Sunken Relic`).
- **Ancient Leyline Network & Overcharging**: Jaringan simpul konduit kristal kuno di seluruh penjuru Asterra yang dapat diaktivasi dengan 10 Mana untuk membuka *Fast Travel* instan. Penyaluran *Starlight Crystal* / *Sunken Relic* meng-overcharge konduit selama 24 jam in-game (mengunci *Low Tide* permanen di rawa dan memberikan buff regional).
- **Mire Flora Foraging & Alchemy**: Simpul panen botani rawa (*Bog Blossom*, *Glow Lotus*, *Luminescent Spore*) dan penempaan ramuan alkimia (*Waterstrider Elixir*, *Mire Cleansing Draught*, *Leyline Surge Tonic*).
- **The Submerged Temple of Asterra (`MAP_SUBMERGED_TEMPLE`)**: Dungeon candi bawah air kuno yang berisi penjaga batu `TempleGuardian` dan ruang pertarungan boss utama.
- **Tidal World Boss — Morvath, the Mire Leviathan**: Pertarungan boss 2 fase amfibi colossus (sabetan ekor area, geyser, dan enrage *Tidal Miasma Surge* di bawah 50% HP yang memanggil kawanan *Bog Leech*).
- **Leyline Resonant Equipment**: Penempaan perlengkapan legendaris dari sisik Morvath dan kristal konduit (*Leviathan Scale Mail*, *Tidecaller Trident*, *Conduit Ring of Leylines*).
- **Leyline Rot Contamination & Cross-Zone Blight**: Sistem pembusukan konduit (Rot 0-100%) dengan sarang spora rawa interaktif (`SporeNestSprite`), mutasi serigala hutan menjadi `SporeHostWolf` beracun (ledakan spora area saat mati), dan quest darurat Noticeboard.
- **HUD & Persistence**: Indikator fase pasang-surut real-time, badge level Rot `☣️ ROT: xx%`, dan timer aktif ramuan di HUD, serta peningkatan `SAVE_SCHEMA_VERSION = 7`.

### J. The Doomsday Infiltration: Shadow Syndicate & The Usurper (`rpg/conspiracy.py`)
- **Conspiracy & Coup Engine**: Pelacak intrik konspirasi Shadow Syndicate dengan penghitung mundur 30 hari (`days_until_coup`), metrik pengaruh sindikat (`syndicate_influence`, 0–100%), dan peringatan darurat saat sisa waktu $\le 5$ hari.
- **Immutable Core NPC Safeguards**: Perlindungan absolut tak tertembus untuk tokoh inti alur cerita dan ekonomi (`Elder Eldrin`, `Merchant Silas`, `Blacksmith Dennis`).
- **Peripheral Suspect Confrontation**: Mini-boss `CorruptLieutenantBran` di persimpangan jalan Hutan. Mengalahkannya memangkas pengaruh sindikat sebesar -15%, membuka `Syndicate Cipher Fragment #1`, dan menyebarkan rumor terbongkarnya pengkhianat.
- **Compromised Minds & Purification Exorcisms**: Mekanik cuci otak NPC sekunder (*Miner Garth*, *Ranger Faye*, *Scholar Mira*) dengan dialog dingin, biaya layanan +40%, duel pertempuran melawan `ShadowParasite`, dan pemurnian akal sehat seutuhnya berhadiah *Shadow Residue*.
- **Covert Territory Shifts & Envoy Defense**: Operasi sabotase tertutup 3 hari terhadap titik kontrol militer (`ruins_plaza`) yang secara halus mengalihkan kendali wilayah ke `FACTION_CULT` jika tidak dicegah, musuh berkecepatan tinggi `ShadowAssassin`, serta quest perlindungan Envoy Vaelin berhadiah `Syndicate Cipher Fragment #2`.
- **The Grand Usurper Climax & Multi-Endings**: Pertarungan world boss multi-fase melawan *Grand Inquisitor Vane, The Usurper* (enrage di bawah 50% HP memanggil kawanan assassin), perlengkapan relic (*Usurper's Royal Signet Ring*, *Crown of Shadows*), serta 3 percabangan ending (*Total Purge*, *Shadow Sovereign*, *Compromised Kingdom*) yang tercatat abadi di `Mythos`.
- **HUD Coup Tracker**: Badge status real-time `🕵️ COUP: Day X/30 (xx%)` di HUD.

### K. Outpost Commander & Sovereign Caravans (`rpg/outpost.py`, `rpg/caravan.py`)
- **Strategic Outpost Construction**: Pembangunan pos komando militer berbenteng di titik kontrol wilayah (`forest_crossroads`, `cave_depths`, `ruins_plaza`, `lake_pier`) saat stabilitas $\ge 70\%$ seharga 100g.
- **Caravan Toll Taxation**: Pendapatan pajak harian (+10g per pos) dari karavan dagang yang melintas, dapat diklaim mandiri atau sekaligus via `collect_all_tolls()`.
- **Faction Warfare Stability Lock**: Pos aktif mengunci stabilitas wilayah melawan degradasi harian ($\ge 85\%$) dan mencegah peralihan kekuasaan sepihak.
- **Physical World Presence**: Menara batu berbenteng interaktif (`OutpostTowerSprite`) dan prajurit penjaga pos (`OutpostGuardNPC`) yang bertambah sesuai level.
- **Sovereign Player Caravans (`CARAVAN_SOVEREIGN_PLAYER`)**: Pengiriman karavan dagang berbendera pemain dari desa ke pos militer dengan komoditas bertingkat (*Provisions*, *Refined Iron Goods*, *Tonic Crates*), bonus +30% hasil pada spesialisasi Trade Hub, serta penugasan companion kapten bersenjata berhadiah +100 XP.
- **Real-Time Ambush Alerts & Convoy Defense**: Simulasi pembegalan karavan di jalan raya, badge peringatan darurat HUD, pertarungan taktis melawan musuh `BanditRaider` di world map, hadiah penyelamatan (+50 EXP, +30g, +10 Road Safety), dan konsekuensi kehancuran gerobak/cedera companion jika waktu 60 detik terlewat.
- **Multi-Tier Outpost Upgrades & Automated Courier Relays**: Peningkatan pos berjenjang (Level 1: 10g/day & 2 guards; Level 2 Bastion: 25g/day & 3 guards; Level 3 Trade Citadel: 50g/day & 4 guards). Pos Level 3 mengotomatisasi penyetoran deviden pajak harian langsung ke pundi-pundi pemain tanpa klaim manual.
- **Continental Trade Monopoly Climax**: Mengembangkan 3+ pos ke Level 3 membuka gelar bergengsi *"Merchant Sovereign of Asterra"*, mencatatkan pencapaian abadi `CONTINENTAL_TRADE_MONOPOLY` di `Mythos`, dan menyebarkan rumor kejayaan ekonomi di Asterra.

### L. The Cataclysm Epochs (`rpg/epochs.py`)
- **Procedural In-Memory Tilemap Overlays**: Engine mutasi tilemap prosedural langsung di memori saat memuat zona tanpa memodifikasi berkas JSON statis di disk.
- **The Deluge Epoch (Zaman Air Bah)**: Menenggelamkan 40%+ daratan rumput terbuka menjadi perairan luas di zona permukaan Asterra dengan jembatan rakit kayu (`wood_bridge`) dan cuaca hujan/badai konsisten.
- **The Scorched Blight (Zaman Bara Api)**: Mengubah lanskap menjadi tanah abu vulkanik (`ash_ground`), pohon terbakar (`burnt_tree`), dan retakan magma cair (`magma`) yang memberi hazard thermal burn (-4 HP/s) tanpa proteksi sepatu tahan api/elixir.
- **The Glacial Winter (Zaman Salju Abadi)**: Menyelimuti Asterra dalam salju abadi (`snow`), pohon cemara salju (`snow_tree`), dan membekukan sungai/danau menjadi lembaran es licin (`ice`) dengan fisika inersia luncur (*low-friction ice sliding*).
- **100% Path Accessibility Guarantee**: Algoritma validasi konektivitas BFS flood-fill memastikan seluruh gateway dan tujuan misi tetap 100% dapat dijangkau.
- **Generational Legacy State & Narrative Inheritance (`mythos.py`, `npc_memory.py`)**: Hasil akhir hero sebelumnya menentukan era awal playthrough berikutnya (gagal api $\rightarrow$ Scorched, tenggelam $\rightarrow$ Deluge, beku $\rightarrow$ Glacial), diiringi dialog folklor generasional dari Elder Eldrin, Dennis, dan Silas.

### M. Sovereign Guilds & The Continental Monopoly (`rpg/monopoly.py`)
- **Territorial Concession Deeds**: Akta konsesi sumber daya eksklusif (*Mining Concession* 150g $\rightarrow$ +3 Iron Ore & +2 Granite Stone/day; *Herbal Rights* 100g $\rightarrow$ +4 Medicinal Herbs & +2 Luminescent Spores/day; *Timber Concession* 120g $\rightarrow$ +5 Oak Timber/day).
- **Guild Commodity Warehouse**: Gudang penampungan komoditas berkapasitas 300 unit yang menerima kiriman pasokan otomatis harian dari akta konsesi yang dimiliki.
- **Bulk Market Liquidation**: Fitur likuidasi borongan komoditas langsung ke pasar untuk mendapatkan Gold sesuai harga pasar (Iron Ore 8g, Herbs 6g, Spores 10g, Timber 5g, Stone 4g).
- **Supply Hoarding & Silas 2.5x Price Surge**: Penimbunan $\ge 30$ unit (80%+) Iron Ore di gudang memicu lonjakan harga senjata besi di toko Silas hingga **2.5x** lipat.
- **Faction Military Embargoes**: Kelangkaan besi / embargo terarah memotong pertahanan ksatria (*Knights of Asterra*) sebesar **-20% DEF** (0.8x) dalam perang faksi. Embargo tanaman obat ke Bandit mematikan regenerasi HP musuh Bandit.
- **Asterra Merchant Syndicate HQ & Gold Vault Banking**: Pembangunan markas besar serikat dagang (250g) membuka brankas emas dengan **bunga majemuk harian +2%** (`deposit_vault`, `withdraw_vault`).
- **"The Sovereign Baron" Prestige Title & Perks**: Memberikan diskon belanja permanen **30%** di semua toko pedagang, membuka opsi **Suap Diplomatik** (50g) untuk meredakan permusuhan faksi, dan mencatatkan `MERCHANT_SYNDICATE_FOUNDED` di `Mythos`.
- **Living Economic Rumors**: Rumor pasar dinamis (`rumor_iron_hoarding`, `rumor_bandit_herb_embargo`) menyebar di desa.
- **Interactive UI Modal**: Modal antarmuka gudang & akta konsesi dua kolom dengan indikator stok visual real-time dan aksi likuidasi instan.

### N. The Living Dungeon Sovereign: Crypt Architect (`rpg/dungeon_architect.py`)
- **Dungeon Core Claiming**: Pemain dapat mengklaim *Dungeon Core Stone* di lantai Crypt, membuka kepemilikan mutlak atas labirin bawah tanah dan memperoleh gelar *"Crypt Sovereign"*.
- **Architect Grid Trap Placement**: Konstruksi jebakan pertahanan berbasis petak grid dengan biaya emas dan material (*Spike Trap*: 25g + 2 Granite Stone, 35 DMG; *Iron Portcullis*: 40g + 4 Iron Ore, 15 DMG & rintangan gerak; *Bait Mimic Chest*: 50g + 1 Luminescent Spore, 60 DMG gigitan). Pembongkaran jebakan mengembalikan 50% modal emas.
- **Beast Capture & Domestication**: Pembuatan jaring perangkap `Beast Capture Net` di Blacksmith (2x Beast Leather, 1x Iron Ore, 20g) untuk menangkap monster liar yang sekarat (<20% HP).
- **Chamber Stationing & Guardian Synergy**: Menempatkan monster tangkapan di ruangan labirin untuk berpatroli dan melipatgandakan rating pertahanan labirin (+2x ATK guardian).
- **Periodic 3-Day Raider Invasions**: Serangan periodik setiap 3 hari oleh regu petualang rival, bandit penjarah, atau kelompok outlaws Nemesis.
- **Defense Simulation & Infamy Spoils**: Menguji rating pertahanan labirin melawan kekuatan penyerang. Berhasil menghalau memberikan **+30 Dungeon Infamy**, **+60–120 Gold**, dan rampasan material (`Iron Ore`, `Timber`, `Beast Leather`).
- **Multi-Floor Excavations & Sovereign Climax**: Ekspansi bertingkat ke Lantai 2 (*Deep Catacombs*, 200g + 50 Infamy) dan Lantai 3 (*Abyssal Vaults*, 400g + 100 Infamy), membuka gelar pamungkas *"The Lord of the Deep Catacombs"* dan mencatat `DUNGEON_SOVEREIGNTY_ESTABLISHED` ke dalam kronik `Mythos`.
- **Real-Time Trap Intruder Collision Engine**: Deteksi tabrakan otomatis terhadap monster/musuh penginvasi yang memicu damage, angka tempur, partikel darah/ledakan, dan timer cooldown independen per jebakan.
- **Architectural Defense Rating**: Perhitungan dinamis skor pertahanan labirin dengan pengganda variasi jenis jebakan (*diversity bonus*) dan kekuatan monster penjaga di seluruh lantai subterranean.

### O. Chrono-Echoes & Spacetime Fractures (`rpg/chrono.py`, `rpg/weather.py`, `rpg/npc_memory.py`, `rpg/mythos.py`)
- **Rolling 3-Day Ring Buffer Snapshot Engine**: Perekaman snapshot memori atomik non-destruktif atas siklus hari, jam dunia, HP/stamina/gold/XP/koordinat pemain, tumpukan inventaris, perlengkapan, progres misi, dan bendera dunia.
- **Relic Item: Chrono-Weaver Hourglass & Aeon Core**: Artifak legendaris temporal yang digunakan untuk memanipulasi ruang dan waktu serta menempa perlengkapan primordial.
- **Atomic 3-Day Spacetime Rollback**: Memutar balik siklus hari dunia, statistik karakter, dan status misi hingga 3 hari ke masa lalu secara bersih tanpa duplikasi item, desinkronisasi, atau korupsi berkas save.
- **Temporal Fractures & Chrono-Doppelganger Mirror Boss (`ChronoDoppelganger`)**: Menimbulkan celah anomali ruang-waktu di koordinat rewind dan memunculkan bos bayangan cermin yang meniru senjata, armor, level, dan kombo serangan pemain pra-rewind hingga dikalahkan.
- **Atmospheric Temporal Rifts & Time Dilation (`WEATHER_TEMPORAL_RIFT`)**: Lapisan langit violet-cyan kromatik dengan partikel chrono sparkles dan efek perlambatan waktu $0.75\times$ (faktor dilatasi 25%) selama celah aktif.
- **NPC Déjà-Vu Reactivity (`NPCMemory`, `get_deja_vu_dialogue`)**: Tokoh desa (`Eldrin`, `Silas`, `Dennis`, `Faye`, `Mira`) merasakan getaran psikis dari lini masa yang terhapus, membuka cabang dialog kontekstual khusus.
- **The Aeon Sentinel Climax Boss & Mythos Chronicle (`AeonSentinel`)**: Pertarungan bos primordial penjaga ruang-waktu untuk menstabilkan kontinum Asterra, membuka gelar prestise *"Chrono-Weaver Supreme"* dan mencatat `TEMPORAL_FABRIC_MENDED` ke dalam kronik `Mythos`.

---

## 🧪 4. Status Pengujian & Kompilasi

Seluruh **365 unit test** di **57 test modules** telah diuji secara otomatis dan lulus 100%:

```bash
python3 -m py_compile main.py rpg/*.py rpg/services/*.py tests/*.py
# Output: ALL modules compiled 100% clean!

python3 -m unittest discover -s tests
# Output: Ran 365 tests in 0.910s - OK
```

---

## 📌 5. Panduan Melanjutkan di Sesi Chat Baru

Bagi AI Agent / Developer yang menerima sesi chat baru:

1. **Baca Berkas Ini (`handover.md`)** dan `update_logs.md` untuk melihat histori perubahan terkini.
2. **Aturan Penting Pengembangan**:
   - Selalu biarkan pengguna (*User*) melakukan `git commit` sendiri.
   - Jangan menambahkan dependency berat eksternal (sistem dirancang 100% offline & deterministik).
   - Pastikan Save Schema (`SAVE_SCHEMA_VERSION = 7`) dan migrasi backward compatibility selalu terjaga di `rpg/save.py`.
   - Selalu uji dengan `python3 -m py_compile main.py rpg/*.py rpg/services/*.py` dan `python3 -m unittest discover -s tests` setelah mengedit kode.
   - Catat setiap penambahan fitur / bug fix baru ke dalam berkas `update_logs.md` dengan format timestamp `[yyyy-mm-dd hh:mm:ss WIB]`.

---

## 🗺️ 6. Module Dependency Map & Architecture Matrix

Berikut adalah peta ketergantungan lengkap seluruh modul `rpg/*.py` (30+ modul terintegrasi). Gunakan matriks ini untuk menganalisis dampak perubahan (*blast radius*) sebelum memodifikasi file.

### A. Pengelompokan Modul Berdasarkan Subsistem

| Kategori | Modul | Tanggung Jawab Utama |
|---|---|---|
| **Core Engine** | `game.py`, `settings.py`, `constants.py`, `events.py`, `scheduler.py`, `save.py`, `services/*` | State machine, event pub/sub, time loop, serialisasi data |
| **Player & Combat** | `player.py`, `combat.py`, `weapon_types.py`, `skills.py`, `equipment.py`, `inventory.py`, `items.py`, `crafting.py` | Kontrol hero, kombo senjata, sistem poise, spell trees, inventory |
| **Enemies & AI** | `enemy.py`, `boss.py`, `ai.py`, `director.py` | Arketipe musuh, AI state machines, encounter pacing |
| **World & Environment** | `world.py`, `map_loader.py`, `dungeon_gen.py`, `weather.py`, `lighting.py`, `hazards.py`, `camera.py`, `collision.py`, `particles.py`, `sound.py` | Rendering peta, BSP dungeon, cuaca dinamis, siklus siang-malam |
| **Living Simulation** | `living_world.py`, `world_state.py`, `factions.py`, `faction_war.py`, `settlement.py`, `economy.py`, `ecology.py`, `rumors.py`, `consequences.py`, `emergent_quests.py`, `rival.py` | Simulasi otonom dunia, perang wilayah, faksi, rumor, ekologi |
| **Memory & Social** | `npc.py`, `npc_memory.py`, `npc_schedule.py`, `memory.py`, `social.py`, `bard.py`, `mythos.py`, `mythos_reader.py` | Memori sosial, relasi NPC, balada Bard Finn, pewarisan pahlawan |
| **UI & Feedback** | `ui.py`, `notification.py`, `style_scoring.py`, `balance.py`, `telemetry.py` | HUD gauges, tab tutorial 2D grid, toast queue, style scoring |

---

### B. Matriks Ketergantungan 8 Expansion Pillars

Daftar modul 8 Pillar, apa yang diimpor olehnya (*Dependencies*), dan siapa yang mengimpornya (*Reverse Dependencies*):

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                               8 MASTER EXPANSION PILLARS                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### 🌊 Pillar 1: Sunken Mire & Ancient Leylines (`sunken_mire.py`, `leylines.py`)
- **Impor Langsung (Dependencies)**: `constants.py`, `items.py`, `events.py`, `settings.py`
- **Diimpor Oleh (Reverse Dependencies)**:
  - `world.py`: Men-spawn `LeylineSprite` dan `MireHerbSprite` di map.
  - `player.py`: Menghitung penalti kecepatan air rawa (`get_speed_multiplier()`) dan durasi elixir (`waterstrider_timer`).
  - `ui.py`: Menampilkan HUD status badge pasang-surut (`TIDE`) dan kontaminasi spora (`ROT`).
  - `save.py`: Serialisasi status pasang-surut dan nodus leylines aktif (Schema v7).
  - `game.py`: Memanggil `mire_manager.update()` dan `leyline_manager.update()`.

#### 🕵️ Pillar 2: Doomsday Conspiracy & Infiltration (`conspiracy.py`)
- **Impor Langsung (Dependencies)**: `constants.py`, `items.py`, `events.py`, `rumors.py`, `npc_memory.py`
- **Diimpor Oleh (Reverse Dependencies)**:
  - `game.py`: Mengelola siklus countdown 30 hari konspirasi.
  - `ui.py`: Merender badge status darurat `🕵️ COUP: Dxx/30 (xx%)` di HUD.
  - `world.py`: Men-spawn agen sindikat `CorruptLieutenantBran`.
  - `faction_war.py`: Memproses sabotase terselubung (`covert_shift_ownership`).
  - `save.py`: Serialisasi data pengaruh sindikat dan status tersangka.

#### 🏰 Pillar 3: Frontier Outposts & Sovereign Caravans (`outpost.py`, `caravan.py`)
- **Impor Langsung (Dependencies)**: `constants.py`, `events.py`, `items.py`, `companion.py`, `settlement.py`, `faction_war.py`
- **Diimpor Oleh (Reverse Dependencies)**:
  - `game.py`: Menangani timer simulasi ambush karavan dan perpindahan konvoi.
  - `world.py`: Men-spawn menara outpost (`OutpostTowerSprite`), sentri penjaga, dan gerobak karavan (`CaravanEntity`).
  - `ui.py`: Menampilkan peringatan darurat sergapan karavan (`⚠️ CARAVAN ATTACKED!`).
  - `save.py`: Serialisasi data kepemilikan outpost, level benteng, dan ledger pajak.
- ⚠️ **Klaster Keterikatan Erat (Tightly Coupled Group)**:
  `outpost.py` $\longleftrightarrow$ `caravan.py` $\longleftrightarrow$ `settlement.py` $\longleftrightarrow$ `companion.py`
  *(Perubahan pada sistem karavan wajib memeriksa status pos luar dan sekutu yang ditugaskan sebagai kapten).*

#### ❄️ Pillar 4: Cataclysm Epochs (`epochs.py`)
- **Impor Langsung (Dependencies)**: `constants.py`, `events.py`, `settings.py`, `weather.py`, `animation.py`
- **Diimpor Oleh (Reverse Dependencies)**:
  - `world.py`: Menerapkan mutasi tilemap prosedural in-memory (Deluge, Scorched, Glacial, Withered).
  - `player.py`: Menangani kontak hazard magma cair (-4 HP/s) dan inersia luncur es licin (`ice`).
  - `ui.py`: Merender badge indikator era aktif di layar.
  - `mythos.py`: Mewariskan era awal generasi berikutnya berdasarkan kekalahan hero terdahulu.
  - `save.py`: Serialisasi era siklus kataklisme aktif.

#### 💰 Pillar 5: Continental Monopoly & Trade Guilds (`monopoly.py`)
- **Impor Langsung (Dependencies)**: `constants.py`, `items.py`, `events.py`, `economy.py`, `faction_war.py`, `rumors.py`
- **Diimpor Oleh (Reverse Dependencies)**:
  - `game.py`: Menghitung bunga harian brankas emas (+2% per hari).
  - `ui.py`: Menampilkan modal antarmuka gudang komoditas dan pembelian akta konsesi.
  - `economy.py`: Menerapkan lonjakan harga 2.5x saat terjadi penimbunan pasokan (*hoarding*).
  - `save.py`: Serialisasi akta konsesi, stok gudang komoditas, dan status embargo faksi.

#### 🔮 Pillar 6: Ancestral Soul Pacts (`pacts.py`)
- **Impor Langsung (Dependencies)**: `constants.py`, `items.py`, `events.py`, `combat.py`
- **Diimpor Oleh (Reverse Dependencies)**:
  - `player.py`: Menghitung jangkauan serangan (`get_attack_range_multiplier()`) dan spell aktif (`cast_pact_ability()`).
  - `equipment.py`: Menerapkan bonus defense Titan (+6..+12) dan penalti kecepatan gerak (0.90x).
  - `world.py`: Men-spawn altar perjanjian (`PactAltarSprite`) di dungeon, cave, ruins, dan sanctuary village.
  - `animation.py`: Merender mutasi fisik prosedural (tentakel void, pauldrons granit, sayap emas solar).
  - `ui.py`: Menampilkan status pakta dan progress mastery tier di lembar karakter (`'V'`).
  - `save.py`: Serialisasi pakta aktif dan tier ascension.

#### 🏛️ Pillar 7: Living Dungeon Architect (`dungeon_architect.py`)
- **Impor Langsung (Dependencies)**: `constants.py`, `items.py`, `events.py`, `enemy.py`, `combat.py`
- **Diimpor Oleh (Reverse Dependencies)**:
  - `game.py`: Menjalankan invasi periodik raider 3 hari sekali dan engine jebakan real-time.
  - `ui.py`: Menampilkan menu konstruksi jebakan, ledger infamy, dan ekskavasi lantai subterranean.
  - `enemy.py`: Menyediakan data monster liar yang dapat dijinakkan (`can_capture_enemy()`).
  - `save.py`: Serialisasi kepemilikan dungeon core, layout jebakan, dan monster peliharaan.

#### ⏳ Pillar 8: Chrono-Echoes & Spacetime Fractures (`chrono.py`)
- **Impor Langsung (Dependencies)**: `constants.py`, `items.py`, `events.py`, `weather.py`, `npc_memory.py`, `mythos.py`
- **Diimpor Oleh (Reverse Dependencies)**:
  - `game.py`: Memproses pemutaran waktu atomik 3 hari (`execute_temporal_rewind()`).
  - `weather.py`: Memicu cuaca anomali celah temporal (`WEATHER_TEMPORAL_RIFT`).
  - `npc_memory.py`: Mengaktifkan cabang dialog déjà-vu pada tokoh desa.
  - `enemy.py`: Men-spawn bos cermin `ChronoDoppelganger` dan bos pamungkas `AeonSentinel`.
  - `save.py`: Serialisasi snapshot riwayat waktu dan celah fraktur aktif.

---

### C. Panduan Keamanan Modifikasi (Blast Radius Rules)

1. **Mengubah `constants.py` / `settings.py`**: Berdampak pada SELURUH game. Pastikan tidak menghapus ID yang dipakai serialisasi `save.py`.
2. **Mengubah `player.py`**: Pastikan recalculation stats di `equipment.py` tetap sinkron (termasuk modifier Soul Pacts dan Alchemical Elixirs).
3. **Mengubah `world.py`**: Pastikan koordinat spawn entitas baru tidak bertabrakan dengan entitas existing di map yang sama (lihat koordinat aman di catatan audit).
4. **Menambahkan Sistem Baru**: Selalu manfaatkan `EventBus` (`events.py`) untuk decoupled pub/sub daripada menambahkan hard circular references.
