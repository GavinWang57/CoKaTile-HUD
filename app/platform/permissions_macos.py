"""macOS 輔助使用權限（Accessibility）偵測與提示。"""
from __future__ import annotations

import sys


def is_macos() -> bool:
  return sys.platform == "darwin"


def has_accessibility_permission() -> bool | None:
  """回傳 None 表示非 macOS 或無法檢查，呼叫端應視為「不需檢查」而非「未授權」。"""
  if not is_macos():
    return None
  try:
    from Quartz import AXIsProcessTrustedWithOptions
  except ImportError:
    return None
  return bool(AXIsProcessTrustedWithOptions(None))


def prompt_accessibility_permission() -> None:
  """引導使用者到系統設定開啟輔助使用權限。"""
  from PySide6.QtCore import QUrl
  from PySide6.QtGui import QDesktopServices

  QDesktopServices.openUrl(
    QUrl("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")
  )
