"""The main window: fields in, one Nuitka command line out.

Only the wiring lives here. What the machine is like, where the toolchain
lives, how the arguments are spelled, how the build runs and how the log
behaves are each in their own module, because each of those is a piece that
can be checked without a window.
"""

from pathlib import Path
from typing import override

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from nuitka_gui.build.buildproc import BuildProcess
from nuitka_gui.build.commandline import (
    BuildRequest,
    build_arguments,
    data_fields,
    data_name,
    data_problem,
    icon_option,
    quote_notes,
    safe_value,
)
from nuitka_gui.build.options import build_args, data_args, off_by_default
from nuitka_gui.build.toolchain import (
    Plugin,
    list_plugins,
    nuitka_command,
    show_command,
)
from nuitka_gui.system.host import default_jobs, launch_dir, logical_cores
from nuitka_gui.system.sources import default_output, find_main
from nuitka_gui.ui.logview import BuildLog
from nuitka_gui.ui.plugindialog import build_plugin_dialog


class NuitkaApp(QWidget):
    """The whole window, and the small state a build needs."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Nuitka GUI')
        self.resize(900, 650)

        self.data_modes = data_args
        self.data_index = 0
        self.selected_plugins: set[str] = set()
        self.plugin_cache: list[Plugin] | None = None
        self.icon_arg = ''
        self.icon_start = ''
        self.auto_script = ''
        self.auto_dest = ''
        self.active_args: list[str] = []

        self._create_widgets()
        self._arrange()
        self._connect()

        self.build = BuildProcess(self.log.note, self.set_busy, self)
        self.sync_args()
        self.autofill_output()
        self.autofill_script()

    def _create_widgets(self) -> None:
        self._create_file_widgets()
        self._create_data_widgets()
        self._create_option_widgets()
        self._create_icon_widgets()
        self._create_run_widgets()
        self.log = BuildLog()

    def _create_file_widgets(self) -> None:
        self.py_dir = QLineEdit(placeholderText='main.py')
        self.py_browse = QPushButton('Browse')

        self.out_dir = QLineEdit(placeholderText='Path/to/dist')
        self.out_browse = QPushButton('Browse')

        self.exe_name = QLineEdit(placeholderText='myapp')

    def _create_data_widgets(self) -> None:
        self.data_source = QLineEdit()
        self.data_source.setPlaceholderText(r'file or folder to include, e.g. assets\app.dat')
        self.data_source.setToolTip(
            'The file or folder to ship with the app, absolute or'
            r' relative to the script folder.\nA source=destination'
            ' pair pasted here still works, the destination being taken'
            ' from it when the next field is empty.'
        )
        self.data_browse = QPushButton('Browse')

        self.data_dest = QLineEdit()
        self.data_dest.setPlaceholderText('name in the app, e.g. app.dat')
        self.data_dest.setToolTip(
            'Where the file or folder lands inside the app, relative to'
            ' its root. Leave it empty to use the name it already has.'
        )

        self.data_btn = QPushButton(self.data_modes[0])

    def _create_option_widgets(self) -> None:
        self.arg_boxes: dict[str, QCheckBox] = {}
        for arg in build_args:
            box = QCheckBox(arg)
            box.setChecked(arg not in off_by_default)
            self.arg_boxes[arg] = box

        self.extra_args = QPlainTextEdit()
        self.extra_args.setPlaceholderText('Extra args, e.g. --company-name=Acme')
        self.extra_args.setFixedHeight(64)

    def _create_icon_widgets(self) -> None:
        self.plugin_btn = QPushButton('Plugins')
        self.plugin_btn.setToolTip('Pick Nuitka plugins to enable. None are enabled by default.')

        self.icon_btn = QPushButton('Icon')
        self.icon_btn.setToolTip('Take the app icon from a .ico or an .exe.')

        self.icon_label = QLabel('No icon')
        # Fixed width and a single elided line, so neither the width nor the
        # height of this column depends on how long the path is.
        self.icon_label.setFixedWidth(190)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.clear_btn = QPushButton('Clear')
        self.clear_btn.setEnabled(False)
        self.clear_btn.setToolTip('Remove the selected icon.')

    def _create_run_widgets(self) -> None:
        self.jobs = QSpinBox()
        self.jobs.setRange(0, 256)
        self.jobs.setPrefix('Jobs ')
        self.jobs.setSpecialValueText('Jobs Auto')
        self.jobs.setValue(0)
        self.jobs.setToolTip(
            'Parallel C compiler processes (Nuitka --jobs).\n'
            f'Auto uses one per logical core ({logical_cores()} here), each'
            ' holding hundreds of MB.\n'
            f"{default_jobs()} is the amount this machine's RAM can take."
        )

        self.compile_btn = QPushButton('Compile')
        self.cancel_btn = QPushButton('Cancel')
        self.cancel_btn.setEnabled(False)

    def _arrange(self) -> None:
        fields = QVBoxLayout()
        fields.addLayout(self._row(self.py_dir, self.py_browse))
        fields.addLayout(self._row(self.out_dir, self.out_browse))
        fields.addLayout(self._row(self.exe_name))

        data_row = QHBoxLayout()
        data_row.addWidget(self.data_source, 1)
        data_row.addWidget(self.data_browse)
        data_row.addWidget(self.data_dest, 1)
        data_row.addWidget(self.data_btn)
        fields.addLayout(data_row)

        grid = QGridLayout()
        for i, box in enumerate(self.arg_boxes.values()):
            grid.addWidget(box, i // 2, i % 2)

        icon_row = QHBoxLayout()
        icon_row.addWidget(self.icon_label, 1, Qt.AlignmentFlag.AlignRight)
        icon_row.addWidget(self.icon_btn)

        side = QVBoxLayout()
        side.addWidget(self.plugin_btn, 0, Qt.AlignmentFlag.AlignRight)
        side.addLayout(icon_row)
        side.addWidget(self.clear_btn, 0, Qt.AlignmentFlag.AlignRight)
        side.addStretch()

        options = QHBoxLayout()
        options.addLayout(grid)
        options.addStretch()
        options.addLayout(side)

        controls = QHBoxLayout()
        controls.addWidget(self.jobs)
        controls.addWidget(self.compile_btn)
        controls.addWidget(self.cancel_btn)
        controls.addStretch()

        root = QVBoxLayout(self)
        root.addLayout(fields)
        root.addLayout(options)
        root.addWidget(self.extra_args)
        root.addLayout(controls)
        root.addWidget(self.log)

    @staticmethod
    def _row(*widgets: QWidget) -> QHBoxLayout:
        """A horizontal row whose first widget takes the spare width."""
        row = QHBoxLayout()
        for i, widget in enumerate(widgets):
            row.addWidget(widget, 1 if i == 0 else 0)
        return row

    def _connect(self) -> None:
        self.py_browse.clicked.connect(self.py_browser)
        self.out_browse.clicked.connect(self.out_browser)
        self.data_browse.clicked.connect(self.data_browser)
        self.data_btn.clicked.connect(self.toggle_data_mode)
        self.plugin_btn.clicked.connect(self.show_plugins)
        self.icon_btn.clicked.connect(self.pick_icon)
        self.clear_btn.clicked.connect(self.clear_icon)
        self.compile_btn.clicked.connect(self.compile)
        self.cancel_btn.clicked.connect(self.cancel)

        for box in self.arg_boxes.values():
            box.toggled.connect(self.sync_args)

        self.out_dir.textChanged.connect(self.autofill_script)
        self.out_dir.textChanged.connect(self.sync_args)
        for control in (
            self.py_dir,
            self.exe_name,
            self.data_source,
            self.data_dest,
        ):
            control.textChanged.connect(self.sync_args)
        self.extra_args.textChanged.connect(self.sync_args)
        self.jobs.valueChanged.connect(self.sync_args)

    def request(self) -> BuildRequest:
        """What the window currently describes, as one build request."""
        return BuildRequest(
            script=self.py_dir.text(),
            out_dir=self.out_dir.text(),
            exe_name=self.exe_name.text(),
            data_source=self.data_source.text(),
            data_dest=self.data_dest.text(),
            data_flag=self.data_modes[self.data_index],
            plugins=self.selected_plugins,
            icon_arg=self.icon_arg,
            extra_args=self.extra_args.toPlainText(),
            jobs=self.jobs.value(),
            flags=[arg for arg, box in self.arg_boxes.items() if box.isChecked()],
        )

    def sync_args(self) -> None:
        self.active_args = build_arguments(self.request())

    def set_busy(self, busy: bool) -> None:
        """Compile and Cancel swap over, one of them always live."""
        self.compile_btn.setEnabled(not busy)
        self.compile_btn.setText('Compiling...' if busy else 'Compile')
        self.cancel_btn.setEnabled(busy)

    def plugin_list(self) -> list[Plugin]:
        """Every plugin the resolved Nuitka has, for this session.

        Cached because it costs a process start. Only a run that worked is
        cached, so a Nuitka that was not reachable yet gets another chance.
        """
        if self.plugin_cache is not None:
            return self.plugin_cache
        try:
            plugins = list_plugins(self)
        except (FileNotFoundError, TimeoutError) as exc:
            self.log.note(str(exc))
            return []
        if len(plugins) == 0:
            # A real Nuitka always lists something, so an empty answer means
            # the run failed, e.g. the venv could not be activated. Not
            # caching it leaves a later attempt free to work.
            self.log.note('Nuitka returned no plugins.')
            return []
        self.plugin_cache = plugins
        return plugins

    def set_plugin(self, name: str, checked: bool) -> None:
        if checked:
            self.selected_plugins.add(name)
        else:
            self.selected_plugins.discard(name)
        self.sync_args()

    def show_plugins(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            dialog = build_plugin_dialog(
                self, self.plugin_list(), self.selected_plugins, self.set_plugin
            )
        finally:
            QApplication.restoreOverrideCursor()
        dialog.adjustSize()
        corner = self.mapToGlobal(self.rect().topRight())
        dialog.move(corner.x() - dialog.width(), corner.y())
        dialog.exec()

    def toggle_data_mode(self) -> None:
        self.data_index = (self.data_index + 1) % len(self.data_modes)
        self.data_btn.setText(self.data_modes[self.data_index])
        self.sync_args()

    def autofill_output(self) -> None:
        """Default the output path to the launch folder's "dist" subfolder.

        Leaves the field alone when it already has a value, or when the
        launch folder has no dist subfolder to offer.
        """
        if self.out_dir.text().strip() != '':
            return
        candidate = default_output(launch_dir())
        if candidate != '':
            self.out_dir.setText(candidate)

    def autofill_script(self) -> None:
        """Fill in main.py from the probed folders, never overwriting a real
        file.

        A path this method filled in earlier is not treated as the user's
        own choice, so re-running after an output path change can replace
        it. Anything else the user typed is left alone.
        """
        current = self.py_dir.text().strip()
        if current != '' and current != self.auto_script:
            return
        found = find_main(self.out_dir.text(), launch_dir())
        if found == '':
            return
        self.auto_script = found
        self.py_dir.setText(found)

    def pick_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Select icon file or executable',
            self.icon_start,
            'Icon or executable (*.ico *.exe)',
        )
        if path == '':
            return
        flag = icon_option(path)
        if flag == '':
            self.log.note('Pick a .ico or an .exe for the icon.')
            return
        self.icon_arg = safe_value(flag)
        self.icon_start = str(Path(path).parent)
        self.icon_btn.setToolTip(f'Icon: {path}')
        self.show_icon_text(path)
        self.clear_btn.setEnabled(True)
        self.sync_args()

    def show_icon_text(self, path: str) -> None:
        """Show the icon path on one line, elided, or the empty label.

        Eliding in the middle keeps the file name readable, and the full
        path stays in the label tooltip.
        """
        if path == '':
            self.icon_label.setText('No icon')
            self.icon_label.setToolTip('')
            return
        metrics = QFontMetrics(self.icon_label.font())
        elided = metrics.elidedText(path, Qt.TextElideMode.ElideMiddle, self.icon_label.width())
        self.icon_label.setText(elided)
        self.icon_label.setToolTip(path)

    def clear_icon(self) -> None:
        self.icon_arg = ''
        self.icon_start = ''
        self.icon_btn.setToolTip('Take the app icon from a .ico or an .exe.')
        self.show_icon_text('')
        self.clear_btn.setEnabled(False)
        self.sync_args()

    def build_problem(self) -> str:
        """The first reason this build cannot start, or "" when it can."""
        request = self.request()
        script = Path(safe_value(request.script.strip()))
        if not script.is_file():
            return 'Select an existing Python file first.'
        if '--zig' in self.active_args and any(
            arg.startswith('--msvc') for arg in self.active_args
        ):
            return 'Pick one C compiler backend: untick --zig or --msvc=latest.'
        # The build runs in the script's folder, which is what a relative
        # path in the data fields is measured from.
        return data_problem(
            request.data_source, request.data_dest, request.data_flag, script.parent
        )

    def running(self) -> bool:
        return self.build.running()

    def compile(self) -> None:
        if self.running():
            return
        problem = self.build_problem()
        if problem != '':
            self.log.note(problem)
            return
        try:
            argv = nuitka_command(self.active_args)
        except FileNotFoundError as exc:
            self.log.note(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self.log.note(f'Could not build Nuitka command: {exc}')
            return
        try:
            script = Path(safe_value(self.py_dir.text().strip()))
            notes = self.quote_notes()
            if len(notes) > 0:
                self.log.note(f'Double quotes replaced with single quotes in: {", ".join(notes)}')
            self.log.note(f'Project: {launch_dir()}')
            # The Nuitka line is logged rather than the PowerShell wrapper
            # around it, since it is the part worth reading and copying.
            self.log.note(show_command(['nuitka.cmd', *self.active_args]))
            self.build.start(argv, str(script.parent), self.log.append_output, self.log.flush)
        except Exception as exc:  # noqa: BLE001
            self.log.note(f'Build process error: {exc}')

    def quote_notes(self) -> list[str]:
        """Which fields had double quotes replaced before the build."""
        return quote_notes(
            {
                'script': self.py_dir.text(),
                'output dir': self.out_dir.text(),
                'output filename': self.exe_name.text(),
                'data path': self.data_source.text(),
                'data name': self.data_dest.text(),
                'extra args': self.extra_args.toPlainText(),
            }
        )

    def cancel(self) -> None:
        self.build.stop()

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        if self.build.proc is not None:
            self.build.kill_tree(self.build.proc)
        super().closeEvent(event)

    def py_browser(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Python File', self.py_dir.text(), 'Python (*.py)'
        )
        if path != '':
            self.py_dir.setText(path)

    def out_browser(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, 'Select output directory', self.out_dir.text()
        )
        if path != '':
            self.out_dir.setText(path)

    def data_start(self) -> str:
        """The folder the data file dialog should open in.

        The folder the path field already names when that is a folder,
        the folder holding it when the field names a file, and the launch
        folder when the field is empty.
        """
        path_text, _ = data_fields(self.data_source.text(), self.data_dest.text())
        if path_text == '':
            return str(launch_dir())
        path = Path(path_text)
        return str(path if path.is_dir() else path.parent)

    def data_browser(self) -> None:
        """Pick the file or folder the data option will include.

        The dialog follows the toggle, since one option wants a single
        file and the other a whole folder.
        """
        if self.data_modes[self.data_index] == '--include-data-dir':
            path = QFileDialog.getExistingDirectory(self, 'Select data folder', self.data_start())
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, 'Select data file', self.data_start(), 'All files (*)'
            )
        if path != '':
            self.set_data_source(path)

    def set_data_source(self, path: str) -> None:
        self.data_source.setText(path)
        self.autofill_data_dest(path)

    def autofill_data_dest(self, picked: str) -> None:
        """Name the destination after a picked path, never over a real one.

        A destination this method filled in itself is not treated as the
        user's own choice, so picking again replaces it, the way
        autofill_script treats a script path it filled in.
        """
        current = self.data_dest.text().strip()
        if current != '' and current != self.auto_dest:
            return
        name = data_name(safe_value(picked))
        if name == '':
            return
        self.auto_dest = name
        self.data_dest.setText(name)
