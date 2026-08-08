#!/usr/bin/env python3
import os, re, subprocess, configparser, sys, shutil, json, locale
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QRadioButton, QButtonGroup,
    QCheckBox, QComboBox, QColorDialog, QFontDialog, QMessageBox,
    QDialog, QDialogButtonBox, QScrollArea, QFrame, QGridLayout,
    QSizePolicy, QLayout, QSlider, QSpinBox, QLineEdit, QFileDialog,
    QTextEdit, QListWidget, QListWidgetItem, QInputDialog,
)
from PySide6.QtGui  import (QIcon, QColor, QFont, QPixmap, QDesktopServices,
                             QPainter, QImage, QPalette)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QSize, QUrl, QTimer, QRect, QPoint
from PySide6.QtSvg  import QSvgRenderer
from about_theme import build_about_colors

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translations import Translator, set_language as set_global_lang
from app_identity import APP_ID, APP_NAME, install_icon_theme




SUPPORTED_LANGS = {'es', 'en', 'de', 'fr', 'pt', 'ja', 'ko', 'ca', 'it', 'tr', 'ru', 'gl'}

def _detect_system_lang():
    """Devuelve el código de idioma soportado más cercano al idioma del sistema."""
    candidates = []

    for var in ('LANGUAGE', 'LANG', 'LC_ALL', 'LC_MESSAGES'):
        val = os.environ.get(var, '')
        if val:
            for part in val.split(':'):
                code = part.split('_')[0].split('.')[0].lower()
                if code: candidates.append(code)

    try:
        loc = locale.getlocale()[0] or ''
        candidates.append(loc.split('_')[0].lower())
    except Exception:
        pass
    for c in candidates:
        if c in SUPPORTED_LANGS:
            return c
    return 'en'




DEFAULT_CONKY_LUA = r"""conky.config = {
    out_to_wayland = true, out_to_x = true,
    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'normal',
    own_window_transparent = true,
    own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'below,sticky,skip_taskbar,skip_pager',
    xinerama_head = 0, alignment = 'top_right', gap_x = 20, gap_y = 25,
    minimum_width = 200, minimum_height = 400,
    use_xft = true, font = 'Fira Sans:size=10',
    default_color = 'F5F5F5',
    color1 = 'FFFFFF',
    color2 = 'B0E0E6',
    update_interval = 1.0, double_buffer = true,
    draw_shades = false, draw_outline = false, draw_borders = false,
    draw_graph_borders = true, cpu_avg_samples = 2, net_avg_samples = 2,
    override_utf8_locale = true, format_human_readable = true,
}
conky.text = [[
${voffset 10}${font Fira Sans:weight=Normal:size=55}${color1}${time %H}${font}${voffset -20}${offset -10}${font Fira Sans:weight=Normal:size=40}${color2}${time %M}${font}
${voffset 10}${font Fira Sans Medium:size=13}${color}${time %a, %d %b %Y}${font}
${voffset 5}${font Fira Sans:Italic:size=11}${color2}${font}
${voffset 5}${hr 1}
${voffset 5}${font Fira Sans:size=10}${color}%%CPU%%: ${goto 55}${color2}${cpu}% ${alignr}${cpugraph 8,70 5B8080 B0E0E6}
${color}%%RAM%%: ${goto 55}${color2}${memperc}% ${alignr}${memgraph 8,70 5B8080 B0E0E6}
${color}%%SWAP%%: ${goto 55}${color2}${swapperc}% ${alignr}${swapbar 8,70 B0E0E6}
${color}%%DISK%%: ${goto 55}${color2}${fs_used_perc /}% ${alignr}${diskiograph 8,70 5B8080 B0E0E6}
${voffset 10}${hr 1}
${voffset 5}${color2}${font Fira Sans:Bold:size=9}%%NOWPLAYING%%:
${color}${font Fira Mono:size=9}${scroll 30 5 ${execi 5 playerctl metadata --format '{{ title }}'}}
${color2}${font Fira Mono:Italic:size=8}${scroll 30 5 ${execi 5 playerctl metadata --format '{{ artist }}'}}${font}
]]"""

MINIMAL_CONKY_LUA = r"""conky.config = {
    out_to_wayland = true, out_to_x = true,
    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'normal',
    own_window_transparent = true,
    own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'below,sticky,skip_taskbar,skip_pager',
    xinerama_head = 0, alignment = 'top_right', gap_x = 20, gap_y = 25,
    minimum_width = 200, minimum_height = 400,
    use_xft = true, font = 'Fira Sans:size=10',
    default_color = 'F5F5F5',
    color1 = 'FFFFFF',
    color2 = 'B0E0E6',
    update_interval = 1.0, double_buffer = true,
    draw_shades = false, draw_outline = false, draw_borders = false,
    draw_graph_borders = true, cpu_avg_samples = 2, net_avg_samples = 2,
    override_utf8_locale = true, format_human_readable = true,
}
conky.text = [[
${voffset 10}${font Fira Sans:weight=Normal:size=55}${color1}${time %H}${font}${voffset -20}${offset -10}${font Fira Sans:weight=Normal:size=40}${color2}${time %M}${font}
${voffset 10}${font Fira Sans Medium:size=13}${color}${time %a, %d %b %Y}${font}
]]"""

LEGACY_CONKY_LUA = r"""conky.config = {
    out_to_wayland = true,
    out_to_x = true,
    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'dock',
    own_window_transparent = true,
    own_window_argb_visual = true,
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
%%DISK%%: ${color2}${fs_used_perc /}%${color} ${diskiograph 10,20 5B8080 8AA34F}${color}  %%RAM%%: ${color2}${memperc}%${color} ${memgraph 10,20 5B8080 8AA34F}${color}
${offset 50}%%CPU%%: ${color2}${cpu}%${color} ${cpugraph 10,20 5B8080 8AA34F}${color}
]]"""

NORD_CONKY_LUA = r"""conky.config = {
    out_to_wayland = true, out_to_x = true,
    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'normal',
    own_window_transparent = true,
    own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'below,sticky,skip_taskbar,skip_pager',
    xinerama_head = 0, alignment = 'top_right', gap_x = 20, gap_y = 25,
    minimum_width = 220, minimum_height = 300,
    use_xft = true, font = 'JetBrains Mono:size=10',
    default_color = 'D8DEE9',
    color1 = 'ECEFF4',
    color2 = '88C0D0',
    update_interval = 1.0, double_buffer = true,
    draw_shades = false, draw_outline = false, draw_borders = false,
    draw_graph_borders = true, cpu_avg_samples = 2, net_avg_samples = 2,
    override_utf8_locale = true, format_human_readable = true,
}
conky.text = [[
${font JetBrains Mono:bold:size=13}${color1}%%SYSTEM%%${font}
${voffset 4}${hr 1}
${voffset 4}${color}%%CPU%%: ${goto 60}${color2}${cpu}% ${alignr}${cpugraph 8,70 5B8080 B0E0E6}
${color}%%MEMORY%%: ${goto 60}${color2}${memperc}% ${alignr}${memgraph 8,70 5B8080 B0E0E6}
${color}%%DISK%%: ${goto 60}${color2}${fs_used_perc /}% ${alignr}${diskiograph 8,70 5B8080 B0E0E6}
${voffset 8}${hr 1}
${voffset 4}${color}%%NETWORK%% ${alignr}${color2}${downspeed} / ${upspeed}
${voffset 4}${color}%%UPTIME%%: ${goto 60}${color2}${uptime}
]]"""

RETROWAVE_CONKY_LUA = r"""conky.config = {
    out_to_wayland = true, out_to_x = true,
    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'normal',
    own_window_transparent = true,
    own_window_argb_visual = true,
    own_window_argb_value = 200,
    own_window_hints = 'below,sticky,skip_taskbar,skip_pager',
    xinerama_head = 0, alignment = 'bottom_left', gap_x = 24, gap_y = 40,
    minimum_width = 260, minimum_height = 220,
    use_xft = true, font = 'Hack:size=9',
    default_color = '00F0FF',
    color1 = '00F0FF',
    color2 = 'FF2E97',
    update_interval = 1.0, double_buffer = true,
    draw_shades = false, draw_outline = false, draw_borders = true,
    draw_graph_borders = true, cpu_avg_samples = 2, net_avg_samples = 2,
    override_utf8_locale = true, format_human_readable = true,
}
conky.text = [[
${color2}${font Hack:bold:size=11}${time %H:%M:%S}${font}${color}
${voffset 4}${color2}${hr 1}
${voffset 4}${color1}%%CPU%%  ${color}${cpu}% ${alignr}${color1}${freq_g}GHz
${cpugraph 18,240 5B8080 B0E0E6}
${voffset 4}${color1}%%RAM%%  ${color}${memperc}% ${alignr}${color1}${mem}
${color2}${membar 6,240}
${voffset 6}${color2}────── ${color1}%%TOPPROCESSES%%${color2} ──────
${color}${top name 1}${alignr}${top cpu 1}%
${color}${top name 2}${alignr}${top cpu 2}%
${color}${top name 3}${alignr}${top cpu 3}%
]]"""


