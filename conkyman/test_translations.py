#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar el sistema de traducción
"""

import os
import sys

# Agregar el directorio actual al path para importar translations
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from translations import get_system_language, t, set_language, get_current_language

def test_language_detection():
    """Prueba la detección automática de idioma"""
    print("=" * 60)
    print("PRUEBA DE DETECCIÓN DE IDIOMA")
    print("=" * 60)
    
    # Mostrar variables de entorno
    print("\nVariables de entorno:")
    print(f"  LANG: {os.environ.get('LANG', 'No definida')}")
    print(f"  LANGUAGE: {os.environ.get('LANGUAGE', 'No definida')}")
    print(f"  LC_ALL: {os.environ.get('LC_ALL', 'No definida')}")
    
    # Detectar idioma
    detected_lang = get_system_language()
    print(f"\nIdioma detectado: {detected_lang}")
    print(f"Idioma actual del sistema: {get_current_language()}")
    
    print("\n" + "=" * 60)
    print("PRUEBA DE TRADUCCIONES")
    print("=" * 60)
    
    # Probar algunas traducciones
    test_keys = [
        'editor_title',
        'manual_editor',
        'save_changes',
        'appearance',
        'system',
        'apply',
        'dark_mode',
        'light_mode'
    ]
    
    for key in test_keys:
        print(f"  {key}: {t(key)}")

def test_all_languages():
    """Prueba todas las traducciones en todos los idiomas"""
    print("\n" + "=" * 60)
    print("PRUEBA DE TODOS LOS IDIOMAS")
    print("=" * 60)
    
    languages = ['es', 'en', 'pt', 'ca']
    test_key = 'editor_title'
    
    for lang in languages:
        set_language(lang)
        lang_names = {
            'es': 'Español',
            'en': 'English',
            'pt': 'Português',
            'ca': 'Català'
        }
        print(f"\n{lang_names[lang]} ({lang}):")
        print(f"  {test_key}: {t(test_key)}")
        print(f"  manual_editor: {t('manual_editor')}")
        print(f"  apply: {t('apply')}")
        print(f"  appearance: {t('appearance')}")

def test_env_override():
    """Prueba que las variables de entorno sobrescriben el locale"""
    print("\n" + "=" * 60)
    print("PRUEBA DE VARIABLES DE ENTORNO")
    print("=" * 60)
    
    # Guardar valores originales
    original_lang = os.environ.get('LANG')
    
    # Probar con diferentes idiomas
    test_langs = {
        'pt_BR.UTF-8': 'pt',
        'en_US.UTF-8': 'en',
        'es_ES.UTF-8': 'es',
        'ca_ES.UTF-8': 'ca'
    }
    
    for env_lang, expected_code in test_langs.items():
        os.environ['LANG'] = env_lang
        detected = get_system_language()
        status = "✓" if detected == expected_code else "✗"
        print(f"{status} LANG={env_lang} → Detectado: {detected} (Esperado: {expected_code})")
    
    # Restaurar valor original
    if original_lang:
        os.environ['LANG'] = original_lang
    else:
        os.environ.pop('LANG', None)

if __name__ == "__main__":
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   SISTEMA DE TRADUCCIÓN - SCRIPT DE PRUEBA              ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    
    test_language_detection()
    test_all_languages()
    test_env_override()
    
    print("\n" + "=" * 60)
    print("PRUEBAS COMPLETADAS")
    print("=" * 60)
    print("\nPara probar con un idioma específico:")
    print("  LANG=pt_BR.UTF-8 python3 test_translations.py")
    print("  LANG=en_US.UTF-8 python3 test_translations.py")
    print("  LANG=ca_ES.UTF-8 python3 test_translations.py")
    print()
