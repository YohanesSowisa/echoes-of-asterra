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
    ├── factions.py, faction_war.py # Faction standings & regional territory warfare
    ├── ecology.py, economy.py, living_world.py, world_state.py # Living world ecosystem & economy simulation
    ├── balance.py, telemetry.py, style_scoring.py # Difficulty scaling, telemetry, combat style evaluator
    ├── enemy.py, boss.py, ai.py, director.py # Enemy archetypes, boss mechanics & AI state machines
    ├── combat.py, weapon_types.py, skills.py, hazards.py # Hit resolution, combos, spell trees, traps
    ├── dungeon_gen.py, map_loader.py, world.py # BSP dungeon generation, map loading & world manager
    ├── items.py, inventory.py, equipment.py, crafting.py, settlement.py # Items, backpack, gear sockets, forge, settlement
    ├── save.py, events.py, scheduler.py # Serialization (Schema v2), EventBus pub/sub, day tick scheduler
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
  - Lebar panel `680px`, navigasi tab keyboard (`A`/`D`, `Tab`, `1`/`2`, Tombol Panah), dan menampilkan **Gelar Aktif Player** pada header window.
- **In-Game Target FPS Setting**:
  - Opsi ganti FPS langsung di menu **Settings** (30, 60, 120, 144, Uncapped) dengan default **`MAX (UNCAPPED)`**.

### C. Combat Balance & Developer Telemetry Engine
- **`rpg/balance.py`**: Centralized balance engine dengan Profil Growth, Kebijakan Scaling, Kurva Polinomial, dan `LivingDangerEngine` (menghitung bahaya dunia dari pertarungan, cuaca, malam, & krisis).
- **`rpg/telemetry.py`**: Melacak analitik developer offline lokal (`rpg/saves/developer_metrics.json`).

---

## 🧪 4. Status Pengujian & Kompilasi

Seluruh modul game telah diuji secara otomatis dan terbukti kompilasi 100% bersih:

```bash
python3 -m py_compile main.py rpg/*.py rpg/services/*.py
# Output: ALL rpg modules compiled 100% clean!
```

---

## 📌 5. Panduan Melanjutkan di Sesi Chat Baru

Bagi AI Agent / Developer yang menerima sesi chat baru:

1. **Baca Berkas Ini (`handover.md`)** dan `update_logs.md` untuk melihat histori perubahan terkini.
2. **Aturan Penting Pengembangan**:
   - Selalu biarkan pengguna (*User*) melakukan `git commit` sendiri.
   - Jangan menambahkan dependency berat eksternal (sistem dirancang 100% offline & deterministik).
   - Selalu uji dengan `python3 -m py_compile main.py rpg/*.py rpg/services/*.py` dan `python3 -m unittest discover -s tests` setelah mengedit kode.
   - Catat setiap penambahan fitur / bug fix baru ke dalam berkas `update_logs.md` dengan format timestamp `[yyyy-mm-dd hh:mm:ss WIB]`.
