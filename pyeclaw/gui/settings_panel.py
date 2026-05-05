from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pyeclaw.config import (
    APP_NAME,
    APP_VERSION,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_HOVER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    FONT_MONO,
    FONT_SYSTEM,
)


class _SettingsTab(QWidget):
    """clickable tab button for settings navigation."""

    clicked = Signal(int)

    def __init__(self, text: str, index: int, parent: QWidget):
        super().__init__(parent)
        self._index = index
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 0)
        layout.setSpacing(0)

        self._label = QLabel(text, self)
        self._label.setFont(QFont(FONT_SYSTEM, 12, QFont.Weight.Medium))
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: transparent;")
        layout.addWidget(self._label)

        layout.addSpacing(6)

        self._indicator = QWidget(self)
        self._indicator.setFixedHeight(2)
        layout.addWidget(self._indicator)

        self._apply_style()

    def set_active(self, active: bool):
        self._active = active
        self._apply_style()

    def _apply_style(self):
        if self._active:
            self._label.setStyleSheet(f"color: {COLOR_PRIMARY}; background: transparent;")
            self._indicator.setStyleSheet(f"background-color: {COLOR_PRIMARY};")
        else:
            self._label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; background: transparent;")
            self._indicator.setStyleSheet("background-color: transparent;")

    def mousePressEvent(self, event):
        self.clicked.emit(self._index)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if not self._active:
            self._label.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style()
        super().leaveEvent(event)


