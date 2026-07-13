"""Small shared UI helpers."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QColor


def card(parent: QWidget | None = None) -> QFrame:
    frame = QFrame(parent)
    frame.setObjectName("Card")
    shadow = QGraphicsDropShadowEffect(frame)
    shadow.setBlurRadius(40)
    shadow.setColor(QColor(0, 0, 0, 90))
    shadow.setOffset(0, 8)
    frame.setGraphicsEffect(shadow)
    return frame


def label(text: str, object_name: str = "", align=Qt.AlignmentFlag.AlignLeft) -> QLabel:
    lbl = QLabel(text)
    if object_name:
        lbl.setObjectName(object_name)
    lbl.setAlignment(align)
    lbl.setWordWrap(True)
    return lbl


def vbox(*widgets, spacing: int = 12, margins=(0, 0, 0, 0)) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(*margins)
    for w in widgets:
        if isinstance(w, QWidget):
            layout.addWidget(w)
        else:
            layout.addLayout(w)
    return layout
