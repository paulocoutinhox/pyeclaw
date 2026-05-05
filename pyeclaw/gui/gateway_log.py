from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QLabel, QStackedWidget, QTextEdit, QVBoxLayout, QWidget

from pyeclaw.config import (
    COLOR_BG,
    COLOR_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    FONT_MONO,
    FONT_SYSTEM,
)


class GatewayLog(QWidget):
    """gateway log viewer with empty state and clean text display."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLOR_BG};")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet("QStackedWidget { border: none; }")

        # empty state (index 0)
        empty = QWidget(self._stack)
        empty.setStyleSheet(f"background-color: {COLOR_BG};")
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_msg = QLabel("No logs yet. Start the gateway to see output.", empty)
        empty_msg.setFont(QFont(FONT_SYSTEM, 13))
        empty_msg.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")
        empty_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_msg)
        self._stack.addWidget(empty)

        # log display (index 1)
        self._display = QTextEdit(self._stack)
        self._display.setReadOnly(True)
        self._display.setFont(QFont(FONT_MONO, 12))
        self._display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._display.setStyleSheet(
            f"QTextEdit {{"
            f"  background-color: {COLOR_BG}; color: {COLOR_TEXT_SECONDARY};"
            f"  border: none; padding: 12px 16px;"
            f"}}"
            f"QScrollBar:vertical {{"
            f"  background: transparent; width: 6px;"
            f"}}"
            f"QScrollBar::handle:vertical {{"
            f"  background: rgba(0,0,0,0.12);"
            f"  border-radius: 3px; min-height: 30px;"
            f"}}"
            f"QScrollBar::add-line:vertical,"
            f"QScrollBar::sub-line:vertical,"
            f"QScrollBar::add-page:vertical,"
            f"QScrollBar::sub-page:vertical {{"
            f"  height: 0; background: none;"
            f"}}"
        )
        self._stack.addWidget(self._display)

        # start with empty state
        self._stack.setCurrentIndex(0)
        layout.addWidget(self._stack)

    def append_text(self, text: str):
        """append clean text line with error highlighting and auto-scroll."""
        if not text.strip():
            return
        # switch to log display
        self._stack.setCurrentIndex(1)
        cursor = self._display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if self._display.toPlainText():
            cursor.insertText("\n")

        # highlight error lines in red
        is_error = "error" in text.lower()
        if is_error:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(COLOR_PRIMARY))
            cursor.insertText(text, fmt)
        else:
            cursor.insertText(text)

        self._display.setTextCursor(cursor)
        self._display.ensureCursorVisible()

    def show_empty(self):
        """show the empty state message."""
        self._stack.setCurrentIndex(0)

    def clear(self):
        """clear all log text."""
        self._display.clear()
        self._stack.setCurrentIndex(0)
