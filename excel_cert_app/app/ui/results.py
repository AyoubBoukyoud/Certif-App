"""Results screen (S5)."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..exam.session import GradeResult
from . import widgets


class ResultsScreen(QWidget):
    next_candidate = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Screen")
        self._build()

    def _build(self) -> None:
        self.title = widgets.label("Résultat", "Title", Qt.AlignmentFlag.AlignCenter)
        self.card = widgets.card()
        self.card.setMaximumWidth(640)
        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(40, 34, 40, 34)
        self.body.setSpacing(10)

        self.score = QLabel("—")
        self.score.setObjectName("ScoreBig")
        self.score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verdict = QLabel("")
        self.verdict.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail = widgets.label("", "FieldLabel", Qt.AlignmentFlag.AlignCenter)
        self.breakdown = QVBoxLayout()

        self.body.addWidget(self.score)
        self.body.addWidget(self.verdict)
        self.body.addWidget(self.detail)
        self.body.addSpacing(10)
        self.body.addLayout(self.breakdown)

        card_row = QHBoxLayout()
        card_row.addStretch(1)
        card_row.addWidget(self.card, 3)
        card_row.addStretch(1)

        next_btn = QPushButton("Candidat suivant")
        next_btn.setMinimumHeight(48)
        next_btn.setMinimumWidth(220)
        next_btn.clicked.connect(self.next_candidate.emit)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(next_btn)
        btn_row.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(50, 44, 50, 40)
        outer.addStretch(1)
        outer.addWidget(self.title)
        outer.addSpacing(16)
        outer.addLayout(card_row)
        outer.addSpacing(28)
        outer.addLayout(btn_row)
        outer.addStretch(1)

    def show_result(self, result: GradeResult, threshold: int,
                    projects: dict[int, str]) -> None:
        self.score.setText(f"{result.score_pct:.0f}%")
        self.score.setStyleSheet(
            f"color: {'#217346' if result.passed else '#cf1124'};"
        )
        if result.passed:
            self.verdict.setObjectName("VerdictPass")
            self.verdict.setText("RÉUSSI")
        else:
            self.verdict.setObjectName("VerdictFail")
            self.verdict.setText("ÉCHOUÉ")
        self.verdict.style().unpolish(self.verdict)
        self.verdict.style().polish(self.verdict)
        self.detail.setText(
            f"{result.passed_tasks} tâches réussies sur {result.total_tasks} "
            f"·  seuil de réussite {threshold}%"
        )

        while self.breakdown.count():
            item = self.breakdown.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for pno, (p, tot) in result.per_project.items():
            name = projects.get(pno, f"Projet {pno}")
            self.breakdown.addWidget(
                widgets.label(f"Projet {pno} — {name} : {p}/{tot}", "FieldLabel")
            )
