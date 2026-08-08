"""Identidad compartida entre ventanas de ConkyMan (app id e icono).

La ventana principal (PySide6) y el editor Lua (GTK) son procesos con
toolkits distintos. En Wayland, el compositor decide que icono mostrar en
la barra de tareas resolviendo el app id contra el tema de iconos del
usuario, asi que ambas ventanas deben anunciar el mismo app id y ese
nombre debe existir como icono instalado.
"""

import os
import shutil
import subprocess

APP_ID = "conkyman"
APP_NAME = "ConkyMan"


def install_icon_theme(svg_path):
    """Copia el icono de la app al tema de iconos del usuario bajo APP_ID,
    para que cualquier ventana con ese app id resuelva el mismo icono."""
    if not svg_path or not os.path.exists(svg_path):
        return
    dest_dir = os.path.join(
        os.path.expanduser("~"), ".local", "share", "icons", "hicolor", "scalable", "apps")
    dest = os.path.join(dest_dir, f"{APP_ID}.svg")
    try:
        os.makedirs(dest_dir, exist_ok=True)
        if not os.path.exists(dest) or os.path.getmtime(svg_path) > os.path.getmtime(dest):
            shutil.copy2(svg_path, dest)
        icons_root = os.path.join(os.path.expanduser("~"), ".local", "share", "icons", "hicolor")
        subprocess.run(["gtk-update-icon-cache", "-f", icons_root],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        pass
