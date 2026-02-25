#!/usr/bin/env python3
"""ConkyMan — Editor de texto manual para configuraciones de Conky."""

import gi
import sys
import os
import configparser

gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Pango, Gdk, GLib

# ─────────────────────────────────────────────────────────────
# TRADUCCIONES
# ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from translations import Translator

    def _load_saved_lang():
        cfg_file = os.path.join(
            os.path.expanduser("~"), ".config", "conkyman", "conkyman.conf")
        if os.path.exists(cfg_file):
            cfg = configparser.ConfigParser()
            cfg.read(cfg_file)
            return cfg.get('General', 'language', fallback=None)
        return None

    _tr = Translator(_load_saved_lang())
    def t(key, default=None):
        return _tr.get(key, default or key)

except ImportError:
    def t(key, default=None):  # pylint: disable=unused-argument
        return default or key


# ─────────────────────────────────────────────────────────────
# EDITOR
# ─────────────────────────────────────────────────────────────
class ConkyEditor(Gtk.Window):

    def __init__(self, file_path=None):
        super().__init__(title=t('editor_title', 'Editor de Configuración - ConkyMan'))
        self.set_default_size(700, 600)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.file_path = (
            file_path if file_path and os.path.exists(file_path)
            else self._detect_conky_path()
        )

        # ── Intentar cargar icono ─────────────────
        base = os.path.dirname(os.path.abspath(__file__))
        logo = os.path.join(base, "conkyman.svg")
        try:
            self.set_icon_from_file(logo)
        except Exception:  # pylint: disable=broad-except
            pass

        self._build_ui()
        self._load_file_content()

    # ─────────────────────────────────────────────
    # DETECCIÓN DE RUTA
    # ─────────────────────────────────────────────
    def _detect_conky_path(self):
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".config", "conky", "conky.lua"),
            os.path.join(home, ".config", "conky", "conky.conf"),
            os.path.join(home, ".conkyrc"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return candidates[0]

    # ─────────────────────────────────────────────
    # CONSTRUCCIÓN DE LA UI
    # ─────────────────────────────────────────────
    def _build_ui(self):
        # Título nativo (barra del gestor de ventanas)
        fname = os.path.basename(self.file_path) if self.file_path else t('file_not_found', 'Archivo no encontrado')
        self.set_title(f"{t('manual_editor', 'Editor Manual')} — {fname}")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        # ══════════════════════════════════════════
        # TOOLBAR
        # ══════════════════════════════════════════
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
        vbox.pack_start(toolbar, False, False, 0)

        def _tbtn(icon, tip, cb):
            btn = Gtk.ToolButton()
            btn.set_icon_widget(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR))
            btn.set_tooltip_text(tip)
            btn.connect("clicked", cb)
            toolbar.insert(btn, -1)
            return btn

        def _sep(expand=False, draw=True):
            s = Gtk.SeparatorToolItem()
            s.set_expand(expand)
            s.set_draw(draw)
            toolbar.insert(s, -1)

        # Guardar
        _tbtn("document-save-symbolic",
              t('save_changes', 'Guardar cambios'),
              self._on_save)

        _sep()

        # Recargar
        _tbtn("document-revert-symbolic",
              t('reload_file', 'Recargar archivo'),
              self._on_reload)

        _sep()

        # Buscar/Reemplazar (toggle)
        self.tbtn_find = Gtk.ToggleToolButton()
        self.tbtn_find.set_icon_widget(
            Gtk.Image.new_from_icon_name("edit-find-replace-symbolic", Gtk.IconSize.LARGE_TOOLBAR))
        self.tbtn_find.set_tooltip_text(t('find_replace', 'Buscar y Reemplazar'))
        self.tbtn_find.connect("toggled", self._on_find_toggled)
        toolbar.insert(self.tbtn_find, -1)

        _sep()

        # Word wrap (toggle)
        self.tbtn_wrap = Gtk.ToggleToolButton()
        self.tbtn_wrap.set_icon_widget(
            Gtk.Image.new_from_icon_name("format-justify-left-symbolic", Gtk.IconSize.LARGE_TOOLBAR))
        self.tbtn_wrap.set_tooltip_text(t('word_wrap', 'Ajuste de línea'))
        self.tbtn_wrap.set_active(False)
        self.tbtn_wrap.connect("toggled", self._on_wrap_toggled)
        toolbar.insert(self.tbtn_wrap, -1)

        # Separador expandible → empuja el label de ruta a la derecha
        _sep(expand=True, draw=False)

        # Label con ruta del archivo (derecha)
        self.lbl_path = Gtk.Label()
        self.lbl_path.set_ellipsize(Pango.EllipsizeMode.START)
        self.lbl_path.set_max_width_chars(40)
        self.lbl_path.set_markup(
            f"<small><span foreground='#888888'>{self.file_path or ''}</span></small>")
        path_item = Gtk.ToolItem()
        path_item.add(self.lbl_path)
        toolbar.insert(path_item, -1)

        _sep(draw=False)  # pequeño margen derecho

        # ══════════════════════════════════════════
        # BARRA DE BUSCAR / REEMPLAZAR (oculta al inicio)
        # ══════════════════════════════════════════
        self.find_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.find_bar.set_margin_start(8)
        self.find_bar.set_margin_end(8)
        self.find_bar.set_margin_top(4)
        self.find_bar.set_margin_bottom(4)

        self.entry_find = Gtk.SearchEntry()
        self.entry_find.set_placeholder_text(t('find_placeholder', 'Buscar...'))
        self.entry_find.set_size_request(180, -1)
        self.entry_find.connect("activate",       self._on_find_next)
        self.entry_find.connect("search-changed", self._on_search_changed)
        self.find_bar.pack_start(self.entry_find, False, False, 0)

        self.entry_replace = Gtk.Entry()
        self.entry_replace.set_placeholder_text(t('replace_placeholder', 'Reemplazar por...'))
        self.entry_replace.set_size_request(180, -1)
        self.find_bar.pack_start(self.entry_replace, False, False, 0)

        btn_replace = Gtk.Button(label=t('replace_one', 'Reemplazar'))
        btn_replace.connect("clicked", self._on_replace_one)
        self.find_bar.pack_start(btn_replace, False, False, 0)

        btn_replace_all = Gtk.Button(label=t('replace_all', 'Reemplazar todo'))
        btn_replace_all.connect("clicked", self._on_replace_all)
        self.find_bar.pack_start(btn_replace_all, False, False, 0)

        self.lbl_find_status = Gtk.Label()
        self.lbl_find_status.set_margin_start(8)
        self.find_bar.pack_start(self.lbl_find_status, False, False, 0)

        # Botón cerrar la barra de búsqueda
        btn_close_find = Gtk.Button()
        btn_close_find.set_relief(Gtk.ReliefStyle.NONE)
        btn_close_find.set_image(
            Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU))
        btn_close_find.set_tooltip_text(t('close', 'Cerrar'))
        btn_close_find.connect("clicked", lambda _b: self._hide_find_bar())
        self.find_bar.pack_end(btn_close_find, False, False, 0)

        vbox.pack_start(self.find_bar, False, False, 0)
        # Oculta por defecto (no show_all en find_bar todavía)

        # ══════════════════════════════════════════
        # ÁREA DE TEXTO
        # ══════════════════════════════════════════
        self.text_view = Gtk.TextView()
        self.text_view.set_left_margin(10)
        self.text_view.set_right_margin(10)
        self.text_view.set_top_margin(10)
        self.text_view.set_bottom_margin(10)
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.text_view.modify_font(Pango.FontDescription("Monospace 11"))

        # Colorear fondo de búsqueda
        self._tag_found = self.text_view.get_buffer().create_tag(
            "found", background="#FFFF00", foreground="#000000")
        self._tag_current = self.text_view.get_buffer().create_tag(
            "current", background="#FF8C00", foreground="#FFFFFF")

        # Seguimiento de cursor para statusbar
        self.text_view.get_buffer().connect("mark-set", self._on_cursor_moved)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.add(self.text_view)
        vbox.pack_start(scrolled, True, True, 0)

        # ══════════════════════════════════════════
        # BARRA DE ESTADO
        # ══════════════════════════════════════════
        sep_status = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(sep_status, False, False, 0)

        self.statusbar = Gtk.Label()
        self.statusbar.set_xalign(0)
        self.statusbar.set_margin_start(8)
        self.statusbar.set_margin_top(3)
        self.statusbar.set_margin_bottom(3)
        self.statusbar.set_markup("<small> </small>")
        vbox.pack_start(self.statusbar, False, False, 0)

        # Teclas de acceso rápido
        self.connect("key-press-event", self._on_key_press)

        self._update_statusbar()

    # ─────────────────────────────────────────────
    # CARGA Y GUARDADO
    # ─────────────────────────────────────────────
    def _load_file_content(self):
        if not self.file_path or not os.path.exists(self.file_path):
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.text_view.get_buffer().set_text(content)
            self._update_statusbar()
        except Exception as e:  # pylint: disable=broad-except
            self._show_msg(f"{t('read_error', 'Error al leer')}: {e}", Gtk.MessageType.ERROR)

    def _on_reload(self, _btn):  # pylint: disable=unused-argument
        """Recarga el archivo desde disco, descartando cambios no guardados."""
        dlg = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=t('editor_conkyman', 'Editor ConkyMan'),
        )
        dlg.format_secondary_text(
            t('reload_confirm', '¿Recargar el archivo y descartar los cambios no guardados?'))
        if dlg.run() == Gtk.ResponseType.YES:
            self._load_file_content()
        dlg.destroy()

    def _on_save(self, _btn):  # pylint: disable=unused-argument
        buf = self.text_view.get_buffer()
        start, end = buf.get_bounds()
        text = buf.get_text(start, end, True)

        conky_dir = os.path.join(os.path.expanduser("~"), ".config", "conky")
        os.makedirs(conky_dir, exist_ok=True)

        targets = [
            os.path.join(conky_dir, "conky.lua"),
            os.path.join(conky_dir, "conky.conf"),
        ]
        # Si el archivo de origen está fuera de esa carpeta, también lo escribimos
        if self.file_path and self.file_path not in targets:
            targets.insert(0, self.file_path)

        errors = []
        for path in targets:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception as e:  # pylint: disable=broad-except
                errors.append(f"{os.path.basename(path)}: {e}")

        if errors:
            self._show_msg(
                f"{t('save_error', 'Error al guardar')}:\n" + "\n".join(errors),
                Gtk.MessageType.ERROR)
        else:
            self._show_msg(t('file_saved', 'Archivo guardado correctamente.'),
                           Gtk.MessageType.INFO)
            os.system("killall -SIGUSR1 conky 2>/dev/null")

    # ─────────────────────────────────────────────
    # WORD WRAP
    # ─────────────────────────────────────────────
    def _on_wrap_toggled(self, btn):
        mode = Gtk.WrapMode.WORD_CHAR if btn.get_active() else Gtk.WrapMode.NONE
        self.text_view.set_wrap_mode(mode)

    # ─────────────────────────────────────────────
    # BUSCAR / REEMPLAZAR
    # ─────────────────────────────────────────────
    def _on_find_toggled(self, btn):
        if btn.get_active():
            self.find_bar.show_all()
            self.entry_find.grab_focus()
        else:
            self._hide_find_bar()

    def _hide_find_bar(self):
        self.find_bar.hide()
        self.tbtn_find.set_active(False)
        self._clear_highlights()
        self.text_view.grab_focus()

    def _on_key_press(self, _widget, event):
        # Ctrl+F → abrir buscar
        if (event.state & Gdk.ModifierType.CONTROL_MASK and
                event.keyval == Gdk.KEY_f):
            self.tbtn_find.set_active(True)
            return True
        # Ctrl+S → guardar
        if (event.state & Gdk.ModifierType.CONTROL_MASK and
                event.keyval == Gdk.KEY_s):
            self._on_save(None)
            return True
        # Escape → cerrar buscar si está abierto
        if event.keyval == Gdk.KEY_Escape and self.tbtn_find.get_active():
            self._hide_find_bar()
            return True
        return False

    def _on_search_changed(self, _entry):
        self._highlight_all()

    def _on_find_next(self, _entry):
        self._find_next()

    def _get_search_text(self):
        return self.entry_find.get_text()

    def _highlight_all(self):
        """Marca todas las ocurrencias en amarillo."""
        buf = self.text_view.get_buffer()
        start, end = buf.get_bounds()
        buf.remove_tag(self._tag_found,   start, end)
        buf.remove_tag(self._tag_current, start, end)

        needle = self._get_search_text()
        if not needle:
            self.lbl_find_status.set_text("")
            return

        count = 0
        itr = buf.get_start_iter()
        while True:
            match = itr.forward_search(needle, Gtk.TextSearchFlags.CASE_INSENSITIVE, None)
            if not match:
                break
            m_start, m_end = match
            buf.apply_tag(self._tag_found, m_start, m_end)
            count += 1
            itr = m_end

        if count == 0:
            self.lbl_find_status.set_markup(
                f"<span foreground='red'>{t('not_found', 'No encontrado')}</span>")
        else:
            self.lbl_find_status.set_text(f"{count} ↓")

    def _find_next(self):
        """Avanza a la siguiente ocurrencia y la resalta en naranja."""
        buf    = self.text_view.get_buffer()
        needle = self._get_search_text()
        if not needle:
            return

        # Empieza desde la posición actual del cursor
        cursor = buf.get_iter_at_mark(buf.get_insert())
        match  = cursor.forward_search(needle, Gtk.TextSearchFlags.CASE_INSENSITIVE, None)

        # Si no hay más hacia adelante, vuelve al inicio (wrap-around)
        if not match:
            cursor = buf.get_start_iter()
            match  = cursor.forward_search(needle, Gtk.TextSearchFlags.CASE_INSENSITIVE, None)

        if match:
            m_start, m_end = match
            # Quitar resaltado naranja anterior
            s, e = buf.get_bounds()
            buf.remove_tag(self._tag_current, s, e)
            buf.apply_tag(self._tag_current, m_start, m_end)
            buf.place_cursor(m_start)
            self.text_view.scroll_to_mark(buf.get_insert(), 0.1, True, 0.5, 0.5)

    def _clear_highlights(self):
        buf = self.text_view.get_buffer()
        start, end = buf.get_bounds()
        buf.remove_tag(self._tag_found,   start, end)
        buf.remove_tag(self._tag_current, start, end)
        self.lbl_find_status.set_text("")

    def _on_replace_one(self, _btn):  # pylint: disable=unused-argument
        buf     = self.text_view.get_buffer()
        needle  = self._get_search_text()
        replace = self.entry_replace.get_text()
        if not needle:
            return

        cursor = buf.get_iter_at_mark(buf.get_insert())
        match  = cursor.forward_search(needle, Gtk.TextSearchFlags.CASE_INSENSITIVE, None)
        if not match:
            cursor = buf.get_start_iter()
            match  = cursor.forward_search(needle, Gtk.TextSearchFlags.CASE_INSENSITIVE, None)

        if match:
            m_start, m_end = match
            buf.begin_user_action()
            buf.delete(m_start, m_end)
            buf.insert(m_start, replace)
            buf.end_user_action()
            self._highlight_all()

    def _on_replace_all(self, _btn):  # pylint: disable=unused-argument
        buf     = self.text_view.get_buffer()
        needle  = self._get_search_text()
        replace = self.entry_replace.get_text()
        if not needle:
            return

        count = 0
        buf.begin_user_action()
        itr = buf.get_start_iter()
        while True:
            match = itr.forward_search(needle, Gtk.TextSearchFlags.CASE_INSENSITIVE, None)
            if not match:
                break
            m_start, m_end = match
            buf.delete(m_start, m_end)
            buf.insert(m_start, replace)
            itr = buf.get_iter_at_offset(m_start.get_offset() + len(replace))
            count += 1
        buf.end_user_action()

        self._highlight_all()
        replaced_label = t('replaced_n', 'reemplazos realizados')
        self.lbl_find_status.set_text(f"{count} {replaced_label}")

    # ─────────────────────────────────────────────
    # BARRA DE ESTADO
    # ─────────────────────────────────────────────
    def _on_cursor_moved(self, buf, _loc, mark):
        if mark == buf.get_insert():
            GLib.idle_add(self._update_statusbar)

    def _update_statusbar(self):
        buf    = self.text_view.get_buffer()
        cursor = buf.get_iter_at_mark(buf.get_insert())
        line   = cursor.get_line() + 1
        col    = cursor.get_line_offset() + 1
        lines  = buf.get_line_count()
        tpl    = t('line_col', 'Línea {line}, Col {col}  |  {lines} líneas')
        self.statusbar.set_markup(
            f"<small>{tpl.format(line=line, col=col, lines=lines)}</small>")

    # ─────────────────────────────────────────────
    # MENSAJES
    # ─────────────────────────────────────────────
    def _show_msg(self, msg, msg_type):
        dlg = Gtk.MessageDialog(
            transient_for=self,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=t('editor_conkyman', 'Editor ConkyMan'),
        )
        dlg.format_secondary_text(msg)
        dlg.run()
        dlg.destroy()


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    app = ConkyEditor(target)
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    # La find_bar se oculta después del show_all
    app.find_bar.hide()
    Gtk.main()
