#!/usr/bin/env python3
"""ConkyMan - Editor Lua para archivos de configuracion de Conky (PySide6)."""

import os
import sys
import configparser

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QTextEdit, QPushButton, QLabel, QLineEdit, QMessageBox,
)
from PySide6.QtGui import (
    QIcon, QColor, QFont, QPainter, QTextCharFormat, QSyntaxHighlighter,
    QTextCursor, QKeySequence, QTextFormat, QShortcut, QPalette,
)
from PySide6.QtCore import Qt, QRect, QSize, QRegularExpression

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translations import Translator
from app_identity import APP_ID, APP_NAME, install_icon_theme
from conkyman import _svg_render, _themed_icon, _themed_qss, QSS, hsep

APP_VERSION = "2.2-lts"

# Estilos propios del editor, añadidos al QSS compartido con la ventana principal.
EDITOR_QSS = """
QPushButton#tool_btn:checked { background: palette(highlight); color: palette(highlighted-text); }
QPlainTextEdit#code_edit {
    background: palette(base); color: palette(text);
    border: 1px solid __SEP__; border-radius: 8px;
    font-family: monospace; font-size: 11px; padding: 4px;
}
QWidget#gutter { background: palette(base); }
"""


def _load_saved_lang():
    cfg_file = os.path.join(os.path.expanduser("~"), ".config", "conkyman", "conkyman.conf")
    if os.path.exists(cfg_file):
        cfg = configparser.ConfigParser()
        cfg.read(cfg_file)
        return cfg.get("General", "language", fallback=None)
    return None


_tr = Translator(_load_saved_lang())


def t(key, default=None):
    return _tr.get(key, default or key)


# ---- Resaltado de sintaxis Lua ----

LUA_KEYWORDS = (
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "goto", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "until", "while",
)

LUA_BUILTINS = (
    "conky", "config", "text", "print", "pairs", "ipairs", "table",
    "string", "math", "os", "io", "tostring", "tonumber", "require",
)


class LuaHighlighter(QSyntaxHighlighter):
    """Resalta sintaxis Lua: keywords, builtins, strings, numeros y comentarios."""

    def __init__(self, document):
        super().__init__(document)
        self._rules = []

        def fmt(color, bold=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            return f

        kw_pattern = r"\b(?:%s)\b" % "|".join(LUA_KEYWORDS)
        bi_pattern = r"\b(?:%s)\b" % "|".join(LUA_BUILTINS)
        self._rules.append((QRegularExpression(kw_pattern), fmt("#C586C0", bold=True)))
        self._rules.append((QRegularExpression(bi_pattern), fmt("#4FC1FF")))
        self._rules.append((QRegularExpression(r"\b\d+\.?\d*\b"), fmt("#B5CEA8")))
        self._rules.append((QRegularExpression(r'"(?:\\.|[^"\\])*"'), fmt("#CE9178")))
        self._rules.append((QRegularExpression(r"'(?:\\.|[^'\\])*'"), fmt("#CE9178")))
        self._rules.append((QRegularExpression(r"--(?!\[\[).*"), fmt("#6A9955")))

        self._block_start = QRegularExpression(r"--\[\[")
        self._block_end = QRegularExpression(r"\]\]")
        self._block_fmt = fmt("#6A9955")

    def highlightBlock(self, text):
        for pattern, fmt_ in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt_)

        self.setCurrentBlockState(0)
        start = 0
        if self.previousBlockState() != 1:
            m = self._block_start.match(text)
            start = m.capturedStart() if m.hasMatch() else -1
        while start >= 0:
            m_end = self._block_end.match(text, start)
            if m_end.hasMatch():
                length = m_end.capturedEnd() - start
            else:
                self.setCurrentBlockState(1)
                length = len(text) - start
            self.setFormat(start, length, self._block_fmt)
            m = self._block_start.match(text, start + max(length, 1))
            start = m.capturedStart() if m.hasMatch() else -1


