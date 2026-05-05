import sys
from pathlib import Path

APP_NAME = "PyeClaw"
APP_VERSION = "1.0.0"

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 18789

# pyeclaw data directory
DATA_DIR = Path.home() / ".pyeclaw"
VERSIONS_DIR = DATA_DIR / "versions"

# openclaw config
OPENCLAW_CONFIG_DIR = Path.home() / ".openclaw"
OPENCLAW_CONFIG_FILE = OPENCLAW_CONFIG_DIR / "openclaw.json"

# resolve base directory for pyinstaller bundle
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

# window
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 750
WINDOW_MIN_WIDTH = 700
WINDOW_MIN_HEIGHT = 500

# sidebar
SIDEBAR_WIDTH = 240

# brand colors
COLOR_PRIMARY = "#E84057"
COLOR_PRIMARY_HOVER = "#D63649"
COLOR_PRIMARY_LIGHT = "#FEF2F2"

# chrome
COLOR_BG = "#FFFFFF"
COLOR_SURFACE = "#FAFBFC"
COLOR_BORDER = "#E5E7EB"
COLOR_BORDER_LIGHT = "#F0F0F0"
COLOR_HOVER = "#F3F4F6"
COLOR_TEXT = "#1F2937"
COLOR_TEXT_SECONDARY = "#6B7280"
COLOR_TEXT_MUTED = "#9CA3AF"

# status
COLOR_ONLINE = "#22C55E"
COLOR_ONLINE_LIGHT = "#F0FDF4"
COLOR_WARNING = "#EAB308"
COLOR_WARNING_LIGHT = "#FEFCE8"
COLOR_OFFLINE = "#9CA3AF"
COLOR_DANGER = "#EF4444"
COLOR_DANGER_HOVER = "#DC2626"

# terminal dark theme
TERM_BG = "#1A1D2E"
TERM_TEXT = "#E0E4F0"
TERM_CURSOR = "#E84057"
TERM_DIM = "#8B949E"
TERM_SELECTION = "#3A3F55"
TERM_COLS = 120
TERM_ROWS = 40

# standard 16 terminal colors
TERM_COLORS = {
    "black": "#3A3F55",
    "red": "#FF6B6B",
    "green": "#51CF66",
    "yellow": "#FFD43B",
    "blue": "#74C0FC",
    "magenta": "#CC5DE8",
    "cyan": "#66D9E8",
    "white": "#CED4DA",
    "brightblack": "#545B77",
    "brightred": "#FF8787",
    "brightgreen": "#69DB7C",
    "brightyellow": "#FFE066",
    "brightblue": "#91D5FF",
    "brightmagenta": "#DA77F2",
    "brightcyan": "#99E9F2",
    "brightwhite": "#F8F9FA",
    "default": "#E0E4F0",
}

# 256-color xterm palette (indices 0-15 map to TERM_COLORS above)
TERM_256 = [
    "#000000",
    "#800000",
    "#008000",
    "#808000",
    "#000080",
    "#800080",
    "#008080",
    "#c0c0c0",
    "#808080",
    "#ff0000",
    "#00ff00",
    "#ffff00",
    "#0000ff",
    "#ff00ff",
    "#00ffff",
    "#ffffff",
]
# 216 color cube (indices 16-231)
for r in range(6):
    for g in range(6):
        for b in range(6):
            TERM_256.append(f"#{r * 51:02x}{g * 51:02x}{b * 51:02x}")
# 24 grayscale (indices 232-255)
for i in range(24):
    v = 8 + i * 10
    TERM_256.append(f"#{v:02x}{v:02x}{v:02x}")

# platform-specific fonts
if sys.platform == "darwin":
    FONT_SYSTEM = ".AppleSystemUIFont"
    FONT_MONO = "Menlo"
elif sys.platform == "win32":
    FONT_SYSTEM = "Segoe UI"
    FONT_MONO = "Consolas"
else:
    FONT_SYSTEM = "sans-serif"
    FONT_MONO = "monospace"

FONT_SIZE = 13
FONT_SIZE_SMALL = 12

# asset paths (relative to BASE_DIR, works in both dev and frozen)
ICON_PATH = BASE_DIR / "extras" / "images" / "icon.png"
LOGO_PATH = BASE_DIR / "extras" / "images" / "logo.png"