AUTOSTART_DESKTOP = """[Desktop Entry]
Type=Application
Name=Conky
Exec=conky -c {conky_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""

LANG_FLAGS = {
    'es': 'Español',
    'en': 'English',
    'de': 'Deutsch',
    'fr': 'Français',
    'pt': 'Português',
    'ja': '日本語',
    'ko': '한국어',
    'ca': 'Català',
    'it': 'Italiano',
    'tr': 'Türkçe',
    'ru': 'Русский',
    'gl': 'Galego',
}





CONKY_LABELS = {
    'es': {'cpu':'CPU','ram':'RAM','swap':'Swap','disk':'Disco','network':'Red',
           'system':'Sistema','memory':'Memoria','uptime':'Tiempo activo',
           'now_playing':'Reproduciendo','top_processes':'Top Procesos'},
    'en': {'cpu':'CPU','ram':'RAM','swap':'Swap','disk':'Disk','network':'Network',
           'system':'System','memory':'Memory','uptime':'Uptime',
           'now_playing':'Now Playing','top_processes':'Top Processes'},
    'de': {'cpu':'CPU','ram':'RAM','swap':'Swap','disk':'Festplatte','network':'Netzwerk',
           'system':'System','memory':'Arbeitsspeicher','uptime':'Laufzeit',
           'now_playing':'Läuft gerade','top_processes':'Top-Prozesse'},
    'fr': {'cpu':'CPU','ram':'RAM','swap':'Swap','disk':'Disque','network':'Réseau',
           'system':'Système','memory':'Mémoire','uptime':'Temps de fonctionnement',
           'now_playing':'Lecture en cours','top_processes':'Processus principaux'},
    'pt': {'cpu':'CPU','ram':'RAM','swap':'Swap','disk':'Disco','network':'Rede',
           'system':'Sistema','memory':'Memória','uptime':'Tempo ativo',
           'now_playing':'Reproduzindo','top_processes':'Principais Processos'},
    'ja': {'cpu':'CPU','ram':'RAM','swap':'スワップ','disk':'ディスク','network':'ネットワーク',
           'system':'システム','memory':'メモリ','uptime':'稼働時間',
           'now_playing':'再生中','top_processes':'上位プロセス'},
    'ko': {'cpu':'CPU','ram':'RAM','swap':'스왑','disk':'디스크','network':'네트워크',
           'system':'시스템','memory':'메모리','uptime':'가동 시간',
           'now_playing':'재생 중','top_processes':'상위 프로세스'},
    'ca': {'cpu':'CPU','ram':'RAM','swap':'Swap','disk':'Disc','network':'Xarxa',
           'system':'Sistema','memory':'Memòria','uptime':'Temps actiu',
           'now_playing':'Reproduint','top_processes':'Processos principals'},
    'it': {'cpu':'CPU','ram':'RAM','swap':'Swap','disk':'Disco','network':'Rete',
           'system':'Sistema','memory':'Memoria','uptime':'Tempo di attività',
           'now_playing':'In riproduzione','top_processes':'Processi principali'},
    'tr': {'cpu':'CPU','ram':'RAM','swap':'Takas','disk':'Disk','network':'Ağ',
           'system':'Sistem','memory':'Bellek','uptime':'Çalışma süresi',
           'now_playing':'Şimdi Çalıyor','top_processes':'En Üst İşlemler'},
    'ru': {'cpu':'CPU','ram':'RAM','swap':'Своп','disk':'Диск','network':'Сеть',
           'system':'Система','memory':'Память','uptime':'Время работы',
           'now_playing':'Сейчас играет','top_processes':'Топ процессов'},
    'gl': {'cpu':'CPU','ram':'RAM','swap':'Swap','disk':'Disco','network':'Rede',
           'system':'Sistema','memory':'Memoria','uptime':'Tempo activo',
           'now_playing':'Reproducindo','top_processes':'Top Procesos'},
}
CONKY_LABEL_TOKENS = {
    'cpu':'%%CPU%%', 'ram':'%%RAM%%', 'swap':'%%SWAP%%', 'disk':'%%DISK%%',
    'network':'%%NETWORK%%', 'system':'%%SYSTEM%%', 'memory':'%%MEMORY%%',
    'uptime':'%%UPTIME%%', 'now_playing':'%%NOWPLAYING%%',
    'top_processes':'%%TOPPROCESSES%%',
}

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





def _svg_render(path, size=28):
    """Renderiza un SVG a QPixmap sin modificar colores (para logos multicolor)."""
    if not os.path.exists(path):
        return QPixmap()
    renderer = QSvgRenderer(path)
    if not renderer.isValid():
        return QPixmap()
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    renderer.render(painter)
    painter.end()
    return QPixmap.fromImage(img)

def _svg_icon(path, size=28, color='#ffffff'):
    """Renderiza un SVG simbólico coloreándolo al color indicado (para iconos monocromo)."""
    px = _svg_render(path, size)
    if px.isNull(): return px
    img = px.toImage().convertToFormat(QImage.Format_ARGB32)
    r = int(color[1:3], 16); g = int(color[3:5], 16); b = int(color[5:7], 16)
    for y in range(img.height()):
        for x in range(img.width()):
            a = (img.pixel(x, y) >> 24) & 0xff
            if a > 0:
                img.setPixel(x, y, (a << 24) | (r << 16) | (g << 8) | b)
    return QPixmap.fromImage(img)


def _mix_color(c1: QColor, c2: QColor, t: float) -> QColor:
    """Mezcla c1 y c2 (t=0 -> c1, t=1 -> c2)."""
    r = c1.red()   + (c2.red()   - c1.red())   * t
    g = c1.green() + (c2.green() - c1.green()) * t
    b = c1.blue()  + (c2.blue()  - c1.blue())  * t
    return QColor(int(r), int(g), int(b))


def _themed_icon(name, size=16, color='#ffffff'):
    """Carga un icono simbolico del tema del sistema y lo coloriza al
    color dado, para que los botones usen los iconos del icon theme
    activo en vez de quedarse sin icono."""
    sym_name = name if name.endswith('-symbolic') else name + '-symbolic'
    icon = QIcon.fromTheme(sym_name)
    if icon.isNull():
        icon = QIcon.fromTheme(name)
    if icon.isNull():
        return QIcon()
    px = icon.pixmap(size, size)
    if px.isNull():
        return QIcon()
    img = px.toImage().convertToFormat(QImage.Format_ARGB32)
    r = int(color[1:3], 16); g = int(color[3:5], 16); b = int(color[5:7], 16)
    for y in range(img.height()):
        for x in range(img.width()):
            a = (img.pixel(x, y) >> 24) & 0xff
            if a > 0:
                img.setPixel(x, y, (a << 24) | (r << 16) | (g << 8) | b)
    return QIcon(QPixmap.fromImage(img))


def _themed_qss(pal: QPalette) -> str:
    """Genera el QSS final, calculando colores de separadores y texto secundario
    con contraste garantizado a partir del fondo y el texto reales del sistema
    (en vez de confiar en los roles 'mid'/'dark' de la paleta, que muchos temas
    dejan mal calibrados y terminan siendo casi invisibles)."""
    window = pal.color(QPalette.Window)
    text   = pal.color(QPalette.WindowText)
    sep    = _mix_color(window, text, 0.35).name()
    muted  = _mix_color(text, window, 0.40).name()
    return QSS.replace('__SEP__', sep).replace('__MUTED__', muted)



QSS = """
* { font-size: 13px; outline: none; }
QMainWindow { background: palette(window); }
QWidget      { background: palette(window); color: palette(window-text); }
QPushButton  { border: 1px solid transparent; }
QRadioButton { border: none; }
QCheckBox    { border: none; }
QLabel       { border: none; background: transparent; }

QWidget#sidebar {
    background: palette(base);
    border-right: 1px solid __SEP__;
}
QPushButton#nav_btn {
    background: transparent; color: palette(window-text);
    border: none; border-radius: 6px;
    padding: 9px 14px; text-align: left; font-size: 13px;
}
QPushButton#nav_btn:hover   { background: palette(alternate-base); color: palette(window-text); }
QPushButton#nav_btn:checked { background: palette(highlight); color: palette(highlighted-text); font-weight: bold; }

QWidget#topbar { background: palette(base); border-bottom: 1px solid __SEP__; }

QFrame#section {
    background: palette(base); border: 1px solid __SEP__; border-radius: 8px;
}
QLabel#sec_title  { color: palette(window-text); font-size: 13px; font-weight: bold; }
QLabel#sec_sub    { color: __MUTED__; font-size: 12px; }
QLabel#ver_lbl    { color: __MUTED__; font-size: 11px; }
QLabel#status_ok  { color: #57e389; font-size: 12px; font-weight: bold; }
QLabel#status_err { color: #ff7b63; font-size: 12px; font-weight: bold; }
QLabel#mono       { font-family: monospace; font-size: 11px; color: __MUTED__; }

QRadioButton { color: palette(window-text); spacing: 6px; font-size: 13px; background: transparent; }
QRadioButton::indicator {
    width: 16px; height: 16px; border-radius: 8px;
    border: 2px solid __SEP__; background: palette(base);
}
QRadioButton::indicator:checked { background: palette(highlight); border-color: palette(highlight); image: none; }
QRadioButton:hover { color: palette(highlight); }

QCheckBox { color: palette(window-text); font-size: 13px; spacing: 6px; background: transparent; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 2px solid __SEP__; background: palette(base);
}
QCheckBox::indicator:checked { background: palette(highlight); border-color: palette(highlight); }

QComboBox {
    background: palette(button); color: palette(button-text);
    border: 1px solid __SEP__; border-radius: 6px;
    padding: 4px 10px; min-width: 120px;
}
QComboBox:hover { border-color: __MUTED__; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: palette(base); color: palette(text);
    selection-background-color: palette(highlight);
    selection-color: palette(highlighted-text);
    border: 1px solid __SEP__;
}

QSlider::groove:horizontal { height: 4px; background: __SEP__; border-radius: 2px; }
QSlider::handle:horizontal {
    background: palette(highlight); width: 16px; height: 16px;
    margin: -6px 0; border-radius: 8px; border: 2px solid __MUTED__;
}
QSlider::sub-page:horizontal { background: palette(highlight); border-radius: 2px; }

QSpinBox {
    background: palette(button); color: palette(button-text);
    border: 1px solid __SEP__; border-radius: 6px;
    padding: 4px 8px; min-width: 72px;
}
QSpinBox:focus { border-color: palette(highlight); }
QSpinBox::up-button, QSpinBox::down-button { width: 18px; background: __SEP__; border-radius: 3px; }

QLineEdit {
    background: palette(base); color: palette(text);
    border: 1px solid __SEP__; border-radius: 6px; padding: 5px 10px;
}
QLineEdit:focus { border-color: palette(highlight); }

QTextEdit {
    background: palette(base); color: palette(text);
    border: 1px solid __SEP__; border-radius: 6px;
    font-family: monospace; font-size: 11px; padding: 8px;
}

QListWidget {
    background: palette(base); color: palette(text);
    border: 1px solid __SEP__; border-radius: 8px; outline: none;
}
QListWidget::item { padding: 9px 14px; border-radius: 5px; }
QListWidget::item:selected { background: palette(highlight); color: palette(highlighted-text); }
QListWidget::item:hover    { background: palette(alternate-base); }

