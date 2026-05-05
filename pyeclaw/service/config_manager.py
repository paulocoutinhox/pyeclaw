import json

from pyeclaw.config import DATA_DIR, VERSIONS_DIR

CONFIG_FILE = DATA_DIR / "config.json"

DEFAULTS = {
    "gatewayPort": 18789,
    "activeVersion": "",
}


class ConfigManager:
    """manages pyeclaw application configuration persisted to disk."""

    def __init__(self):
        self._ensure_dirs()

    def read(self) -> dict:
        """read current config, falling back to defaults."""
        if not CONFIG_FILE.exists():
            return {**DEFAULTS}
        try:
            raw = json.loads(CONFIG_FILE.read_text())
            return {
                "gatewayPort": raw.get("gatewayPort") or DEFAULTS["gatewayPort"],
                "activeVersion": raw.get("activeVersion") or DEFAULTS["activeVersion"],
            }
        except (json.JSONDecodeError, OSError):
            return {**DEFAULTS}

    def save(self, partial: dict) -> None:
        """merge partial config into current and persist."""
        current = self.read()
        merged = {**current, **partial}
        CONFIG_FILE.write_text(json.dumps(merged, indent=2) + "\n")

    def _ensure_dirs(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