class SettingsPanel(QWidget):
    """settings panel organized in tabs: Gateway, Data, About."""

    save_requested = Signal(int)
    clear_all_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLOR_BG};")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header: title + tabs
        header = QWidget(self)
        header.setObjectName("settingsHeader")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.setStyleSheet(f"#settingsHeader {{ background-color: {COLOR_BG}; }}")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # title with padding
        title_wrapper = QWidget(header)
        title_wrapper.setStyleSheet("background: transparent;")
        tw_layout = QHBoxLayout(title_wrapper)
        tw_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("Settings", title_wrapper)
        title.setFont(QFont(FONT_SYSTEM, 14, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")
        tw_layout.addWidget(title)
        tw_layout.addStretch()

        close_btn = QPushButton("\u00d7", title_wrapper)
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFont(QFont(FONT_SYSTEM, 18))
        close_btn.setStyleSheet(
            f"QPushButton {{ background: none; color: {COLOR_TEXT_SECONDARY};"
            f" border: 1px solid {COLOR_BORDER}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {COLOR_HOVER}; color: {COLOR_TEXT}; }}"
        )
        close_btn.clicked.connect(self.close_requested.emit)
        tw_layout.addWidget(close_btn)

        h_layout.addWidget(title_wrapper)

        # tab bar edge-to-edge
        tab_bar = QWidget(header)
        tab_bar.setObjectName("settingsTabBar")
        tab_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tab_bar.setStyleSheet(
            f"#settingsTabBar {{ border-bottom: 1px solid {COLOR_BORDER}; background: transparent; }}"
        )
        tb_layout = QHBoxLayout(tab_bar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(0)

        self._tabs: list[_SettingsTab] = []
        for i, name in enumerate(("Gateway", "Data", "About")):
            tab = _SettingsTab(name, i, tab_bar)
            tab.clicked.connect(self._switch_tab)
            self._tabs.append(tab)
            tb_layout.addWidget(tab)
        tb_layout.addStretch()

        h_layout.addWidget(tab_bar)
        root.addWidget(header)

        # stacked pages
        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet("QStackedWidget { border: none; }")

        self._stack.addWidget(self._build_gateway_page())
        self._stack.addWidget(self._build_data_page())
        self._stack.addWidget(self._build_about_page())

        root.addWidget(self._stack)

        # activate first tab
        self._tabs[0].set_active(True)
        self._stack.setCurrentIndex(0)

    def _switch_tab(self, index: int):
        for i, tab in enumerate(self._tabs):
            tab.set_active(i == index)
        self._stack.setCurrentIndex(index)

    # -- gateway page --

    def _build_gateway_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background-color: {COLOR_BG};")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # scrollable content
        scroll = self._make_scroll()
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(40, 24, 40, 24)
        c_layout.setSpacing(16)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # port field
        port_label = QLabel("Port", content)
        port_label.setFont(QFont(FONT_SYSTEM, 13, QFont.Weight.Medium))
        port_label.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")
        c_layout.addWidget(port_label)

        port_desc = QLabel("The port the OpenClaw gateway will listen on.", content)
        port_desc.setFont(QFont(FONT_SYSTEM, 12))
        port_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")
        port_desc.setWordWrap(True)
        c_layout.addWidget(port_desc)

        self._port_input = QLineEdit(content)
        self._port_input.setText("18789")
        self._port_input.setFixedWidth(200)
        self._port_input.setFixedHeight(34)
        self._port_input.setFont(QFont(FONT_MONO, 13))
        self._port_input.setStyleSheet(
            f"QLineEdit {{"
            f"  background-color: white; color: {COLOR_TEXT};"
            f"  border: 1px solid {COLOR_BORDER};"
            f"  padding: 0 10px;"
            f"}}"
            f"QLineEdit:focus {{ border-color: {COLOR_PRIMARY}; }}"
        )
        self._port_input.textChanged.connect(self._validate_port)
        c_layout.addWidget(self._port_input)

        self._port_error = QLabel("", content)
        self._port_error.setFont(QFont(FONT_SYSTEM, 11))
        self._port_error.setStyleSheet(f"color: {COLOR_PRIMARY}; background: transparent;")
        self._port_error.hide()
        c_layout.addWidget(self._port_error)

        c_layout.addStretch()
        scroll.setWidget(content)
        page_layout.addWidget(scroll)

        # fixed footer with save button
        footer = self._make_footer()
        save_btn = QPushButton("Save", footer)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFont(QFont(FONT_SYSTEM, 12, QFont.Weight.Medium))
        save_btn.setStyleSheet(
            f"QPushButton {{"
            f"  padding: 6px 20px; background-color: {COLOR_PRIMARY};"
            f"  color: white; border: none;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {COLOR_PRIMARY_HOVER};"
            f"}}"
        )
        save_btn.clicked.connect(self._on_save)
        footer.layout().addWidget(save_btn)
        footer.layout().addStretch()
        page_layout.addWidget(footer)

        return page

    # -- data page --

    def _build_data_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background-color: {COLOR_BG};")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(40, 24, 40, 24)
        page_layout.setSpacing(16)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        data_desc = QLabel(
            "Stop the gateway, remove all installed versions, "
            "and delete all application data. This action cannot be undone.",
            page,
        )
        data_desc.setFont(QFont(FONT_SYSTEM, 12))
        data_desc.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")
        data_desc.setWordWrap(True)
        data_desc.setMaximumWidth(400)
        page_layout.addWidget(data_desc)

        clear_btn = QPushButton("Clear All Data", page)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setFont(QFont(FONT_SYSTEM, 12, QFont.Weight.Medium))
        clear_btn.setStyleSheet(
            f"QPushButton {{"
            f"  padding: 6px 14px; background: transparent;"
            f"  color: {COLOR_PRIMARY}; border: 1px solid {COLOR_PRIMARY};"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {COLOR_PRIMARY}; color: white;"
            f"}}"
        )
        clear_btn.clicked.connect(self.clear_all_requested.emit)
        page_layout.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        page_layout.addStretch()
        return page

    # -- about page --

    def _build_about_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background-color: {COLOR_BG};")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(40, 24, 40, 24)
        page_layout.setSpacing(16)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        about_row = QHBoxLayout()
        about_row.setSpacing(8)

        about_name = QLabel(APP_NAME, page)
        about_name.setFont(QFont(FONT_SYSTEM, 13))
        about_name.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; background: transparent;")
        about_row.addWidget(about_name)

        about_ver = QLabel(f"v{APP_VERSION}", page)
        about_ver.setFont(QFont(FONT_MONO, 12))
        about_ver.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")
        about_row.addWidget(about_ver)
        about_row.addStretch()

        page_layout.addLayout(about_row)
        page_layout.addStretch()
        return page

    # -- helpers --

    def _make_scroll(self) -> QScrollArea:
        """create a styled scroll area."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {COLOR_BG}; }}"
            "QScrollBar:vertical { background: transparent; width: 4px; }"
            "QScrollBar::handle:vertical {"
            "  background: rgba(0,0,0,0.08); border-radius: 2px; min-height: 20px;"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {"
            "  height: 0; background: none;"
            "}"
        )
        return scroll

    def _make_footer(self) -> QWidget:
        """create a fixed footer bar with top border."""
        footer = QWidget()
        footer.setObjectName("settingsFooter")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        footer.setStyleSheet(
            f"#settingsFooter {{  border-top: 1px solid {COLOR_BORDER_LIGHT};  background-color: {COLOR_BG};}}"
        )
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(40, 12, 40, 12)
        f_layout.setSpacing(8)
        return footer

    # -- public api --

    def set_port(self, port: int):
        """set the port input value."""
        self._port_input.setText(str(port))

    def get_port(self) -> int:
        """get the current port value, clamped to valid range."""
        try:
            port = int(self._port_input.text())
            return max(1024, min(65535, port))
        except ValueError:
            return 18789

    # -- private --

    def _validate_port(self):
        """validate port input and show error if invalid."""
        text = self._port_input.text().strip()
        try:
            port = int(text)
            if port < 1024 or port > 65535:
                self._port_error.setText("Port must be between 1024 and 65535")
                self._port_error.show()
                self._port_input.setStyleSheet(
                    f"QLineEdit {{"
                    f"  background-color: white; color: {COLOR_TEXT};"
                    f"  border: 1px solid {COLOR_PRIMARY};"
                    f"  padding: 0 10px;"
                    f"}}"
                )
            else:
                self._port_error.hide()
                self._port_input.setStyleSheet(
                    f"QLineEdit {{"
                    f"  background-color: white; color: {COLOR_TEXT};"
                    f"  border: 1px solid {COLOR_BORDER};"
                    f"  padding: 0 10px;"
                    f"}}"
                    f"QLineEdit:focus {{ border-color: {COLOR_PRIMARY}; }}"
                )
        except ValueError:
            if text:
                self._port_error.setText("Port must be a number")
                self._port_error.show()

    def _on_save(self):
        port = self.get_port()
        self._port_input.setText(str(port))
        self._port_error.hide()
        self.save_requested.emit(port)