QPushButton#tool_btn {
    background: transparent; color: palette(window-text);
    border: none; border-radius: 6px; padding: 6px 10px;
}
QPushButton#tool_btn:hover   { background: palette(alternate-base); }
QPushButton#tool_btn:pressed { background: __SEP__; }

QPushButton#action_btn {
    background: palette(button); color: palette(button-text);
    border: 1px solid rgba(128,128,128,110); border-radius: 6px; padding: 6px 16px;
}
QPushButton#action_btn:hover   { background: palette(light); border-color: __MUTED__; }
QPushButton#action_btn:pressed { background: __SEP__; }
QPushButton#action_btn:disabled{ background: palette(window); color: __MUTED__; border-color: rgba(128,128,128,60); }

QPushButton#danger_btn {
    background: palette(base); color: #ff7b63;
    border: 1px solid #6b2b2b; border-radius: 6px; padding: 6px 16px;
}
QPushButton#danger_btn:hover   { background: #4e2020; border-color: #8b3535; }
QPushButton#danger_btn:pressed { background: #2d1010; }

QPushButton#apply_btn {
    background: palette(highlight); color: palette(highlighted-text);
    border: none; border-radius: 6px;
    padding: 10px 28px; font-size: 13px; font-weight: bold;
}
QPushButton#apply_btn:hover    { background: palette(highlight); }
QPushButton#apply_btn:pressed  { background: __MUTED__; }
QPushButton#apply_btn:disabled { background: palette(button); color: __MUTED__; }

