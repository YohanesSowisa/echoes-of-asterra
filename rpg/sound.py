"""
Echoes of Asterra - Procedural Sound & Music Synthesizer
Generates rich, multi-layered adaptive background music and sound effects at runtime.
Uses 2-channel stereo interleaved 16-bit PCM synthesis with ADSR envelopes, modular presets,
phase-offset stereo width (zero frequency beating), soft-limiting headroom compression,
equal-power boundary crossfading, band-limited square wave harmonics, and hash-based noise.
Requires zero external audio assets or dependencies.
"""
import io
import math
import struct
import wave
import os
import logging
from typing import Dict, Union, Callable, Tuple, List

import pygame

logger = logging.getLogger("SoundManager")

# Cache Versioning Constant (Increments trigger automatic audio re-synthesis on startup)
ASSET_VERSION = "v2"


# =============================================================================
# SYNTHESIS BUILDING BLOCKS & DSP PRIMITIVES
# =============================================================================

def hash_noise(t_note: float) -> float:
    """Deterministic integer hash-based white noise (eliminates aliased sinusoidal noise tones)."""
    n = int(t_note * 96000.0) & 0x7fffffff
    n = (n << 13) ^ n
    n = (n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff
    return (n / 1073741824.0) - 1.0


def band_limited_square(t: float, freq: float, samplerate: int = 44100, max_harmonics: int = 6) -> float:
    """Fourier band-limited square wave synthesis preventing harmonic foldback & aliasing."""
    nyquist = samplerate * 0.5
    val = 0.0
    n = 1
    harmonics_used = 0
    while n * freq < nyquist and harmonics_used < max_harmonics:
        val += math.sin(2.0 * math.pi * freq * n * t) / n
        n += 2
        harmonics_used += 1
    if harmonics_used == 0:
        return math.sin(2.0 * math.pi * freq * t)
    return val * (4.0 / math.pi)



def adsr(t_note: float, duration: float, attack: float = 0.02, decay: float = 0.08, sustain: float = 0.7, release: float = 0.08) -> float:
    """Calculates Attack-Decay-Sustain-Release envelope amplitude (0.0 to 1.0)."""
    if t_note < 0.0 or t_note > duration:
        return 0.0
    if t_note < attack:
        return t_note / max(0.0001, attack)
    elif t_note < attack + decay:
        decay_ratio = (t_note - attack) / max(0.0001, decay)
        return 1.0 - (1.0 - sustain) * decay_ratio
    elif t_note < duration - release:
        return sustain
    else:
        rel_ratio = (t_note - (duration - release)) / max(0.0001, release)
        return max(0.0, sustain * (1.0 - rel_ratio))


def soft_limit(val: float, gain: float = 1.0) -> float:
    """Soft-knee tanh compression with linear headroom scaling (prevents pumping & clipping)."""
    return math.tanh(val * gain)


def stereo_pan(sample: float, pan: float = 0.0) -> Tuple[float, float]:
    """Pans a mono sample across stereo field (-1.0 = Left, 0.0 = Center, +1.0 = Right)."""
    pan = max(-1.0, min(1.0, pan))
    left = sample * (1.0 - pan) * 0.5
    right = sample * (1.0 + pan) * 0.5
    return (left, right)


def apply_equal_power_crossfade(samples: List[Tuple[float, float]], samplerate: int, crossfade_sec: float = 0.05) -> List[Tuple[float, float]]:
    """Applies equal-power crossfading (50ms) near track boundaries to eliminate clicks during infinite looping."""
    fade_len = int(samplerate * crossfade_sec)
    total_len = len(samples)
    if total_len <= fade_len * 2:
        return samples

    out = list(samples)
    for i in range(fade_len):
        t = i / fade_len
        w_in = math.sin(t * math.pi * 0.5)
        w_out = math.cos(t * math.pi * 0.5)

        start_idx = i
        end_idx = total_len - fade_len + i

        sl_l, sl_r = samples[start_idx]
        el_l, el_r = samples[end_idx]

        blended_l = sl_l * w_in + el_l * w_out
        blended_r = sl_r * w_in + el_r * w_out

        out[start_idx] = (blended_l, blended_r)
        out[end_idx] = (blended_l, blended_r)

    return out


# =============================================================================
# MODULAR SYNTHESIZER INSTRUMENT PRESETS
# =============================================================================

def synth_lute(t_note: float, duration: float, freq: float, pan: float = -0.15) -> Tuple[float, float]:
    """Plucked acoustic lute string (sine + warm 2nd harmonic + fast decay)."""
    env = adsr(t_note, duration, attack=0.005, decay=0.12, sustain=0.4, release=0.1)
    wave_val = math.sin(2.0 * math.pi * freq * t_note) * 0.7 + math.sin(2.0 * math.pi * freq * 2.0 * t_note) * 0.3
    return stereo_pan(wave_val * env, pan)


def synth_flute(t_note: float, duration: float, freq: float, pan: float = 0.15) -> Tuple[float, float]:
    """Woodwind flute lead (sine + 3rd harmonic + subtle delayed 0.5% vibrato)."""
    env = adsr(t_note, duration, attack=0.04, decay=0.1, sustain=0.8, release=0.12)
    # Tamed vibrato (0.5% depth, delayed onset) to eliminate wah-wah pitch wobble
    vib_amp = 0.005 if t_note > 0.15 else 0.002
    vibrato = 1.0 + vib_amp * math.sin(2.0 * math.pi * 4.5 * t_note)
    wave_val = math.sin(2.0 * math.pi * freq * vibrato * t_note) * 0.8 + math.sin(2.0 * math.pi * freq * 3.0 * t_note) * 0.15
    return stereo_pan(wave_val * env, pan)


def synth_pad(t_note: float, duration: float, freq: float, pan: float = 0.0) -> Tuple[float, float]:
    """Wide stereo ambient pad using fixed phase offset (ZERO frequency beating/wah-wah)."""
    env = adsr(t_note, duration, attack=0.3, decay=0.2, sustain=0.9, release=0.3)
    # Fixed 90-degree phase offset (math.pi / 2) creates wide stereo image without frequency beating over time
    l_wave = math.sin(2.0 * math.pi * freq * t_note) * 0.4
    r_wave = math.sin(2.0 * math.pi * freq * t_note + (math.pi / 2.0)) * 0.4
    left, right = stereo_pan(l_wave * env, pan - 0.15)
    r_left, r_right = stereo_pan(r_wave * env, pan + 0.15)
    return (left + r_left, right + r_right)


def synth_bell(t_note: float, duration: float, freq: float, pan: float = 0.25) -> Tuple[float, float]:
    """High crystalline bell (sine triad + exponential decay)."""
    env = adsr(t_note, duration, attack=0.002, decay=0.3, sustain=0.2, release=0.2)
    wave_val = (math.sin(2.0 * math.pi * freq * t_note) * 0.6 +
                math.sin(2.0 * math.pi * freq * 2.76 * t_note) * 0.25 +
                math.sin(2.0 * math.pi * freq * 5.4 * t_note) * 0.15)
    return stereo_pan(wave_val * env, pan)


def synth_bass(t_note: float, duration: float, freq: float, pan: float = 0.0) -> Tuple[float, float]:
    """Warm sub-bass (sine + triangle low-pass, centered panning)."""
    env = adsr(t_note, duration, attack=0.01, decay=0.08, sustain=0.85, release=0.08)
    sin_val = math.sin(2.0 * math.pi * freq * t_note)
    tri_val = (abs(sin_val) * 2.0 - 1.0)
    wave_val = sin_val * 0.7 + tri_val * 0.3
    return stereo_pan(wave_val * env, 0.0)  # Always centered for low end clarity


def synth_brushed_noise(t_note: float, duration: float, pan: float = 0.0) -> Tuple[float, float]:
    """Soft brushed noise burst for acoustic percussion rhythm using deterministic hash_noise."""
    env = math.exp(-35.0 * t_note) if t_note < duration else 0.0
    noise = hash_noise(t_note)
    return stereo_pan(noise * 0.15 * env, pan)


# =============================================================================
# SOUND MANAGER CLASS
# =============================================================================

class SoundManager:
    """
    Manages procedural sound effects and background music.
    Generates 2-channel stereo PCM WAV files in memory and caches them as Pygame Sound objects.
    """
    def __init__(self) -> None:
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music_channels: Dict[str, pygame.mixer.Channel] = {}
        self.current_music: Union[str, None] = None
        self.samplerate = 44100  # Upgraded to 44.1 kHz for wide Nyquist headroom (22.05 kHz)
        self.enabled = False
        self.music_volume = 1.0
        self.sfx_volume = 1.0

        # Initialize mixer in 2-channel 44.1 kHz stereo
        try:
            pygame.mixer.init(frequency=self.samplerate, size=-16, channels=2, buffer=1024)
            self.enabled = True
        except pygame.error as e:
            logger.warning("Sound: Failed to initialize stereo pygame mixer: %s. Audio disabled.", e)
            return

        if self.enabled:
            self._generate_all_assets()

    def _generate_wav(self, filename: str, wave_func: Callable[[float], Union[float, Tuple[float, float]]], duration: float, volume: float = 0.5) -> pygame.mixer.Sound:
        """
        Generates a 2-channel stereo WAV file on disk (or loads versioned cached version) and returns a Sound object.
        """
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ASSETS_DIR = os.path.join(BASE_DIR, "assets")

        subfolder = "music" if "music" in filename else "sounds"
        dest_folder = os.path.join(ASSETS_DIR, subfolder)
        os.makedirs(dest_folder, exist_ok=True)

        # Versioned cache path ensures updated synthesis logic automatically regenerates audio files
        file_path = os.path.join(dest_folder, f"{filename}_{ASSET_VERSION}.wav")

        # Fast versioned disk cache check: load existing WAV instantly without re-synthesizing
        if os.path.exists(file_path):
            try:
                return pygame.mixer.Sound(file_path)
            except Exception as e:
                logger.warning("Failed to load cached audio file '%s': %s. Re-synthesizing.", file_path, e)

        num_samples = int(duration * self.samplerate)
        raw_samples: List[Tuple[float, float]] = []

        # Generate stereo sample buffer
        for i in range(num_samples):
            t = i / self.samplerate
            val = wave_func(t)
            if isinstance(val, (tuple, list)):
                left_v, right_v = val[0], val[1]
            else:
                left_v, right_v = val, val
            raw_samples.append((left_v, right_v))

        # Apply short equal-power boundary crossfade (50ms) to eliminate clicks without phrase overlap
        if "music" in filename:
            raw_samples = apply_equal_power_crossfade(raw_samples, self.samplerate, crossfade_sec=0.05)

        # Write WAV binary stream
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(2)  # Stereo
            wav_file.setsampwidth(2)   # 16-bit
            wav_file.setframerate(self.samplerate)

            for left_v, right_v in raw_samples:
                # Apply 0.75x headroom scale pre-limiter to avoid compression pumping
                l_lim = soft_limit(left_v * 0.75, gain=1.0)
                r_lim = soft_limit(right_v * 0.75, gain=1.0)

                val_l = int(max(-1.0, min(1.0, l_lim)) * 32767 * volume)
                val_r = int(max(-1.0, min(1.0, r_lim)) * 32767 * volume)
                wav_file.writeframesraw(struct.pack('<hh', val_l, val_r))

        # Cache versioned WAV to disk
        try:
            with open(file_path, 'wb') as f:
                f.write(buffer.getvalue())
        except Exception as e:
            logger.warning("Failed to write audio cache file to %s: %s", file_path, e)

        buffer.seek(0)
        return pygame.mixer.Sound(buffer)

    def _generate_all_assets(self) -> None:
        """Generates all procedural sound effects and rich multi-phrase biome BGM loops."""

        # ---------------------------------------------------------------------
        # SOUND EFFECTS (SFX - Cleaned & Audit Verified)
        # ---------------------------------------------------------------------

        def ui_click_wave(t: float) -> Tuple[float, float]:
            val = math.sin(2.0 * math.pi * 1200 * t) * math.exp(-60.0 * t)
            return stereo_pan(val, 0.0)
        self.sounds["click"] = self._generate_wav("click", ui_click_wave, 0.1, 0.4)

        def footstep_wave(t: float) -> Tuple[float, float]:
            # Low ground pulse + clean soft brushed transient (zero radio static fuzz)
            thud = math.sin(2.0 * math.pi * 75.0 * t) * math.exp(-35.0 * t)
            l_brush, r_brush = synth_brushed_noise(t, 0.05, pan=-0.1)
            return (thud * 0.7 + l_brush * 0.3, thud * 0.7 + r_brush * 0.3)
        self.sounds["footstep"] = self._generate_wav("footstep", footstep_wave, 0.08, 0.15)

        def sword_wave(t: float) -> Tuple[float, float]:
            # Clean frequency sweep pitch drop (600Hz -> 200Hz) simulating blade whoosh
            freq = 600.0 - 400.0 * (t / 0.2)
            val = math.sin(2.0 * math.pi * freq * t) * math.exp(-14.0 * t)
            return stereo_pan(val, 0.1)
        self.sounds["sword"] = self._generate_wav("sword", sword_wave, 0.2, 0.5)

        def magic_wave(t: float) -> Tuple[float, float]:
            freq = 150.0 + 800.0 * (t / 0.3)
            val = (math.sin(2.0 * math.pi * freq * t) * 0.7 + math.sin(2.0 * math.pi * freq * 1.5 * t) * 0.3) * math.exp(-8.0 * t)
            return stereo_pan(val, -0.15)
        self.sounds["magic"] = self._generate_wav("magic", magic_wave, 0.3, 0.4)

        def hit_wave(t: float) -> Tuple[float, float]:
            # Clean sub impact thud (180Hz -> 50Hz pitch drop + fast decay)
            freq = 180.0 - 130.0 * (t / 0.15)
            val = math.sin(2.0 * math.pi * freq * t) * math.exp(-22.0 * t)
            return stereo_pan(val, 0.0)
        self.sounds["hit"] = self._generate_wav("hit", hit_wave, 0.15, 0.6)

        def heal_wave(t: float) -> Tuple[float, float]:
            notes = [261.63, 329.63, 392.00, 523.25]
            note_idx = min(int(t * 10), len(notes) - 1)
            freq = notes[note_idx]
            vibrato = 1.0 + 0.005 * math.sin(2.0 * math.pi * 6 * t)
            val = math.sin(2.0 * math.pi * freq * vibrato * t) * math.exp(-4.0 * t)
            return stereo_pan(val, 0.15)
        self.sounds["heal"] = self._generate_wav("heal", heal_wave, 0.4, 0.45)

        def levelup_wave(t: float) -> Tuple[float, float]:
            notes = [261.63, 329.63, 392.00, 523.25, 659.25, 783.99, 1046.50]
            note_idx = min(int(t * 8.5), len(notes) - 1)
            freq = notes[note_idx]
            sq_val = band_limited_square(t, freq, self.samplerate)
            val = sq_val * 0.4 * math.exp(-2.5 * t)
            return stereo_pan(val, 0.0)
        self.sounds["levelup"] = self._generate_wav("levelup", levelup_wave, 0.8, 0.4)

        def victory_wave(t: float) -> Tuple[float, float]:
            melody = [523.25, 659.25, 783.99, 1046.50, 783.99, 1046.50]
            idx = min(int(t * 4), len(melody) - 1)
            freq = melody[idx]
            lead = band_limited_square(t, freq, self.samplerate)
            bass = math.sin(2.0 * math.pi * (freq / 4.0) * t) * 0.5
            val = (lead * 0.4 + bass * 0.3) * math.exp(-1.0 * t)
            return stereo_pan(val, 0.0)
        self.sounds["victory"] = self._generate_wav("victory", victory_wave, 1.5, 0.4)

        def gameover_wave(t: float) -> Tuple[float, float]:
            melody = [440.00, 415.30, 392.00, 349.23, 329.63, 293.66]
            idx = min(int(t * 3.5), len(melody) - 1)
            freq = melody[idx]
            lead = math.sin(2.0 * math.pi * freq * t)
            harmony = math.sin(2.0 * math.pi * freq * 1.2 * t) * 0.3
            val = (lead * 0.5 + harmony) * math.exp(-0.8 * t)
            return stereo_pan(val, 0.0)
        self.sounds["gameover"] = self._generate_wav("gameover", gameover_wave, 1.8, 0.4)

        # Ambient Weather Procedural SFX
        def thunder_wave(t: float) -> Tuple[float, float]:
            freq = 45.0 - 20.0 * (t / 1.2)
            sub = math.sin(2.0 * math.pi * freq * t) * math.exp(-2.2 * t)
            noise = hash_noise(t) * math.exp(-3.0 * t) * 0.25
            val = (sub * 0.75 + noise) * adsr(t, 1.2, attack=0.04, decay=0.3, sustain=0.4, release=0.5)
            return stereo_pan(val, 0.0)
        self.sounds["thunder"] = self._generate_wav("thunder", thunder_wave, 1.2, 0.6)

        def wind_gust_wave(t: float) -> Tuple[float, float]:
            sweep = math.sin(math.pi * (t / 1.5))
            noise = hash_noise(t) * sweep * 0.35
            tone = math.sin(2.0 * math.pi * (140.0 + 80.0 * sweep) * t) * sweep * 0.15
            val = noise + tone
            return stereo_pan(val, 0.0)
        self.sounds["wind_gust"] = self._generate_wav("wind_gust", wind_gust_wave, 1.5, 0.35)

        def crickets_wave(t: float) -> Tuple[float, float]:
            chirp_pulse = math.sin(2.0 * math.pi * 14.0 * t)
            if chirp_pulse > 0.6:
                val = math.sin(2.0 * math.pi * 4200.0 * t) * 0.2 * math.exp(-12.0 * (t % 0.08))
            else:
                val = 0.0
            return stereo_pan(val, 0.2)
        self.sounds["crickets"] = self._generate_wav("crickets", crickets_wave, 1.0, 0.25)

        # ---------------------------------------------------------------------
        # BACKGROUND MUSIC LOOPS (16-Second Compositions, Zero Beating / Zero Noise)
        # ---------------------------------------------------------------------

        # 1. Village Music: Peaceful, Nostalgic, Warm Acoustic (16 seconds)
        def village_music_wave(t: float) -> Tuple[float, float]:
            chords = [
                {"root": 130.81, "pad": [261.63, 329.63, 392.00, 493.88]},   # Cmaj7
                {"root": 110.00, "pad": [220.00, 261.63, 329.63, 392.00]},   # Am9
                {"root": 87.31,  "pad": [174.61, 220.00, 261.63, 329.63]},   # Fmaj7
                {"root": 98.00,  "pad": [196.00, 293.66, 349.23, 440.00]}    # G11
            ]
            bar_idx = int(t / 4.0) % 4
            bar_t = t % 4.0
            chord = chords[bar_idx]

            # Voice 1: Warm Sub-Bass (Centered)
            bass_l, bass_r = synth_bass(bar_t, 4.0, chord["root"], pan=0.0)

            # Voice 2: Phase-Offset Ambient Pad (Zero Frequency Beating)
            pad_l, pad_r = 0.0, 0.0
            for note_f in chord["pad"]:
                pl, pr = synth_pad(bar_t, 4.0, note_f, pan=0.0)
                pad_l += pl * 0.12
                pad_r += pr * 0.12

            # Voice 3: Plucked Lute Arpeggio
            lute_l, lute_r = 0.0, 0.0
            lute_notes = chord["pad"]
            lute_step = int(bar_t * 4) % len(lute_notes)
            lute_note_t = bar_t % 0.25
            ll, lr = synth_lute(lute_note_t, 0.25, lute_notes[lute_step], pan=-0.2)
            lute_l += ll * 0.25
            lute_r += lr * 0.25

            # Voice 4: Woodwind Flute Lead Melody
            flute_l, flute_r = 0.0, 0.0
            flute_melody = [523.25, 659.25, 587.33, 493.88, 523.25, 659.25, 783.99, 659.25]
            flute_step = int(t * 1.5) % len(flute_melody)
            flute_note_t = t % 0.66
            fl_l, fl_r = synth_flute(flute_note_t, 0.66, flute_melody[flute_step], pan=0.2)
            flute_l += fl_l * 0.35
            flute_r += fl_r * 0.35

            # Voice 5: Soft Brushed Noise Rhythm (Static Volume)
            perc_l, perc_r = 0.0, 0.0
            if bar_t % 0.5 < 0.08:
                perc_l, perc_r = synth_brushed_noise(bar_t % 0.5, 0.08, pan=0.1)

            total_l = bass_l * 0.35 + pad_l + lute_l + flute_l + perc_l * 0.15
            total_r = bass_r * 0.35 + pad_r + lute_r + flute_r + perc_r * 0.15
            return (total_l, total_r)

        self.sounds["village_music"] = self._generate_wav("village_music", village_music_wave, 16.0, 0.35)

        # 2. Forest Music: Mysterious, Airy, Natural (16 seconds)
        def forest_music_wave(t: float) -> Tuple[float, float]:
            chords = [
                {"root": 110.00, "pad": [220.00, 277.18, 329.63, 392.00]},
                {"root": 87.31,  "pad": [174.61, 220.00, 261.63, 329.63]},
                {"root": 73.42,  "pad": [146.83, 220.00, 261.63, 349.23]},
                {"root": 82.41,  "pad": [164.81, 207.65, 246.94, 311.13]}
            ]
            bar_idx = int(t / 4.0) % 4
            bar_t = t % 4.0
            chord = chords[bar_idx]

            # Voice 1: Wood Sub-Bass (Centered)
            bass_l, bass_r = synth_bass(bar_t, 4.0, chord["root"], pan=0.0)

            # Voice 2: Phase-Offset Ambient Pad
            pad_l, pad_r = 0.0, 0.0
            for note_f in chord["pad"]:
                pl, pr = synth_pad(bar_t, 4.0, note_f, pan=0.0)
                pad_l += pl * 0.12
                pad_r += pr * 0.12

            # Voice 3: Plucked Acoustic Harp
            harp_l, harp_r = 0.0, 0.0
            harp_notes = chord["pad"]
            harp_step = int(bar_t * 3) % len(harp_notes)
            harp_note_t = bar_t % 0.33
            hl, hr = synth_lute(harp_note_t, 0.33, harp_notes[harp_step] * 1.5, pan=-0.25)
            harp_l += hl * 0.25
            harp_r += hr * 0.25

            # Voice 4: Woodwind Flute Lead
            flute_melody = [440.00, 523.25, 659.25, 587.33, 523.25, 440.00, 392.00, 440.00]
            flute_step = int(t * 1.25) % len(flute_melody)
            fl_l, fl_r = synth_flute(t % 0.8, 0.8, flute_melody[flute_step], pan=0.2)

            # Voice 5: Deep Warm Forest Atmosphere (Clean sub-harmonic sine tone, zero radio static fuzz)
            air_l, air_r = stereo_pan(math.sin(2.0 * math.pi * (chord["root"] / 2.0) * t) * 0.1, pan=0.0)

            total_l = bass_l * 0.35 + pad_l + harp_l + fl_l * 0.35 + air_l
            total_r = bass_r * 0.35 + pad_r + harp_r + fl_r * 0.35 + air_r
            return (total_l, total_r)

        self.sounds["forest_music"] = self._generate_wav("forest_music", forest_music_wave, 16.0, 0.35)

        # 3. Lake Music: Spacious, Shimmering, Reflective (16 seconds)
        def lake_music_wave(t: float) -> Tuple[float, float]:
            chords = [
                {"root": 130.81, "pad": [261.63, 329.63, 392.00, 493.88, 587.33]},
                {"root": 110.00, "pad": [220.00, 261.63, 329.63, 392.00, 587.33]},
                {"root": 87.31,  "pad": [174.61, 220.00, 261.63, 329.63, 392.00]},
                {"root": 98.00,  "pad": [196.00, 261.63, 293.66, 392.00, 523.25]}
            ]
            bar_idx = int(t / 4.0) % 4
            bar_t = t % 4.0
            chord = chords[bar_idx]

            # Voice 1: Deep Water Bass
            bass_l, bass_r = synth_bass(bar_t, 4.0, chord["root"], pan=0.0)

            # Voice 2: Phase-Offset Water Pad
            pad_l, pad_r = 0.0, 0.0
            for note_f in chord["pad"][:3]:
                pl, pr = synth_pad(bar_t, 4.0, note_f, pan=0.0)
                pad_l += pl * 0.15
                pad_r += pr * 0.15

            # Voice 3: Crystal Chime Bells
            bell_l, bell_r = 0.0, 0.0
            bell_notes = chord["pad"][2:]
            bell_step = int(bar_t * 2) % len(bell_notes)
            bell_t = bar_t % 0.5
            bl, br = synth_bell(bell_t, 0.5, bell_notes[bell_step], pan=0.25)
            bell_l += bl * 0.3
            bell_r += br * 0.3

            total_l = bass_l * 0.3 + pad_l + bell_l
            total_r = bass_r * 0.3 + pad_r + bell_r
            return (total_l, total_r)

        self.sounds["lake_music"] = self._generate_wav("lake_music", lake_music_wave, 16.0, 0.32)

        # 4. Dungeon Music: Oppressive, Dark, Suspenseful (16 seconds)
        def dungeon_music_wave(t: float) -> Tuple[float, float]:
            chords = [
                {"root": 73.42,  "pad": [146.83, 174.61, 220.00, 329.63]},
                {"root": 51.91,  "pad": [103.83, 146.83, 174.61, 246.94]},
                {"root": 58.27,  "pad": [116.54, 174.61, 220.00, 293.66]},
                {"root": 55.00,  "pad": [110.00, 164.81, 196.00, 293.66]}
            ]
            bar_idx = int(t / 4.0) % 4
            bar_t = t % 4.0
            chord = chords[bar_idx]

            # Voice 1: Low Sub-Bass Drone
            bass_l, bass_r = synth_bass(bar_t, 4.0, chord["root"], pan=0.0)

            # Voice 2: Phase-Offset Suspense Pad (Zero Beating)
            pulse_l, pulse_r = synth_pad(bar_t, 4.0, chord["root"] * 2.0, pan=-0.15)

            # Voice 3: Creepy Dissonant Bell Counterpoint
            bell_l, bell_r = 0.0, 0.0
            if int(bar_t * 2) % 2 == 1:
                bl, br = synth_bell(bar_t % 0.5, 0.5, chord["pad"][-1] * 1.414, pan=0.25)
                bell_l, bell_r = bl * 0.2, br * 0.2

            # Voice 4: Deep Dungeon Low Atmosphere Drone (Clean sub sine, zero fuzzy static)
            sub_drone_l, sub_drone_r = stereo_pan(math.sin(2.0 * math.pi * 41.2 * t) * 0.1, pan=0.0)

            total_l = bass_l * 0.4 + pulse_l * 0.25 + bell_l + sub_drone_l
            total_r = bass_r * 0.4 + pulse_r * 0.25 + bell_r + sub_drone_r
            return (total_l, total_r)

        self.sounds["dungeon_music"] = self._generate_wav("dungeon_music", dungeon_music_wave, 16.0, 0.38)

        # 5. Boss Music: Aggressive, Intense, Driving (16 seconds)
        def boss_music_wave(t: float) -> Tuple[float, float]:
            chords = [
                {"root": 82.41,  "lead": [329.63, 392.00, 493.88, 659.25]},
                {"root": 65.41,  "lead": [261.63, 329.63, 392.00, 523.25]},
                {"root": 73.42,  "lead": [293.66, 369.99, 440.00, 587.33]},
                {"root": 61.74,  "lead": [246.94, 311.13, 369.99, 493.88]}
            ]
            bar_idx = int(t / 4.0) % 4
            bar_t = t % 4.0
            chord = chords[bar_idx]

            # Voice 1: Driving 16th-Note Square Bass (Band-limited harmonics)
            bass_pulse = int(bar_t * 8) % 2
            bass_env = adsr(bar_t % 0.125, 0.125, attack=0.002, decay=0.04, sustain=0.6, release=0.02)
            bass_sq = band_limited_square(t, chord["root"], self.samplerate)
            bass_l, bass_r = stereo_pan(bass_sq * bass_env * bass_pulse * 0.35, pan=0.0)

            # Voice 2: Octave-Stacked Chiptune Lead Melody (Band-limited harmonics)
            lead_notes = chord["lead"]
            lead_idx = int(bar_t * 6) % len(lead_notes)
            lead_freq = lead_notes[lead_idx]
            lead_env = adsr(bar_t % 0.166, 0.166, attack=0.005, decay=0.05, sustain=0.7, release=0.04)
            lead_sq = band_limited_square(t, lead_freq, self.samplerate) * 0.3
            lead_l, lead_r = stereo_pan(lead_sq * lead_env, pan=0.15)

            # Voice 3: Accent Staccato Chords (Band-limited harmonics)
            accent_l, accent_r = 0.0, 0.0
            if int(bar_t * 4) % 2 == 1:
                acc_env = adsr(bar_t % 0.25, 0.25, attack=0.005, decay=0.08, sustain=0.3, release=0.05)
                acc_sq = band_limited_square(t, chord["lead"][1], self.samplerate) * 0.18
                accent_l, accent_r = stereo_pan(acc_sq * acc_env, pan=-0.2)

            # Voice 4: Soft High-Frequency Percussive Click
            hihat_l, hihat_r = synth_brushed_noise(bar_t % 0.25, 0.04, pan=0.05)

            total_l = bass_l + lead_l + accent_l + hihat_l * 0.5
            total_r = bass_r + lead_r + accent_r + hihat_r * 0.5
            return (total_l, total_r)

        self.sounds["boss_music"] = self._generate_wav("boss_music", boss_music_wave, 16.0, 0.4)

        # 0. Menu Music: Epic, Mysterious, Majestic Title Theme in D Minor (16 seconds)
        def menu_music_wave(t: float) -> Tuple[float, float]:
            # Epic Title Chords (4 bars x 4.0s = 16s): Dm9 -> Bbmaj7 -> Gm7/C -> A7alt
            chords = [
                {"root": 73.42,  "pad": [146.83, 174.61, 220.00, 261.63, 329.63]},  # Dm9
                {"root": 58.27,  "pad": [116.54, 174.61, 220.00, 293.66, 349.23]},  # Bbmaj7
                {"root": 65.41,  "pad": [130.81, 196.00, 233.08, 293.66, 349.23]},  # Gm7/C
                {"root": 55.00,  "pad": [110.00, 164.81, 196.00, 277.18, 349.23]}   # A7alt
            ]
            bar_idx = int(t / 4.0) % 4
            bar_t = t % 4.0
            chord = chords[bar_idx]

            # Voice 1: Deep Orchestral Sub-Bass Drone (Centered)
            bass_l, bass_r = synth_bass(bar_t, 4.0, chord["root"], pan=0.0)

            # Voice 2: Cathedral Choir / Ancient Ambient Pad
            pad_l, pad_r = 0.0, 0.0
            for note_f in chord["pad"][:4]:
                pl, pr = synth_pad(bar_t, 4.0, note_f, pan=0.0)
                pad_l += pl * 0.15
                pad_r += pr * 0.15

            # Voice 3: Shimmering Title Crystal Bells (Slow, solemn accent motif)
            bell_notes = [587.33, 698.46, 880.00, 783.99, 698.46, 587.33, 554.37, 587.33]
            bell_step = int(t * 0.5) % len(bell_notes)
            bell_note_t = t % 2.0
            bl, br = synth_bell(bell_note_t, 2.0, bell_notes[bell_step], pan=-0.2)

            # Voice 4: Solemn Low Flute Solo Melody (Slow epic phrasing)
            flute_melody = [293.66, 349.23, 440.00, 392.00, 349.23, 293.66, 277.18, 293.66]
            flute_step = int(t * 0.5) % len(flute_melody)
            fl_l, fl_r = synth_flute(t % 2.0, 2.0, flute_melody[flute_step], pan=0.25)

            # Voice 5: Low Atmosphere Sub Drone (41.2 Hz)
            drone_l, drone_r = stereo_pan(math.sin(2.0 * math.pi * 41.2 * t) * 0.08, pan=0.0)

            total_l = bass_l * 0.4 + pad_l + bl * 0.35 + fl_l * 0.3 + drone_l
            total_r = bass_r * 0.4 + pad_r + br * 0.35 + fl_r * 0.3 + drone_r
            return (total_l, total_r)

        self.sounds["menu_music"] = self._generate_wav("menu_music", menu_music_wave, 16.0, 0.35)

        # Priority Table
        self.music_priorities: Dict[str, int] = {
            "boss_music": 5,
            "combat_music": 4,
            "menu_music": 3,
            "dungeon_music": 2,
            "village_music": 2,
            "forest_music": 2,
            "lake_music": 2
        }

        self.music_playback_timer: float = 0.0
        self.music_cooldown_timer: float = 0.0
        self.min_track_duration: float = 10.0
        self.transition_cooldown: float = 3.0

    def update_timers(self, dt: float) -> None:
        """Updates music playback timers and transition cooldowns."""
        self.music_playback_timer += dt
        if self.music_cooldown_timer > 0.0:
            self.music_cooldown_timer = max(0.0, self.music_cooldown_timer - dt)

    def play_sound(self, name: str) -> None:
        """Plays a sound effect by name, applying the SFX volume."""
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.set_volume(self.sfx_volume)
            sound.play()

    def play_footstep(self, tile_type: str = "grass") -> None:
        """Plays tile-specific footstep sound variation (grass, dirt, stone, cave)."""
        if not self.enabled:
            return
        sfx_name = "footstep"
        if tile_type in ["stone", "cave"]:
            sfx_name = "click"
        self.play_sound(sfx_name)

    def play_music(self, name: str, force: bool = False) -> None:
        """
        Loops background music by name, respecting Priority Table & Transition Cooldowns.
        """
        if not self.enabled:
            return
        if self.current_music == name:
            return

        curr_prio = self.music_priorities.get(self.current_music or "", 0)
        new_prio = self.music_priorities.get(name, 0)

        # Enforce transition cooldowns for lower/equal priority switches unless forced or higher priority
        if not force and new_prio <= curr_prio:
            if self.music_playback_timer < self.min_track_duration or self.music_cooldown_timer > 0.0:
                return

        # Stop existing music
        if self.current_music:
            music_sound = self.sounds.get(self.current_music)
            if music_sound:
                music_sound.stop()

        self.current_music = name
        self.music_playback_timer = 0.0
        self.music_cooldown_timer = self.transition_cooldown

        music_sound = self.sounds.get(name)
        if music_sound:
            music_sound.set_volume(self.music_volume)
            music_sound.play(loops=-1)

    def stop_music(self) -> None:
        """Stops current background music."""
        if not self.enabled or not self.current_music:
            return
        music_sound = self.sounds.get(self.current_music)
        if music_sound:
            music_sound.stop()
        self.current_music = None

    def set_music_volume(self, val: float) -> None:
        """Sets the background music volume dynamically."""
        self.music_volume = max(0.0, min(1.0, val))
        if self.current_music:
            music_sound = self.sounds.get(self.current_music)
            if music_sound:
                music_sound.set_volume(self.music_volume)

    def set_sfx_volume(self, val: float) -> None:
        """Sets the sound effects volume."""
        self.sfx_volume = max(0.0, min(1.0, val))
