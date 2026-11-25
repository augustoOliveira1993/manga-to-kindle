"""Paletas acessíveis para os temas claro e escuro."""

from __future__ import annotations

from manga_to_kindle.application.ui.theme_mode import ThemeMode

_LIGHT = """
QMainWindow, QWidget { background: #f4f6f9; color: #202a36; }
QFrame#sidebar { background: #ffffff; border-right: 1px solid #e2e7ee; }
QLabel#brandMark { background: #635bdb; color: white; border-radius: 12px;
  font-size: 18px; font-weight: 800; }
QLabel#pageTitle { font-size: 25px; font-weight: 700; }
QLabel#subtitle { color: #667085; }
QLabel#startupStatus { color: #526174; }
QLabel#simulationBanner { background: #fff4d6; color: #633d00; border: 1px solid #f2d58a;
  border-radius: 8px; padding: 9px 12px; font-weight: 650; }
QFrame#surface, QFrame#emptyState, QFrame#jobPanel { background: #ffffff;
  border: 1px solid #e2e7ee; border-radius: 14px; }
QPushButton, QToolButton { background: #ffffff; border: 1px solid #d9e0e8;
  border-radius: 8px; padding: 8px 12px; }
QPushButton:hover, QToolButton:hover { border-color: #635bdb; background: #f8f7ff; }
QPushButton:checked { background: #efedff; color: #4338a7; border-color: #b8b2ff; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QListWidget:focus {
  border: 2px solid #635bdb; }
QPushButton[primaryAction="true"] { background: #635bdb; color: white;
  border: 0; font-weight: 650; }
QPushButton[primaryAction="true"]:hover { background: #5148c6; }
QLineEdit, QComboBox, QListWidget { background: #ffffff; border: 1px solid #d9e0e8;
  border-radius: 8px; padding: 8px; }
QListWidget::item { padding: 8px; border-radius: 6px; }
QListWidget::item:selected { background: #efedff; color: #332b8c; }
QProgressBar { border: 1px solid #d9e0e8; background: #edf0f5; border-radius: 6px;
  min-height: 12px; text-align: center; }
QProgressBar::chunk { background: #635bdb; border-radius: 5px; }
QLabel#eyebrow { color: #635bdb; font-weight: 700; letter-spacing: 1px; }
QLabel#muted { color: #667085; }
"""

_DARK = """
QMainWindow, QWidget { background: #151a22; color: #e8edf5; }
QFrame#sidebar { background: #1b222d; border-right: 1px solid #303b49; }
QLabel#brandMark { background: #827aff; color: #111322; border-radius: 12px;
  font-size: 18px; font-weight: 800; }
QLabel#pageTitle { font-size: 25px; font-weight: 700; }
QLabel#subtitle, QLabel#muted, QLabel#startupStatus { color: #a9b4c4; }
QLabel#simulationBanner { background: #3c321b; color: #f6df9b; border: 1px solid #7d6834;
  border-radius: 8px; padding: 9px 12px; font-weight: 650; }
QFrame#surface, QFrame#emptyState, QFrame#jobPanel { background: #1d2530;
  border: 1px solid #303b49; border-radius: 14px; }
QPushButton, QToolButton { background: #202a36; border: 1px solid #3a4656;
  border-radius: 8px; padding: 8px 12px; color: #e8edf5; }
QPushButton:hover, QToolButton:hover { border-color: #827aff; background: #282d43; }
QPushButton:checked { background: #302d57; color: #d4d0ff; border-color: #7069d9; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QListWidget:focus {
  border: 2px solid #a39dff; }
QPushButton[primaryAction="true"] { background: #827aff; color: #111322;
  border: 0; font-weight: 650; }
QPushButton[primaryAction="true"]:hover { background: #a39dff; }
QLineEdit, QComboBox, QListWidget { background: #171e27; border: 1px solid #3a4656;
  border-radius: 8px; padding: 8px; color: #e8edf5; }
QListWidget::item { padding: 8px; border-radius: 6px; }
QListWidget::item:selected { background: #302d57; color: #f2f0ff; }
QProgressBar { border: 1px solid #3a4656; background: #171e27; border-radius: 6px;
  min-height: 12px; text-align: center; }
QProgressBar::chunk { background: #827aff; border-radius: 5px; }
QLabel#eyebrow { color: #a39dff; font-weight: 700; letter-spacing: 1px; }
"""


def stylesheet_for(theme: ThemeMode) -> str:
    return _DARK if theme == "dark" else _LIGHT

