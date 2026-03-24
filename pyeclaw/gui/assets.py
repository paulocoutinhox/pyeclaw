from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

from pyeclaw.config import ICON_PATH, LOGO_PATH


class Assets:
    """centralized asset loader for app images."""

    @staticmethod
    def app_icon() -> QIcon:
        """load the application icon as QIcon."""
        icon = QIcon()
        if ICON_PATH.exists():
            icon.addFile(str(ICON_PATH))
        return icon

    @staticmethod
    def icon_pixmap(size: int = 22) -> QPixmap:
        """load the app icon as a scaled QPixmap."""
        if ICON_PATH.exists():
            return QPixmap(str(ICON_PATH)).scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return QPixmap()

    @staticmethod
    def logo_pixmap(size: int = 68) -> QPixmap:
        """load the app logo as a scaled QPixmap."""
        if LOGO_PATH.exists():
            return QPixmap(str(LOGO_PATH)).scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return QPixmap()
