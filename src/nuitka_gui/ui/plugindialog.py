"""The plugin picker."""

from collections.abc import Callable, Collection

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nuitka_gui.build.toolchain import Plugin


def build_plugin_dialog(
    parent: QWidget,
    plugins: Collection[Plugin],
    selected: Collection[str],
    on_toggle: Callable[[str, bool], None],
) -> QDialog:
    """A popup of every plugin with the current picks ticked.

    Shown as a window rather than a menu, because a menu dismisses itself on
    the first pick and this one has to stay open for picking several.
    """
    dialog = QDialog(parent)
    dialog.setWindowFlag(Qt.WindowType.Popup)
    root = QVBoxLayout(dialog)
    listing = QListWidget()
    listing.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    listing.setMinimumWidth(620)
    for plugin in plugins:
        item = QListWidgetItem(f'{plugin.name}   {plugin.description}')
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(
            Qt.CheckState.Checked if plugin.name in selected else Qt.CheckState.Unchecked
        )
        item.setData(Qt.ItemDataRole.UserRole, plugin.name)
        listing.addItem(item)
    root.addWidget(listing)
    root.addWidget(QLabel('Tick plugins to enable, click outside to close.'))

    def toggled(item: QListWidgetItem) -> None:
        name = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(name, str):
            on_toggle(name, item.checkState() == Qt.CheckState.Checked)

    _ = listing.itemChanged.connect(toggled)
    return dialog
