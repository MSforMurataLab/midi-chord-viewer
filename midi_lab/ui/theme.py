# -*- coding: utf-8 -*-
"""Studio Graphite — プロフェッショナルグレー UI テーマ。"""
from __future__ import annotations

import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from midi_lab.ui import design_tokens as t


def _build_app_stylesheet() -> str:
    return f"""
/* ═══════════════════════════════════════════════════════════════
   MIDI Chord Lab — Studio Graphite
   ═══════════════════════════════════════════════════════════════ */

QMainWindow, QWidget {{
    color: {t.TEXT_PRIMARY};
    font-size: 13px;
    font-family: "Segoe UI", "Yu Gothic UI", "Meiryo UI", sans-serif;
}}

QWidget#AppRoot {{
    background: {t.BG_APP};
}}

/* ── ヘッダー ── */
QFrame#AppHeader {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 12px;
    min-height: 72px;
}}
QFrame#LogoMark {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #e4e4e8, stop:1 #9a9aa6);
    border-radius: 12px;
    border: 1px solid {t.BORDER_STRONG};
}}
QLabel#LogoMarkText {{
    color: #1a1a1d;
    font-size: 16px;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: transparent;
}}
QLabel#HeaderTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 0.2px;
    background: transparent;
}}
QLabel#HeaderSubtitle {{
    color: {t.TEXT_MUTED};
    font-size: 11px;
    font-weight: 500;
    background: transparent;
}}
QLabel#HeaderBadge {{
    background: {t.BG_CARD};
    color: {t.TEXT_SECONDARY};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}
QLabel#HeaderBadgeActive {{
    background: {t.ACCENT_SOFT};
    color: {t.ACCENT_HOVER};
    border: 1px solid {t.ACCENT_GLOW};
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QPushButton#HeaderToolButton {{
    background: {t.BG_CARD};
    color: {t.TEXT_SECONDARY};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 8px;
    font-size: 15px;
    padding: 0;
}}
QPushButton#HeaderToolButton:hover {{
    background: {t.BG_HOVER};
    color: {t.TEXT_PRIMARY};
    border-color: {t.BORDER_STRONG};
}}
QPushButton#HeaderToolButton:pressed {{
    background: {t.ACCENT};
    color: #ffffff;
    border-color: {t.ACCENT};
}}

/* ── サイドバー ── */
QFrame#Sidebar {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 12px;
}}
QFrame#SidebarDivider {{
    background: {t.BORDER_SUBTLE};
    border: none;
}}
QScrollArea#SidebarScroll, QWidget#SidebarViewport {{
    background: transparent;
    border: none;
}}
QLabel#SidebarSection {{
    color: {t.TEXT_MUTED};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
    background: transparent;
}}
QLabel#KeyDisplay {{
    color: {t.KEY_DETECT};
    font-size: 14px;
    font-weight: 600;
    padding: 12px 14px;
    background: {t.BG_INPUT};
    border: 1px solid {t.BORDER_DEFAULT};
    border-left: 3px solid {t.KEY_DETECT};
    border-radius: 8px;
}}
QLabel#KeyDisplayHint {{
    color: {t.TEXT_DIM};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 0 4px 6px 4px;
    background: transparent;
}}
QPushButton#NavButton {{
    background: {t.BG_CARD};
    color: {t.TEXT_SECONDARY};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: 8px;
    padding: 0 14px;
    text-align: left;
    font-weight: 500;
    font-size: 12px;
}}
QPushButton#NavButton:hover {{
    background: {t.BG_HOVER};
    border-color: {t.BORDER_DEFAULT};
    color: {t.TEXT_PRIMARY};
}}
QPushButton#NavButton:pressed {{
    background: {t.BG_INPUT};
}}
QPushButton#NavButton:disabled {{
    background: {t.BG_INPUT};
    color: {t.TEXT_DIM};
    border-color: {t.BORDER_SUBTLE};
}}
QPushButton#NavButtonPrimary {{
    background: {t.ACCENT};
    color: #ffffff;
    border: 1px solid {t.ACCENT_PRESSED};
    border-radius: 8px;
    padding: 0 14px;
    font-weight: 600;
    font-size: 12px;
    text-align: left;
}}
QPushButton#NavButtonPrimary:hover {{
    background: {t.ACCENT_HOVER};
    border-color: {t.ACCENT_HOVER};
}}
QPushButton#NavButtonPrimary:disabled {{
    background: {t.BG_CARD};
    color: {t.TEXT_DIM};
    border-color: {t.BORDER_SUBTLE};
}}
QPushButton#NavButtonPlay {{
    background: {t.PLAY};
    color: #0d1f14;
    border: none;
    border-radius: 8px;
    padding: 0 14px;
    font-weight: 600;
    font-size: 12px;
    text-align: left;
}}
QPushButton#NavButtonPlay:hover {{
    background: {t.PLAY_HOVER};
}}
QPushButton#NavButtonPlay:disabled {{
    background: {t.BG_CARD};
    color: {t.TEXT_DIM};
}}
QPushButton#NavButtonStop {{
    background: {t.BG_CARD};
    color: {t.STOP};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 8px;
    padding: 0 14px;
    font-weight: 500;
    font-size: 12px;
    text-align: left;
}}
QPushButton#NavButtonStop:hover {{
    background: {t.STOP_SOFT};
    border-color: {t.STOP};
    color: #fca5a5;
}}
QPushButton#NavButtonStop:disabled {{
    color: {t.TEXT_DIM};
    border-color: {t.BORDER_SUBTLE};
}}
QSpinBox#SidebarTempo {{
    background: {t.BG_INPUT};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 8px;
    padding: 0 10px;
    font-weight: 600;
    font-size: 13px;
}}
QSpinBox#SidebarTempo:disabled {{
    color: {t.TEXT_DIM};
}}

/* ── パネル ── */
QFrame#PanelCard {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 12px;
}}
QFrame#PanelTitleBar {{
    background: {t.BG_CARD};
    border: none;
    border-bottom: 1px solid {t.BORDER_SUBTLE};
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}}
QLabel#PanelTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 600;
    background: transparent;
}}
QLabel#PanelTitleAccent {{
    color: {t.ACCENT};
    font-size: 16px;
    font-weight: 700;
    background: transparent;
    padding-right: 8px;
}}
QLabel#PanelHint {{
    color: {t.TEXT_MUTED};
    font-size: 11px;
    background: transparent;
}}
QLabel#AssistBadge {{
    background: {t.HARMONY_SOFT};
    color: {t.HARMONY};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}

/* ── タイムライン ── */
QFrame#TimelineStatsBar {{
    background: {t.BG_CARD};
    border: none;
    border-bottom: 1px solid {t.BORDER_SUBTLE};
}}
QLabel#TimelineStats {{
    color: {t.TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 500;
    background: transparent;
}}
QTableWidget#TimelineTable {{
    font-size: 13px;
    font-family: "Consolas", "Cascadia Mono", "Yu Gothic UI", monospace;
}}
QTableWidget#TimelineTable QLineEdit {{
    background-color: {t.BG_INPUT};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.ACCENT};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {t.ACCENT};
    selection-color: #ffffff;
}}

QTableWidget {{
    gridline-color: {t.BORDER_SUBTLE};
    background-color: {t.BG_INPUT};
    alternate-background-color: {t.BG_APP};
    color: {t.TEXT_PRIMARY};
    border: none;
    selection-background-color: {t.ACCENT_SOFT};
    selection-color: {t.TEXT_PRIMARY};
    outline: none;
}}
QTableWidget::item {{
    padding: 10px 12px;
    border-bottom: 1px solid {t.BORDER_SUBTLE};
}}
QTableWidget::item:selected {{
    background-color: {t.ACCENT_SOFT};
    color: {t.TEXT_PRIMARY};
    border-left: 3px solid {t.ACCENT};
}}
QTableWidget::item:hover {{
    background-color: {t.BG_HOVER};
}}
QHeaderView::section {{
    background-color: {t.BG_CARD};
    color: {t.TEXT_SECONDARY};
    padding: 10px 10px;
    border: none;
    border-bottom: 2px solid {t.ACCENT};
    border-right: 1px solid {t.BORDER_SUBTLE};
    font-weight: 600;
    font-size: 11px;
}}

/* ── タブ・リスト ── */
QTabWidget::pane {{
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 0 0 8px 8px;
    background: {t.BG_INPUT};
    top: -1px;
}}
QTabBar::tab {{
    background: {t.BG_CARD};
    color: {t.TEXT_MUTED};
    padding: 10px 18px;
    margin-right: 1px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 500;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: {t.BG_INPUT};
    color: {t.TEXT_PRIMARY};
    border-bottom: 2px solid {t.ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background: {t.BG_HOVER};
    color: {t.TEXT_SECONDARY};
}}

QListWidget {{
    background-color: {t.BG_INPUT};
    color: {t.TEXT_SECONDARY};
    border: none;
    padding: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 11px 12px;
    border-radius: 6px;
    margin: 2px 0;
    border: 1px solid transparent;
}}
QListWidget::item:selected {{
    background: {t.BG_HOVER};
    border-color: {t.BORDER_DEFAULT};
    color: {t.TEXT_PRIMARY};
    border-left: 3px solid {t.ACCENT};
}}
QListWidget::item:hover:!selected {{
    background: {t.BG_CARD};
    border-color: {t.BORDER_SUBTLE};
}}

QSplitter::handle {{
    background: {t.BG_DEEP};
    width: 6px;
    margin: 4px 0;
    border-radius: 3px;
}}
QSplitter::handle:hover {{
    background: {t.ACCENT};
}}

/* ── ウェルカム ── */
QWidget#WelcomePage, QScrollArea#WelcomeScroll, QWidget#WelcomeViewport {{
    background: transparent;
    border: none;
}}
QFrame#WelcomeCard {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 16px;
}}
QFrame#DropZone {{
    background: {t.BG_INPUT};
    border: 1px dashed {t.BORDER_STRONG};
    border-radius: 10px;
}}
QFrame#DropZone:hover {{
    border-color: {t.ACCENT};
    background: {t.ACCENT_SOFT};
}}
QLabel#DropZoneIcon {{
    color: {t.ACCENT};
    font-size: 26px;
    background: transparent;
}}
QLabel#DropZoneText {{
    color: {t.TEXT_SECONDARY};
    font-size: 13px;
    background: transparent;
}}
QLabel#WelcomeIcon {{
    color: {t.TEXT_MUTED};
    font-size: 44px;
    background: transparent;
}}
QLabel#WelcomeTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 24px;
    font-weight: 600;
    background: transparent;
}}
QLabel#WelcomeSubtitle {{
    color: {t.ACCENT};
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
    background: transparent;
}}
QLabel#WelcomeBody {{
    color: {t.TEXT_MUTED};
    font-size: 12px;
    background: transparent;
}}
QFrame#FeatureChip {{
    background: {t.BG_CARD};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: 8px;
}}
QLabel#FeatureChipTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 11px;
    font-weight: 600;
    background: transparent;
}}
QLabel#FeatureChipDesc {{
    color: {t.TEXT_MUTED};
    font-size: 10px;
    background: transparent;
}}

/* ── ピアノバー ── */
QFrame#PianoBar {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 12px;
}}
QLabel#PianoBarTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    background: transparent;
}}
QLabel#PianoBarHint {{
    color: {t.TEXT_MUTED};
    font-size: 10px;
    background: transparent;
}}

QPushButton#BtnPrimary {{
    background: {t.ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 12px 28px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton#BtnPrimary:hover {{
    background: {t.ACCENT_HOVER};
}}
QPushButton#BtnGhost {{
    background: transparent;
    color: {t.TEXT_SECONDARY};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 8px;
    padding: 11px 22px;
    font-weight: 500;
}}
QPushButton#BtnGhost:hover {{
    border-color: {t.ACCENT};
    color: {t.ACCENT_HOVER};
    background: {t.ACCENT_SOFT};
}}

QSpinBox {{
    background: {t.BG_INPUT};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 8px;
    padding: 8px 10px;
    font-weight: 600;
    selection-background-color: {t.ACCENT};
}}
QSpinBox:focus {{
    border-color: {t.ACCENT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {t.BG_CARD};
    border: none;
    width: 18px;
}}

/* ── ローディング ── */
QWidget#LoadingOverlay {{
    background: rgba(20, 20, 22, 0.92);
}}
QFrame#LoadingCard {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 12px;
    min-width: 340px;
}}
QLabel#LoadingTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 16px;
    font-weight: 600;
}}
QLabel#LoadingDetail {{
    color: {t.TEXT_MUTED};
    font-size: 12px;
}}
QWidget#LoadingOverlay QProgressBar {{
    background: {t.BG_INPUT};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 3px;
    max-height: 4px;
}}
QWidget#LoadingOverlay QProgressBar::chunk {{
    background: {t.ACCENT};
    border-radius: 2px;
}}

/* ── メニュー・ステータス ── */
QMenuBar {{
    background: transparent;
    color: {t.TEXT_SECONDARY};
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 6px 12px;
    border-radius: 6px;
}}
QMenuBar::item:selected {{
    background: {t.BG_HOVER};
    color: {t.TEXT_PRIMARY};
}}
QMenu {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    padding: 9px 24px 9px 14px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background: {t.ACCENT_SOFT};
    color: {t.TEXT_PRIMARY};
}}
QMenu::separator {{
    height: 1px;
    background: {t.BORDER_SUBTLE};
    margin: 4px 8px;
}}

QStatusBar {{
    background: {t.BG_DEEP};
    color: {t.TEXT_MUTED};
    border-top: 1px solid {t.BORDER_SUBTLE};
    padding: 5px 14px;
    font-size: 11px;
}}
QLabel#StatusPill {{
    background: {t.BG_CARD};
    color: {t.TEXT_SECONDARY};
    border: 1px solid {t.BORDER_SUBTLE};
    border-radius: 4px;
    padding: 3px 9px;
    font-size: 10px;
    font-weight: 500;
}}

QScrollBar:vertical {{
    background: {t.BG_INPUT};
    width: 8px;
    border-radius: 4px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {t.BORDER_STRONG};
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {t.BG_INPUT};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {t.BORDER_STRONG};
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t.ACCENT};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QMessageBox {{
    background-color: {t.BG_ELEVATED};
}}
QMessageBox QLabel {{
    color: {t.TEXT_PRIMARY};
}}
QMessageBox QPushButton {{
    background: {t.BG_CARD};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 8px;
    padding: 9px 20px;
    min-width: 72px;
    font-weight: 500;
}}
QMessageBox QPushButton:hover {{
    border-color: {t.ACCENT};
    background: {t.ACCENT_SOFT};
}}

QToolTip {{
    background: {t.BG_CARD};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}
"""


