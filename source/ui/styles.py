"""
styles.py
Dark-theme Qt stylesheet for VMT (Versatile Media Toolkit) — "Studio Obsidian & Cyber Mint" Design System.
Inspired by pro audio/video workstations with hardware acceleration telemetry.
"""

# ── Color palette (Studio Obsidian & Cyber Mint) ─────────────────────────────
COLORS = {
    "bg_dark":      "#080C0E",  # App background (Ultra-deep obsidian black)
    "bg_base":      "#0B1014",  # Workspace base surface
    "bg_card":      "#10171D",  # Card / panel container
    "bg_card_alt":  "#152028",  # Elevated cards / active items
    "bg_input":     "#0D1318",  # Input fields / drop zones
    "bg_hover":     "#1C2B36",  # Hover state
    "border":       "#18252E",  # Subtle 1px borders
    "border_focus": "#2FE69A",  # Focus border / neon mint outline
    "border_card":  "#1D2D38",  # Card boundary outline
    "accent":       "#2FE69A",  # Primary Accent (Cyber Mint / Emerald Neon)
    "accent_dark":  "#1E9E68",  # Primary Dark / Pressed
    "accent_light": "#67F5BA",  # Primary Light / Dim
    "accent_glow":  "rgba(47, 230, 154, 0.15)", # Accent glow fill
    "success":      "#2FE69A",  # Success Mint
    "warning":      "#FBBF24",  # Warning Amber
    "error":        "#F87171",  # Error Coral Red
    "text_primary": "#F1F5F9",  # High contrast text (Primary)
    "text_muted":   "#8497A3",  # Secondary text (Metadata & labels)
    "text_dim":     "#4C616E",  # Muted text (Placeholders & subtle tags)
    "sidebar_bg":   "#090D10",  # Sidebar background
    "sidebar_sel":  "#152028",  # Sidebar selected nav background
    "progress_bg":  "#10181F",  # Progress bar background track
    "progress_fg":  "#2FE69A",  # Progress bar fill color
}

C = COLORS


