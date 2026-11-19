"""
ui/score_canvas.py
──────────────────
Lienzos vectoriales personalizados con QPainter para MediaHub-MusicalTrainer:
  1. ScoreCanvasWidget      — Partitura grabada de alta precisión (4 claves vectoriales + Gran Pentagrama,
                              armaduras, líneas adicionales, acordes, intervalos y guías pedagógicas).
  2. PianoKeyboardWidget    — Teclado de piano de cola interactivo (C3..G5) con fieltro rojo,
                              atajos de teclado físico y etiquetas en Solfeo/Cifrado.
  3. GuitarFretboardWidget  — Diapasón de guitarra de 6 cuerdas y 13 trastes (0..12) con incrustaciones
                              de nácar e interacción clicable.
  4. CircleOfFifthsDialog   — Rueda interactiva del Círculo de Quintas con reproducción sonora.
  5. SessionReportDialog    — Informe Diagnóstico de Conservatorio copiable.
"""

from __future__ import annotations

import math
from typing import Callable

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QBrush,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.music_theory import (
    CIRCLE_OF_FIFTHS,
    CLEF_BOTTOM_LINE_STEP,
    GUITAR_OPEN_STRINGS,
    KEY_SIG_OFFSETS,
    LETTERS,
    NoteSpec,
    format_pitch_class,
    get_clef_guide_notes,
    midi_to_note_spec,
)


# ─────────────────────────────────────────────────────────────────────────────
#  1. Hoja de Partitura Vectorial (ScoreCanvasWidget)
# ─────────────────────────────────────────────────────────────────────────────

