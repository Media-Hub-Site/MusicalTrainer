"""
core/music_theory.py
────────────────────
Motor musicológico y pedagógico completo para MediaHub-MusicalTrainer.
Incluye:
  - Representación diatónica y cromática de notas (NoteSpec) con cálculo exacto de posición
    en pentagrama para 4 claves (Sol, Fa, Do en 3ª Alto, Do en 4ª Tenor y Gran Pentagrama).
  - Nomenclatura triple: Solfeo Latino (Do, Re, Mi...), Cifrado Americano (C, D, E...) y Dual.
  - Generadores de ejercicios para las 6 disciplinas clásicas:
      1. Lectura de Partitura (Note Trainer) con modo adaptativo inteligente
      2. Armaduras y Tonalidades (Key Signature Trainer + Círculo de Quintas)
      3. Intervalos en Partitura (Interval Trainer con canciones de referencia)
      4. Tríadas y Acordes con Inversiones (Triad & 7th Chord Trainer)
      5. Diapasón de Guitarra y Teclado (Fretboard & Keyboard Trainer)
      6. Entrenamiento Auditivo (Ear Trainer: Intervalos, Acordes y Escalas)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


LETTERS: tuple[str, ...] = ("C", "D", "E", "F", "G", "A", "B")

NATURAL_SEMITONES: dict[str, int] = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

SOLFEGE_ES: dict[str, str] = {
    "C": "Do",
    "D": "Re",
    "E": "Mi",
    "F": "Fa",
    "G": "Sol",
    "A": "La",
    "B": "Si",
}

# Paso diatónico de la primera línea inferior (Línea 1) de cada clave:
# diatonic_step = octave * 7 + LETTERS.index(letter)
CLEF_BOTTOM_LINE_STEP: dict[str, int] = {
    "treble": 4 * 7 + 2,  # E4 = 30 (Clave de Sol en 2ª)
    "bass":   2 * 7 + 4,  # G2 = 18 (Clave de Fa en 4ª)
    "alto":   3 * 7 + 3,  # F3 = 24 (Clave de Do en 3ª - C4 en línea central)
    "tenor":  3 * 7 + 1,  # D3 = 22 (Clave de Do en 4ª - C4 en cuarta línea)
}

# Posiciones de armaduras (offsets respecto a la línea 1 inferior de cada clave)
# Orden de sostenidos: F, C, G, D, A, E, B
# Orden de bemoles:    B, E, A, D, G, C, F
KEY_SIG_OFFSETS: dict[str, dict[str, list[int]]] = {
    "treble": {
        "sharps": [8, 5, 9, 6, 3, 7, 4],
        "flats":  [4, 7, 3, 6, 2, 5, 1],
    },
    "bass": {
        "sharps": [6, 3, 7, 4, 1, 5, 2],
        "flats":  [2, 5, 1, 4, 0, 3, -1],
    },
    "alto": {
        "sharps": [7, 4, 8, 5, 2, 6, 3],
        "flats":  [3, 6, 2, 5, 1, 4, 0],
    },
    "tenor": {
        "sharps": [2, 6, 3, 7, 4, 8, 5],
        "flats":  [5, 8, 4, 7, 3, 6, 2],
    },
}

# Afinación estándar de guitarra de 6 cuerdas (1ª aguda -> 6ª grave)
GUITAR_OPEN_STRINGS: list[tuple[int, str, int, int]] = [
    # (string_number, label, open_midi, base_octave)
    (1, "1ª (Mi4 / E4)", 64, 4),
    (2, "2ª (Si3 / B3)", 59, 3),
    (3, "3ª (Sol3 / G3)", 55, 3),
    (4, "4ª (Re3 / D3)", 50, 3),
    (5, "5ª (La2 / A2)", 45, 2),
    (6, "6ª (Mi2 / E2)", 40, 2),
]

# Mapa cromático desde pitch_class (0..11) hacia (letter, accidental)
CHROMATIC_SHARP_SPELLING: dict[int, tuple[str, int]] = {
    0: ("C", 0),
    1: ("C", 1),
    2: ("D", 0),
    3: ("D", 1),
    4: ("E", 0),
    5: ("F", 0),
    6: ("F", 1),
    7: ("G", 0),
    8: ("G", 1),
    9: ("A", 0),
    10: ("A", 1),
    11: ("B", 0),
}

CHROMATIC_FLAT_SPELLING: dict[int, tuple[str, int]] = {
    0: ("C", 0),
    1: ("D", -1),
    2: ("D", 0),
    3: ("E", -1),
    4: ("E", 0),
    5: ("F", 0),
    6: ("G", -1),
    7: ("G", 0),
    8: ("A", -1),
    9: ("A", 0),
    10: ("B", -1),
    11: ("B", 0),
}


@dataclass(frozen=True)
class NoteSpec:
    """Representa una nota musical con ortografía diatónica exacta."""
    letter: str       # 'C'..'B'
    octave: int       # 2..6
    accidental: int = 0  # -1 (bemol), 0 (natural), +1 (sostenido)

    @property
    def diatonic_step(self) -> int:
        return self.octave * 7 + LETTERS.index(self.letter)

    @property
    def midi(self) -> int:
        return 12 * (self.octave + 1) + NATURAL_SEMITONES[self.letter] + self.accidental

    @property
    def pitch_class(self) -> int:
        return self.midi % 12

    @property
    def freq_hz(self) -> float:
        return 440.0 * (2.0 ** ((self.midi - 69.0) / 12.0))

    @property
    def accidental_symbol(self) -> str:
        if self.accidental > 0:
            return "♯"
        if self.accidental < 0:
            return "♭"
        return ""

    @property
    def pitch_id(self) -> str:
        """Identificador de clase de altura normalizado (0..11) para validar enarmonías."""
        return f"pc_{self.pitch_class}"

    @property
    def spelling_id(self) -> str:
        return f"{self.letter}{self.accidental_symbol}"

    def staff_offset(self, clef: str = "treble") -> int:
        """
        Devuelve el desplazamiento en pasos diatónicos desde la Línea 1 (inferior) de la clave.
        0 = Línea 1, 1 = Espacio 1, 2 = Línea 2 ... 8 = Línea 5 (superior).
        Pares fuera de [0..8] requieren líneas adicionales (ledger lines).
        """
        base = CLEF_BOTTOM_LINE_STEP.get(clef, CLEF_BOTTOM_LINE_STEP["treble"])
        return self.diatonic_step - base

    def format_name(self, notation: str = "dual", include_octave: bool = False) -> str:
        """
        Formatea el nombre de la nota según el sistema preferido:
        - 'solfege': 'Do♯', 'Sol', 'Mi♭'
        - 'cipher':  'C♯', 'G', 'E♭'
        - 'dual':    'Do♯ · C♯'
        """
        sol = f"{SOLFEGE_ES[self.letter]}{self.accidental_symbol}"
        cip = f"{self.letter}{self.accidental_symbol}"
        oct_str = str(self.octave) if include_octave else ""
        if notation == "solfege":
            return f"{sol}{oct_str}"
        if notation == "cipher":
            return f"{cip}{oct_str}"
        if include_octave:
            return f"{sol}{oct_str} ({cip}{oct_str})"
        return f"{sol} · {cip}"


def midi_to_note_spec(midi_note: int, prefer_flats: bool = False) -> NoteSpec:
    """Convierte un valor MIDI (ej. 60) en un NoteSpec bien escrito."""
    pc = midi_note % 12
    octave = (midi_note // 12) - 1
    table = CHROMATIC_FLAT_SPELLING if prefer_flats else CHROMATIC_SHARP_SPELLING
    letter, acc = table[pc]
    return NoteSpec(letter=letter, octave=octave, accidental=acc)


def format_pitch_class(pc: int, notation: str = "dual", prefer_flats: bool = False) -> str:
    """Formatea una clase de altura (0..11) en el sistema de notación activo."""
    table = CHROMATIC_FLAT_SPELLING if prefer_flats else CHROMATIC_SHARP_SPELLING
    letter, acc = table[pc % 12]
    dummy = NoteSpec(letter=letter, octave=4, accidental=acc)
    return dummy.format_name(notation=notation, include_octave=False)


def get_clef_guide_notes(clef: str, notation: str = "dual") -> dict[str, list[tuple[int, str]]]:
    """
    Devuelve las notas guía de las 5 líneas y 4 espacios de la clave indicada
    para mostrar en los rieles pedagógicos del pentagrama.
    """
    if clef == "grand":
        clef = "treble"
    base_step = CLEF_BOTTOM_LINE_STEP.get(clef, 30)
    lines: list[tuple[int, str]] = []
    spaces: list[tuple[int, str]] = []
    for offset in range(9):
        step = base_step + offset
        octv = step // 7
        letter = LETTERS[step % 7]
        ns = NoteSpec(letter=letter, octave=octv, accidental=0)
        label = ns.format_name(notation=notation, include_octave=True)
        if offset % 2 == 0:
            lines.append((offset, label))
        else:
            spaces.append((offset, label))
    return {"lines": lines, "spaces": spaces}


# ─────────────────────────────────────────────────────────────────────────────
#  Catálogo de Tonalidades / Armaduras (Círculo de Quintas)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class KeySignatureInfo:
    fifths: int            # -7 (7 bemoles) .. 0 .. +7 (7 sostenidos)
    major_cipher: str
    major_solfege: str
    minor_cipher: str
    minor_solfege: str
    accidental_list_es: str
    accidental_list_en: str
    mnemonic_es: str
    mnemonic_en: str
    root_midi: int


CIRCLE_OF_FIFTHS: list[KeySignatureInfo] = [
    KeySignatureInfo(
        0, "C Major", "Do Mayor", "A Minor", "La Menor",
        "Sin alteraciones (0)", "No sharps or flats (0)",
        "Tonalidad natural pura: todas las teclas blancas del piano.",
        "Pure natural key: all white keys on the piano.",
        60,
    ),
    KeySignatureInfo(
        1, "G Major", "Sol Mayor", "E Minor", "Mi Menor",
        "1 Sostenido: Fa♯", "1 Sharp: F♯",
        "Regla del ♯: El último sostenido (Fa♯) es la sensible; sube 1 semitono → Sol Mayor.",
        "Sharp rule: The last sharp (F♯) is the leading tone; go up 1 semitone → G Major.",
        67,
    ),
    KeySignatureInfo(
        2, "D Major", "Re Mayor", "B Minor", "Si Menor",
        "2 Sostenidos: Fa♯, Do♯", "2 Sharps: F♯, C♯",
        "Último sostenido: Do♯ (+1 semitono = Re Mayor). Relativa menor: Si Menor.",
        "Last sharp: C♯ (+1 semitone = D Major). Relative minor: B Minor.",
        62,
    ),
    KeySignatureInfo(
        3, "A Major", "La Mayor", "F♯ Minor", "Fa♯ Menor",
        "3 Sostenidos: Fa♯, Do♯, Sol♯", "3 Sharps: F♯, C♯, G♯",
        "Último sostenido: Sol♯ (+1 semitono = La Mayor). Relativa menor: Fa♯ Menor.",
        "Last sharp: G♯ (+1 semitone = A Major). Relative minor: F♯ Minor.",
        69,
    ),
    KeySignatureInfo(
        4, "E Major", "Mi Mayor", "C♯ Minor", "Do♯ Menor",
        "4 Sostenidos: Fa♯, Do♯, Sol♯, Re♯", "4 Sharps: F♯, C♯, G♯, D♯",
        "Último sostenido: Re♯ (+1 semitono = Mi Mayor). Relativa menor: Do♯ Menor.",
        "Last sharp: D♯ (+1 semitone = E Major). Relative minor: C♯ Minor.",
        64,
    ),
    KeySignatureInfo(
        5, "B Major", "Si Mayor", "G♯ Minor", "Sol♯ Menor",
        "5 Sostenidos: Fa♯, Do♯, Sol♯, Re♯, La♯", "5 Sharps: F♯, C♯, G♯, D♯, A♯",
        "Último sostenido: La♯ (+1 semitono = Si Mayor).",
        "Last sharp: A♯ (+1 semitone = B Major).",
        71,
    ),
    KeySignatureInfo(
        6, "F♯ Major", "Fa♯ Mayor", "D♯ Minor", "Re♯ Menor",
        "6 Sostenidos: Fa♯, Do♯, Sol♯, Re♯, La♯, Mi♯", "6 Sharps: F♯, C♯, G♯, D♯, A♯, E♯",
        "Último sostenido: Mi♯ (=Fa natural) + 1 semitono → Fa♯ Mayor.",
        "Last sharp: E♯ + 1 semitone → F♯ Major.",
        66,
    ),
    KeySignatureInfo(
        -1, "F Major", "Fa Mayor", "D Minor", "Re Menor",
        "1 Bemol: Si♭", "1 Flat: B♭",
        "Con 1 solo bemol (Si♭), la tonalidad es Fa Mayor (y su relativa Re Menor).",
        "With a single flat (B♭), the key is F Major (and relative D Minor).",
        65,
    ),
    KeySignatureInfo(
        -2, "B♭ Major", "Si♭ Mayor", "G Minor", "Sol Menor",
        "2 Bemoles: Si♭, Mi♭", "2 Flats: B♭, E♭",
        "Regla del ♭: El penúltimo bemol da el nombre de la tonalidad Mayor → Si♭ Mayor.",
        "Flat rule: The second-to-last flat names the Major key → B♭ Major.",
        70,
    ),
    KeySignatureInfo(
        -3, "E♭ Major", "Mi♭ Mayor", "C Minor", "Do Menor",
        "3 Bemoles: Si♭, Mi♭, La♭", "3 Flats: B♭, E♭, A♭",
        "Penúltimo bemol: Mi♭ → Mi♭ Mayor (Relativa menor: Do Menor).",
        "Second-to-last flat: E♭ → E♭ Major (Relative minor: C Minor).",
        63,
    ),
    KeySignatureInfo(
        -4, "A♭ Major", "La♭ Mayor", "F Minor", "Fa Menor",
        "4 Bemoles: Si♭, Mi♭, La♭, Re♭", "4 Flats: B♭, E♭, A♭, D♭",
        "Penúltimo bemol: La♭ → La♭ Mayor (Relativa menor: Fa Menor).",
        "Second-to-last flat: A♭ → A♭ Major (Relative minor: F Minor).",
        68,
    ),
    KeySignatureInfo(
        -5, "D♭ Major", "Re♭ Mayor", "B♭ Minor", "Si♭ Menor",
        "5 Bemoles: Si♭, Mi♭, La♭, Re♭, Sol♭", "5 Flats: B♭, E♭, A♭, D♭, G♭",
        "Penúltimo bemol: Re♭ → Re♭ Mayor (Relativa menor: Si♭ Menor).",
        "Second-to-last flat: D♭ → D♭ Major (Relative minor: B♭ Minor).",
        61,
    ),
    KeySignatureInfo(
        -6, "G♭ Major", "Sol♭ Mayor", "E♭ Minor", "Mi♭ Menor",
        "6 Bemoles: Si♭, Mi♭, La♭, Re♭, Sol♭, Do♭", "6 Flats: B♭, E♭, A♭, D♭, G♭, C♭",
        "Penúltimo bemol: Sol♭ → Sol♭ Mayor (Enarmónico de Fa♯ Mayor).",
        "Second-to-last flat: G♭ → G♭ Major (Enharmonic to F♯ Major).",
        66,
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
#  Catálogo de Intervalos, Acordes y Escalas
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class IntervalSpec:
    semitones: int
    diatonic_steps: int
    code: str
    name_es: str
    name_en: str
    song_es: str
    song_en: str
    basic_group: str  # '2ª', '3ª', '4ª', '5ª', '6ª', '7ª', '8ª'


INTERVAL_CATALOG: list[IntervalSpec] = [
    IntervalSpec(1, 1, "m2", "2ª Menor (1 st)", "Minor 2nd (1 st)", "Tema de Tiburón (Jaws)", "Jaws Theme", "2ª"),
    IntervalSpec(2, 1, "M2", "2ª Mayor (2 st)", "Major 2nd (2 st)", "Cumpleaños Feliz (inicio)", "Happy Birthday", "2ª"),
    IntervalSpec(3, 2, "m3", "3ª Menor (3 st)", "Minor 3rd (3 st)", "Canción de Cuna (Brahms) / Smoke on the Water", "Brahms Lullaby / Greensleeves", "3ª"),
    IntervalSpec(4, 2, "M3", "3ª Mayor (4 st)", "Major 3rd (4 st)", "Oh When the Saints / Primavera de Vivaldi", "Oh When the Saints", "3ª"),
    IntervalSpec(5, 3, "P4", "4ª Justa (5 st)", "Perfect 4th (5 st)", "Marcha Nupcial / Himno de Hogwarts", "Here Comes the Bride / Amazing Grace", "4ª"),
    IntervalSpec(6, 3, "TT", "Tritono 4ªA/5ªd (6 st)", "Tritone A4/d5 (6 st)", "Los Simpson / Maria (West Side Story)", "The Simpsons / Maria", "4ª"),
    IntervalSpec(7, 4, "P5", "5ª Justa (7 st)", "Perfect 5th (7 st)", "Star Wars (Tema Principal) / Estrellita", "Star Wars Main Theme / Twinkle Twinkle", "5ª"),
    IntervalSpec(8, 5, "m6", "6ª Menor (8 st)", "Minor 6th (8 st)", "The Entertainer / Love Story", "The Entertainer / In My Life", "6ª"),
    IntervalSpec(9, 5, "M6", "6ª Mayor (9 st)", "Major 6th (9 st)", "My Way / Nocturno Op. 9 No. 2 (Chopin)", "My Way / NBC Chime", "6ª"),
    IntervalSpec(10, 6, "m7", "7ª Menor (10 st)", "Minor 7th (10 st)", "Tema original de Star Trek / Winner Takes It All", "Star Trek Original Theme", "7ª"),
    IntervalSpec(11, 6, "M7", "7ª Mayor (11 st)", "Major 7th (11 st)", "Take On Me (coro) / Pure Imagination", "Take On Me (chorus)", "7ª"),
    IntervalSpec(12, 7, "P8", "8ª Justa (12 st)", "Perfect Octave (12 st)", "Somewhere Over the Rainbow", "Somewhere Over the Rainbow", "8ª"),
]


@dataclass(frozen=True)
class ChordQualitySpec:
    code: str
    name_es: str
    name_en: str
    intervals: tuple[int, ...]
    diatonic_steps: tuple[int, ...]
    formula: str
    character_es: str
    character_en: str
    is_seventh: bool = False


CHORD_CATALOG: list[ChordQualitySpec] = [
    ChordQualitySpec(
        "maj", "Tríada Mayor", "Major Triad", (0, 4, 7), (0, 2, 4), "1 - 3 - 5",
        "Luminoso, estable, consonante y resolutivo (3ªM + 5ªJ).",
        "Bright, stable, consonant and resolved (M3 + P5).",
    ),
    ChordQualitySpec(
        "min", "Tríada Menor", "Minor Triad", (0, 3, 7), (0, 2, 4), "1 - ♭3 - 5",
        "Melancólico, expresivo, íntimo y lírico (3ªm + 5ªJ).",
        "Melancholic, expressive, lyrical and warm (m3 + P5).",
    ),
    ChordQualitySpec(
        "dim", "Tríada Disminuida", "Diminished Triad", (0, 3, 6), (0, 2, 4), "1 - ♭3 - ♭5",
        "Tenso, dramático e inestable por su tritono interno (dos 3ªm superpuestas).",
        "Tense, dramatic and unstable due to its internal tritone (two stacked m3).",
    ),
    ChordQualitySpec(
        "aug", "Tríada Aumentada", "Augmented Triad", (0, 4, 8), (0, 2, 4), "1 - 3 - ♯5",
        "Onírico, flotante y simétrico (dos 3ªM superpuestas).",
        "Dreamy, floating and symmetrical (two stacked M3).",
    ),
    ChordQualitySpec(
        "sus4", "Acorde Sus4", "Suspended 4th (Sus4)", (0, 5, 7), (0, 3, 4), "1 - 4 - 5",
        "Abierto y suspendido; reemplaza la 3ª por una 4ª Justa pidiendo resolver.",
        "Open and suspended; replaces the 3rd with a Perfect 4th craving resolution.",
    ),
    ChordQualitySpec(
        "maj7", "Acorde Maj7 (Séptima Mayor)", "Major 7th (Maj7)", (0, 4, 7, 11), (0, 2, 4, 6), "1 - 3 - 5 - 7",
        "Sofisticado, jazzístico, cálido y nostálgico.",
        "Sophisticated, jazzy, lush and nostalgic.",
        is_seventh=True,
    ),
    ChordQualitySpec(
        "m7", "Acorde m7 (Menor Séptima)", "Minor 7th (m7)", (0, 3, 7, 10), (0, 2, 4, 6), "1 - ♭3 - 5 - ♭7",
        "Suave, urbano y aterciopelado, pilar del Jazz y Soul.",
        "Smooth, urban and velvety, cornerstone of Jazz and Soul.",
        is_seventh=True,
    ),
    ChordQualitySpec(
        "dom7", "Acorde 7 (Dominante)", "Dominant 7th (7)", (0, 4, 7, 10), (0, 2, 4, 6), "1 - 3 - 5 - ♭7",
        "Enérgico y con fuerte atracción hacia la tónica; esencial en Blues y Clásico.",
        "Energetic with strong pull toward the tonic; essential in Blues and Classical.",
        is_seventh=True,
    ),
]


@dataclass(frozen=True)
class ScaleSpec:
    code: str
    name_es: str
    name_en: str
    semitones: tuple[int, ...]
    formula: str
    mood_es: str
    mood_en: str


SCALE_CATALOG: list[ScaleSpec] = [
    ScaleSpec(
        "major", "Escala Mayor (Jónica)", "Major Scale (Ionian)",
        (0, 2, 4, 5, 7, 9, 11, 12), "T - T - S - T - T - T - S",
        "Brillante, clara y equilibrada; base de la armonía tonal occidental.",
        "Bright, clear and balanced; foundation of Western tonal harmony.",
    ),
    ScaleSpec(
        "natural_minor", "Menor Natural (Eólica)", "Natural Minor (Aeolian)",
        (0, 2, 3, 5, 7, 8, 10, 12), "T - S - T - T - S - T - T",
        "Nostálgica, noble y emotiva (3ª, 6ª y 7ª menores).",
        "Nostalgic, noble and emotive (minor 3rd, 6th and 7th).",
    ),
    ScaleSpec(
        "harmonic_minor", "Menor Armónica", "Harmonic Minor",
        (0, 2, 3, 5, 7, 8, 11, 12), "T - S - T - T - S - 1½T - S",
        "Exótica, dramática y neoclásica por la 2ª aumentada entre ♭6 y 7 sensible.",
        "Exotic, dramatic and neoclassical due to the augmented 2nd between ♭6 and 7.",
    ),
    ScaleSpec(
        "dorian", "Modo Dórico", "Dorian Mode",
        (0, 2, 3, 5, 7, 9, 10, 12), "1 - 2 - ♭3 - 4 - 5 - 6 - ♭7",
        "Menor con 6ª Mayor luminosa; sonido característico de Jazz, Funk y Celta.",
        "Minor with a bright Major 6th; signature sound of Jazz, Funk and Celtic music.",
    ),
    ScaleSpec(
        "mixolydian", "Modo Mixolidio", "Mixolydian Mode",
        (0, 2, 4, 5, 7, 9, 10, 12), "1 - 2 - 3 - 4 - 5 - 6 - ♭7",
        "Mayor con 7ª menor (♭7); espíritu de Rock Clásico, Blues y Folk.",
        "Major with a minor 7th (♭7); classic Rock, Blues and Folk spirit.",
    ),
    ScaleSpec(
        "pent_major", "Pentatónica Mayor", "Major Pentatonic",
        (0, 2, 4, 7, 9, 12), "1 - 2 - 3 - 5 - 6",
        "Cinco notas sin semitonos; pastoral, alegre y universal.",
        "Five notes without semitones; pastoral, joyful and universal.",
    ),
    ScaleSpec(
        "pent_minor", "Pentatónica Menor", "Minor Pentatonic",
        (0, 3, 5, 7, 10, 12), "1 - ♭3 - 4 - 5 - ♭7",
        "Directa, expresiva y poderosa; lenguaje universal de la guitarra.",
        "Direct, expressive and powerful; universal guitar vocabulary.",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
#  Estructura Unificada de Ejercicio / Pregunta
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TrainerQuestion:
    mode: str                                  # 'notes' | 'keys' | 'intervals' | 'chords' | 'fretboard' | 'ear'
    clef: str                                  # 'treble' | 'bass' | 'alto' | 'tenor' | 'grand'
    notes: list[NoteSpec]                      # Notas en el pentagrama
    key_sig: int = 0                           # -7..+7 (armadura a mostrar)
    prompt_es: str = ""
    prompt_en: str = ""
    choices: list[tuple[str, str]] = field(default_factory=list)  # [(choice_id, label), ...]
    correct_id: str = ""
    correct_display: str = ""
    hint_es: str = ""
    hint_en: str = ""
    theory_detail_es: str = ""
    theory_detail_en: str = ""
    fret_target: tuple[int, int] | None = None  # (string 1..6, fret 0..12)
    hide_notes_until_answered: bool = False
    playback_type: str = "single"              # 'single' | 'interval_asc' | 'interval_desc' | 'interval_harm' | 'chord' | 'scale'
    inversion_label_es: str = ""
    inversion_label_en: str = ""


class ConservatoryCurriculumEngine:
    """
    Generador de ejercicios adaptativos para las 6 disciplinas de MusicalTrainer.
    Registra aciertos, errores por nota/elemento, tiempos de respuesta y rachas.
    """

    def __init__(self) -> None:
        self.notation: str = "dual"          # 'solfege' | 'cipher' | 'dual'
        self.clef: str = "treble"            # 'treble' | 'bass' | 'alto' | 'tenor' | 'grand'
        self.level: int = 1                  # 1 (Básico), 2 (Intermedio), 3 (Avanzado/Conservatorio)
        self.adaptive_mode: bool = True      # Prioriza elementos con más fallos
        self.ear_submode: str = "intervals"  # 'intervals' | 'chords' | 'scales'
        self.ear_play_style: str = "melodic_asc"  # 'melodic_asc' | 'melodic_desc' | 'harmonic'
        self.include_inversions: bool = False

        # Estadísticas de la sesión
        self.total_answered: int = 0
        self.total_correct: int = 0
        self.current_streak: int = 0
        self.best_streak: int = 0
        self.response_times_ms: list[int] = []
        self.missed_weights: dict[str, int] = {}
        self.history_log: list[dict[str, str]] = []
        self._last_question_sig: str = ""

    def reset_stats(self) -> None:
        self.total_answered = 0
        self.total_correct = 0
        self.current_streak = 0
        self.best_streak = 0
        self.response_times_ms.clear()
        self.missed_weights.clear()
        self.history_log.clear()

    @property
    def accuracy_pct(self) -> float:
        if self.total_answered == 0:
            return 100.0
        return (self.total_correct / self.total_answered) * 100.0

    @property
    def avg_response_ms(self) -> int:
        if not self.response_times_ms:
            return 0
        return int(sum(self.response_times_ms) / len(self.response_times_ms))

    def record_attempt(self, question: TrainerQuestion, chosen_id: str, elapsed_ms: int) -> bool:
        """Registra la respuesta del estudiante y actualiza los pesos adaptativos."""
        is_ok = (chosen_id == question.correct_id)
        self.total_answered += 1
        if elapsed_ms > 0:
            self.response_times_ms.append(min(elapsed_ms, 30000))

        key = question.correct_display or question.correct_id
        if is_ok:
            self.total_correct += 1
            self.current_streak += 1
            if self.current_streak > self.best_streak:
                self.best_streak = self.current_streak
            if key in self.missed_weights and self.missed_weights[key] > 0:
                self.missed_weights[key] -= 1
        else:
            self.current_streak = 0
            self.missed_weights[key] = self.missed_weights.get(key, 0) + 2

        self.history_log.append({
            "mode": question.mode,
            "target": question.correct_display,
            "result": "OK" if is_ok else "MISS",
            "ms": str(elapsed_ms),
        })
        return is_ok

    def get_weakest_items(self, limit: int = 4) -> list[tuple[str, int]]:
        items = [(k, v) for k, v in self.missed_weights.items() if v > 0]
        items.sort(key=lambda x: x[1], reverse=True)
        return items[:limit]

    # ─────────────────────────────────────────────────────────────────────────
    #  Generación de Preguntas por Modo
    # ─────────────────────────────────────────────────────────────────────────

    def generate_question(self, mode: str) -> TrainerQuestion:
        for _ in range(8):
            if mode == "notes":
                q = self._gen_note_question()
            elif mode == "keys":
                q = self._gen_key_signature_question()
            elif mode == "intervals":
                q = self._gen_interval_question()
            elif mode == "chords":
                q = self._gen_chord_question()
            elif mode == "fretboard":
                q = self._gen_fretboard_question()
            elif mode == "ear":
                q = self._gen_ear_question()
            else:
                q = self._gen_note_question()

            sig = f"{q.mode}:{q.clef}:{q.correct_id}:{[n.midi for n in q.notes]}"
            if sig != self._last_question_sig:
                self._last_question_sig = sig
                return q
        return q

    def _resolve_active_clef(self) -> str:
        if self.clef == "grand":
            return random.choice(["treble", "bass"])
        return self.clef

    def _gen_note_question(self) -> TrainerQuestion:
        active_clef = self._resolve_active_clef()
        base_step = CLEF_BOTTOM_LINE_STEP[active_clef]

        if self.level == 1:
            # Nivel 1: Dentro de las 5 líneas y 4 espacios (offsets 0..8), solo naturales
            min_off, max_off = 0, 8
            allowed_acc = [0]
        elif self.level == 2:
            # Nivel 2: Hasta 2 líneas adicionales abajo/arriba (offsets -4..12), naturales
            min_off, max_off = -4, 12
            allowed_acc = [0]
        else:
            # Nivel 3: Líneas adicionales extendidas + Sostenidos y Bemoles
            min_off, max_off = -4, 12
            allowed_acc = [-1, 0, 0, 1]

        candidates: list[NoteSpec] = []
        weights: list[float] = []
        for off in range(min_off, max_off + 1):
            step = base_step + off
            octv = step // 7
            letter = LETTERS[step % 7]
            for acc in allowed_acc:
                ns = NoteSpec(letter=letter, octave=octv, accidental=acc)
                if 36 <= ns.midi <= 84:
                    candidates.append(ns)
                    disp = ns.format_name(self.notation, include_octave=False)
                    w = 1.0 + (self.missed_weights.get(disp, 0) * 1.8 if self.adaptive_mode else 0.0)
                    weights.append(w)

        target = random.choices(candidates, weights=weights, k=1)[0]
        offset = target.staff_offset(active_clef)

        # Construir botones de respuesta claros
        choices: list[tuple[str, str]] = []
        if self.level < 3 or target.accidental == 0:
            # 7 notas naturales en orden Do..Si
            for let in LETTERS:
                n_opt = NoteSpec(letter=let, octave=4, accidental=0)
                cid = n_opt.pitch_id
                lbl = n_opt.format_name(self.notation, include_octave=False)
                choices.append((cid, lbl))
            # Si estamos en nivel 3, añadir también alteradas cercanas para mayor reto
            if self.level == 3:
                choices.clear()
                for pc in range(12):
                    prefer_fl = (target.accidental < 0)
                    lbl = format_pitch_class(pc, self.notation, prefer_flats=prefer_fl)
                    choices.append((f"pc_{pc}", lbl))
        else:
            prefer_fl = (target.accidental < 0)
            for pc in range(12):
                lbl = format_pitch_class(pc, self.notation, prefer_flats=prefer_fl)
                choices.append((f"pc_{pc}", lbl))

        # Explicación pedagógica de la posición en el pentagrama
        if offset < 0:
            pos_es = f"{abs(offset) // 2}ª línea/espacio adicional inferior"
            pos_en = f"Ledger position {offset} below staff"
        elif offset > 8:
            pos_es = f"{(offset - 8 + 1) // 2}ª línea/espacio adicional superior"
            pos_en = f"Ledger position +{offset - 8} above staff"
        elif offset % 2 == 0:
            line_num = (offset // 2) + 1
            pos_es = f"{line_num}ª línea del pentagrama"
            pos_en = f"Line {line_num} of the staff"
        else:
            sp_num = (offset // 2) + 1
            pos_es = f"{sp_num}º espacio del pentagrama"
            pos_en = f"Space {sp_num} of the staff"

        clef_names_es = {
            "treble": "Clave de Sol (2ª línea = Sol4)",
            "bass": "Clave de Fa (4ª línea = Fa3)",
            "alto": "Clave de Do en 3ª (Línea central = Do4)",
            "tenor": "Clave de Do en 4ª (4ª línea = Do4)",
        }
        clef_names_en = {
            "treble": "Treble Clef (Line 2 = G4)",
            "bass": "Bass Clef (Line 4 = F3)",
            "alto": "Alto Clef (Middle line 3 = C4)",
            "tenor": "Tenor Clef (Line 4 = C4)",
        }

        disp_no_oct = target.format_name(self.notation, include_octave=False)
        disp_full = target.format_name(self.notation, include_octave=True)

        return TrainerQuestion(
            mode="notes",
            clef="grand" if self.clef == "grand" else active_clef,
            notes=[target],
            key_sig=0,
            prompt_es="Identifica la nota en la partitura (o tócala en el piano inferior):",
            prompt_en="Identify the note on the staff (or play it on the piano below):",
            choices=choices,
            correct_id=target.pitch_id,
            correct_display=disp_no_oct,
            hint_es=f"Pista: {clef_names_es[active_clef]} • Ubicada en la {pos_es}.",
            hint_en=f"Hint: {clef_names_en[active_clef]} • Located on {pos_en}.",
            theory_detail_es=f"{disp_full} • {pos_es} • Frecuencia: {target.freq_hz:.1f} Hz (MIDI {target.midi})",
            theory_detail_en=f"{disp_full} • {pos_en} • Frequency: {target.freq_hz:.1f} Hz (MIDI {target.midi})",
            playback_type="single",
        )

    def _gen_key_signature_question(self) -> TrainerQuestion:
        active_clef = self._resolve_active_clef()
        if self.level == 1:
            pool = [k for k in CIRCLE_OF_FIFTHS if abs(k.fifths) <= 3]
        elif self.level == 2:
            pool = [k for k in CIRCLE_OF_FIFTHS if abs(k.fifths) <= 5]
        else:
            pool = list(CIRCLE_OF_FIFTHS)

        ask_minor = (self.level >= 2 and random.random() < 0.38)
        target_key = random.choice(pool)

        def _fmt_key(k: KeySignatureInfo, minor: bool) -> str:
            if minor:
                if self.notation == "solfege":
                    return k.minor_solfege
                if self.notation == "cipher":
                    return k.minor_cipher
                return f"{k.minor_solfege} ({k.minor_cipher})"
            else:
                if self.notation == "solfege":
                    return k.major_solfege
                if self.notation == "cipher":
                    return k.major_cipher
                return f"{k.major_solfege} ({k.major_cipher})"

        correct_id = f"key_{target_key.fifths}_{'min' if ask_minor else 'maj'}"
        correct_label = _fmt_key(target_key, ask_minor)

        # Seleccionar 5 distractores + la correcta, ordenados por quintas
        others = [k for k in pool if k.fifths != target_key.fifths]
        sampled = random.sample(others, k=min(5, len(others))) + [target_key]
        sampled.sort(key=lambda x: x.fifths)

        choices = [
            (f"key_{k.fifths}_{'min' if ask_minor else 'maj'}", _fmt_key(k, ask_minor))
            for k in sampled
        ]

        # Acorde tónico de referencia para que suene la tonalidad al preguntar/responder
        root_m = target_key.root_midi - (3 if ask_minor else 0)
        third_m = root_m + (3 if ask_minor else 4)
        fifth_m = root_m + 7
        prefer_fl = target_key.fifths < 0
        tonic_notes = [
            midi_to_note_spec(root_m, prefer_fl),
            midi_to_note_spec(third_m, prefer_fl),
            midi_to_note_spec(fifth_m, prefer_fl),
        ]

        mode_str_es = "Tonalidad MENOR Relativa" if ask_minor else "Tonalidad MAYOR"
        mode_str_en = "Relative MINOR Key" if ask_minor else "MAJOR Key"

        return TrainerQuestion(
            mode="keys",
            clef=active_clef,
            notes=tonic_notes,
            key_sig=target_key.fifths,
            prompt_es=f"¿A qué {mode_str_es} corresponde esta armadura de clave?",
            prompt_en=f"Which {mode_str_en} corresponds to this key signature?",
            choices=choices,
            correct_id=correct_id,
            correct_display=correct_label,
            hint_es=f"{target_key.accidental_list_es} • {target_key.mnemonic_es}",
            hint_en=f"{target_key.accidental_list_en} • {target_key.mnemonic_en}",
            theory_detail_es=f"{target_key.major_solfege} / {target_key.minor_solfege} • {target_key.accidental_list_es} • {target_key.mnemonic_es}",
            theory_detail_en=f"{target_key.major_cipher} / {target_key.minor_cipher} • {target_key.accidental_list_en} • {target_key.mnemonic_en}",
            playback_type="chord",
        )

    def _gen_interval_question(self) -> TrainerQuestion:
        active_clef = self._resolve_active_clef()
        base_step = CLEF_BOTTOM_LINE_STEP[active_clef]

        if self.level == 1:
            # Intervalos consonantes/principales
            pool = [i for i in INTERVAL_CATALOG if i.code in ("M2", "m3", "M3", "P4", "P5", "P8")]
        elif self.level == 2:
            pool = [i for i in INTERVAL_CATALOG if i.code != "TT"]
        else:
            pool = list(INTERVAL_CATALOG)

        target_iv = random.choice(pool)

        # Nota base cómoda dentro del pentagrama inferior/medio
        low_off = random.randint(0, 4)
        low_step = base_step + low_off
        low_note = NoteSpec(
            letter=LETTERS[low_step % 7],
            octave=low_step // 7,
            accidental=0,
        )

        # Calcular segunda nota con el número exacto de pasos diatónicos cuando sea posible
        high_step = low_step + target_iv.diatonic_steps
        high_letter = LETTERS[high_step % 7]
        high_oct = high_step // 7
        natural_high = NoteSpec(letter=high_letter, octave=high_oct, accidental=0)
        diff_semi = (low_note.midi + target_iv.semitones) - natural_high.midi
        if -1 <= diff_semi <= 1:
            high_note = NoteSpec(letter=high_letter, octave=high_oct, accidental=diff_semi)
        else:
            high_note = midi_to_note_spec(low_note.midi + target_iv.semitones, prefer_flats=(diff_semi < 0))

        choices = [
            (iv.code, iv.name_es if self.notation != "cipher" else iv.name_en)
            for iv in pool
        ]

        n1_str = low_note.format_name(self.notation, include_octave=True)
        n2_str = high_note.format_name(self.notation, include_octave=True)

        return TrainerQuestion(
            mode="intervals",
            clef=active_clef,
            notes=[low_note, high_note],
            key_sig=0,
            prompt_es=f"Identifica el intervalo entre {n1_str} y {n2_str}:",
            prompt_en=f"Identify the interval between {n1_str} and {n2_str}:",
            choices=choices,
            correct_id=target_iv.code,
            correct_display=target_iv.name_es,
            hint_es=f"Distancia: {target_iv.semitones} semitonos ({target_iv.basic_group}) • Referencia auditiva: «{target_iv.song_es}».",
            hint_en=f"Distance: {target_iv.semitones} semitones ({target_iv.basic_group}) • Ear reference: '{target_iv.song_en}'.",
            theory_detail_es=f"{target_iv.name_es} ({n1_str} → {n2_str}) • Canción guía: «{target_iv.song_es}»",
            theory_detail_en=f"{target_iv.name_en} ({n1_str} → {n2_str}) • Song anchor: '{target_iv.song_en}'",
            playback_type="interval_asc",
        )

    def _gen_chord_question(self) -> TrainerQuestion:
        active_clef = self._resolve_active_clef()
        base_step = CLEF_BOTTOM_LINE_STEP[active_clef]

        if self.level == 1:
            pool = [c for c in CHORD_CATALOG if c.code in ("maj", "min", "dim", "aug")]
        elif self.level == 2:
            pool = [c for c in CHORD_CATALOG if not c.is_seventh] + [
                c for c in CHORD_CATALOG if c.code in ("maj7", "m7", "dom7")
            ]
        else:
            pool = list(CHORD_CATALOG)

        target_chord = random.choice(pool)
        root_off = random.randint(0, 3)
        root_step = base_step + root_off
        root_note = NoteSpec(
            letter=LETTERS[root_step % 7],
            octave=root_step // 7,
            accidental=0,
        )

        # Construir las notas del acorde respetando las terceras diatónicas
        chord_notes: list[NoteSpec] = []
        for semi, d_step in zip(target_chord.intervals, target_chord.diatonic_steps):
            st = root_step + d_step
            let = LETTERS[st % 7]
            octv = st // 7
            nat = NoteSpec(letter=let, octave=octv, accidental=0)
            acc = (root_note.midi + semi) - nat.midi
            if -1 <= acc <= 1:
                chord_notes.append(NoteSpec(letter=let, octave=octv, accidental=acc))
            else:
                chord_notes.append(midi_to_note_spec(root_note.midi + semi, prefer_flats=(acc < 0)))

        inv_es = "Estado Fundamental"
        inv_en = "Root Position"
        if self.include_inversions or self.level == 3:
            inv_choice = random.choice([0, 0, 1, 2])
            if inv_choice == 1 and len(chord_notes) >= 3:
                n0 = chord_notes[0]
                chord_notes = chord_notes[1:] + [NoteSpec(n0.letter, n0.octave + 1, n0.accidental)]
                inv_es = "1ª Inversión (3ª en el bajo)"
                inv_en = "1st Inversion (3rd in bass)"
            elif inv_choice == 2 and len(chord_notes) >= 3:
                n0, n1 = chord_notes[0], chord_notes[1]
                chord_notes = chord_notes[2:] + [
                    NoteSpec(n0.letter, n0.octave + 1, n0.accidental),
                    NoteSpec(n1.letter, n1.octave + 1, n1.accidental),
                ]
                inv_es = "2ª Inversión (5ª en el bajo)"
                inv_en = "2nd Inversion (5th in bass)"

        root_label = root_note.format_name(self.notation, include_octave=False)
        choices = [
            (c.code, f"{c.name_es} ({c.formula})")
            for c in pool
        ]

        notes_joined = " - ".join(n.format_name(self.notation, include_octave=False) for n in chord_notes)

        return TrainerQuestion(
            mode="chords",
            clef=active_clef,
            notes=chord_notes,
            key_sig=0,
            prompt_es=f"Identifica la cualidad del acorde sobre {root_label} ({inv_es}):",
            prompt_en=f"Identify the chord quality built on {root_label} ({inv_en}):",
            choices=choices,
            correct_id=target_chord.code,
            correct_display=f"{root_label} {target_chord.name_es}",
            hint_es=f"Fórmula: {target_chord.formula} • Notas: {notes_joined} • {target_chord.character_es}",
            hint_en=f"Formula: {target_chord.formula} • Notes: {notes_joined} • {target_chord.character_en}",
            theory_detail_es=f"{root_label} {target_chord.name_es} ({inv_es}) • Notas: {notes_joined} • {target_chord.character_es}",
            theory_detail_en=f"{root_label} {target_chord.name_en} ({inv_en}) • Notes: {notes_joined} • {target_chord.character_en}",
            playback_type="chord",
            inversion_label_es=inv_es,
            inversion_label_en=inv_en,
        )

    def _gen_fretboard_question(self) -> TrainerQuestion:
        max_fret = 5 if self.level == 1 else (9 if self.level == 2 else 12)
        allow_acc = (self.level >= 2)

        valid_positions: list[tuple[int, int, NoteSpec, str]] = []
        for s_num, s_label, open_midi, _ in GUITAR_OPEN_STRINGS:
            for fret in range(0, max_fret + 1):
                m = open_midi + fret
                ns = midi_to_note_spec(m, prefer_flats=False)
                if not allow_acc and ns.accidental != 0:
                    continue
                valid_positions.append((s_num, fret, ns, s_label))

        s_num, fret, target_note, s_label = random.choice(valid_positions)
        clef_for_note = "treble" if target_note.midi >= 55 else "bass"

        choices: list[tuple[str, str]] = []
        if not allow_acc:
            for let in LETTERS:
                n_opt = NoteSpec(letter=let, octave=4, accidental=0)
                choices.append((n_opt.pitch_id, n_opt.format_name(self.notation, include_octave=False)))
        else:
            for pc in range(12):
                choices.append((f"pc_{pc}", format_pitch_class(pc, self.notation, prefer_flats=False)))

        disp_name = target_note.format_name(self.notation, include_octave=False)
        disp_full = target_note.format_name(self.notation, include_octave=True)

        return TrainerQuestion(
            mode="fretboard",
            clef=clef_for_note,
            notes=[target_note],
            key_sig=0,
            prompt_es=f"Diapasón: ¿Qué nota suena en la cuerda {s_label}, traste {fret}?",
            prompt_en=f"Fretboard: Which note sounds on string {s_label}, fret {fret}?",
            choices=choices,
            correct_id=target_note.pitch_id,
            correct_display=disp_name,
            hint_es=f"Cuerda al aire: {s_label} + {fret} semitono(s) = {disp_full}.",
            hint_en=f"Open string: {s_label} + {fret} semitone(s) = {disp_full}.",
            theory_detail_es=f"Cuerda {s_num} • Traste {fret} → {disp_full} ({target_note.freq_hz:.1f} Hz)",
            theory_detail_en=f"String {s_num} • Fret {fret} → {disp_full} ({target_note.freq_hz:.1f} Hz)",
            fret_target=(s_num, fret),
            playback_type="single",
        )

    def _gen_ear_question(self) -> TrainerQuestion:
        if self.ear_submode == "chords":
            q = self._gen_chord_question()
            q.mode = "ear"
            q.hide_notes_until_answered = True
            q.prompt_es = "👂 Entrenamiento Auditivo (Acordes): Escucha la sonoridad e identifica el acorde:"
            q.prompt_en = "👂 Ear Training (Chords): Listen to the voicing and identify the chord quality:"
            return q

        if self.ear_submode == "scales":
            pool = SCALE_CATALOG[:4] if self.level == 1 else list(SCALE_CATALOG)
            target_sc = random.choice(pool)
            root_midi = random.choice([60, 62, 64, 65, 67, 69])
            root_ns = midi_to_note_spec(root_midi)
            scale_notes = [midi_to_note_spec(root_midi + semi) for semi in target_sc.semitones]

            choices = [(sc.code, f"{sc.name_es}") for sc in pool]
            root_lbl = root_ns.format_name(self.notation, include_octave=False)

            return TrainerQuestion(
                mode="ear",
                clef="treble",
                notes=scale_notes,
                key_sig=0,
                prompt_es=f"👂 Entrenamiento Auditivo (Escalas sobre {root_lbl}): Escucha e identifica la escala o modo:",
                prompt_en=f"👂 Ear Training (Scales on {root_lbl}): Listen and identify the scale or mode:",
                choices=choices,
                correct_id=target_sc.code,
                correct_display=target_sc.name_es,
                hint_es=f"Estructura: {target_sc.formula} • Carácter: {target_sc.mood_es}",
                hint_en=f"Structure: {target_sc.formula} • Character: {target_sc.mood_en}",
                theory_detail_es=f"{target_sc.name_es} sobre {root_lbl} ({target_sc.formula}) • {target_sc.mood_es}",
                theory_detail_en=f"{target_sc.name_en} on {root_lbl} ({target_sc.formula}) • {target_sc.mood_en}",
                hide_notes_until_answered=True,
                playback_type="scale",
            )

        # Default: Intervalos auditivos
        q = self._gen_interval_question()
        q.mode = "ear"
        q.hide_notes_until_answered = True
        if self.ear_play_style == "harmonic":
            q.playback_type = "interval_harm"
        elif self.ear_play_style == "melodic_desc":
            q.playback_type = "interval_desc"
        else:
            q.playback_type = "interval_asc"
        q.prompt_es = "👂 Entrenamiento Auditivo (Intervalos): Escucha la distancia y reconoce el intervalo:"
        q.prompt_en = "👂 Ear Training (Intervals): Listen to the distance and identify the interval:"
        return q
