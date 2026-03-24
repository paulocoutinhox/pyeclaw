import platform
import sys

from PySide6.QtWidgets import QApplication

from pyeclaw.config import APP_NAME
from pyeclaw.gui.assets import Assets
from pyeclaw.gui.main_window import MainWindow


class MacOSIntegration:
    """macos-specific integrations for menu bar and dock."""

    @staticmethod
    def apply():
        """set the application name in macOS menu bar and dock."""
        if platform.system() != "Darwin":
            return

        import ctypes
        import ctypes.util

        lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))

        send2 = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(("objc_msgSend", lib))

        send3 = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
            ("objc_msgSend", lib)
        )

        send3s = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p)(
            ("objc_msgSend", lib)
        )

        send3l = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)(
            ("objc_msgSend", lib)
        )

        lib.objc_getClass.restype = ctypes.c_void_p
        lib.objc_getClass.argtypes = [ctypes.c_char_p]
        lib.sel_registerName.restype = ctypes.c_void_p
        lib.sel_registerName.argtypes = [ctypes.c_char_p]

        cls = lib.objc_getClass
        sel = lib.sel_registerName

        ns_str = send2(cls(b"NSString"), sel(b"alloc"))
        ns_name = send3s(ns_str, sel(b"initWithUTF8String:"), APP_NAME.encode())

        proc_info = send2(cls(b"NSProcessInfo"), sel(b"processInfo"))
        send3(proc_info, sel(b"setProcessName:"), ns_name)

        ctypes.cdll.LoadLibrary(ctypes.util.find_library("AppKit"))

        app_inst = send2(cls(b"NSApplication"), sel(b"sharedApplication"))
        main_menu = send2(app_inst, sel(b"mainMenu"))
        if main_menu:
            first_item = send3l(main_menu, sel(b"itemAtIndex:"), 0)
            if first_item:
                submenu = send2(first_item, sel(b"submenu"))
                if submenu:
                    send3(submenu, sel(b"setTitle:"), ns_name)


def main():
    QApplication.setApplicationName(APP_NAME)
    QApplication.setOrganizationName("PyeClaw")
    QApplication.setOrganizationDomain("pyeclaw.app")

    app = QApplication(sys.argv)

    icon = Assets.app_icon()
    app.setWindowIcon(icon)

    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()

    MacOSIntegration.apply()

    sys.exit(app.exec())
