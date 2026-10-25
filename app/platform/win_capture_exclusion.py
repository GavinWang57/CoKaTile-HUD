"""Windows 截圖排除：讓指定視窗不出現在螢幕擷取結果中，避免放大鏡截到自己形成遞迴畫面。"""
from __future__ import annotations

import sys

_WDA_EXCLUDEFROMCAPTURE = 0x00000011


def exclude_from_capture(hwnd: int) -> bool:
  """回傳是否設定成功；非 Windows 或 Windows 10 2004 之前的版本會失敗。"""
  if sys.platform != "win32":
    return False
  import ctypes

  return bool(ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, _WDA_EXCLUDEFROMCAPTURE))
