"""Admin / logout dialogs.

- ``AdminSetupDialog``: first-run creation of the secret code + settings.
- ``AdminCodeDialog``: enter the secret code (with attempt lock-out) to reach
  the admin menu, then choose an action.
"""
from __future__ import annotations

import time

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ..db.dao import Database

_MAX_ATTEMPTS = 3
_LOCKOUT_S = 30


class AdminSetupDialog(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Configuration initiale")
        self.setModal(True)
        self.setMinimumWidth(420)

        form = QFormLayout()
        self.code1 = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.code2 = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.results = QLineEdit(str(db.get_setting("results_xlsx_path",
                                                    "resultats.xlsx")))
        self.minutes = QLineEdit(str(db.get_int_setting("exam_minutes", 50)))
        self.threshold = QLineEdit(str(db.get_int_setting("pass_threshold", 85)))
        form.addRow("Code administrateur", self.code1)
        form.addRow("Confirmer le code", self.code2)
        form.addRow("Fichier des résultats", self.results)
        form.addRow("Durée (minutes)", self.minutes)
        form.addRow("Seuil de réussite (%)", self.threshold)

        self.error = QLabel("")
        self.error.setStyleSheet("color:#cf1124;")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self._save)
        buttons.button(QDialogButtonBox.StandardButton.Save).setDefault(True)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Définissez le code administrateur et les paramètres "
                             "de ce poste."))
        lay.addLayout(form)
        lay.addWidget(self.error)
        lay.addWidget(buttons)

        self.code1.setFocus()

    def _save(self) -> None:
        c1, c2 = self.code1.text(), self.code2.text()
        if len(c1) < 4:
            self.error.setText("Le code doit comporter au moins 4 caractères.")
            return
        if c1 != c2:
            self.error.setText("Les deux codes ne correspondent pas.")
            return

        self.db.set_admin_code(c1)
        self.db.set_setting("results_xlsx_path", self.results.text().strip())
        self.db.set_setting("exam_minutes", self.minutes.text().strip() or "50")
        self.db.set_setting("pass_threshold", self.threshold.text().strip() or "85")
        self.accept()


class AdminCodeDialog(QDialog):
    """Returns one of: 'quit', 'abort', 'settings', 'export', or None (cancel)."""

    def __init__(self, db: Database, in_exam: bool, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.result_action: str | None = None
        self._attempts = 0
        self.setWindowTitle("Déconnexion administrateur")
        self.setModal(True)
        self.setMinimumWidth(380)

        self.code = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.code.setPlaceholderText("Code administrateur")
        self.code.returnPressed.connect(self._verify)
        verify = QPushButton("Valider")
        verify.clicked.connect(self._verify)
        self.error = QLabel("")
        self.error.setStyleSheet("color:#cf1124;")

        self.menu = QVBoxLayout()
        self._in_exam = in_exam

        top = QHBoxLayout()
        top.addWidget(self.code)
        top.addWidget(verify)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Saisissez le code pour accéder aux options."))
        lay.addLayout(top)
        lay.addWidget(self.error)
        lay.addLayout(self.menu)

        self.code.setFocus()

    def _verify(self) -> None:
        if self._attempts >= _MAX_ATTEMPTS:
            return
        if self.db.verify_admin_code(self.code.text()):
            self.db.audit("admin_unlock")
            self._show_menu()
        else:
            self._attempts += 1
            self.db.audit("admin_code_fail", detail=f"attempt={self._attempts}")
            remaining = _MAX_ATTEMPTS - self._attempts
            if remaining <= 0:
                self.error.setText(f"Trop de tentatives. Attendez {_LOCKOUT_S}s.")
                self.code.setEnabled(False)
                self._lock_until = time.time() + _LOCKOUT_S
            else:
                self.error.setText(f"Code incorrect. {remaining} tentative(s) restante(s).")

    def _show_menu(self) -> None:
        self.code.setEnabled(False)
        self.error.clear()

        first_btn: QPushButton | None = None

        def make(text, action, obj=""):
            nonlocal first_btn
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            b.setAutoDefault(True)
            b.clicked.connect(lambda: self._choose(action))
            self.menu.addWidget(b)
            if first_btn is None:
                first_btn = b

        if self._in_exam:
            make("Abandonner la session", "abort", "Danger")
        make("Exporter les résultats", "export", "Secondary")
        make("Paramètres", "settings", "Secondary")
        make("Quitter l'application", "quit", "Danger")

        if first_btn is not None:
            first_btn.setFocus()

    def _choose(self, action: str) -> None:
        self.result_action = action
        self.accept()
