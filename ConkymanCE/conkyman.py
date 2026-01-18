import gi
import os
import re
import subprocess
import threading
import json
import configparser
import sys

if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
    os.environ['GDK_BACKEND'] = 'wayland,x11'

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf

DEFAULT_CONKY_LUA = """conky.config = {
    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'dock',
    own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'undecorated,below,sticky,skip_taskbar,skip_pager',
    double_buffer = true,
    alignment = 'top_right',
    gap_x = 20,
    gap_y = 40,
    minimum_width = 200,
    minimum_height = 300,
    use_xft = true,
    default_color = 'F5F5F5',
    color1 = 'E0E0E0',
    color2 = '8AA34F',
    update_interval = 1.0,
    draw_shades = false,
    draw_borders = false,
    cpu_avg_samples = 2,
    net_avg_samples = 2,
    text_buffer_size = 8192,
    out_to_console = false,
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
    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'dock',
    own_window_argb_visual = true,
    own_window_argb_value = 0,
    own_window_hints = 'undecorated,below,sticky,skip_taskbar,skip_pager',
    double_buffer = true,
    alignment = 'top_right',
    gap_x = 20,
    gap_y = 40,
    use_xft = true,
    default_color = 'F5F5F5',
    color1 = 'E0E0E0',
    color2 = '8AA34F',
    update_interval = 1.0,
    override_utf8_locale = true,
}
conky.text = [[
${voffset -20}${font Roboto:weight=Normal:size=85}${color1}${time %H}${font}
${voffset -40}${offset 75}${font Roboto Condensed:weight=Medium:size=80}${color2}${time %M}${font}
${font Roboto Condensed:size=14}${color}${time %a, %d %b %Y}${font}
]]"""

class ConkymanApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="ConkyMan")
        self.set_default_size(650, 520)
        
        self._setup_window_icons("conkyman")
        self.set_position(Gtk.WindowPosition.CENTER)
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.logo_path = os.path.join(self.base_path, "conkyman.svg")
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", "conkyman")
        self.config_file = os.path.join(self.config_dir, "conkyman.conf")
        os.makedirs(self.config_dir, exist_ok=True)
        self.load_colors()
        self.conkyrc_path = self.detect_conky_path()
        
        vbox_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox_main)

        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.notebook.set_show_border(False)

        toolbar = self.create_toolbar()
        vbox_main.pack_start(toolbar, False, False, 0)

        vbox_style = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.apply_margins(vbox_style, 20)
        self.add_pro_section(vbox_style, "Ubicación", "preferences-desktop-display-symbolic", [
            ("Arriba-Derecha", "pos_tr", True), ("Arriba-Izquierda", "pos_tl", False),
            ("Abajo-Derecha", "pos_br", False), ("Abajo-Izquierda", "pos_bl", False),
            ("Centro", "pos_cc", False)
        ])
        self.add_pro_section(vbox_style, "Modo de Color", "weather-clear-night-symbolic", [
            ("Modo Dark", "mode_dark", True), ("Modo Light", "mode_light", False)
        ])
        
        self.colors_frame = Gtk.Frame()
        self.colors_inner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.apply_margins(self.colors_inner_box, 15)
        vbox_style.pack_start(self.colors_frame, False, False, 0)
        self.update_colors_section()
        self.notebook.append_page(vbox_style, Gtk.Label(label="Apariencia"))

        vbox_sys = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.apply_margins(vbox_sys, 20)
        self.add_pro_section(vbox_sys, "Formato de Hora", "preferences-system-time-symbolic", [
            ("24 Horas", "time_24", True), ("12 Horas (AM/PM)", "time_12", False)
        ])
        self.add_pro_section(vbox_sys, "Tipo de Conky", "window-new-symbolic", [
            ("Dock", "type_dock", True), ("Normal", "type_norm", False),
            ("Desktop", "type_desk", False), ("Panel", "type_panel", False)
        ])
        
        frame_mini = Gtk.Frame()
        inner_box_mini = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.apply_margins(inner_box_mini, 15)
        header_mini = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        header_mini.pack_start(Gtk.Image.new_from_icon_name("view-fullscreen-symbolic", Gtk.IconSize.DND), False, False, 0)
        label_mini = Gtk.Label(); label_mini.set_markup("<b><span size='large'>Modo de Visualización</span></b>")
        header_mini.pack_start(label_mini, False, False, 0)
        inner_box_mini.pack_start(header_mini, False, False, 0)
        hbox_mini = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox_mini.pack_start(Gtk.Label(label="Activar Conky Minimal (solo reloj y fecha)"), False, False, 0)
        self.switch_minimal = Gtk.Switch(); self.switch_minimal.set_active(False)
        hbox_mini.pack_end(self.switch_minimal, False, False, 0)
        inner_box_mini.pack_start(hbox_mini, False, False, 0)
        frame_mini.add(inner_box_mini)
        vbox_sys.pack_start(frame_mini, False, False, 0)
        self.notebook.append_page(vbox_sys, Gtk.Label(label="Sistema"))

        vbox_extras = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.apply_margins(vbox_extras, 15)
        
        def create_addon_frame(title, icon_name, widget):
            frame = Gtk.Frame()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            self.apply_margins(box, 10)
            img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND)
            lbl = Gtk.Label(); lbl.set_markup(f"<b>{title}</b>")
            box.pack_start(img, False, False, 0)
            box.pack_start(lbl, False, False, 0)
            box.pack_end(widget, False, False, 0)
            frame.add(box)
            return frame

        self.chk_greeting = Gtk.Switch(); self.chk_greeting.set_valign(Gtk.Align.CENTER)
        self.chk_osinfo = Gtk.Switch(); self.chk_osinfo.set_valign(Gtk.Align.CENTER)
        self.chk_battery = Gtk.Switch(); self.chk_battery.set_valign(Gtk.Align.CENTER)
        self.chk_netinfo = Gtk.Switch(); self.chk_netinfo.set_valign(Gtk.Align.CENTER)
        self.chk_swap = Gtk.Switch(); self.chk_swap.set_valign(Gtk.Align.CENTER)

        vbox_extras.pack_start(create_addon_frame("Saludo de Bienvenida", "face-smile-symbolic", self.chk_greeting), False, False, 0)
        vbox_extras.pack_start(create_addon_frame("Información del Kernel", "computer-symbolic", self.chk_osinfo), False, False, 0)
        vbox_extras.pack_start(create_addon_frame("Monitor de Batería", "battery-good-symbolic", self.chk_battery), False, False, 0)
        vbox_extras.pack_start(create_addon_frame("Estadísticas de Red", "network-workgroup-symbolic", self.chk_netinfo), False, False, 0)
        vbox_extras.pack_start(create_addon_frame("Uso de Memoria Swap", "media-flash-symbolic", self.chk_swap), False, False, 0)

        scrolled_extras = Gtk.ScrolledWindow()
        scrolled_extras.add(vbox_extras)
        self.notebook.append_page(scrolled_extras, Gtk.Label(label="Extras"))
        
        vbox_main.pack_start(self.notebook, True, True, 0)

        action_bar = Gtk.ActionBar()
        self.btn_run = Gtk.Button(label="Aplicar Cambios")
        self.btn_run.get_style_context().add_class("suggested-action")
        self.btn_run.set_size_request(180, 40)
        self.btn_run.set_tooltip_text("Guardar y aplicar la nueva configuración")
        self.btn_run.connect("clicked", self.start_process)
        action_bar.pack_end(self.btn_run)
        vbox_main.pack_end(action_bar, False, False, 0)
        
        self.mode_dark.connect("toggled", self.on_mode_changed)
        self.mode_light.connect("toggled", self.on_mode_changed)
        self.load_config()

    def _setup_window_icons(self, app_name):
        icon_paths = [f"{app_name}.svg", os.path.join(os.path.dirname(__file__), f"{app_name}.svg")]
        self.set_wmclass(app_name, app_name.capitalize())
        self.set_role(f"{app_name}-main")
        for icon_path in icon_paths:
            try:
                abs_path = os.path.abspath(icon_path)
                if os.path.exists(abs_path):
                    self.set_icon_from_file(abs_path)
                    break
            except: pass

    def create_toolbar(self):
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.BOTH_HORIZ)
        
        btn_edit = Gtk.ToolButton(); btn_edit.set_icon_name("document-edit-symbolic")
        btn_edit.set_label("Editor Manual"); btn_edit.set_tooltip_text("Abrir el editor de texto avanzado")
        btn_edit.connect("clicked", self.open_text_editor)
        toolbar.insert(btn_edit, -1)

        btn_restore = Gtk.ToolButton(); btn_restore.set_icon_name("edit-clear-all-symbolic")
        btn_restore.set_label("Restaurar"); btn_restore.set_tooltip_text("Volver a la configuración de fábrica")
        btn_restore.connect("clicked", self.restore_defaults)
        toolbar.insert(btn_restore, -1)

        sep_expand1 = Gtk.SeparatorToolItem(); sep_expand1.set_expand(True); sep_expand1.set_draw(False)
        toolbar.insert(sep_expand1, -1)

        tab_selector = Gtk.ComboBoxText()
        tab_selector.append_text("Apariencia")
        tab_selector.append_text("Sistema")
        tab_selector.append_text("Extras")
        tab_selector.set_active(0)
        tab_selector.set_tooltip_text("Cambiar categoría de configuración")
        tab_selector.connect("changed", lambda cb: self.notebook.set_current_page(cb.get_active()))
        
        tool_item_combo = Gtk.ToolItem(); tool_item_combo.add(tab_selector)
        toolbar.insert(tool_item_combo, -1)

        sep_expand2 = Gtk.SeparatorToolItem(); sep_expand2.set_expand(True); sep_expand2.set_draw(False)
        toolbar.insert(sep_expand2, -1)
        
        btn_restart = Gtk.ToolButton(); btn_restart.set_icon_name("view-refresh-symbolic")
        btn_restart.set_label("Refrescar"); btn_restart.set_tooltip_text("Reiniciar el proceso de Conky")
        btn_restart.connect("clicked", self.restart_conky_process)
        toolbar.insert(btn_restart, -1)

        btn_about = Gtk.ToolButton(); btn_about.set_icon_name("help-about-symbolic")
        btn_about.set_label("Acerca de"); btn_about.set_tooltip_text("Información sobre ConkyMan")
        btn_about.connect("clicked", self.show_about)
        toolbar.insert(btn_about, -1)
        
        return toolbar

    def show_about(self, btn):
        about = Gtk.AboutDialog(transient_for=self)
        about.set_program_name("ConkyMan")
        about.set_version("1.0.1")
        about.set_copyright("🄯 2025 CuerdOS")
        about.set_license_type(Gtk.License.LGPL_3_0)
        about.set_website("https://github.com/cuerdos")
        about.set_website_label("Visitar Pagina Web")
        about.set_comments("Control de Yelena Conky.\nPersonaliza tu configuracion de Conky.")
        if os.path.exists(self.logo_path):
            about.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(self.logo_path, 96, 96, True))
        about.run()
        about.destroy()

    def open_text_editor(self, btn):
        script_path = os.path.join(self.base_path, "text.py")
        if os.path.exists(script_path):
            subprocess.Popen(["python3", script_path, self.conkyrc_path])
        else:
            subprocess.Popen(["xdg-open", self.conkyrc_path])

    def load_colors(self):
        self.colors_data = {"light": {"Mentolado": "#27AE60", "Verde MATE": "#87A556", "Menta": "#6F4E37", "Gato Verde": "#32CD32", "Azul": "#2980B9", "Rojo": "#C0392B", "Naranja": "#D35400", "Amarillo": "#F1C40F", "Púrpura": "#8E44AD", "Turquesa": "#16A085", "Rosa": "#E91E63", "Índigo": "#3F51B5", "Ámbar": "#FF6F00"}, "dark": {"Mentolado": "#8AA34F", "Verde MATE": "#9DB76F", "Café/Menta": "#98D8C8", "Gato Verde": "#7FFF00", "Azul": "#5DADE2", "Rojo": "#E74C3C", "Naranja": "#E67E22", "Amarillo": "#F4D03F", "Púrpura": "#BB8FCE", "Turquesa": "#48C9B0", "Rosa": "#F48FB1", "Índigo": "#7986CB", "Ámbar": "#FFB74D"}}

    def update_colors_section(self):
        for child in self.colors_inner_box.get_children(): self.colors_inner_box.remove(child)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        header.pack_start(Gtk.Image.new_from_icon_name("preferences-color", Gtk.IconSize.DND), False, False, 0)
        label = Gtk.Label(); label.set_markup("<b><span size='large'>Colores de Acento</span></b>")
        header.pack_start(label, False, False, 0); self.colors_inner_box.pack_start(header, False, False, 0)
        mode = "dark" if self.mode_dark.get_active() else "light"
        colors = self.colors_data[mode]; flow = Gtk.FlowBox(); flow.set_min_children_per_line(3); flow.set_selection_mode(Gtk.SelectionMode.NONE)
        first_radio = None
        for color_name, color_value in colors.items():
            radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, color_name)
            if first_radio is None: first_radio = radio; radio.set_active(True)
            setattr(self, f"col_{self.sanitize_attr_name(color_name)}", radio); flow.add(radio)
        self.colors_inner_box.pack_start(flow, False, False, 5)
        self.colors_inner_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)
        hbox_custom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.radio_custom = Gtk.RadioButton.new_with_label_from_widget(first_radio, "Personalizado:")
        self.btn_color_picker = Gtk.ColorButton(); hbox_custom.pack_start(self.radio_custom, False, False, 0); hbox_custom.pack_start(self.btn_color_picker, False, False, 0)
        self.colors_inner_box.pack_start(hbox_custom, False, False, 5); self.colors_frame.add(self.colors_inner_box); self.colors_frame.show_all()

    def sanitize_attr_name(self, name):
        return name.lower().replace('ú', 'u').replace('í', 'i').replace('á', 'a').replace('/', '_').replace(' ', '_')

    def detect_conky_path(self):
        home = os.path.expanduser("~")
        p = os.path.join(home, ".config/conky/conky.lua")
        return p if os.path.exists(p) else os.path.join(home, ".conkyrc")

    def apply_margins(self, widget, val):
        widget.set_margin_top(val); widget.set_margin_bottom(val); widget.set_margin_start(val); widget.set_margin_end(val)

    def add_pro_section(self, container, title, icon_name, items):
        frame = Gtk.Frame(); inner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10); self.apply_margins(inner_box, 15)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        header.pack_start(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND), False, False, 0)
        label = Gtk.Label(); label.set_markup(f"<b><span size='large'>{title}</span></b>")
        header.pack_start(label, False, False, 0); inner_box.pack_start(header, False, False, 0)
        flow = Gtk.FlowBox(); flow.set_min_children_per_line(3); flow.set_selection_mode(Gtk.SelectionMode.NONE)
        first_radio = None
        for label_text, attr, active in items:
            radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, label_text)
            if first_radio is None: first_radio = radio
            radio.set_active(active); setattr(self, attr, radio); flow.add(radio)
        inner_box.pack_start(flow, False, False, 5); frame.add(inner_box); container.pack_start(frame, False, False, 0)

    def on_mode_changed(self, radio):
        if radio.get_active(): self.update_colors_section()

    def restart_conky_process(self, btn):
        os.system("killall conky 2>/dev/null")
        subprocess.Popen(["conky", "-c", self.conkyrc_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def restore_defaults(self, btn):
        dialog = Gtk.MessageDialog(transient_for=self, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text="ConkyMan")
        dialog.format_secondary_text("¿Deseas restaurar el archivo de configuración predeterminado?")
        if dialog.run() == Gtk.ResponseType.YES:
            with open(self.conkyrc_path, 'w', encoding='utf-8') as f: f.write(DEFAULT_CONKY_LUA)
            self.restart_conky_process(None)
        dialog.destroy()

    def start_process(self, btn):
        self.btn_run.set_sensitive(False)
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        success, msg = self.apply_logic()
        GLib.idle_add(self.finish, success, msg)

    def finish(self, success, msg):
        self.btn_run.set_sensitive(True)
        dialog = Gtk.MessageDialog(transient_for=self, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, text="ConkyMan")
        dialog.format_secondary_text(msg); dialog.run(); dialog.destroy()

    def save_config(self):
        config = configparser.ConfigParser()
        config['Appearance'] = {'mode': 'dark' if self.mode_dark.get_active() else 'light'}
        config['System'] = {'minimal': 'yes' if self.switch_minimal.get_active() else 'no', 'time_format': '12' if self.time_12.get_active() else '24'}
        config['Extras'] = {'greeting': 'yes' if self.chk_greeting.get_active() else 'no', 'osinfo': 'yes' if self.chk_osinfo.get_active() else 'no', 'battery': 'yes' if self.chk_battery.get_active() else 'no', 'netinfo': 'yes' if self.chk_netinfo.get_active() else 'no', 'swap': 'yes' if self.chk_swap.get_active() else 'no'}
        with open(self.config_file, 'w') as f: config.write(f)

    def load_config(self):
        if not os.path.exists(self.config_file): return
        config = configparser.ConfigParser(); config.read(self.config_file)
        if 'Appearance' in config:
            if config['Appearance'].get('mode') == 'light': self.mode_light.set_active(True)
        if 'System' in config:
            self.switch_minimal.set_active(config['System'].get('minimal') == 'yes')
            if config['System'].get('time_format') == '12': self.time_12.set_active(True)
        if 'Extras' in config:
            self.chk_greeting.set_active(config['Extras'].get('greeting') == 'yes')
            self.chk_osinfo.set_active(config['Extras'].get('osinfo') == 'yes')
            self.chk_battery.set_active(config['Extras'].get('battery') == 'yes')
            self.chk_netinfo.set_active(config['Extras'].get('netinfo') == 'yes')
            self.chk_swap.set_active(config['Extras'].get('swap') == 'yes')

    def apply_logic(self):
        try:
            content = MINIMAL_CONKY_LUA if self.switch_minimal.get_active() else DEFAULT_CONKY_LUA
            
            addons_str = ""
            if self.chk_greeting.get_active():
                addons_str += "\n${font Roboto Condensed:size=11}${color2}${execi 5 case $(date +%H) in 0[6-9]|1[0-1]) echo 'Buenos días' ;; 1[2-7]) echo 'Buenas tardes' ;; *) echo 'Buenas noches' ;; esac}${color}, $USER${font}"
            if self.chk_osinfo.get_active():
                addons_str += "\n${font Roboto Condensed:size=10}${color}Kernel: ${color2}$kernel${color} | Up: ${color2}$uptime_short${font}"
            if self.chk_battery.get_active():
                addons_str += "\n${font Roboto Condensed:size=10}${color}Batería: ${color2}${battery_percent}%${color} (${battery_status})${font}"
            if self.chk_netinfo.get_active():
                addons_str += "\n${font Roboto Condensed:size=10}${color}IP: ${color2}${addr}${color} | Dn: ${color2}${downspeed}${font}"
            if self.chk_swap.get_active():
                addons_str += "\n${font Roboto Condensed:size=10}${color}SWAP: ${color2}$swapperc%${color} ($swap/$swapmax)${font}"
            
            if addons_str: content = content.replace("]]", addons_str + "\n]]")
            
            if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
                content = content.replace("own_window_type = 'dock'", "own_window_type = 'desktop'")
                content = content.replace("own_window_hints = 'undecorated,below,sticky,skip_taskbar,skip_pager'", "out_to_wayland = true")
            
            pos_map = {'pos_tr': "'top_right'", 'pos_tl': "'top_left'", 'pos_br': "'bottom_right'", 'pos_bl': "'bottom_left'", 'pos_cc': "'middle_middle'"}
            for attr, val in pos_map.items():
                if getattr(self, attr).get_active(): content = re.sub(r"alignment\s*=\s*'.*?'", f"alignment = {val}", content)
            
            if self.mode_dark.get_active(): content = content.replace("'2C3E50'", "'F5F5F5'").replace("'34495E'", "'E0E0E0'")
            else: content = content.replace("'F5F5F5'", "'2C3E50'").replace("'E0E0E0'", "'34495E'")
            
            if self.radio_custom.get_active():
                rgba = self.btn_color_picker.get_rgba()
                c_hex = "{:02x}{:02x}{:02x}".format(int(rgba.red*255), int(rgba.green*255), int(rgba.blue*255)).upper()
                content = re.sub(r"color2\s*=\s*'.*?'", f"color2 = '{c_hex}'", content)
            else:
                mode = "dark" if self.mode_dark.get_active() else "light"
                for color_name in self.colors_data[mode]:
                    if getattr(self, f"col_{self.sanitize_attr_name(color_name)}").get_active():
                        val = self.colors_data[mode][color_name].replace('#', '')
                        content = re.sub(r"color2\s*=\s*'.*?'", f"color2 = '{val}'", content); break
            
            if self.time_12.get_active(): content = content.replace("%H", "%I %p")
            
            with open(self.conkyrc_path, 'w', encoding='utf-8') as f: f.write(content)
            self.save_config()
            self.restart_conky_process(None)
            return True, "Cambios aplicados con éxito."
        except Exception as e: return False, str(e)

if __name__ == "__main__":
    app = ConkymanApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()