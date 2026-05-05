import json
import os
import platform
import shutil
import subprocess
import tarfile
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from pyeclaw.config import VERSIONS_DIR
from pyeclaw.service.config_manager import ConfigManager
from pyeclaw.service.http import HttpClient

_IS_WINDOWS = platform.system() == "Windows"

GITHUB_API = "https://api.github.com/repos/openclaw/openclaw/releases"
READY_MARKER = ".pyeclaw-ready"
NODE_VERSION = "22.16.0"
NODE_DIR = VERSIONS_DIR / "_node"


@dataclass
class InstalledVersion:
    """metadata for a locally installed version."""

    tag: str
    path: str
    size: str


@dataclass
class RemoteRelease:
    """metadata for a remote github release."""

    tag: str
    name: str
    published_at: str
    prerelease: bool
    installed: bool


class VersionManager(QObject):
    """manages openclaw version downloads, installs, and removals.

    downloads node.js runtime,
    fetches source tarball from github, extracts, installs deps,
    builds, creates bin wrapper, and marks ready.
    """

    @staticmethod
    def _get_node_platform_info() -> tuple[str, str, str]:
        """return (platform, arch, extension) for node.js download url."""
        system = platform.system().lower()
        machine = platform.machine().lower()

        plat = "darwin" if system == "darwin" else "linux" if system == "linux" else "win"
        arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
        ext = "zip" if plat == "win" else "tar.gz"

        return plat, arch, ext

    # signals
    versions_loaded = Signal(list)
    install_progress = Signal(str, str)  # (stage, message)
    install_complete = Signal(str)
    install_failed = Signal(str, str)
    removal_complete = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

    def installed_versions(self) -> list[InstalledVersion]:
        """list locally installed version directories with cached size."""
        if not VERSIONS_DIR.exists():
            return []
        versions = []
        for d in sorted(VERSIONS_DIR.iterdir(), reverse=True):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            marker = d / READY_MARKER
            if not marker.exists():
                continue
            size = self._read_cached_size(d)
            versions.append(
                InstalledVersion(
                    tag=d.name,
                    path=str(d),
                    size=self._format_size(size),
                )
            )
        return versions

    def installed_tags(self) -> set[str]:
        """return set of installed version tags (lightweight, no size calculation)."""
        if not VERSIONS_DIR.exists():
            return set()
        tags = set()
        for d in VERSIONS_DIR.iterdir():
            if d.is_dir() and not d.name.startswith("_") and (d / READY_MARKER).exists():
                tags.add(d.name)
        return tags

    def active_version(self) -> str:
        """get the currently selected active version from config."""
        config = ConfigManager()
        cfg = config.read()
        v = cfg.get("activeVersion", "")
        if v and (VERSIONS_DIR / v / READY_MARKER).exists():
            return v
        installed = self.installed_versions()
        return installed[0].tag if installed else ""

    def set_active_version(self, version: str):
        """set the active version in config."""
        config = ConfigManager()
        config.save({"activeVersion": version})

    def version_dir(self, version: str) -> Path:
        """get the directory for a specific version."""
        return VERSIONS_DIR / version

    def get_node_bin(self) -> Path:
        """return path to the bundled node binary."""
        if _IS_WINDOWS:
            return NODE_DIR / "node.exe"
        return NODE_DIR / "bin" / "node"

    def get_bin_path(self, tag: str) -> Path:
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
                return c
        return candidates[0]

    def ensure_bin_wrapper(self, tag: str):
        """ensure the bin/openclaw wrapper exists for a version (idempotent)."""
        self._create_bin_wrapper(tag)

    def fetch_releases(self, count: int = 10):
        """fetch latest releases from github in a background thread."""
        threading.Thread(
            target=self._fetch_releases,
            args=(count,),
            daemon=True,
        ).start()

    def install(self, version: str):
        """install a specific openclaw version in a background thread."""
        threading.Thread(
            target=self._install,
            args=(version,),
            daemon=True,
        ).start()

    def remove(self, version: str):
        """remove an installed version in a background thread."""
        threading.Thread(
            target=self._remove,
            args=(version,),
            daemon=True,
        ).start()

    def _remove(self, version: str):
        """remove an installed version from disk."""
        version_path = VERSIONS_DIR / version
        if version_path.exists():
            shutil.rmtree(version_path)
        if self.active_version() == version:
            self.set_active_version("")
        self.removal_complete.emit(version)

    def _fetch_releases(self, count: int):
        """fetch releases from github api."""
        try:
            url = f"{GITHUB_API}?per_page={count}"
            raw = HttpClient.get_json(
                url,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "PyeClaw",
                },
            )
            data = json.loads(raw.decode())

            installed = self.installed_tags()
            releases = []
            for r in data:
                tag = r.get("tag_name", "")
                releases.append(
                    RemoteRelease(
                        tag=tag,
                        name=r.get("name") or tag,
                        published_at=r.get("published_at", ""),
                        prerelease=bool(r.get("prerelease")),
                        installed=tag in installed,
                    )
                )
            self.versions_loaded.emit(releases)
        except Exception:
            self.versions_loaded.emit([])

    def _install(self, version: str):
        """install openclaw from github source tarball."""
        version_path = VERSIONS_DIR / version

        # skip if already installed
        if version_path.exists() and (version_path / READY_MARKER).exists():
            self.install_complete.emit(version)
            return

        # clean partial install
        if version_path.exists():
            shutil.rmtree(version_path)

        version_path.mkdir(parents=True, exist_ok=True)

        try:
            # step 0: ensure bundled node.js runtime
            self._ensure_node_runtime(version)

            # step 1: download and extract source tarball
            tar_url = f"https://github.com/openclaw/openclaw/archive/refs/tags/{version}.tar.gz"
            self.install_progress.emit("downloading", f"Downloading {version}...")
            self._download_and_extract(tar_url, version_path)

            # step 2: detect package manager and install dependencies
            pm = self._detect_package_manager(version_path)
            node_bin_dir = str(self.get_node_bin().parent)
            npm_bin = str(Path(node_bin_dir) / "npm")
            env = self._build_node_env()

            # ensure package manager is installed globally if needed
            if pm == "pnpm":
                self.install_progress.emit("installing", "Setting up pnpm...")
                self._ensure_pnpm()
            elif pm == "yarn":
                self.install_progress.emit("installing", "Setting up yarn...")
                self._ensure_yarn()

            pm_bin = str(Path(node_bin_dir) / pm)

            self.install_progress.emit("installing", f"Installing dependencies with {pm}...")

            if pm == "npm":
                self._exec([npm_bin, "install", "--production=false"], version_path, env)
            else:
                self._exec([pm_bin, "install"], version_path, env)

            # step 3: build
            self.install_progress.emit("installing", "Building...")
            if pm == "npm":
                self._exec([npm_bin, "run", "build"], version_path, env)
            else:
                self._exec([pm_bin, "run", "build"], version_path, env)

            # step 4: build control ui (optional)
            self.install_progress.emit("installing", "Building Control UI...")
            try:
                if pm == "npm":
                    self._exec([npm_bin, "run", "ui:install"], version_path, env)
                    self._exec([npm_bin, "run", "ui:build"], version_path, env)
                else:
                    self._exec([pm_bin, "run", "ui:install"], version_path, env)
                    self._exec([pm_bin, "run", "ui:build"], version_path, env)
            except RuntimeError:
                pass  # control ui is optional

            # step 5: create bin wrapper
            self._create_bin_wrapper(version)

            # mark as ready and cache directory size
            (version_path / READY_MARKER).write_text(version)
            size = self._get_dir_size(version_path)
            (version_path / ".pyeclaw-size").write_text(str(size))

            self.set_active_version(version)
            self.install_progress.emit("done", f"Version {version} installed successfully")
            self.install_complete.emit(version)

        except Exception as e:
            shutil.rmtree(version_path, ignore_errors=True)
            msg = str(e)
            self.install_progress.emit("error", f"Failed to install {version}: {msg}")
            self.install_failed.emit(version, msg)

    def _ensure_node_runtime(self, tag: str):
        """download and install node.js runtime if not already present."""
        node_bin = self.get_node_bin()

        if not node_bin.exists():
            self.install_progress.emit("downloading", f"Downloading Node.js {NODE_VERSION} runtime...")
            NODE_DIR.mkdir(parents=True, exist_ok=True)

            plat, arch, ext = self._get_node_platform_info()
            url = f"https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}-{plat}-{arch}.{ext}"

            archive_file = NODE_DIR / f"_node.{ext}"
            self._download_file(url, archive_file)

            if ext == "zip":
                self._extract_zip(archive_file, NODE_DIR)
            else:
                self._extract_tar_gz(archive_file, NODE_DIR)
            archive_file.unlink(missing_ok=True)

        # ensure npm/npx wrappers exist
        self._create_node_wrappers()

    def _ensure_pnpm(self):
        """install pnpm globally into the bundled node prefix (idempotent)."""
        pnpm_bin = NODE_DIR / "bin" / "pnpm"
        if pnpm_bin.exists():
            return
        npm_bin = str(NODE_DIR / "bin" / "npm")
        env = self._build_node_env()
        self._exec(
            [npm_bin, "install", "-g", "pnpm"],
            NODE_DIR,
            env,
        )

    def _ensure_yarn(self):
        """install yarn globally into the bundled node prefix (idempotent)."""
        yarn_bin = NODE_DIR / "bin" / "yarn"
        if yarn_bin.exists():
            return
        npm_bin = str(NODE_DIR / "bin" / "npm")
        env = self._build_node_env()
        self._exec(
            [npm_bin, "install", "-g", "yarn"],
            NODE_DIR,
            env,
        )

    def _create_node_wrappers(self):
        """create npm and npx wrapper scripts."""
        if _IS_WINDOWS:
            # on windows, npm.cmd ships with the node distribution
            return

        bin_dir = NODE_DIR / "bin"
        node_bin = bin_dir / "node"
        npm_cli = NODE_DIR / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js"
        npx_cli = NODE_DIR / "lib" / "node_modules" / "npm" / "bin" / "npx-cli.js"

        for cli, name in [(npm_cli, "npm"), (npx_cli, "npx")]:
            wrapper = bin_dir / name
            if not wrapper.exists() and cli.exists():
                wrapper.write_text(f'#!/bin/sh\nexec "{node_bin}" "{cli}" "$@"\n')
                wrapper.chmod(0o755)

    def _create_bin_wrapper(self, tag: str):
        """create bin/openclaw wrapper so the command is available in the terminal."""
        version_dir = VERSIONS_DIR / tag
        bin_dir = version_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)

        entry_point = self.get_bin_path(tag)
        node_bin = self.get_node_bin()
        is_js = str(entry_point).endswith((".mjs", ".js"))

        rel_entry = os.path.relpath(entry_point, bin_dir)
        rel_node = os.path.relpath(node_bin, bin_dir)

        if _IS_WINDOWS:
            # create .cmd wrapper for windows
            if is_js:
                content = f'@echo off\r\n"%~dp0{rel_node}" "%~dp0{rel_entry}" %*\r\n'
            else:
                content = f'@echo off\r\n"%~dp0{rel_entry}" %*\r\n'
            wrapper = bin_dir / "openclaw.cmd"
            wrapper.write_text(content)
        else:
            if is_js:
                content = (
                    "#!/bin/sh\n"
                    'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
                    f'exec "$SCRIPT_DIR/{rel_node}" "$SCRIPT_DIR/{rel_entry}" "$@"\n'
                )
            else:
                content = (
                    f'#!/bin/sh\nSCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"\nexec "$SCRIPT_DIR/{rel_entry}" "$@"\n'
                )
            wrapper = bin_dir / "openclaw"
            wrapper.write_text(content)
            wrapper.chmod(0o755)

    def _detect_package_manager(self, version_dir: Path) -> str:
        """detect package manager from lockfiles or packageManager field."""
        if (version_dir / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (version_dir / "yarn.lock").exists():
            return "yarn"
        pkg_file = version_dir / "package.json"
        if pkg_file.exists():
            try:
                pkg = json.loads(pkg_file.read_text())
                pm_field = pkg.get("packageManager", "")
                if isinstance(pm_field, str):
                    name = pm_field.split("@")[0]
                    if name in ("pnpm", "yarn"):
                        return name
            except (json.JSONDecodeError, OSError):
                pass
        return "npm"

    def _download_and_extract(self, url: str, dest: Path):
        """download tarball and extract, stripping the top-level directory."""
        tar_file = dest / "_download.tar.gz"
        self._download_file(url, tar_file)

        self.install_progress.emit("installing", "Extracting...")
        self._extract_tar_gz(tar_file, dest)

        tar_file.unlink(missing_ok=True)

    def _download_file(self, url: str, dest: Path):
        """download a file to disk."""
        HttpClient.download(url, dest)

    def _extract_tar_gz(self, tar_path: Path, dest: Path):
        """extract a .tar.gz file, stripping the first path component."""
        with tarfile.open(tar_path, "r:gz") as tf:
            for member in tf.getmembers():
                # strip first path component (e.g. openclaw-v2026.3.13/)
                parts = member.name.split("/", 1)
                if len(parts) < 2 or not parts[1]:
                    continue
                member.name = parts[1]

                # resolve the target path safely
                target = dest / member.name
                if not str(target.resolve()).startswith(str(dest.resolve())):
                    continue

                tf.extract(member, dest)

                # preserve executable bit
                if member.isfile() and member.mode & 0o111:
                    target.chmod(0o755)

    def _extract_zip(self, zip_path: Path, dest: Path):
        """extract a .zip file, stripping the first path component."""
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                parts = info.filename.split("/", 1)
                if len(parts) < 2 or not parts[1]:
                    continue
                info.filename = parts[1]

                target = dest / info.filename
                if not str(target.resolve()).startswith(str(dest.resolve())):
                    continue

                zf.extract(info, dest)

    def _build_node_env(self) -> dict[str, str]:
        """build environment with bundled node in PATH."""
        node_bin_dir = str(self.get_node_bin().parent)
        sep = ";" if platform.system() == "Windows" else ":"
        return {
            **os.environ,
            "PATH": f"{node_bin_dir}{sep}{os.environ.get('PATH', '')}",
            "SHELL_SESSIONS_DISABLE": "1",
        }

    def _exec(self, cmd: list[str], cwd: Path, env: dict[str, str]):
        """run a command, raising on failure."""
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            error = result.stderr.strip()[:300] if result.stderr else "command failed"
            raise RuntimeError(f"{cmd[0].split('/')[-1]} {cmd[1] if len(cmd) > 1 else ''} failed: {error}")

    def _read_cached_size(self, version_dir: Path) -> int:
        """read cached size from .pyeclaw-size file, or calculate and cache it."""
        size_file = version_dir / ".pyeclaw-size"
        if size_file.exists():
            try:
                return int(size_file.read_text().strip())
            except (ValueError, OSError):
                pass
        # calculate and cache for next time (runs once per version)
        size = self._get_dir_size(version_dir)
        try:
            size_file.write_text(str(size))
        except OSError:
            pass
        return size

    def _get_dir_size(self, path: Path) -> int:
        """calculate total size of a directory recursively."""
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except OSError:
            pass
        return total

    def _format_size(self, size: int) -> str:
        """format bytes to human-readable string."""
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.1f} GB"
