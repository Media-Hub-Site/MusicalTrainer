"""
core/audio_engine.py
────────────────────
Motor de síntesis acústica polifónica en tiempo real para MusicalTrainer.
Genera ondas WAV PCM estéreo de 16 bits con tres timbres de conservatorio:
  1. 'piano'  — Piano de Cola Steinway (armónicos inarmónicos, ataque de martillo y caja de resonancia).
  2. 'rhodes' — Piano Eléctrico Vintage (campana FM suave + chorus cálido).
  3. 'guitar' — Guitarra / Arpa de Concierto (cuerda pulsada con resonancia de madera).
Incluye caché en directorio temporal y reproducción asíncrona no bloqueante.
"""

from __future__ import annotations

import hashlib
import math
import os
import struct
import tempfile
import threading
import wave
from typing import Sequence


def midi_to_freq(midi_note: int) -> float:
    """Convierte un número de nota MIDI (ej. 69 = A4) a frecuencia en Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69.0) / 12.0))


class ConservatoryAudioEngine:
    """Sintetizador polifónico ligero sin dependencias externas pesadas."""

    SAMPLE_RATE = 22050

    def __init__(self) -> None:
        self.enabled: bool = True
        self.timbre: str = "piano"  # 'piano' | 'rhodes' | 'guitar'
        self.volume: float = 0.78
        self._cache_dir = os.path.join(tempfile.gettempdir(), "mediahub_musicaltrainer_audio")
        os.makedirs(self._cache_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _voice_sample(self, freq: float, t: float, dur: float, timbre: str) -> tuple[float, float]:
        """Calcula una muestra estéreo (L, R) para una nota a frecuencia `freq` en instante `t`."""
        if t < 0.0 or t > dur:
            return 0.0, 0.0

        two_pi_f = 2.0 * math.pi * freq

        if timbre == "rhodes":
            attack = min(1.0, t / 0.006)
            decay = math.exp(-2.1 * t)
            bell = math.exp(-14.0 * t) * 0.42 * math.sin(two_pi_f * 7.0 * t)
            mod = 0.35 * math.exp(-4.5 * t) * math.sin(two_pi_f * 2.0 * t)
            core = math.sin(two_pi_f * t + mod) + 0.22 * math.sin(two_pi_f * 3.0 * t)
            trem_l = 1.0 + 0.08 * math.sin(2.0 * math.pi * 4.2 * t)
            trem_r = 1.0 - 0.08 * math.sin(2.0 * math.pi * 4.2 * t)
            tail = max(0.0, min(1.0, (dur - t) / 0.04))
            val = attack * decay * tail * (core + bell)
            return val * trem_l, val * trem_r

        if timbre == "guitar":
            attack = min(1.0, t / 0.003)
            tail = max(0.0, min(1.0, (dur - t) / 0.035))
            s = (
                1.00 * math.exp(-2.6 * t) * math.sin(two_pi_f * t)
                + 0.58 * math.exp(-4.2 * t) * math.sin(two_pi_f * 2.0 * t + 0.3)
                + 0.34 * math.exp(-6.5 * t) * math.sin(two_pi_f * 3.0 * t + 0.7)
                + 0.18 * math.exp(-9.5 * t) * math.sin(two_pi_f * 4.0 * t)
                + 0.10 * math.exp(-15.0 * t) * math.sin(two_pi_f * 5.0 * t)
            )
            pluck = 0.16 * math.exp(-38.0 * t) * math.sin(two_pi_f * 8.5 * t)
            val = attack * tail * (s + pluck) * 0.72
            return val * 1.03, val * 0.97

        # Default: 'piano' (Concert Grand Piano)
        attack = min(1.0, t / 0.005)
        tail = max(0.0, min(1.0, (dur - t) / 0.045))
        # Inharmonicity stretch factor typical of piano strings
        b = 0.00018
        s_l = 0.0
        s_r = 0.0
        weights = (1.00, 0.52, 0.28, 0.15, 0.09, 0.05)
        decays = (1.85, 2.65, 3.60, 4.90, 6.50, 8.40)
        for n, (w, d) in enumerate(zip(weights, decays), start=1):
            fn = freq * n * math.sqrt(1.0 + b * (n * n))
            if fn >= self.SAMPLE_RATE * 0.46:
                break
            env_n = math.exp(-d * t)
            # Subtle stereo piano soundboard spread
            phase_l = 2.0 * math.pi * fn * t
            phase_r = 2.0 * math.pi * (fn * 1.0004) * t + (0.15 * n)
            s_l += w * env_n * math.sin(phase_l)
            s_r += w * env_n * math.sin(phase_r)

        # Hammer felt transient
        hammer = 0.14 * math.exp(-55.0 * t) * (
            math.sin(two_pi_f * 6.2 * t) + 0.5 * math.sin(two_pi_f * 9.3 * t)
        )
        scale = attack * tail * 0.68
        return (s_l + hammer) * scale, (s_r + hammer) * scale

    def _render_events_to_wav(
        self,
        events: Sequence[tuple[int, float, float]],
        timbre: str | None = None,
    ) -> str:
        """
        Renderiza una lista de eventos `(midi_note, start_sec, duration_sec)` a un archivo WAV
        en caché y devuelve su ruta.
        """
        use_timbre = timbre or self.timbre
        sig = f"{use_timbre}|{self.volume:.2f}|" + ";".join(
            f"{m}:{s:.3f}:{d:.3f}" for m, s, d in events
        )
        digest = hashlib.md5(sig.encode("utf-8")).hexdigest()[:16]
        wav_path = os.path.join(self._cache_dir, f"mt_{digest}.wav")
        if os.path.isfile(wav_path):
            return wav_path

        sr = self.SAMPLE_RATE
        total_dur = max((s + d for _, s, d in events), default=0.4) + 0.04
        num_samples = max(1, int(total_dur * sr))

        buf_l = [0.0] * num_samples
        buf_r = [0.0] * num_samples

        for midi_note, start_s, dur_s in events:
            freq = midi_to_freq(midi_note)
            idx_start = max(0, int(start_s * sr))
            idx_end = min(num_samples, int((start_s + dur_s) * sr))
            for i in range(idx_start, idx_end):
                local_t = (i - idx_start) / sr
                vl, vr = self._voice_sample(freq, local_t, dur_s, use_timbre)
                buf_l[i] += vl
                buf_r[i] += vr

        # Normalización suave para evitar clipping en acordes de 3-4 notas
        peak = max(
            max((abs(x) for x in buf_l), default=0.0),
            max((abs(x) for x in buf_r), default=0.0),
            1.0,
        )
        gain = (30000.0 * self.volume) / peak

        frames = bytearray(num_samples * 4)
        pack_into = struct.pack_into
        for i in range(num_samples):
            sl = int(max(-32767.0, min(32767.0, buf_l[i] * gain)))
            sr_val = int(max(-32767.0, min(32767.0, buf_r[i] * gain)))
            pack_into("<hh", frames, i * 4, sl, sr_val)

        with self._lock:
            if not os.path.isfile(wav_path):
                with wave.open(wav_path, "wb") as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(frames)

        return wav_path

    def _play_wav_async(self, wav_path: str) -> None:
        if not self.enabled or not wav_path or not os.path.isfile(wav_path):
            return

        def _worker() -> None:
            try:
                import winsound
                winsound.PlaySound(
                    wav_path,
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def play_note(self, midi_note: int, duration: float = 0.85) -> None:
        """Reproduce una única nota MIDI."""
        if not self.enabled:
            return
        wav_path = self._render_events_to_wav([(midi_note, 0.0, duration)])
        self._play_wav_async(wav_path)

    def play_chord(
        self,
        midi_notes: Sequence[int],
        duration: float = 1.15,
        arpeggiate: bool = True,
        arp_step: float = 0.065,
    ) -> None:
        """Reproduce un acorde (simultáneo o con arpegio suave de conservatorio)."""
        if not self.enabled or not midi_notes:
            return
        events: list[tuple[int, float, float]] = []
        for idx, m in enumerate(midi_notes):
            delay = (idx * arp_step) if arpeggiate else 0.0
            events.append((int(m), delay, duration))
        wav_path = self._render_events_to_wav(events)
        self._play_wav_async(wav_path)

    def play_sequence(
        self,
        midi_notes: Sequence[int],
        step_delay: float = 0.34,
        note_duration: float = 0.52,
    ) -> None:
        """Reproduce una secuencia melódica (intervalos melódicos o escalas completas)."""
        if not self.enabled or not midi_notes:
            return
        events: list[tuple[int, float, float]] = []
        for idx, m in enumerate(midi_notes):
            events.append((int(m), idx * step_delay, note_duration))
        wav_path = self._render_events_to_wav(events)
        self._play_wav_async(wav_path)

    def play_interval(
        self,
        midi_low: int,
        midi_high: int,
        mode: str = "melodic_asc",
    ) -> None:
        """
        Reproduce un intervalo en uno de tres modos:
        - 'melodic_asc': nota grave -> nota aguda -> ambas juntas suaves
        - 'melodic_desc': nota aguda -> nota grave -> ambas juntas suaves
        - 'harmonic': ambas notas simultáneas
        """
        if not self.enabled:
            return
        if mode == "harmonic":
            events = [(midi_low, 0.0, 1.15), (midi_high, 0.0, 1.15)]
        elif mode == "melodic_desc":
            events = [
                (midi_high, 0.0, 0.48),
                (midi_low, 0.42, 0.52),
                (midi_low, 0.96, 0.85),
                (midi_high, 0.96, 0.85),
            ]
        else:
            events = [
                (midi_low, 0.0, 0.48),
                (midi_high, 0.42, 0.52),
                (midi_low, 0.96, 0.85),
                (midi_high, 0.96, 0.85),
            ]
        wav_path = self._render_events_to_wav(events)
        self._play_wav_async(wav_path)

    def play_error_cue(self) -> None:
        """Pequeño toque grave sutil cuando se falla una respuesta."""
        if not self.enabled:
            return
        events = [(48, 0.0, 0.16), (47, 0.11, 0.22)]
        wav_path = self._render_events_to_wav(events, timbre="rhodes")
        self._play_wav_async(wav_path)

    def play_metronome_click(self, accent: bool = False) -> None:
        """Pulso acústico tipo metrónomo mecánico Wittner (bloque de madera)."""
        if not self.enabled:
            return
        wav_name = "metro_hi.wav" if accent else "metro_lo.wav"
        wav_path = os.path.join(self._cache_dir, wav_name)
        if not os.path.isfile(wav_path):
            sr = self.SAMPLE_RATE
            dur = 0.045
            n = int(sr * dur)
            f0 = 1180.0 if accent else 820.0
            frames = bytearray(n * 4)
            for i in range(n):
                t = i / sr
                env = math.exp(-75.0 * t)
                val = env * (
                    math.sin(2.0 * math.pi * f0 * t)
                    + 0.45 * math.sin(2.0 * math.pi * (f0 * 1.58) * t)
                )
                s = int(max(-32767, min(32767, val * 22000 * self.volume)))
                struct.pack_into("<hh", frames, i * 4, s, s)
            with self._lock:
                if not os.path.isfile(wav_path):
                    with wave.open(wav_path, "wb") as wf:
                        wf.setnchannels(2)
                        wf.setsampwidth(2)
                        wf.setframerate(sr)
                        wf.writeframes(frames)
        self._play_wav_async(wav_path)
