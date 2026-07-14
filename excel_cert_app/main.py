"""Entry point for the Excel certification app.

Usage:
    python main.py            # normal, kiosk-locked run
    python main.py --unlock   # release any stale kiosk lock and exit (recovery)
    python main.py --no-resume  # ignore an interrupted session on startup
"""
from __future__ import annotations

import argparse
import os
import sys


def _prefer_xwayland() -> None:
    """On Linux/Wayland, Qt clients cannot position their own frameless windows,
    so the bottom task panel would float in the middle of the screen. XWayland
    (the ``xcb`` platform) honours absolute ``setGeometry`` positioning, so we
    select it when running under Wayland unless the user forced a platform.
    No effect on Windows/macOS or when QT_QPA_PLATFORM is already set."""
    if not sys.platform.startswith("linux"):
        return
    if os.environ.get("QT_QPA_PLATFORM"):
        return
    if os.environ.get("WAYLAND_DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"


_prefer_xwayland()

from PyQt6.QtWidgets import QApplication  # noqa: E402

from app import config  # noqa: E402
from app.ui.app_controller import AppController  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulateur de certification Excel")
    parser.add_argument("--unlock", action="store_true",
                        help="Libère un verrou kiosk résiduel puis quitte.")
    parser.add_argument("--no-resume", action="store_true",
                        help="Ignore une session interrompue au démarrage.")
    args = parser.parse_args()

    if args.unlock:
        from app import kiosk

        lock = kiosk.create_lock()
        lock.engaged = True
        lock.release()
        print("Verrou libéré.")
        return 0

    config.ensure_runtime_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setOrganizationName(config.ORG_NAME)

    controller = AppController(app)
    controller.start(resume=not args.no_resume)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
