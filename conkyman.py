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
    out_to_wayland = true,
    out_to_x = true,
    
    own_window = true,
    own_window_class = 'Conky',
    own_window_type = 'normal', 
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
    own_window_type = 'normal', 
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

class ConkymanApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="ConkyMan")
        self.set_default_size(650, 520)
        try:
            self.set_icon_from_file("conkyman.svg")
        except Exception:
            pass
        self.set_position(Gtk.WindowPosition.CENTER)
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.logo_path = os.path.join(self.base_path, "conkyman.svg")
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", "conkyman")
        self.config_file = os.path.join(self.config_dir, "conkyman.conf")
        os.makedirs(self.config_dir, exist_ok=True)
        self.load_colors()
        self.conkyrc_path = self.detect_conky_path()
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)
        headerbar.set_title("ConkyMan")
        headerbar.set_subtitle("Control de Yelena Conky")
        self.set_titlebar(headerbar)
        
        btn_restart = Gtk.Button()
        btn_restart.set_tooltip_text("Reiniciar proceso Conky")
        btn_restart.set_image(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.MENU))
        btn_restart.connect("clicked", self.restart_conky_process)
        headerbar.pack_start(btn_restart)
        
        btn_restore = Gtk.Button()
        btn_restore.set_tooltip_text("Restaurar predeterminados")
        btn_restore.set_image(Gtk.Image.new_from_icon_name("edit-clear-all-symbolic", Gtk.IconSize.MENU))
        btn_restore.connect("clicked", self.restore_defaults)
        headerbar.pack_start(btn_restore)
        
        btn_edit = Gtk.Button()
        btn_edit.set_tooltip_text("Editor de texto manual")
        btn_edit.set_image(Gtk.Image.new_from_icon_name("document-edit-symbolic", Gtk.IconSize.MENU))
        btn_edit.connect("clicked", self.open_text_editor)
        headerbar.pack_start(btn_edit)
        
        btn_about = Gtk.Button()
        btn_about.set_tooltip_text("Acerca de ConkyMan")
        btn_about.set_image(Gtk.Image.new_from_icon_name("help-about-symbolic", Gtk.IconSize.MENU))
        btn_about.connect("clicked", self.show_about)
        headerbar.pack_end(btn_about)
        
        vbox_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox_main)
        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)
        stack_switcher.set_halign(Gtk.Align.CENTER)
        headerbar.set_custom_title(stack_switcher)

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

        frame_fonts = Gtk.Frame()
        inner_fonts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.apply_margins(inner_fonts, 15)
        header_f = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        header_f.pack_start(Gtk.Image.new_from_icon_name("preferences-desktop-font", Gtk.IconSize.DND), False, False, 0)
        label_f = Gtk.Label(); label_f.set_markup("<b><span size='large'>Tipografía [Experimental]</span></b>")
        header_f.pack_start(label_f, False, False, 0)
        inner_fonts.pack_start(header_f, False, False, 0)
        grid_f = Gtk.Grid(column_spacing=20, row_spacing=10)
        grid_f.attach(Gtk.Label(label="Fuente Números:", xalign=0), 0, 0, 1, 1)
        self.font_nums = Gtk.FontButton(); self.font_nums.set_font("Roboto 85")
        grid_f.attach(self.font_nums, 1, 0, 1, 1)
        grid_f.attach(Gtk.Label(label="Fuente Textos:", xalign=0), 0, 1, 1, 1)
        self.font_txt = Gtk.FontButton(); self.font_txt.set_font("Roboto Condensed 14")
        grid_f.attach(self.font_txt, 1, 1, 1, 1)
        inner_fonts.pack_start(grid_f, False, False, 0)
        frame_fonts.add(inner_fonts)
        vbox_style.pack_start(frame_fonts, False, False, 0)

        stack.add_titled(vbox_style, "style", "Apariencia")

        vbox_colors = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.apply_margins(vbox_colors, 20)
        self.colors_frame_c1 = Gtk.Frame()
        self.colors_inner_c1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.apply_margins(self.colors_inner_c1, 15)
        self.colors_frame_c1.add(self.colors_inner_c1)
        vbox_colors.pack_start(self.colors_frame_c1, False, False, 0)
        self.colors_frame_c2 = Gtk.Frame()
        self.colors_inner_c2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.apply_margins(self.colors_inner_c2, 15)
        self.colors_frame_c2.add(self.colors_inner_c2)
        vbox_colors.pack_start(self.colors_frame_c2, False, False, 0)
        self.update_colors_section()
        stack.add_titled(vbox_colors, "colors", "Colores")
        
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
        stack.add_titled(vbox_sys, "system", "Sistema")
        
        vbox_main.pack_start(stack, True, True, 0)
        action_bar = Gtk.ActionBar()
        self.btn_run = Gtk.Button(label="Aplicar Cambios")
        self.btn_run.get_style_context().add_class("suggested-action")
        self.btn_run.set_size_request(180, 40)
        self.btn_run.connect("clicked", self.start_process)
        action_bar.pack_end(self.btn_run)
        vbox_main.pack_end(action_bar, False, False, 0)
        
        self.mode_dark.connect("toggled", self.on_mode_changed)
        self.mode_light.connect("toggled", self.on_mode_changed)
        self.load_config()

    def open_text_editor(self, btn):
        script_path = os.path.join(self.base_path, "text.py")
        if os.path.exists(script_path):
            subprocess.Popen(["python3", script_path, self.conkyrc_path])

    def load_colors(self):
        self.colors_data = {"light": {"Mentolado": "#27AE60", "Verde MATE": "#87A556", "Menta": "#6F4E37", "Gato Verde": "#32CD32", "Azul": "#2980B9", "Rojo": "#C0392B", "Naranja": "#D35400", "Amarillo": "#F1C40F", "Púrpura": "#8E44AD", "Turquesa": "#16A085", "Rosa": "#E91E63", "Índigo": "#3F51B5", "Ámbar": "#FF6F00"}, "dark": {"Mentolado": "#8AA34F", "Verde MATE": "#9DB76F", "Café/Menta": "#98D8C8", "Gato Verde": "#7FFF00", "Azul": "#5DADE2", "Rojo": "#E74C3C", "Naranja": "#E67E22", "Amarillo": "#F4D03F", "Púrpura": "#BB8FCE", "Turquesa": "#48C9B0", "Rosa": "#F48FB1", "Índigo": "#7986CB", "Ámbar": "#FFB74D"}}

    def save_config(self):
        config = configparser.ConfigParser()
        config['Appearance'] = {'mode': 'dark' if self.mode_dark.get_active() else 'light'}
        config['System'] = {'minimal': 'yes' if self.switch_minimal.get_active() else 'no', 'time_format': '12' if self.time_12.get_active() else '24'}
        with open(self.config_file, 'w') as f: config.write(f)

    def load_config(self):
        if not os.path.exists(self.config_file): return
        config = configparser.ConfigParser(); config.read(self.config_file)
        if 'Appearance' in config:
            if config['Appearance'].get('mode') == 'light': self.mode_light.set_active(True)
        if 'System' in config:
            self.switch_minimal.set_active(config['System'].get('minimal') == 'yes')
            if config['System'].get('time_format') == '12': self.time_12.set_active(True)

    def sanitize_attr_name(self, name):
        return name.lower().replace('ú', 'u').replace('í', 'i').replace('á', 'a').replace('/', '_').replace(' ', '_')

    def on_mode_changed(self, radio):
        if radio.get_active(): self.update_colors_section()

    def update_colors_section(self):
        def populate_color_box(inner_box, title, prefix):
            for child in inner_box.get_children(): inner_box.remove(child)
            header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
            header.pack_start(Gtk.Image.new_from_icon_name("preferences-color", Gtk.IconSize.DND), False, False, 0)
            label = Gtk.Label(); label.set_markup(f"<b><span size='large'>{title}</span></b>")
            header.pack_start(label, False, False, 0); inner_box.pack_start(header, False, False, 0)
            mode = "dark" if self.mode_dark.get_active() else "light"
            colors = self.colors_data[mode]
            flow = Gtk.FlowBox(); flow.set_min_children_per_line(4); flow.set_selection_mode(Gtk.SelectionMode.NONE)
            first_radio = None
            for color_name, color_value in colors.items():
                radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, color_name)
                if first_radio is None: first_radio = radio; radio.set_active(True)
                setattr(self, f"{prefix}_{self.sanitize_attr_name(color_name)}", radio); flow.add(radio)
            inner_box.pack_start(flow, False, False, 5)
            inner_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)
            hbox_custom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            radio_custom = Gtk.RadioButton.new_with_label_from_widget(first_radio, "Personalizado:")
            setattr(self, f"{prefix}_radio_custom", radio_custom)
            picker = Gtk.ColorButton()
            setattr(self, f"{prefix}_color_picker", picker)
            hbox_custom.pack_start(radio_custom, False, False, 0); hbox_custom.pack_start(picker, False, False, 0)
            inner_box.pack_start(hbox_custom, False, False, 5); inner_box.show_all()

        populate_color_box(self.colors_inner_c1, "Color Primario", "c1")
        populate_color_box(self.colors_inner_c2, "Color de Acento", "c2")

    def detect_conky_path(self):
        home = os.path.expanduser("~")
        for p in [os.path.join(home, ".config/conky/conky.lua"), os.path.join(home, ".conkyrc")]:
            if os.path.exists(p): return p
        return os.path.join(home, ".config/conky/conky.lua")

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

    def show_about(self, btn):
        about = Gtk.AboutDialog(transient_for=self)
        about.set_program_name("ConkyMan")
        about.set_version("1.0")
        about.set_copyright("🄯 2026 CuerdOS")
        about.set_license_type(Gtk.License.LGPL_3_0)
        about.set_website("https://cuerdos.github.io")
        about.set_website_label("Visitar Pagina Web")
        about.set_comments("Control de Yelena Conky.\nPersonaliza tu configuracion de Conky.")
        if os.path.exists(self.logo_path):
            about.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(self.logo_path, 96, 96, True))
        about.run()
        about.destroy()

    def restart_conky_process(self, btn):
        os.system("killall conky")
        subprocess.Popen(["conky", "-c", self.conkyrc_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def restore_defaults(self, btn):
        dialog = Gtk.MessageDialog(transient_for=self, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text="ConkyMan")
        dialog.format_secondary_text("¿Deseas restaurar el archivo de configuración predeterminado (conky.lua)?")
        if dialog.run() == Gtk.ResponseType.YES:
            with open(self.conkyrc_path, 'w', encoding='utf-8') as f: f.write(DEFAULT_CONKY_LUA)
            
            self.pos_tr.set_active(True)
            self.mode_dark.set_active(True)
            self.font_nums.set_font("Roboto 85")
            self.font_txt.set_font("Roboto Condensed 14")
            self.time_24.set_active(True)
            self.type_dock.set_active(True)
            self.switch_minimal.set_active(False)
            self.update_colors_section() 
            
            self.restart_conky_process(None)
        dialog.destroy()

    def apply_logic(self):
        try:
            content = MINIMAL_CONKY_LUA if self.switch_minimal.get_active() else DEFAULT_CONKY_LUA
            
            f_nums_name = self.font_nums.get_font().rsplit(' ', 1)[0]
            f_txt_name = self.font_txt.get_font().rsplit(' ', 1)[0]
            
            content = re.sub(r"\${font [^:]+:weight=[^:]+:size=8([05])}", fr"${{font {f_nums_name}:weight=Normal:size=8\1}}", content)
            content = re.sub(r"\${font [^:]+:size=1([24])}", fr"${{font {f_txt_name}:size=1\1}}", content)

            if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
                content = content.replace("own_window_type = 'dock'", "own_window_type = 'desktop'")
                content = content.replace("own_window_hints = 'undecorated,below,sticky,skip_taskbar,skip_pager'", "out_to_wayland = true")
            
            pos_map = {'pos_tr': "'top_right'", 'pos_tl': "'top_left'", 'pos_br': "'bottom_right'", 'pos_bl': "'bottom_left'", 'pos_cc': "'middle_middle'"}
            for attr, val in pos_map.items():
                if getattr(self, attr).get_active(): content = re.sub(r"alignment\s*=\s*'.*?'", f"alignment = {val}", content)

            mode = "dark" if self.mode_dark.get_active() else "light"
            for prefix, lua_key in [("c1", "color1"), ("c2", "color2")]:
                selected_hex = ""
                if getattr(self, f"{prefix}_radio_custom").get_active():
                    rgba = getattr(self, f"{prefix}_color_picker").get_rgba()
                    selected_hex = "{:02x}{:02x}{:02x}".format(int(rgba.red*255), int(rgba.green*255), int(rgba.blue*255)).upper()
                else:
                    for color_name in self.colors_data[mode]:
                        if getattr(self, f"{prefix}_{self.sanitize_attr_name(color_name)}").get_active():
                            selected_hex = self.colors_data[mode][color_name].replace('#', '')
                            break
                content = re.sub(f"{lua_key}\\s*=\\s*'.*?'", f"{lua_key} = '{selected_hex}'", content)
            
            if self.time_12.get_active():
                content = content.replace("%H", "%I %p")
            else:
                content = content.replace("%I %p", "%H").replace("%I", "%H")

            with open(self.conkyrc_path, 'w', encoding='utf-8') as f: f.write(content)
            self.save_config()
            os.system("killall -SIGUSR1 conky 2>/dev/null")
            return True, "Cambios aplicados con éxito."
        except Exception as e: return False, str(e)

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

if __name__ == "__main__":
    app = ConkymanApp(); app.connect("destroy", Gtk.main_quit); app.show_all(); Gtk.main()