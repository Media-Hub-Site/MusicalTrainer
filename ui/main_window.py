"""
ui/main_window.py
─────────────────
Ventana principal de MediaHub-MusicalTrainer ("Conservatorio Interactivo & Laboratorio de Lectura").
Integra las 6 disciplinas clásicas del Music Trainer original más un Explorador Libre (Sandbox),
metrónomo acústico, rueda del Círculo de Quintas, modo Reto 60s y diagnóstico adaptativo.
"""

from __future__ import annotations

import os
import time
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.audio_engine import ConservatoryAudioEngine
from core.music_theory import (
    CHORD_CATALOG,
    ConservatoryCurriculumEngine,
    NoteSpec,
    SCALE_CATALOG,
    TrainerQuestion,
    midi_to_note_spec,
)
from ui.conservatory_theme import THEMES, build_conservatory_stylesheet
from ui.score_canvas import (
    CircleOfFifthsDialog,
    GuitarFretboardWidget,
    PianoKeyboardWidget,
    ScoreCanvasWidget,
    SessionReportDialog,
)


def _get_asset_path(rel_path: str) -> str:
    import sys
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)


class MusicalTrainerWindow(QMainWindow):
    """Estudio y Conservatorio Interactivo de Lectura de Partituras, Teoría y Oído Musical."""

    DISCIPLINES: list[tuple[str, str, str, str]] = [
        ("notes",     "Partitura (Notas)",     "Staff Sight-Reading"),
        ("keys",      "Armaduras",             "Key Signatures"),
        ("intervals", "Intervalos",            "Intervals"),
        ("chords",    "Tríadas y Acordes",     "Triads & Chords"),
        ("fretboard", "Diapasón y Teclado",    "Fretboard & Keys"),
        ("ear",       "Oído Musical",          "Ear Training"),
        ("sandbox",   "Explorador Libre",      "Theory Sandbox"),
    ]

    # Mapeo de teclas físicas de PC a notas MIDI del piano (C4=60 a E5=76)
    PC_KEY_TO_MIDI: dict[int, int] = {
        Qt.Key.Key_A: 60,  # Do4 / C4
        Qt.Key.Key_W: 61,  # Do#4 / C#4
        Qt.Key.Key_S: 62,  # Re4 / D4
        Qt.Key.Key_E: 63,  # Re#4 / D#4
        Qt.Key.Key_D: 64,  # Mi4 / E4
        Qt.Key.Key_F: 65,  # Fa4 / F4
        Qt.Key.Key_T: 66,  # Fa#4 / F#4
        Qt.Key.Key_G: 67,  # Sol4 / G4
        Qt.Key.Key_Y: 68,  # Sol#4 / G#4
        Qt.Key.Key_H: 69,  # La4 / A4
        Qt.Key.Key_U: 70,  # La#4 / A#4
        Qt.Key.Key_J: 71,  # Si4 / B4
        Qt.Key.Key_K: 72,  # Do5 / C5
        Qt.Key.Key_O: 73,  # Do#5 / C#5
        Qt.Key.Key_L: 74,  # Re5 / D5
    }

    def __init__(self, lang: str = "es") -> None:
        super().__init__()
        self.lang: str = "en" if lang.lower().startswith("en") else "es"
        self.theme_id: str = "parchment"
        self.active_mode: str = "notes"

        self.audio = ConservatoryAudioEngine()
        self.curriculum = ConservatoryCurriculumEngine()

        self.current_question: TrainerQuestion | None = None
        self._question_start_ts: float = time.perf_counter()
        self._awaiting_next: bool = False

        # Metrónomo integrado
        self._metro_running: bool = False
        self._metro_beat: int = 0
        self._metro_timer = QTimer(self)
        self._metro_timer.timeout.connect(self._on_metronome_tick)

        # Modo Reto 60 Segundos (Blitz)
        self._blitz_active: bool = False
        self._blitz_seconds_left: int = 60
        self._blitz_score: int = 0
        self._blitz_timer = QTimer(self)
        self._blitz_timer.setInterval(1000)
        self._blitz_timer.timeout.connect(self._on_blitz_second)

        # Auto-avance tras acertar
        self._next_q_timer = QTimer(self)
        self._next_q_timer.setSingleShot(True)
        self._next_q_timer.timeout.connect(self._load_next_question)

        self._discipline_btns: dict[str, QPushButton] = {}
        self._choice_btns: list[QPushButton] = []

        self._setup_window()
        self._build_ui()
        self._apply_theme()
        self._retranslate_ui()
        self._switch_discipline("notes")

    def _setup_window(self) -> None:
        self.setWindowTitle("MediaHub • MusicalTrainer — Conservatorio Interactivo")
        self.setMinimumSize(1160, 790)
        self.resize(1260, 840)
        ico_path = _get_asset_path(os.path.join("assets", "hub", "Media-Hub.ico"))
        if os.path.isfile(ico_path):
            self.setWindowIcon(QIcon(ico_path))

    # ─────────────────────────────────────────────────────────────────────────
    #  Construcción de la Interfaz de Conservatorio
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("rootWidget")
        self.setCentralWidget(root)

        main_lay = QVBoxLayout(root)
        main_lay.setContentsMargins(14, 12, 14, 12)
        main_lay.setSpacing(10)

        # 1. Cabecera / Masthead de Nogal y Latón
        self.masthead = QFrame()
        self.masthead.setObjectName("mastheadBar")
        mh_lay = QHBoxLayout(self.masthead)
        mh_lay.setContentsMargins(16, 10, 16, 10)
        mh_lay.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        self.lbl_brand = QLabel("MUSICAL TRAINER")
        self.lbl_brand.setFont(QFont("Georgia", 13, QFont.Weight.Bold))
        self.lbl_sub = QLabel()
        self.lbl_sub.setFont(QFont("Segoe UI", 9))
        title_col.addWidget(self.lbl_brand)
        title_col.addWidget(self.lbl_sub)
        mh_lay.addLayout(title_col, stretch=1)

        # Selector de Notación (Solfeo / Cifrado / Dual)
        self.combo_notation = QComboBox()
        self.combo_notation.addItem("Dual: Do · C", "dual")
        self.combo_notation.addItem("Solfeo: Do, Re, Mi", "solfege")
        self.combo_notation.addItem("Cifrado: C, D, E", "cipher")
        self.combo_notation.currentIndexChanged.connect(self._on_notation_changed)
        mh_lay.addWidget(self.combo_notation)

        # Selector de Timbre Acústico
        self.combo_timbre = QComboBox()
        self.combo_timbre.addItem("Piano de Cola", "piano")
        self.combo_timbre.addItem("Rhodes Vintage", "rhodes")
        self.combo_timbre.addItem("Guitarra / Cuerdas", "guitar")
        self.combo_timbre.currentIndexChanged.connect(self._on_timbre_changed)
        mh_lay.addWidget(self.combo_timbre)

        # Metrónomo Acústico Integrado
        self.btn_metro = QPushButton("Metrónomo")
        self.btn_metro.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_metro.clicked.connect(self._toggle_metronome)
        mh_lay.addWidget(self.btn_metro)

        self.spin_bpm = QSpinBox()
        self.spin_bpm.setRange(40, 208)
        self.spin_bpm.setValue(92)
        self.spin_bpm.setSuffix(" BPM")
        self.spin_bpm.valueChanged.connect(self._on_bpm_changed)
        mh_lay.addWidget(self.spin_bpm)

        # Selector de Ambiente Visual (3 temas únicos)
        self.combo_theme = QComboBox()
        for tid, tdata in THEMES.items():
            self.combo_theme.addItem(tdata["name_es"], tid)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        mh_lay.addWidget(self.combo_theme)

        # Botón Sonido y Botón Idioma
        self.btn_sound = QPushButton("Audio")
        self.btn_sound.setFixedWidth(54)
        self.btn_sound.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sound.clicked.connect(self._toggle_sound)
        mh_lay.addWidget(self.btn_sound)

        self.btn_lang = QPushButton("ES")
        self.btn_lang.setFixedWidth(42)
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.clicked.connect(self._toggle_language)
        mh_lay.addWidget(self.btn_lang)

        main_lay.addWidget(self.masthead)

        # 2. Riel de las 7 Disciplinas Musicales
        self.discipline_rail = QFrame()
        self.discipline_rail.setObjectName("disciplineRail")
        rail_lay = QHBoxLayout(self.discipline_rail)
        rail_lay.setContentsMargins(10, 7, 10, 7)
        rail_lay.setSpacing(6)

        for mode_id, name_es, _ in self.DISCIPLINES:
            btn = QPushButton(name_es)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(34)
            btn.clicked.connect(lambda checked=False, m=mode_id: self._switch_discipline(m))
            self._discipline_btns[mode_id] = btn
            rail_lay.addWidget(btn)

        main_lay.addWidget(self.discipline_rail)

        # 3. Escenario Central de Partitura y Controles Pedagógicos
        self.stage_panel = QFrame()
        self.stage_panel.setObjectName("stagePanel")
        stage_lay = QVBoxLayout(self.stage_panel)
        stage_lay.setContentsMargins(14, 10, 14, 10)
        stage_lay.setSpacing(8)

        # 3A. Barra de configuración del ejercicio + Estadísticas en vivo
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.lbl_clef = QLabel("Clave:")
        ctrl_row.addWidget(self.lbl_clef)

        self.combo_clef = QComboBox()
        self.combo_clef.addItem("Clave de Sol (2ª)", "treble")
        self.combo_clef.addItem("Clave de Fa (4ª)", "bass")
        self.combo_clef.addItem("Clave de Do 3ª (Alto)", "alto")
        self.combo_clef.addItem("Clave de Do 4ª (Tenor)", "tenor")
        self.combo_clef.addItem("Gran Pentagrama (Sol+Fa)", "grand")
        self.combo_clef.currentIndexChanged.connect(self._on_clef_changed)
        ctrl_row.addWidget(self.combo_clef)

        self.lbl_level = QLabel("Nivel:")
        ctrl_row.addWidget(self.lbl_level)

        self.combo_level = QComboBox()
        self.combo_level.addItem("Nivel 1 • Básico", 1)
        self.combo_level.addItem("Nivel 2 • Líneas Adicionales", 2)
        self.combo_level.addItem("Nivel 3 • Conservatorio", 3)
        self.combo_level.currentIndexChanged.connect(self._on_level_changed)
        ctrl_row.addWidget(self.combo_level)

        # Selector contextual (ej. Submodo de Oído Musical o Inversiones o Sandbox)
        self.combo_submode = QComboBox()
        self.combo_submode.currentIndexChanged.connect(self._on_submode_changed)
        ctrl_row.addWidget(self.combo_submode)

        self.btn_guides = QPushButton("Guías en Pentagrama: Sí")
        self.btn_guides.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guides.clicked.connect(self._toggle_guides)
        ctrl_row.addWidget(self.btn_guides)

        self.btn_hint = QPushButton("Pista")
        self.btn_hint.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hint.clicked.connect(self._show_hint)
        ctrl_row.addWidget(self.btn_hint)

        self.btn_replay = QPushButton("Escuchar [Espacio]")
        self.btn_replay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_replay.clicked.connect(self._replay_current_audio)
        ctrl_row.addWidget(self.btn_replay)

        self.btn_blitz = QPushButton("Reto 60s")
        self.btn_blitz.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_blitz.clicked.connect(self._toggle_blitz_mode)
        ctrl_row.addWidget(self.btn_blitz)

        self.btn_fifths = QPushButton("Quintas")
        self.btn_fifths.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fifths.clicked.connect(self._open_circle_of_fifths)
        ctrl_row.addWidget(self.btn_fifths)

        self.btn_report = QPushButton("Informe")
        self.btn_report.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_report.clicked.connect(self._open_session_report)
        ctrl_row.addWidget(self.btn_report)

        ctrl_row.addStretch(1)
        stage_lay.addLayout(ctrl_row)

        # 3B. Cinta de métricas de estudio y diagnóstico adaptativo
        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        self.lbl_stat_score = QLabel()
        self.lbl_stat_streak = QLabel()
        self.lbl_stat_speed = QLabel()
        self.lbl_stat_weak = QLabel()

        for lbl in (self.lbl_stat_score, self.lbl_stat_streak, self.lbl_stat_speed, self.lbl_stat_weak):
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            stats_row.addWidget(lbl)

        stats_row.addStretch(1)

        self.btn_reset_stats = QPushButton("Reiniciar Sesión")
        self.btn_reset_stats.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_stats.clicked.connect(self._reset_session_stats)
        stats_row.addWidget(self.btn_reset_stats)

        stage_lay.addLayout(stats_row)

        # 3C. Lienzo de Partitura Grabada (ScoreCanvasWidget)
        self.score_canvas = ScoreCanvasWidget(self)
        stage_lay.addWidget(self.score_canvas, stretch=1)

        # 3D. Banner de Pregunta, Pista y Explicación Musicológica
        self.feedback_frame = QFrame()
        self.feedback_frame.setObjectName("feedbackBanner")
        fb_lay = QVBoxLayout(self.feedback_frame)
        fb_lay.setContentsMargins(12, 7, 12, 7)
        fb_lay.setSpacing(2)

        self.lbl_prompt = QLabel()
        self.lbl_prompt.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_prompt.setWordWrap(True)
        fb_lay.addWidget(self.lbl_prompt)

        self.lbl_theory_note = QLabel()
        self.lbl_theory_note.setFont(QFont("Segoe UI", 9))
        self.lbl_theory_note.setWordWrap(True)
        fb_lay.addWidget(self.lbl_theory_note)

        stage_lay.addWidget(self.feedback_frame)

        # 3E. Cuadrícula Dinámica de Botones de Respuesta / Laboratorio
        self.choices_container = QWidget()
        self.choices_grid = QGridLayout(self.choices_container)
        self.choices_grid.setContentsMargins(0, 2, 0, 2)
        self.choices_grid.setSpacing(7)
        stage_lay.addWidget(self.choices_container)

        main_lay.addWidget(self.stage_panel, stretch=1)

        # 4. Dock Inferior de Instrumentos Interactivos (Piano de Cola + Diapasón de Guitarra)
        self.instrument_dock = QFrame()
        self.instrument_dock.setObjectName("instrumentDock")
        dock_lay = QVBoxLayout(self.instrument_dock)
        dock_lay.setContentsMargins(12, 8, 12, 10)
        dock_lay.setSpacing(6)

        dock_hdr = QHBoxLayout()
        self.lbl_dock_title = QLabel()
        self.lbl_dock_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        dock_hdr.addWidget(self.lbl_dock_title)
        dock_hdr.addStretch(1)

        self.btn_view_piano = QPushButton("Teclado de Piano (C3–G5)")
        self.btn_view_piano.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_piano.clicked.connect(lambda: self._switch_instrument_view(0))
        dock_hdr.addWidget(self.btn_view_piano)

        self.btn_view_guitar = QPushButton("Diapasón de Guitarra (Trastes 0–12)")
        self.btn_view_guitar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_guitar.clicked.connect(lambda: self._switch_instrument_view(1))
        dock_hdr.addWidget(self.btn_view_guitar)

        self.btn_inst_helpers = QPushButton("Nombres en Teclas: Sí")
        self.btn_inst_helpers.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_inst_helpers.clicked.connect(self._toggle_instrument_helpers)
        dock_hdr.addWidget(self.btn_inst_helpers)

        dock_lay.addLayout(dock_hdr)

        self.inst_stack = QStackedWidget()
        self.piano_widget = PianoKeyboardWidget(self)
        self.piano_widget.note_Triggered.connect(self._on_piano_key_pressed)
        self.piano_widget.note_Released.connect(self._on_piano_key_released)
        self.inst_stack.addWidget(self.piano_widget)

        self.fretboard_widget = GuitarFretboardWidget(self)
        self.fretboard_widget.fret_Triggered.connect(self._on_guitar_fret_pressed)
        self.fretboard_widget.fret_Released.connect(self._on_guitar_fret_released)
        self.inst_stack.addWidget(self.fretboard_widget)

        dock_lay.addWidget(self.inst_stack)
        main_lay.addWidget(self.instrument_dock)

    # ─────────────────────────────────────────────────────────────────────────
    #  Temas, Estilos y Traducción Bilingüe (ES / EN)
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        t = THEMES.get(self.theme_id, THEMES["parchment"])
        self.setStyleSheet(build_conservatory_stylesheet(t))

        self.score_canvas.theme = t
        self.piano_widget.theme = t
        self.fretboard_widget.theme = t

        self.lbl_brand.setStyleSheet(f"color: {t['text_masthead']}; font-weight: 800; letter-spacing: 0.6px;")
        self.lbl_sub.setStyleSheet(f"color: {t['text_masthead_sub']};")

        # Estilizar botones de disciplinas
        for mid, btn in self._discipline_btns.items():
            is_act = (mid == self.active_mode)
            if is_act:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {t['accent']}; color: {t['accent_text']}; "
                    f"border: 1px solid {t['accent']}; border-radius: 9px; padding: 6px 12px; "
                    f"font-family: 'Segoe UI'; font-size: 9.5pt; font-weight: 700; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {t['bg_card']}; color: {t['text_primary']}; "
                    f"border: 1px solid {t['border']}; border-radius: 9px; padding: 6px 12px; "
                    f"font-family: 'Segoe UI'; font-size: 9.5pt; font-weight: 600; }}"
                    f"QPushButton:hover {{ background-color: {t['bg_card_hover']}; border: 1px solid {t['border_strong']}; }}"
                )

        # Estilizar botones de herramientas
        sec_btn_qss = (
            f"QPushButton {{ background-color: {t['bg_card']}; color: {t['text_primary']}; "
            f"border: 1px solid {t['border_strong']}; border-radius: 8px; padding: 5px 10px; "
            f"font-family: 'Segoe UI'; font-size: 9pt; font-weight: 600; }}"
            f"QPushButton:hover {{ border: 1px solid {t['accent']}; background-color: {t['bg_card_hover']}; }}"
        )
        accent_btn_qss = (
            f"QPushButton {{ background-color: {t['brass']}; color: #FFFFFF; "
            f"border: none; border-radius: 8px; padding: 5px 11px; "
            f"font-family: 'Segoe UI'; font-size: 9pt; font-weight: 700; }}"
            f"QPushButton:hover {{ background-color: {t['accent']}; }}"
        )

        for b in (
            self.btn_guides, self.btn_hint, self.btn_fifths, self.btn_report,
            self.btn_reset_stats, self.btn_inst_helpers, self.btn_sound, self.btn_lang,
        ):
            b.setStyleSheet(sec_btn_qss)

        self.btn_replay.setStyleSheet(accent_btn_qss)
        self.btn_metro.setStyleSheet(accent_btn_qss if self._metro_running else sec_btn_qss)
        self.btn_blitz.setStyleSheet(accent_btn_qss if self._blitz_active else sec_btn_qss)

        is_piano_view = (self.inst_stack.currentIndex() == 0)
        self.btn_view_piano.setStyleSheet(accent_btn_qss if is_piano_view else sec_btn_qss)
        self.btn_view_guitar.setStyleSheet(accent_btn_qss if not is_piano_view else sec_btn_qss)

        self._style_choice_buttons()
        self.score_canvas.update()
        self.piano_widget.update()
        self.fretboard_widget.update()

    def _style_choice_buttons(self) -> None:
        t = THEMES.get(self.theme_id, THEMES["parchment"])
        qss = (
            f"QPushButton {{ background-color: {t['bg_card']}; color: {t['text_primary']}; "
            f"border: 1.5px solid {t['border_strong']}; border-radius: 10px; padding: 8px 12px; "
            f"font-family: 'Segoe UI'; font-size: 10pt; font-weight: 700; }}"
            f"QPushButton:hover {{ background-color: {t['accent']}; color: {t['accent_text']}; "
            f"border: 1.5px solid {t['accent']}; }}"
        )
        for btn in self._choice_btns:
            btn.setStyleSheet(qss)

    def _retranslate_ui(self) -> None:
        es = (self.lang == "es")
        self.score_canvas.lang = self.lang
        self.btn_lang.setText("ES" if es else "EN")
        self.btn_sound.setText("Audio: On" if self.audio.enabled else "Audio: Off")

        self.lbl_sub.setText(
            "Conservatorio interactivo de partitura, teoría y oído"
            if es
            else "Interactive conservatory for score, theory & ear"
        )

        for mode_id, name_es, name_en in self.DISCIPLINES:
            self._discipline_btns[mode_id].setText(name_es if es else name_en)

        self.lbl_clef.setText("Clave:" if es else "Clef:")
        self.lbl_level.setText("Nivel:" if es else "Level:")

        g_state = ("Sí" if es else "On") if self.score_canvas.show_guides else ("No" if es else "Off")
        self.btn_guides.setText(f"{'Guías' if es else 'Staff Guides'}: {g_state}")
        self.btn_hint.setText("Pista" if es else "Hint")
        self.btn_replay.setText("Escuchar [Espacio]" if es else "Listen [Space]")
        self.btn_fifths.setText("Quintas" if es else "Circle of 5ths")
        self.btn_report.setText("Informe" if es else "Report")
        self.btn_reset_stats.setText("Reiniciar" if es else "Reset")

        if not self._blitz_active:
            self.btn_blitz.setText("Reto 60s" if es else "60s Blitz")

        self.lbl_dock_title.setText(
            "Consola Instrumental Interactiva (Usa el ratón o las teclas A-L / W-O de tu teclado)"
            if es
            else "Interactive Instrument Console (Click or use computer keys A-L / W-O)"
        )
        self.btn_view_piano.setText("Piano de Cola (C3–G5)" if es else "Grand Piano (C3–G5)")
        self.btn_view_guitar.setText("Diapasón (Trastes 0–12)" if es else "Fretboard (Frets 0–12)")

        h_state = ("Sí" if es else "On") if self.piano_widget.show_helpers else ("No" if es else "Off")
        self.btn_inst_helpers.setText(f"{'Etiquetas' if es else 'Key Labels'}: {h_state}")

        self._update_stats_ribbon()

    # ─────────────────────────────────────────────────────────────────────────
    #  Gestión de Disciplinas y Ciclo de Preguntas
    # ─────────────────────────────────────────────────────────────────────────

    def _switch_discipline(self, mode_id: str) -> None:
        self.active_mode = mode_id
        self._next_q_timer.stop()
        self._awaiting_next = False

        # Cambiar vista de instrumento automáticamente si entra a Diapasón
        if mode_id == "fretboard":
            self._switch_instrument_view(1)
        elif mode_id in ("notes", "chords", "intervals", "keys"):
            self._switch_instrument_view(0)

        self._populate_submode_combo()
        self._apply_theme()

        if mode_id == "sandbox":
            self._enter_sandbox_mode()
        else:
            self._load_next_question()

    def _populate_submode_combo(self) -> None:
        es = (self.lang == "es")
        self.combo_submode.blockSignals(True)
        self.combo_submode.clear()

        if self.active_mode == "ear":
            self.combo_submode.setVisible(True)
            self.combo_submode.addItem("👂 Intervalos (Melódico Asc.)" if es else "👂 Intervals (Melodic Asc.)", ("intervals", "melodic_asc"))
            self.combo_submode.addItem("👂 Intervalos (Melódico Desc.)" if es else "👂 Intervals (Melodic Desc.)", ("intervals", "melodic_desc"))
            self.combo_submode.addItem("👂 Intervalos (Armónico)" if es else "👂 Intervals (Harmonic)", ("intervals", "harmonic"))
            self.combo_submode.addItem("🎹 Acordes Auditivos" if es else "🎹 Chord Ear Training", ("chords", "harmonic"))
            self.combo_submode.addItem("🎼 Escalas y Modos Auditivos" if es else "🎼 Scale & Mode Ear Training", ("scales", "melodic_asc"))
        elif self.active_mode == "chords":
            self.combo_submode.setVisible(True)
            self.combo_submode.addItem("Estado Fundamental" if es else "Root Position Only", False)
            self.combo_submode.addItem("Incluir 1ª y 2ª Inversión" if es else "Include 1st & 2nd Inversions", True)
            self.combo_submode.setCurrentIndex(1 if self.curriculum.include_inversions else 0)
        else:
            self.combo_submode.setVisible(False)

        self.combo_submode.blockSignals(False)

    def _load_next_question(self) -> None:
        if self.active_mode == "sandbox":
            return

        self._awaiting_next = False
        q = self.curriculum.generate_question(self.active_mode)
        self.current_question = q
        self._question_start_ts = time.perf_counter()

        self.score_canvas.set_feedback("", "")
        self.score_canvas.set_score_state(
            clef=q.clef,
            notes=q.notes,
            key_sig=q.key_sig,
            hide_mystery=q.hide_notes_until_answered,
            show_labels=False,
            subtitle_badge="melodic" if q.playback_type == "scale" else "",
        )

        # En modo Diapasón iluminamos el traste objetivo; en los demás modos limpiamos resaltado hasta que responda
        if q.mode == "fretboard":
            self.fretboard_widget.set_target_fret(q.fret_target)
            self.piano_widget.set_highlighted_notes([])
        else:
            self.fretboard_widget.set_target_fret(None)
            self.piano_widget.set_highlighted_notes([])

        es = (self.lang == "es")
        self.lbl_prompt.setText(q.prompt_es if es else q.prompt_en)
        self.lbl_theory_note.setText(
            "Selecciona la respuesta correcta abajo o toca la nota directamente en el instrumento."
            if (es and q.mode in ("notes", "fretboard"))
            else ("Elige la opción correcta o pulsa [Espacio] para volver a escuchar." if es else "Choose the correct answer below or press [Space] to replay audio.")
        )

        self._rebuild_choice_buttons(q.choices)
        self._replay_current_audio()

    def _rebuild_choice_buttons(self, choices: list[tuple[str, str]]) -> None:
        while self.choices_grid.count():
            item = self.choices_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self._choice_btns.clear()

        max_cols = 7 if len(choices) <= 7 else 6
        for idx, (cid, label) in enumerate(choices):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("choice_id", cid)
            btn.clicked.connect(lambda checked=False, c=cid: self._submit_answer(c))
            row = idx // max_cols
            col = idx % max_cols
            self.choices_grid.addWidget(btn, row, col)
            self._choice_btns.append(btn)

        self._style_choice_buttons()

    def _submit_answer(self, chosen_id: str) -> None:
        if self.active_mode == "sandbox" or self.current_question is None or self._awaiting_next:
            return

        q = self.current_question
        elapsed_ms = int((time.perf_counter() - self._question_start_ts) * 1000)
        is_ok = self.curriculum.record_attempt(q, chosen_id, elapsed_ms)
        es = (self.lang == "es")
        t = THEMES.get(self.theme_id, THEMES["parchment"])

        # Revelar siempre las notas en el pentagrama y piano al responder
        self.score_canvas.hide_notes_mystery = False
        self.score_canvas.show_note_labels = True
        self.piano_widget.set_highlighted_notes([n.midi for n in q.notes])

        if is_ok:
            self._awaiting_next = True
            if self._blitz_active:
                self._blitz_score += 1
            fb_badge = f"✓ {'¡Correcto!' if es else 'Correct!'} ({elapsed_ms} ms)"
            self.score_canvas.set_feedback("correct", fb_badge)
            self.lbl_prompt.setText(f"✓  {q.correct_display}")
            self.lbl_theory_note.setText(q.theory_detail_es if es else q.theory_detail_en)
            self._replay_current_audio()

            # Colorear botón acertado en verde de conservatorio
            for btn in self._choice_btns:
                if btn.property("choice_id") == chosen_id:
                    btn.setStyleSheet(
                        f"QPushButton {{ background-color: {t['success']}; color: #FFFFFF; "
                        f"border: 1.5px solid {t['success']}; border-radius: 10px; padding: 8px 12px; "
                        f"font-size: 10pt; font-weight: 700; }}"
                    )
            self._update_stats_ribbon()
            delay_ms = 650 if self._blitz_active else 1250
            self._next_q_timer.start(delay_ms)
        else:
            fb_badge = f"✗ {'Intenta de nuevo' if es else 'Try again'}"
            self.score_canvas.set_feedback("wrong", fb_badge)
            self.lbl_theory_note.setText(q.hint_es if es else q.hint_en)
            self.audio.play_error_cue()

            for btn in self._choice_btns:
                if btn.property("choice_id") == chosen_id:
                    btn.setStyleSheet(
                        f"QPushButton {{ background-color: {t['error']}; color: #FFFFFF; "
                        f"border: 1.5px solid {t['error']}; border-radius: 10px; padding: 8px 12px; "
                        f"font-size: 10pt; font-weight: 700; }}"
                    )
            self._update_stats_ribbon()

    # ─────────────────────────────────────────────────────────────────────────
    #  Modo 7: Explorador Libre / Laboratorio Teórico (Sandbox)
    # ─────────────────────────────────────────────────────────────────────────

    def _enter_sandbox_mode(self) -> None:
        self.current_question = None
        es = (self.lang == "es")
        c4 = NoteSpec("C", 4, 0)
        e4 = NoteSpec("E", 4, 0)
        g4 = NoteSpec("G", 4, 0)
        self.score_canvas.set_feedback("", "LABORATORIO ACTIVO" if es else "SANDBOX ACTIVE")
        self.score_canvas.set_score_state(
            clef=self.curriculum.clef,
            notes=[c4, e4, g4],
            key_sig=0,
            hide_mystery=False,
            show_labels=True,
        )
        self.piano_widget.set_highlighted_notes([60, 64, 67])
        self.fretboard_widget.set_target_fret(None)

        self.lbl_prompt.setText(
            "Explorador Libre de Teoría: Toca cualquier tecla del piano, traste de guitarra o estructura inferior:"
            if es
            else "Interactive Theory Sandbox: Click any piano key, guitar fret, or preset below:"
        )
        self.lbl_theory_note.setText(
            "Acorde actual: Do Mayor (Do4 - Mi4 - Sol4) • Fórmula: 1 - 3 - 5 • Toca el teclado o diapasón para analizar."
            if es
            else "Current chord: C Major (C4 - E4 - G4) • Formula: 1 - 3 - 5 • Click any key or fret to inspect."
        )

        # Construir botones rápidos de acordes y escalas para explorar sobre la última nota pulsada
        while self.choices_grid.count():
            item = self.choices_grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self._choice_btns.clear()

        presets: list[tuple[str, str, tuple[int, ...], str]] = [
            ("maj", "Tríada Mayor (1-3-5)", (0, 4, 7), "chord"),
            ("min", "Tríada Menor (1-♭3-5)", (0, 3, 7), "chord"),
            ("dim", "Disminuido (1-♭3-♭5)", (0, 3, 6), "chord"),
            ("maj7", "Acorde Maj7 (1-3-5-7)", (0, 4, 7, 11), "chord"),
            ("m7", "Acorde m7 (1-♭3-5-♭7)", (0, 3, 7, 10), "chord"),
            ("dom7", "Dominante 7 (1-3-5-♭7)", (0, 4, 7, 10), "chord"),
            ("sc_maj", "Escala Mayor", (0, 2, 4, 5, 7, 9, 11, 12), "scale"),
            ("sc_min", "Escala Menor Natural", (0, 2, 3, 5, 7, 8, 10, 12), "scale"),
            ("sc_harm", "Escala Menor Armónica", (0, 2, 3, 5, 7, 8, 11, 12), "scale"),
            ("sc_pent", "Pentatónica Menor", (0, 3, 5, 7, 10, 12), "scale"),
        ]
        for idx, (_, label, semitones, kind) in enumerate(presets):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, st=semitones, k=kind, lbl=label: self._play_sandbox_structure(st, k, lbl)
            )
            self.choices_grid.addWidget(btn, idx // 5, idx % 5)
            self._choice_btns.append(btn)

        self._style_choice_buttons()

    def _play_sandbox_structure(self, semitones: tuple[int, ...], kind: str, label: str) -> None:
        base_midi = self.score_canvas.notes[0].midi if self.score_canvas.notes else 60
        base_midi = max(48, min(67, base_midi))
        notes = [midi_to_note_spec(base_midi + s) for s in semitones]
        self.score_canvas.set_score_state(
            clef=self.curriculum.clef,
            notes=notes,
            key_sig=0,
            hide_mystery=False,
            show_labels=True,
            subtitle_badge="melodic" if kind == "scale" else "",
        )
        self.piano_widget.set_highlighted_notes([n.midi for n in notes])
        names = " · ".join(n.format_name(self.curriculum.notation, include_octave=True) for n in notes)
        self.lbl_prompt.setText(f"{label}  —  {notes[0].format_name(self.curriculum.notation, include_octave=False)}")
        self.lbl_theory_note.setText(f"Notas: {names}")
        if kind == "scale":
            self.audio.play_sequence([n.midi for n in notes], step_delay=0.26, note_duration=0.45)
        else:
            self.audio.play_chord([n.midi for n in notes], arpeggiate=True)

    # ─────────────────────────────────────────────────────────────────────────
    #  Interacción con Piano, Diapasón y Teclado Físico
    # ─────────────────────────────────────────────────────────────────────────

    def _on_piano_key_pressed(self, midi_val: int) -> None:
        self.audio.note_on(midi_val)
        ns = midi_to_note_spec(midi_val)

        if self.active_mode == "sandbox":
            self.score_canvas.set_score_state(
                clef=self.curriculum.clef,
                notes=[ns],
                key_sig=0,
                hide_mystery=False,
                show_labels=True,
            )
            self.piano_widget.set_highlighted_notes([midi_val])
            self.lbl_prompt.setText(
                f"Nota seleccionada: {ns.format_name(self.curriculum.notation, include_octave=True)}"
            )
            self.lbl_theory_note.setText(
                f"Frecuencia fundamental: {ns.freq_hz:.2f} Hz  •  MIDI: {ns.midi}  •  "
                f"2º Armónico (8ª): {ns.freq_hz * 2:.1f} Hz  •  3er Armónico (5ª): {ns.freq_hz * 3:.1f} Hz"
            )
            return

        # Si estamos en Lectura de Partitura o Diapasón, tocar la tecla del piano envía la respuesta
        if self.active_mode in ("notes", "fretboard") and self.current_question is not None:
            self._submit_answer(f"pc_{midi_val % 12}")

    def _on_piano_key_released(self, midi_val: int) -> None:
        self.audio.note_off(midi_val)

    def _on_guitar_fret_pressed(self, string_num: int, fret: int, midi_val: int) -> None:
        self.audio.note_on(midi_val)
        ns = midi_to_note_spec(midi_val)

        if self.active_mode == "sandbox":
            self.score_canvas.set_score_state(
                clef=self.curriculum.clef,
                notes=[ns],
                key_sig=0,
                hide_mystery=False,
                show_labels=True,
            )
            self.piano_widget.set_highlighted_notes([midi_val])
            self.lbl_prompt.setText(
                f"Cuerda {string_num}ª • Traste {fret}  →  {ns.format_name(self.curriculum.notation, include_octave=True)}"
            )
            self.lbl_theory_note.setText(
                f"Frecuencia: {ns.freq_hz:.2f} Hz  •  MIDI: {ns.midi}  •  Equivalente resaltado en el piano y pentagrama."
            )
            return

        if self.active_mode in ("fretboard", "notes") and self.current_question is not None:
            self._submit_answer(f"pc_{midi_val % 12}")

    def _on_guitar_fret_released(self, string_num: int, fret: int, midi_val: int) -> None:
        self.audio.note_off(midi_val)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.isAutoRepeat():
            event.accept()
            return

        key = event.key()
        if key == Qt.Key.Key_Space:
            self._replay_current_audio()
            event.accept()
            return
        if key in self.PC_KEY_TO_MIDI:
            midi_val = self.PC_KEY_TO_MIDI[key]
            self.piano_widget.flash_key(midi_val)
            self._on_piano_key_pressed(midi_val)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.isAutoRepeat():
            event.accept()
            return

        key = event.key()
        if key in self.PC_KEY_TO_MIDI:
            midi_val = self.PC_KEY_TO_MIDI[key]
            self.piano_widget.unflash_key(midi_val)
            self._on_piano_key_released(midi_val)
            event.accept()
            return
        super().keyReleaseEvent(event)

    # ─────────────────────────────────────────────────────────────────────────
    #  Audio, Metrónomo, Reto 60s y Diálogos
    # ─────────────────────────────────────────────────────────────────────────

    def _replay_current_audio(self) -> None:
        if self.current_question is None:
            if self.score_canvas.notes:
                self.audio.play_chord([n.midi for n in self.score_canvas.notes])
            return

        q = self.current_question
        midis = [n.midi for n in q.notes]
        if not midis:
            return

        if q.playback_type == "single":
            self.audio.play_note(midis[0])
        elif q.playback_type == "interval_asc" and len(midis) >= 2:
            self.audio.play_interval(midis[0], midis[1], mode="melodic_asc")
        elif q.playback_type == "interval_desc" and len(midis) >= 2:
            self.audio.play_interval(midis[0], midis[1], mode="melodic_desc")
        elif q.playback_type == "interval_harm" and len(midis) >= 2:
            self.audio.play_interval(midis[0], midis[1], mode="harmonic")
        elif q.playback_type == "chord":
            self.audio.play_chord(midis, arpeggiate=True)
        elif q.playback_type == "scale":
            self.audio.play_sequence(midis, step_delay=0.28, note_duration=0.45)

    def _show_hint(self) -> None:
        if self.current_question is None:
            return
        es = (self.lang == "es")
        self.lbl_theory_note.setText(
            self.current_question.hint_es if es else self.current_question.hint_en
        )

    def _toggle_guides(self) -> None:
        self.score_canvas.show_guides = not self.score_canvas.show_guides
        self._retranslate_ui()
        self.score_canvas.update()

    def _toggle_instrument_helpers(self) -> None:
        new_val = not self.piano_widget.show_helpers
        self.piano_widget.show_helpers = new_val
        self.fretboard_widget.show_helpers = new_val
        self._retranslate_ui()
        self.piano_widget.update()
        self.fretboard_widget.update()

    def _switch_instrument_view(self, index: int) -> None:
        self.inst_stack.setCurrentIndex(index)
        self._apply_theme()

    def _on_notation_changed(self) -> None:
        not_id = self.combo_notation.currentData() or "dual"
        self.curriculum.notation = not_id
        self.score_canvas.notation = not_id
        self.piano_widget.notation = not_id
        self.fretboard_widget.notation = not_id
        self.score_canvas.update()
        self.piano_widget.update()
        self.fretboard_widget.update()
        if self.active_mode != "sandbox":
            self._load_next_question()

    def _on_timbre_changed(self) -> None:
        self.audio.timbre = self.combo_timbre.currentData() or "piano"
        self._replay_current_audio()

    def _on_theme_changed(self) -> None:
        self.theme_id = self.combo_theme.currentData() or "parchment"
        self._apply_theme()

    def _on_clef_changed(self) -> None:
        self.curriculum.clef = self.combo_clef.currentData() or "treble"
        if self.active_mode == "sandbox":
            self.score_canvas.clef = self.curriculum.clef
            self.score_canvas.update()
        else:
            self._load_next_question()

    def _on_level_changed(self) -> None:
        self.curriculum.level = int(self.combo_level.currentData() or 1)
        if self.active_mode != "sandbox":
            self._load_next_question()

    def _on_submode_changed(self) -> None:
        data = self.combo_submode.currentData()
        if self.active_mode == "ear" and isinstance(data, tuple):
            self.curriculum.ear_submode, self.curriculum.ear_play_style = data
            self._load_next_question()
        elif self.active_mode == "chords" and isinstance(data, bool):
            self.curriculum.include_inversions = data
            self._load_next_question()

    def _toggle_sound(self) -> None:
        self.audio.enabled = not self.audio.enabled
        self._retranslate_ui()

    def _toggle_language(self) -> None:
        self.lang = "en" if self.lang == "es" else "es"
        self._populate_submode_combo()
        self._retranslate_ui()
        if self.current_question:
            es = (self.lang == "es")
            self.lbl_prompt.setText(
                self.current_question.prompt_es if es else self.current_question.prompt_en
            )

    def _toggle_metronome(self) -> None:
        self._metro_running = not self._metro_running
        if self._metro_running:
            self._metro_beat = 0
            interval_ms = int(60000 / max(40, self.spin_bpm.value()))
            self._metro_timer.start(interval_ms)
            self._on_metronome_tick()
        else:
            self._metro_timer.stop()
            self.btn_metro.setText("Metrónomo" if self.lang == "es" else "Metronome")
        self._apply_theme()

    def _on_bpm_changed(self, bpm: int) -> None:
        if self._metro_running:
            self._metro_timer.setInterval(int(60000 / max(40, bpm)))

    def _on_metronome_tick(self) -> None:
        is_accent = (self._metro_beat % 4 == 0)
        self.audio.play_metronome_click(accent=is_accent)
        dots = ["● ○ ○ ○", "○ ● ○ ○", "○ ○ ● ○", "○ ○ ○ ●"][self._metro_beat % 4]
        self.btn_metro.setText(f"Metro: {dots}")
        self._metro_beat += 1

    def _toggle_blitz_mode(self) -> None:
        if self._blitz_active:
            self._blitz_active = False
            self._blitz_timer.stop()
            self._retranslate_ui()
            self._apply_theme()
            return

        if self.active_mode == "sandbox":
            self._switch_discipline("notes")

        self._blitz_active = True
        self._blitz_seconds_left = 60
        self._blitz_score = 0
        self.btn_blitz.setText(f"60s ({self._blitz_score} pts)")
        self._apply_theme()
        self._blitz_timer.start()
        self._load_next_question()

    def _on_blitz_second(self) -> None:
        self._blitz_seconds_left -= 1
        if self._blitz_seconds_left <= 0:
            self._blitz_timer.stop()
            self._blitz_active = False
            es = (self.lang == "es")
            self.btn_blitz.setText("Reto 60s" if es else "60s Blitz")
            self._apply_theme()
            self.score_canvas.set_feedback(
                "correct",
                f"{'¡Fin del Reto 60s!' if es else '60s Blitz Complete!'} — {self._blitz_score} {'aciertos' if es else 'correct'}",
            )
        else:
            self.btn_blitz.setText(f"{self._blitz_seconds_left}s ({self._blitz_score} pts)")

    def _open_circle_of_fifths(self) -> None:
        t = THEMES.get(self.theme_id, THEMES["parchment"])
        dlg = CircleOfFifthsDialog(
            theme=t,
            notation=self.curriculum.notation,
            lang=self.lang,
            on_play_chord=lambda midis: self.audio.play_chord(midis, arpeggiate=True),
            parent=self,
        )
        dlg.exec()

    def _open_session_report(self) -> None:
        t = THEMES.get(self.theme_id, THEMES["parchment"])
        dlg = SessionReportDialog(self.curriculum, t, lang=self.lang, parent=self)
        dlg.exec()

    def _reset_session_stats(self) -> None:
        self.curriculum.reset_stats()
        self._update_stats_ribbon()

    def _update_stats_ribbon(self) -> None:
        es = (self.lang == "es")
        c = self.curriculum
        self.lbl_stat_score.setText(
            f"{'Aciertos' if es else 'Score'}: {c.total_correct}/{c.total_answered} ({c.accuracy_pct:.0f}%)"
        )
        self.lbl_stat_streak.setText(
            f"{'Racha' if es else 'Streak'}: {c.current_streak} ({'Máx' if es else 'Best'}: {c.best_streak})"
        )
        self.lbl_stat_speed.setText(
            f"{'Velocidad' if es else 'Avg Speed'}: {c.avg_response_ms} ms"
        )
        weak = c.get_weakest_items(3)
        if weak:
            w_txt = ", ".join(x[0] for x in weak)
            self.lbl_stat_weak.setText(f"{'Reforzar' if es else 'Focus'}: {w_txt}")
        else:
            self.lbl_stat_weak.setText(
                "Adaptativo: Equilibrado" if es else "Adaptive: Balanced"
            )
