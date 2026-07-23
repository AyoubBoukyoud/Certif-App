"""Écran 2 — Identification du candidat.

Single CIN field + "Rechercher" button. On success shows a read-only
identity card (fed by `app/supabase_service/candidates.py`) with a
"Commencer l'examen" button; on failure, "Candidat introuvable."
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..supabase_service.candidates import CandidateRecord
from . import widgets


class CandidateLookupScreen(QWidget):
    candidate_confirmed = pyqtSignal(object)  # CandidateRecord
    admin_requested = pyqtSignal()
    quick_test_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Screen")
        self._candidate: CandidateRecord | None = None
        self._build()

    # -- layout --------------------------------------------------------

    def _build(self) -> None:
        brand = widgets.label("MOS", "Brand", Qt.AlignmentFlag.AlignCenter)
        tagline = widgets.label("Microsoft Office Specialist",
                                "Tagline", Qt.AlignmentFlag.AlignCenter)

        self.card = widgets.card()
        self.card.setMaximumWidth(560)
        self.inner = QVBoxLayout(self.card)
        self.inner.setContentsMargins(44, 38, 44, 34)
        self.inner.setSpacing(0)

        self.inner.addWidget(widgets.label("Identification du candidat", "CardTitle",
                                           Qt.AlignmentFlag.AlignCenter))
        self.inner.addSpacing(6)
        self.subtitle = widgets.label(
            "Saisissez votre numéro de CIN pour retrouver votre dossier.",
            "CardSubtitle", Qt.AlignmentFlag.AlignCenter)
        self.inner.addWidget(self.subtitle)
        self.inner.addSpacing(28)

        # -- search state --
        self.search_box = QWidget()
        search_lay = QVBoxLayout(self.search_box)
        search_lay.setContentsMargins(0, 0, 0, 0)
        search_lay.setSpacing(16)
        self.cin = QLineEdit(placeholderText="AB123456")
        self.cin.setMinimumHeight(44)
        self.cin.setClearButtonEnabled(True)
        self.cin.returnPressed.connect(self._on_search)
        search_lay.addWidget(widgets.label("Numéro de CIN", "FieldLabel"))
        search_lay.addWidget(self.cin)

        self.error = widgets.label("", "ErrorBanner")
        self.error.setVisible(False)
        search_lay.addSpacing(8)
        search_lay.addWidget(self.error)

        search_lay.addSpacing(16)
        self.search_btn = QPushButton("Rechercher")
        self.search_btn.setObjectName("Primary")
        self.search_btn.setMinimumHeight(50)
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.setAutoDefault(True)
        self.search_btn.clicked.connect(self._on_search)
        search_lay.addWidget(self.search_btn)
        self.inner.addWidget(self.search_box)

        # -- result state (built once, populated per lookup) --
        self.result_box = QWidget()
        result_lay = QVBoxLayout(self.result_box)
        result_lay.setContentsMargins(0, 0, 0, 0)
        result_lay.setSpacing(4)
        self.result_grid = QGridLayout()
        self.result_grid.setHorizontalSpacing(14)
        self.result_grid.setVerticalSpacing(8)
        result_lay.addLayout(self.result_grid)
        result_lay.addSpacing(20)
        self.start_btn = QPushButton("Commencer l'examen")
        self.start_btn.setObjectName("Primary")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._on_start)
        result_lay.addWidget(self.start_btn)
        self.back_btn = QPushButton("Nouvelle recherche")
        self.back_btn.setObjectName("Secondary")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self._show_search)
        result_lay.addWidget(self.back_btn)
        self.inner.addWidget(self.result_box)
        self.result_box.setVisible(False)

        card_row = QHBoxLayout()
        card_row.addStretch(1)
        card_row.addWidget(self.card)
        card_row.addStretch(1)

        admin = QPushButton("Administration")
        admin.setObjectName("AdminLink")
        admin.setCursor(Qt.CursorShape.PointingHandCursor)
        admin.clicked.connect(self.admin_requested.emit)

        quick_test = QPushButton("Test rapide")
        quick_test.setObjectName("QuickTestLink")
        quick_test.setCursor(Qt.CursorShape.PointingHandCursor)
        quick_test.clicked.connect(self.quick_test_requested.emit)

        admin_row = QHBoxLayout()
        admin_row.addWidget(quick_test)
        admin_row.addStretch(1)
        admin_row.addWidget(admin)

        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(40, 28, 40, 22)
        outer.addStretch(2)
        outer.addWidget(brand)
        outer.addWidget(tagline)
        outer.addSpacing(26)
        outer.addLayout(card_row)
        outer.addStretch(3)
        outer.addLayout(admin_row)

        scroll = QScrollArea()
        scroll.setObjectName("FormScroll")
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    # -- state -----------------------------------------------------------

    def reset(self) -> None:
        self.cin.clear()
        self.error.setVisible(False)
        self._show_search()

    def focus_default(self) -> None:
        if self.search_box.isVisible():
            self.cin.setFocus()
        else:
            self.start_btn.setFocus()

    def _show_search(self) -> None:
        self._candidate = None
        self.result_box.setVisible(False)
        self.search_box.setVisible(True)
        self.cin.setFocus()

    def _show_error(self, msg: str) -> None:
        self.error.setText(msg)
        self.error.setVisible(True)

    # -- search callback, wired by the controller ------------------------

    #: set by the controller to `lambda cin: supabase_service.candidates.find_by_cin(...)`
    lookup_fn = None

    def _on_search(self) -> None:
        cin = self.cin.text().strip().upper()
        self.cin.setText(cin)
        if not cin:
            self._show_error("Veuillez saisir un numéro de CIN.")
            return
        self.error.setVisible(False)
        if self.lookup_fn is None:
            return
        try:
            record = self.lookup_fn(cin)
        except Exception as exc:
            self._show_error(f"Erreur de connexion à la plateforme : {exc}")
            return
        if record is None:
            self._show_error("Candidat introuvable.")
            return
        self._show_result(record)

    def _show_result(self, record: CandidateRecord) -> None:
        self._candidate = record
        while self.result_grid.count():
            item = self.result_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = [
            ("Nom", f"{record.first_name} {record.last_name}"),
            ("CIN", record.cin),
            ("Date de naissance", record.birth_date or "—"),
            ("Sexe", record.sexe or "—"),
            ("Direction régionale", record.region_name or "—"),
            ("Établissement", record.etablissement_name or "—"),
            ("Filière", record.filiere or "—"),
            ("Groupe", record.groupe or "—"),
            ("Version MOS", record.mos_version or "—"),
            ("Session programmée", record.exam_date or "—"),
            ("Heure de passage", record.start_time or "—"),
        ]
        for r, (label_text, value) in enumerate(rows):
            self.result_grid.addWidget(widgets.label(label_text, "FieldLabel"), r, 0)
            self.result_grid.addWidget(widgets.label(value), r, 1)

        self.search_box.setVisible(False)
        self.result_box.setVisible(True)
        self.start_btn.setFocus()

    def _on_start(self) -> None:
        if self._candidate is not None:
            self.candidate_confirmed.emit(self._candidate)
