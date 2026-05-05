import errno
import os
import platform
import struct
import subprocess
import threading

import pyte
from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

from pyeclaw.config import (
    FONT_MONO,
    FONT_SIZE,
    TERM_256,
    TERM_BG,
    TERM_COLORS,
    TERM_COLS,
    TERM_CURSOR,
    TERM_ROWS,
    TERM_SELECTION,
    TERM_TEXT,
)

_IS_WINDOWS = platform.system() == "Windows"

if not _IS_WINDOWS:
    import fcntl
    import pty
    import select
    import termios


class TerminalDisplay(QTextEdit):
    """terminal display with keyboard capture and blinking cursor overlay."""

    _KEY_MAP = {
        Qt.Key.Key_Up: b"\x1b[A",
        Qt.Key.Key_Down: b"\x1b[B",
        Qt.Key.Key_Right: b"\x1b[C",
        Qt.Key.Key_Left: b"\x1b[D",
        Qt.Key.Key_Home: b"\x1b[H",
        Qt.Key.Key_End: b"\x1b[F",
        Qt.Key.Key_Tab: b"\t",
        Qt.Key.Key_Backtab: b"\x1b[Z",
        Qt.Key.Key_Backspace: b"\x7f",
        Qt.Key.Key_Delete: b"\x1b[3~",
        Qt.Key.Key_Escape: b"\x1b",
        Qt.Key.Key_PageUp: b"\x1b[5~",
        Qt.Key.Key_PageDown: b"\x1b[6~",
    }

    key_pressed = Signal(bytes)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setCursorWidth(0)
        self.setFont(QFont(FONT_MONO, FONT_SIZE))
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(
            f"QTextEdit {{"
            f"  background-color: {TERM_BG}; color: {TERM_TEXT};"
            f"  border: none; padding: 4px;"
            f"  selection-background-color: {TERM_SELECTION};"
            f"}}"
            f"QScrollBar:vertical {{"
            f"  background: {TERM_BG}; width: 8px;"
            f"}}"
            f"QScrollBar::handle:vertical {{"
            f"  background: rgba(255,255,255,0.12);"
            f"  min-height: 30px;"
            f"}}"
            f"QScrollBar::handle:vertical:hover {{"
            f"  background: rgba(255,255,255,0.22);"
            f"}}"
            f"QScrollBar::add-line:vertical,"
            f"QScrollBar::sub-line:vertical,"
            f"QScrollBar::add-page:vertical,"
            f"QScrollBar::sub-page:vertical {{"
            f"  height: 0; background: none;"
            f"}}"
        )
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # blinking cursor state
        self._cursor_rect: QRect | None = None
        self._cursor_on = True

        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(530)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_timer.start()

    def place_cursor(self, row: int, col: int, history_offset: int):
        """calculate and store the cursor rect from the document layout."""
        doc = self.document()
        if doc is None or doc.blockCount() == 0:
            self._cursor_rect = None
            return
        target_line = history_offset + row
        block = doc.findBlockByNumber(target_line)
        if not block.isValid():
            self._cursor_rect = None
            return
        pos = block.position() + min(col, max(block.length() - 1, 0))
        tc = self.textCursor()
        tc.setPosition(pos)
        self._cursor_rect = self.cursorRect(tc)
        self._cursor_on = True
        self.viewport().update()

    def _blink(self):
        self._cursor_on = not self._cursor_on
        if self._cursor_rect is not None:
            self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._cursor_on and self._cursor_rect is not None:
            p = QPainter(self.viewport())
            p.fillRect(
                self._cursor_rect.left(),
                self._cursor_rect.top(),
                2,
                self._cursor_rect.height(),
                QColor(TERM_CURSOR),
            )
            p.end()

    def keyPressEvent(self, event: QKeyEvent):
        data = self._key_to_bytes(event)
        if data:
            self.key_pressed.emit(data)

    @staticmethod
    def _key_to_bytes(event: QKeyEvent) -> bytes:
        """convert a Qt key event to terminal byte sequence."""
        key = event.key()
        mod = event.modifiers()

        if key == Qt.Key.Key_C and mod & Qt.KeyboardModifier.ControlModifier:
            return b"\x03"
        if key == Qt.Key.Key_D and mod & Qt.KeyboardModifier.ControlModifier:
            return b"\x04"
        if key == Qt.Key.Key_Z and mod & Qt.KeyboardModifier.ControlModifier:
            return b"\x1a"
        if key == Qt.Key.Key_L and mod & Qt.KeyboardModifier.ControlModifier:
            return b"\x0c"
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return b"\r"
        if key in TerminalDisplay._KEY_MAP:
            return TerminalDisplay._KEY_MAP[key]
        text = event.text()
        if text:
            return text.encode("utf-8")
        return b""

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.setFocus()


