import platform
import re
import shutil
import threading

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pyeclaw.config import (
    APP_NAME,
    APP_VERSION,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    DATA_DIR,
    FONT_SYSTEM,
    OPENCLAW_CONFIG_DIR,
    TERM_BG,
    VERSIONS_DIR,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_WIDTH,
)
from pyeclaw.gui.confirm_dialog import ConfirmDialog
from pyeclaw.gui.gateway_log import GatewayLog
from pyeclaw.gui.loading_overlay import LoadingOverlay
from pyeclaw.gui.settings_panel import SettingsPanel
from pyeclaw.gui.sidebar import Sidebar
from pyeclaw.gui.splash_screen import SplashScreen
from pyeclaw.gui.terminal import Terminal
from pyeclaw.gui.toast import Toast
from pyeclaw.gui.version_modal import VersionModal
from pyeclaw.service.config_manager import ConfigManager
from pyeclaw.service.openclaw_runner import OpenClawRunner
from pyeclaw.service.version_manager import VersionManager

# regex to strip ansi escape sequences
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class TabButton(QWidget):
    """tab button with 2px bottom indicator."""

    clicked = Signal(str)

    def __init__(self, text: str, parent: QWidget):
        super().__init__(parent)
        self._active = False
        self._text = text
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 0)
        layout.setSpacing(0)

        self._label = QLabel(text, self)
        self._label.setFont(QFont(FONT_SYSTEM, 13, QFont.Weight.Medium))
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
        self.clicked.emit(self._text)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        if not self._active:
            self._label.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style()
        super().leaveEvent(event)