class ScoreCanvasWidget(QWidget):
    """
    Lienzo de partitura musical tipo edición Urtext con dibujo vectorial nativo
    de claves (Sol, Fa, Do 3ª, Do 4ª y Gran Pentagrama), armaduras, notas y guías.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(235)
        self.theme: dict[str, str] = {}
        self.clef: str = "treble"         # 'treble' | 'bass' | 'alto' | 'tenor' | 'grand'
        self.notes: list[NoteSpec] = []
        self.key_sig: int = 0             # -7..+7
        self.notation: str = "dual"       # 'solfege' | 'cipher' | 'dual'
        self.show_guides: bool = True
        self.show_note_labels: bool = False
        self.hide_notes_mystery: bool = False
        self.feedback_state: str = ""     # '' | 'correct' | 'wrong'
        self.feedback_text: str = ""
        self.subtitle_badge: str = ""
        self.lang: str = "es"

    def set_score_state(
        self,
        clef: str,
        notes: list[NoteSpec],
        key_sig: int = 0,
        hide_mystery: bool = False,
        show_labels: bool = False,
        subtitle_badge: str = "",
    ) -> None:
        self.clef = clef
        self.notes = list(notes)
        self.key_sig = key_sig
        self.hide_notes_mystery = hide_mystery
        self.show_note_labels = show_labels
        self.subtitle_badge = subtitle_badge
        self.update()

    def set_feedback(self, state: str, text: str = "") -> None:
        self.feedback_state = state
        self.feedback_text = text
        self.update()

    # ── Geometría del pentagrama ─────────────────────────────────────────────

    def _staff_line_y(self, bottom_y: float, line_spacing: float, offset: int) -> float:
        """
        Convierte un offset diatónico (0 = Línea 1 inferior, 8 = Línea 5 superior)
        en coordenada Y en píxeles. Cada paso diatónico es `line_spacing / 2`.
        """
        return bottom_y - (offset * (line_spacing / 2.0))

    # ── Dibujo vectorial de claves (sin depender de fuentes externas) ────────

    def _draw_treble_clef(self, p: QPainter, x: float, bottom_y: float, ls: float, ink: QColor) -> None:
        """Dibuja una Clave de Sol (G Clef) estilizada con curvas Bézier alrededor de la 2ª línea."""
        p.save()
        g_line_y = bottom_y - ls  # 2ª línea (Sol4)
        top_y = bottom_y - 4.0 * ls

        pen = QPen(ink, 2.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        path = QPainterPath()
        # Espiral central naciente en la 2ª línea (G4)
        path.moveTo(x + 2, g_line_y - 2)
        path.cubicTo(x + 14, g_line_y - 14, x + 22, g_line_y + 4, x + 10, g_line_y + 12)
        path.cubicTo(x - 8, g_line_y + 16, x - 14, g_line_y - 6, x + 2, g_line_y - 18)
        # Ascenso hacia el lazo superior por encima de la 5ª línea
        path.cubicTo(x + 20, top_y + 6, x + 18, top_y - 22, x + 6, top_y - 20)
        path.cubicTo(x - 4, top_y - 18, x - 2, top_y + 4, x + 4, bottom_y + 16)
        # Gancho inferior con botón de tinta
        path.cubicTo(x + 5, bottom_y + 24, x - 6, bottom_y + 26, x - 8, bottom_y + 19)
        p.drawPath(path)

        p.setBrush(QBrush(ink))
        p.drawEllipse(QPointF(x - 7, bottom_y + 18), 3.2, 3.2)
        # Punto de referencia sutil en la 2ª línea
        p.restore()

    def _draw_bass_clef(self, p: QPainter, x: float, bottom_y: float, ls: float, ink: QColor) -> None:
        """Dibuja una Clave de Fa (F Clef) centrada en la 4ª línea con sus dos puntos."""
        p.save()
        f_line_y = bottom_y - 3.0 * ls  # 4ª línea (Fa3)

        p.setPen(QPen(ink, 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(QBrush(ink))
        # Bulbo inicial sobre la 4ª línea
        p.drawEllipse(QPointF(x - 6, f_line_y), 4.2, 4.2)

        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.moveTo(x - 6, f_line_y)
        path.cubicTo(x - 8, f_line_y - 16, x + 15, f_line_y - 16, x + 15, f_line_y + 2)
        path.cubicTo(x + 15, f_line_y + 18, x + 2, bottom_y - 2, x - 10, bottom_y + 2)
        p.drawPath(path)

        # Dos puntos flanqueando la 4ª línea (espacios 3 y 4)
        p.setBrush(QBrush(ink))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(x + 21, f_line_y - ls * 0.45), 2.5, 2.5)
        p.drawEllipse(QPointF(x + 21, f_line_y + ls * 0.45), 2.5, 2.5)
        p.restore()

    def _draw_c_clef(
        self, p: QPainter, x: float, bottom_y: float, ls: float, ink: QColor, tenor: bool = False
    ) -> None:
        """Dibuja una Clave de Do en 3ª (Alto) o en 4ª (Tenor) señalando la línea de Do4."""
        p.save()
        c_offset = 6 if tenor else 4  # 4ª línea (offset 6) o 3ª línea (offset 4)
        cy = self._staff_line_y(bottom_y, ls, c_offset)
        top_y = cy - 2.0 * ls
        bot_y = cy + 2.0 * ls

        # Columna doble izquierda
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(ink))
        p.drawRect(QRectF(x - 10, top_y, 4.2, bot_y - top_y))
        p.setPen(QPen(ink, 1.6))
        p.drawLine(QPointF(x - 2, top_y), QPointF(x - 2, bot_y))

        # Dos arcos simétricos que convergen en la línea de Do4 (cy)
        p.setPen(QPen(ink, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.moveTo(x - 1, top_y + 2)
        path.cubicTo(x + 16, top_y - 2, x + 16, cy - 3, x + 1, cy)
        path.cubicTo(x + 16, cy + 3, x + 16, bot_y + 2, x - 1, bot_y - 2)
        p.drawPath(path)

        # Pequeña muesca indicadora de Do4
        p.setBrush(QBrush(ink))
        p.drawEllipse(QPointF(x + 1, cy), 2.4, 2.4)
        p.restore()

    def _draw_accidental_glyph(
        self, p: QPainter, x: float, y: float, kind: int, color: QColor, scale: float = 1.0
    ) -> None:
        """Dibuja un sostenido (kind=1) o bemol (kind=-1) centrado en (x, y)."""
        if kind == 0:
            return
        p.save()
        font = QFont("Segoe UI Symbol", int(14 * scale), QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(color)
        sym = "♯" if kind > 0 else "♭"
        rect = QRectF(x - 12 * scale, y - 14 * scale, 24 * scale, 28 * scale)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, sym)
        p.restore()

    def _draw_single_staff_system(
        self,
        p: QPainter,
        clef_id: str,
        left_x: float,
        right_x: float,
        bottom_y: float,
        ls: float,
        ink: QColor,
        line_col: QColor,
        draw_notes: list[NoteSpec],
    ) -> None:
        """Dibuja un pentagrama de 5 líneas, su clave, armadura, guías y notas."""
        top_y = bottom_y - 4.0 * ls

        # 5 líneas horizontales del pentagrama
        p.setPen(QPen(line_col, 1.35))
        for i in range(5):
            ly = bottom_y - i * ls
            p.drawLine(QPointF(left_x, ly), QPointF(right_x, ly))

        # Barra inicial y doble barra final de compás
        p.setPen(QPen(ink, 1.8))
        p.drawLine(QPointF(left_x, top_y), QPointF(left_x, bottom_y))
        p.drawLine(QPointF(right_x - 6, top_y), QPointF(right_x - 6, bottom_y))
        p.setPen(QPen(ink, 3.6))
        p.drawLine(QPointF(right_x, top_y), QPointF(right_x, bottom_y))

        # Dibujar Clave
        clef_x = left_x + 28
        if clef_id == "treble":
            self._draw_treble_clef(p, clef_x, bottom_y, ls, ink)
        elif clef_id == "bass":
            self._draw_bass_clef(p, clef_x, bottom_y, ls, ink)
        elif clef_id == "alto":
            self._draw_c_clef(p, clef_x, bottom_y, ls, ink, tenor=False)
        elif clef_id == "tenor":
            self._draw_c_clef(p, clef_x, bottom_y, ls, ink, tenor=True)

        # Dibujar Armadura de Clave (si key_sig != 0)
        ks_x = clef_x + 34
        if self.key_sig != 0:
            offsets_table = KEY_SIG_OFFSETS.get(clef_id, KEY_SIG_OFFSETS["treble"])
            count = min(7, abs(self.key_sig))
            kind = 1 if self.key_sig > 0 else -1
            offs = offsets_table["sharps" if kind > 0 else "flats"][:count]
            for idx, off in enumerate(offs):
                ay = self._staff_line_y(bottom_y, ls, off)
                self._draw_accidental_glyph(p, ks_x + idx * 12, ay, kind, ink, scale=0.95)
            ks_x += count * 12 + 10

        # Dibujar riel de Guías Pedagógicas a la derecha si está activo
        if self.show_guides:
            guide_data = get_clef_guide_notes(clef_id, notation="cipher" if self.notation == "cipher" else "solfege")
            guide_bg = QColor(self.theme.get("score_guide_bg", "#EFE6D0"))
            guide_fg = QColor(self.theme.get("score_guide_fg", "#6D563E"))
            p.save()
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            # Etiquetas de las 5 líneas junto al borde derecho
            for off, lbl in guide_data["lines"]:
                gy = self._staff_line_y(bottom_y, ls, off)
                pill = QRectF(right_x - 118, gy - 6.5, 50, 13)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(guide_bg)
                p.drawRoundedRect(pill, 4, 4)
                p.setPen(guide_fg)
                p.drawText(pill, Qt.AlignmentFlag.AlignCenter, f"L{(off//2)+1}: {lbl}")
            # Etiquetas de los 4 espacios desplazadas ligeramente
            for off, lbl in guide_data["spaces"]:
                gy = self._staff_line_y(bottom_y, ls, off)
                pill = QRectF(right_x - 64, gy - 6.5, 52, 13)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(guide_bg)
                p.drawRoundedRect(pill, 4, 4)
                p.setPen(guide_fg)
                p.drawText(pill, Qt.AlignmentFlag.AlignCenter, f"E{(off//2)+1}: {lbl}")
            p.restore()

        # Si estamos en modo misterio (Oído Musical antes de responder), mostrar medallón acústico
        if self.hide_notes_mystery:
            cx = (ks_x + right_x - 120) / 2.0
            cy = (top_y + bottom_y) / 2.0
            p.save()
            accent_c = QColor(self.theme.get("accent", "#9E2A2B"))
            soft_c = QColor(self.theme.get("accent_soft", "#F7E3E1"))
            p.setPen(QPen(accent_c, 2.0, Qt.PenStyle.DashLine))
            p.setBrush(soft_c)
            box = QRectF(cx - 145, cy - 28, 290, 56)
            p.drawRoundedRect(box, 14, 14)
            p.setPen(accent_c)
            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            msg = (
                "👂 Escucha con atención... (Pulsa Espacio para repetir)"
                if self.lang == "es"
                else "👂 Listen carefully... (Press Space to replay)"
            )
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, msg)
            p.restore()
            return

        if not draw_notes:
            return

        # Determinar si las notas se dibujan apiladas (acorde / armónico) o secuenciales (escala / intervalo)
        usable_left = ks_x + 36
        usable_right = right_x - (135 if self.show_guides else 40)
        center_x = (usable_left + usable_right) / 2.0

        is_sequential = len(draw_notes) > 4 or (len(draw_notes) == 2 and self.subtitle_badge == "melodic")
        sorted_notes = sorted(draw_notes, key=lambda n: n.diatonic_step)

        note_positions: list[tuple[NoteSpec, float, float, int]] = []
        if is_sequential:
            count = len(draw_notes)
            span = min(340.0, max(120.0, usable_right - usable_left - 30))
            start_x = center_x - span / 2.0
            step_x = span / max(1, count - 1)
            for idx, ns in enumerate(draw_notes):
                off = ns.staff_offset(clef_id)
                ny = self._staff_line_y(bottom_y, ls, off)
                note_positions.append((ns, start_x + idx * step_x, ny, off))
        else:
            # Apiladas (una sola nota, intervalo o acorde): desplazar segundas adyacentes
            prev_off: int | None = None
            nudged = False
            for ns in sorted_notes:
                off = ns.staff_offset(clef_id)
                if prev_off is not None and abs(off - prev_off) <= 1 and not nudged:
                    nx = center_x + 15.0
                    nudged = True
                else:
                    nx = center_x
                    nudged = False
                prev_off = off
                ny = self._staff_line_y(bottom_y, ls, off)
                note_positions.append((ns, nx, ny, off))

        # Color de las cabezas de nota según estado de respuesta
        if self.feedback_state == "correct":
            note_color = QColor(self.theme.get("success", "#1E6B43"))
        elif self.feedback_state == "wrong":
            note_color = QColor(self.theme.get("error", "#B42318"))
        else:
            note_color = ink

        # Dibujar líneas adicionales (ledger lines), cabezas, plicas y alteraciones
        for idx, (ns, nx, ny, off) in enumerate(note_positions):
            # Líneas adicionales inferiores (offsets -2, -4, -6...)
            if off <= -2:
                p.setPen(QPen(ink, 1.6))
                for l_off in range(-2, off - 1, -2):
                    ly = self._staff_line_y(bottom_y, ls, l_off)
                    p.drawLine(QPointF(nx - 14, ly), QPointF(nx + 14, ly))
            # Líneas adicionales superiores (offsets 10, 12, 14...)
            if off >= 10:
                p.setPen(QPen(ink, 1.6))
                for l_off in range(10, off + 1, 2):
                    ly = self._staff_line_y(bottom_y, ls, l_off)
                    p.drawLine(QPointF(nx - 14, ly), QPointF(nx + 14, ly))

            # Alteración accidental a la izquierda de la nota
            if ns.accidental != 0:
                acc_dx = -22 - (12 if (idx % 2 == 1 and not is_sequential) else 0)
                self._draw_accidental_glyph(p, nx + acc_dx, ny, ns.accidental, note_color, scale=1.0)

            # Cabeza de nota ovalada inclinada (-18°)
            p.save()
            p.translate(nx, ny)
            p.rotate(-18.0)
            p.setPen(QPen(note_color, 1.6))
            p.setBrush(QBrush(note_color))
            p.drawEllipse(QPointF(0, 0), 7.6, 5.4)
            p.restore()

            # Plica individual (en modo secuencial o nota única)
            if is_sequential or len(note_positions) == 1:
                p.setPen(QPen(note_color, 2.0))
                if off < 4:
                    # Plica hacia arriba por la derecha
                    p.drawLine(QPointF(nx + 6.8, ny - 1), QPointF(nx + 6.8, ny - 3.3 * ls))
                else:
                    # Plica hacia abajo por la izquierda
                    p.drawLine(QPointF(nx - 6.8, ny + 1), QPointF(nx - 6.8, ny + 3.3 * ls))

            # Etiqueta flotante con el nombre de la nota (en Laboratorio o tras responder)
            if self.show_note_labels or self.feedback_state in ("correct", "wrong"):
                p.save()
                lbl_txt = ns.format_name(self.notation, include_octave=True)
                p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                fm = QFontMetrics(p.font())
                tw = fm.horizontalAdvance(lbl_txt) + 12
                lx = nx - tw / 2.0
                ly = (bottom_y + 12 + (idx * 17)) if not is_sequential else (bottom_y + 14)
                badge_rect = QRectF(lx, ly, tw, 16)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(self.theme.get("brass", "#B57C1E")))
                p.drawRoundedRect(badge_rect, 5, 5)
                p.setPen(QColor("#FFFFFF"))
                p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, lbl_txt)
                p.restore()

        # Plica unificada para acordes o intervalos apilados
        if not is_sequential and len(note_positions) > 1:
            min_y = min(pos[2] for pos in note_positions)
            max_y = max(pos[2] for pos in note_positions)
            avg_off = sum(pos[3] for pos in note_positions) / len(note_positions)
            p.setPen(QPen(note_color, 2.1))
            if avg_off < 4:
                stem_x = center_x + 6.8
                p.drawLine(QPointF(stem_x, max_y), QPointF(stem_x, min_y - 3.1 * ls))
            else:
                stem_x = center_x - 6.8
                p.drawLine(QPointF(stem_x, min_y), QPointF(stem_x, max_y + 3.1 * ls))

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())

        paper_outer = QColor(self.theme.get("score_paper", "#FCF8EE"))
        paper_inner = QColor(self.theme.get("score_paper_inner", "#F7F0DE"))
        border_col = QColor(self.theme.get("score_border", "#C5B496"))
        ink = QColor(self.theme.get("score_ink", "#1C1612"))
        line_col = QColor(self.theme.get("score_line", "#5A4938"))

        # Fondo de pergamino con ligero degradado cálido de atril
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, paper_outer)
        grad.setColorAt(1.0, paper_inner)

        card_rect = QRectF(3, 3, w - 6, h - 6)
        p.setPen(QPen(border_col, 1.8))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(card_rect, 14, 14)

        # Marco interior fino tipo edición clásica Peters/Henle
        inner_rect = QRectF(10, 10, w - 20, h - 20)
        p.setPen(QPen(border_col, 0.8, Qt.PenStyle.SolidLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(inner_rect, 10, 10)

        left_x = 34.0
        right_x = w - 28.0

        if self.clef == "grand":
            # Gran Pentagrama (Sol arriba + Fa abajo unidos por llave de piano)
            ls = 11.5
            treble_bot_y = h * 0.41
            bass_bot_y = h * 0.80
            treble_top_y = treble_bot_y - 4.0 * ls

            # Llave lateral izquierda del Gran Pentagrama
            p.setPen(QPen(ink, 2.6))
            p.drawLine(QPointF(left_x - 8, treble_top_y), QPointF(left_x - 8, bass_bot_y))
            p.drawLine(QPointF(left_x - 8, treble_top_y), QPointF(left_x - 2, treble_top_y))
            p.drawLine(QPointF(left_x - 8, bass_bot_y), QPointF(left_x - 2, bass_bot_y))

            treble_notes = [n for n in self.notes if n.midi >= 60]
            bass_notes = [n for n in self.notes if n.midi < 60]

            self._draw_single_staff_system(
                p, "treble", left_x, right_x, treble_bot_y, ls, ink, line_col, treble_notes
            )
            self._draw_single_staff_system(
                p, "bass", left_x, right_x, bass_bot_y, ls, ink, line_col, bass_notes
            )
        else:
            ls = 14.5
            bottom_y = (h / 2.0) + (2.0 * ls) + 4.0
            self._draw_single_staff_system(
                p, self.clef, left_x, right_x, bottom_y, ls, ink, line_col, self.notes
            )

        # Cabecera editorial superior izquierda en la hoja
        clef_titles_es = {
            "treble": "CLAVE DE SOL EN 2ª",
            "bass": "CLAVE DE FA EN 4ª",
            "alto": "CLAVE DE DO EN 3ª (CONTRALTO / VIOLA)",
            "tenor": "CLAVE DE DO EN 4ª (TENOR / CELLO)",
            "grand": "GRAN PENTAGRAMA DE CONCIERTO (SOL + FA)",
        }
        clef_titles_en = {
            "treble": "TREBLE CLEF (G4)",
            "bass": "BASS CLEF (F3)",
            "alto": "ALTO CLEF (C4 MIDDLE LINE)",
            "tenor": "TENOR CLEF (C4 FOURTH LINE)",
            "grand": "CONCERT GRAND STAFF (TREBLE + BASS)",
        }
        header_txt = (
            clef_titles_es.get(self.clef, "CLAVE DE SOL")
            if self.lang == "es"
            else clef_titles_en.get(self.clef, "TREBLE CLEF")
        )
        p.setFont(QFont("Georgia", 8, QFont.Weight.Bold))
        p.setPen(QColor(self.theme.get("score_guide_fg", "#6D563E")))
        p.drawText(QRectF(22, 14, w - 44, 18), Qt.AlignmentFlag.AlignLeft, f"✦  {header_txt}")

        # Sello de retroalimentación en la esquina superior derecha de la hoja
        if self.feedback_text:
            is_ok = (self.feedback_state == "correct")
            bg_c = QColor(self.theme.get("success", "#1E6B43") if is_ok else self.theme.get("error", "#B42318"))
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            fm = QFontMetrics(p.font())
            bw = min(w * 0.58, fm.horizontalAdvance(self.feedback_text) + 22)
            pill_r = QRectF(w - bw - 20, 14, bw, 20)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg_c)
            p.drawRoundedRect(pill_r, 6, 6)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(pill_r, Qt.AlignmentFlag.AlignCenter, self.feedback_text)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  2. Teclado de Piano de Cola Interactivo (PianoKeyboardWidget)
# ─────────────────────────────────────────────────────────────────────────────

class PianoKeyboardWidget(QWidget):
    """
    Teclado de piano de cola de 2.5 octavas (C3=48 a G5=79) con fieltro rojo de conservatorio,
    etiquetas bilingües opcionales, atajos de teclado de PC y resaltado polifónico.
    """

    note_Triggered = pyqtSignal(int)  # Emite el número MIDI (48..79) al pulsar una tecla
    note_Released = pyqtSignal(int)   # Emite el número MIDI al soltar la tecla (sustain/release)

    # Rango MIDI: 48 (C3) .. 79 (G5) -> 19 teclas blancas y 13 negras
    START_MIDI = 48
    END_MIDI = 79

    # Mapeo de atajos de teclado físico para la octava central (C4=60 .. E5=76)
    KEY_SHORTCUT_LABELS: dict[int, str] = {
        60: "A", 61: "W", 62: "S", 63: "E", 64: "D", 65: "F",
        66: "T", 67: "G", 68: "Y", 69: "H", 70: "U", 71: "J",
        72: "K", 73: "O", 74: "L",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(138)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.theme: dict[str, str] = {}
        self.notation: str = "dual"
        self.show_helpers: bool = True
        self.highlighted_midis: set[int] = set()
        self.pressed_midi: int | None = None
        self.hover_midi: int | None = None

        self._white_rects: list[tuple[int, QRectF]] = []
        self._black_rects: list[tuple[int, QRectF]] = []

    @staticmethod
    def _is_black(midi_val: int) -> bool:
        return (midi_val % 12) in (1, 3, 6, 8, 10)

    def set_highlighted_notes(self, midis: list[int] | set[int]) -> None:
        self.highlighted_midis = set(midis)
        self.update()

    def flash_key(self, midi_val: int) -> None:
        self.pressed_midi = midi_val
        self.update()

    def _rebuild_geometry(self) -> None:
        w = float(self.width())
        h = float(self.height())
        margin_x = 10.0
        top_y = 14.0
        key_h = h - top_y - 8.0

        white_midis = [
            m for m in range(self.START_MIDI, self.END_MIDI + 1) if not self._is_black(m)
        ]
        num_white = len(white_midis)
        kw = (w - 2.0 * margin_x) / max(1, num_white)

        self._white_rects.clear()
        self._black_rects.clear()

        white_x_map: dict[int, float] = {}
        for idx, m in enumerate(white_midis):
            rx = margin_x + idx * kw
            white_x_map[m] = rx
            self._white_rects.append((m, QRectF(rx, top_y, kw - 1.5, key_h)))

        bw = kw * 0.62
        bh = key_h * 0.61
        for m in range(self.START_MIDI, self.END_MIDI + 1):
            if self._is_black(m) and (m - 1) in white_x_map:
                left_white_x = white_x_map[m - 1]
                bx = left_white_x + kw - (bw / 2.0) - 0.75
                self._black_rects.append((m, QRectF(bx, top_y, bw, bh)))

    def _midi_at_pos(self, pos: QPointF) -> int | None:
        # Primero comprobar teclas negras (están encima)
        for m, r in self._black_rects:
            if r.contains(pos):
                return m
        for m, r in self._white_rects:
            if r.contains(pos):
                return m
        return None

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        m = self._midi_at_pos(event.position())
        if m != self.hover_midi:
            self.hover_midi = m
            self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self.pressed_midi is not None:
            self.note_Released.emit(self.pressed_midi)
        self.hover_midi = None
        self.pressed_midi = None
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            m = self._midi_at_pos(event.position())
            if m is not None:
                self.pressed_midi = m
                self.update()
                self.note_Triggered.emit(m)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self.pressed_midi is not None:
            self.note_Released.emit(self.pressed_midi)
        self.pressed_midi = None
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        self._rebuild_geometry()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())

        wood_c = QColor(self.theme.get("piano_wood", "#2B1C14"))
        felt_c = QColor(self.theme.get("piano_felt", "#9E2225"))
        white_c = QColor(self.theme.get("piano_white", "#FCF9F2"))
        white_hover_c = QColor(self.theme.get("piano_white_hover", "#F3E8D2"))
        black_c = QColor(self.theme.get("piano_black", "#1E1916"))
        accent_c = QColor(self.theme.get("accent", "#9E2A2B"))
        brass_c = QColor(self.theme.get("brass", "#B57C1E"))

        # Caja de madera del teclado
        p.setPen(QPen(brass_c, 1.4))
        p.setBrush(wood_c)
        p.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 12, 12)

        # Tira de fieltro rojo escarlata sobre el cabezal de las teclas
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(felt_c)
        p.drawRect(QRectF(10, 10, w - 20, 5))

        # 1. Dibujar teclas blancas
        for m, r in self._white_rects:
            is_hi = (m in self.highlighted_midis) or ((m % 12) in {x % 12 for x in self.highlighted_midis} and len(self.highlighted_midis) == 1 and m == next(iter(self.highlighted_midis)))
            is_press = (m == self.pressed_midi)
            is_hov = (m == self.hover_midi)

            if is_press:
                fill = accent_c
                txt_col = QColor("#FFFFFF")
            elif is_hi:
                fill = brass_c
                txt_col = QColor("#FFFFFF")
            elif is_hov:
                fill = white_hover_c
                txt_col = QColor("#1E1712")
            else:
                fill = white_c
                txt_col = QColor("#382D24")

            p.setPen(QPen(QColor("#5C4B3B"), 1.0))
            p.setBrush(fill)
            p.drawRoundedRect(r, 5, 5)

            # Etiqueta de nota en la parte inferior de la tecla blanca
            if self.show_helpers or m == 60:
                ns = midi_to_note_spec(m)
                lbl = ns.format_name(
                    "solfege" if self.notation == "solfege" else "cipher",
                    include_octave=(ns.letter == "C"),
                )
                p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                p.setPen(txt_col)
                lbl_r = QRectF(r.left(), r.bottom() - 22, r.width(), 18)
                p.drawText(lbl_r, Qt.AlignmentFlag.AlignCenter, lbl)

            # Insignia de atajo de teclado físico (A, S, D, F...)
            if m in self.KEY_SHORTCUT_LABELS:
                sc = self.KEY_SHORTCUT_LABELS[m]
                p.setFont(QFont("Segoe UI", 6, QFont.Weight.DemiBold))
                p.setPen(QColor("#FFFFFF") if (is_press or is_hi) else QColor("#8C7A68"))
                sc_r = QRectF(r.left(), r.bottom() - 36, r.width(), 13)
                p.drawText(sc_r, Qt.AlignmentFlag.AlignCenter, f"[{sc}]")

        # 2. Dibujar teclas negras
        for m, r in self._black_rects:
            is_hi = (m in self.highlighted_midis)
            is_press = (m == self.pressed_midi)
            is_hov = (m == self.hover_midi)

            if is_press:
                fill = accent_c
            elif is_hi:
                fill = brass_c
            elif is_hov:
                fill = QColor("#3A302A")
            else:
                fill = black_c

            p.setPen(QPen(QColor("#0D0A08"), 1.2))
            p.setBrush(fill)
            p.drawRoundedRect(r, 4, 4)

            # Brillo biselado superior de tecla de ébano
            if not is_press and not is_hi:
                p.setPen(QPen(QColor(255, 255, 255, 42), 1.0))
                p.drawLine(QPointF(r.left() + 3, r.bottom() - 5), QPointF(r.right() - 3, r.bottom() - 5))

            if self.show_helpers:
                ns = midi_to_note_spec(m)
                lbl = ns.format_name("solfege" if self.notation == "solfege" else "cipher", include_octave=False)
                p.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
                p.setPen(QColor("#F4EAD5"))
                p.drawText(QRectF(r.left(), r.bottom() - 20, r.width(), 16), Qt.AlignmentFlag.AlignCenter, lbl)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  3. Diapasón de Guitarra Luthier Interactivo (GuitarFretboardWidget)
# ─────────────────────────────────────────────────────────────────────────────

class GuitarFretboardWidget(QWidget):
    """
    Diapasón de guitarra de palo de rosa de 6 cuerdas y 13 trastes (0..12)
    con cejuela de hueso, trastes de latón, marcadores de nácar e interacción clicable.
    """

    fret_Triggered = pyqtSignal(int, int, int)  # (string_num 1..6, fret 0..12, midi_note)
    fret_Released = pyqtSignal(int, int, int)

    NUM_FRETS = 12

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(138)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme: dict[str, str] = {}
        self.notation: str = "dual"
        self.show_helpers: bool = False
        self.target_position: tuple[int, int] | None = None  # (string 1..6, fret 0..12)
        self.active_position: tuple[int, int] | None = None

    def set_target_fret(self, pos: tuple[int, int] | None) -> None:
        self.target_position = pos
        self.update()

    def _board_geometry(self) -> tuple[float, float, float, float, float, float]:
        w = float(self.width())
        h = float(self.height())
        left_x = 58.0
        right_x = w - 18.0
        top_y = 18.0
        bot_y = h - 22.0
        fret_w = (right_x - left_x) / (self.NUM_FRETS + 1)
        str_h = (bot_y - top_y) / 5.0
        return left_x, right_x, top_y, bot_y, fret_w, str_h

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        left_x, right_x, top_y, bot_y, fret_w, str_h = self._board_geometry()
        pos = event.position()
        if pos.x() < left_x - 10 or pos.x() > right_x + 10:
            return
        fret = int((pos.x() - left_x) / fret_w)
        fret = max(0, min(self.NUM_FRETS, fret))
        s_idx = int(round((pos.y() - top_y) / max(1.0, str_h)))
        s_idx = max(0, min(5, s_idx))
        s_num, _, open_midi, _ = GUITAR_OPEN_STRINGS[s_idx]
        midi_val = open_midi + fret
        self.active_position = (s_num, fret)
        self._last_fret_midi = (s_num, fret, midi_val)
        self.update()
        self.fret_Triggered.emit(s_num, fret, midi_val)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if hasattr(self, "_last_fret_midi") and self._last_fret_midi:
            s_num, fret, midi_val = self._last_fret_midi
            self.fret_Released.emit(s_num, fret, midi_val)
            self._last_fret_midi = None
        self.active_position = None
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        left_x, right_x, top_y, bot_y, fret_w, str_h = self._board_geometry()

        wood_c = QColor(self.theme.get("fret_wood", "#3B2316"))
        wire_c = QColor(self.theme.get("fret_wire", "#C59B52"))
        accent_c = QColor(self.theme.get("accent", "#9E2A2B"))
        brass_c = QColor(self.theme.get("brass", "#B57C1E"))

        # Cuerpo de madera de palisandro del diapasón
        p.setPen(QPen(wire_c, 1.5))
        p.setBrush(wood_c)
        p.drawRoundedRect(QRectF(4, 4, w - 8, h - 8), 12, 12)

        # Cejuela de hueso (entre traste 0 al aire y traste 1)
        nut_x = left_x + fret_w
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#F4EAD5"))
        p.drawRect(QRectF(nut_x - 3, top_y - 6, 5.5, (bot_y - top_y) + 12))

        # Alambres de traste (1..12) e incrustaciones de nácar (3, 5, 7, 9, 12)
        for f in range(self.NUM_FRETS + 1):
            fx = left_x + (f + 1) * fret_w
            if f >= 1:
                p.setPen(QPen(wire_c, 1.8))
                p.drawLine(QPointF(fx, top_y - 4), QPointF(fx, bot_y + 4))

            # Número de traste abajo
            cx = left_x + (f + 0.5) * fret_w
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(QColor("#D8C3A5"))
            p.drawText(QRectF(cx - 14, bot_y + 5, 28, 14), Qt.AlignmentFlag.AlignCenter, str(f))

            # Puntos de nácar (Fret markers)
            mid_y = (top_y + bot_y) / 2.0
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(246, 240, 224, 150))
            if f in (3, 5, 7, 9):
                p.drawEllipse(QPointF(cx, mid_y), 4.5, 4.5)
            elif f == 12:
                p.drawEllipse(QPointF(cx, top_y + str_h * 1.5), 4.2, 4.2)
                p.drawEllipse(QPointF(cx, top_y + str_h * 3.5), 4.2, 4.2)

        # 6 Cuerdas (1ª aguda arriba -> 6ª bordona grave abajo)
        for idx, (s_num, s_lbl, open_midi, _) in enumerate(GUITAR_OPEN_STRINGS):
            sy = top_y + idx * str_h
            thickness = 1.1 + idx * 0.42
            str_col = QColor("#E5DCD0") if idx < 3 else QColor("#D4A359")
            p.setPen(QPen(str_col, thickness))
            p.drawLine(QPointF(left_x, sy), QPointF(right_x, sy))

            # Etiqueta de cuerda a la izquierda
            short_lbl = s_lbl.split(" ")[0] + " " + midi_to_note_spec(open_midi).format_name(
                "solfege" if self.notation == "solfege" else "cipher", include_octave=False
            )
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(QColor("#F4EAD5"))
            p.drawText(QRectF(8, sy - 8, left_x - 12, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, short_lbl)

            # Dibujar marcadores de notas (si show_helpers o si es el objetivo/activo)
            for f in range(self.NUM_FRETS + 1):
                cx = left_x + (f + 0.5) * fret_w
                is_target = (self.target_position == (s_num, f))
                is_active = (self.active_position == (s_num, f))
                if is_target or is_active:
                    p.setPen(QPen(QColor("#FFFFFF"), 1.8))
                    p.setBrush(accent_c if is_target else brass_c)
                    p.drawEllipse(QPointF(cx, sy), 9.5, 9.5)
                    p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                    p.setPen(QColor("#FFFFFF"))
                    txt = "?" if is_target and not self.show_helpers else midi_to_note_spec(open_midi + f).format_name(
                        "solfege" if self.notation == "solfege" else "cipher", include_octave=False
                    )
                    p.drawText(QRectF(cx - 14, sy - 8, 28, 16), Qt.AlignmentFlag.AlignCenter, txt)
                elif self.show_helpers:
                    ns = midi_to_note_spec(open_midi + f)
                    if ns.accidental == 0:
                        p.setPen(Qt.PenStyle.NoPen)
                        p.setBrush(QColor(25, 18, 14, 185))
                        p.drawEllipse(QPointF(cx, sy), 7.0, 7.0)
                        p.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
                        p.setPen(QColor("#E6D5B8"))
                        lbl = ns.format_name("solfege" if self.notation == "solfege" else "cipher", include_octave=False)
                        p.drawText(QRectF(cx - 10, sy - 6, 20, 12), Qt.AlignmentFlag.AlignCenter, lbl)

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  4. Diálogo Interactivo del Círculo de Quintas (CircleOfFifthsDialog)
# ─────────────────────────────────────────────────────────────────────────────

class _CircleWheelWidget(QWidget):
    """Rueda vectorial interactiva de las 12 posiciones del Círculo de Quintas."""

    wedge_Clicked = pyqtSignal(int)  # fifths (-6..+6)

    ORDER_FIFTHS = [0, 1, 2, 3, 4, 5, 6, -5, -4, -3, -2, -1]

    def __init__(self, theme: dict[str, str], notation: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(360, 360)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme = theme
        self.notation = notation
        self.selected_fifths: int = 0

    def mousePressEvent(self, event) -> None:  # noqa: N802
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        dx = event.position().x() - cx
        dy = event.position().y() - cy
        dist = math.hypot(dx, dy)
        if dist < 35 or dist > 170:
            return
        ang = (math.degrees(math.atan2(dy, dx)) + 90.0 + 15.0) % 360.0
        idx = int(ang // 30.0) % 12
        self.selected_fifths = self.ORDER_FIFTHS[idx]
        self.update()
        self.wedge_Clicked.emit(self.selected_fifths)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r_outer = min(cx, cy) - 14.0
        r_mid = r_outer * 0.66
        r_inner = r_outer * 0.36

        key_map = {k.fifths: k for k in CIRCLE_OF_FIFTHS}
        accent = QColor(self.theme.get("accent", "#9E2A2B"))
        brass = QColor(self.theme.get("brass", "#B57C1E"))
        paper = QColor(self.theme.get("score_paper", "#FCF8EE"))
        ink = QColor(self.theme.get("score_ink", "#1C1612"))

        for idx, fifths in enumerate(self.ORDER_FIFTHS):
            k = key_map[fifths]
            ang_deg = idx * 30.0 - 90.0
            ang_rad = math.radians(ang_deg)

            is_sel = (fifths == self.selected_fifths)
            # Anillo exterior (Mayor)
            mx = cx + ((r_outer + r_mid) / 2.0) * math.cos(ang_rad)
            my = cy + ((r_outer + r_mid) / 2.0) * math.sin(ang_rad)

            p.setPen(QPen(brass if is_sel else QColor("#B39F7E"), 2.0 if is_sel else 1.2))
            p.setBrush(accent if is_sel else paper)
            p.drawEllipse(QPointF(mx, my), 24, 24)

            maj_lbl = (
                k.major_solfege.replace(" Mayor", "")
                if self.notation == "solfege"
                else k.major_cipher.replace(" Major", "")
            )
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(QColor("#FFFFFF") if is_sel else ink)
            p.drawText(QRectF(mx - 22, my - 11, 44, 22), Qt.AlignmentFlag.AlignCenter, maj_lbl)

            # Anillo interior (Relativa Menor)
            inx = cx + ((r_mid + r_inner) / 2.0) * math.cos(ang_rad)
            iny = cy + ((r_mid + r_inner) / 2.0) * math.sin(ang_rad)
            p.setPen(QPen(brass, 1.2))
            p.setBrush(brass if is_sel else QColor(self.theme.get("score_guide_bg", "#EFE6D0")))
            p.drawEllipse(QPointF(inx, iny), 17, 17)

            min_lbl = (
                k.minor_solfege.replace(" Menor", "m")
                if self.notation == "solfege"
                else k.minor_cipher.replace(" Minor", "m")
            )
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.setPen(QColor("#FFFFFF") if is_sel else ink)
            p.drawText(QRectF(inx - 16, iny - 9, 32, 18), Qt.AlignmentFlag.AlignCenter, min_lbl)

        # Medallón central con alteraciones de la tonalidad seleccionada
        sel_k = key_map.get(self.selected_fifths, CIRCLE_OF_FIFTHS[0])
        p.setPen(QPen(brass, 2.0))
        p.setBrush(paper)
        p.drawEllipse(QPointF(cx, cy), r_inner - 8, r_inner - 8)
        p.setFont(QFont("Georgia", 9, QFont.Weight.Bold))
        p.setPen(ink)
        center_txt = f"{sel_k.major_solfege}\n{sel_k.minor_solfege}\n({abs(sel_k.fifths)} {'♯' if sel_k.fifths > 0 else ('♭' if sel_k.fifths < 0 else '♮')})"
        p.drawText(QRectF(cx - r_inner + 10, cy - r_inner + 10, (r_inner - 10) * 2, (r_inner - 10) * 2), Qt.AlignmentFlag.AlignCenter, center_txt)
        p.end()


class CircleOfFifthsDialog(QDialog):
    """Ventana interactiva del Círculo de Quintas con explicación teórica y escucha de tónica."""

    def __init__(
        self,
        theme: dict[str, str],
        notation: str,
        lang: str,
        on_play_chord: Callable[[list[int]], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.theme = theme
        self.notation = notation
        self.lang = lang
        self.on_play_chord = on_play_chord
        self.setWindowTitle(
            "Círculo de Quintas Interactivo" if lang == "es" else "Interactive Circle of Fifths"
        )
        self.setMinimumSize(460, 510)
        self.setStyleSheet(f"QDialog {{ background-color: {theme['bg_panel']}; color: {theme['text_primary']}; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        title = QLabel(
            "Haz clic en cualquier tonalidad para escuchar su acorde tónico y ver su armadura:"
            if lang == "es"
            else "Click any key on the wheel to hear its tonic triad and inspect its key signature:"
        )
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: 10pt; font-weight: 700; color: {theme['text_primary']};")
        lay.addWidget(title)

        self.wheel = _CircleWheelWidget(theme, notation, self)
        self.wheel.wedge_Clicked.connect(self._on_wedge_selected)
        lay.addWidget(self.wheel, stretch=1)

        self.detail_lbl = QLabel()
        self.detail_lbl.setWordWrap(True)
        self.detail_lbl.setStyleSheet(
            f"background-color: {theme['bg_card']}; border: 1px solid {theme['border_strong']}; "
            f"border-radius: 10px; padding: 10px; font-size: 9.5pt; color: {theme['text_primary']};"
        )
        lay.addWidget(self.detail_lbl)

        self._on_wedge_selected(0, play_audio=False)

    def _on_wedge_selected(self, fifths: int, play_audio: bool = True) -> None:
        key_map = {k.fifths: k for k in CIRCLE_OF_FIFTHS}
        k = key_map.get(fifths, CIRCLE_OF_FIFTHS[0])
        if self.lang == "es":
            self.detail_lbl.setText(
                f"<b>{k.major_solfege} ({k.major_cipher})</b>  •  Relativa: <b>{k.minor_solfege} ({k.minor_cipher})</b><br>"
                f"Armadura: <b>{k.accidental_list_es}</b><br>"
                f"<i>{k.mnemonic_es}</i>"
            )
        else:
            self.detail_lbl.setText(
                f"<b>{k.major_cipher} ({k.major_solfege})</b>  •  Relative: <b>{k.minor_cipher} ({k.minor_solfege})</b><br>"
                f"Signature: <b>{k.accidental_list_en}</b><br>"
                f"<i>{k.mnemonic_en}</i>"
            )
        if play_audio:
            r = k.root_midi
            self.on_play_chord([r, r + 4, r + 7])


# ─────────────────────────────────────────────────────────────────────────────
#  5. Informe Diagnóstico de Sesión (SessionReportDialog)
# ─────────────────────────────────────────────────────────────────────────────

class SessionReportDialog(QDialog):
    """Reporte detallado de rendimiento y diagnóstico pedagógico (inspirado en ReportScreen original)."""

    def __init__(self, curriculum, theme: dict[str, str], lang: str = "es", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(
            "Informe Diagnóstico de Conservatorio" if lang == "es" else "Conservatory Diagnostic Report"
        )
        self.setMinimumSize(520, 440)
        self.setStyleSheet(f"QDialog {{ background-color: {theme['bg_panel']}; color: {theme['text_primary']}; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        weak = curriculum.get_weakest_items(6)
        weak_str = (
            ", ".join(f"{name} (peso {w})" for name, w in weak)
            if weak
            else ("Ninguna — ¡Dominio uniforme en toda la sesión!" if lang == "es" else "None — Uniform mastery across the session!")
        )

        report_lines = [
            "═══════════════════════════════════════════════════════════",
            "   MEDIAHUB MUSICALTRAINER • CONSERVATORY SESSION REPORT" if lang == "en"
            else "   MEDIAHUB MUSICALTRAINER • INFORME DE ESTUDIO MUSICAL",
            "═══════════════════════════════════════════════════════════",
            f"• Ejercicios respondidos / Total Answered : {curriculum.total_answered}",
            f"• Aciertos / Correct Answers              : {curriculum.total_correct}",
            f"• Precisión Global / Accuracy             : {curriculum.accuracy_pct:.1f}%",
            f"• Mejor Racha / Best Streak               : {curriculum.best_streak}",
            f"• Tiempo Medio de Lectura / Avg Speed     : {curriculum.avg_response_ms} ms",
            f"• Notas/Elementos por Reforzar            : {weak_str}",
            "───────────────────────────────────────────────────────────",
            "HISTORIAL RECIENTE / RECENT LOG:",
        ]
        for item in curriculum.history_log[-15:]:
            mark = "OK" if item["result"] == "OK" else "X"
            report_lines.append(f"  [{mark}] ({item['mode'].upper()}) {item['target']}  —  {item['ms']} ms")

        self.text_box = QTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setPlainText("\n".join(report_lines))
        self.text_box.setStyleSheet(
            f"background-color: {theme['score_paper']}; color: {theme['score_ink']}; "
            f"border: 1px solid {theme['score_border']}; border-radius: 10px; padding: 12px; "
            f"font-family: 'Consolas', 'Courier New', monospace; font-size: 9.5pt;"
        )
        lay.addWidget(self.text_box, stretch=1)

        btn_row = QHBoxLayout()
        btn_copy = QPushButton("Copiar Informe" if lang == "es" else "Copy Report")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(
            f"background-color: {theme['accent']}; color: {theme['accent_text']}; "
            f"border: none; border-radius: 8px; padding: 8px 16px; font-weight: 700;"
        )
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(self.text_box.toPlainText()))
        btn_row.addWidget(btn_copy)

        btn_close = QPushButton("Cerrar" if lang == "es" else "Close")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            f"background-color: {theme['bg_card']}; color: {theme['text_primary']}; "
            f"border: 1px solid {theme['border_strong']}; border-radius: 8px; padding: 8px 16px; font-weight: 600;"
        )
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        lay.addLayout(btn_row)
