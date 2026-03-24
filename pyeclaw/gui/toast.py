from PySide6.QtCore import QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget

from pyeclaw.config import COLOR_PRIMARY, COLOR_TEXT, FONT_SYSTEM


class Toast(QLabel):
    """transient notification with slide-in/fade animation."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setFont(QFont(FONT_SYSTEM, 13))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(40)
        self.hide()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._dismiss)

        self._fade_anim: QPropertyAnimation | None = None
        self._set_style(False)

    def show_message(self, text: str, error: bool = False):
        """show a toast message for 4 seconds with slide-in animation."""
        self._timer.stop()
        self.setText(text)
        self._set_style(error)
        self._reposition()
        self._animate_in()
        self._timer.start(4000)

    def show_loading(self, text: str):
        """show a persistent message until explicitly dismissed."""
        self._timer.stop()
        self.setText(text)
        self._set_style(False)
        self._reposition()
        self._animate_in()

    def dismiss(self):
        """dismiss the toast immediately."""
        self._timer.stop()
        self._animate_out()

    def _set_style(self, error: bool):
        bg = COLOR_PRIMARY if error else COLOR_TEXT
        self.setStyleSheet(f"background-color: {bg}; color: white; padding: 0 20px; font-weight: 500;")

    def _reposition(self):
        parent = self.parentWidget()
        if parent:
            w = min(400, parent.width() - 40)
            self.setFixedWidth(w)
            x = (parent.width() - w) // 2
            y = parent.height() - 70
            self.move(x, y)

    def _animate_in(self):
        """slide-in and fade-in animation."""
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()

        if self._fade_anim is not None:
            self._fade_anim.stop()

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(200)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def _animate_out(self):
        """fade-out animation then hide."""
        if self._fade_anim is not None:
            self._fade_anim.stop()

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(200)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()

    def _dismiss(self):
        self._animate_out()
