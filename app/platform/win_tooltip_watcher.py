"""透過 WinEvent hook 追蹤其他程式顯示的提示視窗（tooltip），讓放大鏡能避開不蓋住它。"""
from __future__ import annotations

import ctypes
import math
from ctypes import wintypes

from PySide6.QtCore import QRect

from app.platform.screen_utils import capture_screen_dpi_info, physical_to_logical_point

_EVENT_OBJECT_DESTROY = 0x8001
_EVENT_OBJECT_SHOW = 0x8002
_EVENT_OBJECT_HIDE = 0x8003
_WINEVENT_OUTOFCONTEXT = 0x0000
_WINEVENT_SKIPOWNPROCESS = 0x0002
_OBJID_WINDOW = 0
_CHILDID_SELF = 0
_GA_ROOT = 2
_GWL_STYLE = -16
_GWL_EXSTYLE = -20

_WS_POPUP = 0x80000000
_WS_CHILD = 0x40000000
_WS_EX_TOPMOST = 0x00000008
_WS_EX_TOOLWINDOW = 0x00000080
_WS_EX_NOACTIVATE = 0x08000000

# 推測用的門檻（實體像素）：提示視窗通常很小，且緊鄰游標出現
_MAX_TOOLTIP_WIDTH = 1200
_MAX_TOOLTIP_HEIGHT = 500
_MAX_DISTANCE_FROM_CURSOR = 200


def is_tooltip_like(
  class_name: str, style: int, ex_style: int, rect: tuple[int, int, int, int], cursor: tuple[int, int]
) -> bool:
  """判斷新顯示的頂層視窗是否像提示視窗。rect 為 (left, top, right, bottom)，皆為實體像素。

  類別名稱含 tooltip 的（Win32 tooltips_class32、Qt 的 ToolTip 視窗等）直接認定；
  Chrome/Electron 這類沒有專屬類別的，則以「游標附近的小型置頂浮動視窗」推測。
  """
  if "tooltip" in class_name.lower():
    return True
  if not style & _WS_POPUP or style & _WS_CHILD:
    return False
  if not ex_style & (_WS_EX_TOPMOST | _WS_EX_TOOLWINDOW | _WS_EX_NOACTIVATE):
    return False
  left, top, right, bottom = rect
  width, height = right - left, bottom - top
  if not (0 < width <= _MAX_TOOLTIP_WIDTH and 0 < height <= _MAX_TOOLTIP_HEIGHT):
    return False
  dx = max(left - cursor[0], 0, cursor[0] - right)
  dy = max(top - cursor[1], 0, cursor[1] - bottom)
  return math.hypot(dx, dy) <= _MAX_DISTANCE_FROM_CURSOR


# WINFUNCTYPE 只存在於 Windows 版 ctypes；其他平台仍可匯入本模組使用 is_tooltip_like
_WINEVENTPROC = (
  ctypes.WINFUNCTYPE(
    None, wintypes.HANDLE, wintypes.DWORD, wintypes.HWND, wintypes.LONG, wintypes.LONG, wintypes.DWORD, wintypes.DWORD
  )
  if hasattr(ctypes, "WINFUNCTYPE")
  else None
)


def _load_user32():
  user32 = ctypes.WinDLL("user32")
  user32.SetWinEventHook.argtypes = [
    wintypes.DWORD, wintypes.DWORD, wintypes.HMODULE, _WINEVENTPROC, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
  ]
  user32.SetWinEventHook.restype = wintypes.HANDLE
  user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
  user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
  user32.GetAncestor.restype = wintypes.HWND
  user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
  user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
  user32.GetWindowLongW.restype = wintypes.LONG
  user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
  user32.IsWindowVisible.argtypes = [wintypes.HWND]
  user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
  return user32


class WinTooltipWatcher:
  """需在有 Windows 訊息迴圈的執行緒（Qt 主執行緒）上建立，hook 回呼才會被送達。"""

  def __init__(self):
    self._user32 = _load_user32()
    self._tooltips: set[int] = set()
    self._hook = None
    # 回呼物件必須保留參照，否則被回收後 Windows 呼叫到已釋放的位址會讓程式崩潰
    self._callback = _WINEVENTPROC(self._on_win_event)

  def start(self) -> None:
    if self._hook:
      return
    self._hook = self._user32.SetWinEventHook(
      _EVENT_OBJECT_DESTROY,
      _EVENT_OBJECT_HIDE,
      None,
      self._callback,
      0,
      0,
      _WINEVENT_OUTOFCONTEXT | _WINEVENT_SKIPOWNPROCESS,
    )

  def stop(self) -> None:
    if self._hook:
      self._user32.UnhookWinEvent(self._hook)
      self._hook = None
    self._tooltips.clear()

  def tooltip_rects(self) -> list[QRect]:
    """目前仍顯示中的提示視窗範圍（Qt 邏輯座標）。"""
    rects = []
    dpi_info = capture_screen_dpi_info()
    for hwnd in list(self._tooltips):
      if not self._user32.IsWindowVisible(hwnd):
        self._tooltips.discard(hwnd)
        continue
      left, top, right, bottom = self._window_rect(hwnd)
      logical_left, logical_top = physical_to_logical_point(left, top, dpi_info)
      logical_right, logical_bottom = physical_to_logical_point(right, bottom, dpi_info)
      rects.append(QRect(logical_left, logical_top, logical_right - logical_left, logical_bottom - logical_top))
    return rects

  def _on_win_event(self, hook, event, hwnd, id_object, id_child, thread_id, timestamp) -> None:
    try:
      if not hwnd or id_object != _OBJID_WINDOW or id_child != _CHILDID_SELF:
        return
      if event != _EVENT_OBJECT_SHOW:
        self._tooltips.discard(hwnd)
        return
      if self._user32.GetAncestor(hwnd, _GA_ROOT) != hwnd:
        return
      if self._is_tooltip(hwnd):
        self._tooltips.add(hwnd)
    except Exception:  # 回呼中的例外無法往上拋回 Windows，吞掉避免影響整個 hook
      pass

  def _is_tooltip(self, hwnd: int) -> bool:
    buffer = ctypes.create_unicode_buffer(256)
    self._user32.GetClassNameW(hwnd, buffer, len(buffer))
    style = self._user32.GetWindowLongW(hwnd, _GWL_STYLE) & 0xFFFFFFFF
    ex_style = self._user32.GetWindowLongW(hwnd, _GWL_EXSTYLE) & 0xFFFFFFFF
    cursor = wintypes.POINT()
    self._user32.GetCursorPos(ctypes.byref(cursor))
    return is_tooltip_like(buffer.value, style, ex_style, self._window_rect(hwnd), (cursor.x, cursor.y))

  def _window_rect(self, hwnd: int) -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom
