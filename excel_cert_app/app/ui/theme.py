"""Light/dark theme palettes and the stylesheet template that uses them.

The app ships one QSS *template* (below) with ``{token}`` placeholders, and
two flat colour dictionaries (``LIGHT`` / ``DARK``). Building the final
stylesheet is just ``TEMPLATE.format(**palette)`` — see :func:`stylesheet`.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

# Windows 11 (Fluent/WinUI) button palette — accent buttons use the default
# out-of-box Windows blue; standard buttons match the flat, thin-border
# neutral look of native dialog buttons (e.g. File Explorer's OK/Annuler).
_ACCENT = "#0067C0"
_ACCENT_HOVER = "#1975C6"
_ACCENT_PRESSED = "#005A9E"
_ACCENT_DISABLED_BG = "#CCCCCC"
_ACCENT_DISABLED_TEXT = "#8A8A8A"

_DANGER = "#C42B1C"
_DANGER_HOVER = "#A9241A"
_DANGER_PRESSED = "#8C1D15"

LIGHT: dict[str, str] = {
    "text": "#1f2933",
    "screen_g1": "#0f5aa0", "screen_g2": "#0c3f6e", "screen_g3": "#082b4d",
    "dialog_bg": "#0c3f6e", "dialog_text": "#dfe6ee",
    "title": "#ffffff", "subtitle": "#d6e6f5",
    "brand": "#ffffff", "tagline": "#9db9d6",
    "card_bg": "#ffffff",
    "badge_g1": "#2a8a55", "badge_g2": "#1c6b3f", "badge_text": "#ffffff",
    "card_title": "#0c3c68", "card_subtitle": "#7b8794",
    "field_label": "#52606d",
    "error_bg": "#fdecee", "error_border": "#f5c2c7", "error_text": "#b0121f",
    "input_bg": "#f5f7fa", "input_border": "#cbd2d9", "input_text": "#1f2933",
    "input_hover_border": "#9aa5b1",
    "input_focus_border": _ACCENT, "input_focus_bg": "#ffffff",
    "btn_bg": _ACCENT, "btn_text": "#ffffff",
    "btn_hover": _ACCENT_HOVER, "btn_pressed": _ACCENT_PRESSED,
    "btn_disabled_bg": _ACCENT_DISABLED_BG, "btn_disabled_text": _ACCENT_DISABLED_TEXT,
    "secondary_bg": "#fbfbfb", "secondary_text": "#1b1b1b", "secondary_border": "#d1d1d1",
    "secondary_hover": "#f5f5f5", "secondary_pressed": "#ebebeb",
    "secondary_disabled_bg": "#f5f5f5", "secondary_disabled_text": "#a6a6a6",
    "secondary_disabled_border": "#e5e5e5",
    "adminlink_bg": "rgba(255, 255, 255, 0.10)", "adminlink_text": "#cfe0f0",
    "adminlink_hover": "rgba(255, 255, 255, 0.20)", "adminlink_pressed": "rgba(255, 255, 255, 0.28)",
    "quicktest_bg": "rgba(255, 193, 7, 0.16)", "quicktest_text": "#ffd479",
    "quicktest_hover": "rgba(255, 193, 7, 0.28)", "quicktest_pressed": "rgba(255, 193, 7, 0.36)",
    "danger_bg": _DANGER, "danger_hover": _DANGER_HOVER, "danger_pressed": _DANGER_PRESSED,
    "ghost_text": "#1b1b1b", "ghost_border": "#8a8a8a",
    "ghost_hover_bg": "rgba(0, 0, 0, 0.05)", "ghost_pressed_bg": "rgba(0, 0, 0, 0.08)",
    "themetoggle_bg": "rgba(255, 255, 255, 0.10)", "themetoggle_hover": "rgba(255, 255, 255, 0.20)",
    "panel_bg": "#0c3c68", "panel_border": _ACCENT,
    "panelinfo": "#ffffff",
    "clock": "#ffffff", "clock_low": "#ffd166",
    "statement_scroll_bg": "#ffffff", "statement_text": "#1f2933",
    "scrollbar_handle": "#b7c1cc", "scrollbar_handle_hover": "#9aa5b1",
    "tab_bg": "#14476f", "tab_text": "#cfe0f0",
    "tab_selected_bg": "#ffffff", "tab_selected_text": "#0c3c68",
    "projectcard_bg": "#ffffff", "projectcard_hover_border": _ACCENT,
    "verdict_pass": "#217346", "verdict_fail": "#cf1124",
}

DARK: dict[str, str] = {
    "text": "#e6edf3",
    "screen_g1": "#0b1220", "screen_g2": "#070d16", "screen_g3": "#04070c",
    "dialog_bg": "#111a29", "dialog_text": "#dbe4ee",
    "title": "#ffffff", "subtitle": "#a9bdd4",
    "brand": "#ffffff", "tagline": "#7f97b3",
    "card_bg": "#161f2e",
    "badge_g1": "#2a8a55", "badge_g2": "#1c6b3f", "badge_text": "#ffffff",
    "card_title": "#e6edf3", "card_subtitle": "#93a3b8",
    "field_label": "#93a3b8",
    "error_bg": "#3a1620", "error_border": "#7a3040", "error_text": "#ff8fa3",
    "input_bg": "#0e1622", "input_border": "#2a3a4f", "input_text": "#e6edf3",
    "input_hover_border": "#3f556f",
    "input_focus_border": _ACCENT, "input_focus_bg": "#0e1622",
    "btn_bg": _ACCENT, "btn_text": "#ffffff",
    "btn_hover": _ACCENT_HOVER, "btn_pressed": _ACCENT_PRESSED,
    "btn_disabled_bg": "#3a3a3a", "btn_disabled_text": "#6b6b6b",
    "secondary_bg": "#2b2b2b", "secondary_text": "#e6edf3", "secondary_border": "#3d3d3d",
    "secondary_hover": "#333333", "secondary_pressed": "#252525",
    "secondary_disabled_bg": "#2b2b2b", "secondary_disabled_text": "#6b6b6b",
    "secondary_disabled_border": "#333333",
    "adminlink_bg": "rgba(255, 255, 255, 0.06)", "adminlink_text": "#a9bdd4",
    "adminlink_hover": "rgba(255, 255, 255, 0.14)", "adminlink_pressed": "rgba(255, 255, 255, 0.20)",
    "quicktest_bg": "rgba(255, 193, 7, 0.12)", "quicktest_text": "#ffd479",
    "quicktest_hover": "rgba(255, 193, 7, 0.22)", "quicktest_pressed": "rgba(255, 193, 7, 0.30)",
    "danger_bg": _DANGER, "danger_hover": "#d5372a", "danger_pressed": "#9e2416",
    "ghost_text": "#e6edf3", "ghost_border": "#5a5a5a",
    "ghost_hover_bg": "rgba(255, 255, 255, 0.06)", "ghost_pressed_bg": "rgba(255, 255, 255, 0.10)",
    "themetoggle_bg": "rgba(255, 255, 255, 0.06)", "themetoggle_hover": "rgba(255, 255, 255, 0.14)",
    "panel_bg": "#0e1826", "panel_border": _ACCENT,
    "panelinfo": "#e6edf3",
    "clock": "#ffffff", "clock_low": "#ffd166",
    "statement_scroll_bg": "#0e1622", "statement_text": "#e6edf3",
    "scrollbar_handle": "#33455c", "scrollbar_handle_hover": "#445973",
    "tab_bg": "#0e1826", "tab_text": "#93a3b8",
    "tab_selected_bg": "#161f2e", "tab_selected_text": "#e6edf3",
    "projectcard_bg": "#161f2e", "projectcard_hover_border": _ACCENT,
    "verdict_pass": "#3ddc84", "verdict_fail": "#ff5468",
}

TEMPLATE = """
* {{
    font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", sans-serif;
    color: {text};
}}

