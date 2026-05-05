from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from pyeclaw.config import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_TEXT_SECONDARY,
    FONT_SYSTEM,
)


class LoadingSpinner(QWidget):
    """animated loading spinner."""

    def __init__(self, size: int = 28, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(16)

    def _step(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen_w = 3
        rect = self.rect().adjusted(pen_w, pen_w, -pen_w, -pen_w)

        # background ring
        p.setPen(QPen(QColor(COLOR_BORDER), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(rect)

        # accent arc
        p.setPen(QPen(QColor(COLOR_PRIMARY), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, self._angle * 16, 90 * 16)
        p.end()


class LoadingOverlay(QWidget):
    """full-window overlay with spinner and message."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: rgba(255, 255, 255, 178);")
        self.hide()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame(self)
        card.setObjectName("loadingCard")
        card.setStyleSheet(f"#loadingCard {{  background-color: {COLOR_BG};}}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 28, 40, 28)
        card_layout.setSpacing(14)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._spinner = LoadingSpinner(28, card)
        card_layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        self._message = QLabel("Loading...", card)
        self._message.setFont(QFont(FONT_SYSTEM, 13, QFont.Weight.Medium))
        self._message.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; background: transparent;")
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._message)

        layout.addWidget(card)

    def show_loading(self, message: str):
        """show overlay with message."""
        self._message.setText(message)
        self._reposition()
        self.show()
        self.raise_()

    def set_message(self, message: str):
        """update the loading message."""
        self._message.setText(message)

    def hide_loading(self):
        """hide the overlay."""
        self.hide()

    def _reposition(self):
        parent = self.parentWidget()
        if parent:
            self.setGeometry(0, 0, parent.width(), parent.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition()
