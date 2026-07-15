"""Top-level application controller.

Owns the windows, the exam session, the Excel controller and the kiosk lock,
and drives the transitions between screens. Fullscreen screens live in a
stacked main window; during a project the main window hides and Excel fills
the whole screen, with the task panel available on demand via a small
floating handle.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QRect, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolBar,
    QWidget,
)

from .. import config, excel, kiosk
from ..db import results_export
from ..db.dao import Database
from ..exam.session import ExamSession, ExamState
from ..exam import variants, workdir
from . import theme
from .admin_dialog import AdminCodeDialog, AdminSetupDialog
from .system_check import SystemCheckScreen
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
        self._theme_mode = self.db.get_setting("theme") or theme.system_default_mode()
        theme.apply_theme(self.app, self._theme_mode)
        self.excel = excel.create_controller()
        self.lock = kiosk.create_lock()
        self.lock.on_escape = self._on_escape
        self.session = ExamSession(self.db)

        self._last_autosave = 0

        # -- screens --
        self.stack = QStackedWidget()
        self.system_check = SystemCheckScreen()
        self.registration = RegistrationScreen()
        self.instructions = InstructionsScreen()
        self.review = ReviewBoard()
        self.results = ResultsScreen()
        for w in (self.system_check, self.registration, self.instructions,
                  self.review, self.results):
            self.stack.addWidget(w)

        self.main = QMainWindow()
        self.main.setWindowTitle(config.APP_NAME)
        self.main.setCentralWidget(self.stack)
        self._build_quit_toolbar()

        self.panel = TaskPanel()
        self.panel.session = self.session
        self.panel.set_theme_label(self._theme_label())
        self._build_panel_handle()
        self._build_backdrop()

        # -- signals --
        self.system_check.ready.connect(self._on_system_check_passed)
        self.system_check.quit_requested.connect(self._confirm_quit)
        self.registration.submitted.connect(self._on_registered)
        self.registration.admin_requested.connect(lambda: self._open_admin(False))
        self.registration.quick_test_requested.connect(self._on_quick_test)
        self.instructions.start_clicked.connect(self._on_start)
        self.panel.submit_project.connect(self._on_submit_project)
        self.panel.logout_requested.connect(lambda: self._open_admin(True))
        self.panel.quit_requested.connect(self._confirm_quit)
        self.panel.theme_toggle_requested.connect(self._toggle_theme)
        self.panel.hide_requested.connect(self._hide_panel)
        self.panel.refresh_requested.connect(self._on_refresh_excel)
        self.review.reopen_project.connect(self._on_reopen)
        self.review.finish_test.connect(self._on_finish)
        self.results.next_candidate.connect(self._on_next_candidate)

        # -- timers --
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._tick_clock)
        self.watchdog = QTimer()
        self.watchdog.timeout.connect(self._tick_watchdog)

    # -- chrome --------------------------------------------------------------

    def _build_quit_toolbar(self) -> None:
        """Persistent top bar with a theme toggle and a Quit button, visible
        on every screen shown in the main window (registration, instructions,
        review, results)."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        self.theme_btn = QPushButton(self._theme_label())
        self.theme_btn.setObjectName("ThemeToggle")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        toolbar.addWidget(self.theme_btn)
        quit_btn = QPushButton("✕")
        quit_btn.setObjectName("QuitIcon")
        quit_btn.setToolTip("Quitter")
        quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_btn.clicked.connect(self._confirm_quit)
        toolbar.addWidget(quit_btn)
        self.main.addToolBar(toolbar)

    def _build_panel_handle(self) -> None:
        """Small floating handle that stays on screen when the task panel is
        hidden, so Excel can take the full screen without losing the way
        back to the panel."""
        self.panel_handle = QPushButton("▲ Afficher le panneau")
        self.panel_handle.setObjectName("PanelHandle")
        self.panel_handle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.panel_handle.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.panel_handle.clicked.connect(self._restore_panel)

    def _build_backdrop(self) -> None:
        """Full-screen black window shown behind Excel while the task panel
        is hidden, so no desktop/taskbar shows through around the edges."""
        self.backdrop = QWidget()
        self.backdrop.setStyleSheet("background-color: #000000;")
        self.backdrop.setWindowFlags(Qt.WindowType.FramelessWindowHint)

    def _theme_label(self) -> str:
        return "☀ Mode clair" if self._theme_mode == "dark" else "🌙 Mode sombre"

    def _toggle_theme(self) -> None:
        self._theme_mode = "light" if self._theme_mode == "dark" else "dark"
        self.db.set_setting("theme", self._theme_mode)
        theme.apply_theme(self.app, self._theme_mode)
        self.theme_btn.setText(self._theme_label())
        if hasattr(self, "panel"):
            self.panel.set_theme_label(self._theme_label())

    # -- geometry ----------------------------------------------------------

    def _screen_rect(self):
        return QGuiApplication.primaryScreen().geometry()

    def _physical_screen_rect(self) -> QRect:
        """Win32 window-placement calls (used to size/move the real Excel
        window) always work in physical pixels, while Qt's own geometry is
        reported in DPI-scaled logical pixels (e.g. 1536x864 logical for a
        1920x1080 monitor at 125% scaling). Convert explicitly so Excel
        actually fills the monitor instead of stopping at the logical size."""
        screen = QGuiApplication.primaryScreen()
        rect = screen.geometry()
        dpr = screen.devicePixelRatio()
        return QRect(
            int(rect.x() * dpr), int(rect.y() * dpr),
            int(rect.width() * dpr), int(rect.height() * dpr),
        )

    def _panel_height(self) -> int:
        """Bottom panel = 1/4 of the screen (Excel gets the top 3/4), minus a
        small buffer handed back to Excel so its sheet-tab strip stays clear
        of the panel even when Excel adds a notification bar of its own."""
        h = int(self._screen_rect().height() * config.PANEL_HEIGHT_FRACTION)
        return max(config.PANEL_MIN_HEIGHT, h) - config.EXCEL_HEIGHT_BUFFER_PX

    def _show_fullscreen(self, widget) -> None:
        self.panel.hide()
        self.panel_handle.hide()
        self.backdrop.hide()
        if self.excel.can_toggle_chrome:
            self.excel.set_chrome_visible(True)
        self.stack.setCurrentWidget(widget)
        self.main.showFullScreen()
        self.main.raise_()
        self.main.activateWindow()
        focus_default = getattr(widget, "focus_default", None)
        if focus_default is not None:
            QTimer.singleShot(0, focus_default)

    def _show_panel(self) -> None:
        self.panel_handle.hide()
        self.backdrop.hide()
        if self.excel.can_toggle_chrome:
            self.excel.set_chrome_visible(True)
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
        # Position Excel above the panel once it has had time to open. Retried
        # a few times since the very first resize attempt can land before the
        # workbook's window is fully ready and get silently ignored.
        if self.excel.can_position:
            for delay_ms in (600, 1200, 2200):
                QTimer.singleShot(delay_ms, self._position_excel)

    def _position_excel(self) -> None:
        rect = self._physical_screen_rect()
        width = int(rect.width() * config.EXCEL_WIDTH_FRACTION)
        height = int(rect.height() * config.EXCEL_HEIGHT_FRACTION)
        try:
            self.excel.position_window(rect.x(), rect.y(), width, height)
        except Exception:
            pass

    def _position_excel_full(self) -> None:
        rect = self._physical_screen_rect()
        try:
            self.excel.position_window(rect.x(), rect.y(), rect.width(), rect.height())
        except Exception:
            pass

    def _hide_panel(self) -> None:
        """Hide the task panel entirely so Excel can take the full screen;
        a small floating handle stays on screen to bring the panel back."""
        self.main.hide()
        self.panel.hide()
        rect = self._screen_rect()
        self.backdrop.setGeometry(rect.x(), rect.y(), rect.width(), rect.height())
        self.backdrop.show()
        self.backdrop.lower()
        if self.excel.can_toggle_chrome:
            self.excel.set_chrome_visible(False)
        handle_w = max(self.panel_handle.sizeHint().width() + 24, 160)
        handle_h = 30
        self.panel_handle.setFixedSize(handle_w, handle_h)
        self.panel_handle.move(
            rect.x() + (rect.width() - handle_w) // 2,
            rect.y() + rect.height() - handle_h,
        )
        self.panel_handle.show()
        self.panel_handle.raise_()
        if self.excel.can_position:
            for delay_ms in (0, 400, 900):
                QTimer.singleShot(delay_ms, self._position_excel_full)

    def _restore_panel(self) -> None:
        self._show_panel()

    # -- startup -----------------------------------------------------------

    def start(self, resume: bool = True) -> None:
        # A previous run left crashed/orphaned or an admin's own EXCEL.EXE
        # lingering never affects the exam (DispatchEx always opens an
        # isolated instance), but it can leave a stray invisible window that
        # confuses window-handle scans (kiosk lock, positioning). Clear the
        # slate on every launch.
        excel.kill_all_excel_processes()

        if not self.db.is_admin_code_set():
            dlg = AdminSetupDialog(self.db)
            if dlg.exec() != dlg.DialogCode.Accepted:
                sys.exit(0)

        self._resume_on_ready = resume
        self._show_fullscreen(self.system_check)
        self.system_check.start_check()

    def _on_system_check_passed(self) -> None:
        self.excel.start()
        self.lock.engage()

        running = self.db.get_running_session() if self._resume_on_ready else None
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

    def _on_registered(self, first, last, cin, birth_date, institution) -> None:
        cid = self.db.create_candidate(first, last, cin, birth_date, institution)
        variant = variants.next_variant(self.db)
        self.session = ExamSession(self.db)
        self.panel.session = self.session
        self.session.create(cid, variant)
        self.instructions.set_candidate(first, last, variant)
        self._show_fullscreen(self.instructions)

    def _on_start(self) -> None:
        self.session.start()
        self._enter_running()

    def _on_quick_test(self) -> None:
        """Bypass registration and instructions with dummy data, for quickly
        exercising the exam flow without filling in any form."""
        cid = self.db.create_candidate(
            "Test", "Rapide", "AB123456", "01/01/2000",
            "INSTITUT SPECIALISE DE TECHNOLOGIE APPLIQUEE TEMARA",
        )
        variant = variants.next_variant(self.db)
        self.session = ExamSession(self.db)
        self.panel.session = self.session
        self.session.create(cid, variant)
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
        path = Path(sp.workfile_path)
        if not path.exists():
            # The work file can go missing (moved/deleted, or a resumed
            # session from a previous, since-archived run) — regenerate a
            # fresh copy from the pristine project template rather than
            # letting Workbooks.Open blow up.
            path = workdir.prepare_project(self.session.session_id, sp.project_no)
        try:
            self.excel.open_project(path)
        except Exception as exc:
            self.db.audit("excel_open_error", self.session.session_id, str(exc))
            QMessageBox.critical(
                self.main, "Erreur Excel",
                f"Impossible d'ouvrir le fichier du projet {sp.project_no} dans "
                f"Excel :\n\n{exc}\n\nVérifiez que Microsoft Excel fonctionne "
                "correctement, puis contactez l'administrateur si le problème "
                "persiste.",
            )

    def _on_refresh_excel(self) -> None:
        """Manual recovery: kill every Excel process and relaunch the
        current project's work file from scratch (e.g. Excel froze or
        misbehaved). Mirrors the watchdog's crash-recovery path, without
        attempting to save the (possibly unresponsive) workbook first."""
        box = QMessageBox(self.panel)
        box.setWindowTitle("Redémarrer Excel")
        box.setText("Fermer et relancer Excel ? Les modifications non "
                    "enregistrées depuis la dernière sauvegarde automatique "
                    "seront perdues.")
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return

        try:
            self.excel.shutdown()
        except Exception:
            pass
        excel.kill_all_excel_processes()
        self.excel.start()
        self._open_current_project()
        if self.panel.isVisible():
            self._show_panel()
        else:
            self._hide_panel()

    def _on_submit_project(self) -> None:
        try:
            self.excel.force_save()
        except Exception as exc:
            self.db.audit("save_error", self.session.session_id, str(exc))
        self.session.submit_current()
        if self.session.advance_after_submit():
            self._open_current_project()
            self.panel.load_project()
            self._show_panel()
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
                cin=cand.cin, birth_date=cand.birth_date,
                institution=cand.institution, variant=self.session.variant,
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
        for w in (self.panel, self.main, self.panel_handle, self.backdrop):
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

    def _confirm_quit(self) -> None:
        parent = self.panel if self.panel.isVisible() else self.main
        box = QMessageBox(parent)
        box.setWindowTitle("Quitter l'application")
        box.setText("Voulez-vous vraiment quitter l'application ?"
                    + (" La session en cours sera abandonnée." if self.panel.isVisible() else ""))
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.db.audit("direct_quit", self.session.session_id)
            self._quit()

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