QWidget#Screen {{
    background: qlineargradient(x1:0, y1:0, x2:0.6, y2:1,
                                stop:0 {screen_g1}, stop:0.55 {screen_g2},
                                stop:1 {screen_g3});
}}

QDialog, QMessageBox {{
    background: {dialog_bg};
}}
QDialog QLabel, QMessageBox QLabel {{
    color: {dialog_text};
}}

QLabel#Title {{
    color: {title};
    font-size: 28px;
    font-weight: 700;
}}

QLabel#Subtitle {{
    color: {subtitle};
    font-size: 15px;
}}

QLabel#Brand {{
    color: {brand};
    font-size: 19px;
    font-weight: 800;
    letter-spacing: 4px;
}}

QLabel#Tagline {{
    color: {tagline};
    font-size: 7px;
    font-weight: 600;
    letter-spacing: 1px;
}}

QFrame#Card {{
    background: {card_bg};
    border-radius: 18px;
}}

QScrollArea#FormScroll {{
    background: transparent;
    border: none;
}}
QScrollArea#FormScroll > QWidget > QWidget {{ background: transparent; }}
QScrollArea#FormScroll QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 0;
}}
QScrollArea#FormScroll QScrollBar::handle:vertical {{
    background: {scrollbar_handle};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollArea#FormScroll QScrollBar::handle:vertical:hover {{ background: {scrollbar_handle_hover}; }}
