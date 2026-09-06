"""螢幕幾何相關的輔助函式。"""
from __future__ import annotations

from PySide6.QtCore import QRect
from PySide6.QtGui import QGuiApplication, QScreen


def virtual_desktop_rect() -> QRect:
  """回傳涵蓋所有螢幕的整體邊界矩形。"""
  rect = QRect()
  for screen in QGuiApplication.screens():
    rect = rect.united(screen.geometry())
  return rect


def screen_containing_point(x: int, y: int) -> QScreen | None:
  for screen in QGuiApplication.screens():
    if screen.geometry().contains(x, y):
      return screen
  return QGuiApplication.primaryScreen()


def capture_screen_dpi_info() -> list[tuple[int, int, int, int, float]]:
  """擷取目前各螢幕的（logical 邊界, devicePixelRatio），供背景執行緒安全地換算座標用。

  Windows 在有顯示縮放（如 125%）時，pynput 等全域 hook 回傳的是「實體像素」座標，
  但 Qt 的螢幕/視窗幾何是「邏輯像素」座標（實體 ÷ devicePixelRatio）。兩者混用會讓
  游標離螢幕原點越遠、換算誤差越大。這裡只在主執行緒讀取一次 Qt 物件，避免背景執行緒
  直接呼叫 Qt API。
  """
  app = QGuiApplication.instance()
  if app is None:
    return []
  infos = []
  for screen in app.screens():
    geo = screen.geometry()
    infos.append((geo.left(), geo.top(), geo.right(), geo.bottom(), screen.devicePixelRatio()))
  return infos


def physical_to_logical_point(
  x: int, y: int, screen_dpi_info: list[tuple[int, int, int, int, float]]
) -> tuple[int, int]:
  """把實體像素座標換算成 Qt 的邏輯座標；純函式，不觸碰 Qt 物件，背景執行緒呼叫也安全。"""
  for left, top, right, bottom, dpr in screen_dpi_info:
    logical_x, logical_y = x / dpr, y / dpr
    if left <= logical_x <= right and top <= logical_y <= bottom:
      return round(logical_x), round(logical_y)
  if screen_dpi_info:
    dpr = screen_dpi_info[0][4]
    return round(x / dpr), round(y / dpr)
  return x, y
