#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# about_theme.py — Paleta de colores adaptable (dark/light) para diálogos
# "Acerca de" basados en QPalette de Qt.
#
# Genera todos los colores de un AboutDialog a partir de la paleta activa
# de la aplicación (QApplication.palette()), en vez de valores hex fijos.
# Así el diálogo sigue automáticamente el modo claro/oscuro del sistema,
# y también reacciona si el usuario cambia el tema en caliente (basta con
# reconstruir el diálogo — ver nota al final del archivo).
#
# Uso:
#   from about_theme import build_about_colors
#   _C = build_about_colors()
#   header.setStyleSheet(f"background:{_C['header_bg']};")
#   ...
#
# Sin dependencias del proyecto (no importa T(), find_asset(), etc.) para
# poder copiarlo tal cual a cualquier app PySide6 de CuerdOS.

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication


def _readable_variant(color: QColor, on_light: bool) -> QColor:
    """
    Devuelve una variante de `color` con la luminosidad forzada a un rango
    legible como texto: oscura sobre fondos claros, clara sobre fondos
    oscuros. Conserva el matiz/saturación original.

    Necesario porque el color "highlight" de muchos temas es un tono pastel
    pensado para fondos de selección, no para texto — usado tal cual sobre
    un fondo del mismo brillo queda casi invisible (bajo contraste).
    """
    h, s, _l, a = color.getHsl()
    if h == -1:          # color acromático (gris puro): sin matiz que conservar
        h, s = 0, 0
    target_l = 95 if on_light else 190   # 0–255; oscuro en claro, claro en oscuro
    fixed = QColor()
    fixed.setHsl(h, s, target_l, a)
    return fixed


def build_about_colors(app: QApplication | None = None) -> dict:
    """
    Construye el diccionario de colores para un AboutDialog a partir de la
    paleta activa de Qt. Llamar dentro de __init__ del diálogo (no cachear
    a nivel de módulo) para que se recalcule cada vez que se abre y refleje
    un eventual cambio de tema.
    """
    app = app or QApplication.instance()
    pal = app.palette() if app else QApplication.palette()

    hl = pal.color(QPalette.ColorRole.Highlight)
    window = pal.color(QPalette.ColorRole.Window)
    is_dark = window.lightness() < 128

    # Cabecera: variante oscurecida del acento, para dar contraste al logo
    # y al texto en blanco/negro que va encima.
    header_bg = hl.darker(170) if is_dark else hl.darker(120)
    header_fg = QColor("#ffffff") if header_bg.lightness() < 140 else QColor("#101010")
    sub_rgb = "255,255,255" if header_fg.name() == "#ffffff" else "16,16,16"

    # Variante del acento con contraste garantizado, para usar como texto
    # (etiquetas, enlaces) sobre el fondo del cuerpo/pie del diálogo.
    accent_text = _readable_variant(hl, on_light=not is_dark)

    text = pal.color(QPalette.ColorRole.WindowText)
    text_dim = pal.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText)

    return {
        "header_bg":     header_bg.name(),
        "header_fg":     header_fg.name(),
        "header_sub":    f"rgba({sub_rgb},0.75)",
        "accent":        accent_text.name(),
        "text":          text.name(),
        "text_dim":      text_dim.name(),
        "row_alt":       "rgba(128,128,128,0.10)",
        "footer_bg":     "rgba(128,128,128,0.06)",
        "sep":           "palette(mid)",
        "btn_accent_bg":  f"rgba({accent_text.red()},{accent_text.green()},{accent_text.blue()},0.14)",
        "btn_accent_fg":  accent_text.name(),
        "btn_accent_br":  f"rgba({accent_text.red()},{accent_text.green()},{accent_text.blue()},0.55)",
        "btn_accent_hov": f"rgba({accent_text.red()},{accent_text.green()},{accent_text.blue()},0.24)",
        "btn_neutral_bg":  "rgba(128,128,128,0.12)",
        "btn_neutral_fg":  text.name(),
        "btn_neutral_br":  "palette(mid)",
        "btn_neutral_hov": "rgba(128,128,128,0.22)",
    }


# ─────────────────────────────────────────────────────────────────────────
# Guía rápida de integración en un AboutDialog existente
# ─────────────────────────────────────────────────────────────────────────
#
# 1. Copiar este archivo (about_theme.py) junto al about.py de la app.
#
# 2. Borrar el diccionario de colores fijos (algo como):
#        _C = {"header_bg": "#192511", "accent": "#8aab4a", ...}
#
# 3. Importar y llamar dentro de AboutDialog.__init__:
#        from about_theme import build_about_colors
#        ...
#        class AboutDialog(QDialog):
#            def __init__(self, parent=None):
#                super().__init__(parent)
#                _C = build_about_colors()
#                ...  # el resto del código que usa _C['xxx'] no cambia
#
#    Claves disponibles: header_bg, header_fg, header_sub, accent, text,
#    text_dim, row_alt, footer_bg, sep, btn_accent_bg/fg/br/hov,
#    btn_neutral_bg/fg/br/hov (antes btn_web_* / btn_cls_* — renombrar si
#    el about.py original usaba esos nombres literales).
#
# 4. Si el about.py original tenía _C a nivel de módulo (fuera de la
#    clase), moverlo dentro de __init__ como en el paso 3: así se recalcula
#    cada vez que se abre el diálogo y no queda "congelado" con el tema que
#    estaba activo cuando se importó el módulo.
