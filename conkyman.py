#!/usr/bin/env python3

import gi
import os
import re
import subprocess
import threading
import configparser
import sys

if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
    os.environ['GDK_BACKEND'] = 'wayland,x11'

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from translations import Translator, TRANSLATIONS, set_language as set_global_lang
except ImportError:
    class Translator:
        def __init__(self, lang='es'): self.lang = lang
        def get(self, key, default=None): return default or key
        def __call__(self, key, default=None): return self.get(key, default)
    TRANSLATIONS = {'es': {}, 'en': {}, 'pt': {}, 'ca': {}}
    def set_global_lang(lang): pass

# ─────────────────────────────────────────────────────────────
# PLANTILLAS CONKY
# ─────────────────────────────────────────────────────────────
DEFAULT_CONKY_LUA = """conky.config = {
    out_to_wayland = true,
    out_to_x = true,

    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'dock',
    own_window_transparent = true,
    own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'undecorated,below,sticky,skip_taskbar,skip_pager',

    xinerama_head = 0,

    alignment = 'top_right',
    gap_x = 20,
    gap_y = 40,
    minimum_width = 200,
    minimum_height = 300,

    use_xft = true,
    font = 'Roboto:size=10',
    default_color = 'F5F5F5',
    color1 = 'E0E0E0',
    color2 = '8AA34F',

    update_interval = 1.0,
    double_buffer = true,
    draw_shades = false,
    draw_outline = false,
    draw_borders = false,
    draw_graph_borders = true,
    cpu_avg_samples = 2,
    net_avg_samples = 2,

    override_utf8_locale = true,
    format_human_readable = true,
}

conky.text = [[
${voffset -20}${font Roboto:weight=Normal:size=85}${color1}${time %H}${font}
${voffset -40}${offset 75}${font Roboto Condensed:weight=Medium:size=80}${color2}${time %M}${font}
${font Roboto Condensed:size=14}${color}${time %a, %d %b %Y}${font}
${font Roboto Condensed:size=12}${color}
Disk: ${color2}${fs_used_perc /}%${color} ${diskiograph 10,20 5B8080 8AA34F}${color}  RAM: ${color2}${memperc}%${color} ${memgraph 10,20 5B8080 8AA34F}${color}
${offset 50}CPU: ${color2}${cpu}%${color} ${cpugraph 10,20 5B8080 8AA34F}${color}
]]"""

MINIMAL_CONKY_LUA = """conky.config = {
    out_to_wayland = true,
    out_to_x = true,

    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'dock',
    own_window_transparent = true,
    own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'undecorated,below,sticky,skip_taskbar,skip_pager',

    xinerama_head = 0,

    alignment = 'top_right',
    gap_x = 20,
    gap_y = 40,
    minimum_width = 200,
    minimum_height = 300,

    use_xft = true,
    font = 'Roboto:size=10',
    default_color = 'F5F5F5',
    color1 = 'E0E0E0',
    color2 = '8AA34F',

    update_interval = 1.0,
    double_buffer = true,
    draw_shades = false,
    draw_outline = false,
    draw_borders = false,
    draw_graph_borders = true,
    cpu_avg_samples = 2,
    net_avg_samples = 2,

    override_utf8_locale = true,
    format_human_readable = true,
}
conky.text = [[
${voffset -20}${font Roboto:weight=Normal:size=85}${color1}${time %H}${font}
${voffset -40}${offset 75}${font Roboto Condensed:weight=Medium:size=80}${color2}${time %M}${font}
${font Roboto Condensed:size=14}${color}${time %a, %d %b %Y}${font}
]]"""

LANG_FLAGS = {
    'es': 'ES Español',
    'en': 'EN English',
    'pt': 'PT Português',
    'ca': 'CA Català',
}

# Paletas de color — fuente de verdad única
COLORS_DATA = {
    "light": {
        "Mentolado": "#27AE60", "Verde MATE": "#87A556", "Menta": "#6F4E37",
        "Gato Verde": "#32CD32", "Azul": "#2980B9", "Rojo": "#C0392B",
        "Naranja": "#D35400", "Amarillo": "#F1C40F", "Purpura": "#8E44AD",
        "Turquesa": "#16A085", "Rosa": "#E91E63", "Indigo": "#3F51B5", "Ambar": "#FF6F00",
    },
    "dark": {
        "Mentolado": "#8AA34F", "Verde MATE": "#9DB76F", "Cafe Menta": "#98D8C8",
        "Gato Verde": "#7FFF00", "Azul": "#5DADE2", "Rojo": "#E74C3C",
        "Naranja": "#E67E22", "Amarillo": "#F4D03F", "Purpura": "#BB8FCE",
        "Turquesa": "#48C9B0", "Rosa": "#F48FB1", "Indigo": "#7986CB", "Ambar": "#FFB74D",
    },
}