class Terminal(QWidget):
    """full terminal emulator with pyte VT100, blinking cursor, and proper scrollback."""

    @staticmethod
    def _pyte_color_to_qcolor(color, default: str) -> QColor:
        """convert pyte color attribute to QColor."""
        if color == "default" or color is None:
            return QColor(default)
        if isinstance(color, str) and color in TERM_COLORS:
            return QColor(TERM_COLORS[color])
        if isinstance(color, int):
            if 0 <= color < len(TERM_256):
                return QColor(TERM_256[color])
        return QColor(default)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._cols = TERM_COLS
        self._rows = TERM_ROWS
        self._screen = pyte.HistoryScreen(self._cols, self._rows, history=10000)
        self._stream = pyte.Stream(self._screen)
        self._screen.set_mode(pyte.modes.LNM)

        self._master_fd: int | None = None
        self._process: subprocess.Popen | None = None
        self._dirty = False
        self._prev_snapshot: str = ""
        self._lock = threading.Lock()

        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._render)
        self._timer.start(50)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._display = TerminalDisplay(self)
        self._display.key_pressed.connect(self._on_key)
        layout.addWidget(self._display)

    def start_shell(self, env: dict[str, str], cwd: str):
        """spawn an interactive shell."""
        self.stop()
        self._reset_screen()

        if _IS_WINDOWS:
            self._start_shell_windows(env, cwd)
        else:
            self._start_shell_unix(env, cwd)

    def _start_shell_unix(self, env: dict[str, str], cwd: str):
        """spawn shell using unix pty."""
        master_fd, slave_fd = pty.openpty()
        self._update_size()
        self._set_pty_size_unix(slave_fd)

        shell = self._resolve_shell()
        self._process = subprocess.Popen(
            [shell, "--login"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            env=env,
            close_fds=True,
            start_new_session=True,
        )
        os.close(slave_fd)
        self._master_fd = master_fd

        threading.Thread(target=self._read_pty_unix, daemon=True).start()

    def _start_shell_windows(self, env: dict[str, str], cwd: str):
        """spawn shell using windows subprocess pipes."""
        shell = self._resolve_shell()
        self._process = subprocess.Popen(
            [shell],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        threading.Thread(target=self._read_pipe_windows, daemon=True).start()

    def run_command(self, command: str, env: dict[str, str], cwd: str):
        """run a single command in a pty."""
        self.stop()
        self._reset_screen()

        if _IS_WINDOWS:
            self._process = subprocess.Popen(
                command,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            threading.Thread(target=self._read_pipe_windows, daemon=True).start()
        else:
            master_fd, slave_fd = pty.openpty()
            self._update_size()
            self._set_pty_size_unix(slave_fd)

            self._process = subprocess.Popen(
                command,
                shell=True,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=cwd,
                env=env,
                close_fds=True,
                start_new_session=True,
            )
            os.close(slave_fd)
            self._master_fd = master_fd
            threading.Thread(target=self._read_pty_unix, daemon=True).start()

    def stop(self):
        """terminate any running shell process (non-blocking)."""
        proc = self._process
        fd = self._master_fd
        self._process = None
        self._master_fd = None

        if proc is not None or fd is not None:
            threading.Thread(
                target=self._stop_background,
                args=(proc, fd),
                daemon=True,
            ).start()

    @staticmethod
    def _stop_background(proc: subprocess.Popen | None, fd: int | None):
        """background thread that terminates the process and closes the fd."""
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass

    def is_process_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def send_interrupt(self):
        if self._process is not None and self._process.poll() is None:
            if _IS_WINDOWS:
                self._process.terminate()
            else:
                self._process.send_signal(2)

    def focus_display(self):
        self._display.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_size()

    def _reset_screen(self):
        """reset the pyte screen and display."""
        self._screen = pyte.HistoryScreen(self._cols, self._rows, history=10000)
        self._stream = pyte.Stream(self._screen)
        self._screen.set_mode(pyte.modes.LNM)
        self._prev_snapshot = ""
        self._dirty = True

    def _resolve_shell(self) -> str:
        """resolve the shell binary for the current platform."""
        if _IS_WINDOWS:
            return os.environ.get("COMSPEC", "cmd.exe")
        for candidate in (os.environ.get("SHELL"), "/bin/zsh", "/bin/bash", "/bin/sh"):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "/bin/sh"

    def _update_size(self):
        """recalculate terminal columns and rows from widget dimensions."""
        viewport = self._display.viewport()
        if viewport is None:
            return
        vw = viewport.width()
        vh = viewport.height()
        if vw <= 0 or vh <= 0:
            return

        fm = self._display.fontMetrics()
        char_w = fm.horizontalAdvance("M")
        char_h = fm.height()
        if char_w <= 0 or char_h <= 0:
            return

        new_cols = max(40, vw // char_w)
        new_rows = max(10, vh // char_h)

        if new_cols == self._cols and new_rows == self._rows:
            return

        self._cols = new_cols
        self._rows = new_rows
        self._screen.resize(new_rows, new_cols)
        self._dirty = True

        # resize pty if running on unix
        if not _IS_WINDOWS and self._master_fd is not None:
            ws = struct.pack("HHHH", new_rows, new_cols, 0, 0)
            try:
                fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, ws)
            except OSError:
                pass

    def _set_pty_size_unix(self, slave_fd: int):
        ws = struct.pack("HHHH", self._rows, self._cols, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, ws)

    def _on_key(self, data: bytes):
        if _IS_WINDOWS:
            if self._process is not None and self._process.stdin is not None:
                try:
                    self._process.stdin.write(data)
                    self._process.stdin.flush()
                except OSError:
                    pass
        else:
            if self._master_fd is not None:
                try:
                    os.write(self._master_fd, data)
                except OSError:
                    pass

    # unix pty reader

    def _read_pty_unix(self):
        fd = self._master_fd
        while fd is not None:
            try:
                ready, _, _ = select.select([fd], [], [], 0.02)
            except (ValueError, OSError):
                break
            if ready:
                try:
                    data = os.read(fd, 8192)
                except OSError as e:
                    if e.errno == errno.EIO:
                        break
                    raise
                if not data:
                    break
                with self._lock:
                    self._stream.feed(data.decode("utf-8", errors="replace"))
                    self._dirty = True

            if self._process is not None and self._process.poll() is not None:
                self._drain_pty_unix(fd)
                break

        try:
            if fd is not None:
                os.close(fd)
        except OSError:
            pass
        self._master_fd = None
        self._process = None

    def _drain_pty_unix(self, fd: int):
        """drain remaining data from unix pty."""
        try:
            while True:
                r, _, _ = select.select([fd], [], [], 0.01)
                if not r:
                    break
                d = os.read(fd, 8192)
                if not d:
                    break
                with self._lock:
                    self._stream.feed(d.decode("utf-8", errors="replace"))
                    self._dirty = True
        except OSError:
            pass

    # windows pipe reader

    def _read_pipe_windows(self):
        proc = self._process
        if proc is None or proc.stdout is None:
            return
        while True:
            data = proc.stdout.read(4096)
            if not data:
                break
            with self._lock:
                self._stream.feed(data.decode("utf-8", errors="replace"))
                self._dirty = True
        self._process = None

    # renderer

    def _render(self):
        """render pyte screen with colors to the display widget."""
        with self._lock:
            if not self._dirty:
                return
            self._dirty = False

        cols = self._cols
        rows = self._rows

        # build a snapshot string to detect changes
        snapshot = self._build_snapshot(cols, rows)
        if snapshot == self._prev_snapshot:
            self._display.place_cursor(
                self._screen.cursor.y,
                self._screen.cursor.x,
                self._history_line_count(),
            )
            return
        self._prev_snapshot = snapshot

        self._display.setUpdatesEnabled(False)
        self._display.clear()

        cursor = self._display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        default_fmt = QTextCharFormat()
        default_fmt.setForeground(QColor(TERM_TEXT))
        default_fmt.setBackground(QColor(TERM_BG))

        history_lines = self._history_line_count()

        # render scrollback history (snapshot to avoid mutation from pty thread)
        if hasattr(self._screen, "history") and self._screen.history.top:
            for hist_line in list(self._screen.history.top):
                line_text = ""
                for col in range(cols):
                    if col in hist_line:
                        line_text += hist_line[col].data
                    else:
                        line_text += " "
                cursor.insertText(line_text.rstrip() + "\n", default_fmt)

        # render current screen with colors up to last row with content
        buffer = self._screen.buffer
        last_row = self._screen.cursor.y
        for row in range(rows - 1, last_row, -1):
            for col in range(cols):
                if buffer[row][col].data.strip():
                    last_row = row
                    break
            if last_row == row:
                break

        for row in range(last_row + 1):
            for col in range(cols):
                char = buffer[row][col]
                fmt = QTextCharFormat()

                fg = char.fg if char.fg != "default" else None
                bg = char.bg if char.bg != "default" else None

                if char.reverse:
                    fg, bg = bg, fg

                fg_color = self._pyte_color_to_qcolor(fg, TERM_TEXT)
                bg_color = self._pyte_color_to_qcolor(bg, TERM_BG)

                if char.bold:
                    fmt.setFontWeight(QFont.Weight.Bold)
                    if isinstance(char.fg, str) and char.fg in TERM_COLORS:
                        bright_key = f"bright{char.fg}"
                        if bright_key in TERM_COLORS:
                            fg_color = QColor(TERM_COLORS[bright_key])

                if char.italics:
                    fmt.setFontItalic(True)
                if char.underscore:
                    fmt.setFontUnderline(True)

                fmt.setForeground(fg_color)
                if bg is not None:
                    fmt.setBackground(bg_color)

                cursor.insertText(char.data, fmt)

            if row < last_row:
                cursor.insertText("\n", default_fmt)

        # scroll to bottom to keep latest output visible
        self._display.setTextCursor(cursor)
        sb = self._display.verticalScrollBar()
        sb.setValue(sb.maximum())
        self._display.setUpdatesEnabled(True)

        # position the native cursor
        self._display.place_cursor(
            self._screen.cursor.y,
            self._screen.cursor.x,
            history_lines,
        )

    def _history_line_count(self) -> int:
        """count the number of lines in scrollback history."""
        try:
            if hasattr(self._screen, "history") and self._screen.history.top:
                return len(self._screen.history.top)
        except RuntimeError:
            pass
        return 0

    def _build_snapshot(self, cols: int, rows: int) -> str:
        """build a text snapshot for change detection."""
        parts = []
        buffer = self._screen.buffer
        for row in range(rows):
            line = ""
            for col in range(cols):
                char = buffer[row][col]
                line += char.data
            parts.append(line)
        parts.append(f"{self._screen.cursor.y},{self._screen.cursor.x}")
        return "\n".join(parts)