APP_STYLESHEET = _build_app_stylesheet()


def build_splash_stylesheet() -> str:
    return f"""
QWidget#SplashRoot {{
    background-color: {t.BG_DEEP};
}}
QFrame#SplashCard {{
    background: {t.BG_ELEVATED};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 16px;
}}
QFrame#SplashLogo {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #e4e4e8, stop:1 #9a9aa6);
    border-radius: 14px;
    min-width: 56px;
    max-width: 56px;
    min-height: 56px;
    max-height: 56px;
    border: 1px solid {t.BORDER_STRONG};
}}
QLabel#SplashLogoText {{
    color: #1a1a1d;
    font-size: 18px;
    font-weight: 800;
    background: transparent;
}}
QLabel#SplashTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 24px;
    font-weight: 600;
    background: transparent;
}}
QLabel#SplashSubtitle {{
    color: {t.ACCENT};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    background: transparent;
}}
QLabel#SplashStatus {{
    color: {t.TEXT_MUTED};
    font-size: 12px;
    background: transparent;
}}
QLabel#SplashVersion {{
    color: {t.TEXT_DIM};
    font-size: 10px;
    font-weight: 500;
    background: transparent;
}}
QProgressBar {{
    background-color: {t.BG_INPUT};
    border: 1px solid {t.BORDER_DEFAULT};
    border-radius: 3px;
    min-height: 4px;
    max-height: 4px;
}}
QProgressBar::chunk {{
    background: {t.ACCENT};
    border-radius: 2px;
}}
"""


SPLASH_STYLESHEET = build_splash_stylesheet()


def apply_app_font(app: QApplication) -> None:
    if sys.platform == "win32":
        family = "Segoe UI"
    elif sys.platform == "darwin":
        family = ".AppleSystemUIFont"
    else:
        family = "Noto Sans"
    font = QFont(family, 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)