STYLESHEET = f"""
/* ── Global ──────────────────────────────────────────────────── */
QWidget {{
    background-color: {C['bg_base']};
    color: {C['text_primary']};
    font-family: "Segoe UI", "Inter", -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: {C['accent']};
    selection-color: #080C0E;
}}

QMainWindow {{
    background-color: {C['bg_dark']};
}}

/* ── Labels ──────────────────────────────────────────────────── */
QLabel {{
    background: transparent;
    color: {C['text_primary']};
}}
QLabel[class="muted"] {{
    color: {C['text_muted']};
    font-size: 12px;
}}
QLabel[class="dim"] {{
    color: {C['text_dim']};
    font-size: 11px;
}}
QLabel[class="title"] {{
    font-size: 20px;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -0.3px;
}}
QLabel[class="section-title"] {{
    font-size: 11px;
    font-weight: 700;
    color: {C['text_muted']};
    text-transform: uppercase;
    letter-spacing: 1.2px;
}}
QLabel[class="error"] {{
    color: {C['error']};
}}
QLabel[class="success"] {{
    color: {C['success']};
}}

/* ── Buttons ─────────────────────────────────────────────────── */
QPushButton {{
    background-color: {C['bg_card']};
    color: {C['text_primary']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {C['bg_hover']};
    border-color: {C['accent']};
    color: #FFFFFF;
}}
QPushButton:pressed {{
    background-color: {C['accent_dark']};
    color: #080C0E;
}}
QPushButton:disabled {{
    color: {C['text_dim']};
    border-color: {C['border']};
    background-color: {C['bg_input']};
}}

QPushButton[class="primary"] {{
    background-color: {C['accent']};
    color: #080C0E;
    border: 1px solid {C['accent']};
    font-size: 13px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 6px;
    letter-spacing: 0.3px;
}}
QPushButton[class="primary"]:hover {{
    background-color: {C['accent_light']};
    border-color: {C['accent_light']};
}}
QPushButton[class="primary"]:pressed {{
    background-color: {C['accent_dark']};
}}
QPushButton[class="primary"]:disabled {{
    background-color: {C['bg_hover']};
    border-color: {C['border']};
    color: {C['text_dim']};
}}

QPushButton[class="outline-accent"] {{
    background-color: {C['bg_card']};
    color: {C['accent']};
    border: 1px solid {C['accent']};
    font-size: 12px;
    font-weight: 700;
    padding: 8px 16px;
    border-radius: 6px;
    letter-spacing: 0.5px;
}}
QPushButton[class="outline-accent"]:hover {{
    background-color: {C['accent']};
    color: #080C0E;
}}

QPushButton[class="danger"] {{
    background-color: transparent;
    color: {C['error']};
    border: 1px solid {C['error']};
    border-radius: 6px;
}}
QPushButton[class="danger"]:hover {{
    background-color: {C['error']};
    color: #FFFFFF;
}}

QPushButton[class="ghost"] {{
    background: transparent;
    border: none;
    color: {C['text_muted']};
    padding: 4px 8px;
}}
QPushButton[class="ghost"]:hover {{
    color: {C['text_primary']};
    background: {C['bg_card']};
    border-radius: 6px;
}}

QPushButton[class="success"] {{
    background-color: {C['success']};
    color: #080C0E;
    border: none;
    font-size: 13px;
    font-weight: 700;
    padding: 10px 24px;
    border-radius: 6px;
}}
QPushButton[class="success"]:hover {{
    background-color: {C['accent_light']};
}}

/* ── Sidebar nav buttons ─────────────────────────────────────── */
QPushButton[class="nav"] {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: {C['text_muted']};
    text-align: left;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton[class="nav"]:hover {{
    background-color: {C['bg_hover']};
    border-color: {C['border']};
    color: #FFFFFF;
}}
QPushButton[class="nav-active"] {{
    background-color: {C['bg_card_alt']};
    border: 1px solid {C['border_card']};
    border-left: 3px solid {C['accent']};
    border-radius: 6px;
    color: {C['accent']};
    text-align: left;
    padding: 10px 14px;
    font-size: 13px;
    font-weight: 700;
}}

/* ── ComboBox ────────────────────────────────────────────────── */
QComboBox {{
    background-color: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 7px 12px;
    color: {C['text_primary']};
    min-width: 120px;
    font-weight: 500;
}}
QComboBox:hover {{
    border-color: {C['border_card']};
    background-color: {C['bg_card']};
}}
QComboBox:focus {{
    border-color: {C['accent']};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {C['text_muted']};
}}
QComboBox QAbstractItemView {{
    background-color: {C['bg_card']};
    border: 1px solid {C['border_card']};
    border-radius: 6px;
    color: {C['text_primary']};
    selection-background-color: {C['accent']};
    selection-color: #080C0E;
    outline: none;
    padding: 4px;
}}

/* ── LineEdit ────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 7px 12px;
    color: {C['text_primary']};
}}
QLineEdit:hover {{
    border-color: {C['border_card']};
}}
QLineEdit:focus {{
    border-color: {C['accent']};
}}
QLineEdit:disabled {{
    color: {C['text_dim']};
    background-color: {C['bg_dark']};
}}

/* ── SpinBox ─────────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background-color: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 7px 12px;
    color: {C['text_primary']};
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {C['accent']};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: {C['bg_card']};
    border: none;
    border-radius: 3px;
    width: 20px;
}}

/* ── CheckBox ────────────────────────────────────────────────── */
QCheckBox {{
    color: {C['text_primary']};
    spacing: 8px;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {C['border_card']};
    background-color: {C['bg_input']};
}}
QCheckBox::indicator:hover {{
    border-color: {C['accent']};
}}
QCheckBox::indicator:checked {{
    background-color: {C['accent']};
    border-color: {C['accent']};
    image: none;
}}

/* ── RadioButton ─────────────────────────────────────────────── */
QRadioButton {{
    color: {C['text_primary']};
    spacing: 8px;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid {C['border_card']};
    background-color: {C['bg_input']};
}}
QRadioButton::indicator:hover {{
    border-color: {C['accent']};
}}
QRadioButton::indicator:checked {{
    background-color: {C['accent']};
    border-color: {C['accent']};
}}

/* ── Slider ──────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background: {C['bg_input']};
    height: 6px;
    border-radius: 3px;
    border: 1px solid {C['border']};
}}
QSlider::sub-page:horizontal {{
    background: {C['accent']};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 2px solid {C['accent']};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {C['accent_light']};
}}

/* ── Progress Bar ────────────────────────────────────────────── */
QProgressBar {{
    background-color: {C['progress_bg']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    text-align: center;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 700;
    height: 16px;
}}
QProgressBar::chunk {{
    background-color: {C['progress_fg']};
    border-radius: 3px;
}}
QProgressBar[class="thin"] {{
    height: 5px;
    border: none;
    border-radius: 2px;
    background-color: {C['progress_bg']};
}}
QProgressBar[class="thin"]::chunk {{
    background-color: {C['accent']};
    border-radius: 2px;
}}

/* ── Scrollbars ──────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {C['bg_dark']};
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {C['border_card']};
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C['accent_dark']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {C['bg_dark']};
    height: 8px;
    margin: 0;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {C['border_card']};
    min-width: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {C['accent_dark']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Cards and Frames ────────────────────────────────────────── */
QFrame[class="card"] {{
    background-color: {C['bg_card']};
    border: 1px solid {C['border_card']};
    border-radius: 8px;
}}
QFrame[class="card-alt"] {{
    background-color: {C['bg_card_alt']};
    border: 1px solid {C['border_card']};
    border-radius: 8px;
}}
QFrame[class="hero-telemetry"] {{
    background-color: #0B1419;
    border: 1px solid #192D38;
    border-radius: 8px;
}}
QFrame[class="telemetry-badge"] {{
    background-color: #0E1A22;
    border: 1px solid #1E3744;
    border-radius: 6px;
}}

/* ── TabWidget / Stack ───────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {C['border']};
    border-radius: 6px;
    background-color: {C['bg_base']};
}}
QTabBar::tab {{
    background: {C['bg_card']};
    color: {C['text_muted']};
    padding: 8px 16px;
    border: 1px solid {C['border']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {C['bg_base']};
    color: {C['accent']};
    border-bottom: 2px solid {C['accent']};
    font-weight: 700;
}}
QTabBar::tab:hover:!selected {{
    background: {C['bg_hover']};
    color: {C['text_primary']};
}}

/* ── ToolTip ─────────────────────────────────────────────────── */
QToolTip {{
    background-color: {C['bg_card']};
    color: {C['text_primary']};
    border: 1px solid {C['accent']};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ── Splitter ────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {C['border']};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
"""


def apply(app) -> None:
    """Apply the Studio Obsidian & Cyber Mint stylesheet to the QApplication."""
    app.setStyleSheet(STYLESHEET)
