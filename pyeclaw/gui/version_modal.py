from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pyeclaw.config import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_HOVER,
    COLOR_ONLINE,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING_LIGHT,
    FONT_MONO,
    FONT_SYSTEM,
)
from pyeclaw.gui.loading_overlay import LoadingSpinner


class ReleaseItem(QWidget):
    """single release row in the version modal."""

    install_clicked = Signal(str)

    def __init__(self, tag: str, name: str, date_str: str, prerelease: bool, installed: bool, parent: QWidget):
        super().__init__(parent)
        self._tag = tag
        self.setObjectName("releaseItem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"#releaseItem {{"
            f"  border: 1px solid {COLOR_BORDER_LIGHT};"
            f"  background: transparent;"
            f"}}"
            f"#releaseItem:hover {{"
            f"  background: {COLOR_HOVER};"
            f"}}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        # info column
        info = QVBoxLayout()
        info.setSpacing(2)

        # tag row with optional prerelease badge
        tag_row = QHBoxLayout()
        tag_row.setSpacing(6)
        tag_label = QLabel(tag, self)
        tag_label.setFont(QFont(FONT_SYSTEM, 13, QFont.Weight.Medium))
        tag_label.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent; border: none;")
        tag_row.addWidget(tag_label)

        if prerelease:
            badge = QLabel("beta", self)
            badge.setFont(QFont(FONT_SYSTEM, 10))
            badge.setStyleSheet(
                f"color: #A16207; background-color: {COLOR_WARNING_LIGHT};"
                f" border-radius: 10px; padding: 2px 6px; border: none;"
            )
            tag_row.addWidget(badge)

        tag_row.addStretch()
        info.addLayout(tag_row)

        # date
        formatted_date = self._format_date(date_str)
        date_label = QLabel(formatted_date, self)
        date_label.setFont(QFont(FONT_SYSTEM, 11))
        date_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent; border: none;")
        info.addWidget(date_label)

        layout.addLayout(info)
        layout.addStretch()

        # action
        if installed:
            status = QLabel("Installed", self)
            status.setFont(QFont(FONT_SYSTEM, 11, QFont.Weight.Medium))
            status.setStyleSheet(f"color: {COLOR_ONLINE}; background: transparent; border: none;")
            layout.addWidget(status)
        else:
            btn = QPushButton("Install", self)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont(FONT_SYSTEM, 11, QFont.Weight.Medium))
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  padding: 5px 12px; background-color: {COLOR_PRIMARY};"
                f"  color: white; border: none; border-radius: 6px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: {COLOR_PRIMARY_HOVER};"
                f"}}"
            )
            btn.clicked.connect(lambda: self.install_clicked.emit(self._tag))
            layout.addWidget(btn)

    def _format_date(self, iso_str: str) -> str:
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt.strftime("%b %d, %Y")
        except (ValueError, AttributeError):
            return iso_str[:10] if iso_str else ""


