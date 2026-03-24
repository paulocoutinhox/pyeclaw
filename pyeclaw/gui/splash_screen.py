from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyeclaw.config import (
    APP_VERSION,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    FONT_SYSTEM,
)
from pyeclaw.gui.assets import Assets


class SplashScreen(QWidget):
    """welcome screen shown on first run, prompts to install latest version."""

    install_clicked = Signal(str)
    retry_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLOR_BG};")
        self._latest_version: str | None = None
        self._retry_mode = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 0, 40, 0)
        layout.setSpacing(0)

        layout.addStretch(2)

        # logo image
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._logo_label = QLabel(self)
        self._logo_label.setFixedSize(68, 68)
        self._logo_label.setStyleSheet("background: transparent;")
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = Assets.logo_pixmap(68)
        if not pixmap.isNull():
            self._logo_label.setPixmap(pixmap)

        logo_row.addWidget(self._logo_label)
        layout.addLayout(logo_row)

        layout.addSpacing(16)

        # title
        title = QLabel("OpenClaw", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont(FONT_SYSTEM, 30, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT};")
        layout.addWidget(title)

        layout.addSpacing(4)

        # subtitle
        sub = QLabel("Personal AI Assistant", self)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont(FONT_SYSTEM, 15))
        sub.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(sub)

        layout.addSpacing(8)

        # version description
        self._desc = QLabel("Detecting latest version...", self)
        self._desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc.setFont(QFont(FONT_SYSTEM, 13))
        self._desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        self._desc.setWordWrap(True)
        layout.addWidget(self._desc)

        layout.addSpacing(28)

        # install button
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._install_btn = QPushButton("Install", self)
        self._install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._install_btn.setFixedHeight(44)
        self._install_btn.setMinimumWidth(260)
        self._install_btn.setFont(QFont(FONT_SYSTEM, 14, QFont.Weight.DemiBold))
        self._install_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {COLOR_PRIMARY};"
            f"  color: white; border: none;"
            f"  padding: 0 40px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {COLOR_PRIMARY_HOVER};"
            f"}}"
            f"QPushButton:disabled {{"
            f"  opacity: 0.5;"
            f"}}"
        )
        self._install_btn.clicked.connect(self._on_install)
        self._install_btn.setEnabled(False)
        btn_row.addWidget(self._install_btn)
        layout.addLayout(btn_row)

        layout.addSpacing(16)

        # progress bar (hidden)
        progress_row = QHBoxLayout()
        progress_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setFixedSize(240, 4)
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(
            f"QProgressBar {{"
            f"  background-color: {COLOR_BORDER}; border: none;"
            f"}}"
            f"QProgressBar::chunk {{"
            f"  background-color: {COLOR_PRIMARY};"
            f"}}"
        )
        self._progress_bar.hide()
        progress_row.addWidget(self._progress_bar)
        layout.addLayout(progress_row)

        layout.addSpacing(12)

        # status label (hidden)
        self._status = QLabel("", self)
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setFont(QFont(FONT_SYSTEM, 11))
        self._status.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")
        self._status.setWordWrap(True)
        self._status.hide()
        layout.addWidget(self._status)

        # error label (hidden)
        self._error = QLabel("", self)
        self._error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error.setFont(QFont(FONT_SYSTEM, 11))
        self._error.setStyleSheet(f"color: {COLOR_DANGER};")
        self._error.setWordWrap(True)
        self._error.hide()
        layout.addWidget(self._error)

        layout.addStretch(3)

        # footer
        footer = QLabel(f"v{APP_VERSION}", self)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFont(QFont(FONT_SYSTEM, 11))
        footer.setStyleSheet(f"color: {COLOR_BORDER}; padding-bottom: 16px;")
        layout.addWidget(footer)

    def reset(self):
        """reset splash to initial state."""
        self._latest_version = None
        self._retry_mode = False
        self._desc.setText("Detecting latest version...")
        self._desc.show()
        self._install_btn.setText("Install")
        self._install_btn.setEnabled(False)
        self._install_btn.show()
        self._progress_bar.hide()
        self._status.hide()
        self._error.hide()

    def set_latest_version(self, version: str):
        """set the detected latest version and enable install."""
        self._latest_version = version
        self._desc.setText(f"Install openclaw {version} to get started.")
        self._install_btn.setText(f"Install {version}")
        self._install_btn.setEnabled(True)

    def show_progress(self, message: str):
        """show progress bar with status message."""
        self._error.hide()
        self._install_btn.hide()
        self._desc.hide()
        self._progress_bar.show()
        self._status.setText(message)
        self._status.show()

    def show_error(self, message: str):
        """show error message and re-enable install."""
        self._progress_bar.hide()
        self._status.hide()
        self._desc.show()
        self._error.setText(message)
        self._error.show()
        self._install_btn.show()

    def show_retry(self):
        """show retry state when release fetch fails."""
        self._retry_mode = True
        self._progress_bar.hide()
        self._status.hide()
        self._error.hide()
        self._desc.setText("Could not fetch releases. Check your connection and try again.")
        self._desc.show()
        self._install_btn.setText("Retry")
        self._install_btn.setEnabled(True)
        self._install_btn.show()

    def _on_install(self):
        if self._retry_mode:
            self._retry_mode = False
            self._desc.setText("Checking for available versions...")
            self._install_btn.setText("Install")
            self._install_btn.setEnabled(False)
            self.retry_clicked.emit()
            return
        if self._latest_version:
            self.install_clicked.emit(self._latest_version)
