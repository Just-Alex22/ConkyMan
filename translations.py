"""ConkyMan - Carga de traducciones.

Los textos ya no viven en este archivo: cada idioma es un JSON
independiente dentro de i18n/ (por ejemplo i18n/es.json, i18n/en.json...).
Este modulo solo se encarga de descubrirlos, cargarlos y exponer la
misma API que antes (Translator, set_language) para no tener que tocar
conkyman.py ni text.py.
"""

import json
import os

_I18N_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "i18n")

_cache = {}


def _available_langs():
    if not os.path.isdir(_I18N_DIR):
        return []
    return sorted(
        fn[:-5] for fn in os.listdir(_I18N_DIR)
        if fn.endswith(".json")
    )


def _load_lang(lang):
    """Carga (y cachea) el JSON de un idioma. Devuelve {} si no existe."""
    if lang in _cache:
        return _cache[lang]
    path = os.path.join(_I18N_DIR, f"{lang}.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = {}
    _cache[lang] = data
    return data


SUPPORTED_LANGS = set(_available_langs()) or {"es", "en"}

_current_lang = "es"


def set_language(lang):
    global _current_lang
    if lang in SUPPORTED_LANGS:
        _current_lang = lang


class Translator:
    def __init__(self, lang="es"):
        self.lang = lang if lang in SUPPORTED_LANGS else "en"

    def get(self, key, default=None):
        own = _load_lang(self.lang)
        en = _load_lang("en")
        es = _load_lang("es")
        return (own.get(key) or en.get(key) or es.get(key)
                or default or key)

    def __call__(self, key, default=None):
        return self.get(key, default)

    def fmt(self, key, default=None, **kwargs):
        s = self.get(key, default)
        try:
            return s.format(**kwargs)
        except Exception:
            return s
