"""Windows 點擊穿透的原生 fallback，在 Qt 內建設定失效時用 ctypes 疊加穿透旗標。"""
from __future__ import annotations

import sys

_GWL_EXSTYLE = -20
_WS_EX_LAYERED = 0x00080000
_WS_EX_TRANSPARENT = 0x00000020


def is_windows() -> bool:
  return sys.platform == "win32"


def force_click_through(hwnd: int) -> None:
  if not is_windows():
    return
  import ctypes

  user32 = ctypes.windll.user32
  style = user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
  user32.SetWindowLongW(hwnd, _GWL_EXSTYLE, style | _WS_EX_LAYERED | _WS_EX_TRANSPARENT)