class MainWindow(QMainWindow):
    """main application window with sidebar, terminal, and settings."""

    TAB_TERMINAL = "Terminal"
    TAB_LOGS = "Logs"

    _clear_done = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # native titlebar with hidden inset on macos
        if platform.system() == "Darwin":
            self.setUnifiedTitleAndToolBarOnMac(True)

        self._config = ConfigManager()
        self._version_mgr = VersionManager(self)
        self._runner = OpenClawRunner(self)

        self._shell_started = False
        self._current_tab = self.TAB_TERMINAL
        self._active_version = ""
        self._showing_settings = False

        # per-version log buffers
        self._version_logs: dict[str, list[str]] = {}

        # cached releases for the version modal
        self._cached_releases: list = []

        # active version modal (for async release loading)
        self._open_modal: VersionModal | None = None

        self._build_ui()
        self._connect_signals()
        self._check_first_run()

    # ui

    def _build_ui(self):
        central = QWidget(self)
        central.setStyleSheet(f"background-color: {COLOR_BG};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # main body (sidebar + content)
        body = QWidget(central)
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._sidebar = Sidebar(body)
        body_layout.addWidget(self._sidebar)

        self._outer_stack = QStackedWidget(body)
        self._outer_stack.setStyleSheet("QStackedWidget { border: none; }")

        # page 0: splash
        self._splash = SplashScreen(self._outer_stack)
        self._outer_stack.addWidget(self._splash)

        # page 1: main content
        main_content = QWidget(self._outer_stack)
        mc_layout = QVBoxLayout(main_content)
        mc_layout.setContentsMargins(0, 0, 0, 0)
        mc_layout.setSpacing(0)

        # tab bar + version badge
        self._main_header = QWidget(main_content)
        self._main_header.setObjectName("mainHeader")
        self._main_header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._main_header.setStyleSheet(f"#mainHeader {{ background-color: {COLOR_BG}; }}")
        mh_layout = QHBoxLayout(self._main_header)
        mh_layout.setContentsMargins(0, 0, 16, 0)
        mh_layout.setSpacing(0)

        # tab bar
        tab_bar = QWidget(self._main_header)
        tab_bar.setObjectName("tabBar")
        tab_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tab_bar.setStyleSheet(f"#tabBar {{ background-color: {COLOR_BG}; border-bottom: 1px solid {COLOR_BORDER}; }}")
        tb_layout = QHBoxLayout(tab_bar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(0)

        self._tab_terminal = TabButton(self.TAB_TERMINAL, tab_bar)
        self._tab_logs = TabButton(self.TAB_LOGS, tab_bar)
        self._tab_terminal.set_active(True)
        self._tab_terminal.clicked.connect(self._on_tab_click)
        self._tab_logs.clicked.connect(self._on_tab_click)

        tb_layout.addWidget(self._tab_terminal)
        tb_layout.addWidget(self._tab_logs)
        tb_layout.addStretch()
        mh_layout.addWidget(tab_bar)

        # version badge (right-aligned, small)
        self._version_title = QLabel("", self._main_header)
        self._version_title.setFont(QFont(FONT_SYSTEM, 11, QFont.Weight.Medium))
        self._version_title.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; background: transparent;")
        mh_layout.addWidget(self._version_title)

        mc_layout.addWidget(self._main_header)

        # content stack (terminal, logs, settings)
        self._content_stack = QStackedWidget(main_content)
        self._content_stack.setStyleSheet("QStackedWidget { border: none; }")

        # terminal panel with placeholder
        self._term_container = QStackedWidget(self._content_stack)
        self._term_container.setStyleSheet("QStackedWidget { border: none; }")

        placeholder = QWidget(self._term_container)
        placeholder.setStyleSheet(f"background-color: {COLOR_BG};")
        ph_layout = QVBoxLayout(placeholder)
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_msg = QLabel("Install a version first to use the terminal.", placeholder)
        ph_msg.setFont(QFont(FONT_SYSTEM, 13))
        ph_msg.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")
        ph_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_layout.addWidget(ph_msg)
        self._term_container.addWidget(placeholder)

        # terminal page
        term_page = QWidget(self._term_container)
        term_page.setStyleSheet(f"background-color: {TERM_BG};")
        tp_layout = QVBoxLayout(term_page)
        tp_layout.setContentsMargins(6, 6, 8, 6)
        tp_layout.setSpacing(0)

        self._terminal = Terminal(term_page)
        self._terminal.setStyleSheet(f"background-color: {TERM_BG};")
        tp_layout.addWidget(self._terminal)
        self._term_container.addWidget(term_page)

        self._content_stack.addWidget(self._term_container)  # index 0: terminal

        # gateway logs panel
        self._gateway_log = GatewayLog(self._content_stack)
        self._content_stack.addWidget(self._gateway_log)  # index 1: logs

        # settings panel
        self._settings_panel = SettingsPanel(self._content_stack)
        self._content_stack.addWidget(self._settings_panel)  # index 2: settings

        mc_layout.addWidget(self._content_stack)
        self._outer_stack.addWidget(main_content)

        body_layout.addWidget(self._outer_stack)
        root.addWidget(body)

        # toast notification overlay
        self._toast = Toast(central)

        # loading overlay
        self._loading = LoadingOverlay(central)

    def _connect_signals(self):
        # splash
        self._splash.install_clicked.connect(self._on_splash_install)
        self._splash.retry_clicked.connect(self._version_mgr.fetch_releases)

        # version manager
        self._version_mgr.versions_loaded.connect(self._on_releases_loaded)
        self._version_mgr.install_progress.connect(self._on_install_progress)
        self._version_mgr.install_complete.connect(self._on_install_complete)
        self._version_mgr.install_failed.connect(self._on_install_failed)
        self._version_mgr.removal_complete.connect(self._on_removal_complete)

        # sidebar
        self._sidebar.play_requested.connect(self._start_version)
        self._sidebar.stop_requested.connect(self._stop_version)
        self._sidebar.remove_requested.connect(self._remove_version)
        self._sidebar.version_selected.connect(self._select_version)
        self._sidebar.add_version_requested.connect(self._show_version_modal)
        self._sidebar.settings_requested.connect(self._toggle_settings)

        # runner (gateway)
        self._runner.status_changed.connect(self._on_gateway_status)
        self._runner.output_received.connect(self._on_gateway_output)
        self._runner.control_url_found.connect(self._on_control_url)

        # settings panel
        self._settings_panel.save_requested.connect(self._on_save_settings)
        self._settings_panel.clear_all_requested.connect(self._on_clear_all)
        self._settings_panel.close_requested.connect(self._close_settings)

        self._clear_done.connect(self._clear_all_finish)

    # startup

    def _check_first_run(self):
        installed = self._version_mgr.installed_versions()
        if installed:
            self._enter_app()
        else:
            self._sidebar.hide()
            self._outer_stack.setCurrentIndex(0)
            self._version_mgr.fetch_releases()

    def _enter_app(self):
        self._sidebar.show()
        self._outer_stack.setCurrentIndex(1)

        # restore config
        cfg = self._config.read()
        port = cfg.get("gatewayPort", 18789)
        self._settings_panel.set_port(port)
        self._sidebar.update_port_display(port)

        # restore active version
        active = cfg.get("activeVersion", "")
        installed = self._version_mgr.installed_versions()
        tags = {v.tag for v in installed}
        if active and active in tags:
            self._active_version = active
        elif installed:
            self._active_version = installed[0].tag

        self._refresh_sidebar()
        self._update_panels()

        # defer terminal start to allow the widget to be fully laid out first
        QTimer.singleShot(100, self._start_terminal)

    def _refresh_sidebar(self):
        installed = self._version_mgr.installed_versions()
        self._sidebar.set_versions(installed, self._active_version)

    def _update_panels(self):
        """update version title and panel visibility."""
        if self._active_version:
            self._version_title.setText(self._active_version)

        self._sidebar.set_settings_active(self._showing_settings)
        self._main_header.setVisible(not self._showing_settings)

    # tabs

    def _on_tab_click(self, tab_name: str):
        if self._showing_settings:
            self._showing_settings = False

        if tab_name == self._current_tab and not self._showing_settings:
            return
        self._current_tab = tab_name

        if tab_name == self.TAB_TERMINAL:
            self._tab_terminal.set_active(True)
            self._tab_logs.set_active(False)
            self._content_stack.setCurrentIndex(0)
            if not self._shell_started:
                self._start_terminal()
            self._terminal.focus_display()
        else:
            self._tab_terminal.set_active(False)
            self._tab_logs.set_active(True)
            self._content_stack.setCurrentIndex(1)
            self._render_logs()

        self._update_panels()

    # settings toggle

    def _toggle_settings(self):
        if self._showing_settings:
            self._close_settings()
        else:
            self._showing_settings = True
            self._content_stack.setCurrentIndex(2)
            self._update_panels()

    def _close_settings(self):
        """close settings panel and return to previous tab."""
        if not self._showing_settings:
            return
        self._showing_settings = False
        if self._current_tab == self.TAB_TERMINAL:
            self._content_stack.setCurrentIndex(0)
        else:
            self._content_stack.setCurrentIndex(1)
        self._update_panels()

    # splash

    @Slot(str)
    def _on_splash_install(self, version: str):
        self._splash.show_progress("Downloading...")
        self._version_mgr.install(version)

    @Slot(list)
    def _on_releases_loaded(self, releases):
        self._cached_releases = releases

        # update splash if on welcome screen
        if self._outer_stack.currentIndex() == 0:
            if releases:
                stable = next((r for r in releases if not r.prerelease), None)
                if stable:
                    self._splash.set_latest_version(stable.tag)
                elif releases:
                    self._splash.set_latest_version(releases[0].tag)
            else:
                self._splash.show_retry()

        # update open version modal if any
        if self._open_modal is not None and self._open_modal.isVisible():
            try:
                installed_tags = self._version_mgr.installed_tags()
                for r in self._cached_releases:
                    r.installed = r.tag in installed_tags
                self._open_modal.set_releases(self._cached_releases)
            except RuntimeError:
                self._open_modal = None

    # version modal

    def _show_version_modal(self):
        modal = VersionModal(self)
        modal.install_requested.connect(self._install_version)
        self._open_modal = modal

        # always fetch fresh releases (modal shows loading spinner until done)
        self._version_mgr.fetch_releases()

        modal.exec()
        self._open_modal = None

    # install

    def _install_version(self, version: str):
        self._loading.show_loading(f"Installing {version}...")
        self._version_mgr.install(version)

    @Slot(str, str)
    def _on_install_progress(self, stage: str, message: str):
        if self._outer_stack.currentIndex() == 0:
            self._splash.show_progress(message)
        else:
            if stage in ("downloading", "installing"):
                self._loading.set_message(message)
            elif stage == "done":
                self._loading.hide_loading()
                self._toast.show_message(message)
            elif stage == "error":
                self._loading.hide_loading()
                self._toast.show_message(message, error=True)

    @Slot(str)
    def _on_install_complete(self, version: str):
        if self._outer_stack.currentIndex() == 0:
            self._active_version = version
            self._enter_app()
        else:
            self._loading.hide_loading()
            self._refresh_sidebar()

    @Slot(str, str)
    def _on_install_failed(self, version: str, error: str):
        if self._outer_stack.currentIndex() == 0:
            self._splash.show_error(f"Failed to install {version}: {error}")
        else:
            self._loading.hide_loading()
            self._toast.show_message(f"Failed to install {version}", error=True)

    # remove

    def _remove_version(self, version: str):
        confirmed = ConfirmDialog.ask(
            "Remove Version",
            f"Are you sure you want to remove {version}? This cannot be undone.",
            self,
        )
        if not confirmed:
            return

        self._loading.show_loading(f"Removing {version}...")
        if self._runner.running_version == version:
            self._runner.stop()
        self._version_logs.pop(version, None)
        if self._active_version == version:
            self._active_version = ""
        self._version_mgr.remove(version)

    @Slot(str)
    def _on_removal_complete(self, version: str):
        self._loading.hide_loading()
        try:
            self._refresh_sidebar()
            self._toast.show_message(f"Removed {version}")
            self._update_panels()
            if not self._active_version:
                self._restart_terminal_default()
        except Exception:
            self._toast.show_message(f"Failed to remove {version}", error=True)

    # version selection

    def _select_version(self, tag: str):
        # always close settings when clicking a version
        if self._showing_settings:
            self._close_settings()

        if tag == self._active_version:
            return

        confirmed = ConfirmDialog.ask(
            "Switch Version",
            f"Switch to {tag}? This will restart the terminal session.",
            self,
        )
        if not confirmed:
            return

        self._active_version = tag
        self._config.save({"activeVersion": tag})

        self._current_tab = self.TAB_TERMINAL
        self._tab_terminal.set_active(True)
        self._tab_logs.set_active(False)
        self._content_stack.setCurrentIndex(0)

        self._loading.show_loading(f"Switching to {tag}...")
        self._refresh_sidebar()
        self._render_logs()
        self._update_panels()

        # defer terminal restart so the loading overlay renders first
        QTimer.singleShot(50, lambda: self._finish_switch(tag))

    def _finish_switch(self, tag: str):
        """complete the version switch after the loading overlay is visible."""
        self._restart_terminal(tag)
        self._loading.hide_loading()
        self._toast.show_message(f"Switched to {tag}")

    # gateway

    def _start_version(self, tag: str):
        is_swapping = (
            self._runner.running_version
            and self._runner.running_version != tag
            and self._runner.status in ("running", "starting")
        )

        message = (
            f"This will stop {self._runner.running_version} and start {tag}."
            if is_swapping
            else f"Start the gateway with {tag}?"
        )

        confirmed = ConfirmDialog.ask("Start Gateway", message, self)
        if not confirmed:
            return

        self._version_logs[tag] = []

        try:
            if is_swapping:
                self._runner.stop()
            cfg = self._config.read()
            port = cfg.get("gatewayPort", 18789)
            self._runner.start(tag, port)
        except Exception:
            self._toast.show_message(f"Failed to start {tag}", error=True)

    def _stop_version(self, version: str):
        confirmed = ConfirmDialog.ask(
            "Stop Gateway",
            f"Stop the gateway running on {version}?",
            self,
        )
        if not confirmed:
            return
        try:
            self._runner.stop()
        except Exception:
            self._toast.show_message("Failed to stop gateway", error=True)

    @Slot(str, str)
    def _on_gateway_status(self, status: str, version: str):
        self._sidebar.set_gateway_state(status, version)
        self._refresh_sidebar()
        self._update_panels()

        if status == "running":
            self._toast.show_message(f"Gateway started ({version})")
        elif status == "error":
            self._toast.show_message("Gateway failed to start", error=True)

    @Slot(str)
    def _on_gateway_output(self, text: str):
        gw_version = self._runner.running_version
        if not gw_version:
            return

        cleaned = _ANSI_RE.sub("", text).strip()
        if not cleaned:
            return

        if gw_version not in self._version_logs:
            self._version_logs[gw_version] = []
        self._version_logs[gw_version].append(cleaned)

        if self._active_version == gw_version and self._current_tab == self.TAB_LOGS and not self._showing_settings:
            self._gateway_log.append_text(cleaned)

    @Slot(str)
    def _on_control_url(self, url: str):
        self._sidebar.set_dashboard_url(url)
        self._sidebar.set_auth_token(self._runner.get_auth_token())

    # logs

    def _render_logs(self):
        """render per-version logs for the active version."""
        self._gateway_log.clear()
        logs = self._version_logs.get(self._active_version, [])
        if not logs:
            self._gateway_log.show_empty()
            return
        for line in logs:
            self._gateway_log.append_text(line)

    # settings

    @Slot(int)
    def _on_save_settings(self, port: int):
        self._loading.show_loading("Saving settings...")
        try:
            self._config.save({"gatewayPort": port})
            self._sidebar.update_port_display(port)
            self._toast.show_message("Settings saved")
        except Exception:
            self._toast.show_message("Failed to save settings", error=True)
        finally:
            self._loading.hide_loading()

    @Slot()
    def _on_clear_all(self):
        confirmed = ConfirmDialog.ask(
            "Clear All Data",
            "This will stop the gateway, remove all installed versions, "
            "and delete all application data. This cannot be undone.",
            self,
        )
        if not confirmed:
            return

        self._loading.show_loading("Clearing all data...")
        self._runner.stop()
        self._terminal.stop()

        threading.Thread(target=self._clear_all_background, daemon=True).start()

    def _clear_all_background(self):
        """delete all data directories in background thread."""
        try:
            if DATA_DIR.exists():
                shutil.rmtree(DATA_DIR)
            if OPENCLAW_CONFIG_DIR.exists():
                shutil.rmtree(OPENCLAW_CONFIG_DIR)
        except Exception:
            pass

        # signal main thread to finish ui reset
        self._clear_done.emit()

    def _clear_all_finish(self):
        """reset ui state after data deletion (runs on main thread)."""
        self._version_logs.clear()
        self._active_version = ""
        self._shell_started = False
        self._showing_settings = False
        self._current_tab = self.TAB_TERMINAL
        self._cached_releases = []

        # reset ui to initial state
        self._tab_terminal.set_active(True)
        self._tab_logs.set_active(False)
        self._content_stack.setCurrentIndex(0)
        self._term_container.setCurrentIndex(0)
        self._main_header.setVisible(True)
        self._sidebar.set_settings_active(False)
        self._version_title.setText("")

        self._loading.hide_loading()

        self._sidebar.hide()
        self._splash.reset()
        self._outer_stack.setCurrentIndex(0)
        self._version_mgr.fetch_releases()

    # terminal

    def _start_terminal(self):
        """start terminal in the active version's context."""
        if not self._active_version:
            self._term_container.setCurrentIndex(0)
            return
        self._term_container.setCurrentIndex(1)
        # ensure bin wrapper exists so `openclaw` command works in terminal
        try:
            self._version_mgr.ensure_bin_wrapper(self._active_version)
        except Exception:
            pass  # nice-to-have, don't block terminal spawn
        env = self._runner.build_env(self._active_version)
        cwd = str(VERSIONS_DIR / self._active_version)
        self._terminal.start_shell(env, cwd)
        self._shell_started = True

    def _restart_terminal(self, version: str):
        """stop current terminal and start a new one for the given version."""
        self._terminal.stop()
        self._term_container.setCurrentIndex(1)
        try:
            self._version_mgr.ensure_bin_wrapper(version)
        except Exception:
            pass
        env = self._runner.build_env(version)
        cwd = str(VERSIONS_DIR / version)
        # small delay to let stop() background thread release resources
        QTimer.singleShot(50, lambda: self._spawn_shell(env, cwd))

    def _spawn_shell(self, env: dict[str, str], cwd: str):
        """spawn the shell after a brief delay."""
        self._terminal.start_shell(env, cwd)
        self._shell_started = True

    def _restart_terminal_default(self):
        """restart terminal for the current active version or show placeholder."""
        self._terminal.stop()
        if self._active_version:
            self._restart_terminal(self._active_version)
        else:
            installed = self._version_mgr.installed_versions()
            if installed:
                self._active_version = installed[0].tag
                self._config.save({"activeVersion": self._active_version})
                self._restart_terminal(self._active_version)
            else:
                self._term_container.setCurrentIndex(0)
                self._shell_started = False

    # cleanup

    def closeEvent(self, event):
        self._runner.force_kill()
        self._terminal.stop()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_toast"):
            self._toast._reposition()
        if hasattr(self, "_loading"):
            self._loading._reposition()
