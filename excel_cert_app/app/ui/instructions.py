"""Pre-exam instructions screen (S2)."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import config
from . import widgets


class InstructionsScreen(QWidget):
    start_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Screen")
        self._name_lbl: QLabel | None = None
        self._build()

    def _build(self) -> None:
        title = widgets.label("Avant de commencer", "Title",
                              Qt.AlignmentFlag.AlignCenter)
        self._name_lbl = widgets.label("", "Subtitle", Qt.AlignmentFlag.AlignCenter)

        card = widgets.card()
        body = QVBoxLayout(card)
        body.setContentsMargins(40, 34, 40, 34)
        body.setSpacing(14)

        rules = [
            f"⏱  Durée totale : {config.DEFAULT_EXAM_MINUTES} minutes pour "
            f"{config.PROJECTS_PER_EXAM} projets.",
            "📄  Chaque projet contient plusieurs tâches à réaliser dans Excel.",
            "🟢  Marquez une tâche comme « achevée » ou « à réviser » pour vous repérer.",
            "📤  Cliquez sur « Soumettre le projet » pour passer au projet suivant.",
            "🔁  Si vous terminez avant la fin du temps, vous pourrez revenir sur "
            "chaque projet.",
            "🔒  L'application reste verrouillée jusqu'à la fin. La déconnexion "
            "nécessite un code administrateur.",
            "✅  Score de réussite : "
            f"{config.DEFAULT_PASS_THRESHOLD}% ou plus.",
        ]
        cap = widgets.label("Déroulement de l'épreuve", "CardTitle")
        body.addWidget(cap)
        for r in rules:
            body.addWidget(widgets.label(r))

        card.setMaximumWidth(720)
        card_row = QHBoxLayout()
        card_row.addStretch(1)
        card_row.addWidget(card, 4)
        card_row.addStretch(1)

        self.start_btn = QPushButton("Démarrer le test")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setMinimumWidth(240)
        self.start_btn.setAutoDefault(True)
        self.start_btn.clicked.connect(self.start_clicked.emit)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.start_btn)
        btn_row.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.addStretch(1)
        outer.addWidget(title)
        outer.addWidget(self._name_lbl)
        outer.addSpacing(20)
        outer.addLayout(card_row)
        outer.addSpacing(24)
        outer.addLayout(btn_row)
        outer.addStretch(1)

    def set_candidate(self, first: str, last: str, variant: str) -> None:
        self._name_lbl.setText(f"Candidat : {first} {last}  ·  Épreuve {variant}")

    def focus_default(self) -> None:
        self.start_btn.setFocus()
