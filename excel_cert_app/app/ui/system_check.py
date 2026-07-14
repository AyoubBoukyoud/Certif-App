"""System pre-flight check screen (S0), shown before registration.

Reports every installed Office app (name, version, build), the Office UI
language and activation status, and the Windows edition/version/activation —
then gates entry to the exam on Excel alone (the other apps are informational,
not required to run the exam).
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import sysinfo
from . import widgets


def _status_label(ok: bool | None, yes: str, no: str, unknown: str = "?") -> QLabel:
    if ok is True:
        lbl = widgets.label(yes, "StatusOk")
    elif ok is False:
        lbl = widgets.label(no, "StatusBad")
    else:
        lbl = widgets.label(unknown, "StatusUnknown")
    return lbl


class SystemCheckScreen(QWidget):
    ready = pyqtSignal()           # Excel found and supported, safe to continue
    quit_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Screen")
        self._checking = False
        self._build()

    # -- layout ---------------------------------------------------------

    def _build(self) -> None:
        title = widgets.label("Vérification du poste", "Title",
                              Qt.AlignmentFlag.AlignCenter)
        subtitle = widgets.label(
            "Détection de Microsoft Office et de Windows avant de démarrer "
            "l'examen.", "Subtitle", Qt.AlignmentFlag.AlignCenter)

        card = widgets.card()
        card.setMaximumWidth(880)
        body = QVBoxLayout(card)
        body.setContentsMargins(36, 30, 36, 30)
        body.setSpacing(6)

        # -- progress strip --
        self.step_lbl = widgets.label("Préparation…", "FieldLabel")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        body.addWidget(self.step_lbl)
        body.addWidget(self.progress)
        body.addSpacing(14)

        # -- Office apps table --
        body.addWidget(widgets.label("Microsoft Office", "CardTitle"))
        self.apps_grid = QGridLayout()
        self.apps_grid.setHorizontalSpacing(22)
        self.apps_grid.setVerticalSpacing(6)
        for col, header in enumerate(["Application", "Statut", "Version", "Build"]):
            self.apps_grid.addWidget(widgets.label(header, "FieldLabel"), 0, col)
        self._app_rows: dict[str, dict[str, QLabel]] = {}
        for row, (key, name) in enumerate(sysinfo.OFFICE_APPS, start=1):
            name_lbl = widgets.label(name)
            status_lbl = widgets.label("…", "StatusUnknown")
            version_lbl = widgets.label("—")
            build_lbl = widgets.label("—")
            self.apps_grid.addWidget(name_lbl, row, 0)
            self.apps_grid.addWidget(status_lbl, row, 1)
            self.apps_grid.addWidget(version_lbl, row, 2)
            self.apps_grid.addWidget(build_lbl, row, 3)
            self._app_rows[key] = {
                "status": status_lbl, "version": version_lbl, "build": build_lbl,
            }
        body.addLayout(self.apps_grid)
        body.addSpacing(10)

        divider1 = QFrame()
        divider1.setFrameShape(QFrame.Shape.HLine)
        body.addWidget(divider1)
        body.addSpacing(10)

        office_info = QGridLayout()
        office_info.setHorizontalSpacing(10)
        office_info.setVerticalSpacing(6)
        office_info.addWidget(widgets.label("Langue du pack Office", "FieldLabel"), 0, 0)
        self.office_lang_lbl = widgets.label("—")
        office_info.addWidget(self.office_lang_lbl, 0, 1)
        office_info.addWidget(widgets.label("Activation Office", "FieldLabel"), 1, 0)
        self.office_activation_lbl = widgets.label("—", "StatusUnknown")
        office_info.addWidget(self.office_activation_lbl, 1, 1)
        self.office_activation_detail = widgets.label("", "CardSubtitle")
        office_info.addWidget(self.office_activation_detail, 2, 0, 1, 2)
        body.addLayout(office_info)
        body.addSpacing(10)

        divider2 = QFrame()
        divider2.setFrameShape(QFrame.Shape.HLine)
        body.addWidget(divider2)
        body.addSpacing(10)

        # -- Windows --
        body.addWidget(widgets.label("Windows", "CardTitle"))
        win_info = QGridLayout()
        win_info.setHorizontalSpacing(10)
        win_info.setVerticalSpacing(6)
        win_info.addWidget(widgets.label("Édition", "FieldLabel"), 0, 0)
        self.win_edition_lbl = widgets.label("—")
        win_info.addWidget(self.win_edition_lbl, 0, 1)
        win_info.addWidget(widgets.label("Version", "FieldLabel"), 1, 0)
        self.win_version_lbl = widgets.label("—")
        win_info.addWidget(self.win_version_lbl, 1, 1)
        win_info.addWidget(widgets.label("Activation", "FieldLabel"), 2, 0)
        self.win_activation_lbl = widgets.label("—", "StatusUnknown")
        win_info.addWidget(self.win_activation_lbl, 2, 1)
        self.win_activation_detail = widgets.label("", "CardSubtitle")
        win_info.addWidget(self.win_activation_detail, 3, 0, 1, 2)
        body.addLayout(win_info)
        body.addSpacing(14)

        self.error = widgets.label("", "ErrorBanner")
        self.error.setVisible(False)
        body.addWidget(self.error)

        self.retry_btn = QPushButton("Relancer les vérifications")
        self.retry_btn.setObjectName("Secondary")
        self.retry_btn.setMinimumHeight(46)
        self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_btn.clicked.connect(self.start_check)

        self.quit_btn = QPushButton("Quitter")
        self.quit_btn.setObjectName("Ghost")
        self.quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.quit_btn.clicked.connect(self.quit_requested.emit)

        self.continue_btn = QPushButton("Continuer")
        self.continue_btn.setObjectName("Primary")
        self.continue_btn.setMinimumHeight(46)
        self.continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.continue_btn.clicked.connect(self.ready.emit)
        self.continue_btn.setVisible(False)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addWidget(self.quit_btn)
        btn_row.addWidget(self.retry_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.continue_btn)
        body.addSpacing(10)
        body.addLayout(btn_row)

        card_row = QHBoxLayout()
        card_row.addStretch(1)
        card_row.addWidget(card)
        card_row.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 26, 30, 26)
        outer.addWidget(title)
        outer.addWidget(subtitle)
        outer.addSpacing(16)
        outer.addLayout(card_row)

    def focus_default(self) -> None:
        if self.continue_btn.isVisible():
            self.continue_btn.setFocus()
        elif self.retry_btn.isEnabled():
            self.retry_btn.setFocus()

    # -- check flow -------------------------------------------------------

    def start_check(self) -> None:
        if self._checking:
            return
        self._checking = True
        self.progress.setVisible(True)
        self.continue_btn.setVisible(False)
        self.error.setVisible(False)
        self.retry_btn.setEnabled(False)
        self.quit_btn.setEnabled(False)
        for widgets_ in self._app_rows.values():
            widgets_["status"].setText("…")
            self._set_status_style(widgets_["status"], None)
            widgets_["version"].setText("—")
            widgets_["build"].setText("—")
        self.office_lang_lbl.setText("—")
        self._set_status_style(self.office_activation_lbl, None)
        self.office_activation_lbl.setText("—")
        self.office_activation_detail.setText("")
        self.win_edition_lbl.setText("—")
        self.win_version_lbl.setText("—")
        self._set_status_style(self.win_activation_lbl, None)
        self.win_activation_lbl.setText("—")
        self.win_activation_detail.setText("")
        # Defer past the current paint so the reset above is visible before
        # the first (blocking) probe runs.
        QTimer.singleShot(50, self._run_check)

    def _set_step(self, text: str) -> None:
        self.step_lbl.setText(text)
        QApplication.processEvents()

    def _set_status_style(self, label: QLabel, ok: bool | None) -> None:
        name = "StatusOk" if ok is True else "StatusBad" if ok is False else "StatusUnknown"
        label.setObjectName(name)
        label.style().unpolish(label)
        label.style().polish(label)

    def _run_check(self) -> None:
        if not sysinfo.is_windows():
            self._set_step("Environnement de développement détecté — vérification "
                           "ignorée.")
            self._finish(excel_supported=True)
            return

        self._set_step("Recherche des applications Microsoft Office…")
        apps = sysinfo.list_office_apps()
        for app in apps:
            row = self._app_rows[app.key]
            ok = app.found
            row["status"].setText("Installé" if ok else "Introuvable")
            self._set_status_style(row["status"], ok)
            row["version"].setText(app.version or (app.note or "—"))
            row["build"].setText(app.build or "—")

        self._set_step("Détection de la langue du pack Office…")
        language = sysinfo.office_language()
        self.office_lang_lbl.setText(language or "Indéterminée")

        self._set_step("Vérification de l'activation Office…")
        sample_path = next((a.path for a in apps if a.found and a.path), None)
        office_activated, office_detail = sysinfo.office_activation(sample_path)
        self.office_activation_lbl.setText(
            "Activé" if office_activated else "Non activé" if office_activated is False
            else "Indéterminé"
        )
        self._set_status_style(self.office_activation_lbl, office_activated)
        self.office_activation_detail.setText(office_detail)

        self._set_step("Vérification de la version de Windows…")
        win = sysinfo.windows_version()
        self.win_edition_lbl.setText(win.product_name or "Indéterminée")
        version_bits = " · ".join(
            v for v in (win.display_version, f"Build {win.build}" if win.build else None)
            if v
        )
        self.win_version_lbl.setText(version_bits or "Indéterminée")

        self._set_step("Vérification de l'activation Windows…")
        win_activated, win_detail = sysinfo.windows_activation()
        self.win_activation_lbl.setText(
            "Activé" if win_activated else "Non activé" if win_activated is False
            else "Indéterminé"
        )
        self._set_status_style(self.win_activation_lbl, win_activated)
        self.win_activation_detail.setText(win_detail)

        excel = next((a for a in apps if a.key == "excel"), None)
        supported = bool(excel and excel.found and excel.version
                         and sysinfo.version_supported(excel.version))
        self._finish(supported)

    def _finish(self, excel_supported: bool) -> None:
        self._checking = False
        self.progress.setVisible(False)
        self.retry_btn.setEnabled(True)
        self.quit_btn.setEnabled(True)
        if excel_supported:
            self.step_lbl.setText("Vérification terminée.")
            self.error.setVisible(False)
            self.continue_btn.setVisible(True)
            self.continue_btn.setFocus()
        else:
            self.step_lbl.setText("Vérification terminée — problème détecté.")
            self.error.setText(
                "L'examen nécessite Microsoft Excel 2016 ou une version plus "
                "récente, installé sur ce poste. Installez ou mettez à jour "
                "Microsoft Excel, puis relancez la vérification."
            )
            self.error.setVisible(True)
            self.continue_btn.setVisible(False)
            self.retry_btn.setFocus()
