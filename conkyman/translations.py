import locale
import os

def get_system_language():
    """Detecta el idioma del sistema desde variables de entorno y locale"""
    supported_langs = ['es', 'en', 'pt', 'ca']
    
    # Prioridad 1: Variable de entorno LANGUAGE
    lang_env = os.environ.get('LANGUAGE', '').split(':')[0]
    if lang_env:
        lang_code = lang_env.split('_')[0].split('.')[0].lower()
        if lang_code in supported_langs:
            return lang_code
    
    # Prioridad 2: Variable de entorno LANG
    lang_env = os.environ.get('LANG', '')
    if lang_env:
        lang_code = lang_env.split('_')[0].split('.')[0].lower()
        if lang_code in supported_langs:
            return lang_code
    
    # Prioridad 3: Variable de entorno LC_ALL
    lang_env = os.environ.get('LC_ALL', '')
    if lang_env:
        lang_code = lang_env.split('_')[0].split('.')[0].lower()
        if lang_code in supported_langs:
            return lang_code
    
    # Prioridad 4: locale del sistema
    try:
        lang = locale.getdefaultlocale()[0]
        if lang:
            lang_code = lang.split('_')[0].lower()
            if lang_code in supported_langs:
                return lang_code
    except:
        pass
    
    # Por defecto: inglés
    return 'en'

