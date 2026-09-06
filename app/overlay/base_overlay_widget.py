"""覆蓋層與 HUD 視窗共用的視窗旗標設定（永遠置頂、透明背景、可選點擊穿透）。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


def apply_overlay_window_flags(widget: QWidget, click_through: bool = True) -> None:
  flags = (
    Qt.WindowType.FramelessWindowHint
    | Qt.WindowType.WindowStaysOnTopHint
    | Qt.WindowType.Tool
  )
  if click_through:
    flags |= Qt.WindowType.WindowTransparentForInput
  widget.setWindowFlags(flags)
  widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
  widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
  if click_through:
    widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
