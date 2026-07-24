# Echoes of Asterra — Project Context & Handover Guide

> **Dokumen Pengenalan Repositori & Panduan Serah Terima AI / Developer**  
> Dokumen ini dirancang khusus agar sesi chat baru (atau developer lain) dapat langsung memahami arsitektur, sistem yang sudah selesai dibuat, status saat ini, dan cara melanjutkan pengembangan game **Echoes of Asterra**.

---

## 🧭 1. Ringkasan Proyek

- **Nama Game**: *Echoes of Asterra*
- **Genre**: 2D Action RPG / Fantasy Settlement & Living World Simulation
- **Teknologi**: Python 3.10+, Pygame-ce 2.5+
- **Direktori Utama**: `/Users/yohanes29/Documents/python-playground/games/rpg`
- **Cara Menjalankan Game**:
  ```bash
  cd /Users/yohanes29/Documents/python-playground/games/rpg
  python main.py
  ```

---

## 🏛️ 2. Arsitektur & Struktur Berkas Utama

```
rpg/
├── main.py                # Entry point game loop & inisialisasi Pygame
├── game.py                # Game Engine orchestrator, state machine, clock, loop
├── settings.py            # Konfigurasi konstanta layar, FPS (default=0 uncapped), & grid
├── constants.py           # State game, warna UI, status quest, level relasi
├── player.py              # Karakter utama (pergerakan, serangan, skill, UI freeze logic)
├── ui.py                  # UI Manager (HUD, Character Sheet 680px, Inventory, Dialogue)
├── npc.py                 # Objek NPC (Elder, Dennis, Silas, Faye, BardFinn, Statue, Altar)
├── memory.py              # Phase 1: Centralized MemoryEngine & Memory Decay formula
├── social.py              # Phase 2: Reputation Manager, Recognition Tiers & TitleEngine
├── bard.py                # Phase 4: BardSongEngine (Penggubah lagu balada memori)
├── mythos.py              # Mythos Inheritance System (Legasi pahlawan antar playthrough)
├── balance.py             # Adaptive Level Scaling, Growth Profiles, & Living Danger Score
├── telemetry.py           # Offline Developer Telemetry Logger (developer_metrics.json)
├── enemy.py               # Arketipe musuh (Slime, Wolf, Skeleton, Mage, Boss)
├── ai.py                  # Finite State Machine AI musuh & Enemy Recognition Hesitation
├── world.py               # World Manager & Spawner peta (Village, Forest, Crypt)
├── living_world.py        # Living World Simulation (Ekonomi, Karavan, Pertumbuhan Desa)
├── update_logs.md         # Histori log perbaikan & fitur lengkap (Format WIB)
└── saves/                 # Direktori penyimpanan JSON (memories, reputation, mythos)
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
- **Harvest Moon-style Control Freeze (`player.py`)**:
  - Ketika jendela UI apa pun (**`'C'`**, **`'I'`**, **`'Q'`**, **`'G'`**), Dialog NPC, atau Toko Silas terbuka, kontrol gerakan (WASD), serangan (J), dash (Spasi), dan skill **dibekukan total** (`velocity = (0,0)`).
- **Exclusive Single Active Panel (`ui.py`)**:
  - Membuka satu panel UI otomatis menutup panel lain. Hanya 1 panel aktif di layar (mencegah tab overlapping).
- **Character Sheet UI (`'C'`)**:
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
cd /Users/yohanes29/Documents/python-playground/games/rpg
python3 -m py_compile *.py
# Output: ALL rpg modules compiled 100% clean!
```

---

## 📌 5. Panduan Melanjutkan di Sesi Chat Baru

Bagi AI Agent / Developer yang menerima sesi chat baru:

1. **Baca Berkas Ini (`handover.md`)** dan [update_logs.md](file:///Users/yohanes29/Documents/python-playground/games/rpg/update_logs.md) untuk melihat histori perubahan terkini.
2. **Aturan Penting Pengembangan**:
   - Selalu biarkan pengguna (*User*) melakukan `git commit` sendiri.
   - Jangan menambahkan dependency berat eksternal (sistem dirancang 100% offline & deterministik).
   - Selalu uji dengan `python3 -m py_compile *.py` setelah mengedit kode.
   - Catat setiap penambahan fitur / bug fix baru ke dalam berkas `update_logs.md` dengan format timestamp `[yyyy-mm-dd hh:mm:ss WIB]`.