# Diccionario de traducciones
TRANSLATIONS = {
    'es': {
        # text.py translations
        'editor_title': 'Editor de Configuración - ConkyMan',
        'manual_editor': 'Editor Manual',
        'file_not_found': 'Archivo no encontrado',
        'save_changes': 'Guardar cambios',
        'read_error': 'Error al leer',
        'file_saved': 'Archivo guardado correctamente.',
        'save_error': 'Error al guardar',
        'editor_conkyman': 'Editor ConkyMan',
        
        # conkyman.py translations
        'conkyman_title': 'ConkyMan - Gestor de Conky',
        'preview': 'Vista Previa',
        'configurations': 'Configuraciones',
        'add': 'Agregar',
        'select_folder': 'Seleccionar carpeta',
        'select_config': 'Seleccionar configuración',
        'edit': 'Editar',
        'open_editor': 'Abrir editor de texto',
        'delete': 'Eliminar',
        'delete_config': 'Eliminar configuración',
        'active': 'Activa',
        'currently_active': 'Configuración actualmente activa',
        'conky_folder': 'Carpeta de Conky',
        'apply': 'Aplicar',
        'apply_config': 'Aplicar configuración seleccionada',
        'refresh': 'Actualizar',
        'refresh_list': 'Actualizar lista',
        'no_preview': 'Sin vista previa',
        'select_config_msg': 'Selecciona una configuración para ver la vista previa',
        'select_folder_title': 'Seleccionar carpeta de configuraciones',
        'folder_applied': 'Carpeta aplicada correctamente.',
        'folder_error': 'Error al aplicar carpeta',
        'select_config_title': 'Seleccionar archivo de configuración',
        'config_added': 'Configuración agregada correctamente.',
        'config_error': 'Error al agregar configuración',
        'confirm_delete': 'Confirmar eliminación',
        'delete_confirm_msg': '¿Estás seguro de que deseas eliminar esta configuración?',
        'config_deleted': 'Configuración eliminada correctamente.',
        'delete_error': 'Error al eliminar',
        'config_applied': 'Configuración aplicada correctamente.',
        'apply_error': 'Error al aplicar configuración',
        'conky_restarted': 'Conky reiniciado correctamente.',
        'restart_error': 'Error al reiniciar Conky',
        'info': 'Información',
        'warning': 'Advertencia',
        'error': 'Error',
        
        # UI Elements
        'appearance': 'Apariencia',
        'system': 'Sistema',
        'location': 'Ubicación',
        'top_right': 'Arriba-Derecha',
        'top_left': 'Arriba-Izquierda',
        'bottom_right': 'Abajo-Derecha',
        'bottom_left': 'Abajo-Izquierda',
        'center': 'Centro',
        'color_mode': 'Modo de Color',
        'dark_mode': 'Modo Dark',
        'light_mode': 'Modo Light',
        'accent_colors': 'Colores de Acento',
        'custom': 'Personalizado',
        'time_format': 'Formato de Hora',
        '24_hours': '24 Horas',
        '12_hours': '12 Horas (AM/PM)',
        'conky_type': 'Tipo de Conky',
        'dock': 'Dock',
        'normal': 'Normal',
        'desktop': 'Desktop',
        'panel': 'Panel',
        'minimalist_mode': 'Modo Minimalista',
        'enable_minimalist': 'Activar Conky Minimalista (solo reloj)',
        'total_configuration': 'Configuración Total',
        'restore_defaults_title': 'ConkyMan',
        'restore_defaults_msg': '¿Deseas restaurar el archivo de configuración predeterminado (conky.lua)?',
        'changes_applied': 'Cambios aplicados con éxito.',
    },
    'en': {
        # text.py translations
        'editor_title': 'Configuration Editor - ConkyMan',
        'manual_editor': 'Manual Editor',
        'file_not_found': 'File not found',
        'save_changes': 'Save changes',
        'read_error': 'Error reading',
        'file_saved': 'File saved successfully.',
        'save_error': 'Error saving',
        'editor_conkyman': 'ConkyMan Editor',
        
        # conkyman.py translations
        'conkyman_title': 'ConkyMan - Conky Manager',
        'preview': 'Preview',
        'configurations': 'Configurations',
        'add': 'Add',
        'select_folder': 'Select folder',
        'select_config': 'Select configuration',
        'edit': 'Edit',
        'open_editor': 'Open text editor',
        'delete': 'Delete',
        'delete_config': 'Delete configuration',
        'active': 'Active',
        'currently_active': 'Currently active configuration',
        'conky_folder': 'Conky Folder',
        'apply': 'Apply',
        'apply_config': 'Apply selected configuration',
        'refresh': 'Refresh',
        'refresh_list': 'Refresh list',
        'no_preview': 'No preview',
        'select_config_msg': 'Select a configuration to view preview',
        'select_folder_title': 'Select configurations folder',
        'folder_applied': 'Folder applied successfully.',
        'folder_error': 'Error applying folder',
        'select_config_title': 'Select configuration file',
        'config_added': 'Configuration added successfully.',
        'config_error': 'Error adding configuration',
        'confirm_delete': 'Confirm deletion',
        'delete_confirm_msg': 'Are you sure you want to delete this configuration?',
        'config_deleted': 'Configuration deleted successfully.',
        'delete_error': 'Error deleting',
        'config_applied': 'Configuration applied successfully.',
        'apply_error': 'Error applying configuration',
        'conky_restarted': 'Conky restarted successfully.',
        'restart_error': 'Error restarting Conky',
        'info': 'Information',
        'warning': 'Warning',
        'error': 'Error',
        
        # UI Elements
        'appearance': 'Appearance',
        'system': 'System',
        'location': 'Location',
        'top_right': 'Top-Right',
        'top_left': 'Top-Left',
        'bottom_right': 'Bottom-Right',
        'bottom_left': 'Bottom-Left',
        'center': 'Center',
        'color_mode': 'Color Mode',
        'dark_mode': 'Dark Mode',
        'light_mode': 'Light Mode',
        'accent_colors': 'Accent Colors',
        'custom': 'Custom',
        'time_format': 'Time Format',
        '24_hours': '24 Hours',
        '12_hours': '12 Hours (AM/PM)',
        'conky_type': 'Conky Type',
        'dock': 'Dock',
        'normal': 'Normal',
        'desktop': 'Desktop',
        'panel': 'Panel',
        'minimalist_mode': 'Minimalist Mode',
        'enable_minimalist': 'Enable Minimalist Conky (clock only)',
        'total_configuration': 'Total Configuration',
        'restore_defaults_title': 'ConkyMan',
        'restore_defaults_msg': 'Do you want to restore the default configuration file (conky.lua)?',
        'changes_applied': 'Changes applied successfully.',
    },
    'pt': {
        # text.py translations
        'editor_title': 'Editor de Configuração - ConkyMan',
        'manual_editor': 'Editor Manual',
        'file_not_found': 'Arquivo não encontrado',
        'save_changes': 'Salvar alterações',
        'read_error': 'Erro ao ler',
        'file_saved': 'Arquivo salvo com sucesso.',
        'save_error': 'Erro ao salvar',
        'editor_conkyman': 'Editor ConkyMan',
        
        # conkyman.py translations
        'conkyman_title': 'ConkyMan - Gerenciador de Conky',
        'preview': 'Visualização',
        'configurations': 'Configurações',
        'add': 'Adicionar',
        'select_folder': 'Selecionar pasta',
        'select_config': 'Selecionar configuração',
        'edit': 'Editar',
        'open_editor': 'Abrir editor de texto',
        'delete': 'Excluir',
        'delete_config': 'Excluir configuração',
        'active': 'Ativa',
        'currently_active': 'Configuração atualmente ativa',
        'conky_folder': 'Pasta do Conky',
        'apply': 'Aplicar',
        'apply_config': 'Aplicar configuração selecionada',
        'refresh': 'Atualizar',
        'refresh_list': 'Atualizar lista',
        'no_preview': 'Sem visualização',
        'select_config_msg': 'Selecione uma configuração para ver a visualização',
        'select_folder_title': 'Selecionar pasta de configurações',
        'folder_applied': 'Pasta aplicada com sucesso.',
        'folder_error': 'Erro ao aplicar pasta',
        'select_config_title': 'Selecionar arquivo de configuração',
        'config_added': 'Configuração adicionada com sucesso.',
        'config_error': 'Erro ao adicionar configuração',
        'confirm_delete': 'Confirmar exclusão',
        'delete_confirm_msg': 'Tem certeza de que deseja excluir esta configuração?',
        'config_deleted': 'Configuração excluída com sucesso.',
        'delete_error': 'Erro ao excluir',
        'config_applied': 'Configuração aplicada com sucesso.',
        'apply_error': 'Erro ao aplicar configuração',
        'conky_restarted': 'Conky reiniciado com sucesso.',
        'restart_error': 'Erro ao reiniciar o Conky',
        'info': 'Informação',
        'warning': 'Aviso',
        'error': 'Erro',
        
        # UI Elements
        'appearance': 'Aparência',
        'system': 'Sistema',
        'location': 'Localização',
        'top_right': 'Superior-Direita',
        'top_left': 'Superior-Esquerda',
        'bottom_right': 'Inferior-Direita',
        'bottom_left': 'Inferior-Esquerda',
        'center': 'Centro',
        'color_mode': 'Modo de Cor',
        'dark_mode': 'Modo Escuro',
        'light_mode': 'Modo Claro',
        'accent_colors': 'Cores de Destaque',
        'custom': 'Personalizado',
        'time_format': 'Formato de Hora',
        '24_hours': '24 Horas',
        '12_hours': '12 Horas (AM/PM)',
        'conky_type': 'Tipo de Conky',
        'dock': 'Dock',
        'normal': 'Normal',
        'desktop': 'Desktop',
        'panel': 'Painel',
        'minimalist_mode': 'Modo Minimalista',
        'enable_minimalist': 'Ativar Conky Minimalista (apenas relógio)',
        'total_configuration': 'Configuração Total',
        'restore_defaults_title': 'ConkyMan',
        'restore_defaults_msg': 'Deseja restaurar o arquivo de configuração padrão (conky.lua)?',
        'changes_applied': 'Alterações aplicadas com sucesso.',
    },
    'ca': {
        # text.py translations
        'editor_title': 'Editor de Configuració - ConkyMan',
        'manual_editor': 'Editor Manual',
        'file_not_found': 'Arxiu no trobat',
        'save_changes': 'Desar canvis',
        'read_error': 'Error en llegir',
        'file_saved': 'Arxiu desat correctament.',
        'save_error': 'Error en desar',
        'editor_conkyman': 'Editor ConkyMan',
        
        # conkyman.py translations
        'conkyman_title': 'ConkyMan - Gestor de Conky',
        'preview': 'Vista Prèvia',
        'configurations': 'Configuracions',
        'add': 'Afegir',
        'select_folder': 'Seleccionar carpeta',
        'select_config': 'Seleccionar configuració',
        'edit': 'Editar',
        'open_editor': 'Obrir editor de text',
        'delete': 'Eliminar',
        'delete_config': 'Eliminar configuració',
        'active': 'Activa',
        'currently_active': 'Configuració actualment activa',
        'conky_folder': 'Carpeta de Conky',
        'apply': 'Aplicar',
        'apply_config': 'Aplicar configuració seleccionada',
        'refresh': 'Actualitzar',
        'refresh_list': 'Actualitzar llista',
        'no_preview': 'Sense vista prèvia',
        'select_config_msg': 'Selecciona una configuració per veure la vista prèvia',
        'select_folder_title': 'Seleccionar carpeta de configuracions',
        'folder_applied': 'Carpeta aplicada correctament.',
        'folder_error': 'Error en aplicar carpeta',
        'select_config_title': 'Seleccionar arxiu de configuració',
        'config_added': 'Configuració afegida correctament.',
        'config_error': 'Error en afegir configuració',
        'confirm_delete': 'Confirmar eliminació',
        'delete_confirm_msg': 'Estàs segur que vols eliminar aquesta configuració?',
        'config_deleted': 'Configuració eliminada correctament.',
        'delete_error': 'Error en eliminar',
        'config_applied': 'Configuració aplicada correctament.',
        'apply_error': 'Error en aplicar configuració',
        'conky_restarted': 'Conky reiniciat correctament.',
        'restart_error': 'Error en reiniciar Conky',
        'info': 'Informació',
        'warning': 'Advertència',
        'error': 'Error',
        
        # UI Elements
        'appearance': 'Aparença',
        'system': 'Sistema',
        'location': 'Ubicació',
        'top_right': 'Superior-Dreta',
        'top_left': 'Superior-Esquerra',
        'bottom_right': 'Inferior-Dreta',
        'bottom_left': 'Inferior-Esquerra',
        'center': 'Centre',
        'color_mode': 'Mode de Color',
        'dark_mode': 'Mode Fosc',
        'light_mode': 'Mode Clar',
        'accent_colors': 'Colors d\'Accent',
        'custom': 'Personalitzat',
        'time_format': 'Format d\'Hora',
        '24_hours': '24 Hores',
        '12_hours': '12 Hores (AM/PM)',
        'conky_type': 'Tipus de Conky',
        'dock': 'Dock',
        'normal': 'Normal',
        'desktop': 'Escriptori',
        'panel': 'Panell',
        'minimalist_mode': 'Mode Minimalista',
        'enable_minimalist': 'Activar Conky Minimalista (només rellotge)',
        'total_configuration': 'Configuració Total',
        'restore_defaults_title': 'ConkyMan',
        'restore_defaults_msg': 'Vols restaurar l\'arxiu de configuració predeterminat (conky.lua)?',
        'changes_applied': 'Canvis aplicats amb èxit.',
    }
}

class Translator:
    def __init__(self, lang=None):
        self.lang = lang if lang else get_system_language()
        
    def get(self, key, default=None):
        """Obtiene la traducción para una clave"""
        if self.lang in TRANSLATIONS:
            return TRANSLATIONS[self.lang].get(key, default or key)
        return TRANSLATIONS['en'].get(key, default or key)
    
    def __call__(self, key, default=None):
        """Permite usar el traductor como función: t('key')"""
        return self.get(key, default)

# Instancia global del traductor
_translator = Translator()

def t(key, default=None):
    """Función auxiliar para traducir"""
    return _translator.get(key, default)

def set_language(lang):
    """Cambia el idioma del traductor"""
    global _translator
    _translator = Translator(lang)

def get_current_language():
    """Retorna el idioma actual"""
    return _translator.lang
