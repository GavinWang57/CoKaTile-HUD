"""Windows GDI 螢幕區域擷取，可在背景執行緒使用（Qt 的 QScreen.grabWindow 只能在主執行緒呼叫）。"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtGui import QImage

_SRCCOPY = 0x00CC0020
_CAPTUREBLT = 0x40000000  # 一併擷取 layered window（例如聚光燈覆蓋層）
_DIB_RGB_COLORS = 0
_BI_RGB = 0


class _BitmapInfoHeader(ctypes.Structure):
  _fields_ = [
    ("biSize", wintypes.DWORD),
    ("biWidth", wintypes.LONG),
    ("biHeight", wintypes.LONG),
    ("biPlanes", wintypes.WORD),
    ("biBitCount", wintypes.WORD),
    ("biCompression", wintypes.DWORD),
    ("biSizeImage", wintypes.DWORD),
    ("biXPelsPerMeter", wintypes.LONG),
    ("biYPelsPerMeter", wintypes.LONG),
    ("biClrUsed", wintypes.DWORD),
    ("biClrImportant", wintypes.DWORD),
  ]


def _load_gdi():
  # 明確宣告 handle 型別，否則 64 位元下 ctypes 預設以 int 傳遞會截斷指標
  user32 = ctypes.WinDLL("user32")
  gdi32 = ctypes.WinDLL("gdi32")
  user32.GetDC.argtypes = [wintypes.HWND]
  user32.GetDC.restype = wintypes.HDC
  user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
  gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
  gdi32.CreateCompatibleDC.restype = wintypes.HDC
  gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC,
    ctypes.POINTER(_BitmapInfoHeader),
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p),
    wintypes.HANDLE,
    wintypes.DWORD,
  ]
  gdi32.CreateDIBSection.restype = wintypes.HBITMAP
  gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
  gdi32.SelectObject.restype = wintypes.HGDIOBJ
  gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
  gdi32.DeleteDC.argtypes = [wintypes.HDC]
  gdi32.BitBlt.argtypes = [
    wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD,
  ]
  gdi32.BitBlt.restype = wintypes.BOOL
  return user32, gdi32


class GdiRegionCapturer:
  """持有擷取用的 DC 與 DIB，同尺寸時重複使用；需在同一個執行緒建立、使用與關閉。"""

  def __init__(self):
    self._user32, self._gdi32 = _load_gdi()
    self._screen_dc = self._user32.GetDC(None)
    self._mem_dc = self._gdi32.CreateCompatibleDC(self._screen_dc)
    self._bitmap = None
    self._old_bitmap = None
    self._bits = ctypes.c_void_p()
    self._size = (0, 0)

  def capture(self, x: int, y: int, width: int, height: int) -> QImage:
    """擷取實體像素座標下的螢幕區域。"""
    if (width, height) != self._size:
      self._recreate_bitmap(width, height)
    self._gdi32.BitBlt(self._mem_dc, 0, 0, width, height, self._screen_dc, x, y, _SRCCOPY | _CAPTUREBLT)
    data = ctypes.string_at(self._bits, width * height * 4)
    return QImage(data, width, height, width * 4, QImage.Format.Format_RGB32).copy()

  def close(self) -> None:
    self._release_bitmap()
    self._gdi32.DeleteDC(self._mem_dc)
    self._user32.ReleaseDC(None, self._screen_dc)

  def _recreate_bitmap(self, width: int, height: int) -> None:
    self._release_bitmap()
    header = _BitmapInfoHeader()
    header.biSize = ctypes.sizeof(_BitmapInfoHeader)
    header.biWidth = width
    header.biHeight = -height  # 負值代表 top-down，與 QImage 的列順序一致
    header.biPlanes = 1
    header.biBitCount = 32
    header.biCompression = _BI_RGB
    self._bitmap = self._gdi32.CreateDIBSection(
      self._mem_dc, ctypes.byref(header), _DIB_RGB_COLORS, ctypes.byref(self._bits), None, 0
    )
    self._old_bitmap = self._gdi32.SelectObject(self._mem_dc, self._bitmap)
    self._size = (width, height)

  def _release_bitmap(self) -> None:
    if self._bitmap is None:
      return
    self._gdi32.SelectObject(self._mem_dc, self._old_bitmap)
    self._gdi32.DeleteObject(self._bitmap)
    self._bitmap = None
    self._size = (0, 0)
