"""Écran 4 — Préparation de l'examen.

A locked loading screen shown between the supervisor's validation (Écran 3)
and the exam instructions — the controller drives the actual preparation
steps (see `AppController._on_supervisor_validated`) and switches away from
this screen once ready; there is nothing to click here.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QProgressBar, QVBoxLayout, QWidget

from . import widgets


class PreparationScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Screen")

        title = widgets.label("Préparation de l'examen…", "Title",
                              Qt.AlignmentFlag.AlignCenter)
        subtitle = widgets.label(
            "Merci de patienter, votre poste d'examen est en cours de préparation.",
            "Subtitle", Qt.AlignmentFlag.AlignCenter)

        progress = QProgressBar()
        progress.setRange(0, 0)
        progress.setTextVisible(False)
        progress.setFixedHeight(6)
        progress.setFixedWidth(360)

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 26)
        root.addStretch(1)
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(20)
        root.addWidget(progress, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addStretch(2)

    def focus_default(self) -> None:
        pass
