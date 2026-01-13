import gi
import sys
import os

gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Pango, Gdk

class ConkyEditor(Gtk.Window):
    def __init__(self, file_path=None):
        super().__init__(title="Editor de Configuración - ConkyMan")
        self.set_default_size(600, 700)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.file_path = file_path if file_path and os.path.exists(file_path) else self.detect_conky_path()

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("Editor Manual")
        header.set_subtitle(os.path.basename(self.file_path) if self.file_path else "Archivo no encontrado")
        self.set_titlebar(header)

        btn_save = Gtk.Button()
        btn_save.set_tooltip_text("Guardar cambios")
        btn_save.set_image(Gtk.Image.new_from_icon_name("document-save-symbolic", Gtk.IconSize.MENU))
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", self.on_save)
        header.pack_start(btn_save)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        self.text_view = Gtk.TextView()
        self.text_view.set_left_margin(10)
        self.text_view.set_right_margin(10)
        self.text_view.set_top_margin(10)
        self.text_view.set_bottom_margin(10)
        
        font_desc = Pango.FontDescription("Monospace 11")
        self.text_view.modify_font(font_desc)
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(self.text_view)
        vbox.pack_start(scrolled_window, True, True, 0)

        self.load_file_content()

    def detect_conky_path(self):
        """Busca el archivo de configuración si no se pasa por argumento"""
        home = os.path.expanduser("~")
        possible_paths = [
            os.path.join(home, ".config/conky/conky.lua"),
            os.path.join(home, ".config/conky/conky.conf"),
            os.path.join(home, ".conkyrc")
        ]
        for p in possible_paths:
            if os.path.exists(p): return p
        return possible_paths[0]

    def load_file_content(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    buffer = self.text_view.get_buffer()
                    buffer.set_text(content)
            except Exception as e:
                self.show_message(f"Error al leer: {e}", Gtk.MessageType.ERROR)

    def on_save(self, btn):
        buffer = self.text_view.get_buffer()
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, True)

        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            self.show_message("Archivo guardado correctamente.", Gtk.MessageType.INFO)
            os.system("killall -SIGUSR1 conky 2>/dev/null")
        except Exception as e:
            self.show_message(f"Error al guardar: {e}", Gtk.MessageType.ERROR)

    def show_message(self, text, msg_type):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text="Editor ConkyMan"
        )
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else None
    app = ConkyEditor(target_file)
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()