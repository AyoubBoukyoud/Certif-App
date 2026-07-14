"""Candidate registration screen (S1)."""
from __future__ import annotations

import re

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import widgets

CIN_RE = re.compile(r"^[A-Z]{1,2}[0-9]{4,8}$")

INSTITUTIONS = [
    "INSTITUT SPECIALISE DE TECHNOLOGIE APPLIQUEE AIN AOUDA",
    "INSTITUT SPECIALISE DE TECHNOLOGIE APPLIQUEE AIN ATIQ",
    "INSTITUT SPECIALISE DE TECHNOLOGIE APPLIQUEE MULTISECTORIEL TEMARA",
    "INSTITUT SPECIALISE DE TECHNOLOGIE APPLIQUEE TEMARA",
]


def _field(label_text: str, editor: QLineEdit) -> QWidget:
    """A label stacked above its input, returned as one widget."""
    box = QVBoxLayout()
    box.setSpacing(6)
    box.setContentsMargins(0, 0, 0, 0)
    box.addWidget(widgets.label(label_text, "FieldLabel"))
    box.addWidget(editor)
    wrap = QWidget()
    wrap.setLayout(box)
    return wrap


class RegistrationScreen(QWidget):
    submitted = pyqtSignal(str, str, str, str)  # first, last, cin, phone
    admin_requested = pyqtSignal()
    quick_test_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Screen")
        self._warned = False
        self._build()

    def _build(self) -> None:
        # ---- Header brand (above the card) ----
        brand = widgets.label("MOS", "Brand", Qt.AlignmentFlag.AlignCenter)
        tagline = widgets.label("Microsoft Office Specialist",
                                "Tagline", Qt.AlignmentFlag.AlignCenter)

        # ---- Card ----
        card = widgets.card()
        card.setMaximumWidth(560)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(44, 38, 44, 34)
        inner.setSpacing(0)

        badge = widgets.label("X", "BrandBadge", Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(60, 60)
        badge_row = QHBoxLayout()
        badge_row.addStretch(1)
        badge_row.addWidget(badge)
        badge_row.addStretch(1)
        inner.addLayout(badge_row)
        inner.addSpacing(18)

        inner.addWidget(widgets.label("Certification Excel 2016", "CardTitle",
                                      Qt.AlignmentFlag.AlignCenter))
        inner.addSpacing(6)
        inner.addWidget(widgets.label(
            "Renseignez vos informations pour commencer l'examen.",
            "CardSubtitle", Qt.AlignmentFlag.AlignCenter))
        inner.addSpacing(28)

        self.first = QLineEdit(placeholderText="Prénom")
        self.last = QLineEdit(placeholderText="Nom")
        self.cin = QLineEdit(placeholderText="AB123456")
        self.phone = QLineEdit(placeholderText="0612345678")
        for e in (self.first, self.last, self.cin, self.phone):
            e.setMinimumHeight(44)
            e.setClearButtonEnabled(True)
            e.returnPressed.connect(self._on_submit)

        name_row = QHBoxLayout()
        name_row.setSpacing(16)
        name_row.addWidget(_field("Prénom", self.first))
        name_row.addWidget(_field("Nom", self.last))
        inner.addLayout(name_row)
        inner.addSpacing(16)
        inner.addWidget(_field("Numéro de CIN", self.cin))
        inner.addSpacing(16)
        inner.addWidget(_field("Numéro de téléphone", self.phone))

        self.error = widgets.label("", "ErrorBanner")
        self.error.setVisible(False)
        inner.addSpacing(8)
        inner.addWidget(self.error)

        inner.addSpacing(24)
        self.start_btn = QPushButton("Commencer l'examen")
        self.start_btn.setObjectName("Primary")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setAutoDefault(True)
        self.start_btn.clicked.connect(self._on_submit)
        inner.addWidget(self.start_btn)

        card_row = QHBoxLayout()
        card_row.addStretch(1)
        card_row.addWidget(card)
        card_row.addStretch(1)

        # ---- Admin entry (discreet, bottom-right) ----
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

        # ---- Keyboard navigation: Tab walks the form top to bottom ----
        self.setTabOrder(self.first, self.last)
        self.setTabOrder(self.last, self.cin)
        self.setTabOrder(self.cin, self.phone)
        self.setTabOrder(self.phone, self.start_btn)
        self.setTabOrder(self.start_btn, quick_test)
        self.setTabOrder(quick_test, admin)

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

        # ---- Scroll wrapper: guarantees every element stays reachable
        # even if the window is smaller than the content needs. ----
        scroll = QScrollArea()
        scroll.setObjectName("FormScroll")
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def reset(self) -> None:
        for e in (self.first, self.last, self.cin, self.phone):
            e.clear()
        self.error.clear()
        self.error.setVisible(False)
        self._warned = False

    def focus_default(self) -> None:
        self.first.setFocus()

    def _show_error(self, msg: str) -> None:
        self.error.setText(msg)
        self.error.setVisible(True)

    def _on_submit(self) -> None:
        first = self.first.text().strip()
        last = self.last.text().strip()
        cin = self.cin.text().strip().upper()
        phone = self.phone.text().strip()
        self.cin.setText(cin)

        if not (first and last and cin and phone):
            self._show_error("Tous les champs sont obligatoires.")
            return
        warnings = []
        if not CIN_RE.match(cin):
            warnings.append("le format du CIN semble incorrect")
        if not PHONE_RE.match(phone):
            warnings.append("le format du téléphone semble incorrect")
        # Warnings are non-blocking: confirm once, then allow.
        if warnings and not self._warned:
            self._show_error("Attention : " + ", ".join(warnings)
                             + ". Cliquez à nouveau pour continuer.")
            self._warned = True
            return
        self._warned = False
        self.error.setVisible(False)
        self.submitted.emit(first, last, cin, phone)
