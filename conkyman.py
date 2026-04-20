#!/usr/bin/env python3
"""
ConkyMan — PySide6
Sidebar + QStackedWidget. UI nativa Qt con QSS Catppuccin Mocha.
Pestañas: Apariencia, Colores, Sistema, Ajustes, Perfiles, Estado, Herramientas
"""
import os, re, subprocess, configparser, sys, shutil, json, signal
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QRadioButton, QButtonGroup,
    QCheckBox, QComboBox, QColorDialog, QFontDialog, QMessageBox,
    QDialog, QDialogButtonBox, QScrollArea, QFrame, QGridLayout,
    QSizePolicy, QLayout, QSlider, QSpinBox, QLineEdit, QFileDialog,
    QTextEdit, QListWidget, QListWidgetItem, QInputDialog,
)
from PySide6.QtGui  import QIcon, QColor, QFont, QPixmap, QDesktopServices
from PySide6.QtCore import Qt, QThread, Signal, QObject, QSize, QUrl, QTimer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translations import Translator, set_language as set_global_lang

# ─────────────────────────────────────────────────────────────
# Plantillas Conky
# ─────────────────────────────────────────────────────────────
DEFAULT_CONKY_LUA = r"""conky.config = {
    out_to_wayland = true, out_to_x = true,
    own_window = true, own_window_class = 'Conky', own_window_type = 'dock',
    own_window_transparent = true, own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'undecorated,below,sticky,skip_taskbar,skip_pager',
    xinerama_head = 0, alignment = 'top_right', gap_x = 20, gap_y = 40,
    minimum_width = 200, minimum_height = 300,
    use_xft = true, font = 'Roboto:size=10',
    default_color = 'F5F5F5', color1 = 'E0E0E0', color2 = '8AA34F',
    update_interval = 1.0, double_buffer = true,
    draw_shades = false, draw_outline = false, draw_borders = false,
    draw_graph_borders = true, cpu_avg_samples = 2, net_avg_samples = 2,
    override_utf8_locale = true, format_human_readable = true,
}
conky.text = [[
${voffset -20}${font Roboto:weight=Normal:size=85}${color1}${time %H}${font}
${voffset -40}${offset 75}${font Roboto Condensed:weight=Medium:size=80}${color2}${time %M}${font}
${font Roboto Condensed:size=14}${color}${time %a, %d %b %Y}${font}
${font Roboto Condensed:size=12}${color}
Disk: ${color2}${fs_used_perc /}%${color} ${diskiograph 10,20 5B8080 8AA34F}${color}  RAM: ${color2}${memperc}%${color} ${memgraph 10,20 5B8080 8AA34F}${color}
${offset 50}CPU: ${color2}${cpu}%${color} ${cpugraph 10,20 5B8080 8AA34F}${color}
]]"""

MINIMAL_CONKY_LUA = r"""conky.config = {
    out_to_wayland = true, out_to_x = true,
    own_window = true, own_window_class = 'Conky', own_window_type = 'dock',
    own_window_transparent = true, own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'undecorated,below,sticky,skip_taskbar,skip_pager',
    xinerama_head = 0, alignment = 'top_right', gap_x = 20, gap_y = 40,
    minimum_width = 200, minimum_height = 300,
    use_xft = true, font = 'Roboto:size=10',
    default_color = 'F5F5F5', color1 = 'E0E0E0', color2 = '8AA34F',
    update_interval = 1.0, double_buffer = true,
    draw_shades = false, draw_outline = false, draw_borders = false,
    draw_graph_borders = true, cpu_avg_samples = 2, net_avg_samples = 2,
    override_utf8_locale = true, format_human_readable = true,
}
conky.text = [[
${voffset -20}${font Roboto:weight=Normal:size=85}${color1}${time %H}${font}
${voffset -40}${offset 75}${font Roboto Condensed:weight=Medium:size=80}${color2}${time %M}${font}
${font Roboto Condensed:size=14}${color}${time %a, %d %b %Y}${font}
]]"""

AUTOSTART_DESKTOP = """[Desktop Entry]
Type=Application
Name=Conky
Exec=conky -c {conky_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""

LANG_FLAGS = {'es':'ES Español','en':'EN English','pt':'PT Português','ca':'CA Català','ja':'JA 日本語','tr':'TR Türkçe','de':'DE Deutsche','zh':'ZH 汉语','ko':'KO 한국어','it':'IT Italiano','fr':'FR Française'}

COLORS_DATA = {
    "light": {
        "Mentolado":"#27AE60","Verde MATE":"#87A556","Menta":"#6F4E37",
        "Gato Verde":"#32CD32","Azul":"#2980B9","Rojo":"#C0392B",
        "Naranja":"#D35400","Amarillo":"#F1C40F","Purpura":"#8E44AD",
        "Turquesa":"#16A085","Rosa":"#E91E63","Indigo":"#3F51B5","Ambar":"#FF6F00",
    },
    "dark": {
        "Mentolado":"#8AA34F","Verde MATE":"#9DB76F","Cafe Menta":"#98D8C8",
        "Gato Verde":"#7FFF00","Azul":"#5DADE2","Rojo":"#E74C3C",
        "Naranja":"#E67E22","Amarillo":"#F4D03F","Purpura":"#BB8FCE",
        "Turquesa":"#48C9B0","Rosa":"#F48FB1","Indigo":"#7986CB","Ambar":"#FFB74D",
    },
}

def _safe(name): return re.sub(r'[^a-z0-9]', '_', name.lower())

# ─────────────────────────────────────────────────────────────
# QSS — Adwaita Dark
# Paleta de referencia:
#   base:      #242424   surface:   #2d2d2d   card:      #383838
#   border:    #4a4a4a   border2:   #5c5c5c
#   fg:        #ebebeb   fg2:       #c0c0c0   fg_dim:    #808080
#   accent:    #3584e4   acc_hover: #4a90d9   acc_press: #2870c8
#   success:   #57e389   error:     #ff7b63   warning:   #f8c762
# ─────────────────────────────────────────────────────────────
QSS = """
* { font-family: cantarell, sans-serif; font-size: 13px; outline: none; }
QMainWindow { background: #242424; }
QWidget      { background: #242424; color: #ebebeb; }

/* Elimina el subrayado que Fusion dibuja bajo widgets interactivos */
QPushButton  { border: 1px solid transparent; }
QRadioButton { border: none; }
QCheckBox    { border: none; }
QLabel       { border: none; background: transparent; }

/* ── Sidebar ─────────────────────────────────────────────── */
QWidget#sidebar {
    background: #2d2d2d;
    border-right: 1px solid #4a4a4a;
}
QPushButton#nav_btn {
    background: transparent;
    color: #c0c0c0;
    border: none;
    border-radius: 6px;
    padding: 9px 14px;
    text-align: left;
    font-size: 13px;
}
QPushButton#nav_btn:hover   { background: #383838; color: #ebebeb; }
QPushButton#nav_btn:checked {
    background: #3584e4;
    color: #ffffff;
    font-weight: bold;
}

/* ── Topbar ──────────────────────────────────────────────── */
QWidget#topbar {
    background: #2d2d2d;
    border-bottom: 1px solid #4a4a4a;
}

/* ── Secciones (cards) ───────────────────────────────────── */
QFrame#section {
    background: #2d2d2d;
    border: 1px solid #4a4a4a;
    border-radius: 8px;
}
QLabel#sec_title  { color: #ebebeb; font-size: 13px; font-weight: bold; }
QLabel#sec_sub    { color: #808080; font-size: 12px; }
QLabel#ver_lbl    { color: #606060; font-size: 11px; }
QLabel#status_ok  { color: #57e389; font-size: 12px; font-weight: bold; }
QLabel#status_err { color: #ff7b63; font-size: 12px; font-weight: bold; }
QLabel#mono       { font-family: monospace; font-size: 11px; color: #a0a0a0; }

