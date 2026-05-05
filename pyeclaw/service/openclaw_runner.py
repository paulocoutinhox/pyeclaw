import json
import os
import platform
import subprocess
import threading

from PySide6.QtCore import QObject, QTimer, Signal

from pyeclaw.config import GATEWAY_HOST, OPENCLAW_CONFIG_FILE, VERSIONS_DIR
from pyeclaw.service.version_manager import NODE_DIR, VersionManager

_IS_WINDOWS = platform.system() == "Windows"

if not _IS_WINDOWS:
    import signal


class OpenClawRunner(QObject):
    """manages the openclaw gateway process lifecycle.

    uses a status state machine
    (stopped -> starting -> running | error) and generation counter
    to prevent race conditions between background threads.
    """

    # status: "stopped" | "starting" | "running" | "error"
    status_changed = Signal(str, str)  # (status, version)
    output_received = Signal(str)
    control_url_found = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._process: subprocess.Popen | None = None
        self._status = "stopped"
        self._active_version = ""
        self._control_url = ""
        self._generation = 0
        self._exited = False

    @property
    def status(self) -> str:
        return self._status

    @property
    def running_version(self) -> str:
        return self._active_version if self._status in ("starting", "running") else ""

    @property
    def control_url(self) -> str:
        return self._control_url

    def get_auth_token(self) -> str:
        """read the gateway auth token from openclaw config."""
        try:
            raw = json.loads(OPENCLAW_CONFIG_FILE.read_text())
            return raw.get("gateway", {}).get("auth", {}).get("token", "")
        except (json.JSONDecodeError, OSError):
            return ""

    def _get_node_bin(self) -> str:
        """return path to the bundled node binary."""
        return str(NODE_DIR / "bin" / "node")

    def _get_bin_path(self, tag: str) -> str:
        """find the openclaw entry point for a version."""
        version_dir = VERSIONS_DIR / tag
        candidates = [
            version_dir / "openclaw.mjs",
            version_dir / "node_modules" / ".bin" / "openclaw",
            version_dir / "dist" / "cli.js",
            version_dir / "bin" / "openclaw",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return str(candidates[0])

    def build_env(self, version: str) -> dict[str, str]:
        """build environment with bundled node and openclaw for a specific version."""
        version_dir = VERSIONS_DIR / version
        node_bin_dir = str(NODE_DIR / "bin")
        version_bin_dir = str(version_dir / "node_modules" / ".bin")
        openclaw_bin_dir = str(version_dir / "bin")
        sep = ";" if platform.system() == "Windows" else ":"
        path = f"{openclaw_bin_dir}{sep}{version_bin_dir}{sep}{node_bin_dir}{sep}{os.environ.get('PATH', '')}"
        return {
            **os.environ,
            "PATH": path,
            "NODE_ENV": "production",
            "TERM": "xterm-256color",
            "SHELL_SESSIONS_DISABLE": "1",
        }

    def start(self, version: str, port: int = 18789):
        """start the openclaw gateway for a specific version (non-blocking)."""
        if self._process is not None:
            return

        self._exited = False
        self._active_version = version
        self._control_url = ""
        self._generation += 1
        gen = self._generation
        self._set_status("starting")

        # startup timeout must be created on the main thread
        QTimer.singleShot(3000, lambda: self._startup_timeout(gen))

        threading.Thread(
            target=self._start_background,
            args=(version, port, gen),
            daemon=True,
        ).start()

    def _start_background(self, version: str, port: int, gen: int):
        """background thread that prepares runtime and spawns the gateway process."""
        if self._generation != gen:
            return

        version_dir = VERSIONS_DIR / version
        if not version_dir.exists():
            self.output_received.emit(f"version {version} not installed\n")
            self._set_status("error")
            return

        # ensure node runtime is available
        try:
            vm = VersionManager()
            vm._ensure_node_runtime(version)
        except Exception as e:
            self.output_received.emit(f"Failed to prepare runtime: {e}\n")
            self._set_status("error")
            return

        if self._generation != gen:
            return

        # determine command: use bundled node for .mjs/.js entry points
        bin_path = self._get_bin_path(version)
        node_bin = self._get_node_bin()
        use_node = bin_path.endswith((".mjs", ".js"))

        if use_node:
            command = [node_bin, bin_path, "gateway"]
        else:
            command = [bin_path, "gateway"]

        command += ["--port", str(port), "--allow-unconfigured", "--verbose"]

        env = self.build_env(version)

        self._process = subprocess.Popen(
            command,
            cwd=str(version_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )

        threading.Thread(
            target=self._stream_stdout,
            args=(self._process.stdout, gen, port),
            daemon=True,
        ).start()
        threading.Thread(
            target=self._stream_stderr,
            args=(self._process.stderr, gen, port),
            daemon=True,
        ).start()
        threading.Thread(
            target=self._watch,
            args=(gen,),
            daemon=True,
        ).start()

    def stop(self):
        """stop the running gateway (non-blocking)."""
        if self._process is None:
            return

        # invalidate watcher threads before terminating
        self._generation += 1
        proc = self._process
        pid = proc.pid
        self._process = None
        self._active_version = ""
        self._control_url = ""
        self._set_status("stopped")

        # terminate in background to avoid blocking the ui
        threading.Thread(
            target=self._stop_background,
            args=(proc, pid),
            daemon=True,
        ).start()

    def _stop_background(self, proc: subprocess.Popen, pid: int | None):
        """background thread that waits for the process to terminate."""
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self._kill_process(proc, pid)

    def force_kill(self):
        """force kill on app exit (blocking, only called during shutdown)."""
        if self._process is not None:
            self._kill_process(self._process, self._process.pid)
            self._process = None

    @staticmethod
    def _kill_process(proc: subprocess.Popen, pid: int | None):
        """force kill a process using platform-appropriate method."""
        if pid:
            if _IS_WINDOWS:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                    )
                except OSError:
                    pass
            else:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except OSError:
                    pass
        try:
            proc.kill()
        except OSError:
            pass

    def _startup_timeout(self, generation: int):
        """called 3s after start; if still starting, assume running."""
        if self._generation != generation:
            return
        if self._status == "starting" and not self._exited:
            self._set_status("running")

    def _stream_stdout(self, stream, generation: int, port: int):
        """read stdout, detect gateway ready, emit output."""
        for line in stream:
            if self._generation != generation:
                return
            self.output_received.emit(line)
            self._parse_log(line, port)
            lower = line.lower()
            if "listening" in lower or "ready" in lower:
                if self._status == "starting":
                    self._set_status("running")

    def _stream_stderr(self, stream, generation: int, port: int):
        """read stderr, detect gateway ready, emit output."""
        for line in stream:
            if self._generation != generation:
                return
            stripped = line.strip()
            if stripped:
                self.output_received.emit(stripped)
                self._parse_log(stripped, port)

    def _parse_log(self, output: str, port: int):
        """capture gateway control ui url."""
        if not self._control_url:
            lower = output.lower()
            if "listening" in lower or "ready" in lower:
                self._control_url = f"http://{GATEWAY_HOST}:{port}"
                self.control_url_found.emit(self._control_url)

    def _watch(self, generation: int):
        """monitor process exit, guarded by generation counter."""
        if self._process is not None:
            self._process.wait()
            self._exited = True
            if self._generation == generation:
                self._process = None
                if self._status == "starting":
                    self._set_status("error")
                else:
                    self._active_version = ""
                    self._set_status("stopped")

    def _set_status(self, status: str):
        self._status = status
        self.status_changed.emit(status, self._active_version)