def _safe_attr(name):
    """Nombre de color -> atributo Python seguro (solo ASCII)."""
    return re.sub(r'[^a-z0-9]', '_', name.lower())


class ConkymanApp(Gtk.Window):

    # ══════════════════════════════════════════════════════════════
    # INIT
    # ══════════════════════════════════════════════════════════════
    def __init__(self):
        super().__init__(title="Conkyman")
        self.set_default_size(660, 560)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.base_path   = os.path.dirname(os.path.abspath(__file__))
        self.logo_path   = os.path.join(self.base_path, "conkyman.svg")
        self.config_dir  = os.path.join(os.path.expanduser("~"), ".config", "conkyman")
        self.config_file = os.path.join(self.config_dir, "conkyman.conf")
        os.makedirs(self.config_dir, exist_ok=True)

        try:
            self.set_icon_from_file(self.logo_path)
        except Exception:
            pass

        # ── Estado de colores independiente de los widgets ──────────
        # Formato: ('named', 'NombreColor') | ('custom', '#RRGGBB')
        # Se actualiza cuando el usuario cambia la selección,
        # y se restaura al reconstruir los paneles de color.
        first_dark = list(COLORS_DATA['dark'].keys())[0]
        self._color_sel = {
            'c1': ('named', first_dark),
            'c2': ('named', first_dark),
        }

        # Carga el idioma guardado ANTES de construir la UI
        saved_lang = self._read_ini_value('General', 'language')
        self.translator = Translator(saved_lang)

        # Registro de callbacks para traducción en tiempo real.
        # Cada elemento es un callable sin argumentos que actualiza un widget.
        self._tr_callbacks = []

        self.conkyrc_path = self._detect_conky_path()
        self._build_ui()
        self.load_config()   # restaura todo después de crear widgets

    # ══════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════
    def _detect_conky_path(self):
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".config", "conky", "conky.lua"),
            os.path.join(home, ".conkyrc"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return os.path.join(home, ".config", "conky", "conky.lua")

    def _read_ini_value(self, section, key, fallback=None):
        cfg = configparser.ConfigParser()
        cfg.read(self.config_file)
        return cfg.get(section, key, fallback=fallback)

    def _t(self, key, default=None):
        return self.translator.get(key, default or key)

    def _pad(self, w, v):
        w.set_margin_top(v); w.set_margin_bottom(v)
        w.set_margin_start(v); w.set_margin_end(v)

    def _reg(self, cb):
        """Registra un callback de traducción para ejecución diferida."""
        self._tr_callbacks.append(cb)

    def _apply_translations(self):
        """Llama todos los callbacks registrados para actualizar la UI al idioma actual."""
        for cb in self._tr_callbacks:
            try:
                cb()
            except Exception:  # pylint: disable=broad-except
                pass
        # Los paneles de color se reconstruyen con nuevo título
        self._rebuild_color_panel('c1', self._t('primary_color', 'Color Primario'))
        self._rebuild_color_panel('c2', self._t('accent_color', 'Color de Acento'))

    def _current_mode(self):
        return "dark" if self.mode_dark.get_active() else "light"

    # ══════════════════════════════════════════════════════════════
    # CONSTRUCCIÓN DE LA UI
    # ══════════════════════════════════════════════════════════════
    def _build_ui(self):
        # ── Layout raíz ──────────────────────────────────────────
        vbox_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox_main)

        # ══════════════════════════════════════════════════════════
        # TOOLBAR TRADICIONAL
        # ══════════════════════════════════════════════════════════
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)   # solo iconos; tooltip con el texto
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
        vbox_main.pack_start(toolbar, False, False, 0)

        # ── Grupo izquierdo: acciones ─────────────────────────────
        action_defs = [
            ("view-refresh-symbolic",   'restart_conky',    'Reiniciar Conky',       self.restart_conky_process),
            ("edit-clear-all-symbolic", 'restore_defaults', 'Restaurar por defecto', self.restore_defaults),
            ("document-edit-symbolic",  'open_editor',      'Editor de texto',       self.open_text_editor),
        ]
        for icon, tip_key, tip_default, cb in action_defs:
            tbtn = Gtk.ToolButton()
            tbtn.set_icon_widget(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR))
            tbtn.set_tooltip_text(self._t(tip_key, tip_default))
            tbtn.connect("clicked", cb)
            toolbar.insert(tbtn, -1)
            # Registrar callback para actualización en tiempo real
            self._reg(lambda b=tbtn, k=tip_key, d=tip_default:
                      b.set_tooltip_text(self._t(k, d)))

        # Separador expandible izquierdo → empuja el switcher al centro
        sep_left = Gtk.SeparatorToolItem()
        sep_left.set_expand(True)
        sep_left.set_draw(False)
        toolbar.insert(sep_left, -1)

        # ── Stack + StackSwitcher como ToolItem central ───────────
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        sw = Gtk.StackSwitcher()
        sw.set_stack(self.stack)
        sw.set_halign(Gtk.Align.CENTER)

        sw_item = Gtk.ToolItem()
        sw_item.add(sw)
        toolbar.insert(sw_item, -1)

        # Separador expandible derecho → empuja lang/about a la derecha
        sep_right = Gtk.SeparatorToolItem()
        sep_right.set_expand(True)
        sep_right.set_draw(False)
        toolbar.insert(sep_right, -1)

        # ── Grupo derecho: idioma ─────────────────────────────────
        lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        lang_box.set_margin_start(4)
        lang_box.set_margin_end(2)
        lang_box.pack_start(
            Gtk.Image.new_from_icon_name("preferences-desktop-locale-symbolic", Gtk.IconSize.SMALL_TOOLBAR),
            False, False, 0)
        self.lang_combo = Gtk.ComboBoxText()
        current_lang = self.translator.lang
        for i, (code, label) in enumerate(LANG_FLAGS.items()):
            self.lang_combo.append(code, label)
            if code == current_lang:
                self.lang_combo.set_active(i)
        self.lang_combo.connect("changed", self._on_language_changed)
        lang_box.pack_start(self.lang_combo, False, False, 0)

        lang_item = Gtk.ToolItem()
        lang_item.add(lang_box)
        toolbar.insert(lang_item, -1)

        # ── Grupo derecho: acerca de ──────────────────────────────
        tbtn_about = Gtk.ToolButton()
        tbtn_about.set_icon_widget(
            Gtk.Image.new_from_icon_name("help-about-symbolic", Gtk.IconSize.LARGE_TOOLBAR))
        tbtn_about.set_tooltip_text(self._t('about', 'Acerca de ConkyMan'))
        tbtn_about.connect("clicked", self.show_about)
        toolbar.insert(tbtn_about, -1)
        self._reg(lambda b=tbtn_about: b.set_tooltip_text(self._t('about', 'Acerca de ConkyMan')))

        # Separador visual antes del botón about
        sep_about = Gtk.SeparatorToolItem()
        sep_about.set_draw(True)
        toolbar.insert(sep_about, toolbar.get_item_index(tbtn_about))

        # ══════════════════════════════════════════════════════════
        # CONTENIDO DEL STACK (pestañas)
        # ══════════════════════════════════════════════════════════
        self._build_tab_appearance()
        self._build_tab_colors()
        self._build_tab_system()

        # Registrar títulos de pestañas del Stack (actualizan el StackSwitcher)
        for page_name, tr_key, default in [
            ("style",  "appearance", "Apariencia"),
            ("colors", "colors",     "Colores"),
            ("system", "system",     "Sistema"),
        ]:
            child = self.stack.get_child_by_name(page_name)
            self._reg(lambda c=child, k=tr_key, d=default:
                      self.stack.child_set_property(c, "title", self._t(k, d)))

        vbox_main.pack_start(self.stack, True, True, 0)

        # ══════════════════════════════════════════════════════════
        # BARRA INFERIOR: botón Aplicar
        # ══════════════════════════════════════════════════════════
        sep_bottom = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        vbox_main.pack_start(sep_bottom, False, False, 0)

        hbox_bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hbox_bottom.set_margin_top(8)
        hbox_bottom.set_margin_bottom(8)
        hbox_bottom.set_margin_end(12)
        self.btn_run = Gtk.Button(label=self._t('apply_changes', 'Aplicar Cambios'))
        self.btn_run.get_style_context().add_class("suggested-action")
        self.btn_run.set_size_request(180, 36)
        self.btn_run.connect("clicked", self._start_apply)
        hbox_bottom.pack_end(self.btn_run, False, False, 0)
        vbox_main.pack_start(hbox_bottom, False, False, 0)
        
        self._reg(lambda: self.btn_run.set_label(
            self._t('apply_changes', 'Aplicar Cambios')))

    # ── Tab Apariencia ────────────────────────────
    def _build_tab_appearance(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self._pad(vbox, 20)

        self._radio_section(
            vbox, 'location', "preferences-desktop-display-symbolic",
            [('top_right','pos_tr',True), ('top_left','pos_tl',False),
             ('bottom_right','pos_br',False), ('bottom_left','pos_bl',False),
             ('center','pos_cc',False)])

        self._radio_section(
            vbox, 'color_mode', "weather-clear-night-symbolic",
            [('dark_mode','mode_dark',True), ('light_mode','mode_light',False)])

        self.mode_dark.connect("toggled", self._on_mode_toggled)
        self.mode_light.connect("toggled", self._on_mode_toggled)

        # Tipografía
        frame = Gtk.Frame()
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._pad(inner, 15)
        hdr = Gtk.Box(spacing=15)
        hdr.pack_start(Gtk.Image.new_from_icon_name("preferences-desktop-font", Gtk.IconSize.DND), False, False, 0)
        lbl_typo = Gtk.Label()
        lbl_typo.set_markup(f"<b><span size='large'>{self._t('typography', 'Tipografía [Experimental]')}</span></b>")
        self._reg(lambda w=lbl_typo: w.set_markup(
            f"<b><span size='large'>{self._t('typography', 'Tipografía [Experimental]')}</span></b>"))
        hdr.pack_start(lbl_typo, False, False, 0)
        inner.pack_start(hdr, False, False, 0)
        grid = Gtk.Grid(column_spacing=20, row_spacing=10)
        lbl_fn = Gtk.Label(label=self._t('font_numbers', 'Fuente Números:'), xalign=0)
        self._reg(lambda w=lbl_fn: w.set_label(self._t('font_numbers', 'Fuente Números:')))
        grid.attach(lbl_fn, 0, 0, 1, 1)
        self.font_nums = Gtk.FontButton(); self.font_nums.set_font("Roboto 85")
        grid.attach(self.font_nums, 1, 0, 1, 1)
        lbl_ft = Gtk.Label(label=self._t('font_texts', 'Fuente Textos:'), xalign=0)
        self._reg(lambda w=lbl_ft: w.set_label(self._t('font_texts', 'Fuente Textos:')))
        grid.attach(lbl_ft, 0, 1, 1, 1)
        self.font_txt = Gtk.FontButton(); self.font_txt.set_font("Roboto Condensed 14")
        grid.attach(self.font_txt, 1, 1, 1, 1)
        inner.pack_start(grid, False, False, 0)
        frame.add(inner)
        vbox.pack_start(frame, False, False, 0)

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sc.add(vbox)
        self.stack.add_titled(sc, "style", self._t('appearance', 'Apariencia'))

    # ── Tab Colores ───────────────────────────────
    def _build_tab_colors(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self._pad(vbox, 20)

        self.frame_c1 = Gtk.Frame()
        self.inner_c1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._pad(self.inner_c1, 15)
        self.frame_c1.add(self.inner_c1)
        vbox.pack_start(self.frame_c1, False, False, 0)

        self.frame_c2 = Gtk.Frame()
        self.inner_c2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._pad(self.inner_c2, 15)
        self.frame_c2.add(self.inner_c2)
        vbox.pack_start(self.frame_c2, False, False, 0)

        # Primera construcción (sin selección guardada aún)
        self._rebuild_color_panel('c1', self._t('primary_color', 'Color Primario'))
        self._rebuild_color_panel('c2', self._t('accent_color', 'Color de Acento'))

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sc.add(vbox)
        self.stack.add_titled(sc, "colors", self._t('colors', 'Colores'))

    # ── Tab Sistema ───────────────────────────────
    def _build_tab_system(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self._pad(vbox, 20)

        self._radio_section(
            vbox, 'time_format', "preferences-system-time-symbolic",
            [('24_hours','time_24',True), ('12_hours','time_12',False)])

        self._radio_section(
            vbox, 'conky_type', "window-new-symbolic",
            [('dock','type_dock',True), ('normal','type_norm',False),
             ('desktop','type_desk',False), ('panel','type_panel',False)])

        # Modo minimal
        frame = Gtk.Frame()
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._pad(inner, 15)
        hdr = Gtk.Box(spacing=15)
        hdr.pack_start(Gtk.Image.new_from_icon_name("view-fullscreen-symbolic", Gtk.IconSize.DND), False, False, 0)
        lbl_min = Gtk.Label()
        lbl_min.set_markup(f"<b><span size='large'>{self._t('minimalist_mode', 'Modo de Visualización')}</span></b>")
        self._reg(lambda w=lbl_min: w.set_markup(
            f"<b><span size='large'>{self._t('minimalist_mode', 'Modo de Visualización')}</span></b>"))
        hdr.pack_start(lbl_min, False, False, 0)
        inner.pack_start(hdr, False, False, 0)
        hbox = Gtk.Box(spacing=10)
        lbl_sw = Gtk.Label(label=self._t('enable_minimalist', 'Activar Conky Minimal (solo reloj y fecha)'))
        self._reg(lambda w=lbl_sw: w.set_label(
            self._t('enable_minimalist', 'Activar Conky Minimal (solo reloj y fecha)')))
        hbox.pack_start(lbl_sw, False, False, 0)
        self.switch_minimal = Gtk.Switch(); self.switch_minimal.set_active(False)
        hbox.pack_end(self.switch_minimal, False, False, 0)
        inner.pack_start(hbox, False, False, 0)
        frame.add(inner)
        vbox.pack_start(frame, False, False, 0)

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sc.add(vbox)
        self.stack.add_titled(sc, "system", self._t('system', 'Sistema'))

    # ── Secciones con radio buttons ───────────────
    def _radio_section(self, container, title_key, icon, items):
        """items: [(tr_key, attr_name, active_bool), ...]"""
        frame = Gtk.Frame()
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._pad(inner, 15)
        hdr = Gtk.Box(spacing=15)
        hdr.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DND), False, False, 0)
        # Header label — registrado para traducción en tiempo real
        lbl = Gtk.Label()
        lbl.set_markup(f"<b><span size='large'>{self._t(title_key, title_key)}</span></b>")
        self._reg(lambda w=lbl, k=title_key:
                  w.set_markup(f"<b><span size='large'>{self._t(k, k)}</span></b>"))
        hdr.pack_start(lbl, False, False, 0)
        inner.pack_start(hdr, False, False, 0)
        flow = Gtk.FlowBox()
        flow.set_min_children_per_line(3)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        first = None
        for tr_key, attr, active in items:
            radio = Gtk.RadioButton.new_with_label_from_widget(first, self._t(tr_key, tr_key))
            if first is None:
                first = radio
            radio.set_active(active)
            setattr(self, attr, radio)
            # Radio label — registrado para traducción en tiempo real
            self._reg(lambda r=radio, k=tr_key: r.set_label(self._t(k, k)))
            flow.add(radio)
        inner.pack_start(flow, False, False, 5)
        frame.add(inner)
        container.pack_start(frame, False, False, 0)

    # ══════════════════════════════════════════════════════════════
    # PANEL DE COLORES
    # ══════════════════════════════════════════════════════════════
    def _rebuild_color_panel(self, prefix, title):
        """
        Destruye y recrea los widgets de un panel de color.
        Después restaura la selección desde self._color_sel[prefix].
        """
        inner = self.inner_c1 if prefix == 'c1' else self.inner_c2
        for child in inner.get_children():
            inner.remove(child)

        # Cabecera
        hdr = Gtk.Box(spacing=15)
        hdr.pack_start(Gtk.Image.new_from_icon_name("preferences-color", Gtk.IconSize.DND), False, False, 0)
        lbl = Gtk.Label()
        lbl.set_markup(f"<b><span size='large'>{title}</span></b>")
        hdr.pack_start(lbl, False, False, 0)
        inner.pack_start(hdr, False, False, 0)

        # Radio buttons de colores
        mode   = self._current_mode()
        colors = COLORS_DATA[mode]
        flow = Gtk.FlowBox()
        flow.set_min_children_per_line(4)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        first_radio = None
        for color_name in colors:
            radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, color_name)
            if first_radio is None:
                first_radio = radio
            attr = f"{prefix}_{_safe_attr(color_name)}"
            setattr(self, attr, radio)
            # Conectar señal para actualizar estado interno al instante
            radio.connect("toggled", self._on_named_color_toggled, prefix, color_name)
            flow.add(radio)
        inner.pack_start(flow, False, False, 5)
        inner.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)

        # Radio "Personalizado" + ColorButton
        hbox = Gtk.Box(spacing=10)
        radio_custom = Gtk.RadioButton.new_with_label_from_widget(
            first_radio, self._t('custom', 'Personalizado') + ':')
        picker = Gtk.ColorButton()
        setattr(self, f"{prefix}_radio_custom", radio_custom)
        setattr(self, f"{prefix}_color_picker", picker)
        radio_custom.connect("toggled", self._on_custom_color_toggled, prefix)
        picker.connect("color-set", self._on_picker_set, prefix)
        hbox.pack_start(radio_custom, False, False, 0)
        hbox.pack_start(picker, False, False, 0)
        inner.pack_start(hbox, False, False, 5)
        inner.show_all()

        # ── Restaurar selección guardada ──────────────────────────
        self._restore_color_selection(prefix)

    def _restore_color_selection(self, prefix):
        """Aplica self._color_sel[prefix] a los widgets actuales."""
        sel_type, sel_val = self._color_sel[prefix]
        mode   = self._current_mode()
        colors = COLORS_DATA[mode]

        if sel_type == 'custom':
            radio_custom = getattr(self, f"{prefix}_radio_custom")
            picker       = getattr(self, f"{prefix}_color_picker")
            radio_custom.set_active(True)
            rgba = Gdk.RGBA()
            rgba.parse(sel_val)
            picker.set_rgba(rgba)
        else:
            # named: buscar en la paleta del modo actual
            if sel_val in colors:
                attr = f"{prefix}_{_safe_attr(sel_val)}"
                radio = getattr(self, attr, None)
                if radio:
                    radio.set_active(True)
            # Si el nombre no existe en este modo, queda el primero activo (OK)

    # Señales de color
    def _on_named_color_toggled(self, radio, prefix, color_name):
        if radio.get_active():
            self._color_sel[prefix] = ('named', color_name)

    def _on_custom_color_toggled(self, radio, prefix):
        if radio.get_active():
            hex_val = self._picker_hex(prefix)
            self._color_sel[prefix] = ('custom', hex_val)

    def _on_picker_set(self, picker, prefix):
        hex_val = self._picker_hex(prefix)
        self._color_sel[prefix] = ('custom', hex_val)

    def _picker_hex(self, prefix):
        picker = getattr(self, f"{prefix}_color_picker")
        rgba = picker.get_rgba()
        return "#{:02X}{:02X}{:02X}".format(
            int(rgba.red*255), int(rgba.green*255), int(rgba.blue*255))

    def _color_hex_bare(self, prefix):
        """Devuelve el hex sin '#' listo para escribir en el conky.lua."""
        sel_type, sel_val = self._color_sel[prefix]
        if sel_type == 'custom':
            return sel_val.lstrip('#')
        mode   = self._current_mode()
        colors = COLORS_DATA[mode]
        if sel_val in colors:
            return colors[sel_val].lstrip('#')
        # Fallback: primer color de la paleta
        return list(colors.values())[0].lstrip('#')

    def _on_mode_toggled(self, radio):
        if not radio.get_active():
            return
        # Reconstruir paneles conservando la selección actual
        self._rebuild_color_panel('c1', self._t('primary_color', 'Color Primario'))
        self._rebuild_color_panel('c2', self._t('accent_color', 'Color de Acento'))

    # ══════════════════════════════════════════════════════════════
    # IDIOMA
    # ══════════════════════════════════════════════════════════════
    def _on_language_changed(self, combo):
        lang_id = combo.get_active_id()
        if not lang_id or lang_id == self.translator.lang:
            return
        self.translator = Translator(lang_id)
        set_global_lang(lang_id)
        self._save_config()
        # Actualiza en tiempo real TODOS los widgets registrados
        self._apply_translations()

    # ══════════════════════════════════════════════════════════════
    # ACCIONES
    # ══════════════════════════════════════════════════════════════
    def show_about(self, btn):
        about = Gtk.AboutDialog(transient_for=self)
        about.set_program_name("ConkyMan")
        about.set_version("1.2")
        about.set_copyright("🄯 2026 CuerdOS")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_website("https://cuerdos.github.io")
        about.set_website_label(self._t('visit_website', 'Visitar Página Web'))
        about.set_comments(self._t('about_comments', 'Control de Yelena Conky.'))
        if os.path.exists(self.logo_path):
            about.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(self.logo_path, 96, 96, True))
        about.run(); about.destroy()

    def open_text_editor(self, btn):
        script = os.path.join(self.base_path, "text.py")
        if os.path.exists(script):
            subprocess.Popen(["python3", script, self.conkyrc_path])
        else:
            subprocess.Popen(["xdg-open", self.conkyrc_path])

    def restart_conky_process(self, btn):
        os.system("killall conky 2>/dev/null")
        subprocess.Popen(["conky", "-c", self.conkyrc_path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def restore_defaults(self, btn):
        dlg = Gtk.MessageDialog(
            transient_for=self, message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=self._t('restore_defaults_title', 'ConkyMan'))
        dlg.format_secondary_text(self._t('restore_defaults_msg',
            '¿Deseas restaurar la configuración predeterminada?'))
        if dlg.run() == Gtk.ResponseType.YES:
            self._write_conky_files(DEFAULT_CONKY_LUA)
            self.pos_tr.set_active(True)
            self.mode_dark.set_active(True)
            self.font_nums.set_font("Roboto 85")
            self.font_txt.set_font("Roboto Condensed 14")
            self.time_24.set_active(True)
            self.type_dock.set_active(True)
            self.switch_minimal.set_active(False)
            first_dark = list(COLORS_DATA['dark'].keys())[0]
            self._color_sel = {
                'c1': ('named', first_dark),
                'c2': ('named', first_dark),
            }
            self._rebuild_color_panel('c1', self._t('primary_color', 'Color Primario'))
            self._rebuild_color_panel('c2', self._t('accent_color', 'Color de Acento'))
            self._save_config()
            self.restart_conky_process(None)
        dlg.destroy()

    # ══════════════════════════════════════════════════════════════
    # ESCRITURA DE ARCHIVOS CONKY (DUAL)
    # ══════════════════════════════════════════════════════════════
    def _write_conky_files(self, content):
        """Escribe conky.lua Y conky.conf en ~/.config/conky/"""
        conky_dir = os.path.join(os.path.expanduser("~"), ".config", "conky")
        os.makedirs(conky_dir, exist_ok=True)
        for fname in ("conky.lua", "conky.conf"):
            path = os.path.join(conky_dir, fname)
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                print(f"[ConkyMan] Error al escribir {fname}: {e}")
        self.conkyrc_path = os.path.join(conky_dir, "conky.lua")

    # ══════════════════════════════════════════════════════════════
    # APLICAR CAMBIOS
    # ══════════════════════════════════════════════════════════════
    def _start_apply(self, btn):
        self.btn_run.set_sensitive(False)
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        ok, msg = self._apply_logic()
        GLib.idle_add(self._finish, ok, msg)

    def _finish(self, ok, msg):
        self.btn_run.set_sensitive(True)
        self.restart_conky_process(None)
        dlg = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.INFO if ok else Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text="ConkyMan")
        dlg.format_secondary_text(msg)
        dlg.run(); dlg.destroy()

    def _apply_logic(self):
        try:
            content = MINIMAL_CONKY_LUA if self.switch_minimal.get_active() else DEFAULT_CONKY_LUA

            # Modo Dark/Light
            is_dark = self.mode_dark.get_active()
            base_color = "F5F5F5" if is_dark else "2C3E50"
            content = re.sub(r"default_color\s*=\s*'[^']*'",
                             f"default_color = '{base_color}'", content)

            # Fuentes
            f_nums = self.font_nums.get_font().rsplit(' ', 1)[0]
            f_txt  = self.font_txt.get_font().rsplit(' ', 1)[0]
            content = re.sub(r"\${font [^:]+:weight=[^:]+:size=8([05])}",
                             fr"${{font {f_nums}:weight=Normal:size=8\1}}", content)
            content = re.sub(r"\${font [^:]+:size=1([24])}",
                             fr"${{font {f_txt}:size=1\1}}", content)

            # Posición
            pos_map = {
                'pos_tr': 'top_right',    'pos_tl': 'top_left',
                'pos_br': 'bottom_right', 'pos_bl': 'bottom_left',
                'pos_cc': 'middle_middle',
            }
            for attr, val in pos_map.items():
                if getattr(self, attr).get_active():
                    content = re.sub(r"alignment\s*=\s*'[^']*'",
                                     f"alignment = '{val}'", content)
                    break

            # Tipo de ventana
            type_map = {
                'type_dock': 'dock', 'type_norm': 'normal',
                'type_desk': 'desktop', 'type_panel': 'panel',
            }
            win_type = 'dock'
            for attr, val in type_map.items():
                if getattr(self, attr).get_active():
                    win_type = val; break

            # Wayland sobreescribe el tipo
            if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
                win_type = 'desktop'
            content = re.sub(r"own_window_type\s*=\s*'[^']*'",
                             f"own_window_type = '{win_type}'", content)

            # Colores — leídos desde self._color_sel (fuente de verdad)
            c1_hex = self._color_hex_bare('c1')
            c2_hex = self._color_hex_bare('c2')
            content = re.sub(r"color1\s*=\s*'[^']*'", f"color1 = '{c1_hex}'", content)
            content = re.sub(r"color2\s*=\s*'[^']*'", f"color2 = '{c2_hex}'", content)

            # Gráficos sincronizados con c2
            content = re.sub(r"graph 10,20 [0-9A-Fa-f]+ [0-9A-Fa-f]+",
                             f"graph 10,20 5B8080 {c2_hex}", content)

            # Formato hora
            if self.time_12.get_active():
                content = content.replace("%H", "%I %p")
            else:
                content = content.replace("%I %p", "%H").replace("%I", "%H")

            # Escribir en conky.lua Y conky.conf
            self._write_conky_files(content)

            # Guardar preferencias de la app
            self._save_config()

            os.system("killall -SIGUSR1 conky 2>/dev/null")
            return True, self._t('changes_applied', 'Cambios aplicados con éxito.')
        except Exception as e:
            import traceback; traceback.print_exc()
            return False, str(e)

    # ══════════════════════════════════════════════════════════════
    # PERSISTENCIA COMPLETA  (save / load)
    # ══════════════════════════════════════════════════════════════
    def _save_config(self):
        """
        Guarda TODAS las secciones:
          [General]    language
          [Appearance] mode, font_nums, font_txt, position
          [Colors]     c1_type, c1_value, c2_type, c2_value
          [System]     minimal, time_format, type
        """
        cfg = configparser.ConfigParser()

        cfg['General'] = {'language': self.translator.lang}

        pos = next(
            (p for p in ['pos_tr','pos_tl','pos_br','pos_bl','pos_cc']
             if hasattr(self, p) and getattr(self, p).get_active()),
            'pos_tr')
        cfg['Appearance'] = {
            'mode':      'dark' if self.mode_dark.get_active() else 'light',
            'font_nums': self.font_nums.get_font(),
            'font_txt':  self.font_txt.get_font(),
            'position':  pos,
        }

        # Actualizar self._color_sel desde los widgets antes de guardar
        for prefix in ('c1', 'c2'):
            radio_custom = getattr(self, f"{prefix}_radio_custom", None)
            if radio_custom and radio_custom.get_active():
                self._color_sel[prefix] = ('custom', self._picker_hex(prefix))
            else:
                mode = self._current_mode()
                for color_name in COLORS_DATA[mode]:
                    attr = f"{prefix}_{_safe_attr(color_name)}"
                    radio = getattr(self, attr, None)
                    if radio and radio.get_active():
                        self._color_sel[prefix] = ('named', color_name)
                        break

        c1t, c1v = self._color_sel['c1']
        c2t, c2v = self._color_sel['c2']
        cfg['Colors'] = {
            'c1_type': c1t, 'c1_value': c1v,
            'c2_type': c2t, 'c2_value': c2v,
        }

        ctype = next(
            (t for t in ['type_dock','type_norm','type_desk','type_panel']
             if hasattr(self, t) and getattr(self, t).get_active()),
            'type_dock')
        cfg['System'] = {
            'minimal':     'yes' if self.switch_minimal.get_active() else 'no',
            'time_format': '12'  if self.time_12.get_active() else '24',
            'type':        ctype,
        }

        with open(self.config_file, 'w') as f:
            cfg.write(f)

    def load_config(self):
        """
        Restaura TODAS las secciones guardadas.
        Se llama una sola vez en __init__, DESPUÉS de construir los widgets.
        """
        if not os.path.exists(self.config_file):
            return
        cfg = configparser.ConfigParser()
        cfg.read(self.config_file)

        try:
            # ── Appearance ─────────────────────────────────────────
            if 'Appearance' in cfg:
                a = cfg['Appearance']
                if a.get('mode') == 'light':
                    self.mode_light.set_active(True)
                self.font_nums.set_font(a.get('font_nums', 'Roboto 85'))
                self.font_txt.set_font( a.get('font_txt',  'Roboto Condensed 14'))
                pos = a.get('position', 'pos_tr')
                if hasattr(self, pos):
                    getattr(self, pos).set_active(True)

            # ── Colors: primero cargamos el estado interno ──────────
            # y DESPUÉS reconstruimos los paneles para que se aplique.
            if 'Colors' in cfg:
                c = cfg['Colors']
                for prefix in ('c1', 'c2'):
                    t   = c.get(f'{prefix}_type',  'named')
                    val = c.get(f'{prefix}_value', '')
                    if t in ('named', 'custom') and val:
                        self._color_sel[prefix] = (t, val)

            # Reconstruir paneles CON la selección recién cargada
            # (el modo ya fue configurado arriba, así que _current_mode() es correcto)
            self._rebuild_color_panel('c1', self._t('primary_color', 'Color Primario'))
            self._rebuild_color_panel('c2', self._t('accent_color',  'Color de Acento'))

            # ── System ──────────────────────────────────────────────
            if 'System' in cfg:
                s = cfg['System']
                self.switch_minimal.set_active(s.get('minimal') == 'yes')
                if s.get('time_format') == '12':
                    self.time_12.set_active(True)
                ctype = s.get('type', 'type_dock')
                if hasattr(self, ctype):
                    getattr(self, ctype).set_active(True)

        except Exception as e:
            import traceback
            print(f"[ConkyMan] Error en load_config: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    app = ConkymanApp()
    app.connect("destroy", lambda w: (app._save_config(), Gtk.main_quit()))
    app.show_all()
    Gtk.main()