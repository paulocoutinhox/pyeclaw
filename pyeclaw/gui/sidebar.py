import socket
import webbrowser
from urllib.parse import quote

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pyeclaw.config import (
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_HOVER,
    COLOR_ONLINE,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_LIGHT,
    COLOR_SURFACE,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
    FONT_MONO,
    FONT_SYSTEM,
    GATEWAY_HOST,
    GATEWAY_PORT,
    SIDEBAR_WIDTH,
)
from pyeclaw.gui.assets import Assets


class VersionItem(QWidget):
    """version list item with play/stop, remove buttons, size, and status text."""

    play_clicked = Signal(str)
    stop_clicked = Signal(str)
    remove_clicked = Signal(str)
    selected = Signal(str)

    def __init__(
        self,
        version: str,
        size: str,
        active: bool,
        is_gateway_target: bool,
        gateway_status: str,
        parent: QWidget,
    ):
        super().__init__(parent)
        self._version = version
        self._active = active
        self._is_gateway_target = is_gateway_target
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("versionItem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._apply_bg()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # version info column
        info = QVBoxLayout()
        info.setSpacing(1)

        tag_color = COLOR_PRIMARY if active else COLOR_TEXT
        tag = QLabel(version, self)
        tag.setFont(QFont(FONT_SYSTEM, 12, QFont.Weight.Medium))
        tag.setStyleSheet(f"color: {tag_color}; background: transparent;")
        info.addWidget(tag)

        # meta line: size + status
        is_running = is_gateway_target and gateway_status == "running"
        is_starting = is_gateway_target and gateway_status == "starting"
        status_text = " \u2014 running" if is_running else " \u2014 starting..." if is_starting else ""
        meta = QLabel(f"{size}{status_text}", self)
        meta.setFont(QFont(FONT_SYSTEM, 10))
        meta.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")
        info.addWidget(meta)

        layout.addLayout(info)
        layout.addStretch()

        # action buttons
        self._actions = QWidget(self)
        self._actions.setStyleSheet("background: transparent;")
        act_layout = QHBoxLayout(self._actions)
        act_layout.setContentsMargins(0, 0, 0, 0)
        act_layout.setSpacing(2)

        if is_gateway_target:
            stop = QPushButton("\u25a0", self._actions)
            stop.setFixedSize(24, 24)
            stop.setCursor(Qt.CursorShape.PointingHandCursor)
            stop.setToolTip("Stop")
            stop.setStyleSheet(
                f"QPushButton {{ background-color: {COLOR_PRIMARY_LIGHT}; color: {COLOR_PRIMARY};"
                f" border: none; border-radius: 12px; font-size: 10px; }}"
            )
            stop.clicked.connect(lambda: self.stop_clicked.emit(self._version))
            act_layout.addWidget(stop)
        else:
            play = QPushButton("\u25b6", self._actions)
            play.setFixedSize(24, 24)
            play.setCursor(Qt.CursorShape.PointingHandCursor)
            play.setToolTip("Start")
            play.setStyleSheet(
                f"QPushButton {{ background-color: {COLOR_PRIMARY}; color: white;"
                f" border: none; border-radius: 12px; font-size: 10px; }}"
                f"QPushButton:hover {{ background-color: {COLOR_PRIMARY_HOVER}; }}"
            )
            play.clicked.connect(lambda: self.play_clicked.emit(self._version))
            act_layout.addWidget(play)

            # remove button (only when not gateway target)
            rm = QPushButton("\u2715", self._actions)
            rm.setFixedSize(24, 24)
            rm.setCursor(Qt.CursorShape.PointingHandCursor)
            rm.setToolTip("Remove")
            rm.setStyleSheet(
                f"QPushButton {{ background: none; color: {COLOR_TEXT_SECONDARY};"
                f" border: none; border-radius: 4px; font-size: 11px; }}"
                f"QPushButton:hover {{ background-color: {COLOR_PRIMARY_LIGHT}; color: {COLOR_PRIMARY}; }}"
            )
            rm.clicked.connect(lambda: self.remove_clicked.emit(self._version))
            act_layout.addWidget(rm)

        # hide actions by default unless active or gateway target
        if not active and not is_gateway_target:
            self._actions.hide()

        layout.addWidget(self._actions)

    def mousePressEvent(self, event):
        # only emit selected if not clicking an action button
        child = self.childAt(event.pos())
        if child and isinstance(child, QPushButton):
            super().mousePressEvent(event)
            return
        self.selected.emit(self._version)
        super().mousePressEvent(event)

    def _apply_bg(self, hovered: bool = False):
        """apply background style based on active and hover state."""
        if self._active:
            bg = COLOR_PRIMARY_LIGHT
        elif hovered:
            bg = COLOR_HOVER
        else:
            bg = "transparent"
        self.setStyleSheet(f"#versionItem {{ background-color: {bg}; border-radius: 6px; }}")

    def enterEvent(self, event):
        if not self._active:
            self._apply_bg(hovered=True)
        self._actions.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_bg()
        if not self._active and not self._is_gateway_target:
            self._actions.hide()
        super().leaveEvent(event)


class Sidebar(QWidget):
    """sidebar with version list, system info, and gateway status."""

    play_requested = Signal(str)
    stop_requested = Signal(str)
    remove_requested = Signal(str)
    version_selected = Signal(str)
    add_version_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"#sidebar {{ background-color: {COLOR_SURFACE}; border-right: 1px solid {COLOR_BORDER}; }}")
        self._gateway_status = "stopped"
        self._gateway_version = ""
        self._dashboard_url = ""
        self._blink_visible = True
        self._build_ui()
        self._setup_blink_timer()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # header
        header = QHBoxLayout()
        header.setContentsMargins(16, 8, 16, 12)
        header.setSpacing(8)

        icon_label = QLabel(self)
        icon_label.setFixedSize(22, 22)
        icon_label.setStyleSheet("background: transparent;")
        pixmap = Assets.icon_pixmap(22)
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap)
        header.addWidget(icon_label)
        title = QLabel("PyeClaw", self)
        title.setFont(QFont(FONT_SYSTEM, 14, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # info section
        info_widget = QWidget(self)
        info_widget.setStyleSheet("background: transparent;")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(16, 0, 16, 12)
        info_layout.setSpacing(4)

        hostname = socket.gethostname()
        ip = self._local_ip()

        self._info_port_label = None
        for label, value in [("Host", hostname), ("IP", ip), ("Port", str(GATEWAY_PORT))]:
            row = QHBoxLayout()
            row.setSpacing(0)
            lbl = QLabel(label, info_widget)
            lbl.setFont(QFont(FONT_SYSTEM, 11))
            lbl.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")
            lbl.setFixedWidth(36)
            row.addWidget(lbl)
            val = QLabel(value, info_widget)
            val.setFont(QFont(FONT_MONO, 10))
            val.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; background: transparent;")
            row.addWidget(val)
            row.addStretch()
            info_layout.addLayout(row)
            if label == "Port":
                self._info_port_label = val

        layout.addWidget(info_widget)

        # separator
        sep1 = QWidget(self)
        sep1.setFixedHeight(1)
        sep1.setStyleSheet(f"background-color: {COLOR_BORDER_LIGHT};")
        layout.addWidget(sep1)

        # versions section header
        ver_header_w = QWidget(self)
        ver_header_w.setStyleSheet("background: transparent;")
        ver_header_layout = QHBoxLayout(ver_header_w)
        ver_header_layout.setContentsMargins(16, 12, 16, 8)
        ver_header_layout.setSpacing(0)

        ver_title = QLabel("Versions", ver_header_w)
        ver_title.setFont(QFont(FONT_SYSTEM, 11, QFont.Weight.DemiBold))
        ver_title.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent; letter-spacing: 0.5px;")
        ver_header_layout.addWidget(ver_title)
        ver_header_layout.addStretch()

        add_btn = QPushButton("+", ver_header_w)
        add_btn.setFixedSize(24, 24)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFont(QFont(FONT_SYSTEM, 16))
        add_btn.setStyleSheet(
            f"QPushButton {{ background: none; color: {COLOR_TEXT_SECONDARY};"
            f" border: 1px solid {COLOR_BORDER}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background-color: {COLOR_HOVER}; color: {COLOR_TEXT}; }}"
        )
        add_btn.clicked.connect(self.add_version_requested.emit)
        ver_header_layout.addWidget(add_btn)
        layout.addWidget(ver_header_w)

        # version list (scrollable, flex: 1)
        self._version_scroll = QScrollArea(self)
        self._version_scroll.setWidgetResizable(True)
        self._version_scroll.setStyleSheet(
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
        self._version_list = QWidget()
        self._version_list.setStyleSheet("background: transparent;")
        self._version_layout = QVBoxLayout(self._version_list)
        self._version_layout.setContentsMargins(12, 4, 12, 4)
        self._version_layout.setSpacing(4)
        self._version_layout.addStretch()
        self._version_scroll.setWidget(self._version_list)
        layout.addWidget(self._version_scroll)

        # settings nav
        nav_sep = QWidget(self)
        nav_sep.setFixedHeight(1)
        nav_sep.setStyleSheet(f"background-color: {COLOR_BORDER_LIGHT};")
        layout.addWidget(nav_sep)

        nav_w = QWidget(self)
        nav_w.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_w)
        nav_layout.setContentsMargins(12, 4, 12, 4)

        self._settings_btn = QPushButton("  Settings", self)
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.setFont(QFont(FONT_SYSTEM, 12, QFont.Weight.Medium))
        self._settings_btn.setStyleSheet(
            f"QPushButton {{ background: none; color: {COLOR_TEXT_SECONDARY};"
            f" border: none; border-radius: 6px; padding: 7px 8px;"
            f" text-align: left; }}"
            f"QPushButton:hover {{ background-color: {COLOR_HOVER}; color: {COLOR_TEXT}; }}"
        )
        self._settings_btn.clicked.connect(self.settings_requested.emit)
        nav_layout.addWidget(self._settings_btn)
        layout.addWidget(nav_w)

        # footer
        footer_sep = QWidget(self)
        footer_sep.setFixedHeight(1)
        footer_sep.setStyleSheet(f"background-color: {COLOR_BORDER_LIGHT};")
        layout.addWidget(footer_sep)

        footer = QWidget(self)
        footer.setStyleSheet("background: transparent;")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(16, 14, 16, 14)
        footer_layout.setSpacing(12)

        # open control panel button (hidden by default)
        self._open_control_btn = QPushButton("Open Control Panel", footer)
        self._open_control_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_control_btn.setFont(QFont(FONT_SYSTEM, 12, QFont.Weight.Medium))
        self._open_control_btn.setStyleSheet(
            f"QPushButton {{"
            f"  padding: 8px 12px; background-color: {COLOR_PRIMARY};"
            f"  color: white; border: none; border-radius: 6px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {COLOR_PRIMARY_HOVER};"
            f"}}"
        )
        self._open_control_btn.clicked.connect(self._open_dashboard)
        self._open_control_btn.hide()
        footer_layout.addWidget(self._open_control_btn)

        # gateway status row
        status_row = QHBoxLayout()
        status_row.setSpacing(6)

        self._status_dot = QWidget(footer)
        self._status_dot.setFixedSize(7, 7)
        self._status_dot.setStyleSheet(f"background-color: {COLOR_TEXT_MUTED}; border-radius: 3px;")
        status_row.addWidget(self._status_dot)

        self._status_text = QLabel("Gateway Offline", footer)
        self._status_text.setFont(QFont(FONT_SYSTEM, 12))
        self._status_text.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; background: transparent;")
        status_row.addWidget(self._status_text)
        status_row.addStretch()

        footer_layout.addLayout(status_row)
        layout.addWidget(footer)

    def _setup_blink_timer(self):
        """timer for blinking the status dot when gateway is starting."""
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(600)
        self._blink_timer.timeout.connect(self._blink_tick)

    def _blink_tick(self):
        self._blink_visible = not self._blink_visible
        if self._gateway_status == "starting":
            opacity = "1.0" if self._blink_visible else "0.3"
            self._status_dot.setStyleSheet(
                f"background-color: {COLOR_WARNING}; border-radius: 3px; opacity: {opacity};"
            )

    def set_versions(self, installed: list, active: str):
        """rebuild the version list from InstalledVersion objects."""
        while self._version_layout.count() > 1:
            item = self._version_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for v in installed:
            is_active = v.tag == active
            is_gateway_target = v.tag == self._gateway_version
            row = VersionItem(
                version=v.tag,
                size=v.size,
                active=is_active,
                is_gateway_target=is_gateway_target,
                gateway_status=self._gateway_status,
                parent=self._version_list,
            )
            row.play_clicked.connect(self.play_requested.emit)
            row.stop_clicked.connect(self.stop_requested.emit)
            row.remove_clicked.connect(self.remove_requested.emit)
            row.selected.connect(self.version_selected.emit)
            idx = self._version_layout.count() - 1
            self._version_layout.insertWidget(idx, row)

    def set_gateway_state(self, status: str, version: str):
        """update gateway status display with full state machine."""
        self._gateway_status = status
        self._gateway_version = version

        labels = {
            "stopped": "Gateway Offline",
            "starting": "Gateway Starting...",
            "running": "Gateway Running",
            "error": "Gateway Error",
        }
        self._status_text.setText(labels.get(status, "Gateway Offline"))

        if status == "running":
            self._blink_timer.stop()
            self._status_dot.setStyleSheet(f"background-color: {COLOR_ONLINE}; border-radius: 3px;")
            # green glow effect
            glow = QGraphicsDropShadowEffect(self._status_dot)
            glow.setBlurRadius(6)
            glow.setOffset(0, 0)
            glow.setColor(QColor(34, 197, 94, 102))
            self._status_dot.setGraphicsEffect(glow)
        elif status == "starting":
            self._blink_visible = True
            self._blink_timer.start()
            self._status_dot.setStyleSheet(f"background-color: {COLOR_WARNING}; border-radius: 3px;")
            self._status_dot.setGraphicsEffect(None)
        elif status == "error":
            self._blink_timer.stop()
            self._status_dot.setStyleSheet(f"background-color: {COLOR_PRIMARY}; border-radius: 3px;")
            self._status_dot.setGraphicsEffect(None)
        else:
            self._blink_timer.stop()
            self._status_dot.setStyleSheet(f"background-color: {COLOR_TEXT_MUTED}; border-radius: 3px;")
            self._status_dot.setGraphicsEffect(None)

        # hide control panel button on stop/error
        if status in ("stopped", "error"):
            self._dashboard_url = ""
            self._open_control_btn.hide()

    def set_dashboard_url(self, url: str):
        """set the control panel url and show the button."""
        self._dashboard_url = url
        self._open_control_btn.show()

    def update_port_display(self, port: int):
        """update the port display in the info section."""
        if self._info_port_label:
            self._info_port_label.setText(str(port))

    def set_settings_active(self, active: bool):
        """toggle the settings button active state."""
        if active:
            self._settings_btn.setStyleSheet(
                f"QPushButton {{ background-color: {COLOR_PRIMARY_LIGHT}; color: {COLOR_PRIMARY};"
                f" border: none; border-radius: 6px; padding: 7px 8px;"
                f" text-align: left; }}"
            )
        else:
            self._settings_btn.setStyleSheet(
                f"QPushButton {{ background: none; color: {COLOR_TEXT_SECONDARY};"
                f" border: none; border-radius: 6px; padding: 7px 8px;"
                f" text-align: left; }}"
                f"QPushButton:hover {{ background-color: {COLOR_HOVER}; color: {COLOR_TEXT}; }}"
            )

    def set_auth_token(self, token: str):
        """store auth token for control panel url."""
        self._auth_token = token

    @staticmethod
    def _local_ip() -> str:
        """get the local network ip address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _open_dashboard(self):
        base = self._dashboard_url or f"http://{GATEWAY_HOST}:{GATEWAY_PORT}"
        token = getattr(self, "_auth_token", "")
        url = f"{base}#token={quote(token)}" if token else base
        webbrowser.open(url)