/* ── Controles de selección ──────────────────────────────── */
QRadioButton {
    color: #ebebeb; spacing: 6px; font-size: 13px; background: transparent;
}
QRadioButton::indicator {
    width: 16px; height: 16px; border-radius: 8px;
    border: 2px solid #5c5c5c; background: #383838;
}
QRadioButton::indicator:checked {
    background: #3584e4; border-color: #3584e4;
    image: none;
}
QRadioButton:hover { color: #4a90d9; }

QCheckBox { color: #ebebeb; font-size: 13px; spacing: 6px; background: transparent; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 2px solid #5c5c5c; background: #383838;
}
QCheckBox::indicator:checked { background: #3584e4; border-color: #3584e4; }

/* ── ComboBox ────────────────────────────────────────────── */
QComboBox {
    background: #383838; color: #ebebeb;
    border: 1px solid #5c5c5c; border-radius: 6px;
    padding: 4px 10px; min-width: 120px;
}
QComboBox:hover   { border-color: #7a7a7a; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #383838; color: #ebebeb;
    selection-background-color: #3584e4;
    border: 1px solid #5c5c5c;
}

/* ── Slider ──────────────────────────────────────────────── */
QSlider::groove:horizontal {
    height: 4px; background: #4a4a4a; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #3584e4; width: 16px; height: 16px;
    margin: -6px 0; border-radius: 8px; border: 2px solid #2870c8;
}
QSlider::sub-page:horizontal { background: #3584e4; border-radius: 2px; }

/* ── SpinBox ─────────────────────────────────────────────── */
QSpinBox {
    background: #383838; color: #ebebeb;
    border: 1px solid #5c5c5c; border-radius: 6px;
    padding: 4px 8px; min-width: 72px;
}
QSpinBox:focus { border-color: #3584e4; }
QSpinBox::up-button, QSpinBox::down-button {
    width: 18px; background: #4a4a4a; border-radius: 3px;
}

/* ── LineEdit ────────────────────────────────────────────── */
QLineEdit {
    background: #383838; color: #ebebeb;
    border: 1px solid #5c5c5c; border-radius: 6px;
    padding: 5px 10px;
}
QLineEdit:focus { border-color: #3584e4; }

/* ── TextEdit ────────────────────────────────────────────── */
QTextEdit {
    background: #1c1c1c; color: #c0c0c0;
    border: 1px solid #4a4a4a; border-radius: 6px;
    font-family: monospace; font-size: 11px; padding: 8px;
}

/* ── ListWidget ──────────────────────────────────────────── */
QListWidget {
    background: #2d2d2d; color: #ebebeb;
    border: 1px solid #4a4a4a; border-radius: 8px;
    outline: none;
}
QListWidget::item { padding: 9px 14px; border-radius: 5px; }
QListWidget::item:selected { background: #3584e4; color: #ffffff; }
QListWidget::item:hover    { background: #383838; }

/* ── Botones de toolbar ──────────────────────────────────── */
QPushButton#tool_btn {
    background: transparent; color: #c0c0c0;
    border: none; border-radius: 6px; padding: 6px 10px;
}
QPushButton#tool_btn:hover   { background: #383838; color: #ebebeb; }
QPushButton#tool_btn:pressed { background: #4a4a4a; }

/* ── Botón estándar ──────────────────────────────────────── */
QPushButton#action_btn {
    background: #383838; color: #ebebeb;
    border: 1px solid #5c5c5c; border-radius: 6px;
    padding: 6px 16px;
}
QPushButton#action_btn:hover   { background: #444444; border-color: #7a7a7a; }
QPushButton#action_btn:pressed { background: #2d2d2d; }
QPushButton#action_btn:disabled{ background: #2d2d2d; color: #606060; border-color: #404040; }

/* ── Botón destructivo ───────────────────────────────────── */
QPushButton#danger_btn {
    background: #3d1a1a; color: #ff7b63;
    border: 1px solid #6b2b2b; border-radius: 6px;
    padding: 6px 16px;
}
QPushButton#danger_btn:hover   { background: #4e2020; border-color: #8b3535; }
QPushButton#danger_btn:pressed { background: #2d1010; }

/* ── Botón Aplicar (sugerido) ────────────────────────────── */
QPushButton#apply_btn {
    background: #3584e4; color: #ffffff;
    border: none; border-radius: 6px;
    padding: 10px 28px; font-size: 13px; font-weight: bold;
}
QPushButton#apply_btn:hover    { background: #4a90d9; }
QPushButton#apply_btn:pressed  { background: #2870c8; }
QPushButton#apply_btn:disabled { background: #383838; color: #606060; }

/* ── ScrollBar ───────────────────────────────────────────── */
QScrollBar:vertical {
    background: #242424; width: 8px; border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #5c5c5c; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover  { background: #7a7a7a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollArea { border: none; }
QScrollArea > QWidget > QWidget { background: #242424; }

/* ── Separadores ─────────────────────────────────────────── */
QFrame#hsep { background: #4a4a4a; max-height: 1px; border: none; }
QFrame#vsep { background: #4a4a4a; max-width:  1px; border: none; }
"""

# ─────────────────────────────────────────────────────────────
# Worker thread
# ─────────────────────────────────────────────────────────────
class Worker(QObject):
    done = Signal(bool, str)
    def __init__(self, fn): super().__init__(); self._fn = fn
    def run(self): self.done.emit(*self._fn())

# ─────────────────────────────────────────────────────────────
# Helpers de layout
# ─────────────────────────────────────────────────────────────
def hsep():
    f = QFrame(); f.setObjectName("hsep")
    f.setFrameShape(QFrame.HLine); f.setFixedHeight(1); return f

def vsep():
    f = QFrame(); f.setObjectName("vsep")
    f.setFrameShape(QFrame.VLine); f.setFixedWidth(1); return f

def scrolled():
    sc = QScrollArea(); sc.setWidgetResizable(True)
    sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    w = QWidget(); lay = QVBoxLayout(w)
    lay.setContentsMargins(20, 20, 20, 20); lay.setSpacing(14)
    sc.setWidget(w)
    return sc, w, lay

def section_frame(title_text):
    fr = QFrame(); fr.setObjectName("section")
    lay = QVBoxLayout(fr); lay.setContentsMargins(16, 14, 16, 14); lay.setSpacing(10)
    lbl = QLabel(title_text); lbl.setObjectName("sec_title"); lay.addWidget(lbl)
    return fr, lay, lbl

def row_widget(*widgets, spacing=10):
    """Fila horizontal de widgets."""
    w = QWidget(); l = QHBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0); l.setSpacing(spacing)
    for ww in widgets:
        if ww is None: l.addStretch()
        else: l.addWidget(ww)
    return w

# ═════════════════════════════════════════════════════════════
# VENTANA PRINCIPAL
# ═════════════════════════════════════════════════════════════
class ConkymanApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conkyman")
        self.setMinimumSize(820, 580)

        self.base_path   = os.path.dirname(os.path.abspath(__file__))
        self.logo_path   = os.path.join(self.base_path, "conkyman.svg")
        self.config_dir  = os.path.join(os.path.expanduser("~"), ".config", "conkyman")
        self.config_file = os.path.join(self.config_dir, "conkyman.conf")
        self.profiles_dir = os.path.join(self.config_dir, "profiles")
        self.backup_dir   = os.path.join(self.config_dir, "backups")
        for d in (self.config_dir, self.profiles_dir, self.backup_dir):
            os.makedirs(d, exist_ok=True)

        if os.path.exists(self.logo_path):
            self.setWindowIcon(QIcon(self.logo_path))

        first_dark = list(COLORS_DATA['dark'].keys())[0]
        self._color_sel = {'c1': ('named', first_dark), 'c2': ('named', first_dark)}
        self._btn_groups = []
        self._tr_cbs = []

        self._font_nums = QFont("Roboto", 85)
        self._font_txt  = QFont("Roboto Condensed", 14)

        saved_lang = self._ini('General', 'language')
        self.translator = Translator(saved_lang)
        self.conkyrc_path = self._detect_conky()

        # Timer para el panel de estado
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.setInterval(3000)

        self.setStyleSheet(QSS)
        self._build_ui()
        self.load_config()
        self._status_timer.start()

    # ── helpers ───────────────────────────────────────────────
    def _detect_conky(self):
        home = os.path.expanduser("~")
        for p in [os.path.join(home, ".config", "conky", "conky.lua"),
                  os.path.join(home, ".conkyrc")]:
            if os.path.exists(p): return p
        return os.path.join(home, ".config", "conky", "conky.lua")

    def _ini(self, sec, key, fallback=None):
        c = configparser.ConfigParser(); c.read(self.config_file)
        return c.get(sec, key, fallback=fallback)

    def _t(self, key, default=None): return self.translator.get(key, default or key)
    def _tf(self, key, default=None, **kw): return self.translator.fmt(key, default, **kw)
    def _reg(self, cb): self._tr_cbs.append(cb)
    def _mode(self): return "dark" if self.mode_dark.isChecked() else "light"

    def _retranslate(self):
        for cb in self._tr_cbs:
            try: cb()
            except Exception: pass

    def _conky_pid(self):
        try:
            out = subprocess.check_output(["pgrep", "-x", "conky"], text=True).strip()
            return out.split()[0] if out else None
        except Exception:
            return None

    # ── BUILD UI ──────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setSpacing(0); root_lay.setContentsMargins(0, 0, 0, 0)

        # topbar
        topbar = QWidget(); topbar.setObjectName("topbar"); topbar.setFixedHeight(48)
        tb = QHBoxLayout(topbar); tb.setContentsMargins(12, 0, 12, 0); tb.setSpacing(6)

        if os.path.exists(self.logo_path):
            logo = QLabel()
            logo.setPixmap(QPixmap(self.logo_path).scaled(
                28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            tb.addWidget(logo)

        app_title = QLabel("Conkyman")
        app_title.setStyleSheet("font-size:15px;font-weight:bold;color:#ebebeb;")
        tb.addWidget(app_title); tb.addStretch()

        def tool_btn(text, cb):
            b = QPushButton(text); b.setObjectName("tool_btn")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(cb); return b

        self._btn_restart = tool_btn("⟳  " + self._t('btn_restart','Reiniciar'), self.restart_conky)
        self._btn_restore = tool_btn("↺  " + self._t('btn_restore','Restaurar'), self.restore_defaults)
        self._btn_editor  = tool_btn("✎  " + self._t('btn_editor','Editor'),     self.open_editor)
        for b in (self._btn_restart, self._btn_restore, self._btn_editor):
            tb.addWidget(b)
        self._reg(lambda: self._btn_restart.setText("⟳  " + self._t('btn_restart','Reiniciar')))
        self._reg(lambda: self._btn_restore.setText("↺  " + self._t('btn_restore','Restaurar')))
        self._reg(lambda: self._btn_editor.setText("✎  " + self._t('btn_editor','Editor')))

        tb.addWidget(vsep())
        self.lang_combo = QComboBox()
        cur = self.translator.lang
        for i, (code, label) in enumerate(LANG_FLAGS.items()):
            self.lang_combo.addItem(label, code)
            if code == cur: self.lang_combo.setCurrentIndex(i)
        self.lang_combo.currentIndexChanged.connect(self._on_lang)
        tb.addWidget(self.lang_combo)

        btn_about = tool_btn("ℹ", self.show_about)
        btn_about.setToolTip(self._t('btn_about','Acerca de')); tb.addWidget(btn_about)

        root_lay.addWidget(topbar); root_lay.addWidget(hsep())

        # body
        body = QWidget(); body_lay = QHBoxLayout(body)
        body_lay.setSpacing(0); body_lay.setContentsMargins(0, 0, 0, 0)

        # sidebar
        sidebar = QWidget(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(190)
        sb = QVBoxLayout(sidebar); sb.setContentsMargins(10, 16, 10, 16); sb.setSpacing(4)

        self._nav_bg = QButtonGroup(self); self._nav_bg.setExclusive(True)
        self._btn_groups.append(self._nav_bg)
        self._nav_btns = []

        nav_items = [
            ('nav_appearance', '▦  Apariencia'),
            ('nav_colors',     '◑  Colores'),
            ('nav_system',     '⚙  Sistema'),
            ('nav_ajustes',    '☰  Ajustes'),
            ('nav_profiles',   '❐  Perfiles'),
            ('nav_status',     '●  Estado'),
            ('nav_tools',      '⚒  Herramientas'),
        ]
        for i, (tr_key, default) in enumerate(nav_items):
            b = QPushButton(self._t(tr_key, default))
            b.setObjectName("nav_btn"); b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, idx=i: self._nav(idx))
            self._nav_bg.addButton(b); self._nav_btns.append(b); sb.addWidget(b)
            self._reg(lambda btn=b, k=tr_key, d=default:
                      btn.setText(self._t(k, d)))

        self._nav_btns[0].setChecked(True)
        sb.addStretch()
        ver = QLabel("v2.0.1  ·  CuerdOS"); ver.setObjectName("ver_lbl")
        ver.setAlignment(Qt.AlignCenter); sb.addWidget(ver)

        body_lay.addWidget(sidebar); body_lay.addWidget(vsep())

        # stack
        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_appearance())   # 0
        self.stack.addWidget(self._page_colors())        # 1
        self.stack.addWidget(self._page_system())        # 2
        self.stack.addWidget(self._page_ajustes())       # 3
        self.stack.addWidget(self._page_profiles())      # 4
        self.stack.addWidget(self._page_status())        # 5
        self.stack.addWidget(self._page_tools())         # 6
        body_lay.addWidget(self.stack, 1)

        root_lay.addWidget(body, 1); root_lay.addWidget(hsep())

        # footer
        footer = QWidget(); footer.setFixedHeight(56)
        ft = QHBoxLayout(footer); ft.setContentsMargins(16, 0, 16, 0); ft.setSpacing(10)
        self._status_lbl = QLabel(); self._status_lbl.setObjectName("sec_sub")
        ft.addWidget(self._status_lbl); ft.addStretch()
        self.btn_apply = QPushButton(self._t('btn_apply','Aplicar Cambios'))
        self.btn_apply.setObjectName("apply_btn")
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self._start_apply)
        ft.addWidget(self.btn_apply)
        self._reg(lambda: self.btn_apply.setText(self._t('btn_apply','Aplicar Cambios')))
        root_lay.addWidget(footer)

    def _nav(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 5: self._refresh_status()
        if idx == 4: self._refresh_profiles()

    # ── helpers UI ────────────────────────────────────────────
    def _radio_section(self, parent_lay, title_key, title_default, items):
        fr, lay, lbl = section_frame(self._t(title_key, title_default))
        self._reg(lambda w=lbl, k=title_key, d=title_default: w.setText(self._t(k, d)))
        bg = QButtonGroup(fr); bg.setExclusive(True); self._btn_groups.append(bg)
        wrap = QWidget()
        wlay = QHBoxLayout(wrap); wlay.setContentsMargins(0, 0, 0, 0); wlay.setSpacing(16)
        wlay.setAlignment(Qt.AlignLeft)
        for tr_key, default_lbl, attr, checked in items:
            r = QRadioButton(self._t(tr_key, default_lbl))
            r.setChecked(checked); bg.addButton(r); setattr(self, attr, r)
            self._reg(lambda w=r, k=tr_key, d=default_lbl: w.setText(self._t(k, d)))
            wlay.addWidget(r)
        lay.addWidget(wrap); parent_lay.addWidget(fr)
        return bg

    def _labeled_row(self, label_text, widget, sublabel=True):
        """Fila label + widget alineados."""
        lbl = QLabel(label_text)
        if sublabel: lbl.setObjectName("sec_sub")
        return self._labeled_row_lbl(lbl, widget)

    def _labeled_row_lbl(self, lbl, widget):
        """Fila con QLabel ya creado + widget."""
        row = QWidget(); rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(12)
        rl.addWidget(lbl); rl.addStretch(); rl.addWidget(widget)
        return row

    # ══════════════════════════════════════════════════════════
    # PÁGINA: APARIENCIA
    # ══════════════════════════════════════════════════════════
    def _page_appearance(self):
        sc, _, lay = scrolled()

        self._radio_section(lay, 'location', 'Ubicacion', [
            ('top_right',    'Arriba derecha',   'pos_tr', True),
            ('top_left',     'Arriba izquierda', 'pos_tl', False),
            ('bottom_right', 'Abajo derecha',    'pos_br', False),
            ('bottom_left',  'Abajo izquierda',  'pos_bl', False),
            ('center',       'Centro',           'pos_cc', False),
        ])

        self._radio_section(lay, 'color_mode', 'Modo de color', [
            ('dark_mode',  'Modo oscuro', 'mode_dark',  True),
            ('light_mode', 'Modo claro',  'mode_light', False),
        ])
        self.mode_dark.toggled.connect(self._on_mode_toggled)

        # Tipografía
        fr, flay, lbl = section_frame(self._t('typography','Tipografia [Experimental]'))
        grid = QGridLayout(); grid.setHorizontalSpacing(16); grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        for row_i, (key, default, which) in enumerate([
            ('font_numbers', 'Fuente Numeros', 'nums'),
            ('font_texts',   'Fuente Textos',  'txt'),
        ]):
            lbl_f = QLabel(self._t(key, default)); lbl_f.setObjectName("sec_sub")
            self._reg(lambda w=lbl_f, k=key, d=default: w.setText(self._t(k, d)))
            grid.addWidget(lbl_f, row_i, 0)
            font_obj = self._font_nums if which == 'nums' else self._font_txt
            btn_f = QPushButton(f"{font_obj.family()}, {font_obj.pointSize()}pt")
            btn_f.setObjectName("action_btn"); btn_f.setCursor(Qt.PointingHandCursor)
            btn_f.clicked.connect(lambda _=False, w=which: self._pick_font(w))
            setattr(self, f"font_{which}_btn", btn_f)
            grid.addWidget(btn_f, row_i, 1)
        flay.addLayout(grid)
        lay.addWidget(fr); lay.addStretch()
        return sc

    # ══════════════════════════════════════════════════════════
    # PÁGINA: COLORES
    # ══════════════════════════════════════════════════════════
    def _page_colors(self):
        sc, _, lay = scrolled()
        self._color_panels = {}

        for prefix, title_key, title_default in [
            ('c1', 'primary_color', 'Color Primario'),
            ('c2', 'accent_color',  'Color de Acento'),
        ]:
            setattr(self, f"_{prefix}_picker_color", QColor("#8AA34F"))
            fr, flay, title_lbl = section_frame(self._t(title_key, title_default))
            self._reg(lambda w=title_lbl, k=title_key, d=title_default:
                      w.setText(self._t(k, d)))

            for mode in ('dark', 'light'):
                colors = COLORS_DATA[mode]
                panel = QWidget(); panel.setStyleSheet("background:transparent;")
                pv = QVBoxLayout(panel); pv.setContentsMargins(0, 4, 0, 0); pv.setSpacing(8)

                bg = QButtonGroup(self); bg.setExclusive(True)
                self._btn_groups.append(bg)
                setattr(self, f"_{prefix}_{mode}_bg", bg)

                grid_w = QWidget(); grid_w.setStyleSheet("background:transparent;")
                grid = QGridLayout(grid_w)
                grid.setHorizontalSpacing(16); grid.setVerticalSpacing(8)
                grid.setContentsMargins(0, 0, 0, 0)
                COLS = 3
                for idx, (cname, chex) in enumerate(colors.items()):
                    ri = idx // COLS; ci = (idx % COLS) * 2
                    sw = QPushButton(); sw.setFixedSize(22, 22)
                    sw.setStyleSheet(
                        f"QPushButton{{background:{chex};border:2px solid #45475a;border-radius:5px;}}"
                        f"QPushButton:hover{{border-color:#a6e3a1;}}")
                    radio = QRadioButton(cname)
                    radio.setStyleSheet("background:transparent;")
                    attr = f"_{prefix}_{mode}_{_safe(cname)}"
                    setattr(self, attr, radio); bg.addButton(radio)
                    radio.toggled.connect(
                        lambda chk, p=prefix, cn=cname: self._on_named(chk, p, cn))
                    sw.clicked.connect(lambda _=False, r=radio: r.setChecked(True))
                    grid.addWidget(sw, ri, ci); grid.addWidget(radio, ri, ci + 1)

                pv.addWidget(grid_w); pv.addWidget(hsep())

                cust_row = QWidget(); cust_row.setStyleSheet("background:transparent;")
                cr = QHBoxLayout(cust_row); cr.setContentsMargins(0,0,0,0); cr.setSpacing(8)
                r_cust = QRadioButton(self._t('custom', 'Personalizado'))
                r_cust.setStyleSheet("background:transparent;")
                bg.addButton(r_cust)
                setattr(self, f"_{prefix}_{mode}_radio_custom", r_cust)
                r_cust.toggled.connect(lambda chk, p=prefix: self._on_custom(chk, p))
                sw_cust = QPushButton(); sw_cust.setFixedSize(22, 22)
                sw_cust.setStyleSheet(
                    "QPushButton{background:#8AA34F;border:2px solid #45475a;border-radius:5px;}"
                    "QPushButton:hover{border-color:#a6e3a1;}")
                setattr(self, f"_{prefix}_{mode}_swatch_custom", sw_cust)
                sw_cust.clicked.connect(lambda _=False, p=prefix: self._pick_color(p))
                self._reg(lambda w=r_cust: w.setText(self._t('custom', 'Personalizado')))
                cr.addWidget(sw_cust); cr.addWidget(r_cust); cr.addStretch()
                pv.addWidget(cust_row)

                flay.addWidget(panel)
                self._color_panels[(prefix, mode)] = panel

            lay.addWidget(fr)

        lay.addStretch()
        self._sync_color_visibility()
        self._restore_color('c1'); self._restore_color('c2')
        return sc

    # ══════════════════════════════════════════════════════════
    # PÁGINA: SISTEMA
    # ══════════════════════════════════════════════════════════
    def _page_system(self):
        sc, _, lay = scrolled()

        self._radio_section(lay, 'time_format', 'Formato de hora', [
            ('24_hours', '24 horas',         'time_24', True),
            ('12_hours', '12 horas (AM/PM)', 'time_12', False),
        ])
        self._radio_section(lay, 'conky_type', 'Tipo de ventana', [
            ('dock',    'dock',    'type_dock',  True),
            ('normal',  'normal',  'type_norm',  False),
            ('desktop', 'desktop', 'type_desk',  False),
            ('panel',   'panel',   'type_panel', False),
        ])

        # Modo minimal
        fr, flay, lbl = section_frame(self._t('minimalist_mode','Modo de Visualizacion'))
        row = QHBoxLayout()
        lbl_sw = QLabel(self._t('enable_minimalist','Activar Conky Minimal (solo reloj y fecha)'))
        lbl_sw.setObjectName("sec_sub"); row.addWidget(lbl_sw); row.addStretch()
        self._reg(lambda w=lbl_sw: w.setText(self._t('enable_minimalist','Activar Conky Minimal (solo reloj y fecha)')))
        self.switch_minimal = QCheckBox(); row.addWidget(self.switch_minimal)
        flay.addLayout(row); lay.addWidget(fr)

        # Monitor xinerama
        fr2, fl2, _ = section_frame(self._t('monitor_head','Monitor (xinerama_head)'))
        self.xinerama_combo = QComboBox()
        for n in ["0","1","2","3"]: self.xinerama_combo.addItem(n, n)
        lbl_mon = QLabel(self._t('monitor_label','Monitor principal (0, 1, 2...)')); lbl_mon.setObjectName("sec_sub")
        self._reg(lambda w=lbl_mon: w.setText(self._t('monitor_label','Monitor principal (0, 1, 2...)')))
        fl2.addWidget(self._labeled_row_lbl(lbl_mon, self.xinerama_combo))
        lay.addWidget(fr2)

        lay.addStretch()
        return sc

    # ══════════════════════════════════════════════════════════
    # PÁGINA: AJUSTES (Gap, Interval, Preview)
    # ══════════════════════════════════════════════════════════
    def _page_ajustes(self):
        sc, _, lay = scrolled()

        # Gap X / Gap Y
        fr, flay, lbl_pos = section_frame(self._t('sec_position','Posicion y margenes'))
        self._reg(lambda w=lbl_pos: w.setText(self._t('sec_position','Posicion y margenes')))

        self.gap_x_spin = QSpinBox(); self.gap_x_spin.setRange(0, 500); self.gap_x_spin.setValue(20)
        self.gap_y_spin = QSpinBox(); self.gap_y_spin.setRange(0, 500); self.gap_y_spin.setValue(40)
        lbl_gx = QLabel(self._t('gap_x','Gap X (margen horizontal)')); lbl_gx.setObjectName("sec_sub")
        self._reg(lambda w=lbl_gx: w.setText(self._t('gap_x','Gap X (margen horizontal)')))
        lbl_gy = QLabel(self._t('gap_y','Gap Y (margen vertical)')); lbl_gy.setObjectName("sec_sub")
        self._reg(lambda w=lbl_gy: w.setText(self._t('gap_y','Gap Y (margen vertical)')))
        flay.addWidget(self._labeled_row_lbl(lbl_gx, self.gap_x_spin))
        flay.addWidget(self._labeled_row_lbl(lbl_gy, self.gap_y_spin))
        lay.addWidget(fr)

        # Update interval
        fr2, fl2, lbl_iv2 = section_frame(self._t('sec_interval','Intervalo de actualizacion'))
        self._reg(lambda w=lbl_iv2: w.setText(self._t('sec_interval','Intervalo de actualizacion')))
        self.interval_slider = QSlider(Qt.Horizontal)
        self.interval_slider.setRange(5, 100)   # 0.5s – 10.0s en décimas
        self.interval_slider.setValue(10)        # 1.0s default
        self.interval_lbl = QLabel("1.0 s"); self.interval_lbl.setObjectName("sec_sub")
        self.interval_lbl.setFixedWidth(40)
        self.interval_slider.valueChanged.connect(
            lambda v: self.interval_lbl.setText(f"{v/10:.1f} s"))
        row_iv = QWidget(); rl = QHBoxLayout(row_iv)
        rl.setContentsMargins(0,0,0,0); rl.setSpacing(12)
        lbl_iv = QLabel(self._t('interval_each','Cada:'))
        self._reg(lambda w=lbl_iv: w.setText(self._t('interval_each','Cada:')))
        rl.addWidget(lbl_iv); rl.addWidget(self.interval_slider, 1)
        rl.addWidget(self.interval_lbl)
        fl2.addWidget(row_iv); lay.addWidget(fr2)

        # Tamaño mínimo
        fr3, fl3, lbl_min = section_frame(self._t('sec_min_size','Tamano minimo de ventana'))
        self._reg(lambda w=lbl_min: w.setText(self._t('sec_min_size','Tamano minimo de ventana')))
        self.min_w_spin = QSpinBox(); self.min_w_spin.setRange(50, 2000); self.min_w_spin.setValue(200)
        self.min_h_spin = QSpinBox(); self.min_h_spin.setRange(50, 2000); self.min_h_spin.setValue(300)
        lbl_mw = QLabel(self._t('min_width','Ancho minimo (px)')); lbl_mw.setObjectName("sec_sub")
        self._reg(lambda w=lbl_mw: w.setText(self._t('min_width','Ancho minimo (px)')))
        lbl_mh = QLabel(self._t('min_height','Alto minimo (px)')); lbl_mh.setObjectName("sec_sub")
        self._reg(lambda w=lbl_mh: w.setText(self._t('min_height','Alto minimo (px)')))
        fl3.addWidget(self._labeled_row_lbl(lbl_mw, self.min_w_spin))
        fl3.addWidget(self._labeled_row_lbl(lbl_mh, self.min_h_spin))
        lay.addWidget(fr3)

        # Preview
        fr4, fl4, lbl_prev = section_frame(self._t('sec_preview','Vista previa (simulada)'))
        self._reg(lambda w=lbl_prev: w.setText(self._t('sec_preview','Vista previa (simulada)')))
        lbl_hint = QLabel(self._t('preview_hint2',
            "Muestra como quedara el conky con los ajustes actuales.\n"
            "Pulsa 'Actualizar preview' para regenerar."))
        lbl_hint.setObjectName("sec_sub"); lbl_hint.setWordWrap(True)
        self._reg(lambda w=lbl_hint: w.setText(self._t('preview_hint2',
            "Muestra como quedara el conky con los ajustes actuales.\n"
            "Pulsa 'Actualizar preview' para regenerar.")))
        fl4.addWidget(lbl_hint)
        self.preview_text = QTextEdit(); self.preview_text.setReadOnly(True)
        self.preview_text.setFixedHeight(160)
        fl4.addWidget(self.preview_text)
        btn_prev = QPushButton(self._t('btn_preview','Actualizar preview')); btn_prev.setObjectName("action_btn")
        btn_prev.clicked.connect(self._update_preview)
        fl4.addWidget(btn_prev)
        lay.addWidget(fr4)

        lay.addStretch()
        return sc

    def _update_preview(self):
        """Genera el conky.lua con los ajustes actuales y lo muestra."""
        try:
            ok, content = self._build_content()
            if ok:
                self.preview_text.setPlainText(content[:2000])
            else:
                self.preview_text.setPlainText(f"Error: {content}")
        except Exception as e:
            self.preview_text.setPlainText(str(e))

    # ══════════════════════════════════════════════════════════
    # PÁGINA: PERFILES
    # ══════════════════════════════════════════════════════════
    def _page_profiles(self):
        sc, _, lay = scrolled()

        fr, flay, _ = section_frame(self._t('sec_profiles','Perfiles guardados'))
        lbl_hint = QLabel(self._t('profiles_hint',
            "Guarda la configuracion actual con un nombre para\n"
            "cambiar entre distintos setups rapidamente."))
        lbl_hint.setObjectName("sec_sub"); lbl_hint.setWordWrap(True)
        self._reg(lambda w=lbl_hint: w.setText(self._t('profiles_hint','Guarda la configuracion actual con un nombre para\ncambiar entre distintos setups rapidamente.')))
        flay.addWidget(lbl_hint)

        self.profile_list = QListWidget()
        self.profile_list.setFixedHeight(200)
        flay.addWidget(self.profile_list)

        btns = QWidget(); bl = QHBoxLayout(btns)
        bl.setContentsMargins(0,0,0,0); bl.setSpacing(8)
        btn_save = QPushButton(self._t('btn_save_profile','Guardar perfil actual')); btn_save.setObjectName("action_btn")
        btn_load = QPushButton(self._t('btn_load_profile','Cargar seleccionado'));   btn_load.setObjectName("action_btn")
        btn_del  = QPushButton(self._t('btn_del_profile','Eliminar'));              btn_del.setObjectName("danger_btn")
        btn_save.clicked.connect(self._save_profile)
        btn_load.clicked.connect(self._load_profile)
        btn_del.clicked.connect(self._delete_profile)
        for b in (btn_save, btn_load, btn_del): bl.addWidget(b)
        self._reg(lambda b=btn_save: b.setText(self._t('btn_save_profile','Guardar perfil actual')))
        self._reg(lambda b=btn_load: b.setText(self._t('btn_load_profile','Cargar seleccionado')))
        self._reg(lambda b=btn_del:  b.setText(self._t('btn_del_profile','Eliminar')))
        bl.addStretch()
        flay.addWidget(btns)
        lay.addWidget(fr)

        # Exportar / Importar
        fr2, fl2, _ = section_frame(self._t('sec_export','Exportar / Importar configuracion'))
        lbl_ei = QLabel(self._t('export_hint','Guarda o carga la configuracion de ConkyMan (.conf) y el conky.lua.'))
        lbl_ei.setObjectName("sec_sub"); lbl_ei.setWordWrap(True)
        self._reg(lambda w=lbl_ei: w.setText(self._t('export_hint','Guarda o carga la configuracion de ConkyMan (.conf) y el conky.lua.')))
        fl2.addWidget(lbl_ei)
        btns2 = QWidget(); bl2 = QHBoxLayout(btns2); bl2.setContentsMargins(0,0,0,0); bl2.setSpacing(8)
        btn_exp = QPushButton(self._t('btn_export_dots','Exportar…')); btn_exp.setObjectName("action_btn")
        btn_imp = QPushButton(self._t('btn_import_dots','Importar…')); btn_imp.setObjectName("action_btn")
        btn_exp.clicked.connect(self._export_config)
        btn_imp.clicked.connect(self._import_config)
        self._reg(lambda b=btn_exp: b.setText(self._t('btn_export_dots','Exportar…')))
        self._reg(lambda b=btn_imp: b.setText(self._t('btn_import_dots','Importar…')))
        bl2.addWidget(btn_exp); bl2.addWidget(btn_imp); bl2.addStretch()
        fl2.addWidget(btns2); lay.addWidget(fr2)

        lay.addStretch()
        return sc

    def _refresh_profiles(self):
        self.profile_list.clear()
        for f in sorted(os.listdir(self.profiles_dir)):
            if f.endswith(".json"):
                item = QListWidgetItem(f[:-5])
                item.setData(Qt.UserRole, os.path.join(self.profiles_dir, f))
                self.profile_list.addItem(item)

    def _save_profile(self):
        name, ok = QInputDialog.getText(self, self._t('save_profile_title','Guardar perfil'), self._t('input_profile_name','Nombre del perfil:'))
        if not ok or not name.strip(): return
        name = name.strip()
        self._save_config()
        data = {'conkyman_conf': open(self.config_file).read() if os.path.exists(self.config_file) else ''}
        lua = self.conkyrc_path
        if os.path.exists(lua):
            data['conky_lua'] = open(lua).read()
        path = os.path.join(self.profiles_dir, f"{name}.json")
        with open(path, 'w') as f: json.dump(data, f, indent=2)
        self._refresh_profiles()
        self._status_lbl.setText(self._tf('profile_saved', name=name))

    def _load_profile(self):
        item = self.profile_list.currentItem()
        if not item: return
        path = item.data(Qt.UserRole)
        try:
            data = json.loads(open(path).read())
            if 'conkyman_conf' in data:
                with open(self.config_file, 'w') as f: f.write(data['conkyman_conf'])
            if 'conky_lua' in data:
                self._write_conky_str(data['conky_lua'])
            self.load_config()
            self._status_lbl.setText(self._tf('profile_loaded', name=item.text()))
        except Exception as e:
            QMessageBox.critical(self, self._t('error_loading_profile','Error'), str(e))

    def _delete_profile(self):
        item = self.profile_list.currentItem()
        if not item: return
        r = QMessageBox.question(self, self._t('profile_del_title','Eliminar perfil'),
            self._tf('profile_del_q', name=item.text()), QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            os.remove(item.data(Qt.UserRole))
            self._refresh_profiles()

    def _export_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self._t('export_title','Exportar configuracion'), os.path.expanduser("~/conkyman_export.json"),
            "JSON (*.json)")
        if not path: return
        data = {}
        if os.path.exists(self.config_file):
            data['conkyman_conf'] = open(self.config_file).read()
        if os.path.exists(self.conkyrc_path):
            data['conky_lua'] = open(self.conkyrc_path).read()
        with open(path, 'w') as f: json.dump(data, f, indent=2)
        self._status_lbl.setText(self._tf('exported_to', name=os.path.basename(path)))

    def _import_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self._t('import_title','Importar configuracion'), os.path.expanduser("~"),
            "JSON (*.json)")
        if not path: return
        try:
            data = json.loads(open(path).read())
            if 'conkyman_conf' in data:
                with open(self.config_file, 'w') as f: f.write(data['conkyman_conf'])
            if 'conky_lua' in data:
                self._write_conky_str(data['conky_lua'])
            self.load_config()
            self._status_lbl.setText(self._t('config_imported','Configuracion importada.'))
        except Exception as e:
            QMessageBox.critical(self, self._t('import_error','Error al importar'), str(e))

    # ══════════════════════════════════════════════════════════
    # PÁGINA: ESTADO
    # ══════════════════════════════════════════════════════════
    def _page_status(self):
        sc, _, lay = scrolled()

        # Estado de Conky
        fr, flay, lbl_stat = section_frame(self._t('sec_status','Estado de Conky'))
        self._reg(lambda w=lbl_stat: w.setText(self._t('sec_status','Estado de Conky')))
        row_st = QWidget(); rl = QHBoxLayout(row_st)
        rl.setContentsMargins(0,0,0,0); rl.setSpacing(12)
        self._conky_status_dot = QLabel("●"); self._conky_status_dot.setFixedWidth(20)
        self._conky_status_lbl = QLabel(self._t('checking','Verificando...'))
        self._conky_pid_lbl    = QLabel(""); self._conky_pid_lbl.setObjectName("sec_sub")
        rl.addWidget(self._conky_status_dot); rl.addWidget(self._conky_status_lbl)
        rl.addStretch(); rl.addWidget(self._conky_pid_lbl)
        flay.addWidget(row_st)

        btns_st = QWidget(); bs = QHBoxLayout(btns_st)
        bs.setContentsMargins(0,0,0,0); bs.setSpacing(8)
        btn_start = QPushButton(self._t('btn_start','Iniciar'));  btn_start.setObjectName("action_btn")
        btn_stop  = QPushButton(self._t('btn_stop','Detener'));  btn_stop.setObjectName("danger_btn")
        btn_reload= QPushButton(self._t('btn_reload','Recargar')); btn_reload.setObjectName("action_btn")
        self._reg(lambda b=btn_start:  b.setText(self._t('btn_start','Iniciar')))
        self._reg(lambda b=btn_stop:   b.setText(self._t('btn_stop','Detener')))
        self._reg(lambda b=btn_reload: b.setText(self._t('btn_reload','Recargar')))
        btn_start.clicked.connect(self.restart_conky)
        btn_stop.clicked.connect(lambda: (os.system("killall conky 2>/dev/null"),
                                          self._refresh_status()))
        btn_reload.clicked.connect(lambda: (os.system("killall -SIGUSR1 conky 2>/dev/null"),
                                            self._refresh_status()))
        for b in (btn_start, btn_stop, btn_reload): bs.addWidget(b)
        bs.addStretch(); flay.addWidget(btns_st)
        lay.addWidget(fr)

        # Archivo activo
        fr2, fl2, lbl_af = section_frame(self._t('sec_active_file','Archivo de configuracion activo'))
        self._reg(lambda w=lbl_af: w.setText(self._t('sec_active_file','Archivo de configuracion activo')))
        self._path_lbl = QLabel(self.conkyrc_path); self._path_lbl.setObjectName("mono")
        self._path_lbl.setWordWrap(True); fl2.addWidget(self._path_lbl)
        btns_p = QWidget(); bp = QHBoxLayout(btns_p)
        bp.setContentsMargins(0,0,0,0); bp.setSpacing(8)
        btn_change = QPushButton(self._t('btn_change_path','Cambiar ruta…')); btn_change.setObjectName("action_btn")
        btn_open   = QPushButton(self._t('btn_open_folder','Abrir carpeta')); btn_open.setObjectName("action_btn")
        btn_change.clicked.connect(self._change_conky_path)
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(os.path.dirname(self.conkyrc_path))))
        bp.addWidget(btn_change); bp.addWidget(btn_open); bp.addStretch()
        self._reg(lambda b=btn_change: b.setText(self._t('btn_change_path','Cambiar ruta…')))
        self._reg(lambda b=btn_open:   b.setText(self._t('btn_open_folder','Abrir carpeta')))
        fl2.addWidget(btns_p); lay.addWidget(fr2)

        # Historial de cambios (último backup)
        fr3, fl3, lbl_hist = section_frame(self._t('sec_history','Historial de cambios (deshacer)'))
        self._reg(lambda w=lbl_hist: w.setText(self._t('sec_history','Historial de cambios (deshacer)')))
        lbl_bk = QLabel(self._t('history_hint','Cada vez que aplicas cambios se guarda un backup automatico.'))
        lbl_bk.setObjectName("sec_sub"); lbl_bk.setWordWrap(True)
        self._reg(lambda w=lbl_bk: w.setText(self._t('history_hint','Cada vez que aplicas cambios se guarda un backup automatico.')))
        fl3.addWidget(lbl_bk)
        self.backup_list = QListWidget(); self.backup_list.setFixedHeight(130)
        fl3.addWidget(self.backup_list)
        btn_restore_bk = QPushButton(self._t('btn_restore_bk','Restaurar backup seleccionado'))
        btn_restore_bk.setObjectName("action_btn")
        btn_restore_bk.clicked.connect(self._restore_backup)
        self._reg(lambda b=btn_restore_bk: b.setText(self._t('btn_restore_bk','Restaurar backup seleccionado')))
        fl3.addWidget(btn_restore_bk); lay.addWidget(fr3)

        lay.addStretch()
        return sc

    def _refresh_status(self):
        pid = self._conky_pid()
        if pid:
            self._conky_status_dot.setStyleSheet("color: #a6e3a1; font-size: 18px;")
            self._conky_status_lbl.setText(self._t('running','Corriendo')); self._conky_status_lbl.setObjectName("status_ok")
            self._conky_pid_lbl.setText(f"PID: {pid}")
        else:
            self._conky_status_dot.setStyleSheet("color: #f38ba8; font-size: 18px;")
            self._conky_status_lbl.setText(self._t('stopped','Detenido')); self._conky_status_lbl.setObjectName("status_err")
            self._conky_pid_lbl.setText("")
        # ruta
        self._path_lbl.setText(self.conkyrc_path)
        # backups
        self.backup_list.clear()
        for f in sorted(os.listdir(self.backup_dir), reverse=True)[:15]:
            if f.endswith(".lua"):
                item = QListWidgetItem(f)
                item.setData(Qt.UserRole, os.path.join(self.backup_dir, f))
                self.backup_list.addItem(item)

    def _change_conky_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self._t('select_conky_lua','Seleccionar conky.lua'), os.path.dirname(self.conkyrc_path),
            "Lua (*.lua);;Todos (*)")
        if path:
            self.conkyrc_path = path
            self._path_lbl.setText(path)

    def _restore_backup(self):
        item = self.backup_list.currentItem()
        if not item: return
        src = item.data(Qt.UserRole)
        r = QMessageBox.question(self, self._t('restore_bk_title','Restaurar backup'),
            self._tf('restore_bk_q', name=item.text()),
            QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            shutil.copy2(src, self.conkyrc_path)
            self.restart_conky()
            self._status_lbl.setText(self._t('backup_restored','Backup restaurado.'))

    # ══════════════════════════════════════════════════════════
    # PÁGINA: HERRAMIENTAS
    # ══════════════════════════════════════════════════════════
    def _page_tools(self):
        sc, _, lay = scrolled()

        # Autostart
        fr, flay, lbl_as2 = section_frame(self._t('sec_autostart','Inicio automatico con la sesion'))
        self._reg(lambda w=lbl_as2: w.setText(self._t('sec_autostart','Inicio automatico con la sesion')))
        lbl_as = QLabel(self._t('autostart_hint',
            "Crea o elimina el archivo .desktop en ~/.config/autostart\n"
            "para que Conky arranque automaticamente al iniciar sesion."))
        lbl_as.setObjectName("sec_sub"); lbl_as.setWordWrap(True)
        self._reg(lambda w=lbl_as: w.setText(self._t('autostart_hint','Crea o elimina el archivo .desktop en ~/.config/autostart\npara que Conky arranque automaticamente al iniciar sesion.')))
        flay.addWidget(lbl_as)
        row_as = QWidget(); ras = QHBoxLayout(row_as)
        ras.setContentsMargins(0,0,0,0); ras.setSpacing(8)
        self._autostart_lbl = QLabel(); ras.addWidget(self._autostart_lbl); ras.addStretch()
        btn_as_on  = QPushButton(self._t('btn_autostart_on','Activar autostart'));   btn_as_on.setObjectName("action_btn")
        btn_as_off = QPushButton(self._t('btn_autostart_off','Desactivar autostart')); btn_as_off.setObjectName("danger_btn")
        btn_as_on.clicked.connect(self._enable_autostart)
        btn_as_off.clicked.connect(self._disable_autostart)
        self._reg(lambda b=btn_as_on:  b.setText(self._t('btn_autostart_on','Activar autostart')))
        self._reg(lambda b=btn_as_off: b.setText(self._t('btn_autostart_off','Desactivar autostart')))
        ras.addWidget(btn_as_on); ras.addWidget(btn_as_off)
        flay.addWidget(row_as)
        self._refresh_autostart_lbl()
        lay.addWidget(fr)

        # Instalar Conky
        fr2, fl2, lbl_inst2 = section_frame(self._t('sec_install','Verificar / instalar Conky'))
        self._reg(lambda w=lbl_inst2: w.setText(self._t('sec_install','Verificar / instalar Conky')))
        lbl_inst = QLabel(self._t('install_hint','Comprueba si Conky esta instalado en el sistema.'))
        lbl_inst.setObjectName("sec_sub")
        self._reg(lambda w=lbl_inst: w.setText(self._t('install_hint','Comprueba si Conky esta instalado en el sistema.')))
        fl2.addWidget(lbl_inst)
        row_inst = QWidget(); ri = QHBoxLayout(row_inst)
        ri.setContentsMargins(0,0,0,0); ri.setSpacing(8)
        self._conky_ver_lbl = QLabel(); ri.addWidget(self._conky_ver_lbl); ri.addStretch()
        btn_chk = QPushButton(self._t('btn_check','Verificar')); btn_chk.setObjectName("action_btn")
        btn_chk.clicked.connect(self._check_conky_install)
        self._reg(lambda b=btn_chk: b.setText(self._t('btn_check','Verificar')))
        ri.addWidget(btn_chk); fl2.addWidget(row_inst); lay.addWidget(fr2)
        self._check_conky_install()

        # Limpiar backups
        fr3, fl3, lbl_cl2 = section_frame(self._t('sec_cleanup','Limpieza'))
        self._reg(lambda w=lbl_cl2: w.setText(self._t('sec_cleanup','Limpieza')))
        lbl_cl = QLabel(self._t('cleanup_hint','Elimina todos los backups automaticos guardados por ConkyMan.'))
        lbl_cl.setObjectName("sec_sub")
        self._reg(lambda w=lbl_cl: w.setText(self._t('cleanup_hint','Elimina todos los backups automaticos guardados por ConkyMan.')))
        fl3.addWidget(lbl_cl)
        btn_clean = QPushButton(self._t('btn_clean','Limpiar backups')); btn_clean.setObjectName("danger_btn")
        btn_clean.clicked.connect(self._clean_backups)
        self._reg(lambda b=btn_clean: b.setText(self._t('btn_clean','Limpiar backups')))
        fl3.addWidget(btn_clean); lay.addWidget(fr3)

        lay.addStretch()
        return sc

    def _refresh_autostart_lbl(self):
        as_path = os.path.join(os.path.expanduser("~"),
                               ".config", "autostart", "conky.desktop")
        if os.path.exists(as_path):
            self._autostart_lbl.setText(self._t('autostart_on','\u2713 Autostart activo'))
            self._autostart_lbl.setStyleSheet("color: #a6e3a1;")
        else:
            self._autostart_lbl.setText(self._t('autostart_off','\u2717 Autostart inactivo'))
            self._autostart_lbl.setStyleSheet("color: #f38ba8;")

    def _enable_autostart(self):
        d = os.path.join(os.path.expanduser("~"), ".config", "autostart")
        os.makedirs(d, exist_ok=True)
        content = AUTOSTART_DESKTOP.format(conky_path=self.conkyrc_path)
        with open(os.path.join(d, "conky.desktop"), 'w') as f: f.write(content)
        self._refresh_autostart_lbl()
        self._status_lbl.setText(self._t('autostart_enabled','Autostart activado.'))

    def _disable_autostart(self):
        p = os.path.join(os.path.expanduser("~"),
                         ".config", "autostart", "conky.desktop")
        if os.path.exists(p): os.remove(p)
        self._refresh_autostart_lbl()
        self._status_lbl.setText(self._t('autostart_disabled','Autostart desactivado.'))

    def _check_conky_install(self):
        try:
            ver = subprocess.check_output(
                ["conky", "--version"], stderr=subprocess.STDOUT, text=True).split('\n')[0]
            self._conky_ver_lbl.setText(ver[:60])
            self._conky_ver_lbl.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        except Exception:
            self._conky_ver_lbl.setText(self._t('conky_not_found','Conky no encontrado en el sistema.'))
            self._conky_ver_lbl.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _clean_backups(self):
        r = QMessageBox.question(self, self._t('btn_clean','Limpiar backups'),
            self._t('clean_bk_q','Eliminar todos los backups automaticos?'),
            QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            for f in os.listdir(self.backup_dir):
                try: os.remove(os.path.join(self.backup_dir, f))
                except Exception: pass
            self._status_lbl.setText(self._t('backups_cleared','Backups eliminados.'))

    # ══════════════════════════════════════════════════════════
    # COLOR helpers
    # ══════════════════════════════════════════════════════════
    def _sync_color_visibility(self):
        cur = self._mode(); other = 'light' if cur == 'dark' else 'dark'
        for prefix in ('c1', 'c2'):
            self._color_panels[(prefix, cur)].show()
            self._color_panels[(prefix, other)].hide()

    def _restore_color(self, prefix):
        sel_type, sel_val = self._color_sel[prefix]
        mode = self._mode(); colors = COLORS_DATA[mode]
        if sel_type == 'custom':
            r = getattr(self, f"_{prefix}_{mode}_radio_custom", None)
            if r: r.setChecked(True)
            c = QColor(sel_val); setattr(self, f"_{prefix}_picker_color", c)
            self._update_swatch_custom(prefix, c)
        else:
            key = sel_val if sel_val in colors else list(colors.keys())[0]
            r = getattr(self, f"_{prefix}_{mode}_{_safe(key)}", None)
            if r: r.setChecked(True)
            self._update_swatch_custom(prefix, QColor(colors[key]))

    def _update_swatch_custom(self, prefix, color):
        for mode in ('dark', 'light'):
            sw = getattr(self, f"_{prefix}_{mode}_swatch_custom", None)
            if sw:
                sw.setStyleSheet(
                    f"QPushButton{{background:{color.name()};border:2px solid #45475a;"
                    f"border-radius:5px;}}QPushButton:hover{{border-color:#a6e3a1;}}")

    def _on_named(self, chk, prefix, name):
        if chk: self._color_sel[prefix] = ('named', name)

    def _on_custom(self, chk, prefix):
        if chk:
            c = getattr(self, f"_{prefix}_picker_color", QColor("#8AA34F"))
            self._color_sel[prefix] = ('custom', c.name().upper())

    def _pick_color(self, prefix):
        cur = getattr(self, f"_{prefix}_picker_color", QColor("#8AA34F"))
        c = QColorDialog.getColor(cur, self)
        if c.isValid():
            setattr(self, f"_{prefix}_picker_color", c)
            self._update_swatch_custom(prefix, c)
            mode = self._mode()
            r = getattr(self, f"_{prefix}_{mode}_radio_custom", None)
            if r: r.setChecked(True)
            self._color_sel[prefix] = ('custom', c.name().upper())

    def _color_bare(self, prefix):
        t, v = self._color_sel[prefix]
        if t == 'custom': return v.lstrip('#')
        colors = COLORS_DATA[self._mode()]
        return colors.get(v, list(colors.values())[0]).lstrip('#')

    def _on_mode_toggled(self, chk):
        if not chk: return
        self._sync_color_visibility()
        self._restore_color('c1'); self._restore_color('c2')

    # ── Fuentes ───────────────────────────────────────────────
    def _pick_font(self, which):
        cur = self._font_nums if which == 'nums' else self._font_txt
        # PySide6: getFont devuelve (ok: bool, font: QFont) — orden inverso a PyQt5
        ok, f = QFontDialog.getFont(cur, self)
        if not ok or not isinstance(f, QFont): return
        if which == 'nums':
            self._font_nums = f
            self.font_nums_btn.setText(f"{f.family()}, {f.pointSize()}pt")
        else:
            self._font_txt = f
            self.font_txt_btn.setText(f"{f.family()}, {f.pointSize()}pt")

    # ── Idioma ────────────────────────────────────────────────
    def _on_lang(self, idx):
        lang_id = self.lang_combo.itemData(idx)
        if not lang_id or lang_id == self.translator.lang: return
        self.translator = Translator(lang_id)
        set_global_lang(lang_id)
        self._save_config(); self._retranslate()

    # ── Acciones ──────────────────────────────────────────────
    def show_about(self):
        d = QDialog(self)
        d.setWindowTitle(self._t("about_title", "Acerca de ConkyMan"))
        d.setMinimumWidth(320)
        d.setStyleSheet(QSS)
        
        lay = QVBoxLayout(d)
        lay.setContentsMargins(30, 30, 30, 30) 
        lay.setSpacing(12)
        
        if os.path.exists(self.logo_path):
            logo_pix = QPixmap(self.logo_path)
            if not logo_pix.isNull():
                lbl_img = QLabel()
                lbl_img.setAlignment(Qt.AlignCenter)
                lbl_img.setPixmap(logo_pix.scaled(
                    80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                lay.addWidget(lbl_img)
        
        info_texts = [
            "<span style='font-size: 14pt;'><b>ConkyMan 2.0.1</b></span>",
            "<small>© 2026 CuerdOS Dev Team</small>", 
            f"<i>{self._t('about_comments', 'Gestor de configuración para Conky.')}</i>",
            "<b>GPL 3.0</b>"
        ]
        
        for txt in info_texts:
            l = QLabel(txt)
            l.setWordWrap(True)
            l.setAlignment(Qt.AlignCenter)
            lay.addWidget(l)
            
        lay.addSpacing(15)
        
        btn_web = QPushButton(self._t('visit_website', 'Visitar página web'))
        btn_web.setObjectName("action_btn")
        btn_web.setCursor(Qt.PointingHandCursor)
        btn_web.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://cuerdos.github.io")))
        lay.addWidget(btn_web)

      
        d.exec()

    def open_editor(self):
        script = os.path.join(self.base_path, "text.py")
        if os.path.exists(script):
            subprocess.Popen(["python3", script, self.conkyrc_path])
        else:
            subprocess.Popen(["xdg-open", self.conkyrc_path])

    def restart_conky(self):
        os.system("killall conky 2>/dev/null")
        subprocess.Popen(["conky", "-c", self.conkyrc_path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._status_lbl.setText(self._t('restarted','Conky reiniciado.'))
        QTimer.singleShot(1500, self._refresh_status)

    def restore_defaults(self):
        r = QMessageBox.question(self, "ConkyMan",
            self._t('restore_defaults_q','Restaurar configuracion predeterminada?'),
            QMessageBox.Yes | QMessageBox.No)
        if r != QMessageBox.Yes: return
        self._write_conky(DEFAULT_CONKY_LUA)
        self.pos_tr.setChecked(True); self.mode_dark.setChecked(True)
        self._font_nums = QFont("Roboto", 85); self.font_nums_btn.setText("Roboto, 85pt")
        self._font_txt = QFont("Roboto Condensed", 14)
        self.font_txt_btn.setText("Roboto Condensed, 14pt")
        self.time_24.setChecked(True); self.type_dock.setChecked(True)
        self.switch_minimal.setChecked(False); self.xinerama_combo.setCurrentIndex(0)
        self.gap_x_spin.setValue(20); self.gap_y_spin.setValue(40)
        self.interval_slider.setValue(10)
        self.min_w_spin.setValue(200); self.min_h_spin.setValue(300)
        first = list(COLORS_DATA['dark'].keys())[0]
        self._color_sel = {'c1': ('named', first), 'c2': ('named', first)}
        self._sync_color_visibility()
        self._restore_color('c1'); self._restore_color('c2')
        self._save_config(); self.restart_conky()

    # ── Conky files ───────────────────────────────────────────
    def _write_conky(self, content):
        d = os.path.join(os.path.expanduser("~"), ".config", "conky")
        os.makedirs(d, exist_ok=True)
        # backup automático
        if os.path.exists(self.conkyrc_path):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(self.conkyrc_path,
                         os.path.join(self.backup_dir, f"conky_{ts}.lua"))
        self._write_conky_str(content)

    def _write_conky_str(self, content):
        d = os.path.join(os.path.expanduser("~"), ".config", "conky")
        os.makedirs(d, exist_ok=True)
        for fname in ("conky.lua", "conky.conf"):
            try:
                with open(os.path.join(d, fname), 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                print(f"[ConkyMan] {fname}: {e}")
        self.conkyrc_path = os.path.join(d, "conky.lua")

    # ── Aplicar ───────────────────────────────────────────────
    def _start_apply(self):
        self.btn_apply.setEnabled(False); self._status_lbl.setText(self._t('applying','Aplicando...'))
        self._thread = QThread()
        self._worker = Worker(self._apply_logic)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.done.connect(self._on_done)
        self._worker.done.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self, ok, msg):
        self.btn_apply.setEnabled(True); self._status_lbl.setText(msg)
        self.restart_conky()
        if not ok: QMessageBox.critical(self, "ConkyMan", msg)

    def _build_content(self):
        """Genera el contenido del conky.lua. Devuelve (True, content) o (False, error)."""
        try:
            content = MINIMAL_CONKY_LUA if self.switch_minimal.isChecked() else DEFAULT_CONKY_LUA

            base_color = "F5F5F5" if self.mode_dark.isChecked() else "2C3E50"
            content = re.sub(r"default_color\s*=\s*'[^']*'",
                             f"default_color = '{base_color}'", content)

            fn = self._font_nums.family(); ft = self._font_txt.family()
            content = re.sub(r"\${font [^:]+:weight=[^:]+:size=8([05])}",
                             fr"${{font {fn}:weight=Normal:size=8\1}}", content)
            content = re.sub(r"\${font [^:]+:size=1([24])}",
                             fr"${{font {ft}:size=1\1}}", content)

            for attr, val in [('pos_tr','top_right'),('pos_tl','top_left'),
                               ('pos_br','bottom_right'),('pos_bl','bottom_left'),
                               ('pos_cc','middle_middle')]:
                if hasattr(self, attr) and getattr(self, attr).isChecked():
                    content = re.sub(r"alignment\s*=\s*'[^']*'",
                                     f"alignment = '{val}'", content); break

            win = 'dock'
            for attr, val in [('type_dock','dock'),('type_norm','normal'),
                               ('type_desk','desktop'),('type_panel','panel')]:
                if hasattr(self, attr) and getattr(self, attr).isChecked():
                    win = val; break
            if os.environ.get('XDG_SESSION_TYPE') == 'wayland': win = 'desktop'
            content = re.sub(r"own_window_type\s*=\s*'[^']*'",
                             f"own_window_type = '{win}'", content)

            c1 = self._color_bare('c1'); c2 = self._color_bare('c2')
            content = re.sub(r"color1\s*=\s*'[^']*'", f"color1 = '{c1}'", content)
            content = re.sub(r"color2\s*=\s*'[^']*'", f"color2 = '{c2}'", content)
            content = re.sub(r"graph 10,20 [0-9A-Fa-f]+ [0-9A-Fa-f]+",
                             f"graph 10,20 5B8080 {c2}", content)

            if self.time_12.isChecked():
                content = content.replace("%H", "%I %p")
            else:
                content = content.replace("%I %p", "%H").replace("%I", "%H")

            xi = self.xinerama_combo.currentData() or "0"
            content = re.sub(r"xinerama_head\s*=\s*\d+", f"xinerama_head = {xi}", content)

            gx = self.gap_x_spin.value(); gy = self.gap_y_spin.value()
            content = re.sub(r"gap_x\s*=\s*\d+", f"gap_x = {gx}", content)
            content = re.sub(r"gap_y\s*=\s*\d+", f"gap_y = {gy}", content)

            interval = self.interval_slider.value() / 10.0
            content = re.sub(r"update_interval\s*=\s*[\d.]+",
                             f"update_interval = {interval:.1f}", content)

            mw = self.min_w_spin.value(); mh = self.min_h_spin.value()
            content = re.sub(r"minimum_width\s*=\s*\d+",  f"minimum_width = {mw}",  content)
            content = re.sub(r"minimum_height\s*=\s*\d+", f"minimum_height = {mh}", content)

            return True, content
        except Exception as e:
            import traceback; traceback.print_exc()
            return False, str(e)

    def _apply_logic(self):
        ok, result = self._build_content()
        if not ok: return False, result
        self._write_conky(result)
        self._save_config()
        os.system("killall -SIGUSR1 conky 2>/dev/null")
        return True, self._t('changes_applied','Cambios aplicados.')

    # ── Config ────────────────────────────────────────────────
    def _save_config(self):
        cfg = configparser.ConfigParser()
        cfg['General'] = {'language': self.translator.lang}
        pos = next((p for p in ['pos_tr','pos_tl','pos_br','pos_bl','pos_cc']
                    if hasattr(self, p) and getattr(self, p).isChecked()), 'pos_tr')
        cfg['Appearance'] = {
            'mode':      'dark' if self.mode_dark.isChecked() else 'light',
            'font_nums': f"{self._font_nums.family()} {self._font_nums.pointSize()}",
            'font_txt':  f"{self._font_txt.family()} {self._font_txt.pointSize()}",
            'position':  pos,
        }
        mode = self._mode()
        for prefix in ('c1', 'c2'):
            rc = getattr(self, f"_{prefix}_{mode}_radio_custom", None)
            if rc and rc.isChecked():
                c = getattr(self, f"_{prefix}_picker_color", QColor("#8AA34F"))
                self._color_sel[prefix] = ('custom', c.name().upper())
            else:
                for cn in COLORS_DATA[mode]:
                    r = getattr(self, f"_{prefix}_{mode}_{_safe(cn)}", None)
                    if r and r.isChecked():
                        self._color_sel[prefix] = ('named', cn); break
        c1t, c1v = self._color_sel['c1']; c2t, c2v = self._color_sel['c2']
        cfg['Colors'] = {'c1_type':c1t,'c1_value':c1v,'c2_type':c2t,'c2_value':c2v}
        ct = next((t for t in ['type_dock','type_norm','type_desk','type_panel']
                   if hasattr(self, t) and getattr(self, t).isChecked()), 'type_dock')
        cfg['System'] = {
            'minimal':     'yes' if self.switch_minimal.isChecked() else 'no',
            'time_format': '12'  if self.time_12.isChecked() else '24',
            'type':        ct,
            'xinerama':    self.xinerama_combo.currentData() or '0',
        }
        cfg['Ajustes'] = {
            'gap_x':    str(self.gap_x_spin.value()),
            'gap_y':    str(self.gap_y_spin.value()),
            'interval': str(self.interval_slider.value()),
            'min_w':    str(self.min_w_spin.value()),
            'min_h':    str(self.min_h_spin.value()),
        }
        with open(self.config_file, 'w') as f: cfg.write(f)

    def load_config(self):
        if not os.path.exists(self.config_file): return
        cfg = configparser.ConfigParser(); cfg.read(self.config_file)
        try:
            if 'Appearance' in cfg:
                a = cfg['Appearance']
                if a.get('mode') == 'light': self.mode_light.setChecked(True)
                for key, attr, default in [('font_nums','_font_nums','Roboto 85'),
                                           ('font_txt', '_font_txt', 'Roboto Condensed 14')]:
                    parts = a.get(key, default).rsplit(' ', 1)
                    if len(parts) == 2:
                        try:
                            fnt = QFont(parts[0], int(parts[1])); setattr(self, attr, fnt)
                            btn = self.font_nums_btn if attr == '_font_nums' else self.font_txt_btn
                            btn.setText(f"{fnt.family()}, {fnt.pointSize()}pt")
                        except ValueError: pass
                pos = a.get('position', 'pos_tr')
                if hasattr(self, pos): getattr(self, pos).setChecked(True)

            if 'Colors' in cfg:
                c = cfg['Colors']
                for p in ('c1', 'c2'):
                    t = c.get(f'{p}_type', 'named'); v = c.get(f'{p}_value', '')
                    if t in ('named', 'custom') and v: self._color_sel[p] = (t, v)
            self._sync_color_visibility()
            self._restore_color('c1'); self._restore_color('c2')

            if 'System' in cfg:
                s = cfg['System']
                self.switch_minimal.setChecked(s.get('minimal') == 'yes')
                if s.get('time_format') == '12': self.time_12.setChecked(True)
                ct = s.get('type', 'type_dock')
                if hasattr(self, ct): getattr(self, ct).setChecked(True)
                xi = s.get('xinerama', '0')
                idx = self.xinerama_combo.findData(xi)
                if idx >= 0: self.xinerama_combo.setCurrentIndex(idx)

            if 'Ajustes' in cfg:
                aj = cfg['Ajustes']
                self.gap_x_spin.setValue(int(aj.get('gap_x', 20)))
                self.gap_y_spin.setValue(int(aj.get('gap_y', 40)))
                self.interval_slider.setValue(int(aj.get('interval', 10)))
                self.min_w_spin.setValue(int(aj.get('min_w', 200)))
                self.min_h_spin.setValue(int(aj.get('min_h', 300)))

        except Exception as e:
            import traceback; print(f"[ConkyMan] load_config: {e}"); traceback.print_exc()

    def closeEvent(self, event):
        self._status_timer.stop(); self._save_config(); super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = ConkymanApp(); w.showMaximized()
    sys.exit(app.exec())
