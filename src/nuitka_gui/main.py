"""Entry point for the Nuitka GUI."""

import sys

from PySide6.QtWidgets import QApplication

from nuitka_gui import NuitkaApp, __version__


def restore_qt_connect() -> None:
    """Give PySide6 its own signal methods back when the app is frozen.

    Nuitka's PySide6 plugin replaces SignalInstance.connect and disconnect
    and wraps compiled bound methods in functools.partial, as a guard against
    an old Shiboken argument-counting bug. On this toolchain that guard
    corrupts memory: the frozen app dies with a segmentation fault on the
    first QProcess signal a build connects, so pressing Compile closed the
    window instead of running Nuitka. The patch keeps the methods it replaced
    as orig_connect and friends, so they are easy to put back.

    A no-op when running from source, where no such patch exists.
    """
    from PySide6 import QtCore

    for module in list(sys.modules.values()):
        try:
            original = getattr(module, 'orig_connect', None)
        except Exception:  # noqa: BLE001, S112
            continue
        if original is None:
            continue
        QtCore.SignalInstance.connect = original
        if hasattr(module, 'orig_disconnect'):
            QtCore.SignalInstance.disconnect = module.orig_disconnect
        if hasattr(module, 'orig_singleShot'):
            QtCore.QTimer.singleShot = module.orig_singleShot
        return


def main() -> None:
    restore_qt_connect()
    app = QApplication(sys.argv)
    app.setApplicationName('Nuitka GUI')
    app.setApplicationDisplayName('Nuitka GUI')
    app.setApplicationVersion(__version__)
    window = NuitkaApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