QScrollBar:vertical { background: palette(window); width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: __SEP__; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: __MUTED__; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollArea { border: none; }
QScrollArea > QWidget > QWidget { background: palette(window); }

QFrame#hsep { background: __SEP__; max-height: 1px; border: none; }
QFrame#vsep { background: __SEP__; max-width:  1px; border: none; }
"""




class Worker(QObject):
    done = Signal(bool, str)
    def __init__(self, fn): super().__init__(); self._fn = fn
    def run(self): self.done.emit(*self._fn())


class FlowLayout(QLayout):
    """Layout que acomoda sus widgets en filas y salta de linea
    automaticamente cuando no caben en el ancho disponible, en vez de
    recortarlos como hacia el QHBoxLayout fijo original."""

    def __init__(self, parent=None, margin=0, spacing=10):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items = []

    def addItem(self, item): self._items.append(item)
    def count(self): return len(self._items)
    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None
    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None
    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self): return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self): return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(),
                       margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x, y = rect.x(), rect.y()
        line_height = 0
        spacing = self._spacing
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + spacing
            if next_x - spacing > rect.right() and line_height > 0:
                x = rect.x(); y += line_height + spacing
                next_x = x + hint.width() + spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()




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
    w = QWidget(); l = QHBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0); l.setSpacing(spacing)
    for ww in widgets:
        if ww is None: l.addStretch()
        else: l.addWidget(ww)
    return w




class ConkymanApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conkyman")
        self.setMinimumSize(820, 580)

        self.base_path    = os.path.dirname(os.path.abspath(__file__))
        self.logo_path    = os.path.join(self.base_path, "conkyman.svg")
        self.config_dir   = os.path.join(os.path.expanduser("~"), ".config", "conkyman")
        self.config_file  = os.path.join(self.config_dir, "conkyman.conf")
        self.profiles_dir = os.path.join(self.config_dir, "profiles")
        self.backup_dir   = os.path.join(self.config_dir, "backups")
        for d in (self.config_dir, self.profiles_dir, self.backup_dir):
            os.makedirs(d, exist_ok=True)


        install_icon_theme(self.logo_path)
        logo_px = _svg_render(self.logo_path, 32)
        if not logo_px.isNull():
            self.setWindowIcon(QIcon(logo_px))

        first_dark = list(COLORS_DATA['dark'].keys())[0]
        self._color_sel = {'c1': ('named', first_dark), 'c2': ('named', first_dark)}
        self._btn_groups = []
        self._tr_cbs     = []
        self._dirty      = False

        self._font_nums = QFont("Fira Sans", 55)
        self._font_txt  = QFont("Fira Sans Medium", 13)


        saved_lang = self._ini('General', 'language')
        if not saved_lang:
            saved_lang = _detect_system_lang()
        self.translator = Translator(saved_lang)

        self.conkyrc_path = self._detect_conky()

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.setInterval(3000)

        self.setStyleSheet(_themed_qss(self.palette()))
        self._muted = _mix_color(self.palette().color(QPalette.WindowText),
                                  self.palette().color(QPalette.Window), 0.40).name()
        self._build_ui()
        self.load_config()
        self._status_timer.start()


    def _detect_conky(self):
        home = os.path.expanduser("~")
        for p in [os.path.join(home, ".config", "conky", "conky.lua"),
                  os.path.join(home, ".conkyrc")]:
            if os.path.exists(p): return p
        return os.path.join(home, ".config", "conky", "conky.lua")

    def _ini(self, sec, key, fallback=None):
        c = configparser.ConfigParser(); c.read(self.config_file)
        return c.get(sec, key, fallback=fallback)

    def _t(self, key, default=None):  return self.translator.get(key, default or key)
    def _tf(self, key, default=None, **kw): return self.translator.fmt(key, default, **kw)
    def _reg(self, cb): self._tr_cbs.append(cb)
    def _mode(self): return "dark" if self.mode_dark.isChecked() else "light"

    def _retranslate(self):
        for cb in self._tr_cbs:
            try: cb()
            except Exception: pass

    def _mark_dirty(self, *_):
        """Marca que hay cambios sin aplicar."""
        if not self._dirty:
            self._dirty = True

            if hasattr(self, 'btn_apply'):
                self.btn_apply.setObjectName("apply_btn_dirty")
                self.btn_apply.setStyleSheet(
                    "QPushButton#apply_btn_dirty {"
                    " background: #c97a1a; color: #ffffff;"
                    " border: none; border-radius: 6px;"
                    " padding: 10px 28px; font-size: 13px; font-weight: bold; }")

    def _mark_clean(self):
        self._dirty = False
        if hasattr(self, 'btn_apply'):
            self.btn_apply.setObjectName("apply_btn")
            self.btn_apply.setStyleSheet("")

    def _conky_pid(self):
        try:
            out = subprocess.check_output(["pgrep", "-x", "conky"], text=True).strip()
            return out.split()[0] if out else None
        except Exception:
            return None


    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        root_lay = QVBoxLayout(root)
        root_lay.setSpacing(0); root_lay.setContentsMargins(0, 0, 0, 0)


        body = QWidget(); body_lay = QHBoxLayout(body)
        body_lay.setSpacing(0); body_lay.setContentsMargins(0, 0, 0, 0)

        icon_color = self.palette().color(QPalette.WindowText).name()

        sidebar = QWidget(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(190)
        sb = QVBoxLayout(sidebar); sb.setContentsMargins(10, 16, 10, 16); sb.setSpacing(4)

        self._nav_bg = QButtonGroup(self); self._nav_bg.setExclusive(True)
        self._btn_groups.append(self._nav_bg)
        self._nav_btns = []

        nav_items = [
            ('nav_appearance', 'Apariencia',   'applications-graphics'),
            ('nav_colors',     'Colores',      'preferences-desktop-color'),
            ('nav_system',     'Sistema',      'preferences-system'),
            ('nav_profiles',   'Perfiles',     'system-users'),
            ('nav_status',     'Estado',       'utilities-system-monitor'),
            ('nav_tools',      'Herramientas', 'applications-utilities'),
            ('nav_ajustes',    'Ajustes',      'preferences-other'),
        ]
        for i, (tr_key, default, icon_name) in enumerate(nav_items):
            b = QPushButton(self._t(tr_key, default))
            b.setObjectName("nav_btn"); b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(_themed_icon(icon_name, 16, icon_color))
            b.setIconSize(QSize(16, 16))
            b.clicked.connect(lambda _=False, idx=i: self._nav(idx))
            self._nav_bg.addButton(b); self._nav_btns.append(b); sb.addWidget(b)
            self._reg(lambda btn=b, k=tr_key, d=default: btn.setText(self._t(k, d)))

        self._nav_btns[0].setChecked(True)
        sb.addStretch()

        sb.addWidget(hsep())
        sb.addSpacing(4)

        self.btn_restart = QPushButton(self._t('btn_restart', 'Reiniciar Conky'))
        self.btn_restart.setObjectName("nav_btn"); self.btn_restart.setCursor(Qt.PointingHandCursor)
        self.btn_restart.setIcon(_themed_icon('view-refresh', 16, icon_color))
        self.btn_restart.setIconSize(QSize(16, 16))
        self.btn_restart.clicked.connect(self.restart_conky)
        self._reg(lambda: self.btn_restart.setText(self._t('btn_restart', 'Reiniciar Conky')))
        sb.addWidget(self.btn_restart)

        self.btn_editor = QPushButton(self._t('btn_editor', 'Abrir editor'))
        self.btn_editor.setObjectName("nav_btn"); self.btn_editor.setCursor(Qt.PointingHandCursor)
        self.btn_editor.setIcon(_themed_icon('accessories-text-editor', 16, icon_color))
        self.btn_editor.setIconSize(QSize(16, 16))
        self.btn_editor.clicked.connect(self.open_editor)
        self._reg(lambda: self.btn_editor.setText(self._t('btn_editor', 'Abrir editor')))
        sb.addWidget(self.btn_editor)

        self.btn_about = QPushButton(self._t('btn_about', 'Acerca de'))
        self.btn_about.setObjectName("nav_btn"); self.btn_about.setCursor(Qt.PointingHandCursor)
        self.btn_about.setIcon(_themed_icon('help-about', 16, icon_color))
        self.btn_about.setIconSize(QSize(16, 16))
        self.btn_about.clicked.connect(self.show_about)
        self._reg(lambda: self.btn_about.setText(self._t('btn_about', 'Acerca de')))
        sb.addWidget(self.btn_about)

        body_lay.addWidget(sidebar); body_lay.addWidget(vsep())


        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_appearance())
        self.stack.addWidget(self._page_colors())
        self.stack.addWidget(self._page_system())
        self.stack.addWidget(self._page_profiles())
        self.stack.addWidget(self._page_status())
        self.stack.addWidget(self._page_tools())
        self.stack.addWidget(self._page_ajustes())
        body_lay.addWidget(self.stack, 1)

        root_lay.addWidget(body, 1); root_lay.addWidget(hsep())


        footer = QWidget(); footer.setFixedHeight(56)
        ft = QHBoxLayout(footer); ft.setContentsMargins(16, 0, 16, 0); ft.setSpacing(10)
        self._status_lbl = QLabel(); self._status_lbl.setObjectName("sec_sub")
        ft.addWidget(self._status_lbl)
        ft.addStretch()

        self.btn_apply = QPushButton(self._t('btn_apply','Aplicar Cambios'))
        self.btn_apply.setObjectName("apply_btn")
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.setIcon(_themed_icon('emblem-ok', 16, '#ffffff'))
        self.btn_apply.clicked.connect(self._start_apply)
        ft.addWidget(self.btn_apply)
        self._reg(lambda: self.btn_apply.setText(self._t('btn_apply','Aplicar Cambios')))
        root_lay.addWidget(footer)

    def _nav(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 5: self._refresh_status()
        if idx == 4: self._refresh_profiles()


    def _radio_section(self, parent_lay, title_key, title_default, items):
        fr, lay, lbl = section_frame(self._t(title_key, title_default))
        self._reg(lambda w=lbl, k=title_key, d=title_default: w.setText(self._t(k, d)))
        bg = QButtonGroup(fr); bg.setExclusive(True); self._btn_groups.append(bg)
        wrap = QWidget()
        wlay = FlowLayout(wrap, margin=0, spacing=16)
        for tr_key, default_lbl, attr, checked in items:
            r = QRadioButton(self._t(tr_key, default_lbl))
            r.setChecked(checked); bg.addButton(r); setattr(self, attr, r)
            r.toggled.connect(self._mark_dirty)
            self._reg(lambda w=r, k=tr_key, d=default_lbl: w.setText(self._t(k, d)))
            wlay.addWidget(r)
        lay.addWidget(wrap); parent_lay.addWidget(fr)
        return bg

    def _labeled_row(self, label_text, widget, sublabel=True):
        lbl = QLabel(label_text)
        if sublabel: lbl.setObjectName("sec_sub")
        return self._labeled_row_lbl(lbl, widget)

    def _labeled_row_lbl(self, lbl, widget):
        row = QWidget(); rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(12)
        rl.addWidget(lbl); rl.addStretch(); rl.addWidget(widget)
        return row




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


        fr, flay, lbl_ty = section_frame(self._t('typography','Tipografia [Experimental]'))
        self._reg(lambda w=lbl_ty: w.setText(self._t('typography','Tipografia [Experimental]')))
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
                    radio.toggled.connect(lambda chk, p=prefix, cn=cname: self._on_named(chk, p, cn))
                    radio.toggled.connect(self._mark_dirty)
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
                r_cust.toggled.connect(self._mark_dirty)
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

        fr_mode, fl_mode, lbl_mode = section_frame(self._t('conky_template','Plantilla Conky'))
        self._reg(lambda w=lbl_mode: w.setText(self._t('conky_template','Plantilla Conky')))
        bg_mode = QButtonGroup(fr_mode); bg_mode.setExclusive(True)
        self._btn_groups.append(bg_mode)
        mode_wrap = QWidget()
        mode_lay  = QGridLayout(mode_wrap); mode_lay.setContentsMargins(0,0,0,0)
        mode_lay.setHorizontalSpacing(16); mode_lay.setVerticalSpacing(8)
        self.mode_normal   = QRadioButton(self._t('mode_normal','Normal (Fira Sans)'))
        self.mode_minimal  = QRadioButton(self._t('mode_minimal','Minimal (solo reloj)'))
        self.mode_legacy   = QRadioButton(self._t('mode_legacy','Legacy (Roboto)'))
        self.mode_nord      = QRadioButton(self._t('mode_nord','Nord Minimalista'))
        self.mode_retrowave = QRadioButton(self._t('mode_retrowave','Retrowave'))
        self.mode_normal.setChecked(True)
        mode_items = (self.mode_normal, self.mode_minimal, self.mode_legacy,
                      self.mode_nord, self.mode_retrowave)
        for i, r in enumerate(mode_items):
            bg_mode.addButton(r); r.toggled.connect(self._mark_dirty)
            mode_lay.addWidget(r, i // 3, i % 3)
        self._reg(lambda w=self.mode_normal:  w.setText(self._t('mode_normal','Normal (Fira Sans)')))
        self._reg(lambda w=self.mode_minimal: w.setText(self._t('mode_minimal','Minimal (solo reloj)')))
        self._reg(lambda w=self.mode_legacy:  w.setText(self._t('mode_legacy','Legacy (Roboto)')))
        self._reg(lambda w=self.mode_nord:      w.setText(self._t('mode_nord','Nord Minimalista')))
        self._reg(lambda w=self.mode_retrowave: w.setText(self._t('mode_retrowave','Retrowave')))
        fl_mode.addWidget(mode_wrap); lay.addWidget(fr_mode)

        self.switch_minimal = QCheckBox(); self.switch_minimal.setVisible(False)


        fr_cl, fl_cl, lbl_cl = section_frame(self._t('conky_language','Idioma del Conky'))
        self._reg(lambda w=lbl_cl: w.setText(self._t('conky_language','Idioma del Conky')))
        lbl_cl_hint = QLabel(self._t('conky_language_hint',
            'Idioma de los textos que se muestran en el widget de Conky (independiente del idioma de la app).'))
        lbl_cl_hint.setObjectName("sec_sub"); lbl_cl_hint.setWordWrap(True)
        self._reg(lambda w=lbl_cl_hint: w.setText(self._t('conky_language_hint',
            'Idioma de los textos que se muestran en el widget de Conky (independiente del idioma de la app).')))
        fl_cl.addWidget(lbl_cl_hint)
        self.conky_lang_combo = QComboBox()
        for i, (code, label) in enumerate(LANG_FLAGS.items()):
            self.conky_lang_combo.addItem(label, code)
            if code == 'en': self.conky_lang_combo.setCurrentIndex(i)
        self.conky_lang_combo.currentIndexChanged.connect(self._mark_dirty)
        fl_cl.addWidget(self.conky_lang_combo)
        lay.addWidget(fr_cl)

        fr2, fl2, lbl2 = section_frame(self._t('monitor_head','Monitor (xinerama_head)'))
        self._reg(lambda w=lbl2: w.setText(self._t('monitor_head','Monitor (xinerama_head)')))
        self.xinerama_combo = QComboBox()
        for n in ["0","1","2","3"]: self.xinerama_combo.addItem(n, n)
        self.xinerama_combo.currentIndexChanged.connect(self._mark_dirty)
        lbl_mon = QLabel(self._t('monitor_label','Monitor principal (0, 1, 2...)')); lbl_mon.setObjectName("sec_sub")
        self._reg(lambda w=lbl_mon: w.setText(self._t('monitor_label','Monitor principal (0, 1, 2...)')))
        fl2.addWidget(self._labeled_row_lbl(lbl_mon, self.xinerama_combo))
        lay.addWidget(fr2); lay.addStretch()
        return sc

    def _page_ajustes(self):
        sc, _, lay = scrolled()

        fr_lang, fl_lang, lbl_lang = section_frame(self._t('sec_language', 'Idioma de la aplicacion'))
        self._reg(lambda w=lbl_lang: w.setText(self._t('sec_language', 'Idioma de la aplicacion')))
        row_lang = QWidget(); row_lang.setStyleSheet("background: palette(alternate-base); border-radius:6px;")
        rl_lang = QHBoxLayout(row_lang); rl_lang.setContentsMargins(12, 8, 12, 8); rl_lang.setSpacing(8)
        lbl_lang_l = QLabel(self._t('language_label', 'Idioma'))
        lbl_lang_l.setStyleSheet("font-size:11px; font-weight:bold; background:transparent;")
        self._reg(lambda w=lbl_lang_l: w.setText(self._t('language_label', 'Idioma')))
        self.btn_lang = QPushButton(LANG_FLAGS.get(self.translator.lang, self.translator.lang))
        self.btn_lang.setObjectName("action_btn")
        self.btn_lang.setCursor(Qt.PointingHandCursor)
        self.btn_lang.clicked.connect(self.show_language_dialog)
        rl_lang.addWidget(lbl_lang_l); rl_lang.addStretch(); rl_lang.addWidget(self.btn_lang)
        fl_lang.addWidget(row_lang)
        lay.addWidget(fr_lang)

        fr, flay, lbl_pos = section_frame(self._t('sec_position','Posicion y margenes'))
        self._reg(lambda w=lbl_pos: w.setText(self._t('sec_position','Posicion y margenes')))
        self.gap_x_spin = QSpinBox(); self.gap_x_spin.setRange(0, 500); self.gap_x_spin.setValue(20)
        self.gap_y_spin = QSpinBox(); self.gap_y_spin.setRange(0, 500); self.gap_y_spin.setValue(25)
        self.gap_x_spin.valueChanged.connect(self._mark_dirty)
        self.gap_y_spin.valueChanged.connect(self._mark_dirty)
        lbl_gx = QLabel(self._t('gap_x','Gap X (margen horizontal)')); lbl_gx.setObjectName("sec_sub")
        self._reg(lambda w=lbl_gx: w.setText(self._t('gap_x','Gap X (margen horizontal)')))
        lbl_gy = QLabel(self._t('gap_y','Gap Y (margen vertical)')); lbl_gy.setObjectName("sec_sub")
        self._reg(lambda w=lbl_gy: w.setText(self._t('gap_y','Gap Y (margen vertical)')))
        flay.addWidget(self._labeled_row_lbl(lbl_gx, self.gap_x_spin))
        flay.addWidget(self._labeled_row_lbl(lbl_gy, self.gap_y_spin))
        lay.addWidget(fr)

        fr2, fl2, lbl_iv2 = section_frame(self._t('sec_interval','Intervalo de actualizacion'))
        self._reg(lambda w=lbl_iv2: w.setText(self._t('sec_interval','Intervalo de actualizacion')))
        self.interval_slider = QSlider(Qt.Horizontal)
        self.interval_slider.setRange(5, 100); self.interval_slider.setValue(10)
        self.interval_slider.valueChanged.connect(self._mark_dirty)
        self.interval_lbl = QLabel("1.0 s"); self.interval_lbl.setObjectName("sec_sub")
        self.interval_lbl.setFixedWidth(40)
        self.interval_slider.valueChanged.connect(lambda v: self.interval_lbl.setText(f"{v/10:.1f} s"))
        row_iv = QWidget(); rl = QHBoxLayout(row_iv); rl.setContentsMargins(0,0,0,0); rl.setSpacing(12)
        lbl_iv = QLabel(self._t('interval_each','Cada:'))
        self._reg(lambda w=lbl_iv: w.setText(self._t('interval_each','Cada:')))
        rl.addWidget(lbl_iv); rl.addWidget(self.interval_slider, 1); rl.addWidget(self.interval_lbl)
        fl2.addWidget(row_iv); lay.addWidget(fr2)

        fr3, fl3, lbl_min = section_frame(self._t('sec_min_size','Tamano minimo de ventana'))
        self._reg(lambda w=lbl_min: w.setText(self._t('sec_min_size','Tamano minimo de ventana')))
        self.min_w_spin = QSpinBox(); self.min_w_spin.setRange(50, 2000); self.min_w_spin.setValue(200)
        self.min_h_spin = QSpinBox(); self.min_h_spin.setRange(50, 2000); self.min_h_spin.setValue(400)
        self.min_w_spin.valueChanged.connect(self._mark_dirty)
        self.min_h_spin.valueChanged.connect(self._mark_dirty)
        lbl_mw = QLabel(self._t('min_width','Ancho minimo (px)')); lbl_mw.setObjectName("sec_sub")
        self._reg(lambda w=lbl_mw: w.setText(self._t('min_width','Ancho minimo (px)')))
        lbl_mh = QLabel(self._t('min_height','Alto minimo (px)')); lbl_mh.setObjectName("sec_sub")
        self._reg(lambda w=lbl_mh: w.setText(self._t('min_height','Alto minimo (px)')))
        fl3.addWidget(self._labeled_row_lbl(lbl_mw, self.min_w_spin))
        fl3.addWidget(self._labeled_row_lbl(lbl_mh, self.min_h_spin))
        lay.addWidget(fr3)

        fr4, fl4, lbl_prev = section_frame(self._t('sec_preview','Vista previa (simulada)'))
        self._reg(lambda w=lbl_prev: w.setText(self._t('sec_preview','Vista previa (simulada)')))
        lbl_hint = QLabel(self._t('preview_hint2',"Muestra como quedara el conky con los ajustes actuales.\nPulsa 'Actualizar preview' para regenerar."))
        lbl_hint.setObjectName("sec_sub"); lbl_hint.setWordWrap(True)
        self._reg(lambda w=lbl_hint: w.setText(self._t('preview_hint2',"Muestra como quedara el conky con los ajustes actuales.\nPulsa 'Actualizar preview' para regenerar.")))
        fl4.addWidget(lbl_hint)
        self.preview_text = QTextEdit(); self.preview_text.setReadOnly(True)
        self.preview_text.setFixedHeight(160); fl4.addWidget(self.preview_text)
        btn_prev = QPushButton(self._t('btn_preview','Actualizar preview')); btn_prev.setObjectName("action_btn")
        self._reg(lambda b=btn_prev: b.setText(self._t('btn_preview','Actualizar preview')))
        btn_prev.clicked.connect(self._update_preview); fl4.addWidget(btn_prev)
        lay.addWidget(fr4); lay.addStretch()
        return sc

    def _update_preview(self):
        ok, content = self._build_content()
        self.preview_text.setPlainText(content[:2000] if ok else f"Error: {content}")

    def _page_profiles(self):
        sc, _, lay = scrolled()
        fr, flay, lbl_p = section_frame(self._t('sec_profiles','Perfiles guardados'))
        self._reg(lambda w=lbl_p: w.setText(self._t('sec_profiles','Perfiles guardados')))
        lbl_hint = QLabel(self._t('profiles_hint',"Guarda la configuracion actual con un nombre para\ncambiar entre distintos setups rapidamente."))
        lbl_hint.setObjectName("sec_sub"); lbl_hint.setWordWrap(True)
        self._reg(lambda w=lbl_hint: w.setText(self._t('profiles_hint',"Guarda la configuracion actual con un nombre para\ncambiar entre distintos setups rapidamente.")))
        flay.addWidget(lbl_hint)
        self.profile_list = QListWidget(); self.profile_list.setFixedHeight(200)
        flay.addWidget(self.profile_list)
        btns = QWidget(); bl = QHBoxLayout(btns); bl.setContentsMargins(0,0,0,0); bl.setSpacing(8)
        btn_save = QPushButton(self._t('btn_save_profile','Guardar perfil actual')); btn_save.setObjectName("action_btn")
        btn_load = QPushButton(self._t('btn_load_profile','Cargar seleccionado'));   btn_load.setObjectName("action_btn")
        btn_del  = QPushButton(self._t('btn_del_profile','Eliminar'));               btn_del.setObjectName("danger_btn")
        btn_save.clicked.connect(self._save_profile); btn_load.clicked.connect(self._load_profile)
        btn_del.clicked.connect(self._delete_profile)
        for b in (btn_save, btn_load, btn_del): bl.addWidget(b)
        self._reg(lambda b=btn_save: b.setText(self._t('btn_save_profile','Guardar perfil actual')))
        self._reg(lambda b=btn_load: b.setText(self._t('btn_load_profile','Cargar seleccionado')))
        self._reg(lambda b=btn_del:  b.setText(self._t('btn_del_profile','Eliminar')))
        bl.addStretch(); flay.addWidget(btns); lay.addWidget(fr)

        fr2, fl2, lbl_e = section_frame(self._t('sec_export','Exportar / Importar configuracion'))
        self._reg(lambda w=lbl_e: w.setText(self._t('sec_export','Exportar / Importar configuracion')))
        lbl_ei = QLabel(self._t('export_hint','Guarda o carga la configuracion de ConkyMan (.conf) y el conky.lua.'))
        lbl_ei.setObjectName("sec_sub"); lbl_ei.setWordWrap(True)
        self._reg(lambda w=lbl_ei: w.setText(self._t('export_hint','Guarda o carga la configuracion de ConkyMan (.conf) y el conky.lua.')))
        fl2.addWidget(lbl_ei)
        btns2 = QWidget(); bl2 = QHBoxLayout(btns2); bl2.setContentsMargins(0,0,0,0); bl2.setSpacing(8)
        btn_exp = QPushButton(self._t('btn_export_dots','Exportar\u2026')); btn_exp.setObjectName("action_btn")
        btn_imp = QPushButton(self._t('btn_import_dots','Importar\u2026')); btn_imp.setObjectName("action_btn")
        btn_exp.clicked.connect(self._export_config); btn_imp.clicked.connect(self._import_config)
        self._reg(lambda b=btn_exp: b.setText(self._t('btn_export_dots','Exportar\u2026')))
        self._reg(lambda b=btn_imp: b.setText(self._t('btn_import_dots','Importar\u2026')))
        bl2.addWidget(btn_exp); bl2.addWidget(btn_imp); bl2.addStretch()
        fl2.addWidget(btns2); lay.addWidget(fr2); lay.addStretch()
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
        name = name.strip(); self._save_config()
        data = {'conkyman_conf': open(self.config_file).read() if os.path.exists(self.config_file) else ''}
        if os.path.exists(self.conkyrc_path): data['conky_lua'] = open(self.conkyrc_path).read()
        with open(os.path.join(self.profiles_dir, f"{name}.json"), 'w') as f: json.dump(data, f, indent=2)
        self._refresh_profiles(); self._status_lbl.setText(self._tf('profile_saved', name=name))

    def _load_profile(self):
        item = self.profile_list.currentItem()
        if not item: return
        try:
            data = json.loads(open(item.data(Qt.UserRole)).read())
            if 'conkyman_conf' in data:
                with open(self.config_file, 'w') as f: f.write(data['conkyman_conf'])
            if 'conky_lua' in data: self._write_conky_str(data['conky_lua'])
            self.load_config(); self._status_lbl.setText(self._tf('profile_loaded', name=item.text()))
        except Exception as e:
            QMessageBox.critical(self, self._t('error_loading_profile','Error'), str(e))

    def _delete_profile(self):
        item = self.profile_list.currentItem()
        if not item: return
        r = QMessageBox.question(self, self._t('profile_del_title','Eliminar perfil'),
            self._tf('profile_del_q', name=item.text()), QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            os.remove(item.data(Qt.UserRole)); self._refresh_profiles()

    def _export_config(self):
        path, _ = QFileDialog.getSaveFileName(self, self._t('export_title','Exportar configuracion'),
            os.path.expanduser("~/conkyman_export.json"), "JSON (*.json)")
        if not path: return
        data = {}
        if os.path.exists(self.config_file): data['conkyman_conf'] = open(self.config_file).read()
        if os.path.exists(self.conkyrc_path): data['conky_lua'] = open(self.conkyrc_path).read()
        with open(path, 'w') as f: json.dump(data, f, indent=2)
        self._status_lbl.setText(self._tf('exported_to', name=os.path.basename(path)))

    def _import_config(self):
        path, _ = QFileDialog.getOpenFileName(self, self._t('import_title','Importar configuracion'),
            os.path.expanduser("~"), "JSON (*.json)")
        if not path: return
        try:
            data = json.loads(open(path).read())
            if 'conkyman_conf' in data:
                with open(self.config_file, 'w') as f: f.write(data['conkyman_conf'])
            if 'conky_lua' in data: self._write_conky_str(data['conky_lua'])
            self.load_config(); self._status_lbl.setText(self._t('config_imported','Configuracion importada.'))
        except Exception as e:
            QMessageBox.critical(self, self._t('import_error','Error al importar'), str(e))

    def _page_status(self):
        sc, _, lay = scrolled()
        fr, flay, lbl_stat = section_frame(self._t('sec_status','Estado de Conky'))
        self._reg(lambda w=lbl_stat: w.setText(self._t('sec_status','Estado de Conky')))
        row_st = QWidget(); rl = QHBoxLayout(row_st); rl.setContentsMargins(0,0,0,0); rl.setSpacing(12)
        self._conky_status_dot = QLabel("●"); self._conky_status_dot.setFixedWidth(20)
        self._conky_status_lbl = QLabel(self._t('checking','Verificando...'))
        self._conky_pid_lbl    = QLabel(""); self._conky_pid_lbl.setObjectName("sec_sub")
        rl.addWidget(self._conky_status_dot); rl.addWidget(self._conky_status_lbl)
        rl.addStretch(); rl.addWidget(self._conky_pid_lbl); flay.addWidget(row_st)
        btns_st = QWidget(); bs = QHBoxLayout(btns_st); bs.setContentsMargins(0,0,0,0); bs.setSpacing(8)
        btn_start  = QPushButton(self._t('btn_start','Iniciar'));  btn_start.setObjectName("action_btn")
        btn_stop   = QPushButton(self._t('btn_stop','Detener'));   btn_stop.setObjectName("danger_btn")
        btn_reload = QPushButton(self._t('btn_reload','Recargar')); btn_reload.setObjectName("action_btn")
        self._reg(lambda b=btn_start:  b.setText(self._t('btn_start','Iniciar')))
        self._reg(lambda b=btn_stop:   b.setText(self._t('btn_stop','Detener')))
        self._reg(lambda b=btn_reload: b.setText(self._t('btn_reload','Recargar')))
        btn_start.clicked.connect(self.restart_conky)
        btn_stop.clicked.connect(lambda: (os.system("killall conky 2>/dev/null"), self._refresh_status()))
        btn_reload.clicked.connect(lambda: (os.system("killall -SIGUSR1 conky 2>/dev/null"), self._refresh_status()))
        for b in (btn_start, btn_stop, btn_reload): bs.addWidget(b)
        bs.addStretch(); flay.addWidget(btns_st); lay.addWidget(fr)

        fr2, fl2, lbl_af = section_frame(self._t('sec_active_file','Archivo de configuracion activo'))
        self._reg(lambda w=lbl_af: w.setText(self._t('sec_active_file','Archivo de configuracion activo')))
        self._path_lbl = QLabel(self.conkyrc_path); self._path_lbl.setObjectName("mono")
        self._path_lbl.setWordWrap(True); fl2.addWidget(self._path_lbl)
        btns_p = QWidget(); bp = QHBoxLayout(btns_p); bp.setContentsMargins(0,0,0,0); bp.setSpacing(8)
        btn_change = QPushButton(self._t('btn_change_path','Cambiar ruta\u2026')); btn_change.setObjectName("action_btn")
        btn_open   = QPushButton(self._t('btn_open_folder','Abrir carpeta'));      btn_open.setObjectName("action_btn")
        btn_change.clicked.connect(self._change_conky_path)
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(self.conkyrc_path))))
        self._reg(lambda b=btn_change: b.setText(self._t('btn_change_path','Cambiar ruta\u2026')))
        self._reg(lambda b=btn_open:   b.setText(self._t('btn_open_folder','Abrir carpeta')))
        bp.addWidget(btn_change); bp.addWidget(btn_open); bp.addStretch()
        fl2.addWidget(btns_p); lay.addWidget(fr2)

        fr3, fl3, lbl_hist = section_frame(self._t('sec_history','Historial de cambios (deshacer)'))
        self._reg(lambda w=lbl_hist: w.setText(self._t('sec_history','Historial de cambios (deshacer)')))
        lbl_bk = QLabel(self._t('history_hint','Cada vez que aplicas cambios se guarda un backup automatico.'))
        lbl_bk.setObjectName("sec_sub"); lbl_bk.setWordWrap(True)
        self._reg(lambda w=lbl_bk: w.setText(self._t('history_hint','Cada vez que aplicas cambios se guarda un backup automatico.')))
        fl3.addWidget(lbl_bk)
        self.backup_list = QListWidget(); self.backup_list.setFixedHeight(130); fl3.addWidget(self.backup_list)
        btn_restore_bk = QPushButton(self._t('btn_restore_bk','Restaurar backup seleccionado'))
        btn_restore_bk.setObjectName("action_btn"); btn_restore_bk.clicked.connect(self._restore_backup)
        self._reg(lambda b=btn_restore_bk: b.setText(self._t('btn_restore_bk','Restaurar backup seleccionado')))
        fl3.addWidget(btn_restore_bk); lay.addWidget(fr3); lay.addStretch()
        return sc

    def _refresh_status(self):
        pid = self._conky_pid()
        if pid:
            self._conky_status_dot.setStyleSheet("color:#57e389;font-size:18px;")
            self._conky_status_lbl.setText(self._t('running','En ejecucion'))
            self._conky_status_lbl.setObjectName("status_ok")
            self._conky_pid_lbl.setText(f"PID: {pid}")
        else:
            self._conky_status_dot.setStyleSheet("color:#ff7b63;font-size:18px;")
            self._conky_status_lbl.setText(self._t('stopped','Detenido'))
            self._conky_status_lbl.setObjectName("status_err")
            self._conky_pid_lbl.setText("")
        self._path_lbl.setText(self.conkyrc_path)
        self.backup_list.clear()
        for f in sorted(os.listdir(self.backup_dir), reverse=True)[:15]:
            if f.endswith(".lua"):
                item = QListWidgetItem(f)
                item.setData(Qt.UserRole, os.path.join(self.backup_dir, f))
                self.backup_list.addItem(item)

    def _change_conky_path(self):
        path, _ = QFileDialog.getOpenFileName(self, self._t('select_conky_lua','Seleccionar conky.lua'),
            os.path.dirname(self.conkyrc_path), "Lua (*.lua);;Todos (*)")
        if path: self.conkyrc_path = path; self._path_lbl.setText(path)

    def _restore_backup(self):
        item = self.backup_list.currentItem()
        if not item: return
        r = QMessageBox.question(self, self._t('restore_bk_title','Restaurar backup'),
            self._tf('restore_bk_q', name=item.text()), QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            shutil.copy2(item.data(Qt.UserRole), self.conkyrc_path)
            self.restart_conky(); self._status_lbl.setText(self._t('backup_restored','Backup restaurado.'))

    def _page_tools(self):
        sc, _, lay = scrolled()

        fr0, fl0, lbl_qa = section_frame(self._t('sec_quick_actions', 'Acciones rapidas'))
        self._reg(lambda w=lbl_qa: w.setText(self._t('sec_quick_actions', 'Acciones rapidas')))
        btn_restore = QPushButton(self._t('btn_restore', 'Restaurar valores predeterminados')); btn_restore.setObjectName("danger_btn")
        btn_restore.clicked.connect(self.restore_defaults)
        self._reg(lambda b=btn_restore: b.setText(self._t('btn_restore', 'Restaurar valores predeterminados')))
        fl0.addWidget(btn_restore)
        lay.addWidget(fr0)

        fr, flay, lbl_as2 = section_frame(self._t('sec_autostart','Inicio automatico con la sesion'))
        self._reg(lambda w=lbl_as2: w.setText(self._t('sec_autostart','Inicio automatico con la sesion')))
        lbl_as = QLabel(self._t('autostart_hint',"Crea o elimina el archivo .desktop en ~/.config/autostart\npara que Conky arranque automaticamente al iniciar sesion."))
        lbl_as.setObjectName("sec_sub"); lbl_as.setWordWrap(True)
        self._reg(lambda w=lbl_as: w.setText(self._t('autostart_hint',"Crea o elimina el archivo .desktop en ~/.config/autostart\npara que Conky arranque automaticamente al iniciar sesion.")))
        flay.addWidget(lbl_as)
        row_as = QWidget(); ras = QHBoxLayout(row_as); ras.setContentsMargins(0,0,0,0); ras.setSpacing(8)
        self._autostart_lbl = QLabel(); ras.addWidget(self._autostart_lbl); ras.addStretch()
        btn_as_on  = QPushButton(self._t('btn_autostart_on','Activar autostart'));    btn_as_on.setObjectName("action_btn")
        btn_as_off = QPushButton(self._t('btn_autostart_off','Desactivar autostart')); btn_as_off.setObjectName("danger_btn")
        btn_as_on.clicked.connect(self._enable_autostart); btn_as_off.clicked.connect(self._disable_autostart)
        self._reg(lambda b=btn_as_on:  b.setText(self._t('btn_autostart_on','Activar autostart')))
        self._reg(lambda b=btn_as_off: b.setText(self._t('btn_autostart_off','Desactivar autostart')))
        ras.addWidget(btn_as_on); ras.addWidget(btn_as_off)
        flay.addWidget(row_as); self._refresh_autostart_lbl(); lay.addWidget(fr)

        fr2, fl2, lbl_inst2 = section_frame(self._t('sec_install','Verificar / instalar Conky'))
        self._reg(lambda w=lbl_inst2: w.setText(self._t('sec_install','Verificar / instalar Conky')))
        lbl_inst = QLabel(self._t('install_hint','Comprueba si Conky esta instalado en el sistema.'))
        lbl_inst.setObjectName("sec_sub")
        self._reg(lambda w=lbl_inst: w.setText(self._t('install_hint','Comprueba si Conky esta instalado en el sistema.')))
        fl2.addWidget(lbl_inst)
        row_inst = QWidget(); ri = QHBoxLayout(row_inst); ri.setContentsMargins(0,0,0,0); ri.setSpacing(8)
        self._conky_ver_lbl = QLabel(); ri.addWidget(self._conky_ver_lbl); ri.addStretch()
        btn_chk = QPushButton(self._t('btn_check','Verificar')); btn_chk.setObjectName("action_btn")
        btn_chk.clicked.connect(self._check_conky_install)
        self._reg(lambda b=btn_chk: b.setText(self._t('btn_check','Verificar')))
        ri.addWidget(btn_chk); fl2.addWidget(row_inst); lay.addWidget(fr2)
        self._check_conky_install()

        fr3, fl3, lbl_cl2 = section_frame(self._t('sec_cleanup','Limpieza'))
        self._reg(lambda w=lbl_cl2: w.setText(self._t('sec_cleanup','Limpieza')))
        lbl_cl = QLabel(self._t('cleanup_hint','Elimina todos los backups automaticos guardados por ConkyMan.'))
        lbl_cl.setObjectName("sec_sub")
        self._reg(lambda w=lbl_cl: w.setText(self._t('cleanup_hint','Elimina todos los backups automaticos guardados por ConkyMan.')))
        fl3.addWidget(lbl_cl)
        btn_clean = QPushButton(self._t('btn_clean','Limpiar backups')); btn_clean.setObjectName("danger_btn")
        btn_clean.clicked.connect(self._clean_backups)
        self._reg(lambda b=btn_clean: b.setText(self._t('btn_clean','Limpiar backups')))
        fl3.addWidget(btn_clean); lay.addWidget(fr3); lay.addStretch()
        return sc

    def _refresh_autostart_lbl(self):
        p = os.path.join(os.path.expanduser("~"), ".config", "autostart", "conky.desktop")
        if os.path.exists(p):
            self._autostart_lbl.setText(self._t('autostart_on','\u2713 Autostart activo'))
            self._autostart_lbl.setStyleSheet("color:#57e389;")
        else:
            self._autostart_lbl.setText(self._t('autostart_off','\u2717 Autostart inactivo'))
            self._autostart_lbl.setStyleSheet("color:#ff7b63;")

    def _enable_autostart(self):
        d = os.path.join(os.path.expanduser("~"), ".config", "autostart")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "conky.desktop"), 'w') as f:
            f.write(AUTOSTART_DESKTOP.format(conky_path=self.conkyrc_path))
        self._refresh_autostart_lbl()
        self._status_lbl.setText(self._t('autostart_enabled','Autostart activado.'))

    def _disable_autostart(self):
        p = os.path.join(os.path.expanduser("~"), ".config", "autostart", "conky.desktop")
        if os.path.exists(p): os.remove(p)
        self._refresh_autostart_lbl()
        self._status_lbl.setText(self._t('autostart_disabled','Autostart desactivado.'))

    def _check_conky_install(self):
        try:
            ver = subprocess.check_output(["conky","--version"], stderr=subprocess.STDOUT, text=True).split('\n')[0]
            self._conky_ver_lbl.setText(ver[:60])
            self._conky_ver_lbl.setStyleSheet("color:#57e389;font-size:11px;")
        except Exception:
            self._conky_ver_lbl.setText(self._t('conky_not_found','Conky no encontrado en el sistema.'))
            self._conky_ver_lbl.setStyleSheet("color:#ff7b63;font-size:11px;")

    def _clean_backups(self):
        r = QMessageBox.question(self, self._t('btn_clean','Limpiar backups'),
            self._t('clean_bk_q','Eliminar todos los backups automaticos?'), QMessageBox.Yes | QMessageBox.No)
        if r == QMessageBox.Yes:
            for f in os.listdir(self.backup_dir):
                try: os.remove(os.path.join(self.backup_dir, f))
                except Exception: pass
            self._status_lbl.setText(self._t('backups_cleared','Backups eliminados.'))


    def _sync_color_visibility(self):
        cur = self._mode(); other = 'light' if cur == 'dark' else 'dark'
        for p in ('c1', 'c2'):
            self._color_panels[(p, cur)].show()
            self._color_panels[(p, other)].hide()

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
            self._mark_dirty()

    def _color_bare(self, prefix):
        t, v = self._color_sel[prefix]
        if t == 'custom': return v.lstrip('#')
        colors = COLORS_DATA[self._mode()]
        return colors.get(v, list(colors.values())[0]).lstrip('#')

    def _on_mode_toggled(self, chk):
        if not chk: return
        self._sync_color_visibility(); self._restore_color('c1'); self._restore_color('c2')
        self._mark_dirty()


    def _pick_font(self, which):
        cur = self._font_nums if which == 'nums' else self._font_txt

        ok, f = QFontDialog.getFont(cur, self)
        if not ok or not isinstance(f, QFont): return
        if which == 'nums':
            self._font_nums = f
            self.font_nums_btn.setText(f"{f.family()}, {f.pointSize()}pt")
        else:
            self._font_txt = f
            self.font_txt_btn.setText(f"{f.family()}, {f.pointSize()}pt")
        self._mark_dirty()


    def _on_lang(self, lang_id):
        if not lang_id or lang_id == self.translator.lang: return
        self.translator = Translator(lang_id)
        set_global_lang(lang_id)
        if hasattr(self, 'btn_lang'):
            self.btn_lang.setText(LANG_FLAGS.get(lang_id, lang_id))
        self._save_config(); self._retranslate()

    def show_language_dialog(self):
        d = QDialog(self)
        d.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        d.setAttribute(Qt.WA_TranslucentBackground)
        d.setFixedWidth(220)

        card = QWidget(d)
        card.setObjectName("lang_popup")
        card.setStyleSheet(
            _themed_qss(self.palette()) +
            "#lang_popup { background: palette(window);"
            " border: 1px solid rgba(128,128,128,110); border-radius: 8px; }")

        outer = QVBoxLayout(d)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        bl = QVBoxLayout(card)
        bl.setContentsMargins(6, 6, 6, 6)
        bl.setSpacing(1)

        cur = self.translator.lang
        for code, label in LANG_FLAGS.items():
            row_btn = QPushButton(label)
            row_btn.setCheckable(True)
            row_btn.setChecked(code == cur)
            row_btn.setCursor(Qt.PointingHandCursor)
            row_btn.setStyleSheet(
                "QPushButton { text-align:left; padding:7px 10px; border:none; border-radius:6px;"
                " background: transparent; font-size:12px; }"
                "QPushButton:hover { background: palette(alternate-base); }"
                "QPushButton:checked { background: palette(highlight); color: palette(highlighted-text); font-weight:bold; }")

            def _pick(_checked=False, c=code, dlg=d):
                self._on_lang(c)
                dlg.accept()
            row_btn.clicked.connect(_pick)
            bl.addWidget(row_btn)

        anchor = getattr(self, 'btn_lang', None)
        if anchor is not None:
            pos = anchor.mapToGlobal(QPoint(anchor.width() - d.width(), anchor.height() + 4))
            d.move(pos)

        d.exec()



    def show_about(self):
        d = QDialog(self)
        d.setWindowTitle(self._t("about_title", "Acerca de ConkyMan"))
        d.setFixedWidth(460)
        d.setStyleSheet(_themed_qss(self.palette()))

        _C = build_about_colors()

        outer = QVBoxLayout(d)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)


        header = QWidget()
        header.setStyleSheet(f"background: {_C['header_bg']};")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(0, 24, 0, 20)
        hl.setSpacing(0)
        hl.setAlignment(Qt.AlignHCenter)

        logo_px = _svg_render(self.logo_path, 80)
        if not logo_px.isNull():
            lbl_logo = QLabel()
            lbl_logo.setPixmap(logo_px)
            lbl_logo.setAlignment(Qt.AlignCenter)
            hl.addWidget(lbl_logo)

        hl.addSpacing(6)

        lbl_name = QLabel("ConkyMan")
        lbl_name.setAlignment(Qt.AlignCenter)
        lbl_name.setStyleSheet(
            f"font-size:20px; font-weight:bold; color:{_C['header_fg']}; background:transparent;")
        hl.addWidget(lbl_name)

        lbl_ver = QLabel("© 2026 CuerdOS Project")
        lbl_ver.setAlignment(Qt.AlignCenter)
        lbl_ver.setStyleSheet(
            f"font-size:11px; color:{_C['header_sub']}; background:transparent; margin-top:1px;")
        hl.addWidget(lbl_ver)

        outer.addWidget(header)
        outer.addWidget(hsep())


        body = QWidget()
        body.setStyleSheet("background:palette(window);")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 18, 28, 18)
        bl.setSpacing(0)

        rows = [
            (self._t("about_version",  "Versión"),   "2.2-lts"),
            (self._t("about_license",  "Licencia"),  "GNU GPL v3.0"),
            (self._t("about_authors",  "Autores"),   "CuerdOS Dev. Team"),
        ]

        for i, (label, value) in enumerate(rows):
            row_w = QWidget()
            row_w.setStyleSheet(
                f"background:{_C['row_alt']}; border-radius:6px;"
                if i % 2 == 0 else
                "background:transparent;")
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(12, 8, 12, 8)
            rl.setSpacing(8)
            lbl_l = QLabel(label)
            lbl_l.setStyleSheet(
                f"color:{_C['accent']}; font-size:11px; font-weight:bold;"
                " min-width:90px; background:transparent;")
            lbl_v = QLabel(value)
            lbl_v.setStyleSheet(
                f"color:{_C['text']}; font-size:11px; background:transparent;")
            lbl_v.setWordWrap(True)
            rl.addWidget(lbl_l)
            rl.addWidget(lbl_v, 1)
            bl.addWidget(row_w)


        bl.addSpacing(12)
        lbl_desc = QLabel(self._t("about_comments", "Gestor de configuracion para Conky."))
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet(
            f"color:{_C['text_dim']}; font-size:11px; font-style:italic; background:transparent;")
        bl.addWidget(lbl_desc)

        outer.addWidget(body)
        outer.addWidget(hsep())


        footer_w = QWidget()
        footer_w.setFixedHeight(52)
        footer_w.setStyleSheet(f"background:{_C['footer_bg']};")
        fl = QHBoxLayout(footer_w)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.setSpacing(8)
        fl.addStretch()

        btn_web = QPushButton(self._t("visit_website", "Página web"))
        btn_web.setCursor(Qt.PointingHandCursor)
        btn_web.setStyleSheet(
            f"QPushButton {{ background: {_C['btn_accent_bg']}; color:{_C['btn_accent_fg']};"
            f" border: 1px solid {_C['btn_accent_br']}; border-radius: 6px; padding: 6px 16px; }}"
            f"QPushButton:hover {{ background: {_C['btn_accent_hov']}; }}"
            f"QPushButton:pressed {{ background: {_C['btn_accent_hov']}; }}")
        btn_web.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://cuerdos.github.io")))

        btn_close = QPushButton(self._t("btn_close", "Cerrar"))
        btn_close.setObjectName("action_btn")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(d.accept)

        fl.addWidget(btn_web)
        fl.addWidget(btn_close)
        outer.addWidget(footer_w)
        d.exec()
    def open_editor(self):
        script = os.path.join(self.base_path, "text.py")
        if os.path.exists(script): subprocess.Popen(["python3", script, self.conkyrc_path])
        else: subprocess.Popen(["xdg-open", self.conkyrc_path])

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
        if hasattr(self, 'conky_lang_combo'):
            idx = self.conky_lang_combo.findData('en')
            if idx >= 0: self.conky_lang_combo.setCurrentIndex(idx)
        self._write_conky(self._apply_conky_lang(DEFAULT_CONKY_LUA))
        self.pos_tr.setChecked(True); self.mode_dark.setChecked(True)
        self._font_nums = QFont("Fira Sans", 55); self.font_nums_btn.setText("Fira Sans, 55pt")
        self._font_txt = QFont("Fira Sans Medium", 13); self.font_txt_btn.setText("Fira Sans Medium, 13pt")
        self.time_24.setChecked(True); self.type_norm.setChecked(True)
        if hasattr(self,'mode_normal'): self.mode_normal.setChecked(True)
        self.switch_minimal.setChecked(False); self.xinerama_combo.setCurrentIndex(0)
        self.gap_x_spin.setValue(20); self.gap_y_spin.setValue(25)
        self.interval_slider.setValue(10); self.min_w_spin.setValue(200); self.min_h_spin.setValue(400)
        first = list(COLORS_DATA['dark'].keys())[0]
        self._color_sel = {'c1': ('named', first), 'c2': ('named', first)}
        self._sync_color_visibility(); self._restore_color('c1'); self._restore_color('c2')
        self._save_config(); self.restart_conky(); self._mark_clean()


    def _ask_unsaved(self):
        """
        Si hay cambios sin aplicar, pregunta al usuario qué hacer.
        Devuelve True si se puede continuar, False si el usuario cancela.
        """
        if not self._dirty:
            return True
        key_title = 'unsaved_title'
        key_msg   = 'unsaved_msg'
        title = self._t(key_title, 'Cambios sin aplicar')
        msg   = self._t(key_msg,   'Tienes cambios sin aplicar. ¿Qué deseas hacer?')
        box = QMessageBox(self)
        box.setWindowTitle(title); box.setText(msg)
        box.setIcon(QMessageBox.Warning)
        btn_apply  = box.addButton(self._t('btn_apply','Aplicar Cambios'), QMessageBox.AcceptRole)
        btn_discard= box.addButton(self._t('btn_discard','Descartar'),     QMessageBox.DestructiveRole)
        btn_cancel = box.addButton(self._t('btn_cancel','Cancelar'),       QMessageBox.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked == btn_apply:
            self._start_apply()
            return True
        elif clicked == btn_discard:
            self._mark_clean()
            return True
        else:
            return False


    def _write_conky(self, content):
        d = os.path.join(os.path.expanduser("~"), ".config", "conky")
        os.makedirs(d, exist_ok=True)
        if os.path.exists(self.conkyrc_path):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(self.conkyrc_path, os.path.join(self.backup_dir, f"conky_{ts}.lua"))
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


    def _start_apply(self):
        self.btn_apply.setEnabled(False)
        self._status_lbl.setText(self._t('applying','Aplicando...'))
        self._thread = QThread()
        self._worker = Worker(self._apply_logic)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.done.connect(self._on_done)
        self._worker.done.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self, ok, msg):
        self.btn_apply.setEnabled(True)
        self._status_lbl.setText(msg)
        if ok: self._mark_clean()
        self.restart_conky()
        if not ok: QMessageBox.critical(self, "ConkyMan", msg)

    def _build_content(self):
        try:
            if hasattr(self, 'mode_legacy') and self.mode_legacy.isChecked():
                content = LEGACY_CONKY_LUA
            elif hasattr(self, 'mode_minimal') and self.mode_minimal.isChecked():
                content = MINIMAL_CONKY_LUA
            elif hasattr(self, 'mode_nord') and self.mode_nord.isChecked():
                content = NORD_CONKY_LUA
            elif hasattr(self, 'mode_retrowave') and self.mode_retrowave.isChecked():
                content = RETROWAVE_CONKY_LUA
            else:
                content = DEFAULT_CONKY_LUA
            base_color = "F5F5F5" if self.mode_dark.isChecked() else "2C3E50"
            content = re.sub(r"default_color\s*=\s*'[^']*'", f"default_color = '{base_color}'", content)

            fn = self._font_nums.family(); ft = self._font_txt.family()
            content = re.sub(r"\${font [^:]+:weight=[^:]+:size=\d+}",
                             fr"${{font {fn}:weight=Normal:size=55}}", content)
            content = re.sub(r"\${font [^:]+:weight=[^:]+:size=\d+}",
                             fr"${{font {fn}:weight=Normal:size=40}}", content, count=1)
            content = re.sub(r"\${font Fira Sans Medium:size=\d+}",
                             fr"${{font {ft}:size=13}}", content)

            for attr, val in [('pos_tr','top_right'),('pos_tl','top_left'),
                               ('pos_br','bottom_right'),('pos_bl','bottom_left'),('pos_cc','middle_middle')]:
                if hasattr(self, attr) and getattr(self, attr).isChecked():
                    content = re.sub(r"alignment\s*=\s*'[^']*'", f"alignment = '{val}'", content); break

            win = 'normal'
            for attr, val in [('type_dock','dock'),('type_norm','normal'),
                               ('type_desk','desktop'),('type_panel','panel')]:
                if hasattr(self, attr) and getattr(self, attr).isChecked():
                    win = val; break
            if os.environ.get('XDG_SESSION_TYPE') == 'wayland': win = 'desktop'
            content = re.sub(r"own_window_type\s*=\s*'[^']*'", f"own_window_type = '{win}'", content)

            c1 = self._color_bare('c1'); c2 = self._color_bare('c2')
            content = re.sub(r"color1\s*=\s*'[^']*'", f"color1 = '{c1}'", content)
            content = re.sub(r"color2\s*=\s*'[^']*'", f"color2 = '{c2}'", content)

            content = re.sub(r"(cpu|mem|swap|disk)graph \d+,\d+ [0-9A-Fa-f]+ [0-9A-Fa-f]+",
                             lambda m: f"{m.group().split()[0].split('graph')[0]}graph "
                                       f"{m.group().split()[1]} 5B8080 {c2}", content)

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
            content = re.sub(r"update_interval\s*=\s*[\d.]+", f"update_interval = {interval:.1f}", content)

            mw = self.min_w_spin.value(); mh = self.min_h_spin.value()
            content = re.sub(r"minimum_width\s*=\s*\d+",  f"minimum_width = {mw}",  content)
            content = re.sub(r"minimum_height\s*=\s*\d+", f"minimum_height = {mh}", content)

            content = self._apply_conky_lang(content)

            return True, content
        except Exception as e:
            import traceback; traceback.print_exc(); return False, str(e)

    def _apply_conky_lang(self, content):
        lang = 'en'
        if hasattr(self, 'conky_lang_combo'):
            lang = self.conky_lang_combo.currentData() or 'en'
        labels = CONKY_LABELS.get(lang, CONKY_LABELS['en'])
        for key, token in CONKY_LABEL_TOKENS.items():
            content = content.replace(token, labels.get(key, CONKY_LABELS['en'][key]))
        return content

    def _apply_logic(self):
        ok, result = self._build_content()
        if not ok: return False, result
        self._write_conky(result); self._save_config()
        os.system("killall -SIGUSR1 conky 2>/dev/null")
        return True, self._t('changes_applied','Cambios aplicados.')


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
                   if hasattr(self, t) and getattr(self, t).isChecked()), 'type_norm')
        if hasattr(self,'mode_legacy') and self.mode_legacy.isChecked():
            template = 'legacy'
        elif hasattr(self,'mode_minimal') and self.mode_minimal.isChecked():
            template = 'minimal'
        elif hasattr(self,'mode_nord') and self.mode_nord.isChecked():
            template = 'nord'
        elif hasattr(self,'mode_retrowave') and self.mode_retrowave.isChecked():
            template = 'retrowave'
        else:
            template = 'normal'
        conky_lang = (self.conky_lang_combo.currentData() or 'en') \
                     if hasattr(self, 'conky_lang_combo') else 'en'
        cfg['System'] = {
            'template':    template,
            'time_format': '12'  if self.time_12.isChecked() else '24',
            'type':        ct,
            'xinerama':    self.xinerama_combo.currentData() or '0',
            'conky_lang':  conky_lang,
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
                for key, attr, default in [('font_nums','_font_nums','Fira Sans 55'),
                                           ('font_txt', '_font_txt', 'Fira Sans Medium 13')]:
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
                tmpl = s.get('template', s.get('minimal','no'))
                if tmpl == 'legacy'  and hasattr(self,'mode_legacy'):  self.mode_legacy.setChecked(True)
                elif tmpl in ('yes','minimal') and hasattr(self,'mode_minimal'): self.mode_minimal.setChecked(True)
                elif tmpl == 'nord' and hasattr(self,'mode_nord'): self.mode_nord.setChecked(True)
                elif tmpl == 'retrowave' and hasattr(self,'mode_retrowave'): self.mode_retrowave.setChecked(True)
                if s.get('time_format') == '12': self.time_12.setChecked(True)
                ct = s.get('type', 'type_norm')
                if hasattr(self, ct): getattr(self, ct).setChecked(True)
                xi = s.get('xinerama', '0')
                idx = self.xinerama_combo.findData(xi)
                if idx >= 0: self.xinerama_combo.setCurrentIndex(idx)
                if hasattr(self, 'conky_lang_combo'):
                    cl = s.get('conky_lang', 'en')
                    idx = self.conky_lang_combo.findData(cl)
                    if idx >= 0: self.conky_lang_combo.setCurrentIndex(idx)
            if 'Ajustes' in cfg:
                aj = cfg['Ajustes']
                self.gap_x_spin.setValue(int(aj.get('gap_x', 20)))
                self.gap_y_spin.setValue(int(aj.get('gap_y', 25)))
                self.interval_slider.setValue(int(aj.get('interval', 10)))
                self.min_w_spin.setValue(int(aj.get('min_w', 200)))
                self.min_h_spin.setValue(int(aj.get('min_h', 400)))
        except Exception as e:
            import traceback; print(f"[ConkyMan] load_config: {e}"); traceback.print_exc()

        self._mark_clean()

    def closeEvent(self, event):
        if not self._ask_unsaved():
            event.ignore(); return
        self._status_timer.stop(); self._save_config(); super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_ID)  # mismo app id que el editor Lua (GTK)
    w = ConkymanApp(); w.showMaximized()
    sys.exit(app.exec())