# ---- Gutter de numeros de linea ----

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.setObjectName("gutter")
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """QPlainTextEdit con numeracion de lineas y resaltado de la linea actual."""

    def __init__(self):
        super().__init__()
        self.setObjectName("code_edit")
        self.setFont(QFont("Monospace", 11))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.gutter = LineNumberArea(self)

        self.blockCountChanged.connect(self._update_gutter_width)
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self._update_gutter_width()
        self.highlight_current_line()

    def line_number_area_width(self):
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_gutter_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_gutter(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_gutter_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def paint_line_numbers(self, event):
        painter = QPainter(self.gutter)
        muted = self.palette().color(QPalette.WindowText)
        muted.setAlpha(140)
        painter.fillRect(event.rect(), self.palette().base())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(muted)
                painter.drawText(0, int(top), self.gutter.width() - 8, self.fontMetrics().height(),
                                  Qt.AlignRight, str(block_number + 1))
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self):
        selection = QTextEdit.ExtraSelection()
        color = self.palette().alternateBase().color()
        selection.format.setBackground(color)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])


# ---- Ventana principal del editor ----

class ConkyEditor(QMainWindow):

    def __init__(self, file_path=None):
        super().__init__()
        self.resize(820, 640)

        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.file_path = (
            file_path if file_path and os.path.exists(file_path)
            else self._detect_conky_path()
        )
        self._dirty = False

        install_icon_theme(os.path.join(self.base_path, "conkyman.svg"))
        logo_px = _svg_render(os.path.join(self.base_path, "conkyman.svg"), 32)
        if not logo_px.isNull():
            self.setWindowIcon(QIcon(logo_px))

        self.setStyleSheet(_themed_qss(self.palette()) + EDITOR_QSS)

        self._build_ui()
        self._load_file_content()
        self._update_title()

    # -- Deteccion de ruta --

    def _detect_conky_path(self):
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".config", "conky", "conky.lua"),
            os.path.join(home, ".config", "conky", "conky.conf"),
            os.path.join(home, ".conkyrc"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return candidates[0]

    # -- Construccion de la interfaz --

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        root.addWidget(self._build_toolbar())
        self.find_bar = self._build_find_bar()
        root.addWidget(self.find_bar)
        self.find_bar.hide()
        root.addWidget(self._build_editor())
        root.addWidget(self._build_statusbar())

        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._toggle_find_bar)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._on_save)
        QShortcut(QKeySequence("Escape"), self, activated=self._hide_find_bar)

    def _build_toolbar(self):
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        def tool_btn(icon_name, tooltip, checkable=False):
            btn = QPushButton()
            btn.setObjectName("tool_btn")
            btn.setIcon(_themed_icon(icon_name, 16, "#dddddd"))
            btn.setToolTip(tooltip)
            btn.setCheckable(checkable)
            btn.setCursor(Qt.PointingHandCursor)
            lay.addWidget(btn)
            return btn

        self.btn_save = tool_btn("document-save", t("save_changes", "Guardar cambios"))
        self.btn_save.clicked.connect(self._on_save)

        self.btn_reload = tool_btn("document-revert", t("reload_file", "Recargar archivo"))
        self.btn_reload.clicked.connect(self._on_reload)

        self.btn_find = tool_btn("edit-find-replace", t("find_replace", "Buscar y reemplazar"), checkable=True)
        self.btn_find.toggled.connect(self._on_find_toggled)

        self.btn_wrap = tool_btn("format-justify-left", t("word_wrap", "Ajuste de linea"), checkable=True)
        self.btn_wrap.toggled.connect(self._on_wrap_toggled)

        lay.addStretch(1)

        self.lbl_path = QLabel(self.file_path or "")
        self.lbl_path.setObjectName("mono")
        lay.addWidget(self.lbl_path)

        return bar

    def _build_find_bar(self):
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.entry_find = QLineEdit()
        self.entry_find.setPlaceholderText(t("find_placeholder", "Buscar..."))
        self.entry_find.setFixedWidth(200)
        self.entry_find.returnPressed.connect(self._find_next)
        self.entry_find.textChanged.connect(self._highlight_all)
        lay.addWidget(self.entry_find)

        self.entry_replace = QLineEdit()
        self.entry_replace.setPlaceholderText(t("replace_placeholder", "Reemplazar por..."))
        self.entry_replace.setFixedWidth(200)
        lay.addWidget(self.entry_replace)

        btn_replace = QPushButton(t("replace_one", "Reemplazar"))
        btn_replace.setObjectName("action_btn")
        btn_replace.clicked.connect(self._on_replace_one)
        lay.addWidget(btn_replace)

        btn_replace_all = QPushButton(t("replace_all", "Reemplazar todo"))
        btn_replace_all.setObjectName("action_btn")
        btn_replace_all.clicked.connect(self._on_replace_all)
        lay.addWidget(btn_replace_all)

        self.lbl_find_status = QLabel()
        self.lbl_find_status.setObjectName("sec_sub")
        lay.addWidget(self.lbl_find_status)

        lay.addStretch(1)

        btn_close = QPushButton(t("close", "Cerrar"))
        btn_close.setObjectName("tool_btn")
        btn_close.clicked.connect(lambda: self.btn_find.setChecked(False))
        lay.addWidget(btn_close)

        return bar

    def _build_editor(self):
        self.text_edit = CodeEditor()
        self.highlighter = LuaHighlighter(self.text_edit.document())
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.cursorPositionChanged.connect(self._update_status)
        return self.text_edit

    def _build_statusbar(self):
        box = QWidget()
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        outer.addWidget(hsep())

        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)

        self.lbl_status = QLabel()
        self.lbl_status.setObjectName("sec_sub")
        lay.addWidget(self.lbl_status)
        lay.addStretch(1)

        lbl_version = QLabel(f"ConkyMan {APP_VERSION}")
        lbl_version.setObjectName("ver_lbl")
        lay.addWidget(lbl_version)

        outer.addWidget(row)
        return box

    # -- Carga y guardado --

    def _load_file_content(self):
        if not self.file_path or not os.path.exists(self.file_path):
            self._update_status()
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.text_edit.blockSignals(True)
            self.text_edit.setPlainText(content)
            self.text_edit.blockSignals(False)
            self._mark_clean()
            self._update_status()
        except Exception as e:
            self._show_msg(f"{t('read_error', 'Error al leer')}: {e}", QMessageBox.Critical)

    def _on_reload(self):
        if self._dirty and not self._confirm(
                t("reload_confirm", "Recargar el archivo y descartar los cambios no guardados?")):
            return
        self._load_file_content()

    def _on_save(self):
        text = self.text_edit.toPlainText()

        conky_dir = os.path.join(os.path.expanduser("~"), ".config", "conky")
        os.makedirs(conky_dir, exist_ok=True)

        targets = [
            os.path.join(conky_dir, "conky.lua"),
            os.path.join(conky_dir, "conky.conf"),
        ]
        if self.file_path and self.file_path not in targets:
            targets.insert(0, self.file_path)

        errors = []
        for path in targets:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception as e:
                errors.append(f"{os.path.basename(path)}: {e}")

        if errors:
            self._show_msg(f"{t('save_error', 'Error al guardar')}:\n" + "\n".join(errors), QMessageBox.Critical)
            return

        self._mark_clean()
        self._show_msg(t("file_saved", "Archivo guardado correctamente."), QMessageBox.Information)
        os.system("killall -SIGUSR1 conky 2>/dev/null")

    # -- Estado del documento --

    def _on_text_changed(self):
        self._dirty = True
        self._update_title()
        self._update_status()

    def _mark_clean(self):
        self._dirty = False
        self._update_title()

    def _update_title(self):
        fname = os.path.basename(self.file_path) if self.file_path else t("file_not_found", "Archivo no encontrado")
        mark = "* " if self._dirty else ""
        self.setWindowTitle(f"{mark}{t('manual_editor', 'Editor Lua')} - {fname}")

    def closeEvent(self, event):
        if self._dirty and not self._confirm(
                t("unsaved_confirm", "Hay cambios sin guardar. Salir de todos modos?")):
            event.ignore()
            return
        event.accept()

    def _confirm(self, message):
        box = QMessageBox(self)
        box.setWindowTitle(t("editor_conkyman", "Editor ConkyMan"))
        box.setText(message)
        box.setIcon(QMessageBox.Question)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        return box.exec() == QMessageBox.Yes

    # -- Ajuste de linea --

    def _on_wrap_toggled(self, checked):
        mode = QPlainTextEdit.WidgetWidth if checked else QPlainTextEdit.NoWrap
        self.text_edit.setLineWrapMode(mode)

    # -- Buscar y reemplazar --

    def _toggle_find_bar(self):
        self.btn_find.setChecked(not self.btn_find.isChecked())

    def _on_find_toggled(self, checked):
        self.find_bar.setVisible(checked)
        if checked:
            self.entry_find.setFocus()
            self.entry_find.selectAll()
        else:
            self._clear_highlights()

    def _hide_find_bar(self):
        if self.btn_find.isChecked():
            self.btn_find.setChecked(False)
        self.text_edit.setFocus()

    def _highlight_all(self):
        doc = self.text_edit.document()
        needle = self.entry_find.text()

        extra = []
        if not needle:
            self.lbl_find_status.setText("")
            self.text_edit.setExtraSelections([])
            self.text_edit.highlight_current_line()
            return

        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#5c5c1e"))

        cursor = QTextCursor(doc)
        count = 0
        while True:
            cursor = doc.find(needle, cursor)
            if cursor.isNull():
                break
            sel = QTextEdit.ExtraSelection()
            sel.format = fmt
            sel.cursor = cursor
            extra.append(sel)
            count += 1

        self.text_edit.setExtraSelections(extra)
        if count == 0:
            self.lbl_find_status.setText(t("not_found", "No encontrado"))
        else:
            self.lbl_find_status.setText(f"{count} ↓")

    def _find_next(self):
        needle = self.entry_find.text()
        if not needle:
            return
        found = self.text_edit.find(needle)
        if not found:
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.text_edit.setTextCursor(cursor)
            self.text_edit.find(needle)

    def _clear_highlights(self):
        self.text_edit.setExtraSelections([])
        self.text_edit.highlight_current_line()
        self.lbl_find_status.setText("")

    def _on_replace_one(self):
        needle = self.entry_find.text()
        replace = self.entry_replace.text()
        if not needle:
            return
        cursor = self.text_edit.textCursor()
        if cursor.hasSelectedText() and cursor.selectedText() == needle:
            cursor.insertText(replace)
        self._find_next()

    def _on_replace_all(self):
        needle = self.entry_find.text()
        replace = self.entry_replace.text()
        if not needle:
            return

        doc = self.text_edit.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        count = 0
        pos = QTextCursor(doc)
        while True:
            pos = doc.find(needle, pos)
            if pos.isNull():
                break
            pos.insertText(replace)
            count += 1
        cursor.endEditBlock()

        self._highlight_all()
        self.lbl_find_status.setText(f"{count} {t('replaced_n', 'reemplazos realizados')}")

    # -- Barra de estado --

    def _update_status(self):
        cursor = self.text_edit.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        lines = self.text_edit.document().blockCount()
        tpl = t("line_col", "Linea {line}, Col {col}  |  {lines} lineas")
        self.lbl_status.setText(tpl.format(line=line, col=col, lines=lines))

    # -- Dialogos --

    def _show_msg(self, msg, icon):
        box = QMessageBox(self)
        box.setWindowTitle(t("editor_conkyman", "Editor ConkyMan"))
        box.setText(msg)
        box.setIcon(icon)
        box.exec()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_ID)
    win = ConkyEditor(target)
    win.show()
    sys.exit(app.exec())
