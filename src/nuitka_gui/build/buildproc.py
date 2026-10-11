"""Running the build as a child process, and stopping it again.

Takes plain callbacks rather than a widget, so the recovery paths can be
exercised without a screen.
"""

from collections.abc import Callable

from PySide6.QtCore import QObject, QProcess


class BuildProcess(QObject):
    """One Nuitka run, with the recovery paths in one place."""

    def __init__(
        self,
        log: Callable[[str], None],
        on_busy: Callable[[bool], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.log = log
        self.on_busy = on_busy
        self.on_output: Callable[[str], None] | None = None
        self.on_output_end: Callable[[], None] | None = None
        self.proc: QProcess | None = None
        self.killer: QProcess | None = None

    def running(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning

    def start(
        self,
        argv: list[str],
        working_dir: str,
        on_output: Callable[[str], None],
        on_output_end: Callable[[], None] | None = None,
    ) -> None:
        """Launch argv and report what it prints, in whatever chunks it
        produces; joining them is the receiver's job."""
        try:
            proc = QProcess(self)
            proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            proc.setWorkingDirectory(working_dir)
            self.on_output = on_output
            self.on_output_end = on_output_end
            _ = proc.readyReadStandardOutput.connect(lambda: self.read_output(proc))
            _ = proc.errorOccurred.connect(lambda error: self.on_error(proc, error))
            _ = proc.finished.connect(self.on_finished)
            self.proc = proc
            self.on_busy(True)
            proc.start(argv[0], argv[1:])
        except Exception as exc:  # noqa: BLE001
            self.log(f"Failed to start process: {exc}")
            self.on_busy(False)

    def read_output(self, proc: QProcess) -> None:
        data = bytes(proc.readAllStandardOutput().data())
        if len(data) == 0 or self.on_output is None:
            return
        self.on_output(data.decode("utf-8", errors="replace"))

    def reset_run_state(self) -> None:
        """Say the build is over, however it ended."""
        self.on_busy(False)

    def on_error(self, proc: QProcess, error: QProcess.ProcessError) -> None:
        """Recover from a start failure.

        A process that never started is the one failure Qt does not report
        as "finished", so the reset has to happen here as well, or the
        window would sit on "Compiling..." with nothing to cancel.
        """
        if error != QProcess.ProcessError.FailedToStart:
            return
        self.reset_run_state()
        self.proc = None
        self.log(f"Could not start Nuitka: {proc.errorString()}")

    def on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self.reset_run_state()
        self.proc = None
        if self.on_output_end is not None:
            self.on_output_end()
        self.log(f"\nProcess exited: code={exit_code} status={exit_status.name}")

    def stop(self) -> None:
        """Kill the build and everything it spawned.

        Nuitka drives cl.exe and Scons as children of itself, so killing
        only the direct child would leave those running and eating RAM.
        """
        proc = self.proc
        if proc is None or proc.state() == QProcess.ProcessState.NotRunning:
            # Nothing to kill, but the caller must not be left thinking a
            # build is on.
            self.reset_run_state()
            return
        self.log("Cancelling...")
        self.kill_tree(proc)
        self.reset_run_state()
        self.proc = None

    def kill_tree(self, proc: QProcess) -> None:
        if proc.state() == QProcess.ProcessState.NotRunning:
            return
        pid = proc.processId()
        if pid > 0:
            killer = QProcess(self)
            self.killer = killer
            killer.start("taskkill", ["/F", "/T", "/PID", str(pid)])
            _ = killer.waitForFinished(10000)
            self.killer = None
        _ = proc.kill()
        _ = proc.waitForFinished(5000)