QScrollArea#FormScroll QScrollBar::add-line:vertical,
QScrollArea#FormScroll QScrollBar::sub-line:vertical {{ height: 0; }}

QLabel#BrandBadge {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 {badge_g1}, stop:1 {badge_g2});
    color: {badge_text};
    border-radius: 16px;
    font-size: 28px;
    font-weight: 800;
}}

QLabel#CardTitle {{
    font-size: 20px;
    font-weight: 700;
    color: {card_title};
}}

QLabel#CardSubtitle {{
    font-size: 14px;
    color: {card_subtitle};
}}

QLabel#FieldLabel {{
    font-size: 12px;
    font-weight: 700;
    color: {field_label};
    letter-spacing: 0.4px;
}}

QLabel#ErrorBanner {{
    background: {error_bg};
    border: 1px solid {error_border};
    border-radius: 8px;
    color: {error_text};
    font-size: 13px;
    font-weight: 600;
    padding: 10px 12px;
}}

QLineEdit {{
    background: {input_bg};
    border: 1px solid {input_border};
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 15px;
    color: {input_text};
    selection-background-color: {btn_bg};
    selection-color: #ffffff;
}}
QLineEdit:hover  {{ border: 1px solid {input_hover_border}; }}
QLineEdit:focus {{
    border: 2px solid {input_focus_border};
    background: {input_focus_bg};
}}

QComboBox, QDateEdit {{
    background: {input_bg};
    border: 1px solid {input_border};
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 15px;
    color: {input_text};
    selection-background-color: {btn_bg};
    selection-color: #ffffff;
}}
QComboBox:hover, QDateEdit:hover {{ border: 1px solid {input_hover_border}; }}
QComboBox:focus, QDateEdit:focus {{
    border: 2px solid {input_focus_border};
    background: {input_focus_bg};
}}
QComboBox::drop-down, QDateEdit::drop-down {{
    border: none;
    width: 26px;
}}
QComboBox QAbstractItemView {{
    background: {input_bg};
    color: {input_text};
    border: 1px solid {input_border};
    selection-background-color: {btn_bg};
    selection-color: #ffffff;
    outline: none;
}}

QPushButton {{
    background: {btn_bg};
    color: {btn_text};
    border: none;
    border-radius: 3px;
    padding: 7px 14px;
    font-size: 10px;
    font-weight: 600;
}}
QPushButton:hover   {{ background: {btn_hover}; }}
QPushButton:pressed {{ background: {btn_pressed}; }}
QPushButton:disabled {{ background: {btn_disabled_bg}; color: {btn_disabled_text}; }}

QPushButton#Primary {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.3px;
}}

QPushButton#Secondary {{
    background: {secondary_bg};
    color: {secondary_text};
    border: 1px solid {secondary_border};
}}
QPushButton#Secondary:hover    {{ background: {secondary_hover}; }}
QPushButton#Secondary:pressed  {{ background: {secondary_pressed}; }}
QPushButton#Secondary:disabled {{
    background: {secondary_disabled_bg};
    color: {secondary_disabled_text};
    border: 1px solid {secondary_disabled_border};
}}

QPushButton#AdminLink {{
    background: {adminlink_bg};
    color: {adminlink_text};
    font-weight: 600;
    padding: 6px 13px;
    border-radius: 3px;
}}
QPushButton#AdminLink:hover   {{ background: {adminlink_hover}; }}
QPushButton#AdminLink:pressed {{ background: {adminlink_pressed}; }}

QPushButton#QuickTestLink {{
    background: {quicktest_bg};
    color: {quicktest_text};
    font-weight: 600;
    padding: 6px 13px;
    border-radius: 3px;
}}
QPushButton#QuickTestLink:hover   {{ background: {quicktest_hover}; }}
QPushButton#QuickTestLink:pressed {{ background: {quicktest_pressed}; }}

QPushButton#Danger {{
    background: {danger_bg};
}}
QPushButton#Danger:hover   {{ background: {danger_hover}; }}
QPushButton#Danger:pressed {{ background: {danger_pressed}; }}

