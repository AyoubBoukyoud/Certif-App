"""Review board (S4): shown when all projects are submitted but time remains."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..exam.session import ExamSession
from ..exam.timer import format_mmss
from . import widgets


class _ProjectCard(QWidget):
    clicked = pyqtSignal(int)

    def __init__(self, project_no: int, title: str, complete: int,
                 review: int, total: int) -> None:
        super().__init__()
        self._no = project_no
        frame = widgets.card()
        frame.setObjectName("ProjectCard")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.addWidget(widgets.label(f"Projet {project_no}", "CardTitle"))
        lay.addWidget(widgets.label(title, "FieldLabel"))
        lay.addWidget(widgets.label(f"✔ {complete}/{total} achevées", "FieldLabel"))
        lay.addWidget(widgets.label(f"★ {review} à réviser", "FieldLabel"))
        btn = QPushButton("Reprendre")
        btn.clicked.connect(lambda: self.clicked.emit(self._no))
        lay.addWidget(btn)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)


class ReviewBoard(QWidget):
    reopen_project = pyqtSignal(int)
    finish_test = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Screen")
        self.session: ExamSession | None = None
        self._build()

    def _build(self) -> None:
        self.title = widgets.label("Tableau de bord — révision", "Title",
                                   Qt.AlignmentFlag.AlignCenter)
        self.subtitle = widgets.label("", "Subtitle", Qt.AlignmentFlag.AlignCenter)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(18)

        finish = QPushButton("Terminer le test")
        finish.setObjectName("Danger")
        finish.setMinimumHeight(48)
        finish.setMinimumWidth(220)
        finish.clicked.connect(self._confirm_finish)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(finish)
        btn_row.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(50, 40, 50, 36)
        outer.addWidget(self.title)
        outer.addWidget(self.subtitle)
        outer.addSpacing(20)
        outer.addWidget(self.grid_host, 1)
        outer.addSpacing(16)
        outer.addLayout(btn_row)

    def refresh(self) -> None:
        assert self.session is not None
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        remaining = self.session.remaining_seconds()
        self.subtitle.setText(
            f"Temps restant : {format_mmss(remaining)}  ·  "
            "Cliquez sur un projet pour le reprendre."
        )
        for i, sp in enumerate(self.session.session_projects):
            project = self.session.projects[sp.project_no]
            marks = self.session.db.get_task_marks(sp.id)
            complete = sum(1 for m in marks.values() if m["complete"])
            review = sum(1 for m in marks.values() if m["review"])
            card = _ProjectCard(sp.project_no, project.title, complete,
                                review, len(project.tasks))
            card.clicked.connect(self.reopen_project.emit)
            self.grid.addWidget(card, i // 4, i % 4)

    def _confirm_finish(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle("Terminer le test")
        box.setText("Terminer et corriger le test maintenant ? Cette action est "
                    "définitive.")
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.finish_test.emit()
