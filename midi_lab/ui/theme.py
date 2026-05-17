# -*- coding: utf-8 -*-
"""Midnight Studio — アプリケーション全体のビジュアルテーマ。"""
from __future__ import annotations

import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

APP_STYLESHEET = """
/* ═══════════════════════════════════════════════════════════════
   MIDI Chord Lab — Midnight Studio Design System
   ═══════════════════════════════════════════════════════════════ */

QMainWindow, QWidget {
    color: #f4f4f5;
    font-size: 13px;
    font-family: "Segoe UI", "Yu Gothic UI", "Meiryo UI", sans-serif;
}

QWidget#AppRoot {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0a0a10, stop:0.4 #08080e, stop:1 #050508);
}

/* ── ヘッダー ── */
QFrame#AppHeader {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #12121a, stop:0.5 #18181f, stop:1 #12121a);
    border: 1px solid #2a2a38;
    border-radius: 16px;
    min-height: 72px;
}
QFrame#LogoMark {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #fbbf24, stop:0.5 #f59e0b, stop:1 #d97706);
    border-radius: 14px;
    border: 1px solid rgba(251, 191, 36, 0.4);
}
QLabel#LogoMarkText {
    color: #1c1917;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: transparent;
}
QLabel#HeaderTitle {
    color: #fafafa;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.3px;
    background: transparent;
}
QLabel#HeaderSubtitle {
    color: #71717a;
    font-size: 11px;
    font-weight: 500;
    background: transparent;
}
QLabel#HeaderBadge {
    background: rgba(245, 158, 11, 0.12);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel#HeaderBadgeActive {
    background: rgba(52, 211, 153, 0.1);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.35);
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 11px;
    font-weight: 700;
}
QPushButton#HeaderToolButton {
    background: #1a1a22;
    color: #a1a1aa;
    border: 1px solid #32324a;
    border-radius: 12px;
    font-size: 16px;
    font-weight: 600;
    padding: 0;
}
QPushButton#HeaderToolButton:hover {
    background: #252530;
    color: #fbbf24;
    border-color: #f59e0b;
}
QPushButton#HeaderToolButton:pressed {
    background: #f59e0b;
    color: #1c1917;
}

/* ── サイドバー ── */
QFrame#Sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #111118, stop:1 #0c0c12);
    border: 1px solid #2a2a38;
    border-radius: 16px;
}
QFrame#SidebarDivider {
    background: #252532;
    border: none;
    margin: 0;
}
QScrollArea#SidebarScroll {
    background: transparent;
    border: none;
}
QWidget#SidebarViewport {
    background: transparent;
}
QLabel#SidebarSection {
    color: #71717a;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.5px;
    padding: 0;
    margin: 0;
    background: transparent;
}
QLabel#KeyDisplay {
    color: #34d399;
    font-size: 15px;
    font-weight: 700;
    padding: 14px 16px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(52, 211, 153, 0.1), stop:1 rgba(52, 211, 153, 0.03));
    border: 1px solid rgba(52, 211, 153, 0.28);
    border-radius: 12px;
}
QLabel#KeyDisplayHint {
    color: #52525b;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 0 4px 6px 4px;
    background: transparent;
}
QPushButton#NavButton {
    background: #12121a;
    color: #d4d4d8;
    border: 1px solid #252532;
    border-radius: 10px;
    padding: 0 14px;
    margin: 0;
    text-align: left;
    font-weight: 600;
    font-size: 12px;
}
QPushButton#NavButton:hover {
    background: #1a1a24;
    border-color: #32324a;
    color: #fafafa;
}
QPushButton#NavButton:pressed {
    background: #252530;
}
QPushButton#NavButton:disabled {
    background: #0e0e14;
    color: #52525b;
    border: 1px solid #1f1f28;
}
QPushButton#NavButtonPrimary {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fbbf24, stop:1 #d97706);
    color: #1c1917;
    border: none;
    border-radius: 10px;
    padding: 0 14px;
    margin: 0;
    font-weight: 700;
    font-size: 12px;
    text-align: left;
}
QPushButton#NavButtonPrimary:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fcd34d, stop:1 #f59e0b);
}
QPushButton#NavButtonPrimary:disabled {
    background: #1a1a22;
    color: #3f3f46;
}
QPushButton#NavButtonPlay {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4ade80, stop:1 #16a34a);
    color: #052e16;
    border: none;
    border-radius: 10px;
    padding: 0 14px;
    margin: 0;
    font-weight: 700;
    font-size: 12px;
    text-align: left;
}
QPushButton#NavButtonPlay:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #86efac, stop:1 #22c55e);
}
QPushButton#NavButtonPlay:disabled {
    background: #1a1a22;
    color: #3f3f46;
}
QPushButton#NavButtonStop {
    background: #1a1a22;
    color: #fca5a5;
    border: 1px solid #3f1515;
    border-radius: 10px;
    padding: 0 14px;
    margin: 0;
    font-weight: 600;
    font-size: 12px;
    text-align: left;
}
QSpinBox#SidebarTempo {
    background: #0c0c12;
    color: #f4f4f5;
    border: 1px solid #32324a;
    border-radius: 10px;
    padding: 0 10px;
    margin: 0;
    font-weight: 700;
    font-size: 13px;
}
QSpinBox#SidebarTempo:disabled {
    color: #52525b;
    border-color: #252532;
}
QPushButton#NavButtonStop:hover {
    background: rgba(239, 68, 68, 0.15);
    border-color: #ef4444;
    color: #fecaca;
}
QPushButton#NavButtonStop:disabled {
    color: #3f3f46;
    border-color: #252532;
}

/* ── パネル ── */
QFrame#PanelCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #16161f, stop:1 #111118);
    border: 1px solid #2a2a38;
    border-radius: 16px;
}
QFrame#PanelTitleBar {
    background: transparent;
    border: none;
    border-bottom: 1px solid #252532;
}
QLabel#PanelTitle {
    color: #fafafa;
    font-size: 15px;
    font-weight: 700;
    background: transparent;
}
QLabel#PanelTitleAccent {
    color: #f59e0b;
    font-size: 18px;
    font-weight: 800;
    background: transparent;
    padding-right: 8px;
}
QLabel#PanelHint {
    color: #71717a;
    font-size: 11px;
    background: transparent;
}
QLabel#AssistBadge {
    background: rgba(167, 139, 250, 0.12);
    color: #c4b5fd;
    border: 1px solid rgba(167, 139, 250, 0.3);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1px;
}

/* ── タイムライン統計バー ── */
QFrame#TimelineStatsBar {
    background: #0e0e16;
    border: none;
    border-bottom: 1px solid #252532;
}
QLabel#TimelineStats {
    color: #a1a1aa;
    font-size: 12px;
    font-weight: 600;
    background: transparent;
}
QTableWidget#TimelineTable {
    font-size: 13px;
}
QTableWidget#TimelineTable QLineEdit {
    background-color: #12121a;
    color: #f4f4f5;
    border: 2px solid #f59e0b;
    border-radius: 4px;
    padding: 2px 8px;
    selection-background-color: #f59e0b;
    selection-color: #0c0c12;
}

/* ── テーブル（タイムライン） ── */
QTableWidget {
    gridline-color: #2a2a38;
    background-color: #0c0c12;
    alternate-background-color: #12121a;
    color: #f4f4f5;
    border: none;
    border-radius: 0;
    selection-background-color: rgba(245, 158, 11, 0.35);
    selection-color: #ffffff;
    outline: none;
    font-size: 12px;
}
QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #1a1a24;
}
QTableWidget::item:selected {
    background-color: rgba(245, 158, 11, 0.28);
    color: #ffffff;
}
QTableWidget::item:hover {
    background-color: #16161f;
}
QHeaderView::section {
    background-color: #14141c;
    color: #d4d4d8;
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid #f59e0b;
    border-right: 1px solid #252532;
    font-weight: 700;
    font-size: 11px;
}
QHeaderView::section:vertical {
    background-color: #111118;
    color: #71717a;
    border-bottom: 1px solid #252532;
    padding: 4px;
    font-size: 10px;
}

/* ── タブ ── */
QTabWidget::pane {
    border: 1px solid #252532;
    border-radius: 0 0 12px 12px;
    background: #0c0c12;
    top: -1px;
}
QTabBar::tab {
    background: #111118;
    color: #71717a;
    padding: 11px 20px;
    margin-right: 2px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-weight: 600;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: #1a1a24;
    color: #fbbf24;
    border-bottom: 2px solid #f59e0b;
}
QTabBar::tab:hover:!selected {
    background: #16161f;
    color: #d4d4d8;
}

QListWidget {
    background-color: #0c0c12;
    color: #d4d4d8;
    border: none;
    border-radius: 0;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    padding: 12px 14px;
    border-radius: 10px;
    margin: 3px 2px;
    border: 1px solid transparent;
}
QListWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(167, 139, 250, 0.2), stop:1 rgba(245, 158, 11, 0.12));
    border-color: rgba(245, 158, 11, 0.35);
    color: #fafafa;
}
QListWidget::item:hover:!selected {
    background: #16161f;
    border-color: #252532;
}

QSplitter::handle {
    background: #111118;
    width: 8px;
    margin: 4px 0;
    border-radius: 4px;
}
QSplitter::handle:hover {
    background: #f59e0b;
}

/* ── ウェルカム ── */
QWidget#WelcomePage {
    background: transparent;
}
QScrollArea#WelcomeScroll {
    background: transparent;
    border: none;
}
QWidget#WelcomeViewport {
    background: transparent;
}
QFrame#WelcomeCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #18181f, stop:1 #0e0e14);
    border: 1px solid rgba(245, 158, 11, 0.22);
    border-radius: 24px;
}
QFrame#DropZone {
    background: rgba(12, 12, 18, 0.9);
    border: 2px dashed #3f3f46;
    border-radius: 14px;
}
QFrame#DropZone:hover {
    border-color: #f59e0b;
    background: rgba(245, 158, 11, 0.04);
}
QLabel#DropZoneIcon {
    color: #f59e0b;
    font-size: 28px;
    background: transparent;
}
QLabel#DropZoneText {
    color: #a1a1aa;
    font-size: 13px;
    background: transparent;
}
QLabel#WelcomeIcon {
    color: #fbbf24;
    font-size: 48px;
    min-height: 52px;
    max-height: 56px;
    background: transparent;
}
QLabel#WelcomeTitle {
    color: #fafafa;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: transparent;
}
QLabel#WelcomeSubtitle {
    color: #a78bfa;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}
QLabel#WelcomeBody {
    color: #71717a;
    font-size: 12px;
    background: transparent;
}
QFrame#FeatureChip {
    background: #111118;
    border: 1px solid #252532;
    border-radius: 10px;
}
QLabel#FeatureChipTitle {
    color: #fbbf24;
    font-size: 11px;
    font-weight: 700;
    background: transparent;
}
QLabel#FeatureChipDesc {
    color: #52525b;
    font-size: 10px;
    background: transparent;
}

QFrame#PlotPlaceholder {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0c0c12, stop:1 #08080c);
    border: 1px dashed #32324a;
    border-radius: 14px;
    min-height: 220px;
}
QLabel#PlotPlaceholderTitle {
    color: #a1a1aa;
    font-size: 17px;
    font-weight: 700;
    background: transparent;
}
QLabel#PlotPlaceholderBody {
    color: #52525b;
    font-size: 12px;
    background: transparent;
}
QLabel#PlotPlaceholderIcon {
    color: #3f3f46;
    font-size: 40px;
    background: transparent;
}

QToolBar#PlotToolBar {
    background: #111118;
    border: none;
    border-bottom: 1px solid #252532;
    border-radius: 12px 12px 0 0;
    padding: 6px 8px;
    spacing: 4px;
}
QToolBar#PlotToolBar QToolButton {
    background: #1a1a22;
    border: 1px solid #252532;
    border-radius: 8px;
    padding: 6px;
    margin: 2px;
}
QToolBar#PlotToolBar QToolButton:hover {
    background: #252530;
    border-color: #f59e0b;
}

QFrame#PianoBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #111118, stop:1 #0a0a0e);
    border: 1px solid #2a2a38;
    border-radius: 16px;
}
QLabel#PianoBarTitle {
    color: #fafafa;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    background: transparent;
}
QLabel#PianoBarHint {
    color: #52525b;
    font-size: 10px;
    background: transparent;
}

QPushButton#BtnPrimary {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fbbf24, stop:1 #d97706);
    color: #1c1917;
    border: none;
    border-radius: 12px;
    padding: 14px 32px;
    font-weight: 800;
    font-size: 14px;
    letter-spacing: 0.3px;
}
QPushButton#BtnPrimary:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fcd34d, stop:1 #f59e0b);
}
QPushButton#BtnGhost {
    background: transparent;
    color: #a1a1aa;
    border: 1px solid #32324a;
    border-radius: 12px;
    padding: 12px 24px;
    font-weight: 600;
}
QPushButton#BtnGhost:hover {
    border-color: #f59e0b;
    color: #fbbf24;
}

QSpinBox {
    background: #0c0c12;
    color: #f4f4f5;
    border: 1px solid #32324a;
    border-radius: 10px;
    padding: 8px 10px;
    min-height: 44px;
    font-weight: 700;
    font-size: 13px;
    selection-background-color: #f59e0b;
}
QSpinBox:focus {
    border-color: #f59e0b;
}
QSpinBox::up-button, QSpinBox::down-button {
    background: #1a1a22;
    border: none;
    width: 20px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #252530;
}

/* ── ローディング ── */
QWidget#LoadingOverlay {
    background: rgba(5, 5, 8, 0.88);
}
QFrame#LoadingCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #18181f, stop:1 #0e0e14);
    border: 1px solid #f59e0b;
    border-radius: 20px;
    min-width: 340px;
}
QLabel#LoadingTitle {
    color: #fafafa;
    font-size: 17px;
    font-weight: 700;
}
QLabel#LoadingDetail {
    color: #71717a;
    font-size: 12px;
}
QWidget#LoadingOverlay QProgressBar {
    background: #0c0c12;
    border: 1px solid #32324a;
    border-radius: 4px;
    max-height: 6px;
}
QWidget#LoadingOverlay QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f59e0b, stop:1 #fbbf24);
    border-radius: 3px;
}

QMenuBar {
    background: transparent;
    color: #a1a1aa;
    padding: 4px 8px;
    spacing: 4px;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 8px;
    background: transparent;
}
QMenuBar::item:selected {
    background: #1a1a24;
    color: #fbbf24;
}
QMenu {
    background: #16161f;
    border: 1px solid #32324a;
    border-radius: 12px;
    padding: 8px;
}
QMenu::item {
    padding: 10px 28px 10px 16px;
    border-radius: 8px;
}
QMenu::item:selected {
    background: rgba(245, 158, 11, 0.2);
    color: #fafafa;
}
QMenu::separator {
    height: 1px;
    background: #252532;
    margin: 6px 8px;
}

QStatusBar {
    background: #0a0a10;
    color: #71717a;
    border-top: 1px solid #252532;
    padding: 6px 16px;
    font-size: 11px;
}
QLabel#StatusPill {
    background: #16161f;
    color: #a1a1aa;
    border: 1px solid #252532;
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 10px;
    font-weight: 600;
}

QScrollBar:vertical {
    background: #0c0c12;
    width: 10px;
    border-radius: 5px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #32324a;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #f59e0b;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #0c0c12;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #32324a;
    border-radius: 5px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: #f59e0b;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QMessageBox {
    background-color: #16161f;
}
QMessageBox QLabel {
    color: #f4f4f5;
}
QMessageBox QPushButton {
    background: #1a1a24;
    color: #f4f4f5;
    border: 1px solid #32324a;
    border-radius: 10px;
    padding: 10px 24px;
    min-width: 80px;
    font-weight: 600;
}
QMessageBox QPushButton:hover {
    border-color: #f59e0b;
    color: #fbbf24;
}

QToolTip {
    background: #18181f;
    color: #e4e4e7;
    border: 1px solid #f59e0b;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}
"""


def apply_app_font(app: QApplication) -> None:
    """OS に合わせた UI フォントを設定。"""
    if sys.platform == "win32":
        family = "Segoe UI"
    elif sys.platform == "darwin":
        family = "SF Pro Display"
    else:
        family = "Noto Sans"
    font = QFont(family, 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)
