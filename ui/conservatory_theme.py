"""
ui/conservatory_theme.py
────────────────────────
Sistema de identidad visual tipo "Conservatorio & Taller de Luthier" para MusicalTrainer.
Evita las plantillas oscuras genéricas con gradientes neón y ofrece 3 ambientes táctiles:
  1. 'parchment' — Partitura Urtext & Nogal (papel crema de manuscrito, madera de nogal, latón y carmesí).
  2. 'steinway'  — Steinway Nocturno (ébano de cola de concierto, bronce cepillado, fieltro rojo y marfil).
  3. 'luthier'   — Luthier Sunburst (caoba tostada, tapa de abeto cálido, cobre y nácar turquesa).
"""

from __future__ import annotations

THEMES: dict[str, dict[str, str]] = {
    "parchment": {
        "id": "parchment",
        "name_es": "🎼 Partitura Clásica",
        "name_en": "🎼 Classical Score",
        "bg_window": "#EAE1CF",
        "bg_masthead": "#241913",
        "text_masthead": "#F9F4E8",
        "text_masthead_sub": "#D1C0A5",
        "bg_panel": "#F5EFE1",
        "bg_card": "#FBF8F1",
        "bg_card_hover": "#FFFDF8",
        "bg_subtle": "#E4D9C3",
        "score_paper": "#FCF8EE",
        "score_paper_inner": "#F7F0DE",
        "score_border": "#C5B496",
        "score_ink": "#1C1612",
        "score_line": "#5A4938",
        "score_guide_bg": "#EFE6D0",
        "score_guide_fg": "#6D563E",
        "text_primary": "#1E1712",
        "text_secondary": "#544537",
        "text_muted": "#82705D",
        "border": "#D3C5AC",
        "border_strong": "#B39F7E",
        "accent": "#9E2A2B",         # Carmesí batuta / fieltro de piano
        "accent_hover": "#7E1F20",
        "accent_soft": "#F7E3E1",
        "accent_text": "#FFFFFF",
        "brass": "#B57C1E",          # Latón / herraje de conservatorio
        "brass_soft": "#F6EBD3",
        "success": "#1E6B43",
        "success_soft": "#DCF3E5",
        "error": "#B42318",
        "error_soft": "#FCE4E2",
        "piano_wood": "#2B1C14",
        "piano_felt": "#9E2225",
        "piano_white": "#FCF9F2",
        "piano_white_hover": "#F3E8D2",
        "piano_black": "#1E1916",
        "fret_wood": "#3B2316",
        "fret_wire": "#C59B52",
    },
    "steinway": {
        "id": "steinway",
        "name_es": "🎹 Steinway Nocturno",
        "name_en": "🎹 Steinway Nocturne",
        "bg_window": "#12100E",
        "bg_masthead": "#191512",
        "text_masthead": "#F6EFE2",
        "text_masthead_sub": "#BFA98B",
        "bg_panel": "#1B1714",
        "bg_card": "#231E1A",
        "bg_card_hover": "#2C2621",
        "bg_subtle": "#2A241E",
        "score_paper": "#F6EFE0",    # La hoja de partitura mantiene papel cálido legible bajo luz de atril
        "score_paper_inner": "#EFE6D2",
        "score_border": "#8F734C",
        "score_ink": "#18130F",
        "score_line": "#4F3F2F",
        "score_guide_bg": "#E6DBC4",
        "score_guide_fg": "#5A4531",
        "text_primary": "#F4EDE2",
        "text_secondary": "#C4B5A2",
        "text_muted": "#877867",
        "border": "#332B24",
        "border_strong": "#524335",
        "accent": "#D4A359",         # Bronce de concierto
        "accent_hover": "#E2B56E",
        "accent_soft": "#33281A",
        "accent_text": "#14100C",
        "brass": "#E09F3E",
        "brass_soft": "#302313",
        "success": "#22C55E",
        "success_soft": "#112D1E",
        "error": "#F87171",
        "error_soft": "#361717",
        "piano_wood": "#1A130F",
        "piano_felt": "#A62629",
        "piano_white": "#FAF6ED",
        "piano_white_hover": "#EFE4CD",
        "piano_black": "#161311",
        "fret_wood": "#2D1B12",
        "fret_wire": "#D4A359",
    },
    "luthier": {
        "id": "luthier",
        "name_es": "🎸 Luthier Sunburst",
        "name_en": "🎸 Luthier Sunburst",
        "bg_window": "#1C130F",
        "bg_masthead": "#271812",
        "text_masthead": "#F9EFE3",
        "text_masthead_sub": "#D7B494",
        "bg_panel": "#241813",
        "bg_card": "#2F2019",
        "bg_card_hover": "#3A281F",
        "bg_subtle": "#36251C",
        "score_paper": "#F8F1E1",
        "score_paper_inner": "#F1E7D0",
        "score_border": "#A87B51",
        "score_ink": "#211610",
        "score_line": "#5C4433",
        "score_guide_bg": "#E9DEC6",
        "score_guide_fg": "#664A34",
        "text_primary": "#FAF0E4",
        "text_secondary": "#D6BFA9",
        "text_muted": "#9B8068",
        "border": "#422E23",
        "border_strong": "#664736",
        "accent": "#D96B27",         # Ámbar sunburst / cobre acústico
        "accent_hover": "#E87F3D",
        "accent_soft": "#3D2112",
        "accent_text": "#FFFFFF",
        "brass": "#2A9D8F",          # Incrustación de nácar turquesa
        "brass_soft": "#132E2B",
        "success": "#34D399",
        "success_soft": "#123025",
        "error": "#FB7185",
        "error_soft": "#3B1720",
        "piano_wood": "#291811",
        "piano_felt": "#B53028",
        "piano_white": "#FBF7EE",
        "piano_white_hover": "#F0E3CA",
        "piano_black": "#1A1411",
        "fret_wood": "#3F2417",
        "fret_wire": "#D6A15C",
    },
}


