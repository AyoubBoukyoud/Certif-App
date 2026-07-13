"""Top-level application controller.

Owns the windows, the exam session, the Excel controller and the kiosk lock,
and drives the transitions between screens. Fullscreen screens live in a
stacked main window; during a project the main window hides and the bottom
task panel is shown with Excel filling the space above it.
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
)

from .. import config, excel, kiosk
from ..db import results_export
from ..db.dao import Database
from ..exam.session import ExamSession, ExamState
from ..exam import variants, workdir
from .admin_dialog import AdminCodeDialog, AdminSetupDialog
from .instructions import InstructionsScreen
from .registration import RegistrationScreen
from .results import ResultsScreen
from .review_board import ReviewBoard
from .task_panel import TaskPanel

_WATCHDOG_MS = 700
_CLOCK_MS = 1000
_AUTOSAVE_S = 60


class AppController:
    def __init__(self, app: QApplication) -> None:
        self.app = app
        config.ensure_runtime_dirs()
        self.db = Database()
        self.excel = excel.create_controller()
        self.lock = kiosk.create_lock()
        self.lock.on_escape = self._on_escape
        self.session = ExamSession(self.db)

        self._last_autosave = 0

        # -- screens --
        self.stack = QStackedWidget()
        self.registration = RegistrationScreen()
        self.instructions = InstructionsScreen()
        self.review = ReviewBoard()
        self.results = ResultsScreen()
        for w in (self.registration, self.instructions, self.review, self.results):
            self.stack.addWidget(w)

        self.main = QMainWindow()
        self.main.setWindowTitle(config.APP_NAME)
        self.main.setCentralWidget(self.stack)

        self.panel = TaskPanel()
        self.panel.session = self.session

        # -- signals --
        self.registration.submitted.connect(self._on_registered)
        self.registration.admin_requested.connect(lambda: self._open_admin(False))
        self.instructions.start_clicked.connect(self._on_start)
        self.panel.submit_project.connect(self._on_submit_project)
        self.panel.logout_requested.connect(lambda: self._open_admin(True))
        self.review.reopen_project.connect(self._on_reopen)
        self.review.finish_test.connect(self._on_finish)
        self.results.next_candidate.connect(self._on_next_candidate)

        # -- timers --
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._tick_clock)
        self.watchdog = QTimer()
        self.watchdog.timeout.connect(self._tick_watchdog)

    # -- geometry ----------------------------------------------------------

    def _screen_rect(self):
        return QGuiApplication.primaryScreen().geometry()

    def _panel_height(self) -> int:
        """Bottom panel = 1/4 of the screen (Excel gets the top 3/4)."""
        h = int(self._screen_rect().height() * config.PANEL_HEIGHT_FRACTION)
        return max(config.PANEL_MIN_HEIGHT, h)

    def _show_fullscreen(self, widget) -> None:
        self.panel.hide()
        self.stack.setCurrentWidget(widget)
        self.main.showFullScreen()
        self.main.raise_()
        self.main.activateWindow()

    def _show_panel(self) -> None:
        rect = self._screen_rect()
        panel_h = self._panel_height()
        self.main.hide()
        self.panel.setFixedHeight(panel_h)
        self.panel.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.panel.setGeometry(
            rect.x(), rect.y() + rect.height() - panel_h,
            rect.width(), panel_h,
        )
        self.panel.show()
        self.panel.raise_()
        # Position Excel above the panel once it has had time to open.
        if self.excel.can_position:
            QTimer.singleShot(1200, self._position_excel)

    def _position_excel(self) -> None:
        rect = self._screen_rect()
        panel_h = self._panel_height()
        try:
            self.excel.position_window(
                rect.x(), rect.y(), rect.width(),
                rect.height() - panel_h,
            )
        except Exception:
            pass

    # -- startup -----------------------------------------------------------

    def start(self, resume: bool = True) -> None:
        if not self.db.is_admin_code_set():
            dlg = AdminSetupDialog(self.db)
            if dlg.exec() != dlg.DialogCode.Accepted:
                sys.exit(0)

        self.excel.start()
        self.lock.engage()

        running = self.db.get_running_session() if resume else None
        if running:
            self._prompt_resume(running.id)
        else:
            self._goto_registration()

    def _prompt_resume(self, session_id: int) -> None:
        s = self.db.get_session(session_id)
        cand = self.db.get_candidate(s.candidate_id)
        box = QMessageBox()
        box.setWindowTitle("Reprendre la session")
        box.setText(f"Une session de {cand.first_name} {cand.last_name} est en "
                    "cours. La reprendre ?")
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.session.resume(session_id)
            self._enter_running()
        else:
            self.session.abort()
            workdir.archive_session(session_id)
            self.session = ExamSession(self.db)
            self.panel.session = self.session
            self._goto_registration()

    def _goto_registration(self) -> None:
        self.clock_timer.stop()
        self.watchdog.stop()
        self.registration.reset()
        self._show_fullscreen(self.registration)

    # -- flow --------------------------------------------------------------

    def _on_registered(self, first, last, cin, phone) -> None:
        cid = self.db.create_candidate(first, last, cin, phone)
        variant = variants.next_variant(self.db)
        self.session = ExamSession(self.db)
        self.panel.session = self.session
        self.session.create(cid, variant)
        self.instructions.set_candidate(first, last, variant)
        self._show_fullscreen(self.instructions)

    def _on_start(self) -> None:
        self.session.start()
        self._enter_running()

    def _enter_running(self) -> None:
        self.session.state = ExamState.RUNNING
        self._open_current_project()
        self.panel.load_project()
        self._show_panel()
        self.watchdog.start(_WATCHDOG_MS)
        self.clock_timer.start(_CLOCK_MS)
        self._tick_clock()

    def _open_current_project(self) -> None:
        sp = self.session.current_session_project()
        self.excel.open_project(sp.workfile_path)

    def _on_submit_project(self) -> None:
        try:
            self.excel.force_save()
        except Exception as exc:
            self.db.audit("save_error", self.session.session_id, str(exc))
        self.session.submit_current()
        if self.session.advance_after_submit():
            self._open_current_project()
            self.panel.load_project()
            if self.excel.can_position:
                QTimer.singleShot(1000, self._position_excel)
        else:
            self._enter_review()

    def _enter_review(self) -> None:
        self.excel.close_workbook(save=True)
        self.session.state = ExamState.REVIEWING
        if self.session.remaining_seconds() <= 0:
            self._on_finish()
            return
        self.review.session = self.session
        self.review.refresh()
        self._show_fullscreen(self.review)

    def _on_reopen(self, project_no: int) -> None:
        self.session.reopen(project_no)
        self._open_current_project()
        self.panel.load_project()
        self._show_panel()

    def _on_finish(self) -> None:
        self.clock_timer.stop()
        try:
            self.excel.force_save()
            self.excel.close_workbook(save=True)
        except Exception:
            pass
        self.app.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = self.session.grade()
        finally:
            self.app.restoreOverrideCursor()

        cand = self.session.candidate
        results_path = self.db.get_setting("results_xlsx_path", "resultats.xlsx")
        try:
            written = results_export.append_result(
                config.DATA_DIR / results_path if not str(results_path).startswith("/")
                else results_path,
                first_name=cand.first_name, last_name=cand.last_name,
                cin=cand.cin, phone=cand.phone, variant=self.session.variant,
                duration_s=self.session.elapsed_seconds(),
                score_pct=result.score_pct, passed=result.passed,
            )
            self.db.audit("results_exported", self.session.session_id, str(written))
        except Exception as exc:
            self.db.audit("results_export_error", self.session.session_id, str(exc))

        titles = {pno: self.session.projects[pno].title
                  for pno in self.session.project_nos}
        self.results.show_result(result, self.session.pass_threshold, titles)
        self._show_fullscreen(self.results)

    def _on_next_candidate(self) -> None:
        self.session.cleanup()
        self.session = ExamSession(self.db)
        self.panel.session = self.session
        self._goto_registration()

    # -- timers ------------------------------------------------------------

    def _tick_clock(self) -> None:
        remaining = self.session.remaining_seconds()
        self.panel.update_clock(remaining)
        if remaining <= 0 and self.session.state in (
            ExamState.RUNNING, ExamState.REVIEWING
        ):
            self.clock_timer.stop()
            QMessageBox.information(self.panel, "Temps écoulé",
                                    "Le temps est écoulé. Le test va être corrigé.")
            self._on_finish()
            return
        # periodic autosave during a project
        if self.session.state == ExamState.RUNNING:
            elapsed = self.session.elapsed_seconds()
            if elapsed - self._last_autosave >= _AUTOSAVE_S:
                self._last_autosave = elapsed
                try:
                    self.excel.force_save()
                except Exception:
                    pass

    def _tick_watchdog(self) -> None:
        if not self.excel.is_alive() and self.session.state == ExamState.RUNNING:
            # Excel crashed — relaunch and reopen the current work file.
            self.db.audit("excel_crash", self.session.session_id)
            try:
                self.excel.start()
                self._open_current_project()
            except Exception:
                pass
        allowed = self._allowed_hwnds()
        self.lock.enforce(allowed)

    def _allowed_hwnds(self) -> list[int]:
        hwnds: list[int] = []
        if hasattr(self.excel, "excel_window_handles"):
            try:
                hwnds.extend(self.excel.excel_window_handles())
            except Exception:
                pass
        for w in (self.panel, self.main):
            try:
                hwnds.append(int(w.winId()))
            except Exception:
                pass
        return hwnds

    # -- admin / escape ----------------------------------------------------

    def _on_escape(self, detail: str) -> None:
        self.db.audit("escape_attempt", self.session.session_id, detail)

    def _open_admin(self, in_exam: bool) -> None:
        parent = self.panel if in_exam and self.panel.isVisible() else self.main
        dlg = AdminCodeDialog(self.db, in_exam, parent)
        dlg.exec()
        action = dlg.result_action
        if action == "quit":
            self._quit()
        elif action == "abort" and in_exam:
            self.session.abort()
            self.session.cleanup()
            self.session = ExamSession(self.db)
            self.panel.session = self.session
            self.clock_timer.stop()
            self.watchdog.stop()
            self._goto_registration()
        elif action == "settings":
            AdminSetupDialog(self.db, parent).exec()
        elif action == "export":
            QMessageBox.information(parent, "Export",
                                    "Les résultats sont enregistrés après chaque test.")

    def _quit(self) -> None:
        self.clock_timer.stop()
        self.watchdog.stop()
        self.lock.release()
        try:
            self.excel.shutdown()
        except Exception:
            pass
        self.db.close()
        self.app.quit()
