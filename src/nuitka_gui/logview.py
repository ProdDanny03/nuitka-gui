"""The build output pane.

A QPlainTextEdit with the two behaviours a build log needs: it follows the
output unless the reader has scrolled up, and it reassembles process output
that arrives in chunks which do not line up with the lines being written.
"""

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit


class BuildLog(QPlainTextEdit):
    """Read-only output that keeps itself readable during a build."""

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setPlaceholderText("Build output...")
        self.setFixedHeight(180)
        # A process writes in whatever sizes the pipe hands over, so a line
        # can arrive in pieces. The tail waits here for its newline.
        self.pending: str = ""

    def write(self, text: str) -> None:
        """Append text, scrolling only if the view was already at the end."""
        if text == "":
            return
        bar = self.verticalScrollBar()
        following = bar.value() >= bar.maximum()
        cursor = self.textCursor()
        _ = cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        if following:
            bar.setValue(bar.maximum())

    def note(self, text: str) -> None:
        """Add one of our own messages as a line of its own."""
        self.write(text + "\n")

    def append_output(self, text: str) -> None:
        """Add process output, holding back any half-written last line."""
        if text == "":
            return
        self.pending += text
        head, newline, self.pending = self.pending.rpartition("\n")
        if newline == "":
            return
        self.write(head + newline)

    def flush(self) -> None:
        """Write out a last line that never got its newline."""
        if self.pending == "":
            return
        tail, self.pending = self.pending, ""
        self.write(tail)