def build_conservatory_stylesheet(t: dict[str, str]) -> str:
    """Construye la hoja de estilos QSS para el tema de Conservatorio seleccionado."""
    return f"""
        QMainWindow, QWidget#rootWidget {{
            background-color: {t['bg_window']};
            color: {t['text_primary']};
            font-family: "Georgia", "Segoe UI Variable Display", "Segoe UI", serif;
        }}
        QLabel {{
            background: transparent;
            color: {t['text_primary']};
            font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
        }}
        QFrame#mastheadBar {{
            background-color: {t['bg_masthead']};
            border: 1px solid {t['border_strong']};
            border-radius: 14px;
        }}
        QFrame#disciplineRail {{
            background-color: {t['bg_panel']};
            border: 1px solid {t['border']};
            border-radius: 14px;
        }}
        QFrame#stagePanel {{
            background-color: {t['bg_panel']};
            border: 1px solid {t['border']};
            border-radius: 16px;
        }}
        QFrame#instrumentDock {{
            background-color: {t['bg_panel']};
            border: 1px solid {t['border']};
            border-radius: 16px;
        }}
        QFrame#statBadge {{
            background-color: {t['bg_card']};
            border: 1px solid {t['border']};
            border-radius: 10px;
        }}
        QFrame#feedbackBanner {{
            background-color: {t['bg_card']};
            border: 1px solid {t['border_strong']};
            border-radius: 11px;
        }}
        QComboBox {{
            background-color: {t['bg_card']};
            color: {t['text_primary']};
            border: 1px solid {t['border_strong']};
            border-radius: 8px;
            padding: 4px 10px;
            font-family: "Segoe UI", sans-serif;
            font-size: 9.5pt;
            font-weight: 600;
        }}
        QComboBox:hover {{
            border: 1px solid {t['accent']};
        }}
        QComboBox::drop-down {{
            border: none;
            padding-right: 6px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {t['bg_card']};
            color: {t['text_primary']};
            border: 1px solid {t['border_strong']};
            selection-background-color: {t['accent']};
            selection-color: {t['accent_text']};
            padding: 4px;
        }}
        QSpinBox {{
            background-color: {t['bg_card']};
            color: {t['text_primary']};
            border: 1px solid {t['border_strong']};
            border-radius: 8px;
            padding: 3px 8px;
            font-family: "Segoe UI", sans-serif;
            font-size: 9.5pt;
            font-weight: 700;
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 8px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {t['border_strong']};
            min-height: 28px;
            border-radius: 4px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """
