"""Écran 3 — Validation du surveillant.

A modal dialog (matches the cahier des charges' "afficher une nouvelle
fenêtre"), styled like the existing admin dialogs (`admin_dialog.py`):
Login + Mot de passe, Valider/Annuler.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from ..supabase_service.auth import SupervisorAuthError, SupervisorIdentity


class SupervisorValidationDialog(QDialog):
    """Returns the validated `SupervisorIdentity` via `self.identity`, or
    None if the candidate cancelled / validation failed and the dialog was
    dismissed."""

    def __init__(self, expected_etablissement_id: str, sign_in_fn, parent=None) -> None:
        super().__init__(parent)
        self._expected_etablissement_id = expected_etablissement_id
        self._sign_in_fn = sign_in_fn  # (login, password, expected_etab_id) -> SupervisorIdentity
        self.identity: SupervisorIdentity | None = None

        self.setWindowTitle("Validation du surveillant")
        self.setModal(True)
        self.setMinimumWidth(420)

        form = QFormLayout()
        self.login = QLineEdit()
        self.login.setPlaceholderText("surveillant@etablissement.ma")
        self.password = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        form.addRow("Login", self.login)
        form.addRow("Mot de passe", self.password)

        self.error = QLabel("")
        self.error.setStyleSheet("color:#cf1124;")
        self.error.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Valider")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self._on_validate)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Un surveillant doit valider ce candidat avant de "
                             "commencer l'examen."))
        lay.addLayout(form)
        lay.addWidget(self.error)
        lay.addWidget(buttons)

        self.login.setFocus()

    def _on_validate(self) -> None:
        login = self.login.text().strip()
        password = self.password.text()
        if not login or not password:
            self.error.setText("Login et mot de passe sont obligatoires.")
            return
        try:
            self.identity = self._sign_in_fn(
                login, password, expected_etablissement_id=self._expected_etablissement_id,
            )
        except SupervisorAuthError as exc:
            self.error.setText(str(exc))
            self.password.clear()
            self.password.setFocus()
            return
        except Exception as exc:
            self.error.setText(f"Erreur de connexion à la plateforme : {exc}")
            return
        self.accept()