class VersionModal(QDialog):
    """add version modal with custom version input and remote releases list."""

    install_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Version")
        self.setFixedSize(440, 500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget(self)
        card.setObjectName("versionModalCard")
        card.setStyleSheet(f"#versionModalCard {{  background-color: {COLOR_BG};}}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # header
        header = QWidget(card)
        header.setObjectName("vmHeader")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.setStyleSheet(f"#vmHeader {{ border-bottom: 1px solid {COLOR_BORDER}; background: transparent; }}")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("Add Version", header)
        title.setFont(QFont(FONT_SYSTEM, 16, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        close_btn = QPushButton("\u00d7", header)
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFont(QFont(FONT_SYSTEM, 18))
        close_btn.setStyleSheet(
            f"QPushButton {{ background: none; color: {COLOR_TEXT_SECONDARY};"
            f" border: 1px solid {COLOR_BORDER}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {COLOR_HOVER}; color: {COLOR_TEXT}; }}"
        )
        close_btn.clicked.connect(self.reject)
        h_layout.addWidget(close_btn)
        card_layout.addWidget(header)

        # body
        body = QWidget(card)
        body.setStyleSheet("background: transparent;")
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(20, 16, 20, 16)
        b_layout.setSpacing(0)

        # custom version input (hidden while loading)
        self._custom_row_widget = QWidget(body)
        self._custom_row_widget.setStyleSheet("background: transparent;")
        custom_row = QHBoxLayout(self._custom_row_widget)
        custom_row.setContentsMargins(0, 0, 0, 0)
        custom_row.setSpacing(8)

        self._tag_input = QLineEdit(self._custom_row_widget)
        self._tag_input.setPlaceholderText("e.g. v2026.3.13")
        self._tag_input.setFixedHeight(34)
        self._tag_input.setFont(QFont(FONT_MONO, 13))
        self._tag_input.setStyleSheet(
            f"QLineEdit {{"
            f"  background-color: white; color: {COLOR_TEXT};"
            f"  border: 1px solid {COLOR_BORDER}; border-radius: 6px;"
            f"  padding: 0 10px;"
            f"}}"
            f"QLineEdit:focus {{ border-color: {COLOR_PRIMARY}; }}"
        )
        self._tag_input.returnPressed.connect(self._on_custom_install)
        custom_row.addWidget(self._tag_input)

        install_btn = QPushButton("Install", self._custom_row_widget)
        install_btn.setFixedSize(60, 34)
        install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        install_btn.setFont(QFont(FONT_SYSTEM, 12, QFont.Weight.Medium))
        install_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLOR_PRIMARY}; color: white;"
            f" border: none; border-radius: 6px; }}"
            f"QPushButton:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}"
        )
        install_btn.clicked.connect(self._on_custom_install)
        custom_row.addWidget(install_btn)

        self._custom_row_widget.hide()
        b_layout.addWidget(self._custom_row_widget)

        # spacing between input and releases (hidden while loading)
        self._input_spacer = QWidget(body)
        self._input_spacer.setFixedHeight(16)
        self._input_spacer.setStyleSheet("background: transparent;")
        self._input_spacer.hide()
        b_layout.addWidget(self._input_spacer)

        # releases header (hidden while loading)
        self._releases_header = QLabel("Latest releases from GitHub", body)
        self._releases_header.setFont(QFont(FONT_SYSTEM, 11, QFont.Weight.DemiBold))
        self._releases_header.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; background: transparent; letter-spacing: 0.5px; text-transform: uppercase;"
        )
        self._releases_header.hide()
        b_layout.addWidget(self._releases_header)

        self._releases_header_spacer = QWidget(body)
        self._releases_header_spacer.setFixedHeight(8)
        self._releases_header_spacer.setStyleSheet("background: transparent;")
        self._releases_header_spacer.hide()
        b_layout.addWidget(self._releases_header_spacer)

        # scrollable releases list
        scroll = QScrollArea(body)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { background: transparent; width: 4px; }"
            "QScrollBar::handle:vertical {"
            "  background: rgba(0,0,0,0.08); border-radius: 2px; min-height: 20px;"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {"
            "  height: 0; background: none;"
            "}"
        )

        self._releases_container = QWidget()
        self._releases_container.setStyleSheet("background: transparent;")
        self._releases_layout = QVBoxLayout(self._releases_container)
        self._releases_layout.setContentsMargins(0, 0, 0, 0)
        self._releases_layout.setSpacing(4)
        self._releases_layout.addStretch()

        # loading placeholder with spinner
        self._loading_widget = QWidget(self._releases_container)
        self._loading_widget.setStyleSheet("background: transparent;")
        lw_layout = QVBoxLayout(self._loading_widget)
        lw_layout.setContentsMargins(0, 32, 0, 32)
        lw_layout.setSpacing(10)
        lw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._loading_spinner = LoadingSpinner(20, self._loading_widget)
        lw_layout.addWidget(self._loading_spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        self._loading_label = QLabel("Loading releases...", self._loading_widget)
        self._loading_label.setFont(QFont(FONT_SYSTEM, 13))
        self._loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lw_layout.addWidget(self._loading_label)

        self._releases_layout.insertWidget(0, self._loading_widget)

        scroll.setWidget(self._releases_container)
        b_layout.addWidget(scroll)

        card_layout.addWidget(body)
        outer.addWidget(card)

    def set_releases(self, releases: list):
        """populate the releases list."""
        # clear existing release items (keep the stretch at the end)
        while self._releases_layout.count() > 1:
            item = self._releases_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        # hide loading, show content
        self._loading_widget.hide()
        self._custom_row_widget.show()
        self._input_spacer.show()
        self._releases_header.show()
        self._releases_header_spacer.show()

        if not releases:
            self._loading_label.setText("Failed to load releases")
            self._loading_spinner.hide()
            self._loading_widget.show()
            return

        for r in releases:
            row = ReleaseItem(
                tag=r.tag,
                name=r.name,
                date_str=r.published_at,
                prerelease=r.prerelease,
                installed=r.installed,
                parent=self._releases_container,
            )
            row.install_clicked.connect(self._on_release_install)
            idx = self._releases_layout.count() - 1
            self._releases_layout.insertWidget(idx, row)

    def _on_custom_install(self):
        tag = self._tag_input.text().strip()
        if tag:
            self._tag_input.clear()
            self.install_requested.emit(tag)
            self.accept()

    def _on_release_install(self, tag: str):
        self.install_requested.emit(tag)
        self.accept()