QPushButton#Ghost {{
    background: transparent;
    color: {ghost_text};
    border: 1px solid {ghost_border};
}}
QPushButton#Ghost:hover    {{ background: {ghost_hover_bg}; }}
QPushButton#Ghost:pressed  {{ background: {ghost_pressed_bg}; }}
QPushButton#Ghost:disabled {{ color: {secondary_disabled_text}; border: 1px solid {secondary_disabled_border}; }}

QPushButton#QuitIcon {{
    background: transparent;
    color: {danger_bg};
    font-size: 14px;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 3px;
}}
QPushButton#QuitIcon:hover   {{ background: {danger_bg}; color: #ffffff; }}
QPushButton#QuitIcon:pressed {{ background: {danger_pressed}; color: #ffffff; }}

QPushButton#ThemeToggle {{
    background: {themetoggle_bg};
    color: {text};
    font-weight: 600;
    padding: 6px 10px;
    border-radius: 3px;
}}
QPushButton#ThemeToggle:hover {{ background: {themetoggle_hover}; }}

QPushButton#PanelHandle {{
    background: {btn_bg};
    color: {btn_text};
    font-size: 11px;
    font-weight: 700;
    padding: 6px 16px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}}
QPushButton#PanelHandle:hover {{ background: {btn_hover}; }}

/* ---- System check screen ---- */
QLabel#StatusOk {{ color: {verdict_pass}; font-weight: 700; }}
QLabel#StatusBad {{ color: {verdict_fail}; font-weight: 700; }}
QLabel#StatusUnknown {{ color: {field_label}; font-weight: 700; }}
QProgressBar {{
    background: {input_bg};
    border: none;
    border-radius: 3px;
}}
QProgressBar::chunk {{
    background: {btn_bg};
    border-radius: 3px;
}}

/* ---- Bottom exam task panel ---- */
QFrame#TaskPanel {{
    background: {panel_bg};
    border-top: 3px solid {panel_border};
}}
QLabel#PanelInfo {{
    color: {panelinfo};
    font-size: 14px;
    font-weight: 700;
}}
QLabel#Clock {{
    color: {clock};
    font-size: 20px;
    font-weight: 800;
    font-family: "DejaVu Sans Mono", monospace;
}}
QLabel#ClockLow {{ color: {clock_low}; }}
QScrollArea#StatementScroll {{
    background: {statement_scroll_bg};
    border-radius: 8px;
}}
QScrollArea#StatementScroll > QWidget > QWidget {{ background: transparent; }}
QLabel#Statement {{
    background: transparent;
    color: {statement_text};
    padding: 12px 14px;
    font-size: 14px;
}}
QScrollArea#StatementScroll QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 0;
}}
QScrollArea#StatementScroll QScrollBar::handle:vertical {{
    background: {scrollbar_handle};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollArea#StatementScroll QScrollBar::handle:vertical:hover {{ background: {scrollbar_handle_hover}; }}
QScrollArea#StatementScroll QScrollBar::add-line:vertical,
QScrollArea#StatementScroll QScrollBar::sub-line:vertical {{ height: 0; }}
QTabBar::tab {{
    background: {tab_bg};
    color: {tab_text};
    padding: 7px 14px;
    margin-right: 3px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}}
QTabBar::tab:selected {{ background: {tab_selected_bg}; color: {tab_selected_text}; }}

/* ---- Review board cards ---- */
QFrame#ProjectCard {{
    background: {projectcard_bg};
    border-radius: 12px;
    border: 2px solid transparent;
}}
QFrame#ProjectCard:hover {{ border: 2px solid {projectcard_hover_border}; }}

/* ---- Results ---- */
QLabel#ScoreBig {{
    font-size: 64px;
    font-weight: 800;
}}
QLabel#VerdictPass {{ color: {verdict_pass}; font-size: 28px; font-weight: 800; }}
QLabel#VerdictFail {{ color: {verdict_fail}; font-size: 28px; font-weight: 800; }}
"""


def stylesheet(mode: str) -> str:
    palette = DARK if mode == "dark" else LIGHT
    return TEMPLATE.format(**palette)


def system_default_mode() -> str:
    """Best-effort read of the OS light/dark preference; light if unknown."""
    try:
        hints = QGuiApplication.styleHints()
        scheme = hints.colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
        if scheme == Qt.ColorScheme.Light:
            return "light"
    except Exception:
        pass
    return "light"


def apply_theme(app: QApplication, mode: str) -> None:
    app.setStyleSheet(stylesheet(mode))
