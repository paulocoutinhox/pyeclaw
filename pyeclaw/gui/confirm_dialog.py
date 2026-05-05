from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyeclaw.config import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_TEXT,
    COLOR_TEXT_SECONDARY,
    FONT_SYSTEM,
)


class ConfirmDialog(QDialog):
    """styled confirmation dialog with title, message, cancel/confirm buttons."""

    def __init__(
        self,
        title: str,
        message: str,
        parent: QWidget | None = None,
        confirm_text: str = "Confirm",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(360)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui(title, message, confirm_text)

    def _build_ui(self, title: str, message: str, confirm_text: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget(self)
        card.setObjectName("confirmCard")
        card.setStyleSheet(f"#confirmCard {{  background-color: {COLOR_BG};}}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # header
        header = QWidget(card)
        header.setObjectName("confirmHeader")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.setStyleSheet(f"#confirmHeader {{  border-bottom: 1px solid {COLOR_BORDER};  background: transparent;}}")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 16, 20, 16)

        title_label = QLabel(title, header)
        title_label.setFont(QFont(FONT_SYSTEM, 16, QFont.Weight.DemiBold))
        title_label.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")
        h_layout.addWidget(title_label)
        h_layout.addStretch()
        card_layout.addWidget(header)

        # body
        body = QWidget(card)
        body.setStyleSheet("background: transparent;")
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(20, 16, 20, 16)

        msg_label = QLabel(message, body)
        msg_label.setFont(QFont(FONT_SYSTEM, 13))
        msg_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; background: transparent;")
        msg_label.setWordWrap(True)
        b_layout.addWidget(msg_label)
        card_layout.addWidget(body)

        # footer
        footer = QWidget(card)
        footer.setObjectName("confirmFooter")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        footer.setStyleSheet(f"#confirmFooter {{  border-top: 1px solid {COLOR_BORDER};  background: transparent;}}")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(20, 12, 20, 12)
        f_layout.setSpacing(8)
        f_layout.addStretch()

        cancel_btn = QPushButton("Cancel", footer)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFont(QFont(FONT_SYSTEM, 12, QFont.Weight.Medium))
        cancel_btn.setStyleSheet(
            f"QPushButton {{"
            f"  padding: 6px 14px; background: none;"
            f"  border: 1px solid {COLOR_BORDER};"
            f"  color: {COLOR_TEXT_SECONDARY};"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: #F3F4F6; color: {COLOR_TEXT};"
            f"}}"
        )
        cancel_btn.clicked.connect(self.reject)
        f_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton(confirm_text, footer)
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setFont(QFont(FONT_SYSTEM, 12, QFont.Weight.Medium))
        confirm_btn.setStyleSheet(
            f"QPushButton {{"
            f"  padding: 6px 14px; background-color: {COLOR_PRIMARY};"
            f"  color: white; border: none;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {COLOR_PRIMARY_HOVER};"
            f"}}"
        )
        confirm_btn.clicked.connect(self.accept)
        f_layout.addWidget(confirm_btn)

        card_layout.addWidget(footer)
        outer.addWidget(card)

    @staticmethod
    def ask(
        title: str,
        message: str,
        parent: QWidget | None = None,
        confirm_text: str = "Confirm",
    ) -> bool:
        """show dialog and return True if confirmed."""
        dialog = ConfirmDialog(title, message, parent, confirm_text)
        return dialog.exec() == QDialog.DialogCode.Accepted
