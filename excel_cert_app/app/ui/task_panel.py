"""Bottom-docked exam task panel (S3).

Mirrors the original simulator: project position + countdown on top, a tab per
task, the current task statement, and the mark/navigate buttons. Excel occupies
the screen above this panel.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from .. import config
from ..exam.session import ExamSession
from ..exam.timer import format_mmss
from . import widgets


class TaskPanel(QWidget):
    submit_project = pyqtSignal()
    logout_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    theme_toggle_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    hide_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TaskPanel")
        self.setFixedHeight(config.PANEL_HEIGHT)
        self.session: ExamSession | None = None
        self._current_task_idx = 0
        self._build()

    def _build(self) -> None:
        frame = QWidget(self)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        root = QVBoxLayout(frame)
        root.setContentsMargins(18, 10, 18, 12)
        root.setSpacing(8)

        # -- top strip: project/clock on one row, actions on their own row
        # below so labels and buttons never crowd each other on narrower
        # screens. --
        self.info = widgets.label("Projet 1 sur 7", "PanelInfo")
        self.info.setMinimumWidth(0)
        self.clock = QLabel("50:00")
        self.clock.setObjectName("Clock")

        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self.info, 1)
        top.addWidget(self.clock, 0)
        root.addLayout(top)

        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setObjectName("ThemeToggle")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setToolTip("Changer de thème")
        self.theme_btn.clicked.connect(self.theme_toggle_requested.emit)
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setObjectName("ThemeToggle")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setToolTip(
            "Redémarrer Excel (ferme tous les processus Excel et rouvre le "
            "fichier du projet en cours)"
        )
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.hide_btn = QPushButton("▾ Masquer")
        self.hide_btn.setObjectName("Secondary")
        self.hide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hide_btn.setToolTip("Masquer le panneau (Excel occupe tout l'écran)")
        self.hide_btn.clicked.connect(self.hide_requested.emit)
        submit = QPushButton("Soumettre le projet")
        submit.clicked.connect(self._confirm_submit)
        logout = QPushButton("Déconnexion")
        logout.setObjectName("Secondary")
        logout.clicked.connect(self.logout_requested.emit)
        quit_btn = QPushButton("✕")
        quit_btn.setObjectName("QuitIcon")
        quit_btn.setToolTip("Quitter")
        quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_btn.clicked.connect(self.quit_requested.emit)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.theme_btn)
        actions.addWidget(self.refresh_btn)
        actions.addWidget(self.hide_btn)
        actions.addStretch(1)
        actions.addWidget(quit_btn)
        actions.addWidget(logout)
        actions.addWidget(submit)
        root.addLayout(actions)

        # -- task tabs --
        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self.tabs)

        # -- statement (scrolls when the task text is long) --
        self.statement = QLabel("")
        self.statement.setObjectName("Statement")
        self.statement.setWordWrap(True)
        self.statement.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.statement.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        scroll = QScrollArea()
        scroll.setObjectName("StatementScroll")
        scroll.setWidget(self.statement)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setMinimumHeight(70)
        root.addWidget(scroll, 1)

        # -- bottom buttons --
        self.prev_btn = QPushButton("◀ Tâche précédente")
        self.prev_btn.setObjectName("Secondary")
        self.prev_btn.clicked.connect(self._prev_task)
        self.review_btn = QPushButton("Marquer pour réviser")
        self.review_btn.setObjectName("Secondary")
        self.review_btn.clicked.connect(self._toggle_review)
        self.complete_btn = QPushButton("Marquer achevée")
        self.complete_btn.clicked.connect(self._toggle_complete)
        self.next_btn = QPushButton("Tâche suivante ▶")
        self.next_btn.setObjectName("Secondary")
        self.next_btn.clicked.connect(self._next_task)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        bottom.addStretch(1)
        bottom.addWidget(self.prev_btn)
        bottom.addWidget(self.review_btn)
        bottom.addWidget(self.complete_btn)
        bottom.addWidget(self.next_btn)
        bottom.addStretch(1)
        root.addLayout(bottom)

    def set_theme_label(self, label: str) -> None:
        self.theme_btn.setToolTip(label)

    # -- data binding ------------------------------------------------------

    def load_project(self) -> None:
        """Rebuild the panel for the session's current project."""
        assert self.session is not None
        project = self.session.current_project()
        idx, total = self.session.display_position()
        self.info.setText(f"Projet {idx} sur {total}  ·  {project.title}")

        self.tabs.blockSignals(True)
        while self.tabs.count():
            self.tabs.removeTab(0)
        for t in project.tasks:
            self.tabs.addTab(f"Tâche {t.id}")
        self.tabs.blockSignals(False)
        self._current_task_idx = 0
        self.tabs.setCurrentIndex(0)
        self._refresh_task()

    def _current_task(self):
        return self.session.current_project().tasks[self._current_task_idx]

    def _refresh_task(self) -> None:
        task = self._current_task()
        self.statement.setText(task.statement)
        marks = self.session.current_marks().get(task.id, {})
        complete = marks.get("complete", False)
        review = marks.get("review", False)
        self.complete_btn.setText("✔ Achevée" if complete else "Marquer achevée")
        self.review_btn.setText("★ À réviser" if review else "Marquer pour réviser")
        self.prev_btn.setEnabled(self._current_task_idx > 0)
        self.next_btn.setEnabled(
            self._current_task_idx < self.tabs.count() - 1
        )
        self._refresh_tab_labels()

    def _refresh_tab_labels(self) -> None:
        marks = self.session.current_marks()
        for i, t in enumerate(self.session.current_project().tasks):
            m = marks.get(t.id, {})
            prefix = "✔ " if m.get("complete") else ("★ " if m.get("review") else "")
            self.tabs.setTabText(i, f"{prefix}Tâche {t.id}")

    # -- clock -------------------------------------------------------------

    def update_clock(self, seconds: int) -> None:
        self.clock.setText(format_mmss(seconds))
        self.clock.setObjectName("ClockLow" if seconds <= config.LOW_TIME_WARNING_S
                                 else "Clock")
        # re-apply stylesheet for the changed objectName
        self.clock.style().unpolish(self.clock)
        self.clock.style().polish(self.clock)

    # -- interactions ------------------------------------------------------

    def _on_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        self._current_task_idx = index
        self._refresh_task()

    def _prev_task(self) -> None:
        if self._current_task_idx > 0:
            self.tabs.setCurrentIndex(self._current_task_idx - 1)

    def _next_task(self) -> None:
        if self._current_task_idx < self.tabs.count() - 1:
            self.tabs.setCurrentIndex(self._current_task_idx + 1)

    def _toggle_complete(self) -> None:
        task = self._current_task()
        marks = self.session.current_marks().get(task.id, {})
        new_val = not marks.get("complete", False)
        self.session.mark_task(task.id, complete=new_val,
                               review=False if new_val else None)
        self._refresh_task()

    def _toggle_review(self) -> None:
        task = self._current_task()
        marks = self.session.current_marks().get(task.id, {})
        new_val = not marks.get("review", False)
        self.session.mark_task(task.id, review=new_val,
                               complete=False if new_val else None)
        self._refresh_task()

    def _confirm_submit(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle("Soumettre le projet")
        box.setText("Soumettre ce projet ? Vous ne pourrez y revenir qu'après "
                    "avoir soumis les 7 projets (si du temps reste).")
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.submit_project.emit()
